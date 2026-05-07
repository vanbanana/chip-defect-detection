"""
Industrial-grade logging system for the chip inspection application.
Provides structured logging with file rotation and multiple handlers.
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from core.constants import (
    DEFAULT_LOG_DIR, LOG_FORMAT, LOG_DATE_FORMAT,
    APP_NAME, APP_VERSION
)
from core.enums import SystemEventType


class ColoredFormatter(logging.Formatter):
    """Console formatter with color codes for different log levels."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[37m',       # White
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        return super().format(record)


class LogHandler:
    """
    Centralized logging handler for the application.

    Provides:
    - Console logging with colors
    - File logging with rotation
    - Separate log files for different components
    - Structured event logging for database
    """

    _instance: Optional['LogHandler'] = None
    _loggers: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._ensure_log_dir()
        self._setup_root_logger()

    def _ensure_log_dir(self):
        """Ensure log directory exists."""
        log_dir = Path(DEFAULT_LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_root_logger(self):
        """Setup the root logger with all handlers."""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler (general log)
        today = datetime.now().strftime('%Y%m%d')
        general_log = Path(DEFAULT_LOG_DIR) / f"{APP_NAME}_{today}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            general_log,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Error log file
        error_log = Path(DEFAULT_LOG_DIR) / f"{APP_NAME}_error_{today}.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger for a specific component."""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            self._loggers[name] = logger
        return self._loggers[name]


# Global instance
_log_handler: Optional[LogHandler] = None


def setup_logging(log_level: str = "INFO", log_dir: Optional[str] = None):
    """
    Setup the logging system.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Optional custom log directory
    """
    global _log_handler

    if log_dir:
        from core import constants
        constants.DEFAULT_LOG_DIR = log_dir

    _log_handler = LogHandler()

    # Set root logger level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.getLogger().setLevel(level)

    # Log startup
    logger = get_logger(__name__)
    logger.info(f"{APP_NAME} v{APP_VERSION} - Logging initialized")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__ of the calling module)

    Returns:
        Logger instance
    """
    if _log_handler is None:
        setup_logging()
    return _log_handler.get_logger(name)


def log_event(
    logger: logging.Logger,
    event_type: SystemEventType,
    message: str,
    details: Optional[str] = None
):
    """
    Log a system event with structured format.

    Args:
        logger: Logger instance
        event_type: Type of system event
        message: Event message
        details: Optional additional details
    """
    log_message = f"[{event_type.name}] {message}"
    if details:
        log_message += f" | {details}"

    if event_type in [SystemEventType.ERROR, SystemEventType.DETECTION_FAILED, SystemEventType.DATABASE_ERROR]:
        logger.error(log_message)
    elif event_type == SystemEventType.WARNING:
        logger.warning(log_message)
    elif event_type == SystemEventType.DEBUG:
        logger.debug(log_message)
    else:
        logger.info(log_message)


class DatabaseLogHandler(logging.Handler):
    """
    Custom logging handler that writes to the database.
    Used for tracking system events in the inspections database.
    """

    def __init__(self):
        super().__init__()
        self._service = None  # Will be set by ResultService

    def set_service(self, service):
        """Set the result service for database writes."""
        self._service = service

    def emit(self, record):
        """Emit a log record to the database."""
        if self._service is None:
            return

        try:
            from core.models import SystemEvent
            from core.enums import SystemEventType

            # Map logging level to event type
            event_type_map = {
                logging.ERROR: SystemEventType.ERROR,
                logging.WARNING: SystemEventType.WARNING,
                logging.INFO: SystemEventType.INFO,
                logging.DEBUG: SystemEventType.DEBUG,
            }

            event_type = event_type_map.get(record.levelno, SystemEventType.INFO)

            event = SystemEvent(
                event_type=event_type.name,
                event_category=record.name,
                message=record.getMessage(),
                details=self.format(record)
            )

            self._service.log_event(event)
        except Exception:
            # Don't let logging errors propagate
            pass
