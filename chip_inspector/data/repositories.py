"""
Data access objects (repositories) for database operations.
"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from data.database import Database
from core.models import InspectionResult, Recipe, SystemEvent
from core.enums import DetectionStatus
from core.exceptions import DatabaseError
from utils.logger import get_logger


class InspectionRepository:
    """Repository for inspection results."""

    def __init__(self, database: Database):
        self._db = database
        self._logger = get_logger(__name__)

    def save(self, result: InspectionResult) -> int:
        """
        Save an inspection result to the database.

        Returns:
            ID of the inserted record
        """
        query = """
            INSERT INTO inspections (
                image_path, image_name, status, defect_area,
                recipe_name, parameters, processing_time_ms, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            result.image_path,
            result.image_name,
            result.status.name,
            result.defect_area,
            result.recipe_name,
            json.dumps(result.parameters),
            result.processing_time_ms,
            json.dumps(result.metadata)
        )

        with self._db.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.lastrowid

    def save_batch(self, results: List[InspectionResult]) -> List[int]:
        """
        Save multiple inspection results.

        Returns:
            List of inserted IDs
        """
        ids = []
        for result in results:
            ids.append(self.save(result))
        return ids

    def get_by_id(self, inspection_id: int) -> Optional[InspectionResult]:
        """Get an inspection result by ID."""
        query = "SELECT * FROM inspections WHERE id = ?"
        row = self._db.execute_query(query, (inspection_id,), fetch="one")

        if row is None:
            return None

        return self._row_to_result(row)

    def get_all(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[InspectionResult]:
        """
        Get all inspection results with optional filtering.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            status_filter: Filter by status ('OK', 'NG', or None for all)

        Returns:
            List of InspectionResult
        """
        query = "SELECT * FROM inspections WHERE 1=1"
        params = []

        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        elif offset:
            query += " OFFSET ?"
            params.append(offset)

        rows = self._db.execute_query(query, tuple(params))
        return [self._row_to_result(row) for row in rows]

    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[InspectionResult]:
        """Get inspections within a date range."""
        query = """
            SELECT * FROM inspections
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp DESC
        """

        rows = self._db.execute_query(query, (start_date, end_date))
        return [self._row_to_result(row) for row in rows]

    def get_statistics(self) -> Dict[str, Any]:
        """Get inspection statistics."""
        query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'OK' THEN 1 ELSE 0 END) as ok_count,
                SUM(CASE WHEN status = 'NG' THEN 1 ELSE 0 END) as ng_count,
                AVG(defect_area) as avg_area,
                MAX(defect_area) as max_area
            FROM inspections
        """

        row = self._db.execute_query(query, fetch="one")

        return {
            'total': row[0] or 0,
            'ok_count': row[1] or 0,
            'ng_count': row[2] or 0,
            'pass_rate': (row[1] / row[0] * 100) if row[0] > 0 else 0,
            'avg_area': row[3] or 0,
            'max_area': row[4] or 0
        }

    def delete_by_id(self, inspection_id: int) -> bool:
        """Delete an inspection by ID."""
        query = "DELETE FROM inspections WHERE id = ?"
        with self._db.get_connection() as conn:
            cursor = conn.execute(query, (inspection_id,))
            return cursor.rowcount > 0

    def delete_old(self, days: int) -> int:
        """Delete inspections older than specified days."""
        query = f"""
            DELETE FROM inspections
            WHERE timestamp < datetime('now', '-{days} days')
        """

        with self._db.get_connection() as conn:
            cursor = conn.execute(query)
            return cursor.rowcount

    def clear_all(self) -> int:
        """Clear all inspection results."""
        query = "DELETE FROM inspections"

        with self._db.get_connection() as conn:
            cursor = conn.execute(query)
            count = cursor.rowcount
            self._logger.info(f"Cleared all inspections ({count} records)")
            return count

    def _row_to_result(self, row) -> InspectionResult:
        """Convert database row to InspectionResult."""
        return InspectionResult(
            id=row['id'],
            image_path=row['image_path'],
            image_name=row['image_name'],
            status=DetectionStatus[row['status']],
            defect_area=row['defect_area'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            recipe_name=row['recipe_name'],
            parameters=json.loads(row['parameters']) if row['parameters'] else {},
            processing_time_ms=row['processing_time_ms'] or 0,
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )


class RecipeRepository:
    """Repository for detection recipes."""

    def __init__(self, database: Database):
        self._db = database
        self._logger = get_logger(__name__)

    def save(self, recipe: Recipe) -> int:
        """Save or update a recipe."""
        # Check if exists
        existing = self.get_by_name(recipe.name)

        if existing:
            query = """
                UPDATE recipes
                SET description = ?, algorithm = ?, parameters = ?, modified_at = ?
                WHERE name = ?
            """

            params = (
                recipe.description,
                recipe.algorithm,
                json.dumps(recipe.parameters),
                datetime.now().isoformat(),
                recipe.name
            )

            with self._db.get_connection() as conn:
                conn.execute(query, params)
                return existing.id
        else:
            query = """
                INSERT INTO recipes (name, description, algorithm, parameters, created_at, modified_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """

            params = (
                recipe.name,
                recipe.description,
                recipe.algorithm,
                json.dumps(recipe.parameters),
                recipe.created_at.isoformat() if recipe.created_at else datetime.now().isoformat(),
                recipe.modified_at.isoformat() if recipe.modified_at else datetime.now().isoformat()
            )

            with self._db.get_connection() as conn:
                cursor = conn.execute(query, params)
                return cursor.lastrowid

    def get_by_name(self, name: str) -> Optional[Recipe]:
        """Get a recipe by name."""
        query = "SELECT * FROM recipes WHERE name = ?"
        row = self._db.execute_query(query, (name,), fetch="one")

        if row is None:
            return None

        return self._row_to_recipe(row)

    def get_all(self) -> List[Recipe]:
        """Get all recipes."""
        query = "SELECT * FROM recipes ORDER BY name"
        rows = self._db.execute_query(query)
        return [self._row_to_recipe(row) for row in rows]

    def delete(self, name: str) -> bool:
        """Delete a recipe by name."""
        query = "DELETE FROM recipes WHERE name = ?"

        with self._db.get_connection() as conn:
            cursor = conn.execute(query, (name,))
            return cursor.rowcount > 0

    def _row_to_recipe(self, row) -> Recipe:
        """Convert database row to Recipe."""
        created = datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        modified = datetime.fromisoformat(row['modified_at']) if row['modified_at'] else None

        return Recipe(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            algorithm=row['algorithm'],
            parameters=json.loads(row['parameters']) if row['parameters'] else {},
            created_at=created,
            modified_at=modified
        )


class EventRepository:
    """Repository for system events."""

    def __init__(self, database: Database):
        self._db = database
        self._logger = get_logger(__name__)

    def save(self, event: SystemEvent) -> int:
        """Save a system event."""
        query = """
            INSERT INTO system_events (event_type, event_category, message, details)
            VALUES (?, ?, ?, ?)
        """

        params = (
            event.event_type,
            event.event_category,
            event.message,
            event.details
        )

        with self._db.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.lastrowid

    def get_all(
        self,
        limit: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> List[SystemEvent]:
        """Get system events with optional filtering."""
        query = "SELECT * FROM system_events WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = self._db.execute_query(query, tuple(params))
        return [self._row_to_event(row) for row in rows]

    def delete_old(self, days: int) -> int:
        """Delete events older than specified days."""
        query = f"""
            DELETE FROM system_events
            WHERE timestamp < datetime('now', '-{days} days')
        """

        with self._db.get_connection() as conn:
            cursor = conn.execute(query)
            return cursor.rowcount

    def clear_all(self) -> int:
        """Clear all events."""
        query = "DELETE FROM system_events"

        with self._db.get_connection() as conn:
            cursor = conn.execute(query)
            return cursor.rowcount

    def _row_to_event(self, row) -> SystemEvent:
        """Convert database row to SystemEvent."""
        return SystemEvent(
            id=row['id'],
            event_type=row['event_type'],
            event_category=row['event_category'],
            message=row['message'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            details=row['details']
        )
