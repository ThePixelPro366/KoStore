"""
Patch Selection Dialog for KOReader Store
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTreeWidget, QTreeWidgetItem, QTextEdit, QSplitter,
    QFrame, QCheckBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextDocument

from ui.themes import LIGHT_THEME, PRIMARY, SUCCESS, ERROR
from api.github import GitHubAPI
from utils.markdown import convert_markdown_to_html

logger = logging.getLogger(__name__)


class PatchDownloadWorker(QThread):
    """Worker for downloading patch information"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, api: GitHubAPI, patch_data: dict):
        super().__init__()
        self.api = api
        self.patch_data = patch_data
    
    def run(self):
        try:
            self.progress.emit("Fetching patch information...")
            
            # Get repository contents
            owner = self.patch_data['owner']['login']
            repo = self.patch_data['name']
            
            # Get README
            readme = self.api.get_repository_readme(owner, repo)
            
            # Get repository contents (file tree)
            contents = self.api.get_repository_contents(owner, repo)
            
            self.finished.emit({
                'readme': readme,
                'contents': contents,
                'patch_data': self.patch_data
            })
            
        except Exception as e:
            logger.error(f"Error fetching patch info: {e}")
            self.error.emit(str(e))


class PatchSelectionDialog(QDialog):
    """Dialog for selecting patches to install"""
    
    def __init__(self, parent=None, patch_data=None, api=None):
        super().__init__(parent)
        self.patch_data = patch_data
        self.api = api
        self.selected_patches = []
        self.patch_files = []
        
        self.setWindowTitle("Select Patches to Install")
        self.setGeometry(200, 200, 1400, 900)
        self.setStyleSheet(LIGHT_THEME)
        
        self.init_ui()
        self.load_patch_info()
    
    def resizeEvent(self, event):
        """Handle dialog resize to reposition overlay"""
        super().resizeEvent(event)
        self.center_progress_overlay()
    
    def center_progress_overlay(self):
        """Center the progress overlay over the content area"""
        if hasattr(self, 'progress_overlay'):
            # Calculate center position
            dialog_size = self.size()
            
            # Set fixed size for better visibility
            self.progress_overlay.setFixedSize(350, 100)
            
            x = (dialog_size.width() - 350) // 2
            y = (dialog_size.height() - 100) // 2
            
            self.progress_overlay.move(x, y)
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setSizes([630, 770])  # 45% left, 55% right for 1400px width
        
        # Left side - README
        self.readme_widget = self.create_readme_widget()
        splitter.addWidget(self.readme_widget)
        
        # Right side - File explorer
        self.file_explorer = self.create_file_explorer()
        splitter.addWidget(self.file_explorer)
        
        # Make splitter expand to fill available space
        layout.addWidget(splitter, stretch=1)
        
        # Bottom buttons
        button_layout = self.create_button_layout()
        layout.addLayout(button_layout)
        
        # Progress overlay (positioned over the content)
        self.progress_overlay = QFrame(self)
        self.progress_overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.98);
                border-radius: 16px;
                border: 2px solid #3b82f6;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            }
        """)
        self.progress_overlay.setVisible(False)
        
        progress_layout = QVBoxLayout(self.progress_overlay)
        progress_layout.setContentsMargins(25, 25, 25, 25)
        
        self.progress_label = QLabel("Loading patch information...")
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #1f2937;
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 15px;
            }
        """)
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                text-align: center;
                font-weight: 500;
                color: #6b7280;
                background-color: #f9fafb;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
    
    def create_header(self):
        """Create header section"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 12px;
                padding: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        layout = QVBoxLayout(header)
        
        title = QLabel(f"📦 Patch Selection: {self.patch_data['name']}")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 5px;
        """)
        title.setWordWrap(True)
        layout.addWidget(title)
        
        subtitle = QLabel(f"From: {self.patch_data['owner']['login']}")
        subtitle.setStyleSheet("""
            font-size: 14px;
            color: #6b7280;
        """)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        
        return header
    
    def create_readme_widget(self):
        """Create README display widget"""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # README title
        readme_title = QLabel("📄 README")
        readme_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #374151;
            margin-bottom: 10px;
        """)
        layout.addWidget(readme_title)
        
        # README content
        self.readme_content = QTextEdit()
        self.readme_content.setReadOnly(True)
        self.readme_content.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                background-color: #f9fafb;
            }
        """)
        layout.addWidget(self.readme_content)
        
        return container
    
    def create_file_explorer(self):
        """Create file explorer widget"""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # File explorer title
        files_title = QLabel("📁 Patch Files")
        files_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #374151;
            margin-bottom: 10px;
        """)
        layout.addWidget(files_title)
        
        # Instructions
        instructions = QLabel("Select the patch files you want to install:")
        instructions.setStyleSheet("""
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 10px;
        """)
        layout.addWidget(instructions)
        
        # Tree widget for files
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["Select", "File Name", "Size", "Type"])
        self.file_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background-color: #f9fafb;
            }
            QTreeWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTreeWidget::item:selected {
                background-color: #e0e7ff;
            }
            QTreeWidget::header {
                background-color: #f3f4f6;
                padding: 8px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.file_tree)
        
        return container
    
    def create_button_layout(self):
        """Create bottom button layout"""
        layout = QHBoxLayout()
        layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #6b7280;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #4b5563;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        # Download button
        self.download_btn = QPushButton("⬇️ Download Selected")
        self.download_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
            QPushButton:disabled {{
                background-color: #d1d5db;
                color: #9ca3af;
            }}
        """)
        self.download_btn.clicked.connect(self.download_selected)
        self.download_btn.setEnabled(False)
        layout.addWidget(self.download_btn)
        
        return layout
    
    def load_patch_info(self):
        """Load patch information from GitHub"""
        self.progress_overlay.setVisible(True)
        self.progress_overlay.raise_()
        self.center_progress_overlay()
        
        self.worker = PatchDownloadWorker(self.api, self.patch_data)
        self.worker.progress.connect(self.progress_label.setText)
        self.worker.finished.connect(self.on_patch_info_loaded)
        self.worker.error.connect(self.on_patch_info_error)
        self.worker.start()
    
    def on_patch_info_loaded(self, data):
        """Handle patch info loading completion"""
        self.progress_overlay.setVisible(False)
        
        # Display README
        readme = data['readme']
        if readme.startswith("No README file found") or readme.startswith("README not available"):
            readme_html = f"""
            <div style='color: #6b7280; padding: 20px; text-align: center;'>
                <h3>📄 No README Available</h3>
                <p>This repository doesn't have a README file.</p>
                <p>You can visit the repository on GitHub for more information:</p>
                <p><a href="{self.patch_data['html_url']}" style='color: #3b82f6;'>View on GitHub →</a></p>
            </div>
            """
        else:
            # Convert markdown to HTML
            readme_html = convert_markdown_to_html(readme)
        
        self.readme_content.setHtml(readme_html)
        
        # Populate file tree
        self.populate_file_tree(data['contents'])
    
    def on_patch_info_error(self, error_msg):
        """Handle patch info loading error"""
        self.progress_overlay.setVisible(False)
        self.readme_content.setHtml(f"""
            <div style='color: #ef4444; padding: 20px; text-align: center;'>
                <h3>❌ Error Loading Information</h3>
                <p>Failed to load patch information: {error_msg}</p>
            </div>
        """)
    
    def populate_file_tree(self, contents):
        """Populate the file tree with repository contents"""
        self.patch_files.clear()
        self.file_tree.clear()
        
        # Filter for patch files (common extensions)
        patch_extensions = ['.patch', '.diff', '.lua', '.sh']
        
        def add_items(items, parent=None):
            for item in items:
                if item['type'] == 'file':
                    name = item['name']
                    # Check if it's likely a patch file
                    if any(name.lower().endswith(ext) for ext in patch_extensions) or 'patch' in name.lower():
                        tree_item = QTreeWidgetItem(parent) if parent else QTreeWidgetItem(self.file_tree)
                        
                        # Checkbox for selection
                        checkbox = QCheckBox()
                        checkbox.stateChanged.connect(self.on_selection_changed)
                        self.file_tree.setItemWidget(tree_item, 0, checkbox)
                        
                        # File info
                        tree_item.setText(1, name)
                        tree_item.setText(2, self.format_file_size(item.get('size', 0)))
                        tree_item.setText(3, item['type'])
                        
                        # Store file data
                        tree_item.setData(0, Qt.ItemDataRole.UserRole, item)
                        self.patch_files.append(item)
                
                elif item['type'] == 'dir':
                    # Add directory
                    tree_item = QTreeWidgetItem(parent) if parent else QTreeWidgetItem(self.file_tree)
                    tree_item.setText(1, f"📁 {item['name']}")
                    tree_item.setText(2, "")
                    tree_item.setText(3, "directory")
                    
                    # Recursively add contents
                    if 'contents' in item:
                        add_items(item['contents'], tree_item)
        
        add_items(contents)
        
        # Expand all directories
        self.file_tree.expandAll()
        
        # Enable download button if we have patch files
        self.download_btn.setEnabled(len(self.patch_files) > 0)
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def on_selection_changed(self):
        """Handle checkbox selection changes"""
        # Update selected patches list
        self.selected_patches.clear()
        
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            self.check_item_selection(item)
        
        # Update button state
        self.download_btn.setEnabled(len(self.selected_patches) > 0)
    
    def check_item_selection(self, item):
        """Recursively check item selection"""
        checkbox = self.file_tree.itemWidget(item, 0)
        if checkbox and checkbox.isChecked():
            file_data = item.data(0, Qt.ItemDataRole.UserRole)
            if file_data:
                self.selected_patches.append(file_data)
        
        # Check children
        for i in range(item.childCount()):
            self.check_item_selection(item.child(i))
    
    def download_selected(self):
        """Download selected patches"""
        if not self.selected_patches:
            QMessageBox.warning(self, "Warning", "No patches selected for download.")
            return
        
        # Store selected patches for parent to access
        self.selected_patches = self.selected_patches
        self.accept()
