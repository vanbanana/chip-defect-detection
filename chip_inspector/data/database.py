"""
Database management for the chip inspection system.
Uses SQLite for local storage of inspection results, recipes, and system events.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from core.constants import DATABASE_NAME, DEFAULT_DATA_DIR, DATABASE_BACKUP_DIR
from core.exceptions import DatabaseError
from utils.logger import get_logger


class Database:
    """
    SQLite database manager for the inspection system.

    Tables:
    - inspections: Detection results
    - recipes: Saved detection recipes
    - system_events: Application event log
    """

    def __init__(self, db_path: Optional[str] = None):
        self._logger = get_logger(__name__)

        if db_path is None:
            data_dir = Path(DEFAULT_DATA_DIR)
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / DATABASE_NAME)

        self._db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize database and create tables."""
        with self.get_connection() as conn:
            self._create_tables(conn)

    @contextmanager
    def get_connection(self):
        """Get a database connection with context management."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f"Database error: {str(e)}")
        finally:
            conn.close()

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create all database tables."""

        # Inspections table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT NOT NULL,
                image_name TEXT NOT NULL,
                status TEXT NOT NULL,
                defect_area REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                recipe_name TEXT NOT NULL,
                parameters TEXT,
                processing_time_ms REAL,
                metadata TEXT
            )
        """)

        # Create indexes for inspections
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_inspections_status
            ON inspections(status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_inspections_timestamp
            ON inspections(timestamp DESC)
        """)

        # Recipes table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                algorithm TEXT NOT NULL,
                parameters TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                modified_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # System events table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_category TEXT NOT NULL,
                message TEXT,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for events
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON system_events(timestamp DESC)
        """)

        self._logger.info("Database tables initialized")

    def backup(self, backup_path: Optional[str] = None) -> str:
        """
        Create a backup of the database.

        Args:
            backup_path: Optional custom backup path

        Returns:
            Path to the backup file
        """
        if backup_path is None:
            backup_dir = Path(DATABASE_BACKUP_DIR)
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = str(backup_dir / f"backup_{timestamp}.db")

        # Copy database file
        import shutil
        shutil.copy2(self._db_path, backup_path)

        self._logger.info(f"Database backed up to: {backup_path}")
        return backup_path

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            # Count inspections
            total = conn.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
            ok_count = conn.execute(
                "SELECT COUNT(*) FROM inspections WHERE status = 'OK'"
            ).fetchone()[0]
            ng_count = conn.execute(
                "SELECT COUNT(*) FROM inspections WHERE status = 'NG'"
            ).fetchone()[0]

            # Count recipes
            recipe_count = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]

            # Count events
            event_count = conn.execute("SELECT COUNT(*) FROM system_events").fetchone()[0]

            # Database size
            db_size = Path(self._db_path).stat().st_size

            return {
                'inspections_total': total,
                'inspections_ok': ok_count,
                'inspections_ng': ng_count,
                'recipes_count': recipe_count,
                'events_count': event_count,
                'database_size_bytes': db_size,
                'database_path': self._db_path
            }

    def execute_query(
        self,
        query: str,
        params: tuple = (),
        fetch: str = "all"
    ) -> Any:
        """
        Execute a raw SQL query.

        Args:
            query: SQL query
            params: Query parameters
            fetch: 'all', 'one', or None (no fetch)

        Returns:
            Query result based on fetch mode
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)

            if fetch == "all":
                return cursor.fetchall()
            elif fetch == "one":
                return cursor.fetchone()
            else:
                return None

    def vacuum(self) -> None:
        """Vacuum the database to reclaim space."""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
        self._logger.info("Database vacuumed")
