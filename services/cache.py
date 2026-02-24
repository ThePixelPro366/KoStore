"""
Cache service for KOReader Store
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching plugin and patch data"""
    
    def __init__(self, cache_duration: timedelta = timedelta(weeks=4)):
        self.cache_duration = cache_duration
        self.plugin_cache_file = Path("appstore_cache_plugin.json")
        self.patch_cache_file = Path("appstore_cache_patch.json")
        self.plugin_cache_data = {}
        self.patch_cache_data = {}
        
        logger.info("Initializing cache service with separate plugin and patch cache files")
        self.load_cache()
    
    def load_cache(self) -> bool:
        """
        Load cache from separate plugin and patch files.
        
        Returns:
            True if at least one cache was loaded successfully, False otherwise
        """
        plugin_loaded = False
        patch_loaded = False
        
        # Load plugin cache
        try:
            if self.plugin_cache_file.exists():
                with open(self.plugin_cache_file, 'r', encoding='utf-8') as f:
                    self.plugin_cache_data = json.load(f)
                
                # Check if plugin cache is expired
                if not self._is_cache_data_expired(self.plugin_cache_data):
                    logger.info(f"Plugin cache loaded: {len(self.plugin_cache_data)} plugins")
                    plugin_loaded = True
                else:
                    logger.info("Plugin cache expired, clearing")
                    self.plugin_cache_data = {}
            else:
                logger.info("No plugin cache file found")
                self.plugin_cache_data = {}
        except Exception as e:
            logger.error(f"Error loading plugin cache: {e}")
            self.plugin_cache_data = {}
        
        # Load patch cache
        try:
            if self.patch_cache_file.exists():
                with open(self.patch_cache_file, 'r', encoding='utf-8') as f:
                    self.patch_cache_data = json.load(f)
                
                # Check if patch cache is expired
                if not self._is_cache_data_expired(self.patch_cache_data):
                    logger.info(f"Patch cache loaded: {len(self.patch_cache_data)} patches")
                    patch_loaded = True
                else:
                    logger.info("Patch cache expired, clearing")
                    self.patch_cache_data = {}
            else:
                logger.info("No patch cache file found")
                self.patch_cache_data = {}
        except Exception as e:
            logger.error(f"Error loading patch cache: {e}")
            self.patch_cache_data = {}
        
        return plugin_loaded or patch_loaded
    
    def _is_cache_data_expired(self, cache_data: Dict[str, Any]) -> bool:
        """
        Check if specific cache data is expired.
        
        Args:
            cache_data: Cache data dictionary to check
            
        Returns:
            True if cache is expired, False otherwise
        """
        if 'last_updated' not in cache_data:
            return True
        
        try:
            last_updated = datetime.fromisoformat(cache_data['last_updated'])
            return datetime.now() - last_updated > self.cache_duration
        except Exception as e:
            logger.warning(f"Error checking cache expiration: {e}")
            return True
    
    def save_cache(self) -> bool:
        """
        Save cache to separate plugin and patch files.
        
        Returns:
            True if both caches were saved successfully, False otherwise
        """
        plugin_saved = False
        patch_saved = False
        
        # Save plugin cache
        try:
            if self.plugin_cache_data:
                self.plugin_cache_data['last_updated'] = datetime.now().isoformat()
                with open(self.plugin_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.plugin_cache_data, f, indent=2, ensure_ascii=False)
                plugin_saved = True
                logger.info("Plugin cache saved successfully")
        except Exception as e:
            logger.error(f"Error saving plugin cache: {e}")
        
        # Save patch cache
        try:
            if self.patch_cache_data:
                self.patch_cache_data['last_updated'] = datetime.now().isoformat()
                with open(self.patch_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.patch_cache_data, f, indent=2, ensure_ascii=False)
                patch_saved = True
                logger.info("Patch cache saved successfully")
        except Exception as e:
            logger.error(f"Error saving patch cache: {e}")
        
        return plugin_saved and patch_saved
    
    def get_plugins(self) -> list:
        """
        Get cached plugins.
        
        Returns:
            List of cached plugins
        """
        return self.plugin_cache_data.get('repos', [])
    
    def get_patches(self) -> list:
        """
        Get cached patches.
        
        Returns:
            List of cached patches
        """
        return self.patch_cache_data.get('repos', [])
    
    def set_plugins(self, plugins: list) -> None:
        """
        Set cached plugins.
        
        Args:
            plugins: List of plugins to cache
        """
        self.plugin_cache_data['repos'] = plugins
        logger.info(f"Cached {len(plugins)} plugins")
    
    def set_patches(self, patches: list) -> None:
        """
        Set cached patches.
        
        Args:
            patches: List of patches to cache
        """
        self.patch_cache_data['repos'] = patches
        logger.info(f"Cached {len(patches)} patches")
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        self.plugin_cache_data = {}
        self.patch_cache_data = {}
        # Remove cache files
        if self.plugin_cache_file.exists():
            self.plugin_cache_file.unlink()
        if self.patch_cache_file.exists():
            self.patch_cache_file.unlink()
        logger.info("Cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the cache.
        
        Returns:
            Dictionary with cache information
        """
        info = {
            "plugin_cache_file": str(self.plugin_cache_file),
            "patch_cache_file": str(self.patch_cache_file),
            "plugin_cache_exists": self.plugin_cache_file.exists(),
            "patch_cache_exists": self.patch_cache_file.exists(),
            "plugins_count": len(self.get_plugins()),
            "patches_count": len(self.get_patches()),
            "plugin_last_updated": self.plugin_cache_data.get('last_updated', 'Never'),
            "patch_last_updated": self.patch_cache_data.get('last_updated', 'Never')
        }
        
        # Format timestamps
        for key in ['plugin_last_updated', 'patch_last_updated']:
            if info[key] != 'Never':
                try:
                    last_updated = datetime.fromisoformat(info[key])
                    info[key] = last_updated.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
        
        return info
    
    def update_cache(self, plugins: list = None, patches: list = None) -> bool:
        """
        Update cache with new data.
        
        Args:
            plugins: List of plugins to cache (optional)
            patches: List of patches to cache (optional)
            
        Returns:
            True if cache was updated successfully, False otherwise
        """
        if plugins is not None:
            self.set_plugins(plugins)
        
        if patches is not None:
            self.set_patches(patches)
        
        return self.save_cache()
    
    def get_plugin_by_id(self, plugin_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific plugin by ID from cache.
        
        Args:
            plugin_id: GitHub repository ID
            
        Returns:
            Plugin dictionary if found, None otherwise
        """
        plugins = self.get_plugins()
        for plugin in plugins:
            if plugin.get('id') == plugin_id:
                return plugin
        return None
    
    def is_cache_expired(self) -> bool:
        """
        Check if any cache is expired.
        
        Returns:
            True if either cache is expired, False otherwise
        """
        plugin_expired = self._is_cache_data_expired(self.plugin_cache_data)
        patch_expired = self._is_cache_data_expired(self.patch_cache_data)
        return plugin_expired or patch_expired
    
    def get_favorites(self) -> set:
        """
        Get cached favorites.
        
        Returns:
            Set of favorite plugin names
        """
        return set(self.plugin_cache_data.get('favorites', []))
    
    def set_favorites(self, favorites: set) -> None:
        """
        Set cached favorites.
        
        Args:
            favorites: Set of favorite plugin names
        """
        self.plugin_cache_data['favorites'] = list(favorites)
        logger.info(f"Cached {len(favorites)} favorites")
    
    def add_favorite(self, plugin_name: str) -> None:
        """
        Add a plugin to favorites.
        
        Args:
            plugin_name: Name of the plugin to add to favorites
        """
        favorites = self.get_favorites()
        favorites.add(plugin_name)
        self.set_favorites(favorites)
        self.save_cache()
        logger.info(f"Added {plugin_name} to favorites")
    
    def remove_favorite(self, plugin_name: str) -> None:
        """
        Remove a plugin from favorites.
        
        Args:
            plugin_name: Name of the plugin to remove from favorites
        """
        favorites = self.get_favorites()
        favorites.discard(plugin_name)
        self.set_favorites(favorites)
        self.save_cache()
        logger.info(f"Removed {plugin_name} from favorites")
    
    def is_favorite(self, plugin_name: str) -> bool:
        """
        Check if a plugin is in favorites.
        
        Args:
            plugin_name: Name of the plugin to check
            
        Returns:
            True if plugin is in favorites, False otherwise
        """
        return plugin_name in self.get_favorites()
