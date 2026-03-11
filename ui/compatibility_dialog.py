"""
Dialog for displaying plugin compatibility check results.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QTreeWidget, QTreeWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextDocument

from services.compatibility_checker import CompatibilityChecker, CompatibilityIssue


class CompatibilityCheckDialog(QDialog):
    """Dialog for showing compatibility check results."""
    
    def __init__(self, compatibility_checker: CompatibilityChecker, parent=None):
        super().__init__(parent)
        self.checker = compatibility_checker
        self.setWindowTitle("Plugin Compatibility Check")
        self.setMinimumSize(700, 500)
        self._build_ui()
        self._load_device_info()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Device info group
        self.device_info_group = QGroupBox("Device Information")
        device_layout = QVBoxLayout(self.device_info_group)
        
        self.device_info_text = QTextEdit()
        self.device_info_text.setReadOnly(True)
        self.device_info_text.setMaximumHeight(120)
        self.device_info_text.setFont(QFont("Consolas", 9))
        device_layout.addWidget(self.device_info_text)
        
        layout.addWidget(self.device_info_group)
        
        # Compatibility results
        self.results_group = QGroupBox("Compatibility Check Results")
        results_layout = QVBoxLayout(self.results_group)
        
        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Severity", "Issue", "Suggestion"])
        self.results_tree.setColumnWidth(0, 80)
        self.results_tree.setColumnWidth(1, 300)
        self.results_tree.setColumnWidth(2, 300)
        
        results_layout.addWidget(self.results_tree)
        
        # Summary label
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        results_layout.addWidget(self.summary_label)
        
        layout.addWidget(self.results_group)
        
        # Check buttons
        check_layout = QHBoxLayout()
        
        self.check_plugin_btn = QPushButton("Check Plugin from Metadata")
        self.check_plugin_btn.clicked.connect(self._on_check_plugin_metadata)
        
        self.refresh_device_btn = QPushButton("Refresh Device Info")
        self.refresh_device_btn.clicked.connect(self._on_refresh_device)
        
        check_layout.addWidget(self.check_plugin_btn)
        check_layout.addWidget(self.refresh_device_btn)
        check_layout.addStretch()
        
        layout.addLayout(check_layout)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)
    
    def _load_device_info(self):
        """Load and display device information."""
        device_info = self.checker.get_device_info()
        
        info_text = f"Platform: {device_info.platform}\n"
        info_text += f"KOReader Version: {device_info.koreader_version}\n"
        info_text += f"Screen Size: {device_info.screen_size[0]}x{device_info.screen_size[1]}\n"
        info_text += f"Memory: {device_info.memory_mb} MB\n"
        info_text += f"Storage: {device_info.storage_space_mb} MB\n"
        info_text += f"Touchscreen: {'Yes' if device_info.has_touchscreen else 'No'}\n"
        info_text += f"Keyboard: {'Yes' if device_info.has_keyboard else 'No'}\n"
        info_text += f"Physical Buttons: {'Yes' if device_info.has_physical_buttons else 'No'}\n"
        
        if device_info.supported_features:
            info_text += f"Features: {', '.join(sorted(device_info.supported_features))}"
        
        self.device_info_text.setPlainText(info_text)
    
    def check_plugin(self, plugin_metadata: str, installed_plugins: list = None) -> bool:
        """Check plugin compatibility and display results."""
        if installed_plugins is None:
            installed_plugins = []
        
        try:
            is_compatible, issues = self.checker.check_plugin_compatibility(
                plugin_metadata, installed_plugins
            )
            
            # Clear previous results
            self.results_tree.clear()
            
            # Add issues to tree
            for issue in issues:
                item = QTreeWidgetItem()
                item.setText(0, issue.severity.upper())
                item.setText(1, issue.message)
                item.setText(2, issue.suggestion or "")
                
                # Color code by severity
                if issue.severity == "error":
                    item.setBackground(0, Qt.GlobalColor.red)
                elif issue.severity == "warning":
                    item.setBackground(0, Qt.GlobalColor.yellow)
                elif issue.severity == "info":
                    item.setBackground(0, Qt.GlobalColor.blue)
                
                self.results_tree.addTopLevelItem(item)
            
            # Update summary
            error_count = sum(1 for issue in issues if issue.severity == "error")
            warning_count = sum(1 for issue in issues if issue.severity == "warning")
            info_count = sum(1 for issue in issues if issue.severity == "info")
            
            if is_compatible:
                if warning_count > 0 or info_count > 0:
                    self.summary_label.setText(
                        f"✓ Plugin is compatible with {warning_count} warning(s) and {info_count} info note(s)"
                    )
                    self.summary_label.setStyleSheet("color: orange;")
                else:
                    self.summary_label.setText("✓ Plugin is fully compatible with your device")
                    self.summary_label.setStyleSheet("color: green;")
            else:
                self.summary_label.setText(
                    f"✗ Plugin is not compatible ({error_count} error(s), {warning_count} warning(s))"
                )
                self.summary_label.setStyleSheet("color: red;")
            
            return is_compatible
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to check compatibility: {e}")
            return False
    
    def _on_check_plugin_metadata(self):
        """Handle check plugin metadata button."""
        from PyQt6.QtWidgets import QInputDialog
        
        metadata, ok = QInputDialog.getMultiLineText(
            self,
            "Plugin Metadata",
            "Paste the contents of _meta.lua file:"
        )
        
        if ok and metadata.strip():
            # Get installed plugins (this would need to be passed in or retrieved)
            installed_plugins = []  # This should be provided by the caller
            self.check_plugin(metadata, installed_plugins)
    
    def _on_refresh_device(self):
        """Handle refresh device info button."""
        # Re-detect device info
        self.checker._detect_device_info()
        self._load_device_info()
        
        QMessageBox.information(self, "Device Info Refreshed", "Device information has been refreshed.")


class QuickCompatibilityCheck:
    """Utility for quick compatibility checks."""
    
    @staticmethod
    def check_and_show(
        parent, 
        compatibility_checker: CompatibilityChecker, 
        plugin_metadata: str, 
        installed_plugins: list = None
    ) -> bool:
        """Check compatibility and show results if there are issues."""
        if installed_plugins is None:
            installed_plugins = []
        
        try:
            is_compatible, issues = compatibility_checker.check_plugin_compatibility(
                plugin_metadata, installed_plugins
            )
            
            # If fully compatible, just return True
            if is_compatible and not any(issue.severity in ["error", "warning"] for issue in issues):
                return True
            
            # Show detailed results
            dialog = CompatibilityCheckDialog(compatibility_checker, parent)
            dialog.check_plugin(plugin_metadata, installed_plugins)
            dialog.exec()
            
            return is_compatible
            
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to check compatibility: {e}")
            return False
