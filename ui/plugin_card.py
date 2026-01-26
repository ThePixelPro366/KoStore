"""
Plugin installation service for KOReader Store
"""

import os
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class PluginInstaller:
    """Service for installing KOReader plugins and patches"""
    
    def __init__(self, koreader_path: str):
        self.koreader_path = Path(koreader_path)
        self.plugins_path = self.koreader_path / "plugins"
        self.patches_path = self.koreader_path / "patches"
        
        logger.info(f"Initializing plugin installer for {koreader_path}")
        
        # Ensure directories exist
        self.plugins_path.mkdir(exist_ok=True)
        self.patches_path.mkdir(exist_ok=True)
    
    def install_plugin_from_zip(self, zip_content: bytes, repo_name: str) -> Dict[str, Any]:
        """
        Install plugin from ZIP content.
        
        Args:
            zip_content: ZIP file content as bytes
            repo_name: Name of the repository
            
        Returns:
            Dictionary with installation result
        """
        result = {
            "success": False,
            "message": "",
            "plugin_name": "",
            "plugin_path": ""
        }
        
        try:
            # Create temporary directory
            temp_dir = Path("temp_download")
            temp_dir.mkdir(exist_ok=True)
            zip_path = temp_dir / f"{repo_name}.zip"
            
            # Save ZIP content
            with open(zip_path, "wb") as f:
                f.write(zip_content)
            
            logger.info(f"Extracting {repo_name} to temporary directory")
            
            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find plugin directory
            plugin_dir = self._find_plugin_directory(temp_dir)
            
            if not plugin_dir:
                result["message"] = "No valid plugin structure found (missing main.lua and _meta.lua)"
                return result
            
            # Determine plugin name
            plugin_name = plugin_dir.name
            if not plugin_name.endswith(".koplugin"):
                plugin_name = f"{plugin_name}.koplugin"
            
            # Install plugin
            target_path = self.plugins_path / plugin_name
            
            # Remove existing installation
            if target_path.exists():
                logger.info(f"Removing existing plugin: {target_path}")
                shutil.rmtree(target_path)
            
            # Copy plugin
            logger.info(f"Installing plugin to: {target_path}")
            shutil.copytree(plugin_dir, target_path)
            
            # Cleanup
            shutil.rmtree(temp_dir)
            
            result.update({
                "success": True,
                "message": f"{repo_name} installed successfully!",
                "plugin_name": plugin_name,
                "plugin_path": str(target_path)
            })
            
            logger.info(f"Successfully installed plugin: {plugin_name}")
            
        except Exception as e:
            logger.error(f"Error installing plugin {repo_name}: {e}")
            result["message"] = f"Error: {str(e)}"
        
        return result
    
    def _find_plugin_directory(self, search_dir: Path) -> Optional[Path]:
        """
        Find the plugin directory in extracted files.
        
        Args:
            search_dir: Directory to search in
            
        Returns:
            Path to plugin directory if found, None otherwise
        """
        # Search for directories containing main.lua and _meta.lua
        for root_dir in search_dir.glob("*"):
            if not root_dir.is_dir():
                continue
            
            main_lua = root_dir / "main.lua"
            meta_lua = root_dir / "_meta.lua"
            
            # Check if this directory contains both main.lua and _meta.lua
            if main_lua.exists() and meta_lua.exists():
                logger.info(f"Found plugin directory: {root_dir} with main.lua and _meta.lua")
                return root_dir
            
            # Also check for .koplugin directories (fallback)
            for koplugin_dir in root_dir.rglob("*.koplugin"):
                if koplugin_dir.is_dir():
                    koplugin_main = koplugin_dir / "main.lua"
                    koplugin_meta = koplugin_dir / "_meta.lua"
                    if koplugin_main.exists() and koplugin_meta.exists():
                        logger.info(f"Found .koplugin directory: {koplugin_dir}")
                        return koplugin_dir
        
        # If still not found, try to find any directory with main.lua
        for root_dir in search_dir.glob("*"):
            if not root_dir.is_dir():
                continue
            
            main_lua = root_dir / "main.lua"
            if main_lua.exists():
                logger.info(f"Found directory with main.lua: {root_dir}")
                return root_dir
        
        return None
    
    def install_patches(self, patches: list) -> Dict[str, Any]:
        """
        Install patch files.
        
        Args:
            patches: List of patch dictionaries with name and download_url
            
        Returns:
            Dictionary with installation result
        """
        result = {
            "success": False,
            "message": "",
            "installed_patches": []
        }
        
        try:
            import requests
            
            installed_count = 0
            
            for patch in patches:
                patch_name = patch["name"]
                download_url = patch["download_url"]
                
                logger.info(f"Downloading patch: {patch_name}")
                
                response = requests.get(download_url, timeout=10)
                response.raise_for_status()
                
                patch_file = self.patches_path / patch_name
                
                with open(patch_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
                
                result["installed_patches"].append(patch_name)
                installed_count += 1
            
            result.update({
                "success": True,
                "message": f"{installed_count} patch(es) installed successfully!"
            })
            
            logger.info(f"Successfully installed {installed_count} patches")
            
        except Exception as e:
            logger.error(f"Error installing patches: {e}")
            result["message"] = f"Error: {str(e)}"
        
        return result
    
    def uninstall_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """
        Uninstall a plugin.
        
        Args:
            plugin_name: Name of the plugin to uninstall
            
        Returns:
            Dictionary with uninstallation result
        """
        result = {
            "success": False,
            "message": ""
        }
        
        try:
            # Ensure plugin name ends with .koplugin
            if not plugin_name.endswith(".koplugin"):
                plugin_name = f"{plugin_name}.koplugin"
            
            plugin_path = self.plugins_path / plugin_name
            
            if not plugin_path.exists():
                result["message"] = f"Plugin {plugin_name} is not installed"
                return result
            
            logger.info(f"Uninstalling plugin: {plugin_path}")
            shutil.rmtree(plugin_path)
            
            result.update({
                "success": True,
                "message": f"{plugin_name} uninstalled successfully!"
            })
            
            logger.info(f"Successfully uninstalled plugin: {plugin_name}")
            
        except Exception as e:
            logger.error(f"Error uninstalling plugin {plugin_name}: {e}")
            result["message"] = f"Error: {str(e)}"
        
        return result
    
    def get_installed_plugins(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of installed plugins.
        
        Returns:
            Dictionary of installed plugins with their info
        """
        plugins = {}
        
        try:
            for plugin_dir in self.plugins_path.glob("*.koplugin"):
                if plugin_dir.is_dir():
                    plugin_name = plugin_dir.name
                    
                    # Try to read plugin metadata
                    meta_file = plugin_dir / "_meta.lua"
                    version = "Unknown"
                    
                    if meta_file.exists():
                        try:
                            with open(meta_file, 'r') as f:
                                content = f.read()
                                # Simple version extraction
                                import re
                                version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                                if version_match:
                                    version = version_match.group(1)
                        except Exception as e:
                            logger.warning(f"Could not read metadata for {plugin_name}: {e}")
                    
                    plugins[plugin_name] = {
                        "name": plugin_name,
                        "path": str(plugin_dir),
                        "version": version,
                        "has_meta": meta_file.exists()
                    }
        
        except Exception as e:
            logger.error(f"Error getting installed plugins: {e}")
        
        return plugins
