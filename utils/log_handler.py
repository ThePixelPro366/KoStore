"""
Custom logging handler for UI display
"""
import logging
from PyQt6.QtCore import QObject, pyqtSignal


class QtLogHandler(logging.Handler, QObject):
    """Logging handler that emits logs as Qt signals"""
    
    log_message = pyqtSignal(str)
    
    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self._active = True
    
    def emit(self, record):
        """Emit log record as signal"""
        if not self._active:
            return
        try:
            msg = self.format(record)
            self.log_message.emit(msg)
        except Exception:
            self.handleError(record)
    
    def close(self):
        """Properly close the handler"""
        self._active = False
        super().close()
