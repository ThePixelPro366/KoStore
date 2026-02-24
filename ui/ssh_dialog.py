"""
SSH connection dialog for wireless KOReader device connections
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QMessageBox,
    QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from services.ssh_connection import SSHConnectionService


class SSHConnectWorker(QThread):
    """Background worker so the UI doesn't freeze during connection."""
    success = pyqtSignal(str)   # emits the koreader path
    error = pyqtSignal(str)

    def __init__(self, service, host, port, user, password, remote_path):
        super().__init__()
        self.service = service
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.remote_path = remote_path

    def run(self):
        try:
            self.service.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                remote_path=self.remote_path,
                password=self.password or None
            )
            koreader_path = self.service.get_koreader_path()
            if koreader_path:
                self.success.emit(koreader_path)
            else:
                self.error.emit(
                    "Connected, but couldn't find the KOReader folder.\n"
                    "Try setting the remote path manually."
                )
        except RuntimeError as e:
            self.error.emit(str(e))


class SSHConnectionDialog(QDialog):
    # Emitted when connection succeeds; carries the local mount path
    connected = pyqtSignal(str)

    def __init__(self, ssh_service: SSHConnectionService, parent=None):
        super().__init__(parent)
        self.ssh_service = ssh_service
        self.worker = None
        self.setWindowTitle("Connect via WiFi (SFTP)")
        self.setMinimumWidth(380)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Info label
        info = QLabel(
            "Connect wirelessly to your KOReader device.\n"
            "Make sure the SSH plugin is enabled in KOReader\n"
            "and your device is on the same WiFi network."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Connection fields
        group = QGroupBox("Connection Settings")
        form = QFormLayout(group)

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("e.g. 192.168.1.42")
        form.addRow("Device IP:", self.host_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(2222)  # KOReader SSH plugin default
        form.addRow("SSH Port:", self.port_input)

        self.user_input = QLineEdit()
        self.user_input.setText("root")  # KOReader default
        form.addRow("Username:", self.user_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Leave empty if no password set")
        form.addRow("Password:", self.password_input)

        self.remote_path_input = QLineEdit()
        self.remote_path_input.setText("/mnt/onboard/")
        self.remote_path_input.setPlaceholderText("/mnt/onboard/  or  /mnt/us")
        form.addRow("Remote Path:", self.remote_path_input)

        layout.addWidget(group)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Buttons
        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _on_connect(self):
        host = self.host_input.text().strip()
        if not host:
            self.status_label.setText("Please enter the device IP address.")
            return

        self.connect_btn.setEnabled(False)
        self.status_label.setText("Connecting... (this may take a few seconds)")

        self.worker = SSHConnectWorker(
            service=self.ssh_service,
            host=host,
            port=self.port_input.value(),
            user=self.user_input.text().strip(),
            password=self.password_input.text(),
            remote_path=self.remote_path_input.text().strip()
        )
        self.worker.success.connect(self._on_success)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_success(self, koreader_path: str):
        self.connected.emit(koreader_path)
        self.accept()

    def _on_error(self, message: str):
        self.status_label.setText(f"Error: {message}")
        self.connect_btn.setEnabled(True)
