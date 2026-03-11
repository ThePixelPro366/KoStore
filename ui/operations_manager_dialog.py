"""
Dialog for managing parallel plugin operations with progress and cancellation.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QProgressBar, QMessageBox,
    QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from services.plugin_operations import OperationStatus, PluginOperationManager


class OperationsManagerDialog(QDialog):
    """Dialog for managing parallel plugin operations."""
    
    def __init__(self, operations_manager: PluginOperationManager, parent=None):
        super().__init__(parent)
        self.operations_manager = operations_manager
        self.setWindowTitle("Plugin Operations")
        self.setMinimumSize(800, 600)
        self._build_ui()
        self._connect_signals()
        self._setup_timer()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Status summary
        self.status_group = QGroupBox("Status Summary")
        status_layout = QHBoxLayout(self.status_group)
        
        self.pending_label = QLabel("Pending: 0")
        self.running_label = QLabel("Running: 0")
        self.completed_label = QLabel("Completed: 0")
        self.failed_label = QLabel("Failed: 0")
        
        status_layout.addWidget(self.pending_label)
        status_layout.addWidget(self.running_label)
        status_layout.addWidget(self.completed_label)
        status_layout.addWidget(self.failed_label)
        status_layout.addStretch()
        
        layout.addWidget(self.status_group)
        
        # Operations tree
        self.operations_tree = QTreeWidget()
        self.operations_tree.setHeaderLabels([
            "Plugin", "Operation", "Status", "Progress", "Time", "Message"
        ])
        self.operations_tree.setColumnWidth(0, 150)  # Plugin
        self.operations_tree.setColumnWidth(1, 100)  # Operation
        self.operations_tree.setColumnWidth(2, 100)  # Status
        self.operations_tree.setColumnWidth(3, 150)  # Progress
        self.operations_tree.setColumnWidth(4, 80)   # Time
        self.operations_tree.setColumnWidth(5, 200)  # Message
        
        layout.addWidget(self.operations_tree)
        
        # Details panel
        self.details_group = QGroupBox("Operation Details")
        details_layout = QVBoxLayout(self.details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(100)
        self.details_text.setFont(QFont("Consolas", 9))
        details_layout.addWidget(self.details_text)
        
        layout.addWidget(self.details_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_selected_btn = QPushButton("Cancel Selected")
        self.cancel_selected_btn.clicked.connect(self._on_cancel_selected)
        self.cancel_selected_btn.setEnabled(False)
        
        self.cancel_all_btn = QPushButton("Cancel All")
        self.cancel_all_btn.clicked.connect(self._on_cancel_all)
        
        self.clear_completed_btn = QPushButton("Clear Completed")
        self.clear_completed_btn.clicked.connect(self._on_clear_completed)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_operations)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_selected_btn)
        button_layout.addWidget(self.cancel_all_btn)
        button_layout.addWidget(self.clear_completed_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect signals from operations manager."""
        self.operations_manager.operation_started.connect(self._on_operation_started)
        self.operations_manager.operation_completed.connect(self._on_operation_completed)
        self.operations_manager.operation_failed.connect(self._on_operation_failed)
        self.operations_manager.operation_cancelled.connect(self._on_operation_cancelled)
        
        # Tree selection
        self.operations_tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.operations_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
    
    def _setup_timer(self):
        """Setup update timer."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._refresh_operations)
        self.update_timer.start(1000)  # Update every second
    
    def _refresh_operations(self):
        """Refresh the operations list."""
        # Clear tree
        self.operations_tree.clear()
        
        # Get all operations
        operations = self.operations_manager.get_all_operations()
        
        # Sort by creation time (newest first)
        operations.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Count by status
        pending_count = sum(1 for op in operations if op["status"] == "pending")
        running_count = sum(1 for op in operations if op["status"] == "running")
        completed_count = sum(1 for op in operations if op["status"] == "completed")
        failed_count = sum(1 for op in operations if op["status"] == "failed")
        
        # Update status labels
        self.pending_label.setText(f"Pending: {pending_count}")
        self.running_label.setText(f"Running: {running_count}")
        self.completed_label.setText(f"Completed: {completed_count}")
        self.failed_label.setText(f"Failed: {failed_count}")
        
        # Add operations to tree
        for op in operations:
            item = QTreeWidgetItem()
            item.setText(0, op["plugin_name"])
            item.setText(1, op["operation_type"].title())
            item.setText(2, op["status"].title())
            
            # Progress
            if op["status"] == "running":
                item.setText(3, "Running...")
            elif op["status"] == "completed":
                item.setText(3, "100%")
            elif op["status"] == "failed":
                item.setText(3, "Failed")
            elif op["status"] == "cancelled":
                item.setText(3, "Cancelled")
            else:
                item.setText(3, "Queued")
            
            # Time
            if op["started_at"] and op["completed_at"]:
                duration = op["completed_at"] - op["started_at"]
                item.setText(4, f"{duration:.1f}s")
            elif op["started_at"]:
                duration = op.get("completed_at", time.time()) - op["started_at"]
                item.setText(4, f"{duration:.1f}s")
            else:
                item.setText(4, "-")
            
            # Message
            if op["status"] == "failed":
                item.setText(5, op["error_message"][:50] + "..." if len(op["error_message"]) > 50 else op["error_message"])
            elif op["status"] == "completed" and op["result"]:
                message = op["result"].get("message", "")
                item.setText(5, message[:50] + "..." if len(message) > 50 else message)
            else:
                item.setText(5, "")
            
            # Store operation ID
            item.setData(0, Qt.ItemDataRole.UserRole, op["operation_id"])
            
            # Color code by status
            if op["status"] == "completed":
                item.setBackground(2, Qt.GlobalColor.green)
            elif op["status"] == "failed":
                item.setBackground(2, Qt.GlobalColor.red)
            elif op["status"] == "running":
                item.setBackground(2, Qt.GlobalColor.yellow)
            elif op["status"] == "cancelled":
                item.setBackground(2, Qt.GlobalColor.gray)
            
            self.operations_tree.addTopLevelItem(item)
    
    def _on_operation_started(self, operation_id: str):
        """Handle operation started."""
        self._refresh_operations()
    
    def _on_operation_completed(self, operation_id: str, result: dict):
        """Handle operation completed."""
        self._refresh_operations()
    
    def _on_operation_failed(self, operation_id: str, error_message: str):
        """Handle operation failed."""
        self._refresh_operations()
    
    def _on_operation_cancelled(self, operation_id: str):
        """Handle operation cancelled."""
        self._refresh_operations()
    
    def _on_selection_changed(self):
        """Handle tree selection change."""
        selected_items = self.operations_tree.selectedItems()
        has_selection = bool(selected_items)
        
        self.cancel_selected_btn.setEnabled(has_selection)
        
        if selected_items:
            item = selected_items[0]
            operation_id = item.data(0, Qt.ItemDataRole.UserRole)
            if operation_id:
                status = self.operations_manager.get_operation_status(operation_id)
                if status:
                    # Show details
                    details = f"Operation ID: {status['operation_id']}\n"
                    details += f"Plugin: {status['plugin_name']}\n"
                    details += f"Type: {status['operation_type']}\n"
                    details += f"Status: {status['status']}\n"
                    
                    if status["started_at"]:
                        from datetime import datetime
                        started = datetime.fromtimestamp(status["started_at"])
                        details += f"Started: {started.strftime('%H:%M:%S')}\n"
                    
                    if status["completed_at"]:
                        from datetime import datetime
                        completed = datetime.fromtimestamp(status["completed_at"])
                        details += f"Completed: {completed.strftime('%H:%M:%S')}\n"
                    
                    if status["error_message"]:
                        details += f"Error: {status['error_message']}"
                    
                    self.details_text.setPlainText(details)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on item."""
        operation_id = item.data(0, Qt.ItemDataRole.UserRole)
        if operation_id:
            status = self.operations_manager.get_operation_status(operation_id)
            if status and status["status"] in ["failed", "completed"]:
                # Show full message in a dialog
                message = status.get("error_message") or status.get("result", {}).get("message", "")
                if message:
                    QMessageBox.information(self, "Operation Details", message)
    
    def _on_cancel_selected(self):
        """Handle cancel selected button."""
        selected_items = self.operations_tree.selectedItems()
        if not selected_items:
            return
        
        operation_id = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        if operation_id:
            status = self.operations_manager.get_operation_status(operation_id)
            if status and status["status"] in ["pending", "running"]:
                reply = QMessageBox.question(
                    self,
                    "Cancel Operation",
                    f"Cancel operation '{status['plugin_name']}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.operations_manager.cancel_operation(operation_id)
    
    def _on_cancel_all(self):
        """Handle cancel all button."""
        pending_ops = self.operations_manager.get_pending_operations()
        running_ops = self.operations_manager.get_running_operations()
        
        if not pending_ops and not running_ops:
            QMessageBox.information(self, "No Operations", "No pending or running operations to cancel.")
            return
        
        reply = QMessageBox.question(
            self,
            "Cancel All Operations",
            f"Cancel all {len(pending_ops) + len(running_ops)} pending/running operations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            cancelled = self.operations_manager.cancel_all_operations()
            QMessageBox.information(self, "Operations Cancelled", f"Cancelled {cancelled} operations.")
    
    def _on_clear_completed(self):
        """Handle clear completed button."""
        # This would need to be implemented in the operations manager
        # For now, just refresh
        self._refresh_operations()
    
    def closeEvent(self, event):
        """Handle dialog close."""
        self.update_timer.stop()
        super().closeEvent(event)
