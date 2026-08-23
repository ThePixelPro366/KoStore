"""Workers for KOReader Store."""

import logging
import os
import requests
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from utils.plugin_naming import derive_plugin_folder_name


logger = logging.getLogger(__name__)


class DataFetchWorker(QThread):
    """Background worker for fetching plugins/patches from GitHub and updating cache."""

    finished = pyqtSignal(bool, object, object, str)

    def __init__(self, appstore_service: Any, cache_service: Any):
        super().__init__()
        self._appstore_service = appstore_service
        self._cache_service = cache_service

    def run(self):
        try:
            logging.info("Fetching plugins from GitHub...")
            plugins = self._appstore_service.fetch_repositories("plugin")
            logging.info(f"Fetched {len(plugins)} plugins")

            logging.info("Fetching patches from GitHub...")
            raw_patches = self._appstore_service.fetch_repositories("patch")
            logging.info(f"Fetched {len(raw_patches)} raw patch repositories")

            logging.info("Filtering patch repositories...")
            patches = self._appstore_service.filter_patch_repos_only(raw_patches)
            logging.info(f"Filtered to {len(patches)} actual patches")

            logging.info("Updating cache...")
            self._cache_service.update_cache(plugins, patches)
            logging.info("Cache update completed")

            self.finished.emit(True, plugins, patches, "")
        except Exception as exc:
            logger.exception("Error while fetching data")
            self.finished.emit(False, [], [], str(exc))


class DeviceDetectionWorker(QThread):
    """Background worker for KOReader device detection."""

    finished = pyqtSignal(object, str)

    def __init__(self, device_detection_service: Any):
        super().__init__()
        self._service = device_detection_service

    def run(self):
        try:
            logging.info("Starting KOReader device detection")
            path_or_paths = self._service.detect_koreader_device()
            self.finished.emit(path_or_paths, "")
        except Exception as exc:
            logger.exception("Error during device detection")
            self.finished.emit(None, str(exc))


class AppUpdateWorker(QThread):
    """Background worker that checks for a newer KoStore release on GitHub."""

    # Emits (has_update, latest_version, html_url)
    finished = pyqtSignal(bool, str, str)

    def __init__(self, appstore_service: Any, current_version: str):
        super().__init__()
        self._appstore_service = appstore_service
        self._current_version = current_version

    def run(self):
        try:
            result = self._appstore_service.check_app_update(self._current_version)
            if result:
                self.finished.emit(True, result["latest_version"], result["html_url"])
            else:
                self.finished.emit(False, "", "")
        except Exception as exc:
            logger.warning("App update check failed: %s", exc)
            self.finished.emit(False, "", "")


def find_plugin_root(base: Path) -> Path | None:
    """Find the root directory of a plugin within the given base path."""
    if (base / "main.lua").exists() and (base / "_meta.lua").exists():
        logger.info(f"Found plugin in root directory: {base}")
        return base

    for root, _dirs, files in os.walk(base):
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

    def __init__(self, api, item_data, install_path, item_type="plugin", is_update=False, installer=None):
        super().__init__()
        self.api = api
        self.item_data = item_data
        self.install_path = install_path
        self.item_type = item_type
        self.is_update = is_update
        # PluginInstaller handles both SFTP (SSH) and local filesystem writes.
        # When present, use it so remote installs don't hit the local disk.
        self.installer = installer

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

                self.progress.emit("Installing...")

                if self.installer is not None:
                    result = self.installer.install_plugin_from_zip(
                        zip_content,
                        repo,
                        progress_callback=self._emit_upload_progress,
                    )
                    if result["success"]:
                        verb = "updated" if self.is_update else "installed"
                        self.finished.emit(True, f"{repo} {verb} successfully!")
                    else:
                        self.finished.emit(False, result["message"])
                    return

                # Fallback: no installer supplied — write to a local path.
                temp_dir = Path(tempfile.mkdtemp(prefix="koreader_store_"))
                zip_path = temp_dir / f"{repo}.zip"

                with open(zip_path, "wb") as f:
                    f.write(zip_content)

                self.progress.emit("Extracting...")
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

                self.progress.emit("Analyzing plugin structure...")

                plugin_dir = find_plugin_root(temp_dir)

                if not plugin_dir:
                    self.finished.emit(
                        False,
                        "No valid plugin structure found (main.lua/_meta.lua missing)",
                    )
                    return

                # Derive a stable folder name from the repo, not the
                # zipball root (which is "<owner>-<repo>-<sha>").
                plugin_name = derive_plugin_folder_name(plugin_dir.name, repo)

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
                patches = self.api.get_patch_files(owner, repo)
                if not patches:
                    self.finished.emit(False, "No patches found")
                    return

                self.progress.emit("Downloading patches...")

                if self.installer is not None:
                    result = self.installer.install_patches(patches)
                    if result["success"]:
                        self.finished.emit(True, result["message"])
                    else:
                        self.finished.emit(False, result["message"])
                    return

                # Fallback: no installer supplied — write to a local path.
                patch_dir = Path(self.install_path) / "patches"
                patch_dir.mkdir(exist_ok=True)

                for patch in patches:
                    response = requests.get(patch["download_url"], timeout=10)
                    patch_file = patch_dir / patch["name"]
                    with open(patch_file, "w", encoding="utf-8") as f:
                        f.write(response.text)

                self.finished.emit(True, f"{len(patches)} patch(es) installed!")

        except Exception as e:
            logger.error(f"Error during installation: {e}")
            self.finished.emit(False, f"Error: {str(e)}")
        finally:
            if "temp_dir" in locals() and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to cleanup temporary directory {temp_dir}: {cleanup_error}"
                    )

    def _emit_upload_progress(self, done, total):
        """Relay per-file install progress to the progress dialog."""
        self.progress.emit(f"Installing... ({done}/{total})")
