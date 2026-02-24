"""
SSH/SFTP connection service for wireless KOReader device connections.

Uses paramiko (pure-Python SSH) instead of SSHFS, which eliminates:
  - SSHFS-Win installation requirement
  - "Connection reset by peer" caused by OpenSSH <-> Dropbear cipher mismatches
  - All platform-specific mount/unmount complexity

Install dependency:
    pip install paramiko

KOReader must have its SSH plugin enabled (default port 2222, user 'root').
"""

from __future__ import annotations

import logging
import os
import socket
import stat
from pathlib import PurePosixPath
from typing import Iterator

logger = logging.getLogger(__name__)

try:
    import paramiko
except ImportError:
    raise ImportError(
        "paramiko is required for SSH connections.\n"
        "Install it with:  pip install paramiko"
    ) from None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ConnectionError(OSError):
    """Raised when the SSH/SFTP connection cannot be established."""


class NotConnectedError(RuntimeError):
    """Raised when an SFTP operation is attempted without an active connection."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SSHConnectionService:
    """
    Manages an SFTP session to a KOReader device over its built-in SSH plugin.

    KOReader's Dropbear SSH server usually requires NO password (auth method
    "none").  This class handles that automatically, falling back to password
    or key auth when needed.

    Basic usage::

        svc = SSHConnectionService()
        svc.connect("192.168.1.42")          # no password needed by default

        for name in svc.listdir("/mnt/us"):
            print(name)

        svc.get("/mnt/us/koreader/settings.reader.lua", "settings.reader.lua")
        svc.put("plugin.zip", "/mnt/us/koreader/plugins/plugin.zip")
        svc.disconnect()

    Or as a context manager::

        with SSHConnectionService() as svc:
            svc.connect("192.168.1.42")
            print(svc.get_koreader_path())
    """

    # Algorithms supported by Dropbear. Paramiko will negotiate the best
    # common option automatically when the transport is started.
    _PREFERRED_CIPHERS = [
        "aes128-ctr", "aes256-ctr",
        "aes128-cbc", "aes256-cbc",
        "3des-cbc",
    ]
    _PREFERRED_MACS = [
        "hmac-sha2-256", "hmac-sha2-512",
        "hmac-sha1",
    ]
    _PREFERRED_KEX = [
        "curve25519-sha256", "curve25519-sha256@libssh.org",
        "ecdh-sha2-nistp256", "ecdh-sha2-nistp384",
        "diffie-hellman-group14-sha256",
        "diffie-hellman-group14-sha1",
        "diffie-hellman-group1-sha1",
    ]
    _PREFERRED_PUBKEYS = [
        "ecdsa-sha2-nistp256", "ecdsa-sha2-nistp384",
        "ssh-rsa", "ssh-dss",
    ]

    def __init__(self) -> None:
        self._transport: paramiko.Transport | None = None
        self._sftp: paramiko.SFTPClient | None = None
        self._host: str = ""
        self._remote_root: str = "/mnt/us"

    # ------------------------------------------------------------------
    # Context-manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "SSHConnectionService":
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(
        self,
        host: str,
        port: int = 2222,
        user: str = "root",
        remote_path: str = "/mnt/us",
        password: str | None = None,
        key_path: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        """
        Open an SSH connection and start an SFTP session.

        Authentication is attempted in this order:
          1. ``none``   — works with the default KOReader SSH plugin config
          2. password   — if *password* is provided
          3. public-key — if *key_path* is provided, or keys are in ~/.ssh

        Parameters
        ----------
        host:
            IP address or hostname of the KOReader device.
        port:
            SSH port (KOReader default: 2222).
        user:
            SSH username (KOReader default: 'root').
        remote_path:
            Root path on the device to use as the working base.
        password:
            SSH password, if one is set in KOReader's SSH plugin settings.
            Leave as None if no password is configured (the default).
        key_path:
            Path to a private key file for public-key auth (optional).
        timeout:
            TCP connect / auth timeout in seconds.
        """
        self.disconnect()

        self._remote_root = remote_path.rstrip("/") or "/"
        self._host = host

        logger.info("Connecting to %s@%s:%d …", user, host, port)

        # ------------------------------------------------------------------
        # 1. Open a raw TCP socket and start the SSH transport ourselves.
        #    This lets us control algorithm negotiation before any auth
        #    attempt, and lets us try auth_none() first — which is what
        #    KOReader's default Dropbear config requires.
        # ------------------------------------------------------------------
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
        except OSError as exc:
            raise ConnectionError(
                f"Could not reach {host}:{port}: {exc}\n\n"
                "Checklist:\n"
                "  • Device and computer are on the same Wi-Fi network\n"
                "  • KOReader's SSH plugin is enabled and started\n"
                "  • The IP address and port are correct"
            ) from exc

        transport = paramiko.Transport(sock)

        # Set preferred algorithms BEFORE the key exchange.
        # We filter each list against what THIS paramiko build actually supports
        # to avoid KeyErrors from optional algorithms (e.g. curve25519 requires
        # the cryptography package's curve25519 support to be present).
        def _filter(wanted: list, available: dict | list) -> list:
            keys = set(available) if isinstance(available, dict) else set(available)
            return [a for a in wanted if a in keys] or list(available)

        transport._preferred_ciphers = _filter(self._PREFERRED_CIPHERS, transport._preferred_ciphers)
        transport._preferred_macs    = _filter(self._PREFERRED_MACS,    transport._preferred_macs)
        transport._preferred_keys    = _filter(self._PREFERRED_PUBKEYS, transport._preferred_keys)
        transport._preferred_kex     = _filter(self._PREFERRED_KEX,     transport._preferred_kex)

        try:
            transport.start_client(timeout=timeout)
        except paramiko.SSHException as exc:
            transport.close()
            sock.close()
            raise ConnectionError(
                f"SSH handshake failed with {host}:{port}: {exc}\n"
                "Make sure KOReader's SSH plugin is running."
            ) from exc

        # Skip host-key verification (KOReader generates a fresh key on every
        # boot; there is nothing useful to check against).
        # transport.get_remote_server_key() can be logged here if desired.

        # ------------------------------------------------------------------
        # 2. Authenticate — try each method in turn, stop on first success.
        # ------------------------------------------------------------------
        self._authenticate(transport, user, password, key_path)

        # ------------------------------------------------------------------
        # 3. Open SFTP channel.
        # ------------------------------------------------------------------
        try:
            sftp = transport.open_sftp_client()
            if sftp is None:
                raise paramiko.SSHException("Server refused SFTP subsystem")
        except paramiko.SSHException as exc:
            transport.close()
            raise ConnectionError(f"Could not open SFTP channel: {exc}") from exc

        self._transport = transport
        self._sftp = sftp
        logger.info("SFTP session open. Remote root: %s", self._remote_root)

    # ------------------------------------------------------------------

    def _authenticate(
        self,
        transport: paramiko.Transport,
        user: str,
        password: str | None,
        key_path: str | None,
    ) -> None:
        """
        Try auth methods in order until one succeeds.
        Raises ConnectionError if every method fails.
        """
        host = self._host
        allowed: list[str] = []  # filled in by the server on first rejection

        # --- Method 1: none (KOReader default — no password configured) ---
        try:
            transport.auth_none(user)
            logger.info("Authenticated via 'none'")
            return
        except paramiko.BadAuthenticationType as exc:
            # Server rejected none-auth and told us what it does accept.
            allowed = list(exc.allowed_types)
            logger.info("Server requires one of: %s", allowed)
        except paramiko.AuthenticationException:
            logger.debug("auth_none rejected without allowed-types hint")

        # --- Method 2: empty-string password ---
        # KOReader "login without password" = Dropbear accepts password="" .
        # Always try this before requiring the caller to supply a password.
        if "password" in allowed:
            try:
                transport.auth_password(user, password or "")
                logger.info("Authenticated via %s", "password" if password else "empty-string password")
                return
            except paramiko.AuthenticationException:
                if not password:
                    logger.debug("Empty-string password rejected — a real password is required")
                else:
                    raise ConnectionError(
                        f"Password authentication failed for {user}@{host}.\n"
                        "Check the password set in KOReader's SSH plugin settings."
                    )

        # --- Method 3: public key ---
        pkey: paramiko.PKey | None = None
        if key_path:
            try:
                pkey = self._load_private_key(key_path)
            except Exception as exc:
                raise ConnectionError(f"Could not load private key '{key_path}': {exc}") from exc

        if pkey is None:
            pkey = self._find_default_key()

        if pkey is not None:
            try:
                transport.auth_publickey(user, pkey)
                logger.info("Authenticated via public key")
                return
            except paramiko.AuthenticationException:
                logger.debug("Public-key auth rejected")

        # --- Nothing worked — give the user actionable info ---
        allowed_str = ", ".join(allowed) if allowed else "unknown"
        raise ConnectionError(
            f"Could not authenticate as {user}@{host}.\n"
            f"Server accepted methods: {allowed_str}\n\n"
            + (
                "The device requires a password but none was provided.\n"
                "Pass password= to connect(), matching what is set in KOReader's SSH plugin."
                if "password" in allowed and password is None
                else
                "The device requires a public key but none was found.\n"
                "Pass key_path= to connect(), or add a key to ~/.ssh/."
                if "publickey" in allowed
                else
                "Tips:\n"
                "  • If you set a password in KOReader's SSH plugin, pass it to connect()\n"
                "  • If no password is set, restart the SSH plugin on the device and retry"
            )
        )

    # ------------------------------------------------------------------

    def disconnect(self) -> None:
        """Close the SFTP session and underlying SSH transport."""
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None

        if self._transport:
            try:
                self._transport.close()
            except Exception:
                pass
            self._transport = None

        self._host = ""

    def is_connected(self) -> bool:
        """Return True if there is an active SSH/SFTP connection."""
        return (
            self._transport is not None
            and self._transport.is_active()
            and self._sftp is not None
        )

    # ------------------------------------------------------------------
    # SFTP file operations
    # ------------------------------------------------------------------

    def listdir(self, remote_path: str | None = None) -> list[str]:
        """Return filenames in *remote_path* (default: remote root)."""
        return self._sftp_op().listdir(self._resolve(remote_path))

    def listdir_attr(self, remote_path: str | None = None) -> list[paramiko.SFTPAttributes]:
        """Like listdir() but returns SFTPAttributes (name, size, mtime, …)."""
        return self._sftp_op().listdir_attr(self._resolve(remote_path))

    def get(
        self,
        remote_path: str,
        local_path: str | os.PathLike,
        callback: "callable[[int, int], None] | None" = None,
    ) -> None:
        """Download *remote_path* to the local *local_path*."""
        remote = self._resolve(remote_path)
        logger.debug("GET %s → %s", remote, local_path)
        self._sftp_op().get(remote, str(local_path), callback=callback)

    def put(
        self,
        local_path: str | os.PathLike,
        remote_path: str,
        callback: "callable[[int, int], None] | None" = None,
    ) -> paramiko.SFTPAttributes:
        """Upload *local_path* to *remote_path*. Returns remote file attributes."""
        remote = self._resolve(remote_path)
        logger.debug("PUT %s → %s", local_path, remote)
        return self._sftp_op().put(str(local_path), remote, callback=callback, confirm=True)

    def read_bytes(self, remote_path: str) -> bytes:
        """Return the full contents of a remote file as bytes."""
        with self._sftp_op().open(self._resolve(remote_path), "rb") as fh:
            return fh.read()

    def write_bytes(self, remote_path: str, data: bytes) -> None:
        """Overwrite (or create) a remote file with raw *data*."""
        with self._sftp_op().open(self._resolve(remote_path), "wb") as fh:
            fh.write(data)

    def makedirs(self, remote_path: str) -> None:
        """
        Create *remote_path* and all missing parent directories.
        Does not raise an error if the path already exists.
        """
        sftp = self._sftp_op()
        parts = PurePosixPath(self._resolve(remote_path)).parts
        current = ""
        for part in parts:
            current = str(PurePosixPath(current) / part) if current else part
            try:
                sftp.mkdir(current)
            except OSError:
                pass  # already exists

    def remove(self, remote_path: str) -> None:
        """Delete a remote file."""
        self._sftp_op().remove(self._resolve(remote_path))

    def rename(self, old_path: str, new_path: str) -> None:
        """Rename / move a remote file or directory."""
        self._sftp_op().rename(self._resolve(old_path), self._resolve(new_path))

    def stat(self, remote_path: str) -> paramiko.SFTPAttributes:
        """Return attributes for *remote_path* (follows symlinks)."""
        return self._sftp_op().stat(self._resolve(remote_path))

    def exists(self, remote_path: str) -> bool:
        """Return True if *remote_path* exists on the device."""
        try:
            self.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def is_dir(self, remote_path: str) -> bool:
        """Return True if *remote_path* is a directory."""
        try:
            return stat.S_ISDIR(self.stat(remote_path).st_mode or 0)
        except (FileNotFoundError, TypeError):
            return False

    def walk(
        self, remote_path: str | None = None
    ) -> Iterator[tuple[str, list[str], list[str]]]:
        """
        os.walk()-style generator for the remote filesystem.
        Yields (dirpath, dirnames, filenames) tuples.
        """
        sftp = self._sftp_op()
        root = self._resolve(remote_path)

        def _walk(path: str) -> Iterator[tuple[str, list[str], list[str]]]:
            entries = sftp.listdir_attr(path)
            dirs, files = [], []
            for entry in entries:
                (dirs if stat.S_ISDIR(entry.st_mode or 0) else files).append(entry.filename)
            yield path, dirs, files
            for d in dirs:
                yield from _walk(f"{path}/{d}")

        yield from _walk(root)

    # ------------------------------------------------------------------
    # KOReader-specific helpers
    # ------------------------------------------------------------------

    def get_koreader_path(self) -> str | None:
        """
        Find the KOReader installation directory on the connected device.
        Returns the remote path containing 'plugins/', or None if not found.
        """
        if not self.is_connected():
            return None

        candidates = [
            "koreader",               # Kindle and most generic devices
            ".adds/koreader",         # Kobo
            "applications/koreader",  # Some Android variants
        ]
        for rel in candidates:
            candidate = f"{self._remote_root}/{rel}"
            if self.is_dir(f"{candidate}/plugins"):
                logger.debug("KOReader found at %s", candidate)
                return candidate

        logger.warning("KOReader directory not found under %s", self._remote_root)
        return None

    def exec_command(
        self, command: str, timeout: float = 10.0
    ) -> tuple[int, str, str]:
        """
        Run a shell command on the device.
        Returns (exit_code, stdout_text, stderr_text).
        """
        if not self._transport or not self.is_connected():
            raise NotConnectedError("Not connected. Call connect() first.")
        channel = self._transport.open_session()
        channel.settimeout(timeout)
        channel.exec_command(command)
        exit_code = channel.recv_exit_status()
        stdout = channel.makefile("rb").read().decode(errors="replace")
        stderr = channel.makefile_stderr("rb").read().decode(errors="replace")
        channel.close()
        return exit_code, stdout, stderr

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sftp_op(self) -> paramiko.SFTPClient:
        if not self._sftp or not self.is_connected():
            raise NotConnectedError("Not connected. Call connect() first.")
        return self._sftp

    def _resolve(self, path: str | None) -> str:
        """Resolve *path* relative to the remote root."""
        if not path:
            return self._remote_root
        if path.startswith("/"):
            return path
        return f"{self._remote_root}/{path}"

    @staticmethod
    def _load_private_key(key_path: str) -> paramiko.PKey:
        """Try loading a private key, auto-detecting the type."""
        for cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey):
            try:
                return cls.from_private_key_file(key_path)
            except paramiko.SSHException:
                continue
        raise ValueError(f"Unsupported or corrupt private key: {key_path!r}")

    @staticmethod
    def _find_default_key() -> paramiko.PKey | None:
        """Look for a usable private key in the default ~/.ssh location."""
        ssh_dir = os.path.expanduser("~/.ssh")
        for name in ("id_ed25519", "id_ecdsa", "id_rsa"):
            path = os.path.join(ssh_dir, name)
            if os.path.exists(path):
                try:
                    return SSHConnectionService._load_private_key(path)
                except Exception:
                    continue
        return None

    # Backwards-compatibility alias
    def unmount(self) -> None:
        """Alias for disconnect() — kept for backwards compatibility."""
        self.disconnect()