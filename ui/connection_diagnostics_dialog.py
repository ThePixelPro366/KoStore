"""
Connection diagnostics dialog for testing SSH connections.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QProgressBar, QMessageBox, QFormLayout,
    QLineEdit, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor

from services.connection_diagnostics import ConnectionDiagnostics, DiagnosticResult


class DiagnosticsWorker(QThread):
    """Background worker for running diagnostics."""
    
    result_ready = pyqtSignal(object)  # DiagnosticResult
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, diagnostics, host, port, user, password, timeout):
        super().__init__()
        self.diagnostics = diagnostics
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout
    
    def run(self):
        try:
            # Override the results list to emit results as they come
            original_results = self.diagnostics.results
            self.diagnostics.results = []
            
            # Run each test individually and emit results
            self.diagnostics._test_dns_resolution(self.host)
            if self.diagnostics.results:
                self.result_ready.emit(self.diagnostics.results[-1])
            
            self.diagnostics._test_tcp_connectivity(self.host, self.port, self.timeout)
            if self.diagnostics.results:
                self.result_ready.emit(self.diagnostics.results[-1])
            
            self.diagnostics._test_ssh_protocol(self.host, self.port, self.timeout)
            if self.diagnostics.results:
                self.result_ready.emit(self.diagnostics.results[-1])
            
            self.diagnostics._test_authentication_methods(
                self.host, self.port, self.user, self.password, self.timeout
            )
            if self.diagnostics.results:
                self.result_ready.emit(self.diagnostics.results[-1])
            
            self.diagnostics._test_sftp_subsystem(
                self.host, self.port, self.user, self.password, self.timeout
            )
            if self.diagnostics.results:
                self.result_ready.emit(self.diagnostics.results[-1])
            
            self.diagnostics._test_koreader_path(
                self.host, self.port, self.user, self.password, self.timeout
            )
            if self.diagnostics.results:
                self.result_ready.emit(self.diagnostics.results[-1])
            
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class ConnectionDiagnosticsDialog(QDialog):
    """Dialog for running and displaying connection diagnostics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection Diagnostics")
        self.setMinimumSize(700, 600)
        self.diagnostics = ConnectionDiagnostics()
        self.worker = None
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Connection settings group
        settings_group = QGroupBox("Connection Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("192.168.1.42")
        settings_layout.addRow("Device IP:", self.host_input)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(2222)
        settings_layout.addRow("Port:", self.port_input)
        
        self.user_input = QLineEdit()
        self.user_input.setText("root")
        settings_layout.addRow("Username:", self.user_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Leave empty if no password")
        settings_layout.addRow("Password:", self.password_input)
        
        layout.addWidget(settings_group)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 6)  # 6 diagnostic tests
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to run diagnostics")
        layout.addWidget(self.status_label)
        
        # Results text area
        results_group = QGroupBox("Diagnostic Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 9))
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
        # Troubleshooting tips
        self.tips_group = QGroupBox("Troubleshooting Tips")
        self.tips_layout = QVBoxLayout(self.tips_group)
        
        self.tips_text = QTextEdit()
        self.tips_text.setReadOnly(True)
        self.tips_text.setMaximumHeight(120)
        self.tips_layout.addWidget(self.tips_text)
        
        layout.addWidget(self.tips_group)
        self.tips_group.hide()  # Hide initially
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("Run Diagnostics")
        self.run_btn.clicked.connect(self._on_run_diagnostics)
        
        self.clear_btn = QPushButton("Clear Results")
        self.clear_btn.clicked.connect(self._on_clear_results)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _on_run_diagnostics(self):
        """Run connection diagnostics."""
        host = self.host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "Missing Information", 
                              "Please enter the device IP address.")
            return
        
        # Clear previous results
        self._on_clear_results()
        
        # Disable inputs during test
        self._set_inputs_enabled(False)
        self.run_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Running diagnostics...")
        
        # Start background worker
        self.worker = DiagnosticsWorker(
            self.diagnostics,
            host,
            self.port_input.value(),
            self.user_input.text().strip(),
            self.password_input.text(),
            10.0  # timeout
        )
        self.worker.result_ready.connect(self._on_result_ready)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_result_ready(self, result: DiagnosticResult):
        """Handle a diagnostic result."""
        # Update progress
        self.progress_bar.setValue(self.progress_bar.value() + 1)
        
        # Add result to text area
        status_icon = "✓" if result.success else "✗"
        self._append_result(f"{status_icon} {result.name}: {result.message}")
        
        if result.details:
            self._append_result(f"   Details: {result.details}", indent=4)
        
        # Scroll to bottom
        cursor = self.results_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.results_text.setTextCursor(cursor)
    
    def _on_finished(self):
        """Handle diagnostics completion."""
        self._set_inputs_enabled(True)
        self.run_btn.setEnabled(True)
        
        summary = self.diagnostics.get_summary()
        self.status_label.setText(
            f"Diagnostics complete: {summary['passed']}/{summary['total']} tests passed"
        )
        
        # Show troubleshooting tips if there were failures
        if summary['failed'] > 0:
            tips = self.diagnostics.get_troubleshooting_tips()
            if tips:
                self.tips_text.setPlainText("\n".join(tips))
                self.tips_group.show()
    
    def _on_error(self, error_msg: str):
        """Handle diagnostic error."""
        self._append_result(f"✗ Error: {error_msg}")
        self.status_label.setText("Diagnostics failed with error")
        self._set_inputs_enabled(True)
        self.run_btn.setEnabled(True)
    
    def _on_clear_results(self):
        """Clear diagnostic results."""
        self.results_text.clear()
        self.tips_text.clear()
        self.tips_group.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready to run diagnostics")
    
    def _append_result(self, text: str, indent: int = 0):
        """Append text to results with optional indentation."""
        if indent > 0:
            text = " " * indent + text
        self.results_text.append(text)
    
    def _set_inputs_enabled(self, enabled: bool):
        """Enable/disable input fields."""
        self.host_input.setEnabled(enabled)
        self.port_input.setEnabled(enabled)
        self.user_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
    
    def set_connection_info(self, host: str, port: int = 2222, user: str = "root"):
        """Pre-fill connection information."""
        self.host_input.setText(host)
        self.port_input.setValue(port)
        self.user_input.setText(user)
