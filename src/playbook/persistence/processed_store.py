"""SQLite-backed store for processed file records.

This module provides persistence for tracking processed files across restarts,
enabling GUI visualization and manual file management capabilities.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterator

# Valid status values for processed files
ProcessingStatus = Literal["linked", "copied", "symlinked", "skipped", "error"]


# Custom datetime adapter and converter to avoid Python 3.12+ deprecation warnings
def _adapt_datetime(dt: datetime) -> str:
    """Convert datetime to ISO format string for SQLite storage."""
    return dt.isoformat()


def _convert_datetime(data: bytes) -> datetime:
    """Convert ISO format string from SQLite to datetime."""
    return datetime.fromisoformat(data.decode("utf-8"))


# Register the adapter and converter
sqlite3.register_adapter(datetime, _adapt_datetime)
sqlite3.register_converter("TIMESTAMP", _convert_datetime)


@dataclass
class ProcessedFileRecord:
    """Record of a processed file.

    Attributes:
        source_path: Path to the source file
        destination_path: Path to the destination file
        sport_id: Sport identifier (e.g., "f1", "nba")
        show_id: Show identifier (e.g., "formula-1-2024")
        season_index: Season index (0-based)
        episode_index: Episode index within season (0-based)
        processed_at: Timestamp when file was processed
        checksum: File checksum (optional)
        status: Processing status
        error_message: Error message if status is "error"
        quality_score: Computed quality score for upgrade comparisons (optional)
        quality_info: JSON-encoded quality attributes (optional)
    """

    source_path: str
    destination_path: str
    sport_id: str
    show_id: str
    season_index: int
    episode_index: int
    processed_at: datetime
    checksum: str | None = None
    status: ProcessingStatus = "linked"
    error_message: str | None = None
    quality_score: int | None = None
    quality_info: str | None = None


class ProcessedFileStore:
    """SQLite-backed store for processed file records.

    This store tracks processed files for GUI visualization and allows
    queries by source path, show, season, or episode.

    The database uses WAL mode for better concurrency in watch mode.

    Example:
        store = ProcessedFileStore(Path("/cache/playbook.db"))
        store.record_processed(ProcessedFileRecord(
            source_path="/source/file.mkv",
            destination_path="/dest/file.mkv",
            sport_id="f1",
            show_id="formula-1-2024",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
        ))
    """

    SCHEMA_VERSION = 2

    def __init__(self, db_path: Path) -> None:
        """Initialize the store with the given database path.

        Args:
            db_path: Path to the SQLite database file
        """
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection for the current thread.

        Uses thread-local storage to maintain separate connections per thread,
        which is required by SQLite.
        """
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._local.connection = sqlite3.connect(
                self._db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

        # Check current schema version
        cursor = conn.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        current_version = row["version"] if row else 0

        if current_version < self.SCHEMA_VERSION:
            self._migrate_schema(current_version)

    def _migrate_schema(self, from_version: int) -> None:
        """Migrate schema from a previous version.

        Args:
            from_version: Current schema version in database
        """
        conn = self._get_connection()

        if from_version < 1:
            # Initial schema
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT UNIQUE NOT NULL,
                    destination_path TEXT NOT NULL,
                    sport_id TEXT NOT NULL,
                    show_id TEXT NOT NULL,
                    season_index INTEGER NOT NULL,
                    episode_index INTEGER NOT NULL,
                    processed_at TIMESTAMP NOT NULL,
                    checksum TEXT,
                    status TEXT NOT NULL DEFAULT 'linked',
                    error_message TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_files_sport
                ON processed_files(sport_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_files_show
                ON processed_files(show_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_files_season
                ON processed_files(show_id, season_index)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_files_status
                ON processed_files(status)
            """)

        if from_version < 2:
            # Schema v2: Add quality scoring columns
            # Check if columns already exist (in case of partial migration)
            cursor = conn.execute("PRAGMA table_info(processed_files)")
            existing_columns = {row["name"] for row in cursor}

            if "quality_score" not in existing_columns:
                conn.execute("""
                    ALTER TABLE processed_files
                    ADD COLUMN quality_score INTEGER DEFAULT NULL
                """)

            if "quality_info" not in existing_columns:
                conn.execute("""
                    ALTER TABLE processed_files
                    ADD COLUMN quality_info TEXT DEFAULT NULL
                """)

            # Add index for quality-based queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_files_quality
                ON processed_files(sport_id, quality_score)
            """)

            # Add index for destination path lookups (for quality comparison)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_files_destination
                ON processed_files(destination_path)
            """)

        # Update schema version
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))
        conn.commit()

    def close(self) -> None:
        """Close the database connection for the current thread."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def record_processed(self, record: ProcessedFileRecord) -> None:
        """Record a processed file.

        If a record with the same source_path already exists, it will be updated.

        Args:
            record: The processed file record to store
        """
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO processed_files (
                source_path, destination_path, sport_id, show_id,
                season_index, episode_index, processed_at, checksum,
                status, error_message, quality_score, quality_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_path) DO UPDATE SET
                destination_path = excluded.destination_path,
                sport_id = excluded.sport_id,
                show_id = excluded.show_id,
                season_index = excluded.season_index,
                episode_index = excluded.episode_index,
                processed_at = excluded.processed_at,
                checksum = excluded.checksum,
                status = excluded.status,
                error_message = excluded.error_message,
                quality_score = excluded.quality_score,
                quality_info = excluded.quality_info
            """,
            (
                record.source_path,
                record.destination_path,
                record.sport_id,
                record.show_id,
                record.season_index,
                record.episode_index,
                record.processed_at,
                record.checksum,
                record.status,
                record.error_message,
                record.quality_score,
                record.quality_info,
            ),
        )
        conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> ProcessedFileRecord:
        """Convert a database row to a ProcessedFileRecord."""
        # Handle both v1 and v2 schema rows gracefully
        row_keys = row.keys()
        quality_score = row["quality_score"] if "quality_score" in row_keys else None
        quality_info = row["quality_info"] if "quality_info" in row_keys else None

        return ProcessedFileRecord(
            source_path=row["source_path"],
            destination_path=row["destination_path"],
            sport_id=row["sport_id"],
            show_id=row["show_id"],
            season_index=row["season_index"],
            episode_index=row["episode_index"],
            processed_at=row["processed_at"],
            checksum=row["checksum"],
            status=row["status"],
            error_message=row["error_message"],
            quality_score=quality_score,
            quality_info=quality_info,
        )

    def get_by_source(self, source_path: str) -> ProcessedFileRecord | None:
        """Get a record by source path.

        Args:
            source_path: The source file path to look up

        Returns:
            The processed file record, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM processed_files WHERE source_path = ?",
            (source_path,),
        )
        row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def check_processed_with_destination(self, source_path: str) -> tuple[bool, str | None]:
        """Check if source is processed and destination still exists.

        This method is used for early filtering in the processing pipeline to skip
        files that have already been processed and whose destination still exists.

        Args:
            source_path: The source file path to check

        Returns:
            (True, dest_path) - source processed AND destination exists → skip
            (False, dest_path) - source in DB but destination missing → re-process
            (False, None) - source not in DB → normal processing
        """
        record = self.get_by_source(source_path)
        if record is None:
            return (False, None)

        from pathlib import Path

        if Path(record.destination_path).exists():
            return (True, record.destination_path)

        return (False, record.destination_path)

    def get_by_show(self, show_id: str) -> list[ProcessedFileRecord]:
        """Get all records for a show.

        Args:
            show_id: The show identifier

        Returns:
            List of processed file records for the show
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM processed_files WHERE show_id = ? ORDER BY season_index, episode_index",
            (show_id,),
        )
        return [self._row_to_record(row) for row in cursor]

    def get_by_season(self, show_id: str, season_index: int) -> list[ProcessedFileRecord]:
        """Get all records for a season.

        Args:
            show_id: The show identifier
            season_index: The season index (0-based)

        Returns:
            List of processed file records for the season
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """SELECT * FROM processed_files
               WHERE show_id = ? AND season_index = ?
               ORDER BY episode_index""",
            (show_id, season_index),
        )
        return [self._row_to_record(row) for row in cursor]

    def get_by_sport(self, sport_id: str) -> list[ProcessedFileRecord]:
        """Get all records for a sport.

        Args:
            sport_id: The sport identifier

        Returns:
            List of processed file records for the sport
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM processed_files WHERE sport_id = ? ORDER BY show_id, season_index, episode_index",
            (sport_id,),
        )
        return [self._row_to_record(row) for row in cursor]

    def get_by_status(self, status: ProcessingStatus) -> list[ProcessedFileRecord]:
        """Get all records with a given status.

        Args:
            status: The processing status to filter by

        Returns:
            List of processed file records with the given status
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM processed_files WHERE status = ? ORDER BY processed_at DESC",
            (status,),
        )
        return [self._row_to_record(row) for row in cursor]

    def get_errors(self) -> list[ProcessedFileRecord]:
        """Get all records with error status.

        Returns:
            List of processed file records with error status
        """
        return self.get_by_status("error")

    def get_by_destination(self, destination_path: str) -> ProcessedFileRecord | None:
        """Get a record by destination path.

        Args:
            destination_path: The destination file path to look up

        Returns:
            The processed file record, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM processed_files WHERE destination_path = ?",
            (destination_path,),
        )
        row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def get_quality_score(self, destination_path: str) -> int | None:
        """Get the highest quality score for a destination path.

        This is used to compare quality scores when deciding whether to
        upgrade an existing file. We use MAX because multiple source files
        may have been processed to the same destination (after upgrades),
        and we want to compare against the best quality we've ever achieved.

        Args:
            destination_path: The destination file path to look up

        Returns:
            The highest quality score, or None if not found or not set
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT MAX(quality_score) as quality_score FROM processed_files WHERE destination_path = ?",
            (destination_path,),
        )
        row = cursor.fetchone()
        if row and row["quality_score"] is not None:
            return row["quality_score"]
        return None

    def update_quality(
        self,
        destination_path: str,
        quality_score: int | None,
        quality_info: str | None,
    ) -> bool:
        """Update quality information for an existing record.

        Args:
            destination_path: The destination file path to update
            quality_score: The new quality score
            quality_info: JSON-encoded quality attributes

        Returns:
            True if a record was updated, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            UPDATE processed_files
            SET quality_score = ?, quality_info = ?
            WHERE destination_path = ?
            """,
            (quality_score, quality_info, destination_path),
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_recent(self, limit: int = 100) -> list[ProcessedFileRecord]:
        """Get most recently processed files.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of most recent processed file records
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM processed_files ORDER BY processed_at DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_record(row) for row in cursor]

    def iter_all(self) -> Iterator[ProcessedFileRecord]:
        """Iterate over all records.

        Yields:
            ProcessedFileRecord for each record in the database
        """
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM processed_files ORDER BY processed_at DESC")
        for row in cursor:
            yield self._row_to_record(row)

    def get_stats(self) -> dict[str, int]:
        """Get statistics about processed files.

        Returns:
            Dictionary with counts:
            - total: Total number of records
            - by_status: Dict of status -> count
            - by_sport: Dict of sport_id -> count
        """
        conn = self._get_connection()

        # Total count
        cursor = conn.execute("SELECT COUNT(*) as count FROM processed_files")
        total = cursor.fetchone()["count"]

        # By status
        cursor = conn.execute("SELECT status, COUNT(*) as count FROM processed_files GROUP BY status")
        by_status = {row["status"]: row["count"] for row in cursor}

        # By sport
        cursor = conn.execute("SELECT sport_id, COUNT(*) as count FROM processed_files GROUP BY sport_id")
        by_sport = {row["sport_id"]: row["count"] for row in cursor}

        return {
            "total": total,
            "by_status": by_status,
            "by_sport": by_sport,
        }

    def delete_by_source(self, source_path: str) -> bool:
        """Delete a record by source path.

        Args:
            source_path: The source file path to delete

        Returns:
            True if a record was deleted, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM processed_files WHERE source_path = ?",
            (source_path,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def delete_old_destination_records(self, destination_path: str, keep_source: str) -> int:
        """Delete old records for a destination, keeping only the specified source.

        This should be called when a file is replaced to clean up stale records
        from previous sources that pointed to the same destination.

        Args:
            destination_path: The destination file path
            keep_source: The source path to keep (the new replacement file)

        Returns:
            Number of old records deleted
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM processed_files WHERE destination_path = ? AND source_path != ?",
            (destination_path, keep_source),
        )
        conn.commit()
        return cursor.rowcount

    def delete_by_show(self, show_id: str) -> int:
        """Delete all records for a show.

        Args:
            show_id: The show identifier

        Returns:
            Number of records deleted
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM processed_files WHERE show_id = ?",
            (show_id,),
        )
        conn.commit()
        return cursor.rowcount

    def clear(self) -> int:
        """Delete all records.

        Returns:
            Number of records deleted
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM processed_files")
        conn.commit()
        return cursor.rowcount
