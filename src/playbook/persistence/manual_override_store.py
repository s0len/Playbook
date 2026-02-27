"""SQLite-backed store for manual override records.

Manual overrides persist user-initiated manual matches so that files are
automatically resolved on subsequent runs without pattern matching, even
if the destination folder is cleared.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

LOGGER = logging.getLogger(__name__)


@dataclass
class ManualOverride:
    """A persistent manual override mapping a filename to a specific episode.

    Attributes:
        filename: Filename only (override key, survives directory reorganization)
        sport_id: Sport config id
        show_slug: Show key for metadata lookup
        season_index: Season index
        episode_index: Episode index
        created_at: When the override was created
        source_path: Original full path (informational only)
    """

    filename: str
    sport_id: str
    show_slug: str
    season_index: int
    episode_index: int
    created_at: datetime
    source_path: str | None = None


class ManualOverrideStore:
    """SQLite-backed store for manual override records.

    Overrides are keyed by filename (not full path) so they survive source
    directory reorganization. The table lives in the same ``playbook.db``
    used by other persistence stores.

    The database uses WAL mode for better concurrency in watch mode.
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection for the current thread."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                self._local.connection = self._open_connection()
            except sqlite3.OperationalError as exc:
                if "locking protocol" in str(exc):
                    LOGGER.warning("Corrupted SQLite lock files detected, recovering: %s", self._db_path)
                    self._remove_lock_files()
                    self._local.connection = self._open_connection()
                else:
                    raise
        return self._local.connection

    def _open_connection(self) -> sqlite3.Connection:
        """Open a new SQLite connection with WAL mode enabled."""
        conn = sqlite3.connect(
            self._db_path,
            timeout=10,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _remove_lock_files(self) -> None:
        """Remove SQLite WAL/SHM lock files that may be corrupted."""
        for suffix in ("-shm", "-wal"):
            lock_file = Path(str(self._db_path) + suffix)
            if lock_file.exists():
                lock_file.unlink()
                LOGGER.info("Removed corrupted lock file: %s", lock_file)

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS manual_override_schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

        cursor = conn.execute("SELECT version FROM manual_override_schema_version LIMIT 1")
        row = cursor.fetchone()
        current_version = row["version"] if row else 0

        if current_version < self.SCHEMA_VERSION:
            self._migrate_schema(current_version)

    def _migrate_schema(self, from_version: int) -> None:
        """Migrate schema from a previous version."""
        conn = self._get_connection()

        if from_version < 1:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS manual_overrides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    sport_id TEXT NOT NULL,
                    show_slug TEXT NOT NULL,
                    season_index INTEGER NOT NULL,
                    episode_index INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    source_path TEXT
                )
            """)

        conn.execute("DELETE FROM manual_override_schema_version")
        conn.execute("INSERT INTO manual_override_schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))
        conn.commit()

    def close(self) -> None:
        """Close the database connection for the current thread."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def add_override(
        self,
        filename: str,
        sport_id: str,
        show_slug: str,
        season_index: int,
        episode_index: int,
        source_path: str | None = None,
    ) -> None:
        """Add or update a manual override.

        If an override for the same filename already exists, it is replaced.

        Args:
            filename: Filename only (override key)
            sport_id: Sport config id
            show_slug: Show key for metadata lookup
            season_index: Season index
            episode_index: Episode index
            source_path: Original full path (informational)
        """
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO manual_overrides
                (filename, sport_id, show_slug, season_index, episode_index, created_at, source_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                sport_id = excluded.sport_id,
                show_slug = excluded.show_slug,
                season_index = excluded.season_index,
                episode_index = excluded.episode_index,
                created_at = excluded.created_at,
                source_path = excluded.source_path
            """,
            (filename, sport_id, show_slug, season_index, episode_index, datetime.now(), source_path),
        )
        conn.commit()

    def get_override(self, filename: str) -> ManualOverride | None:
        """Look up an override by filename.

        Args:
            filename: The filename to look up

        Returns:
            The override record, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM manual_overrides WHERE filename = ?",
            (filename,),
        )
        row = cursor.fetchone()
        return self._row_to_override(row) if row else None

    def remove_override(self, filename: str) -> bool:
        """Remove an override by filename.

        Args:
            filename: The filename to remove

        Returns:
            True if a record was deleted, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM manual_overrides WHERE filename = ?",
            (filename,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_all(self, limit: int = 500, offset: int = 0) -> list[ManualOverride]:
        """Get all overrides with pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of override records
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM manual_overrides ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [self._row_to_override(row) for row in cursor]

    def get_count(self) -> int:
        """Get total number of overrides.

        Returns:
            Number of override records
        """
        conn = self._get_connection()
        cursor = conn.execute("SELECT COUNT(*) as count FROM manual_overrides")
        return cursor.fetchone()["count"]

    def _row_to_override(self, row: sqlite3.Row) -> ManualOverride:
        """Convert a database row to a ManualOverride."""
        return ManualOverride(
            filename=row["filename"],
            sport_id=row["sport_id"],
            show_slug=row["show_slug"],
            season_index=row["season_index"],
            episode_index=row["episode_index"],
            created_at=row["created_at"],
            source_path=row["source_path"],
        )
