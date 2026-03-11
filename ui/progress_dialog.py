"""
Progress dialog for file transfers with cancel support.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal


class TransferProgressDialog(QDialog):
    """Dialog showing progress for file transfers."""
    
    cancelled = pyqtSignal()
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setModal(True)
        self._build_ui()
        self._cancelled = False
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Starting transfer...")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Details label
        self.details_label = QLabel("")
        self.details_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.details_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def update_progress(self, transferred: int, total: int):
        """Update progress bar and details."""
        if total > 0:
            percent = int((transferred / total) * 100)
            self.progress_bar.setValue(percent)
            
            # Format sizes
            transferred_mb = transferred / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            
            self.details_label.setText(
                f"{transferred_mb:.1f} MB / {total_mb:.1f} MB ({percent}%)"
            )
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.details_label.setText(f"{transferred} bytes transferred")
    
    def set_status(self, status: str):
        """Update status label."""
        self.status_label.setText(status)
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self._cancelled = True
        self.cancelled.emit()
        self.cancel_btn.setEnabled(False)
        self.set_status("Cancelling...")
    
    def is_cancelled(self) -> bool:
        """Check if transfer was cancelled."""
        return self._cancelled
    
    def set_complete(self, message: str = "Transfer complete!"):
        """Mark transfer as complete."""
        self.progress_bar.setValue(100)
        self.set_status(message)
        self.cancel_btn.setText("Close")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)


class ProgressCallback:
    """Callback handler for file transfer progress."""
    
    def __init__(self, progress_dialog: TransferProgressDialog):
        self.dialog = progress_dialog
    
    def __call__(self, transferred: int, total: int):
        """Handle progress update."""
        # Check if cancelled
        if self.dialog.is_cancelled():
            raise InterruptedError("Transfer cancelled by user")
        
        # Update UI (must be thread-safe)
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self.dialog,
            "update_progress",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, transferred),
            Q_ARG(int, total)
        )
