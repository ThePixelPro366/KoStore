"""
SSH connection dialog for wireless KOReader device connections
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QMessageBox,
    QFormLayout, QGroupBox, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from services.ssh_connection import SSHConnectionService
from services.known_devices import KnownDevicesManager, KnownDevice
from ui.known_devices_dialog import KnownDevicesDialog, AddDeviceDialog
from ui.connection_diagnostics_dialog import ConnectionDiagnosticsDialog


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
        self.devices_manager = KnownDevicesManager()
        self.setWindowTitle("Connect via WiFi (SFTP)")
        self.setMinimumWidth(420)
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

        # Quick connect buttons for known devices
        quick_group = QGroupBox("Quick Connect")
        quick_layout = QVBoxLayout(quick_group)
        
        self.known_devices_btn = QPushButton("Known Devices")
        self.known_devices_btn.clicked.connect(self._on_known_devices)
        quick_layout.addWidget(self.known_devices_btn)
        
        self.diagnostics_btn = QPushButton("Connection Test")
        self.diagnostics_btn.clicked.connect(self._on_diagnostics)
        quick_layout.addWidget(self.diagnostics_btn)
        
        # Show recent devices if any
        recent_devices = self.devices_manager.get_recent_devices(3)
        if recent_devices:
            recent_label = QLabel("Recent devices:")
            recent_label.setWordWrap(True)
            quick_layout.addWidget(recent_label)
            
            for device in recent_devices:
                btn = QPushButton(f"{device.name} ({device.host})")
                btn.clicked.connect(lambda checked, d=device: self._on_quick_connect(d))
                quick_layout.addWidget(btn)
        
        layout.addWidget(quick_group)

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
        # Save successful connection to known devices
        device = KnownDevice(
            name=f"Device {self.host_input.text()}",
            host=self.host_input.text().strip(),
            port=self.port_input.value(),
            user=self.user_input.text().strip(),
            remote_path=self.remote_path_input.text().strip()
        )
        self.devices_manager.add_device(device)
        
        self.connected.emit(koreader_path)
        self.accept()

    def _on_error(self, message: str):
        self.status_label.setText(f"Error: {message}")
        self.connect_btn.setEnabled(True)

    def _on_known_devices(self):
        """Handle known devices button click."""
        dialog = KnownDevicesDialog(self.devices_manager, self)
        dialog.device_selected.connect(self._on_device_selected)
        dialog.connect_new.connect(self._on_add_new_device)
        dialog.exec()
    
    def _on_device_selected(self, device: KnownDevice):
        """Handle device selection from known devices."""
        # Fill the form with device details
        self.host_input.setText(device.host)
        self.port_input.setValue(device.port)
        self.user_input.setText(device.user)
        self.remote_path_input.setText(device.remote_path)
        self.password_input.clear()  # Don't store passwords
    
    def _on_add_new_device(self):
        """Handle add new device request."""
        dialog = AddDeviceDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            device = dialog.get_device()
            if device:
                self.devices_manager.add_device(device)
                # Fill the form with new device details
                self.host_input.setText(device.host)
                self.port_input.setValue(device.port)
                self.user_input.setText(device.user)
                self.remote_path_input.setText(device.remote_path)
    
    def _on_quick_connect(self, device: KnownDevice):
        """Handle quick connect button click."""
        self.host_input.setText(device.host)
        self.port_input.setValue(device.port)
        self.user_input.setText(device.user)
        self.remote_path_input.setText(device.remote_path)
        self.password_input.clear()
        # Auto-connect
        self._on_connect()

    def _on_diagnostics(self):
        """Handle diagnostics button click."""
        dialog = ConnectionDiagnosticsDialog(self)
        dialog.set_connection_info(
            self.host_input.text().strip(),
            self.port_input.value(),
            self.user_input.text().strip()
        )
        dialog.exec()
