"""
Connection diagnostics and testing service for SSH connections.
Provides detailed connection status and troubleshooting information.
"""

import logging
import socket
import time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DiagnosticResult:
    """Result of a diagnostic test."""
    
    def __init__(self, name: str, success: bool, message: str, details: Optional[str] = None):
        self.name = name
        self.success = success
        self.message = message
        self.details = details
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "success": self.success,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


class ConnectionDiagnostics:
    """Provides comprehensive connection diagnostics for SSH connections."""
    
    def __init__(self):
        self.results: List[DiagnosticResult] = []
    
    def run_full_diagnostics(
        self,
        host: str,
        port: int = 2222,
        user: str = "root",
        password: Optional[str] = None,
        timeout: float = 10.0
    ) -> List[DiagnosticResult]:
        """Run full diagnostic suite."""
        self.results = []
        
        # Test 1: DNS resolution
        self._test_dns_resolution(host)
        
        # Test 2: TCP connectivity
        self._test_tcp_connectivity(host, port, timeout)
        
        # Test 3: SSH protocol support
        self._test_ssh_protocol(host, port, timeout)
        
        # Test 4: Authentication methods
        self._test_authentication_methods(host, port, user, password, timeout)
        
        # Test 5: SFTP subsystem
        self._test_sftp_subsystem(host, port, user, password, timeout)
        
        # Test 6: KOReader path discovery
        self._test_koreader_path(host, port, user, password, timeout)
        
        return self.results
    
    def _test_dns_resolution(self, host: str) -> None:
        """Test DNS resolution."""
        try:
            import socket
            socket.gethostbyname(host)
            self.results.append(DiagnosticResult(
                "DNS Resolution",
                True,
                f"Successfully resolved {host}",
                f"Host {host} resolves to {socket.gethostbyname(host)}"
            ))
        except socket.gaierror as e:
            self.results.append(DiagnosticResult(
                "DNS Resolution",
                False,
                f"Failed to resolve {host}",
                str(e)
            ))
    
    def _test_tcp_connectivity(self, host: str, port: int, timeout: float) -> None:
        """Test TCP connectivity."""
        try:
            start_time = time.time()
            sock = socket.create_connection((host, port), timeout=timeout)
            end_time = time.time()
            
            sock.close()
            latency = (end_time - start_time) * 1000  # Convert to ms
            
            self.results.append(DiagnosticResult(
                "TCP Connectivity",
                True,
                f"Connected to {host}:{port} in {latency:.0f}ms",
                f"Connection successful, latency: {latency:.2f}ms"
            ))
        except (OSError, socket.timeout) as e:
            self.results.append(DiagnosticResult(
                "TCP Connectivity",
                False,
                f"Cannot connect to {host}:{port}",
                f"Error: {e}"
            ))
    
    def _test_ssh_protocol(self, host: str, port: int, timeout: float) -> None:
        """Test SSH protocol support."""
        try:
            import paramiko
            
            sock = socket.create_connection((host, port), timeout=timeout)
            transport = paramiko.Transport(sock)
            
            try:
                transport.start_client(timeout=timeout)
                server_key = transport.get_remote_server_key()
                
                self.results.append(DiagnosticResult(
                    "SSH Protocol",
                    True,
                    f"SSH handshake successful",
                    f"Server key type: {server_key.get_name()}, fingerprint: {server_key.get_fingerprint().hex()[:16]}..."
                ))
            finally:
                transport.close()
                sock.close()
                
        except ImportError:
            self.results.append(DiagnosticResult(
                "SSH Protocol",
                False,
                "Paramiko not available",
                "Install paramiko to test SSH protocol"
            ))
        except Exception as e:
            self.results.append(DiagnosticResult(
                "SSH Protocol",
                False,
                "SSH handshake failed",
                str(e)
            ))
    
    def _test_authentication_methods(
        self, host: str, port: int, user: str, password: Optional[str], timeout: float
    ) -> None:
        """Test available authentication methods."""
        try:
            import paramiko
            
            sock = socket.create_connection((host, port), timeout=timeout)
            transport = paramiko.Transport(sock)
            
            try:
                transport.start_client(timeout=timeout)
                
                # Test 'none' authentication
                try:
                    transport.auth_none(user)
                    self.results.append(DiagnosticResult(
                        "Authentication",
                        True,
                        "No-password authentication successful",
                        "KOReader SSH plugin default configuration"
                    ))
                    return
                except paramiko.BadAuthenticationType as e:
                    allowed_methods = list(e.allowed_types)
                    
                    # Test password authentication if password provided
                    if "password" in allowed_methods and password:
                        try:
                            transport.auth_password(user, password)
                            self.results.append(DiagnosticResult(
                                "Authentication",
                                True,
                                "Password authentication successful",
                                f"Allowed methods: {', '.join(allowed_methods)}"
                            ))
                            return
                        except paramiko.AuthenticationException:
                            pass
                    
                    self.results.append(DiagnosticResult(
                        "Authentication",
                        False,
                        "Authentication failed",
                        f"Allowed methods: {', '.join(allowed_methods)}"
                    ))
                    
            finally:
                transport.close()
                sock.close()
                
        except ImportError:
            self.results.append(DiagnosticResult(
                "Authentication",
                False,
                "Paramiko not available",
                "Install paramiko to test authentication"
            ))
        except Exception as e:
            self.results.append(DiagnosticResult(
                "Authentication",
                False,
                "Authentication test failed",
                str(e)
            ))
    
    def _test_sftp_subsystem(
        self, host: str, port: int, user: str, password: Optional[str], timeout: float
    ) -> None:
        """Test SFTP subsystem availability."""
        try:
            import paramiko
            from services.ssh_connection import SSHConnectionService
            
            # Use the existing SSH service for consistency
            ssh_service = SSHConnectionService()
            ssh_service.connect(host, port, user, password=password, timeout=timeout)
            
            try:
                # Test basic SFTP operation
                files = ssh_service.listdir("/")
                self.results.append(DiagnosticResult(
                    "SFTP Subsystem",
                    True,
                    "SFTP connection successful",
                    f"Root directory contains {len(files)} items"
                ))
            finally:
                ssh_service.disconnect()
                
        except Exception as e:
            self.results.append(DiagnosticResult(
                "SFTP Subsystem",
                False,
                "SFTP connection failed",
                str(e)
            ))
    
    def _test_koreader_path(
        self, host: str, port: int, user: str, password: Optional[str], timeout: float
    ) -> None:
        """Test KOReader installation discovery."""
        try:
            import paramiko
            from services.ssh_connection import SSHConnectionService
            
            ssh_service = SSHConnectionService()
            ssh_service.connect(host, port, user, password=password, timeout=timeout)
            
            try:
                koreader_path = ssh_service.get_koreader_path()
                if koreader_path:
                    # Test plugins directory
                    plugins_path = f"{koreader_path}/plugins"
                    if ssh_service.is_dir(plugins_path):
                        plugins = ssh_service.listdir(plugins_path)
                        self.results.append(DiagnosticResult(
                            "KOReader Installation",
                            True,
                            f"KOReader found at {koreader_path}",
                            f"Plugins directory contains {len(plugins)} plugins"
                        ))
                    else:
                        self.results.append(DiagnosticResult(
                            "KOReader Installation",
                            True,
                            f"KOReader found at {koreader_path}",
                            "But plugins directory is missing"
                        ))
                else:
                    self.results.append(DiagnosticResult(
                        "KOReader Installation",
                        False,
                        "KOReader installation not found",
                        "Checked common locations: koreader, .adds/koreader, applications/koreader"
                    ))
            finally:
                ssh_service.disconnect()
                
        except Exception as e:
            self.results.append(DiagnosticResult(
                "KOReader Installation",
                False,
                "KOReader detection failed",
                str(e)
            ))
    
    def get_summary(self) -> Dict:
        """Get diagnostic summary."""
        if not self.results:
            return {"status": "not_run", "passed": 0, "failed": 0, "total": 0}
        
        passed = sum(1 for r in self.results if r.success)
        failed = len(self.results) - passed
        
        status = "passed" if failed == 0 else "failed" if passed == 0 else "partial"
        
        return {
            "status": status,
            "passed": passed,
            "failed": failed,
            "total": len(self.results),
            "results": [r.to_dict() for r in self.results]
        }
    
    def get_troubleshooting_tips(self) -> List[str]:
        """Get troubleshooting tips based on failed tests."""
        tips = []
        
        for result in self.results:
            if not result.success:
                if result.name == "DNS Resolution":
                    tips.append("• Check the device IP address - make sure there are no typos")
                    tips.append("• Ensure your device is connected to the same WiFi network")
                elif result.name == "TCP Connectivity":
                    tips.append("• Verify KOReader's SSH plugin is enabled and started")
                    tips.append("• Check that port 2222 (or your custom port) is not blocked by firewall")
                    tips.append("• Try restarting the SSH plugin on your device")
                elif result.name == "SSH Protocol":
                    tips.append("• The device might be running a different SSH server")
                    tips.append("• Try restarting KOReader or the SSH plugin")
                elif result.name == "Authentication":
                    tips.append("• If you set a password in KOReader, make sure to enter it here")
                    tips.append("• Try restarting the SSH plugin on your device")
                    tips.append("• Check if your device requires a specific authentication method")
                elif result.name == "SFTP Subsystem":
                    tips.append("• Your SSH server might not support SFTP")
                    tips.append("• Try restarting KOReader completely")
                elif result.name == "KOReader Installation":
                    tips.append("• Check that KOReader is properly installed on your device")
                    tips.append("• Verify the remote path points to the correct location")
                    tips.append("• Common paths: /mnt/us, /mnt/onboard, .adds/koreader")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tips = []
        for tip in tips:
            if tip not in seen:
                seen.add(tip)
                unique_tips.append(tip)
        
        return unique_tips
