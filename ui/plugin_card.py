"""
Plugin Card Widget for individual plugin display
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor


class PluginCard(QFrame):
    """Widget for individual plugin card"""
    install_clicked = pyqtSignal(dict, bool)
    details_clicked = pyqtSignal(dict)
    
    def __init__(self, data, installed=False, has_update=False, version=""):
        super().__init__()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        self.data = data
        self.installed = installed
        self.has_update = has_update
        self.version = version
        self.init_ui()
    
    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Modern card design with gradient background
        self.setFixedSize(280, 200)
        
        # Dynamic styling based on status
        if self.has_update:
            border_color = "#f59e0b"
            accent_color = "#f59e0b"
        elif self.installed:
            border_color = "#10b981"
            accent_color = "#10b981"
        else:
            border_color = "#3b82f6"
            accent_color = "#3b82f6"
        
        self.setStyleSheet("""
QFrame {
    background-color: #ffffff;
    border-radius: 18px;
}

QFrame:hover {
    background-color: #f8fafc;
}
""")

        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Status badges
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)
        
        if self.installed:
            installed_badge = QLabel("✅ INSTALLED")
            installed_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {accent_color};
                    color: white;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 9px;
                    font-weight: bold;
                }}
            """)
            status_layout.addWidget(installed_badge)
        
        if self.has_update:
            update_badge = QLabel("⬆️ UPDATE")
            update_badge.setStyleSheet("""
                QLabel {
                    background-color: #f59e0b;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 9px;
                    font-weight: bold;
                }
            """)
            status_layout.addWidget(update_badge)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # App name
        name_label = QLabel(self.data.get("name", "Unknown"))
        name_label.setStyleSheet("""
font-size: 15px;
font-weight: 600;
color: #111827;
""")

        name_label.setWordWrap(True)
        name_label.setMinimumHeight(20)
        name_label.setMaximumHeight(40)
        layout.addWidget(name_label)
        
        # Developer name
        owner_label = QLabel(f"by {self.data['owner']['login']}")
        owner_label.setStyleSheet("""
font-size: 11px;
color: #6b7280;
""")
        layout.addWidget(owner_label)
        
        # Description (truncated)
        desc = self.data.get("description") or "No description"
        desc_label = QLabel(desc[:60] + "..." if len(desc) > 60 else desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
font-size: 12px;
color: #4b5563;
line-height: 1.4;
""")

        desc_label.setMinimumHeight(30)
        desc_label.setMaximumHeight(50)
        layout.addWidget(desc_label)
        
        # Rating and stats
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        # Stars rating
        stars_text = f"⭐ {self.data.get('stargazers_count', 0)}"
        stars_label = QLabel(stars_text)
        stars_label.setStyleSheet("font-size: 10px; color: #9ca3af;")
        stats_layout.addWidget(stars_label)
        
        # Updated date
        updated = self.data.get("updated_at", "")[:10]
        date_label = QLabel(f"📅 {updated}")
        date_label.setStyleSheet("font-size: 10px; color: #9ca3af;")
        stats_layout.addWidget(date_label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Details button
        details_btn = QPushButton("📋")
        details_btn.setFixedSize(32, 32)
        details_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #1a1a1a;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        details_btn.clicked.connect(lambda: self.details_clicked.emit(self.data))
        button_layout.addWidget(details_btn)
        
        # Install/Update button
        if self.installed:
            if self.has_update:
                install_btn = QPushButton("⬆️ Update")
                btn_color = "#f59e0b"
                hover_color = "#d97706"
            else:
                install_btn = QPushButton("✅ Installed")
                btn_color = "#10b981"
                hover_color = "#059669"
        else:
            install_btn = QPushButton("⬇️ Install")
            btn_color = "#3b82f6"
            hover_color = "#2563eb"
        
        install_btn.setEnabled(not self.installed or self.has_update)
        install_btn.setStyleSheet(f"""
QPushButton {{
    background-color: {btn_color};
    color: white;
    border-radius: 12px;
    padding: 10px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {hover_color};
}}

QPushButton:disabled {{
    background-color: #e5e7eb;
    color: #9ca3af;
}}
""")

        install_btn.clicked.connect(lambda: self.install_clicked.emit(self.data, self.has_update))
        button_layout.addWidget(install_btn)
        
        layout.addLayout(button_layout)
