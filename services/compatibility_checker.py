"""
Device-side compatibility checks for KOReader plugins.
Validates plugin requirements against device capabilities.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CompatibilityIssue:
    """Represents a compatibility issue."""
    
    def __init__(self, severity: str, message: str, suggestion: Optional[str] = None):
        self.severity = severity  # "error", "warning", "info"
        self.message = message
        self.suggestion = suggestion
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion
        }


class DeviceInfo:
    """Information about the connected KOReader device."""
    
    def __init__(self):
        self.platform = "unknown"  # "kindle", "kobo", "android", "pocketbook", "linux"
        self.koreader_version = "unknown"
        self.screen_size = (0, 0)  # (width, height)
        self.has_touchscreen = True
        self.has_keyboard = False
        self.has_physical_buttons = True
        self.cpu_arch = "unknown"
        self.memory_mb = 0
        self.storage_space_mb = 0
        self.firmware_version = "unknown"
        self.supported_features = set()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "koreader_version": self.koreader_version,
            "screen_size": self.screen_size,
            "has_touchscreen": self.has_touchscreen,
            "has_keyboard": self.has_keyboard,
            "has_physical_buttons": self.has_physical_buttons,
            "cpu_arch": self.cpu_arch,
            "memory_mb": self.memory_mb,
            "storage_space_mb": self.storage_space_mb,
            "firmware_version": self.firmware_version,
            "supported_features": list(self.supported_features)
        }


class PluginRequirements:
    """Requirements extracted from plugin metadata."""
    
    def __init__(self):
        self.min_koreader_version = None
        self.max_koreader_version = None
        self.supported_platforms = []  # List of platform names
        self.requires_touchscreen = False
        self.requires_keyboard = False
        self.requires_physical_buttons = False
        self.min_screen_width = 0
        self.min_screen_height = 0
        self.required_features = set()
        self.optional_features = set()
        self.conflicts_with = []  # List of plugin names
        self.dependencies = []  # List of plugin names
        self.min_memory_mb = 0
        self.required_storage_mb = 0
    
    @classmethod
    def from_plugin_metadata(cls, metadata_content: str) -> "PluginRequirements":
        """Parse requirements from plugin _meta.lua content."""
        req = cls()
        
        try:
            # Parse version requirements
            version_match = re.search(r'min_koreader_version\s*=\s*["\']([^"\']+)["\']', metadata_content)
            if version_match:
                req.min_koreader_version = version_match.group(1)
            
            version_match = re.search(r'max_koreader_version\s*=\s*["\']([^"\']+)["\']', metadata_content)
            if version_match:
                req.max_koreader_version = version_match.group(1)
            
            # Parse platform requirements
            platforms_match = re.search(r'supported_platforms\s*=\s*{([^}]+)}', metadata_content)
            if platforms_match:
                platforms_str = platforms_match.group(1)
                req.supported_platforms = [p.strip().strip('"\'') for p in platforms_str.split(',')]
            
            # Parse hardware requirements
            req.requires_touchscreen = 'requires_touchscreen\s*=\s*true' in metadata_content
            req.requires_keyboard = 'requires_keyboard\s*=\s*true' in metadata_content
            req.requires_physical_buttons = 'requires_physical_buttons\s*=\s*true' in metadata_content
            
            # Parse screen size requirements
            width_match = re.search(r'min_screen_width\s*=\s*(\d+)', metadata_content)
            if width_match:
                req.min_screen_width = int(width_match.group(1))
            
            height_match = re.search(r'min_screen_height\s*=\s*(\d+)', metadata_content)
            if height_match:
                req.min_screen_height = int(height_match.group(1))
            
            # Parse memory requirements
            memory_match = re.search(r'min_memory_mb\s*=\s*(\d+)', metadata_content)
            if memory_match:
                req.min_memory_mb = int(memory_match.group(1))
            
            storage_match = re.search(r'required_storage_mb\s*=\s*(\d+)', metadata_content)
            if storage_match:
                req.required_storage_mb = int(storage_match.group(1))
            
            # Parse features
            features_match = re.search(r'required_features\s*=\s*{([^}]+)}', metadata_content)
            if features_match:
                features_str = features_match.group(1)
                req.required_features = {f.strip().strip('"\'') for f in features_str.split(',')}
            
            features_match = re.search(r'optional_features\s*=\s*{([^}]+)}', metadata_content)
            if features_match:
                features_str = features_match.group(1)
                req.optional_features = {f.strip().strip('"\'') for f in features_str.split(',')}
            
            # Parse conflicts and dependencies
            conflicts_match = re.search(r'conflicts_with\s*=\s*{([^}]+)}', metadata_content)
            if conflicts_match:
                conflicts_str = conflicts_match.group(1)
                req.conflicts_with = [c.strip().strip('"\'') for c in conflicts_str.split(',')]
            
            deps_match = re.search(r'dependencies\s*=\s*{([^}]+)}', metadata_content)
            if deps_match:
                deps_str = deps_match.group(1)
                req.dependencies = [d.strip().strip('"\'') for d in deps_str.split(',')]
                
        except Exception as e:
            logger.warning("Error parsing plugin requirements: %s", e)
        
        return req


class CompatibilityChecker:
    """Checks plugin compatibility with device capabilities."""
    
    def __init__(self, ssh_service=None):
        self.ssh_service = ssh_service
        self.device_info = DeviceInfo()
        self._detect_device_info()
    
    def _detect_device_info(self):
        """Detect device information."""
        if not self.ssh_service or not self.ssh_service.is_connected():
            logger.warning("No SSH connection available, using default device info")
            return
        
        try:
            # Try to detect platform
            self._detect_platform()
            
            # Get KOReader version
            self._get_koreader_version()
            
            # Get screen information
            self._get_screen_info()
            
            # Get hardware info
            self._get_hardware_info()
            
            # Get available features
            self._get_available_features()
            
        except Exception as e:
            logger.error("Error detecting device info: %s", e)
    
    def _detect_platform(self):
        """Detect the device platform."""
        # Check for platform-specific files/paths
        if self.ssh_service.exists("/mnt/us"):
            self.device_info.platform = "kindle"
        elif self.ssh_service.exists("/mnt/onboard"):
            self.device_info.platform = "kobo"
        elif self.ssh_service.exists("/system"):
            self.device_info.platform = "android"
        elif self.ssh_service.exists("/usr/bin"):
            self.device_info.platform = "linux"
        
        logger.info("Detected platform: %s", self.device_info.platform)
    
    def _get_koreader_version(self):
        """Get KOReader version."""
        try:
            # Look for version file
            version_files = [
                "koreader/git-rev",
                "koreader/version.lua",
                ".adds/koreader/git-rev",
                ".adds/koreader/version.lua"
            ]
            
            for version_file in version_files:
                if self.ssh_service.exists(version_file):
                    content = self.ssh_service.read_bytes(version_file).decode('utf-8', errors='ignore')
                    
                    # Try to extract version
                    version_match = re.search(r'v?(\d{4}\.\d{2}-\d+|\d+\.\d+\.\d+)', content)
                    if version_match:
                        self.device_info.koreader_version = version_match.group(1)
                        break
            
            logger.info("KOReader version: %s", self.device_info.koreader_version)
            
        except Exception as e:
            logger.warning("Could not get KOReader version: %s", e)
    
    def _get_screen_info(self):
        """Get screen information."""
        try:
            # Try to read screen dimensions from KOReader settings
            settings_files = [
                "koreader/settings.reader.lua",
                ".adds/koreader/settings.reader.lua"
            ]
            
            for settings_file in settings_files:
                if self.ssh_service.exists(settings_file):
                    content = self.ssh_service.read_bytes(settings_file).decode('utf-8', errors='ignore')
                    
                    # Look for screen dimensions
                    dpi_match = re.search(r'dpi\s*=\s*(\d+)', content)
                    width_match = re.search(r'screen_width\s*=\s*(\d+)', content)
                    height_match = re.search(r'screen_height\s*=\s*(\d+)', content)
                    
                    if width_match and height_match:
                        self.device_info.screen_size = (int(width_match.group(1)), int(height_match.group(1)))
                        break
            
            logger.info("Screen size: %s", self.device_info.screen_size)
            
        except Exception as e:
            logger.warning("Could not get screen info: %s", e)
    
    def _get_hardware_info(self):
        """Get hardware information."""
        try:
            # Try to get memory info
            if self.ssh_service.exists("/proc/meminfo"):
                content = self.ssh_service.read_bytes("/proc/meminfo").decode('utf-8', errors='ignore')
                mem_match = re.search(r'MemTotal:\s+(\d+)\s+kB', content)
                if mem_match:
                    self.device_info.memory_mb = int(mem_match.group(1)) // 1024
            
            # Try to get storage info
            stat = self.ssh_service.stat("/")
            if stat and hasattr(stat, 'st_bsize') and hasattr(stat, 'st_blocks'):
                self.device_info.storage_space_mb = (stat.st_bsize * stat.st_blocks) // (1024 * 1024)
            
            logger.info("Memory: %d MB, Storage: %d MB", 
                       self.device_info.memory_mb, self.device_info.storage_space_mb)
            
        except Exception as e:
            logger.warning("Could not get hardware info: %s", e)
    
    def _get_available_features(self):
        """Get available features on the device."""
        try:
            # Check for common features
            features = []
            
            # Check for frontlight
            if self.ssh_service.exists("/sys/class/backlight"):
                features.append("frontlight")
            
            # Check for network
            if self.ssh_service.exists("/sys/class/net"):
                features.append("network")
            
            # Check for GPS
            if self.ssh_service.exists("/sys/class/gps"):
                features.append("gps")
            
            # Check for accelerometer
            if self.ssh_service.exists("/sys/class/input"):
                features.append("accelerometer")
            
            self.device_info.supported_features = set(features)
            logger.info("Available features: %s", features)
            
        except Exception as e:
            logger.warning("Could not get available features: %s", e)
    
    def check_plugin_compatibility(
        self, 
        plugin_metadata: str, 
        installed_plugins: List[str]
    ) -> Tuple[bool, List[CompatibilityIssue]]:
        """Check if a plugin is compatible with the current device."""
        issues = []
        
        # Parse plugin requirements
        requirements = PluginRequirements.from_plugin_metadata(plugin_metadata)
        
        # Check KOReader version compatibility
        if requirements.min_koreader_version:
            if not self._version_compatible(
                self.device_info.koreader_version, 
                requirements.min_koreader_version,
                requirements.max_koreader_version
            ):
                issues.append(CompatibilityIssue(
                    "error",
                    f"KOReader version {self.device_info.koreader_version} is incompatible. "
                    f"Required: {requirements.min_koreader_version}"
                    + (f" to {requirements.max_koreader_version}" if requirements.max_koreader_version else ""),
                    "Update KOReader to a compatible version"
                ))
        
        # Check platform compatibility
        if requirements.supported_platforms:
            if self.device_info.platform not in requirements.supported_platforms:
                issues.append(CompatibilityIssue(
                    "error",
                    f"Platform {self.device_info.platform} is not supported. "
                    f"Supported platforms: {', '.join(requirements.supported_platforms)}",
                    "This plugin is not compatible with your device type"
                ))
        
        # Check hardware requirements
        if requirements.requires_touchscreen and not self.device_info.has_touchscreen:
            issues.append(CompatibilityIssue(
                "error",
                "Plugin requires touchscreen but device doesn't have one",
                "Use a device with touchscreen support"
            ))
        
        if requirements.requires_keyboard and not self.device_info.has_keyboard:
            issues.append(CompatibilityIssue(
                "warning",
                "Plugin requires keyboard but device doesn't have one",
                "Some features may not be available"
            ))
        
        if requirements.requires_physical_buttons and not self.device_info.has_physical_buttons:
            issues.append(CompatibilityIssue(
                "warning",
                "Plugin requires physical buttons but device doesn't have them",
                "Some features may not be available"
            ))
        
        # Check screen size requirements
        if requirements.min_screen_width > 0 or requirements.min_screen_height > 0:
            screen_width, screen_height = self.device_info.screen_size
            if screen_width < requirements.min_screen_width or screen_height < requirements.min_screen_height:
                issues.append(CompatibilityIssue(
                    "warning",
                    f"Screen size {screen_width}x{screen_height} may be too small. "
                    f"Recommended: {requirements.min_screen_width}x{requirements.min_screen_height} or larger",
                    "UI elements may not display correctly"
                ))
        
        # Check memory requirements
        if requirements.min_memory_mb > 0 and self.device_info.memory_mb > 0:
            if self.device_info.memory_mb < requirements.min_memory_mb:
                issues.append(CompatibilityIssue(
                    "warning",
                    f"Device has {self.device_info.memory_mb} MB memory but plugin requires {requirements.min_memory_mb} MB",
                    "Plugin may run slowly or crash"
                ))
        
        # Check storage requirements
        if requirements.required_storage_mb > 0 and self.device_info.storage_space_mb > 0:
            if self.device_info.storage_space_mb < requirements.required_storage_mb:
                issues.append(CompatibilityIssue(
                    "error",
                    f"Insufficient storage space. Required: {requirements.required_storage_mb} MB",
                    "Free up space on your device"
                ))
        
        # Check required features
        missing_features = requirements.required_features - self.device_info.supported_features
        if missing_features:
            issues.append(CompatibilityIssue(
                "error",
                f"Missing required features: {', '.join(missing_features)}",
                "These features are not available on your device"
            ))
        
        # Check optional features
        missing_optional = requirements.optional_features - self.device_info.supported_features
        if missing_optional:
            issues.append(CompatibilityIssue(
                "info",
                f"Optional features not available: {', '.join(missing_optional)}",
                "Some features may be limited"
            ))
        
        # Check conflicts with installed plugins
        installed_set = set(installed_plugins)
        conflicts = set(requirements.conflicts_with) & installed_set
        if conflicts:
            issues.append(CompatibilityIssue(
                "error",
                f"Conflicts with installed plugins: {', '.join(conflicts)}",
                f"Uninstall these plugins first: {', '.join(conflicts)}"
            ))
        
        # Check dependencies
        missing_deps = set(requirements.dependencies) - installed_set
        if missing_deps:
            issues.append(CompatibilityIssue(
                "warning",
                f"Missing dependencies: {', '.join(missing_deps)}",
                f"Install these plugins first: {', '.join(missing_deps)}"
            ))
        
        # Determine overall compatibility
        has_errors = any(issue.severity == "error" for issue in issues)
        
        return not has_errors, issues
    
    def _version_compatible(self, current: str, min_version: str, max_version: Optional[str] = None) -> bool:
        """Check if current version is within the required range."""
        try:
            # Simple version comparison for KOReader date-based versions (YYYY.MM-DD)
            def parse_version(v):
                # Handle formats like "2024.02-01" or "2024.02.01"
                v = v.replace('v', '').replace('_', '.')
                parts = v.split('.')
                if len(parts) >= 2:
                    year = int(parts[0])
                    month_day = parts[1].replace('-', '.')
                    month_day_parts = month_day.split('.')
                    month = int(month_day_parts[0])
                    day = int(month_day_parts[1]) if len(month_day_parts) > 1 else 1
                    return year * 10000 + month * 100 + day
                return 0
            
            current_num = parse_version(current)
            min_num = parse_version(min_version)
            
            if current_num < min_num:
                return False
            
            if max_version:
                max_num = parse_version(max_version)
                if current_num > max_num:
                    return False
            
            return True
            
        except Exception as e:
            logger.warning("Error comparing versions: %s", e)
            return True  # Assume compatible if we can't compare
    
    def get_device_info(self) -> DeviceInfo:
        """Get the detected device information."""
        return self.device_info
