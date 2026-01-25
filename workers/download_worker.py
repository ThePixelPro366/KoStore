"""
Background Worker for Downloads
"""

import logging
import os
import requests
import shutil
import tempfile
import zipfile
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


def find_plugin_root(base: Path) -> Path | None:
    """
    Find the root directory of a plugin within the given base path.
    
    Handles two plugin structure types:
    1. Release ZIP - files directly in root (main.lua, _meta.lua)
    2. Repository ZIP - files in subdirectories (foo.koplugin/)
    
    Args:
        base: Base directory to search in
        
    Returns:
        Path to plugin root directory, or None if not found
    """
    # Case 1: Release ZIP - files in root
    if (base / "main.lua").exists() and (base / "_meta.lua").exists():
        logger.info(f"Found plugin in root directory: {base}")
        return base
    
    # Case 2: Repository ZIP - search recursively
    for root, dirs, files in os.walk(base):
        if "main.lua" in files and "_meta.lua" in files:
            plugin_path = Path(root)
            logger.info(f"Found plugin in subdirectory: {plugin_path}")
            return plugin_path
    
    logger.warning(f"No valid plugin structure found in: {base}")
    return None


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
                
                # Save temporarily with unique directory
                temp_dir = Path(tempfile.mkdtemp(prefix="koreader_store_"))
                zip_path = temp_dir / f"{repo}.zip"
                
                with open(zip_path, "wb") as f:
                    f.write(zip_content)
                
                self.progress.emit("Extracting...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                self.progress.emit("Analyzing plugin structure...")
                
                # Find plugin directory using robust detection
                plugin_dir = find_plugin_root(temp_dir)
                
                if not plugin_dir:
                    self.finished.emit(
                        False,
                        "No valid plugin structure found (main.lua/_meta.lua missing)"
                    )
                    return
                
                plugin_name = plugin_dir.name
                if not plugin_name.endswith(".koplugin"):
                    plugin_name += ".koplugin"
                
                self.progress.emit("Installing...")
                
                target = Path(self.install_path) / "plugins" / plugin_name
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(plugin_dir, target)
                
                if self.is_update:
                    success_msg = f"{repo} updated successfully!"
                else:
                    success_msg = f"{repo} installed successfully!"
                
                self.finished.emit(True, success_msg)
            
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
        finally:
            # Cleanup temporary directory if it exists
            if 'temp_dir' in locals() and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temporary directory {temp_dir}: {cleanup_error}")
