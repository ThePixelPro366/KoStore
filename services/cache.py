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
    
    def __init__(self, cache_file: str = "koreader_store_cache.json", cache_duration: timedelta = timedelta(weeks=4)):
        self.cache_file = Path(cache_file)
        self.cache_duration = cache_duration
        self.cache_data = {}
        
        logger.info(f"Initializing cache service with file: {cache_file}")
        self.load_cache()
    
    def load_cache(self) -> bool:
        """
        Load cache from file.
        
        Returns:
            True if cache was loaded successfully, False otherwise
        """
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                
                # Check if cache is expired
                if self.is_cache_expired():
                    logger.info("Cache expired, clearing cache")
                    self.cache_data = {}
                    return False
                
                logger.info(f"Cache loaded successfully. Plugins: {len(self.cache_data.get('plugins', []))}, Patches: {len(self.cache_data.get('patches', []))}")
                return True
            else:
                logger.info("No cache file found, starting with empty cache")
                self.cache_data = {}
                return False
                
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.cache_data = {}
            return False
    
    def save_cache(self) -> bool:
        """
        Save cache to file.
        
        Returns:
            True if cache was saved successfully, False otherwise
        """
        try:
            # Add timestamp
            self.cache_data['last_updated'] = datetime.now().isoformat()
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Cache saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
            return False
    
    def is_cache_expired(self) -> bool:
        """
        Check if cache is expired.
        
        Returns:
            True if cache is expired, False otherwise
        """
        if 'last_updated' not in self.cache_data:
            return True
        
        try:
            last_updated = datetime.fromisoformat(self.cache_data['last_updated'])
            return datetime.now() - last_updated > self.cache_duration
        except Exception as e:
            logger.warning(f"Error checking cache expiration: {e}")
            return True
    
    def get_plugins(self) -> list:
        """
        Get cached plugins.
        
        Returns:
            List of cached plugins
        """
        return self.cache_data.get('plugins', [])
    
    def get_patches(self) -> list:
        """
        Get cached patches.
        
        Returns:
            List of cached patches
        """
        return self.cache_data.get('patches', [])
    
    def set_plugins(self, plugins: list) -> None:
        """
        Set cached plugins.
        
        Args:
            plugins: List of plugins to cache
        """
        self.cache_data['plugins'] = plugins
        logger.info(f"Cached {len(plugins)} plugins")
    
    def set_patches(self, patches: list) -> None:
        """
        Set cached patches.
        
        Args:
            patches: List of patches to cache
        """
        self.cache_data['patches'] = patches
        logger.info(f"Cached {len(patches)} patches")
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        self.cache_data = {}
        logger.info("Cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the cache.
        
        Returns:
            Dictionary with cache information
        """
        info = {
            "cache_file": str(self.cache_file),
            "cache_exists": self.cache_file.exists(),
            "is_expired": self.is_cache_expired(),
            "plugins_count": len(self.get_plugins()),
            "patches_count": len(self.get_patches()),
            "last_updated": self.cache_data.get('last_updated', 'Never')
        }
        
        if info["last_updated"] != 'Never':
            try:
                last_updated = datetime.fromisoformat(info["last_updated"])
                info["last_updated"] = last_updated.strftime("%Y-%m-%d %H:%M:%S")
                info["age_days"] = (datetime.now() - last_updated).days
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
    
    def get_patch_by_id(self, patch_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific patch by ID from cache.
        
        Args:
            patch_id: GitHub repository ID
            
        Returns:
            Patch dictionary if found, None otherwise
        """
        patches = self.get_patches()
        for patch in patches:
            if patch.get('id') == patch_id:
                return patch
        return None
