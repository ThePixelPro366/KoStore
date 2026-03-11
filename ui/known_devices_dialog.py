"""
Known devices selection dialog for quick reconnection.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QPushButton, QMessageBox, QGroupBox, QFormLayout, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from services.known_devices import KnownDevicesManager, KnownDevice


class KnownDevicesDialog(QDialog):
    """Dialog for selecting and managing known devices."""
    
    device_selected = pyqtSignal(KnownDevice)
    connect_new = pyqtSignal()
    
    def __init__(self, devices_manager: KnownDevicesManager, parent=None):
        super().__init__(parent)
        self.devices_manager = devices_manager
        self.setWindowTitle("Known Devices")
        self.setMinimumSize(500, 400)
        self._build_ui()
        self._refresh_devices()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Select a device to connect to:")
        header.setFont(QFont("", 10, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Devices list
        self.devices_list = QListWidget()
        self.devices_list.itemDoubleClicked.connect(self._on_device_selected)
        layout.addWidget(self.devices_list)
        
        # Device details group
        self.details_group = QGroupBox("Device Details")
        details_layout = QFormLayout(self.details_group)
        
        self.name_label = QLabel("-")
        self.host_label = QLabel("-")
        self.port_label = QLabel("-")
        self.user_label = QLabel("-")
        self.path_label = QLabel("-")
        self.last_label = QLabel("-")
        
        details_layout.addRow("Name:", self.name_label)
        details_layout.addRow("Host:", self.host_label)
        details_layout.addRow("Port:", self.port_label)
        details_layout.addRow("User:", self.user_label)
        details_layout.addRow("Path:", self.path_label)
        details_layout.addRow("Last Connected:", self.last_label)
        
        layout.addWidget(self.details_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.connect_btn.setEnabled(False)
        
        self.remove_btn = QPushButton("Remove Device")
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        self.remove_btn.setEnabled(False)
        
        self.new_btn = QPushButton("Add New Device")
        self.new_btn.clicked.connect(self._on_new_clicked)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.remove_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.new_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Connect list selection
        self.devices_list.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _refresh_devices(self):
        """Refresh the devices list."""
        self.devices_list.clear()
        devices = self.devices_manager.get_all_devices()
        
        if not devices:
            self.devices_list.addItem("No known devices")
            self.devices_list.setEnabled(False)
            return
        
        self.devices_list.setEnabled(True)
        for device in devices:
            # Format: "Name (host:port) - Last connected"
            last_time = device.last_connected.split('T')[0] if device.last_connected else "Unknown"
            item_text = f"{device.name} ({device.host}:{device.port}) - {last_time}"
            self.devices_list.addItem(item_text)
    
    def _on_selection_changed(self):
        """Handle device selection change."""
        selected_items = self.devices_list.selectedItems()
        has_selection = bool(selected_items) and self.devices_list.isEnabled()
        
        self.connect_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)
        
        if has_selection:
            row = self.devices_list.row(selected_items[0])
            device = self.devices_manager.get_all_devices()[row]
            self._show_device_details(device)
        else:
            self._clear_device_details()
    
    def _show_device_details(self, device: KnownDevice):
        """Show device details in the details group."""
        self.name_label.setText(device.name)
        self.host_label.setText(device.host)
        self.port_label.setText(str(device.port))
        self.user_label.setText(device.user)
        self.path_label.setText(device.remote_path)
        
        if device.last_connected:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(device.last_connected)
                self.last_label.setText(dt.strftime("%Y-%m-%d %H:%M"))
            except:
                self.last_label.setText(device.last_connected)
        else:
            self.last_label.setText("Unknown")
    
    def _clear_device_details(self):
        """Clear device details."""
        for label in [self.name_label, self.host_label, self.port_label, 
                     self.user_label, self.path_label, self.last_label]:
            label.setText("-")
    
    def _on_device_selected(self):
        """Handle double-click on device."""
        self._on_connect_clicked()
    
    def _on_connect_clicked(self):
        """Handle connect button click."""
        selected_items = self.devices_list.selectedItems()
        if not selected_items:
            return
        
        row = self.devices_list.row(selected_items[0])
        device = self.devices_manager.get_all_devices()[row]
        self.device_selected.emit(device)
        self.accept()
    
    def _on_remove_clicked(self):
        """Handle remove device button click."""
        selected_items = self.devices_list.selectedItems()
        if not selected_items:
            return
        
        row = self.devices_list.row(selected_items[0])
        device = self.devices_manager.get_all_devices()[row]
        
        reply = QMessageBox.question(
            self,
            "Remove Device",
            f"Remove device '{device.name}' from known devices?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.devices_manager.remove_device(device.host)
            self._refresh_devices()
    
    def _on_new_clicked(self):
        """Handle add new device button click."""
        self.connect_new.emit()
        self.accept()


class AddDeviceDialog(QDialog):
    """Dialog for adding a new known device."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Known Device")
        self.setMinimumWidth(400)
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Form
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("My Kindle")
        form.addRow("Device Name:", self.name_input)
        
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("192.168.1.42")
        form.addRow("IP Address:", self.host_input)
        
        self.port_input = QLineEdit()
        self.port_input.setText("2222")
        form.addRow("Port:", self.port_input)
        
        self.user_input = QLineEdit()
        self.user_input.setText("root")
        form.addRow("Username:", self.user_input)
        
        self.path_input = QLineEdit()
        self.path_input.setText("/mnt/us")
        form.addRow("Remote Path:", self.path_input)
        
        layout.addLayout(form)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Device")
        self.add_btn.clicked.connect(self._on_add_clicked)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _on_add_clicked(self):
        """Handle add button click."""
        name = self.name_input.text().strip()
        host = self.host_input.text().strip()
        port_str = self.port_input.text().strip()
        user = self.user_input.text().strip()
        path = self.path_input.text().strip()
        
        if not name or not host:
            QMessageBox.warning(self, "Missing Information", 
                              "Please enter at least a device name and IP address.")
            return
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Invalid Port", 
                              "Please enter a valid port number (1-65535).")
            return
        
        self.device_data = {
            "name": name,
            "host": host,
            "port": port,
            "user": user or "root",
            "remote_path": path or "/mnt/us"
        }
        
        self.accept()
    
    def get_device(self) -> KnownDevice:
        """Get the created device."""
        if hasattr(self, 'device_data'):
            return KnownDevice(**self.device_data)
        return None
