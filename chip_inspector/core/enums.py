"""
Enumerations for the chip inspection system.
Defines all status types and event categories used throughout the application.
"""
from enum import Enum, auto


class DetectionStatus(Enum):
    """Result status for a single inspection."""
    OK = auto()      # Passed inspection
    NG = auto()      # Failed inspection (defect found)
    UNKNOWN = auto()  # Unable to determine


class ProcessingStatus(Enum):
    """Current state of batch processing."""
    IDLE = auto()      # No processing active
    RUNNING = auto()   # Batch detection in progress
    PAUSED = auto()    # Processing paused
    COMPLETED = auto() # Batch finished
    ERROR = auto()     # Error occurred


class SystemEventType(Enum):
    """Categories of system events for logging."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    DEBUG = auto()

    # Event subcategories
    DETECTION_START = auto()
    DETECTION_COMPLETE = auto()
    DETECTION_FAILED = auto()
    CONFIG_LOADED = auto()
    CONFIG_SAVED = auto()
    RECIPE_CREATED = auto()
    RECIPE_UPDATED = auto()
    RECIPE_DELETED = auto()
    IMAGE_LOAD_FAILED = auto()
    DATABASE_ERROR = auto()
    EXPORT_COMPLETE = auto()


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class ExportFormat(Enum):
    """Supported export formats."""
    CSV = "csv"
    EXCEL = "xlsx"
    JSON = "json"


class ImageFormat(Enum):
    """Supported image formats for input."""
    JPG = ".jpg"
    JPEG = ".jpeg"
    PNG = ".png"
    BMP = ".bmp"
    TIFF = ".tiff"
