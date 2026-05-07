"""
Industrial Chip Inspector - Main Entry Point

An industrial-grade chip defect detection system using HSV color segmentation.
Designed for factory production environments with high-contrast UI and
touch-friendly controls.

Usage:
    python main.py

    Or with custom config directory:
    python main.py --config-dir /path/to/config
"""
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from core.constants import APP_NAME, APP_VERSION, DEFAULT_CONFIG_DIR
from utils.logger import setup_logging, get_logger

# Import algorithm modules to register them
import algorithms.hsv_detector  # This registers the HSV detector


def parse_args():
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} - Industrial Chip Defect Detection System"
    )
    parser.add_argument(
        '--config-dir',
        type=str,
        default=None,
        help=f'Path to configuration directory (default: {DEFAULT_CONFIG_DIR})'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Minimum log level to display'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )

    return parser.parse_args()


def main():
    """Main application entry point."""
    # Parse arguments
    args = parse_args()

    # Setup logging
    log_level = 'DEBUG' if args.debug else args.log_level
    setup_logging(log_level=log_level)
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.info("=" * 60)

    # Create Qt application
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("IndustrialVision")

    # Set application style
    app.setStyle("Fusion")

    # Import and create main window
    try:
        from ui.main_window import MainWindow

        window = MainWindow()
        window.show()

        logger.info("Application window created")

        # Run event loop
        exit_code = app.exec()

        logger.info(f"Application exited with code: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)

        # Show error dialog if possible
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Startup Error")
        msg.setText(f"Failed to start {APP_NAME}")
        msg.setDetailedText(str(e))
        msg.exec()

        sys.exit(1)


if __name__ == '__main__':
    main()
