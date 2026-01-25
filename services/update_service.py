"""
Update service for KOReader Store
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from utils.versioning import parse_version, is_newer_version

logger = logging.getLogger(__name__)


class UpdateService:
    """Service for checking plugin updates"""
    
    def __init__(self, github_api):
        self.github_api = github_api
        self.logger = logging.getLogger(__name__)
    
    def check_for_updates(self, installed_plugins: Dict[str, Dict[str, Any]], 
                         available_plugins: list) -> Dict[str, Dict[str, Any]]:
        """
        Check for updates for installed plugins
        
        Args:
            installed_plugins: Dictionary of installed plugins with their info
            available_plugins: List of available plugins from GitHub
            
        Returns:
            Dictionary of plugins that have updates available
        """
        updates = {}
        
        for plugin_name, installed_info in installed_plugins.items():
            # Find the corresponding available plugin
            available_plugin = self._find_available_plugin(plugin_name, available_plugins)
            
            if not available_plugin:
                self.logger.debug(f"No available plugin found for {plugin_name}")
                continue
            
            # Check for updates using different strategies
            update_info = self._check_plugin_update(installed_info, available_plugin)
            
            if update_info and update_info["has_update"]:
                updates[plugin_name] = {
                    "installed_version": installed_info.get("version", "Unknown"),
                    "latest_version": update_info["latest_version"],
                    "update_type": update_info["update_type"],
                    "download_url": update_info.get("download_url"),
                    "release_notes": update_info.get("release_notes", ""),
                    "published_at": update_info.get("published_at", "")
                }
                
                if installed_info.get("version", "Unknown") == "Unknown":
                    self.logger.info(f"Unknown version for {plugin_name}: Unknown -> {update_info['latest_version']}")
                else:
                    self.logger.info(f"Update available for {plugin_name}: {installed_info.get('version')} -> {update_info['latest_version']}")
        
        return updates
    
    def _find_available_plugin(self, plugin_name: str, available_plugins: list) -> Optional[Dict[str, Any]]:
        """Find the corresponding available plugin for an installed plugin"""
        # Try exact match first
        for plugin in available_plugins:
            if plugin.get("name") == plugin_name:
                return plugin
        
        # Try removing .koplugin suffix
        clean_name = plugin_name.replace(".koplugin", "")
        for plugin in available_plugins:
            if plugin.get("name") == clean_name:
                return plugin
        
        # Try case-insensitive match
        for plugin in available_plugins:
            if plugin.get("name", "").lower() == clean_name.lower():
                return plugin
        
        return None
    
    def _check_plugin_update(self, installed_info: Dict[str, Any], 
                            available_plugin: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if a plugin has an update available"""
        owner = available_plugin["owner"]["login"]
        repo = available_plugin["name"]
        
        # Strategy 1: Check releases first (most reliable)
        latest_release = self.github_api.get_latest_release(owner, repo)
        
        if latest_release and latest_release["tag_name"]:
            installed_version = installed_info.get("version", "")
            latest_version = latest_release["tag_name"]
            
            # Clean version strings (remove 'v' prefix if present)
            installed_clean = installed_version.lstrip('v')
            latest_clean = latest_version.lstrip('v')
            
            if is_newer_version(installed_clean, latest_clean):
                return {
                    "has_update": True,
                    "latest_version": latest_version,
                    "update_type": "release",
                    "download_url": self._get_release_download_url(latest_release),
                    "release_notes": latest_release.get("body", ""),
                    "published_at": latest_release.get("published_at", "")
                }
        
        # Strategy 2: Fallback to commit date comparison
        installed_meta_path = installed_info.get("path", "")
        if installed_meta_path:
            try:
                from pathlib import Path
                meta_file = Path(installed_meta_path) / "_meta.lua"
                
                if meta_file.exists():
                    # Get file modification time
                    installed_time = datetime.fromtimestamp(meta_file.stat().st_mtime)
                    
                    # Get latest commit info
                    commits = self.github_api.get_repository_commits(owner, repo)
                    
                    if commits:
                        latest_commit_date = datetime.fromisoformat(
                            commits["latest_commit_date"].replace('Z', '+00:00')
                        )
                        
                        # If latest commit is newer than installation by more than 1 day
                        if latest_commit_date > installed_time + timedelta(days=1):
                            return {
                                "has_update": True,
                                "latest_version": commits["latest_commit"][:8],
                                "update_type": "commit",
                                "published_at": commits["latest_commit_date"]
                            }
                            
            except Exception as e:
                self.logger.warning(f"Error checking file modification time for {repo}: {e}")
        
        # Strategy 3: Repository last updated as final fallback
        try:
            repo_updated = available_plugin.get("updated_at", "")
            if repo_updated:
                repo_updated_date = datetime.fromisoformat(repo_updated.replace('Z', '+00:00'))
                
                # If repository was updated recently (last 7 days) and we have no version info
                installed_version = installed_info.get("version", "Unknown")
                if installed_version == "Unknown" and repo_updated_date > datetime.now(repo_updated_date.tzinfo) - timedelta(days=7):
                    return {
                        "has_update": True,
                        "latest_version": "Recent Update",
                        "update_type": "repository",
                        "published_at": repo_updated
                    }
                    
        except Exception as e:
            self.logger.warning(f"Error checking repository update time for {repo}: {e}")
        
        return {"has_update": False}
    
    def _get_release_download_url(self, release: Dict[str, Any]) -> Optional[str]:
        """Get the download URL for a release"""
        assets = release.get("assets", [])
        
        # Look for ZIP files first
        for asset in assets:
            if asset.get("name", "").endswith(".zip"):
                return asset.get("browser_download_url")
        
        # Fallback to source archive
        owner = release.get("html_url", "").split("/")[-2]
        repo = release.get("html_url", "").split("/")[-1]
        
        if owner and repo:
            return f"https://github.com/{owner}/{repo}/archive/{release.get('tag_name', 'main')}.zip"
        
        return None
