"""
Loading overlay widget for KOReader Store
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class LoadingOverlay(QWidget):
    """Loading screen overlay widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
    
    def init_ui(self):
        # Set up the overlay to cover the entire parent
        if self.parent:
            self.setGeometry(self.parent.rect())
        
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 23, 42, 0.95);
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        # Title
        title_label = QLabel("KOReader Store")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        title_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Loading plugins and patches...")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 14px;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(subtitle_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #334155;
                border-radius: 8px;
                text-align: center;
                color: #e5e7eb;
                background-color: #1e293b;
                height: 8px;
            }
            
            QProgressBar::chunk {
                background-color: #8b5cf6;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #cbd5e1;
                font-size: 12px;
                margin-top: 10px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Hide initially
        self.hide()
    
    def show_loading(self, parent=None):
        """Show the loading overlay"""
        if parent:
            self.setParent(parent)
            # Cover the entire parent widget
            self.setGeometry(0, 0, parent.width(), parent.height())
        
        self.show()
        self.raise_()
        self.activateWindow()
    
    def hide_loading(self):
        """Hide the loading overlay"""
        self.hide()
    
    def update_status(self, message):
        """Update the status message"""
        self.status_label.setText(message)
    
    def set_progress(self, value, maximum=100):
        """Set progress bar to determinate mode and update value"""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)
    
    def set_indeterminate(self):
        """Set progress bar to indeterminate mode"""
        self.progress_bar.setRange(0, 0)
    
    def resizeEvent(self, event):
        """Handle resize events to maintain overlay coverage"""
        super().resizeEvent(event)
        if self.parent:
            self.setGeometry(self.parent.rect())
