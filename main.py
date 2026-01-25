"""
KOReader Store - Desktop Application
Automatic installation of plugins and patches to your KOReader device
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from ui.main_window import KOReaderStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('koreader_store.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = KOReaderStore()
    window.show()
    
    logger.info("KOReader Store application started")
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
