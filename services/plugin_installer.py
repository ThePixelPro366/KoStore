"""
Plugin installation service for KOReader Store.

Works in two modes:
  - SSH / wireless: pass an active SSHConnectionService as `ssh`.
    All file operations go over SFTP to the device.
  - USB / wired:   leave `ssh` as None. koreader_path must be a real
    local path (e.g. "G:\\.adds\\koreader"). Local filesystem ops are used.
"""

import io
import logging
import re
import shutil
import stat as _stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginInstaller:
    """
    Installs, uninstalls, and lists KOReader plugins and patches.

    Parameters
    ----------
    koreader_path:
        Path to the KOReader directory.  Remote SFTP path when using SSH,
        local filesystem path when connected via USB.
    ssh:
        Active ``SSHConnectionService`` instance, or ``None`` for USB mode.
    """

    def __init__(self, koreader_path: str, ssh=None) -> None:
        self._ssh = ssh

        if ssh is not None:
            # SSH / wireless — POSIX remote paths
            self.koreader_path = koreader_path.rstrip("/")
            self.plugins_path  = f"{self.koreader_path}/plugins"
            self.patches_path  = f"{self.koreader_path}/patches"
        else:
            # USB / local — native OS paths via pathlib
            self.koreader_path = str(koreader_path)
            self.plugins_path  = str(Path(koreader_path) / "plugins")
            self.patches_path  = str(Path(koreader_path) / "patches")

        logger.info(
            "Initializing plugin installer for %s (mode: %s)",
            koreader_path, "SSH" if ssh else "USB",
        )

        if ssh is not None:
            ssh.makedirs(self.plugins_path)
            ssh.makedirs(self.patches_path)
        else:
            Path(self.plugins_path).mkdir(parents=True, exist_ok=True)
            Path(self.patches_path).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Install plugin
    # ------------------------------------------------------------------

    def install_plugin_from_zip(
        self, zip_content: bytes, repo_name: str
    ) -> Dict[str, Any]:
        """
        Install a plugin from raw ZIP bytes.

        The ZIP is extracted locally into a temp directory, the plugin
        folder is identified, then files are either uploaded via SFTP
        (SSH mode) or copied locally (USB mode).
        """
        result: Dict[str, Any] = {
            "success": False,
            "message": "",
            "plugin_name": "",
            "plugin_path": "",
        }

        tmp = tempfile.mkdtemp(prefix="kostore_")
        try:
            tmp_path = Path(tmp)

            try:
                with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
                    zf.extractall(tmp_path)
            except zipfile.BadZipFile as exc:
                result["message"] = f"Invalid ZIP file: {exc}"
                return result

            plugin_dir = self._find_plugin_directory(tmp_path)
            if not plugin_dir:
                result["message"] = (
                    "No valid plugin structure found "
                    "(expected main.lua + _meta.lua inside the ZIP)"
                )
                return result

            plugin_name = plugin_dir.name
            if not plugin_name.endswith(".koplugin"):
                plugin_name = f"{plugin_name}.koplugin"

            dest = f"{self.plugins_path}/{plugin_name}"

            if self._ssh is not None:
                if self._ssh.is_dir(dest):
                    logger.info("Removing existing plugin: %s", dest)
                    self._sftp_rmtree(dest)
                logger.info("Uploading plugin to: %s", dest)
                self._sftp_upload_tree(plugin_dir, dest)
            else:
                dest_path = Path(dest)
                if dest_path.exists():
                    logger.info("Removing existing plugin: %s", dest_path)
                    shutil.rmtree(dest_path)
                logger.info("Copying plugin to: %s", dest_path)
                shutil.copytree(plugin_dir, dest_path)

            result.update(
                success=True,
                message=f"{repo_name} installed successfully!",
                plugin_name=plugin_name,
                plugin_path=dest,
            )
            logger.info("Successfully installed plugin: %s", plugin_name)

        except Exception as exc:
            logger.error("Error installing plugin %s: %s", repo_name, exc)
            result["message"] = f"Error: {exc}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        return result

    # ------------------------------------------------------------------
    # Install patches
    # ------------------------------------------------------------------

    def install_patches(self, patches: List[Dict[str, str]]) -> Dict[str, Any]:
        """Download and install patch files onto the device."""
        result: Dict[str, Any] = {
            "success": False,
            "message": "",
            "installed_patches": [],
        }

        try:
            import requests

            installed = 0
            for patch in patches:
                patch_name = patch["name"]
                url        = patch["download_url"]

                logger.info("Downloading patch: %s", patch_name)
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()

                dest = f"{self.patches_path}/{patch_name}"
                if self._ssh is not None:
                    self._ssh.write_bytes(dest, resp.content)
                else:
                    Path(dest).write_bytes(resp.content)

                result["installed_patches"].append(patch_name)
                installed += 1

            result.update(
                success=True,
                message=f"{installed} patch(es) installed successfully!",
            )
            logger.info("Installed %d patches", installed)

        except Exception as exc:
            logger.error("Error installing patches: %s", exc)
            result["message"] = f"Error: {exc}"

        return result

    # ------------------------------------------------------------------
    # Uninstall
    # ------------------------------------------------------------------

    def uninstall_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """Remove a plugin from the device."""
        result: Dict[str, Any] = {"success": False, "message": ""}

        if not plugin_name.endswith(".koplugin"):
            plugin_name = f"{plugin_name}.koplugin"

        dest = f"{self.plugins_path}/{plugin_name}"

        try:
            if self._ssh is not None:
                if not self._ssh.is_dir(dest):
                    result["message"] = f"Plugin {plugin_name} is not installed"
                    return result
                logger.info("Uninstalling plugin: %s", dest)
                self._sftp_rmtree(dest)
            else:
                dest_path = Path(dest)
                if not dest_path.exists():
                    result["message"] = f"Plugin {plugin_name} is not installed"
                    return result
                logger.info("Uninstalling plugin: %s", dest_path)
                shutil.rmtree(dest_path)

            result.update(
                success=True,
                message=f"{plugin_name} uninstalled successfully!",
            )
            logger.info("Successfully uninstalled: %s", plugin_name)

        except Exception as exc:
            logger.error("Error uninstalling %s: %s", plugin_name, exc)
            result["message"] = f"Error: {exc}"

        return result

    # ------------------------------------------------------------------
    # List installed
    # ------------------------------------------------------------------

    def get_installed_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Return a dict of installed plugins keyed by plugin folder name."""
        plugins: Dict[str, Dict[str, Any]] = {}

        try:
            if self._ssh is not None:
                for entry in self._ssh.listdir_attr(self.plugins_path):
                    if not _stat.S_ISDIR(entry.st_mode or 0):
                        continue
                    name = entry.filename
                    if not name.endswith(".koplugin"):
                        continue
                    plugin_path = f"{self.plugins_path}/{name}"
                    meta_path   = f"{plugin_path}/_meta.lua"
                    has_meta    = self._ssh.exists(meta_path)
                    version     = "Unknown"
                    if has_meta:
                        try:
                            raw = self._ssh.read_bytes(meta_path).decode(errors="replace")
                            m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', raw)
                            if m:
                                version = m.group(1)
                        except Exception as exc:
                            logger.warning("Could not read metadata for %s: %s", name, exc)
                    plugins[name] = {
                        "name": name, "path": plugin_path,
                        "version": version, "has_meta": has_meta,
                    }
            else:
                for d in Path(self.plugins_path).glob("*.koplugin"):
                    if not d.is_dir():
                        continue
                    name     = d.name
                    meta_p   = d / "_meta.lua"
                    has_meta = meta_p.exists()
                    version  = "Unknown"
                    if has_meta:
                        try:
                            raw = meta_p.read_text(encoding="utf-8", errors="replace")
                            m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', raw)
                            if m:
                                version = m.group(1)
                        except Exception as exc:
                            logger.warning("Could not read metadata for %s: %s", name, exc)
                    plugins[name] = {
                        "name": name, "path": str(d),
                        "version": version, "has_meta": has_meta,
                    }

        except Exception as exc:
            logger.error("Error listing installed plugins: %s", exc)

        return plugins

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_plugin_directory(self, search_dir: Path) -> Optional[Path]:
        """Find the plugin folder inside a locally-extracted ZIP tree."""
        # Best match: direct child with both main.lua and _meta.lua
        for d in search_dir.glob("*"):
            if d.is_dir() and (d / "main.lua").exists() and (d / "_meta.lua").exists():
                return d
        # Fallback: named *.koplugin anywhere in the tree
        for d in search_dir.rglob("*.koplugin"):
            if d.is_dir() and (d / "main.lua").exists():
                return d
        # Last resort: any direct child with main.lua
        for d in search_dir.glob("*"):
            if d.is_dir() and (d / "main.lua").exists():
                return d
        return None

    def _sftp_upload_tree(self, local_dir: Path, remote_dir: str) -> None:
        """Recursively upload a local directory tree via SFTP."""
        self._ssh.makedirs(remote_dir)
        for item in local_dir.iterdir():
            remote_item = f"{remote_dir}/{item.name}"
            if item.is_dir():
                self._sftp_upload_tree(item, remote_item)
            else:
                self._ssh.put(item, remote_item)

    def _sftp_rmtree(self, remote_path: str) -> None:
        """Recursively delete a remote directory tree via SFTP."""
        sftp = self._ssh._sftp_op()
        for entry in sftp.listdir_attr(remote_path):
            child = f"{remote_path}/{entry.filename}"
            if _stat.S_ISDIR(entry.st_mode or 0):
                self._sftp_rmtree(child)
            else:
                sftp.remove(child)
        sftp.rmdir(remote_path)