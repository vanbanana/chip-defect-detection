"""
Result service - Business logic for inspection result management.
Handles database operations, queries, and export for inspection results.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from data.database import Database
from data.repositories import InspectionRepository, EventRepository
from core.models import InspectionResult, SystemEvent, BatchProgress
from core.enums import DetectionStatus
from core.exceptions import DatabaseError
from utils.logger import get_logger


class ResultService:
    """
    High-level result management service.

    Features:
    - Save and retrieve inspection results
    - Query and filter results
    - Statistics calculation
    - System event logging
    """

    def __init__(self, database: Optional[Database] = None):
        self._db = database or Database()
        self._inspections = InspectionRepository(self._db)
        self._events = EventRepository(self._db)
        self._logger = get_logger(__name__)

    # Inspection Results

    def save_inspection(self, result: InspectionResult) -> int:
        """Save an inspection result to the database."""
        try:
            result_id = self._inspections.save(result)
            self._logger.debug(f"Saved inspection result: {result.image_name}")
            return result_id
        except Exception as e:
            self._logger.error(f"Failed to save inspection: {str(e)}")
            raise DatabaseError(f"Failed to save result: {str(e)}")

    def save_batch(self, results: List[InspectionResult]) -> List[int]:
        """Save multiple inspection results."""
        try:
            ids = self._inspections.save_batch(results)
            self._logger.info(f"Saved {len(results)} inspection results")
            return ids
        except Exception as e:
            self._logger.error(f"Failed to save batch: {str(e)}")
            raise DatabaseError(f"Failed to save batch: {str(e)}")

    def get_inspection(self, inspection_id: int) -> Optional[InspectionResult]:
        """Get an inspection by ID."""
        return self._inspections.get_by_id(inspection_id)

    def get_recent_inspectons(
        self,
        limit: int = 100,
        status_filter: Optional[str] = None
    ) -> List[InspectionResult]:
        """Get recent inspection results."""
        return self._inspections.get_all(
            limit=limit,
            status_filter=status_filter
        )

    def get_inspectons_by_date(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[InspectionResult]:
        """Get inspections within a date range."""
        return self._inspections.get_by_date_range(start_date, end_date)

    def get_today_inspections(self) -> List[InspectionResult]:
        """Get today's inspections."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return self.get_inspectons_by_date(today, tomorrow)

    def get_statistics(self) -> Dict[str, Any]:
        """Get inspection statistics."""
        return self._inspections.get_statistics()

    def get_batch_statistics(self, results: List[InspectionResult]) -> Dict[str, Any]:
        """Calculate statistics for a batch of results."""
        if not results:
            return {
                'total': 0,
                'ok_count': 0,
                'ng_count': 0,
                'pass_rate': 0.0,
                'avg_area': 0.0,
                'max_area': 0.0,
                'avg_time_ms': 0.0
            }

        ok_count = sum(1 for r in results if r.is_ok)
        ng_count = len(results) - ok_count
        total_area = sum(r.defect_area for r in results)
        max_area = max((r.defect_area for r in results), default=0)
        total_time = sum(r.processing_time_ms for r in results)

        return {
            'total': len(results),
            'ok_count': ok_count,
            'ng_count': ng_count,
            'pass_rate': (ok_count / len(results) * 100) if results else 0,
            'avg_area': total_area / len(results),
            'max_area': max_area,
            'avg_time_ms': total_time / len(results)
        }

    def delete_inspection(self, inspection_id: int) -> bool:
        """Delete an inspection result."""
        return self._inspections.delete_by_id(inspection_id)

    def delete_old_inspections(self, days: int) -> int:
        """Delete inspections older than specified days."""
        count = self._inspections.delete_old(days)
        self._logger.info(f"Deleted {count} old inspections (>{days} days)")
        return count

    def clear_all_inspections(self) -> int:
        """Clear all inspection results from database."""
        count = self._inspections.clear_all()
        self._logger.info(f"Cleared all inspection data ({count} records)")
        return count

    # System Events

    def log_event(self, event: SystemEvent) -> int:
        """Log a system event."""
        try:
            event_id = self._events.save(event)
            return event_id
        except Exception as e:
            self._logger.error(f"Failed to log event: {str(e)}")
            return -1

    def log_info(self, category: str, message: str, details: Optional[str] = None) -> int:
        """Log an info event."""
        event = SystemEvent(
            event_type='INFO',
            event_category=category,
            message=message,
            details=details
        )
        return self.log_event(event)

    def log_warning(self, category: str, message: str, details: Optional[str] = None) -> int:
        """Log a warning event."""
        event = SystemEvent(
            event_type='WARNING',
            event_category=category,
            message=message,
            details=details
        )
        return self.log_event(event)

    def log_error(self, category: str, message: str, details: Optional[str] = None) -> int:
        """Log an error event."""
        event = SystemEvent(
            event_type='ERROR',
            event_category=category,
            message=message,
            details=details
        )
        return self.log_event(event)

    def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None
    ) -> List[SystemEvent]:
        """Get recent system events."""
        return self._events.get_all(limit=limit, event_type=event_type)

    def get_today_events(self) -> List[SystemEvent]:
        """Get today's events."""
        return self.get_recent_events(limit=1000)

    def clear_old_events(self, days: int) -> int:
        """Clear events older than specified days."""
        count = self._events.delete_old(days)
        self._logger.info(f"Cleared {count} old events (>{days} days)")
        return count

    def clear_all_events(self) -> int:
        """Clear all events."""
        count = self._events.clear_all()
        self._logger.info(f"Cleared all events ({count} records)")
        return count

    # Database Management

    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of the database."""
        return self._db.backup(backup_path)

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics."""
        return self._db.get_statistics()

    def vacuum_database(self) -> None:
        """Vacuum the database to reclaim space."""
        self._db.vacuum()
        self._logger.info("Database vacuumed")
