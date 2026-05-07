"""
Data models for the chip inspection system.
Defines all data structures used throughout the application.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from .enums import DetectionStatus
from PySide6.QtGui import QPixmap


@dataclass
class AlgorithmParameter:
    """A single algorithm parameter definition."""
    name: str
    display_name: str
    value: float
    min_value: float
    max_value: float
    step: float = 1.0
    scale: float = 1.0
    unit: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'value': self.value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'step': self.step,
            'scale': self.scale,
            'unit': self.unit,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlgorithmParameter':
        """Create from dictionary."""
        return cls(
            name=data['name'],
            display_name=data.get('display_name', data['name']),
            value=data['value'],
            min_value=data['min_value'],
            max_value=data['max_value'],
            step=data.get('step', 1.0),
            scale=data.get('scale', 1.0),
            unit=data.get('unit', ''),
            description=data.get('description', '')
        )


@dataclass
class Recipe:
    """A detection recipe with parameters."""
    name: str
    algorithm: str
    parameters: Dict[str, Any]
    description: str = ""
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    id: Optional[int] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.modified_at is None:
            self.modified_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'algorithm': self.algorithm,
            'description': self.description,
            'parameters': self.parameters,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'modified_at': self.modified_at.strftime('%Y-%m-%d %H:%M:%S') if self.modified_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], id: Optional[int] = None) -> 'Recipe':
        """Create from dictionary."""
        created = None
        modified = None
        if data.get('created_at'):
            created = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S')
        if data.get('modified_at'):
            modified = datetime.strptime(data['modified_at'], '%Y-%m-%d %H:%M:%S')

        return cls(
            name=data['name'],
            algorithm=data.get('algorithm', 'hsv_detector'),
            description=data.get('description', ''),
            parameters=data.get('parameters', {}),
            created_at=created,
            modified_at=modified,
            id=id
        )


@dataclass
class InspectionResult:
    """Result of a single chip inspection."""
    image_path: str
    image_name: str
    status: DetectionStatus
    defect_area: float
    timestamp: datetime
    recipe_name: str
    parameters: Dict[str, Any]
    processing_time_ms: float = 0.0
    id: Optional[int] = None
    # Optional: processed images for display
    original_image: Optional[QPixmap] = None
    result_image: Optional[QPixmap] = None
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without QPixmap objects)."""
        return {
            'id': self.id,
            'image_path': self.image_path,
            'image_name': self.image_name,
            'status': self.status.name,
            'defect_area': self.defect_area,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'recipe_name': self.recipe_name,
            'parameters': self.parameters,
            'processing_time_ms': self.processing_time_ms,
            'metadata': self.metadata
        }

    @property
    def is_ok(self) -> bool:
        """Check if result is OK."""
        return self.status == DetectionStatus.OK

    @property
    def is_ng(self) -> bool:
        """Check if result is NG."""
        return self.status == DetectionStatus.NG

    def get_status_display(self) -> str:
        """Get status as display string."""
        return "OK" if self.is_ok else "NG" if self.is_ng else "UNKNOWN"


@dataclass
class SystemEvent:
    """A system event for logging."""
    event_type: str
    event_category: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_category': self.event_category,
            'message': self.message,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'details': self.details
        }


@dataclass
class BatchProgress:
    """Progress information for batch processing."""
    total: int
    completed: int
    current_file: str = ""
    ok_count: int = 0
    ng_count: int = 0

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.completed == 0:
            return 0.0
        return (self.ok_count / self.completed) * 100

    @property
    def progress_percent(self) -> int:
        """Get progress as percentage."""
        if self.total == 0:
            return 0
        return int((self.completed / self.total) * 100)


@dataclass
class DetectionConfig:
    """Configuration for detection algorithm."""
    # HSV parameters for chip detection
    h_min: int = 100
    h_max: int = 130
    s_min: int = 90
    v_min: int = 50
    v_max: int = 255
    s_max: int = 255

    # Defect detection parameters
    stain_v_thresh: int = 100
    max_total_area: int = 150
    min_blob: int = 5

    # Safe zone margin
    safe_margin: int = 15

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetectionConfig':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

    def update(self, **kwargs):
        """Update parameters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
