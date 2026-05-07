"""
Base class for detection algorithms.
All detection algorithms must inherit from BaseDetector.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
import time

from PySide6.QtGui import QPixmap

from core.enums import DetectionStatus
from core.exceptions import AlgorithmError


@dataclass
class DetectionResult:
    """Result from a detection algorithm."""
    status: DetectionStatus
    defect_area: float
    original_image: Optional[QPixmap] = None
    result_image: Optional[QPixmap] = None
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseDetector(ABC):
    """
    Abstract base class for all detection algorithms.

    Algorithm plugins must:
    1. Inherit from BaseDetector
    2. Implement the detect() method
    3. Define algorithm_id and algorithm_name
    4. Register with AlgorithmRegistry
    """

    def __init__(self):
        self._parameters: Dict[str, Any] = {}
        self._initialized = False

    @property
    @abstractmethod
    def algorithm_id(self) -> str:
        """Unique identifier for this algorithm."""
        pass

    @property
    @abstractmethod
    def algorithm_name(self) -> str:
        """Human-readable name for this algorithm."""
        pass

    @property
    @abstractmethod
    def algorithm_description(self) -> str:
        """Description of what this algorithm does."""
        pass

    @abstractmethod
    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameter values for this algorithm."""
        pass

    @abstractmethod
    def get_parameter_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get parameter definitions with validation rules.

        Returns:
            Dict mapping parameter names to their definitions:
            {
                'param_name': {
                    'display_name': 'Display Name',
                    'type': 'int'|'float',
                    'min': 0,
                    'max': 255,
                    'default': 100,
                    'step': 1,
                    'scale': 1.0,
                    'unit': '',
                    'description': 'Description'
                }
            }
        """
        pass

    @abstractmethod
    def detect(self, image_path: str, **kwargs) -> DetectionResult:
        """
        Run detection on an image.

        Args:
            image_path: Path to the image file
            **kwargs: Additional detection parameters

        Returns:
            DetectionResult with status and metadata

        Raises:
            AlgorithmError: If detection fails
        """
        pass

    def set_parameter(self, name: str, value: Any) -> None:
        """Set a single parameter value."""
        definitions = self.get_parameter_definitions()
        if name not in definitions:
            raise AlgorithmError(f"Unknown parameter: {name}")

        self._parameters[name] = value

    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Set multiple parameter values."""
        definitions = self.get_parameter_definitions()
        for name, value in params.items():
            if name in definitions:
                self._parameters[name] = value

    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get a parameter value."""
        return self._parameters.get(name, default)

    def get_parameters(self) -> Dict[str, Any]:
        """Get all current parameters."""
        # Merge defaults with current values
        result = self.get_default_parameters().copy()
        result.update(self._parameters)
        return result

    def reset_parameters(self) -> None:
        """Reset all parameters to defaults."""
        self._parameters = {}

    def validate_parameters(self) -> bool:
        """Validate current parameter values."""
        definitions = self.get_parameter_definitions()
        params = self.get_parameters()

        for name, definition in definitions.items():
            value = params.get(name)
            if value is None:
                continue

            min_val = definition.get('min')
            max_val = definition.get('max')

            if min_val is not None and value < min_val:
                return False
            if max_val is not None and value > max_val:
                return False

        return True

    def _load_image(self, image_path: str) -> Optional[Any]:
        """
        Load an image file. Override in subclass for specific format handling.

        Args:
            image_path: Path to image file

        Returns:
            Image object or None if loading fails
        """
        # Base implementation - subclasses should override
        return None
