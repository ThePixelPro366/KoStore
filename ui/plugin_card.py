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
    uninstall_clicked = pyqtSignal(dict)
    details_clicked = pyqtSignal(dict)
    favorite_clicked = pyqtSignal(dict, bool)
    
    def __init__(self, data, installed=False, has_update=False, version="", is_favorite=False, enable_shadow=True):
        super().__init__()

        if enable_shadow:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(24)
            shadow.setOffset(0, 6)
            shadow.setColor(QColor(0, 0, 0, 40))
            self.setGraphicsEffect(shadow)

        self.data = data
        self.installed = installed
        self.has_update = has_update
        self.version = version
        self.is_favorite = is_favorite
        self.init_ui()
    
    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Modern card design with dynamic height
        self.setFixedWidth(280)
        self.setMinimumHeight(200)
        
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
        
        self.setStyleSheet(f"""
PluginCard {{
    background-color: #ffffff;
    border: 2px solid {border_color};
    border-radius: 18px;
}}

PluginCard:hover {{
    background-color: #f8fafc;
}}
""")

        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # Status badges
        status_layout = QHBoxLayout()
        status_layout.setSpacing(4)
        
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
        desc_label.setMaximumHeight(36)
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
        
        layout.addStretch()
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(0)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Favorite button
        favorite_btn = QPushButton("🤍" if not self.is_favorite else "❤️")
        favorite_btn.setFixedSize(52, 40)
        favorite_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #1a1a1a;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 22px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        favorite_btn.clicked.connect(lambda: self.favorite_clicked.emit(self.data, not self.is_favorite))
        button_layout.addWidget(favorite_btn)
        
        # Details button
        details_btn = QPushButton("📋")
        details_btn.setFixedSize(52, 40)
        details_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #1a1a1a;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 20px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        details_btn.clicked.connect(lambda: self.details_clicked.emit(self.data))
        button_layout.addWidget(details_btn)
        
        button_layout.addStretch()
        
        # Install/Update/Uninstall button
        if self.installed:
            if self.has_update:
                install_btn = QPushButton("⬆️ Update")
                btn_color = "#f59e0b"
                hover_color = "#d97706"
            else:
                install_btn = QPushButton("🗑️ Uninstall")
                btn_color = "#ef4444"
                hover_color = "#dc2626"
        else:
            install_btn = QPushButton("⬇️ Install")
            btn_color = "#3b82f6"
            hover_color = "#2563eb"
        
        install_btn.setEnabled(True)  # Always enable the button
        install_btn.setStyleSheet(f"""
QPushButton {{
    background-color: {btn_color};
    color: white;
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 13px;
    font-weight: 600;
    min-width: 110px;
}}

QPushButton:hover {{
    background-color: {hover_color};
}}

QPushButton:disabled {{
    background-color: #e5e7eb;
    color: #9ca3af;
}}
""")

        # Connect appropriate signal based on button type
        if self.installed and not self.has_update:
            install_btn.clicked.connect(lambda: self.uninstall_clicked.emit(self.data))
        else:
            install_btn.clicked.connect(lambda: self.install_clicked.emit(self.data, self.has_update))
        button_layout.addWidget(install_btn)
        
        layout.addLayout(button_layout)
