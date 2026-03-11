"""
Loading overlay widget for KOReader Store
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QTextEdit, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont


class LoadingOverlay(QWidget):
    """Loading screen overlay widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
    
    def init_ui(self):
        # Set fixed size for modal appearance
        self.setFixedSize(400, 350)
        
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.98);
                border-radius: 12px;
                border: 2px solid #e2e8f0;
            }
        """)
        
        # Main container with padding
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(15)
        
        # Center the container in this widget
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(container)
        
        # Title
        title_label = QLabel("KOReader Store")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #1f2937;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        container_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Loading plugins and patches...")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 14px;
            }
        """)
        container_layout.addWidget(subtitle_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                text-align: center;
                color: #374151;
                background-color: #f9fafb;
                height: 8px;
            }
            
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 6px;
            }
        """)
        container_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #4b5563;
                font-size: 12px;
            }
        """)
        container_layout.addWidget(self.status_label)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(120)
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #f9fafb;
                color: #374151;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        container_layout.addWidget(self.log_display)
        
        # Hide initially
        self.hide()
    
    def show_loading(self, parent=None):
        """Show the loading overlay"""
        if parent:
            self.setParent(parent)
            # Center the overlay in the parent widget
            parent_rect = parent.rect()
            overlay_rect = self.rect()
            x = (parent_rect.width() - overlay_rect.width()) // 2
            y = (parent_rect.height() - overlay_rect.height()) // 2
            self.move(x, y)
        
        self.show()
        self.raise_()
    
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
    
        
    # Method to add logs
    @pyqtSlot(str)
    def append_log(self, message):
        """Append a log message to the display"""
        self.log_display.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        QApplication.processEvents()
        
        # Also update the status label with the last line
        self.status_label.setText(message.split('\n')[-1])
