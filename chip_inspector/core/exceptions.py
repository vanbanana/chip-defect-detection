"""
Custom exceptions for the chip inspection system.
"""


class ChipInspectionError(Exception):
    """Base exception for all chip inspection errors."""
    pass


class AlgorithmError(ChipInspectionError):
    """Raised when an algorithm encounters an error during detection."""
    pass


class ConfigurationError(ChipInspectionError):
    """Raised when configuration is invalid or cannot be loaded."""
    pass


class ValidationError(ChipInspectionError):
    """Raised when input validation fails."""
    pass


class ImageLoadError(ChipInspectionError):
    """Raised when an image cannot be loaded or processed."""
    pass


class DatabaseError(ChipInspectionError):
    """Raised when a database operation fails."""
    pass


class ExportError(ChipInspectionError):
    """Raised when data export fails."""
    pass


class RecipeError(ChipInspectionError):
    """Raised when recipe operations fail."""
    pass
