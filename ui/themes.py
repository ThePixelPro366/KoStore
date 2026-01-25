"""
UI Design Tokens and Theme Definitions for KOReader Store
"""

# =========================
# UI DESIGN TOKENS
# =========================
PRIMARY = "#3b82f6"
PRIMARY_HOVER = "#2563eb"

SUCCESS = "#10b981"
WARNING = "#f59e0b"
ERROR = "#ef4444"

BG_MAIN = "#ffffff"
BG_CARD = "#f8f9fa"
BG_SOFT = "#f1f5f9"

TEXT_MAIN = "#111827"
TEXT_MUTED = "#6b7280"

BORDER = "#e5e7eb"

# =========================
# THEME DEFINITIONS
# =========================
LIGHT_THEME = """
QMainWindow {
    background-color: #ffffff;
}

QFrame {
    background-color: #ffffff;
}

QLabel {
    color: #111827;
}

QLineEdit {
    background-color: #f8f9fa;
    border-radius: 12px;
    padding: 10px;
    color: #111827;
    border: 1px solid #e5e7eb;
}

QLineEdit::placeholder {
    color: #6b7280;
}

QTabBar::tab {
    background-color: #e5e7eb;
    color: #374151;
    border-radius: 14px;
    padding: 10px 26px;
    font-size: 13px;
}

QTabBar::tab:selected {
    background-color: #3b82f6;
    color: white;
    font-weight: 600;
}

QTabBar::tab:hover {
    background-color: #dbeafe;
}

QComboBox {
    background-color: #f1f5f9;
    border-radius: 12px;
    padding: 8px 14px;
    color: #111827;
    border: 1px solid #e5e7eb;
}

QComboBox QAbstractItemView {
    background-color: white;
    color: #111827;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    selection-background-color: #3b82f6;
}

QScrollArea {
    background-color: #ffffff;
    border: none;
}

QWidget {
    background-color: #ffffff;
    color: #111827;
}

QPushButton {
    background-color: #f1f5f9;
    color: #374151;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 8px 14px;
    font-size: 12px;
}

/* Special buttons - protected from generic styling */
QPushButton#checkUpdatesBtn,
QPushButton#refreshBtn {
    background: none;
    border: none;
}

QPushButton#checkUpdatesBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #22c55e, stop:1 #16a34a);
    color: white;
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton#refreshBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #2563eb);
    color: white;
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton#checkUpdatesBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #16a34a, stop:1 #15803d);
}

QPushButton#refreshBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
}

QPushButton:hover {
    background-color: #e5e7eb;
}

QPushButton:pressed {
    background-color: #d1d5db;
}

QProgressBar {
    border: 2px solid #334155;
    border-radius: 8px;
    text-align: center;
    color: #111827;
    background-color: #f1f5f9;
}

QProgressBar::chunk {
    background-color: #8b5cf6;
    border-radius: 6px;
}

QMessageBox {
    background-color: #ffffff;
    color: #111827;
}

QMessageBox QLabel {
    color: #111827;
}

QMessageBox QPushButton {
    background-color: #3b82f6;
    color: white;
    border: none;
    padding: 8px 16px;
}

QMessageBox QPushButton:hover {
    background-color: #2563eb;
}
"""
