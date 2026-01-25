"""
Background Worker for Downloads
"""

import logging
import requests
import shutil
import zipfile
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class DownloadWorker(QThread):
    """Background Worker für Downloads"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, api, item_data, install_path, item_type="plugin", is_update=False):
        super().__init__()
        self.api = api
        self.item_data = item_data
        self.install_path = install_path
        self.item_type = item_type
        self.is_update = is_update
    
    def run(self):
        try:
            owner = self.item_data["owner"]["login"]
            repo = self.item_data["name"]
            
            if self.item_type == "plugin":
                self.progress.emit(f"Downloading {repo}...")
                zip_content = self.api.download_repository_zip(owner, repo)
                
                if not zip_content:
                    self.finished.emit(False, "Failed to download repository")
                    return
                
                # Save temporarily
                temp_dir = Path("temp_download")
                temp_dir.mkdir(exist_ok=True)
                zip_path = temp_dir / f"{repo}.zip"
                
                with open(zip_path, "wb") as f:
                    f.write(zip_content)
                
                self.progress.emit("Extracting...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                self.progress.emit("Analyzing plugin structure...")
                
                # Find plugin directory by looking for main.lua and _meta.lua
                plugin_dir = None
                plugin_name = None
                
                # Search for directories containing main.lua and _meta.lua
                for root_dir in temp_dir.glob("*"):
                    if not root_dir.is_dir():
                        continue
                    
                    main_lua = root_dir / "main.lua"
                    meta_lua = root_dir / "_meta.lua"
                    
                    # Check if this directory contains both main.lua and _meta.lua
                    if main_lua.exists() and meta_lua.exists():
                        plugin_dir = root_dir
                        plugin_name = root_dir.name
                        logger.info(f"Found plugin directory: {plugin_dir} with main.lua and _meta.lua")
                        break
                    
                    # Also check for .koplugin directories (fallback)
                    for koplugin_dir in root_dir.rglob("*.koplugin"):
                        if koplugin_dir.is_dir():
                            koplugin_main = koplugin_dir / "main.lua"
                            koplugin_meta = koplugin_dir / "_meta.lua"
                            if koplugin_main.exists() and koplugin_meta.exists():
                                plugin_dir = koplugin_dir
                                plugin_name = koplugin_dir.name
                                logger.info(f"Found .koplugin directory: {plugin_dir}")
                                break
                    if plugin_dir:
                        break
                
                # If still not found, try to find any directory with main.lua
                if not plugin_dir:
                    for root_dir in temp_dir.glob("*"):
                        if not root_dir.is_dir():
                            continue
                        
                        main_lua = root_dir / "main.lua"
                        if main_lua.exists():
                            plugin_dir = root_dir
                            plugin_name = root_dir.name
                            logger.info(f"Found directory with main.lua: {plugin_dir}")
                            break
                
                if plugin_dir:
                    self.progress.emit("Installing...")
                    
                    # Create proper .koplugin directory name if needed
                    if not plugin_name.endswith(".koplugin"):
                        plugin_name = f"{plugin_name}.koplugin"
                    
                    target = Path(self.install_path) / "plugins" / plugin_name
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(plugin_dir, target)
                    
                    # Cleanup
                    shutil.rmtree(temp_dir)
                    
                    if self.is_update:
                        self.finished.emit(True, f"{repo} updated successfully!")
                    else:
                        self.finished.emit(True, f"{repo} installed successfully!")
                else:
                    self.finished.emit(False, "No valid plugin structure found (missing main.lua and _meta.lua)")
            
            elif self.item_type == "patch":
                # Download individual patch file
                patches = self.api.get_patch_files(owner, repo)
                if patches:
                    self.progress.emit(f"Downloading patches...")
                    patch_dir = Path(self.install_path) / "patches"
                    patch_dir.mkdir(exist_ok=True)
                    
                    for patch in patches:
                        response = requests.get(patch["download_url"], timeout=10)
                        patch_file = patch_dir / patch["name"]
                        with open(patch_file, "w", encoding="utf-8") as f:
                            f.write(response.text)
                    
                    self.finished.emit(True, f"{len(patches)} patch(es) installed!")
                else:
                    self.finished.emit(False, "No patches found")
                    
        except Exception as e:
            logger.error(f"Error during installation: {e}")
            self.finished.emit(False, f"Error: {str(e)}")
