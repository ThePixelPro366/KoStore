"""

KOReader Store - Desktop Application

Automatic installation of plugins and patches to your KOReader device

"""



import sys
import logging
from PyQt6.QtWidgets import QApplication
from ui.main_window import KOReaderStore
from utils.log_handler import QtLogHandler


def setup_logging(overlay):
    """Setup logging with console and UI output"""
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Console handler (as before)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # NEW: UI handler for LoadingOverlay
    ui_handler = QtLogHandler()
    ui_handler.setLevel(logging.INFO)
    ui_formatter = logging.Formatter('%(message)s')  # Only the message, no timestamp
    ui_handler.setFormatter(ui_formatter)
    
    # Connect the handler with the overlay
    ui_handler.log_message.connect(overlay.append_log)
    logger.addHandler(ui_handler)
    
    return ui_handler





def main():
    """Main entry point for the application"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = KOReaderStore()
    
    # Setup logging with the LoadingOverlay
    ui_handler = setup_logging(window.loading_overlay)
    
    window.show()
    
    # Test log (optional, you can delete)
    logging.info("KOReader Store started")
    
    try:
        result = app.exec()
    finally:
        # Properly cleanup QtLogHandler
        if ui_handler:
            ui_handler.close()
            # Remove from global logger to prevent atexit callback error
            logging.getLogger().removeHandler(ui_handler)
    
    return result





if __name__ == "__main__":

    sys.exit(main())

