"""
Main Window UI for KOReader Store
"""

import re
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTabWidget, QComboBox, QMessageBox, QProgressDialog, 
    QFileDialog, QScrollArea, QFrame, QGridLayout, QProgressBar, QInputDialog, QDialog, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, QTimer, QUrl
from PyQt6.QtGui import QFont, QDesktopServices, QTextDocument

# Try to import QWebEngineView - fallback to QTextEdit if not available
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage
    WEBENGINE_AVAILABLE = True
except ImportError:
    print("Warning: PyQt6-WebEngine not available. Install with: pip install PyQt6-WebEngine")
    print("Falling back to QTextEdit for README display (limited functionality)")
    WEBENGINE_AVAILABLE = False
    QWebEngineView = None
    QWebEnginePage = None


class ExternalLinkPage(QWebEnginePage):
    """Custom WebEnginePage that opens external links in system browser"""
    
    def acceptNavigationRequest(self, url, nav_type, isMainFrame):
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False  # Don't navigate in the WebView
        return True


def sanitize_readme_html(html_content):
    """Sanitize README HTML by removing scripts, iframes, and potentially unsafe content"""
    import re
    
    # Remove script tags and their content
    html_content = re.sub(r'<script.*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove iframe tags and their content
    html_content = re.sub(r'<iframe.*?>.*?</iframe>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove other potentially unsafe tags
    unsafe_tags = ['object', 'embed', 'form', 'input', 'button', 'select', 'textarea']
    for tag in unsafe_tags:
        html_content = re.sub(f'<{tag}.*?>.*?</{tag}>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(f'<{tag}[^>]*>', '', html_content, flags=re.IGNORECASE)
    
    # Remove inline event handlers
    html_content = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)
    
    # Remove javascript: URLs
    html_content = re.sub(r'href\s*=\s*["\']javascript:[^"\']*["\']', '', html_content, flags=re.IGNORECASE)
    
    return html_content


def detect_support_links(html_content, repo_url):
    """Detect support platform links and return support button info"""
    support_info = []
    
    # Common support platforms
    platforms = {
        'buymeacoffee.com': ('☕ Buy me a Coffee', '#ff813f'),
        'ko-fi.com': ('☕ Support on Ko-fi', '#29abe0'),
        'patreon.com': ('🎁 Become a Patron', '#f96854'),
        'github.com/sponsors': ('🤝 Sponsor on GitHub', '#ea4aaa'),
        'liberapay.com': ('💝 Donate on Liberapay', '#f6c915'),
        'paypal.me': ('💸 Support via PayPal', '#00457c'),
    }
    
    import re
    for domain, (label, color) in platforms.items():
        # Look for links to these platforms
        pattern = rf'href=["\']([^"\']*{domain}[^"\']*)["\']'
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        
        if matches:
            # Extract username from URL if possible
            url = matches[0]
            support_info.append({
                'url': url,
                'label': label,
                'color': color,
                'domain': domain
            })
    
    return support_info

from ui.themes import LIGHT_THEME, PRIMARY, SUCCESS, ERROR
from ui.plugin_card import PluginCard
from ui.loading_overlay import LoadingOverlay
from ui.readme_text_edit import ReadmeTextEdit
from ui.patch_selection_dialog import PatchSelectionDialog
from api.github import GitHubAPI
from workers.download_worker import DownloadWorker
from services.device_detection import DeviceDetection
from services.plugin_installer import PluginInstaller
from services.cache import CacheService
from services.update_service import UpdateService
from utils.markdown import convert_markdown_to_html

logger = logging.getLogger(__name__)


class KOReaderStore(QMainWindow):
    """Main window of KOReader Store App"""
    
    def __init__(self):
        logger.info("Initializing KoStore application")
        super().__init__()
        
        self.koreader_path = None
        self.plugins = []
        self.patches = []
        self.installed_plugins = set()
        
        # Services
        self.cache_service = CacheService()
        
        # Initialize cached updates
        self.cached_updates = {}
        
        # Token storage
        self.token_file = Path("koreader_store_token.json")
        
        # Load saved token or prompt for new one
        saved_token = self.load_saved_token()
        if not saved_token:
            github_token = self.prompt_for_github_token()
            if github_token:
                self.save_token(github_token)
        else:
            github_token = saved_token
        
        # Initialize API and services
        self.api = GitHubAPI(token=github_token)
        self.update_service = UpdateService(self.api)
        self.device_detection = DeviceDetection()
        
        # Initialize UI
        self.init_ui()
        
        # Show loading screen
        self.loading_overlay = LoadingOverlay(self)
        # Don't show immediately - let background_init handle it
        
        # Start background initialization
        QTimer.singleShot(100, self.background_init)
    
    def background_init(self):
        """Background initialization to avoid blocking UI"""
        try:
            logger.info("Starting background initialization")
            
            # Show loading overlay
            self.loading_overlay.show_loading(self)
            
            # Load cache first
            logger.info("Loading cached data")
            if self.cache_service.get_plugins() and self.cache_service.get_patches():
                logger.info("Using cached data, displaying items")
                self.plugins = self.cache_service.get_plugins()
                self.patches = self.cache_service.get_patches()
                self.display_items(self.plugins, self.plugins_layout, "plugin")
                self.display_items(self.patches, self.patches_layout, "patch")
            
            # Device detection
            logger.info("Detecting KOReader devices")
            self.detect_koreader_device()
            
            # Load fresh data if cache is empty or expired
            if not self.plugins or not self.patches:
                logger.info("No cached data available, fetching from GitHub")
                self.load_data()
            
            # Hide loading screen
            self.loading_overlay.hide_loading()
            logger.info("Background initialization completed")
            
        except Exception as e:
            logger.error(f"Error during background initialization: {e}")
            self.loading_overlay.hide_loading()
            QMessageBox.critical(self, "Error", f"Failed to initialize: {e}")
    
    def init_ui(self):
        logger.info("Initializing main UI components")
        
        # Apply light theme FIRST - before creating any UI components
        self.setStyleSheet(LIGHT_THEME)
        
        self.setWindowTitle("KoStore")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Search & Filter Bar
        search_bar = self.create_search_bar()
        main_layout.addWidget(search_bar)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Plugins Tab
        self.plugins_scroll = QScrollArea()
        self.plugins_scroll.setWidgetResizable(True)
        self.plugins_container = QWidget()
        self.plugins_layout = QGridLayout(self.plugins_container)
        self.plugins_layout.setSpacing(15)
        self.plugins_scroll.setWidget(self.plugins_container)
        
        # Patches Tab
        self.patches_scroll = QScrollArea()
        self.patches_scroll.setWidgetResizable(True)
        self.patches_container = QWidget()
        self.patches_layout = QGridLayout(self.patches_container)
        self.patches_layout.setSpacing(15)
        self.patches_scroll.setWidget(self.patches_container)
        
        self.tabs.addTab(self.plugins_scroll, "Plugins")
        self.tabs.addTab(self.patches_scroll, "Patches")
        
        main_layout.addWidget(self.tabs)
        
        logger.info("UI initialization completed")
    
    def create_header(self):
        """Create header with logo and device status"""
        logger.info("Creating header component")
        header = QFrame()
        
        layout = QHBoxLayout(header)
        
        # Logo and Title
        title_layout = QVBoxLayout()
        title = QLabel(" KoStore")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        subtitle = QLabel("Plugins & Patches Hub")
        subtitle.setStyleSheet("font-size: 14px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Device Status
        self.device_status = QLabel(" No device detected")
        layout.addWidget(self.device_status)
        
        # Path Button
        path_btn = QPushButton("Choose Path...")
        path_btn.clicked.connect(self.select_koreader_path)
        layout.addWidget(path_btn)
        
        return header
    
    def create_search_bar(self):
        """Create enhanced search bar with filters"""
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 16px;
                padding: 20px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        main_layout = QVBoxLayout(bar)
        main_layout.setSpacing(15)
        
        # Top search row
        search_row = QHBoxLayout()
        
        # Search input with icon
        search_container = QFrame()
        search_container.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
                padding: 5px;
            }
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(15, 8, 15, 8)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 16px;")
        search_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search plugins and patches...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                font-size: 14px;
                padding: 5px;
            }
        """)
        self.search_input.textChanged.connect(self.filter_items)
        search_layout.addWidget(self.search_input)
        
        search_row.addWidget(search_container, stretch=4)
        
        # Filter chips
        filter_chips = QHBoxLayout()
        filter_chips.setSpacing(10)
        
        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.addItems(["🎯 All Categories", "⭐ Top Rated", "🆕 Recently Updated", "🔥 Trending", "📚 Most Installed", "🛠️ Utilities", "📖 Readers", "🎨 Themes", "🔧 System"])
        self.category_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 20px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid currentColor;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                selection-background-color: #3b82f6;
            }
        """)
        self.category_combo.currentTextChanged.connect(self.filter_items)
        filter_chips.addWidget(self.category_combo)
        
        # Sort filter
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["📊 Sort", "⭐ Stars", "📅 Updated", "📝 Name", "👥 Downloads"])
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(34, 197, 94, 0.2);
                border: 1px solid rgba(34, 197, 94, 0.5);
                border-radius: 20px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid currentColor;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                selection-background-color: #22c55e;
            }
        """)
        self.sort_combo.currentTextChanged.connect(self.filter_items)
        filter_chips.addWidget(self.sort_combo)
        
        # Status filter
        self.status_combo = QComboBox()
        self.status_combo.addItems(["🎮 Status", "✅ Installed", "⬆️ Updates Available", "🆕 Not Installed"])
        self.status_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(168, 85, 247, 0.2);
                border: 1px solid rgba(168, 85, 247, 0.5);
                border-radius: 20px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid currentColor;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                selection-background-color: #a855f7;
            }
        """)
        self.status_combo.currentTextChanged.connect(self.filter_items)
        filter_chips.addWidget(self.status_combo)
        
        filter_chips.addStretch()
        
        # Check for Updates button
        check_updates_btn = QPushButton("⬆️ Check Updates")
        check_updates_btn.setObjectName("checkUpdatesBtn")
        check_updates_btn.clicked.connect(self.check_for_updates)
        filter_chips.addWidget(check_updates_btn)
        
        # Refresh button with modern style
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("refreshBtn")
        refresh_btn.clicked.connect(lambda: self.load_data(force_refresh=True))
        filter_chips.addWidget(refresh_btn)
        
        search_row.addLayout(filter_chips)
        main_layout.addLayout(search_row)
        
        return bar
    
    def save_token(self, token):
        """Save GitHub token to file"""
        try:
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump({'token': token}, f, indent=2)
            logger.info("GitHub token saved successfully")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
    
    def load_saved_token(self):
        """Load saved GitHub token from file"""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    token = data.get('token')
                    #validate token format if invalid will prompt again on next run of program.
                    valid_token = re.search(r"^ghp_[a-zA-Z0-9]{36}$",token)
                    if valid_token:
                        logger.info("Loaded saved GitHub token")
                        return token
                    else:
                        logger.warning("Invalid Token Format")
                        return None
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
        return None
    
    def detect_koreader_device(self):
        """Detect KOReader device"""
        logger.info("Starting KOReader device detection")
        
        koreader_path = self.device_detection.detect_koreader_device()
        
        if koreader_path:
            self.koreader_path = koreader_path
            logger.info(f"Selected KOReader device: {self.koreader_path}")
            self.update_device_status(True)
            self.plugin_installer = PluginInstaller(str(self.koreader_path))
            self.load_installed_plugins()
        else:
            logger.info("No KOReader devices detected")
            self.update_device_status(False)
    
    def select_koreader_path(self):
        """Manually select KOReader path"""
        path = QFileDialog.getExistingDirectory(self, "Select KOReader Device")
        if path:
            selected_path = Path(path)
            device_info = self.device_detection.get_device_info(str(selected_path))
            
            if device_info["valid"]:
                self.koreader_path = selected_path
                self.update_device_status(True)
                self.plugin_installer = PluginInstaller(str(self.koreader_path))
                self.load_installed_plugins()
                logger.info(f"Manually selected KOReader device: {self.koreader_path}")
            else:
                QMessageBox.warning(self, "Error", 
                    "No valid KOReader device found!\n\n"
                    "Please select the main directory of your device that contains koreader.sh.")
    
    def update_device_status(self, connected):
        """Update device status display"""
        if connected:
            from pathlib import Path
            path_name = Path(self.koreader_path).name
            self.device_status.setText(f" Connected: {path_name}")
            self.device_status.setStyleSheet(f"""
                background-color: #ecfdf5;
color: {SUCCESS};
border: 1px solid #bbf7d0;

                padding: 10px 20px;
                border-radius: 20px;
                border: 1px solid rgba(34, 197, 94, 0.3);
                font-weight: bold;
            """)
        else:
            self.device_status.setText(" No device detected")
            self.device_status.setStyleSheet(f"""
                background-color: #fef2f2;
color: {ERROR};
border: 1px solid #fecaca;

                border-radius: 20px;
                border: 1px solid rgba(239, 68, 68, 0.3);
                font-weight: bold;
            """)
    
    def load_installed_plugins(self):
        """Load list of installed plugins"""
        if not self.plugin_installer:
            return
        
        logger.info("Loading installed plugins")
        self.installed_plugins.clear()
        
        installed = self.plugin_installer.get_installed_plugins()
        for plugin_name in installed.keys():
            self.installed_plugins.add(plugin_name)
        
        logger.info(f"Loaded {len(self.installed_plugins)} installed plugins")
    
    def load_data(self, force_refresh=False):
        """Load plugins and patches from GitHub with caching"""
        if not force_refresh and not self.cache_service.is_cache_expired():
            logger.info("Using cached data")
            self.plugins = self.cache_service.get_plugins()
            self.patches = self.cache_service.get_patches()
            self.display_items(self.plugins, self.plugins_layout, "plugin")
            self.display_items(self.patches, self.patches_layout, "patch")
            return
        
        logger.info("Loading data from GitHub")
        
        try:
            # Load plugins
            self.plugins = self.api.search_repositories(
                topic="koreader-plugin",
                name_patterns=["koplugin", "koreader"]  # KOReader-specific patterns
            )
            
            # Load patches
            self.patches = self.api.search_repositories(
                topic="koreader-user-patch",
                name_patterns=["patch", "patches"]
            )
            
            # Filter by type
            self.plugins = [p for p in self.plugins if p.get("repo_type") == "plugin"]
            self.patches = [p for p in self.patches if p.get("repo_type") == "patch"]
            
            # Display items
            self.display_items(self.plugins, self.plugins_layout, "plugin")
            self.display_items(self.patches, self.patches_layout, "patch")
            
            # Save to cache
            self.cache_service.update_cache(self.plugins, self.patches)
            
            logger.info(f"Successfully loaded {len(self.plugins)} plugins and {len(self.patches)} patches")
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            QMessageBox.warning(self, "Warning", 
                "Failed to load data. Please check your internet connection.")
    
    def display_items(self, items, layout, item_type):
        """Display items in grid layout"""
        # Clear layout
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Check for updates if we have installed plugins and update service
        # Only check if updates were previously checked (stored in self.cached_updates)
        updates = self.cached_updates if hasattr(self, 'cached_updates') else {}
        
        # Add items
        col = 0
        row = 0
        for item in items:
            item_name = item.get("name") or "Unknown"
            installed = item_name in self.installed_plugins
            
            # Check if this plugin has an update
            has_update = False
            if installed and item_name in updates:
                # Don't show update badge if installed version is "Unknown"
                update_info = updates[item_name]
                if update_info.get("installed_version", "Unknown") != "Unknown":
                    has_update = True
            elif installed:
                # Also check by removing .koplugin suffix
                clean_name = item_name.replace(".koplugin", "")
                if clean_name in updates:
                    update_info = updates[clean_name]
                    if update_info.get("installed_version", "Unknown") != "Unknown":
                        has_update = True
            
            card = PluginCard(item, installed, has_update)
            card.install_clicked.connect(lambda data, has_update, t=item_type: self.install_item(data, t, has_update))
            card.details_clicked.connect(self.show_details)
            layout.addWidget(card, row, col)
            
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        # Add stretch at bottom
        layout.setRowStretch(row + 1, 1)
    
    def filter_items(self):
        """Filter displayed items"""
        try:
            query = self.search_input.text().lower()
            category = self.category_combo.currentText()
            sort_option = self.sort_combo.currentText()
            status_option = self.status_combo.currentText()
            
            # Get current tab items
            current_tab = self.tabs.currentIndex()
            items = self.plugins if current_tab == 0 else self.patches
            layout = self.plugins_layout if current_tab == 0 else self.patches_layout
            item_type = "plugin" if current_tab == 0 else "patch"
            
            # Filter
            filtered = []
            for item in items:
                item_name = item.get("name") or ""
                item_desc = item.get("description") or ""
                
                # Search filter
                if query not in item_name.lower() and query not in item_desc.lower():
                    continue
                
                # Category filter
                if category == "⭐ Top Rated" and item.get("stargazers_count", 0) < 50:
                    continue
                elif category == "🆕 Recently Updated":
                    try:
                        updated_str = item.get("updated_at", "")
                        if updated_str:
                            updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                            days_old = (datetime.now(updated.tzinfo) - updated).days
                            if days_old > 30:
                                continue
                    except:
                        continue
                
                # Status filter
                installed = item_name in self.installed_plugins
                if status_option == "✅ Installed" and not installed:
                    continue
                elif status_option == "🆕 Not Installed" and installed:
                    continue
                
                filtered.append(item)
            
            # Sort items
            if sort_option == "⭐ Stars":
                filtered.sort(key=lambda x: x.get('stargazers_count', 0), reverse=True)
            elif sort_option == "📅 Updated":
                filtered.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            elif sort_option == "📝 Name":
                filtered.sort(key=lambda x: x.get('name', '').lower())
            
            self.display_items(filtered, layout, item_type)
        except Exception as e:
            logger.error(f"Error in filter_items: {e}")
    
    def check_for_updates(self):
        """Check for updates manually when button is clicked"""
        if not self.installed_plugins or not self.update_service:
            QMessageBox.information(self, "Info", "No installed plugins found or update service not available.")
            return
        
        try:
            # Show progress dialog
            progress = QProgressDialog(self)
            progress.setWindowTitle("Checking for Updates")
            progress.setLabelText("Checking for plugin updates...")
            progress.setCancelButton(None)
            progress.setRange(0, 0)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            # Get detailed installed plugins info
            installed_plugins_info = {}
            if self.plugin_installer:
                installed_plugins_info = self.plugin_installer.get_installed_plugins()
            
            # Check for updates
            self.cached_updates = self.update_service.check_for_updates(installed_plugins_info, self.plugins)
            
            progress.close()
            
            update_count = len(self.cached_updates)
            if update_count > 0:
                QMessageBox.information(self, "Updates Available", 
                    f"Found updates for {update_count} plugin(s)!\n\nPlugins with updates will show an update badge.")
            else:
                QMessageBox.information(self, "No Updates", "All plugins are up to date!")
            
            # Refresh display to show update badges
            self.filter_items()
            
        except Exception as e:
            progress.close()
            logger.error(f"Error checking for updates: {e}")
            QMessageBox.critical(self, "Error", f"Failed to check for updates:\n{e}")
    
    def install_item(self, data, item_type, is_update=False):
        """Install plugin or patch"""
        if not self.plugin_installer:
            QMessageBox.warning(self, "Error", 
                "No KOReader device connected!\n\n"
                "Please connect your device or choose the path manually.")
            return
        
        # For patches, show selection dialog
        if item_type == "patch":
            self.show_patch_selection_dialog(data)
        else:
            # For plugins, use the original flow
            self.start_plugin_installation(data, is_update)
    
    def show_patch_selection_dialog(self, data):
        """Show patch selection dialog"""
        try:
            dialog = PatchSelectionDialog(self, data, self.api)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # User selected patches, install them
                selected_patches = dialog.selected_patches
                if selected_patches:
                    self.install_selected_patches(data, selected_patches)
                else:
                    QMessageBox.information(self, "Info", "No patches selected for installation.")
        except Exception as e:
            logger.error(f"Error showing patch selection dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to show patch selection:\n{e}")
    
    def install_selected_patches(self, patch_data, selected_patches):
        """Install the selected patches"""
        try:
            # Create patch data for installer
            patches_to_install = []
            for patch_file in selected_patches:
                # Construct download URL for the patch file
                download_url = f"https://raw.githubusercontent.com/{patch_data['owner']['login']}/{patch_data['name']}/main/{patch_file['path']}"
                patches_to_install.append({
                    'name': patch_file['name'],
                    'download_url': download_url,
                    'path': patch_file['path']
                })
            
            # Show progress dialog
            self.progress_dialog = QProgressDialog(self)
            self.progress_dialog.setWindowTitle("Installing Patches")
            self.progress_dialog.setLabelText(f"Installing {len(patches_to_install)} selected patch(es)...")
            self.progress_dialog.setCancelButton(None)
            self.progress_dialog.setRange(0, 0)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.show()
            
            # Install patches using the plugin installer
            result = self.plugin_installer.install_patches(patches_to_install)
            
            self.progress_dialog.close()
            
            if result["success"]:
                QMessageBox.information(self, "Success", 
                    f"{result['message']}\n\nPlease restart KOReader to use the patches.")
            else:
                QMessageBox.critical(self, "Error", f"Patch installation failed:\n{result['message']}")
                
        except Exception as e:
            if hasattr(self, 'progress_dialog'):
                self.progress_dialog.close()
            logger.error(f"Error installing selected patches: {e}")
            QMessageBox.critical(self, "Error", f"Failed to install patches:\n{e}")
    
    def start_plugin_installation(self, data, is_update=False):
        """Start plugin installation using the original flow"""
        # Start download worker
        self.worker = DownloadWorker(self.api, data, str(self.koreader_path), "plugin", is_update)
        
        # Progress dialog
        dialog_title = "Updating" if is_update else "Installation"
        self.progress_dialog = QProgressDialog(self)
        self.progress_dialog.setWindowTitle(dialog_title)
        self.progress_dialog.setLabelText("Preparing download...")
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setRange(0, 0)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        
        self.worker.progress.connect(self.progress_dialog.setLabelText)
        self.worker.finished.connect(self.install_finished)
        
        self.worker.start()
        self.progress_dialog.exec()
    
    def install_finished(self, success, message):
        """Installation completed"""
        self.progress_dialog.close()
        
        if success:
            QMessageBox.information(self, "Success", 
                f"{message}\n\nPlease restart KOReader to use the plugin.")
            # Reload installed plugins
            self.load_installed_plugins()
            # Refresh display
            self.filter_items()
        else:
            QMessageBox.critical(self, "Error", f"Installation failed:\n{message}")
    
    def show_details(self, data):
        """Show details dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Details: {data['name']}")
        dialog.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Header info
        header_text = f"""
        <h2 style='color: #a78bfa; margin: 10px 0;'>{data['name']}</h2>
        <p style='color: #FF006E; margin: 5px 0;'><b>From:</b> {data['owner']['login']}</p>
        <p style='color: #FF006E; margin: 5px 0;'><b>Stars:</b> {data.get('stargazers_count', 0)}</p>
        <p style='color: #FF006E; margin: 5px 0;'><b>Description:</b><br>{data.get('description', 'No description')}</p>
        <p style='color: #FF006E; margin: 5px 0;'><b>Language:</b> {data.get('language', 'Unknown')}</p>
        <p style='color: #FF006E; margin: 5px 0;'><b>Updated:</b> {data.get('updated_at', 'Unknown')[:10]}</p>
        """
        
        header_label = QTextEdit()
        header_label.setHtml(header_text)
        header_label.setReadOnly(True)
        layout.addWidget(header_label)
        
        # README content
        readme = self.api.get_repository_readme(
            data["owner"]["login"], 
            data["name"]
        )
        
        # Handle different README scenarios
        if readme.startswith("No README file found"):
            readme_html = f"""
            <div style='color: #4CAF50; padding: 20px; text-align: center;'>
                <h3>📄 No README Available</h3>
                <p>This repository doesn't have a README file.</p>
                <p>You can visit the repository on GitHub for more information:</p>
                <p><a href="{data['html_url']}" style='color: #60a5fa;'>View on GitHub →</a></p>
            </div>
            """
        elif readme.startswith("README not available"):
            readme_html = f"""
            <div style='color: #4CAF50; padding: 20px; text-align: center;'>
                <h3>⚠️ README Unavailable</h3>
                <p>{readme}</p>
                <p>You can visit the repository on GitHub for more information:</p>
                <p><a href="{data['html_url']}" style='color: #60a5fa;'>View on GitHub →</a></p>
            </div>
            """
        else:
            readme_html = convert_markdown_to_html(readme[:4000])
            if len(readme) > 2000:
                readme_html += f"<br><br><i style='color: #4CAF50;'>... (README truncated)</i> <a href='{data['html_url']}'>View on GitHub →</a>"
        
        # Sanitize HTML to remove unsafe content (scripts, iframes, etc.)
        readme_html = sanitize_readme_html(readme_html)
        
        # Detect support links for custom buttons
        support_links = detect_support_links(readme_html, data['html_url'])
        
        # Use QWebEngineView for proper HTML/GIF rendering if available, fallback to ReadmeTextEdit
        if WEBENGINE_AVAILABLE:
            readme_view = QWebEngineView()
            readme_view.setPage(ExternalLinkPage(readme_view))
            
            # Enable remote content access - CRITICAL for GitHub images
            settings = readme_view.settings()
            settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(settings.WebAttribute.AllowRunningInsecureContent, True)
            
            # Fix relative GitHub images by converting to absolute URLs
            readme_html = readme_html.replace(
                'src="',
                f'src="{data["html_url"]}/raw/HEAD/'
            )
            
            # Set base URL to GitHub repository with trailing slash for external resources
            base_url = QUrl(data["html_url"] + "/")
            readme_view.setHtml(readme_html, base_url)
            
            # Style the web view
            readme_view.setStyleSheet("""
                QWebEngineView {
                    background-color: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                }
            """)
            layout.addWidget(readme_view)
        else:
            # Fallback to original ReadmeTextEdit
            readme_label = ReadmeTextEdit()
            readme_label.setReadmeContent(readme_html)
            
            readme_label.setStyleSheet("""
                ReadmeTextEdit {
                    background-color: #ffffff;
                    color: #374151;
                    font-size: 13px;
                    line-height: 1.5;
                    padding: 15px;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                }
            """)
            
            # Make README scrollable
            scroll = QScrollArea()
            scroll.setWidget(readme_label)
            scroll.setWidgetResizable(True)
            layout.addWidget(scroll)
        
        # Add support buttons if any were detected
        if support_links:
            support_layout = QHBoxLayout()
            support_layout.setSpacing(10)
            
            for support in support_links:
                btn = QPushButton(support['label'])
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {support['color']};
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-weight: 600;
                        font-size: 13px;
                    }}
                    QPushButton:hover {{
                        background-color: {support['color']}dd;
                    }}
                """)
                btn.clicked.connect(lambda checked, url=support['url']: QDesktopServices.openUrl(QUrl(url)))
                support_layout.addWidget(btn)
            
            support_layout.addStretch()
            layout.addLayout(support_layout)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def prompt_for_github_token(self):
        """Prompt user for optional GitHub token"""
        tutorial_text = """
How to create a GitHub PAT (Personal Access Token):

1. Sign in at github.com and open Settings → Developer settings → Personal access tokens
   You can follow this link: https://github.com/settings/tokens/new

2. Click Generate new token

3. Name the token (e.g., KoStore), set an expiration, and grant at least the public_repo scope

4. Generate and copy the token immediately—GitHub will not show it again

5. The token is optional but recommended for higher API rate limits
        """
        
        dialog = QDialog(self)
        dialog.setWindowTitle("GitHub Token (Optional)")
        dialog.setGeometry(300, 300, 600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Title
        title = QLabel("GitHub Personal Access Token (Optional)")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #a78bfa; margin: 10px 0;")
        layout.addWidget(title)
        
        # Explanation
        explanation = QLabel("Providing a GitHub token is optional but recommended for better API rate limits.")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        
        # Tutorial
        tutorial = QTextEdit()
        tutorial.setPlainText(tutorial_text)
        tutorial.setReadOnly(True)
        tutorial.setMaximumHeight(250)
        layout.addWidget(tutorial)
        
        # Token input
        token_label = QLabel("Enter your GitHub token (leave empty to skip):")
        layout.addWidget(token_label)
        
        token_input = QLineEdit()
        token_input.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        token_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(token_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        skip_btn = QPushButton("Skip")
        skip_btn.clicked.connect(dialog.reject)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        
        button_layout.addWidget(skip_btn)
        button_layout.addWidget(ok_btn)
        layout.addLayout(button_layout)
        
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            token = token_input.text().strip()
            if token:
                logger.info("GitHub token provided by user")
                return token
            else:
                logger.info("Empty token provided, continuing without authentication")
                return None
        else:
            logger.info("User skipped GitHub token input")
            return None
