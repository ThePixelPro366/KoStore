"""
Known devices management for quick reconnection to KOReader devices.
Stores connection details and provides one-click reconnect functionality.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class KnownDevice:
    """Represents a known KOReader device connection."""
    
    def __init__(
        self,
        name: str,
        host: str,
        port: int = 2222,
        user: str = "root",
        remote_path: str = "/mnt/us",
        last_connected: Optional[str] = None,
        connection_type: str = "ssh"
    ):
        self.name = name
        self.host = host
        self.port = port
        self.user = user
        self.remote_path = remote_path
        self.last_connected = last_connected or datetime.now().isoformat()
        self.connection_type = connection_type
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "remote_path": self.remote_path,
            "last_connected": self.last_connected,
            "connection_type": self.connection_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "KnownDevice":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            host=data["host"],
            port=data["port"],
            user=data["user"],
            remote_path=data["remote_path"],
            last_connected=data.get("last_connected"),
            connection_type=data.get("connection_type", "ssh")
        )
    
    def __str__(self) -> str:
        return f"{self.name} ({self.host}:{self.port})"


class KnownDevicesManager:
    """Manages known devices for quick reconnection."""
    
    def __init__(self, config_file: Optional[Path] = None):
        if config_file is None:
            config_dir = Path.home() / ".koreader"
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / "known_devices.json"
        
        self.config_file = config_file
        self._devices: Dict[str, KnownDevice] = {}
        self.load_devices()
    
    def add_device(self, device: KnownDevice) -> None:
        """Add or update a known device."""
        self._devices[device.host] = device
        device.last_connected = datetime.now().isoformat()
        self.save_devices()
        logger.info("Added/updated known device: %s", device)
    
    def remove_device(self, host: str) -> bool:
        """Remove a known device by host."""
        if host in self._devices:
            device = self._devices.pop(host)
            self.save_devices()
            logger.info("Removed known device: %s", device)
            return True
        return False
    
    def get_device(self, host: str) -> Optional[KnownDevice]:
        """Get a known device by host."""
        return self._devices.get(host)
    
    def get_all_devices(self) -> List[KnownDevice]:
        """Get all known devices, sorted by last connection time."""
        return sorted(
            self._devices.values(),
            key=lambda d: d.last_connected,
            reverse=True
        )
    
    def get_recent_devices(self, limit: int = 5) -> List[KnownDevice]:
        """Get recently used devices."""
        return self.get_all_devices()[:limit]
    
    def load_devices(self) -> None:
        """Load devices from config file."""
        if not self.config_file.exists():
            logger.debug("No known devices file found, starting fresh")
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._devices = {
                host: KnownDevice.from_dict(device_data)
                for host, device_data in data.items()
            }
            logger.debug("Loaded %d known devices", len(self._devices))
        except Exception as e:
            logger.error("Failed to load known devices: %s", e)
            self._devices = {}
    
    def save_devices(self) -> None:
        """Save devices to config file."""
        try:
            data = {
                host: device.to_dict()
                for host, device in self._devices.items()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug("Saved %d known devices", len(self._devices))
        except Exception as e:
            logger.error("Failed to save known devices: %s", e)
