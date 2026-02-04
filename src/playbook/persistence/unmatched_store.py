"""SQLite-backed store for unmatched file records.

This module provides persistence for tracking files that failed pattern matching,
enabling GUI visualization and manual matching capabilities.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterator

# File category types
FileCategory = Literal["video", "sample", "metadata", "archive", "other"]

# File extension to category mapping
FILE_CATEGORY_EXTENSIONS: dict[FileCategory, set[str]] = {
    "video": {".mkv", ".mp4", ".avi", ".ts", ".m4v", ".wmv", ".mov", ".flv", ".webm"},
    "metadata": {".nfo", ".txt", ".jpg", ".jpeg", ".png", ".srt", ".sub", ".idx", ".ass", ".ssa"},
    "archive": {".rar", ".zip", ".7z", ".tar", ".gz", ".bz2"},
}

# Patterns that indicate a sample file (case-insensitive)
SAMPLE_INDICATORS = {"sample", "-sample", ".sample", "_sample"}


def classify_file_category(filename: str) -> FileCategory:
    """Classify a file into a category based on its name and extension.

    Args:
        filename: The filename to classify

    Returns:
        The file category
    """
    lower_name = filename.lower()

    # Check for sample files first (these take priority over video)
    for indicator in SAMPLE_INDICATORS:
        if indicator in lower_name:
            return "sample"

    # Get extension
    ext = Path(filename).suffix.lower()

    # Check each category
    for category, extensions in FILE_CATEGORY_EXTENSIONS.items():
        if ext in extensions:
            return category

    return "other"


# Custom datetime adapter and converter
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
class MatchAttempt:
    """Record of a single match attempt against a sport.

    Attributes:
        sport_id: Sport identifier that was attempted
        sport_name: Human-readable sport name
        pattern_description: Description of the pattern that was tried
        status: Outcome of the attempt (regex-no-match, season-unresolved, episode-unresolved)
        captured_groups: Regex capture groups (if pattern matched)
        failure_reason: Detailed reason for failure
        best_score: Fuzzy match score if applicable (0-1)
    """

    sport_id: str
    sport_name: str | None
    pattern_description: str | None
    status: str
    captured_groups: dict[str, str] = field(default_factory=dict)
    failure_reason: str = ""
    best_score: float | None = None


@dataclass
class UnmatchedFileRecord:
    """Record of an unmatched file.

    Attributes:
        source_path: Absolute path to the file
        filename: Just the filename for display
        first_seen: When the file was first detected as unmatched
        last_seen: When the file was last seen in a scan
        file_size: File size in bytes
        file_category: Category (video, sample, metadata, archive, other)
        attempted_sports: List of sport IDs that were tried
        match_attempts: Detailed match attempt information
        best_match_sport: Sport with the closest match
        best_match_score: How close the best match was (0-1)
        failure_summary: Brief summary of why matching failed
        manually_matched: Whether the file was manually matched
        matched_show_slug: Show slug if manually matched
        matched_season: Season index if manually matched
        matched_episode: Episode index if manually matched
        matched_at: When the file was manually matched
        hidden: Whether the file is hidden from the UI
    """

    source_path: str
    filename: str
    first_seen: datetime
    last_seen: datetime
    file_size: int
    file_category: FileCategory
    attempted_sports: list[str] = field(default_factory=list)
    match_attempts: list[MatchAttempt] = field(default_factory=list)
    best_match_sport: str | None = None
    best_match_score: float | None = None
    failure_summary: str = ""
    manually_matched: bool = False
    matched_show_slug: str | None = None
    matched_season: int | None = None
    matched_episode: int | None = None
    matched_at: datetime | None = None
    hidden: bool = False


class UnmatchedFileStore:
    """SQLite-backed store for unmatched file records.

    This store tracks files that failed pattern matching, allowing users to:
    - View why files didn't match
    - Manually match files to shows/episodes
    - Filter out uninteresting files

    The database uses WAL mode for better concurrency in watch mode.
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path) -> None:
        """Initialize the store with the given database path.

        Args:
            db_path: Path to the SQLite database file
        """
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection for the current thread."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._local.connection = sqlite3.connect(
                self._db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unmatched_schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

        cursor = conn.execute("SELECT version FROM unmatched_schema_version LIMIT 1")
        row = cursor.fetchone()
        current_version = row["version"] if row else 0

        if current_version < self.SCHEMA_VERSION:
            self._migrate_schema(current_version)

    def _migrate_schema(self, from_version: int) -> None:
        """Migrate schema from a previous version."""
        conn = self._get_connection()

        if from_version < 1:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS unmatched_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    first_seen TIMESTAMP NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_category TEXT NOT NULL,
                    attempted_sports TEXT NOT NULL DEFAULT '[]',
                    match_attempts TEXT NOT NULL DEFAULT '[]',
                    best_match_sport TEXT,
                    best_match_score REAL,
                    failure_summary TEXT NOT NULL DEFAULT '',
                    manually_matched INTEGER NOT NULL DEFAULT 0,
                    matched_show_slug TEXT,
                    matched_season INTEGER,
                    matched_episode INTEGER,
                    matched_at TIMESTAMP,
                    hidden INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_unmatched_files_category
                ON unmatched_files(file_category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_unmatched_files_last_seen
                ON unmatched_files(last_seen)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_unmatched_files_hidden
                ON unmatched_files(hidden)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_unmatched_files_manually_matched
                ON unmatched_files(manually_matched)
            """)

        conn.execute("DELETE FROM unmatched_schema_version")
        conn.execute("INSERT INTO unmatched_schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))
        conn.commit()

    def close(self) -> None:
        """Close the database connection for the current thread."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def record_unmatched(self, record: UnmatchedFileRecord) -> None:
        """Record an unmatched file.

        If a record with the same source_path already exists, it will be updated
        with the new last_seen time and match attempts.

        Args:
            record: The unmatched file record to store
        """
        conn = self._get_connection()

        # Serialize complex fields
        attempted_sports_json = json.dumps(record.attempted_sports)
        match_attempts_json = json.dumps(
            [
                {
                    "sport_id": attempt.sport_id,
                    "sport_name": attempt.sport_name,
                    "pattern_description": attempt.pattern_description,
                    "status": attempt.status,
                    "captured_groups": attempt.captured_groups,
                    "failure_reason": attempt.failure_reason,
                    "best_score": attempt.best_score,
                }
                for attempt in record.match_attempts
            ]
        )

        conn.execute(
            """
            INSERT INTO unmatched_files (
                source_path, filename, first_seen, last_seen, file_size,
                file_category, attempted_sports, match_attempts,
                best_match_sport, best_match_score, failure_summary,
                manually_matched, matched_show_slug, matched_season,
                matched_episode, matched_at, hidden
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_path) DO UPDATE SET
                last_seen = excluded.last_seen,
                file_size = excluded.file_size,
                attempted_sports = excluded.attempted_sports,
                match_attempts = excluded.match_attempts,
                best_match_sport = excluded.best_match_sport,
                best_match_score = excluded.best_match_score,
                failure_summary = excluded.failure_summary
            """,
            (
                record.source_path,
                record.filename,
                record.first_seen,
                record.last_seen,
                record.file_size,
                record.file_category,
                attempted_sports_json,
                match_attempts_json,
                record.best_match_sport,
                record.best_match_score,
                record.failure_summary,
                1 if record.manually_matched else 0,
                record.matched_show_slug,
                record.matched_season,
                record.matched_episode,
                record.matched_at,
                1 if record.hidden else 0,
            ),
        )
        conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> UnmatchedFileRecord:
        """Convert a database row to an UnmatchedFileRecord."""
        attempted_sports = json.loads(row["attempted_sports"]) if row["attempted_sports"] else []
        match_attempts_data = json.loads(row["match_attempts"]) if row["match_attempts"] else []
        match_attempts = [
            MatchAttempt(
                sport_id=a["sport_id"],
                sport_name=a.get("sport_name"),
                pattern_description=a.get("pattern_description"),
                status=a["status"],
                captured_groups=a.get("captured_groups", {}),
                failure_reason=a.get("failure_reason", ""),
                best_score=a.get("best_score"),
            )
            for a in match_attempts_data
        ]

        return UnmatchedFileRecord(
            source_path=row["source_path"],
            filename=row["filename"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            file_size=row["file_size"],
            file_category=row["file_category"],
            attempted_sports=attempted_sports,
            match_attempts=match_attempts,
            best_match_sport=row["best_match_sport"],
            best_match_score=row["best_match_score"],
            failure_summary=row["failure_summary"],
            manually_matched=bool(row["manually_matched"]),
            matched_show_slug=row["matched_show_slug"],
            matched_season=row["matched_season"],
            matched_episode=row["matched_episode"],
            matched_at=row["matched_at"],
            hidden=bool(row["hidden"]),
        )

    def get_by_source(self, source_path: str) -> UnmatchedFileRecord | None:
        """Get a record by source path.

        Args:
            source_path: The source file path to look up

        Returns:
            The unmatched file record, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM unmatched_files WHERE source_path = ?",
            (source_path,),
        )
        row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def get_all(
        self,
        *,
        include_hidden: bool = False,
        include_manually_matched: bool = False,
        categories: list[FileCategory] | None = None,
        search_query: str | None = None,
        sport_filter: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[UnmatchedFileRecord]:
        """Get unmatched files with optional filtering.

        Args:
            include_hidden: Include hidden files
            include_manually_matched: Include manually matched files
            categories: Filter by file categories
            search_query: Filter by filename search
            sport_filter: Filter by attempted sport
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of unmatched file records
        """
        conn = self._get_connection()
        conditions = []
        params: list = []

        if not include_hidden:
            conditions.append("hidden = 0")

        if not include_manually_matched:
            conditions.append("manually_matched = 0")

        if categories:
            placeholders = ",".join("?" * len(categories))
            conditions.append(f"file_category IN ({placeholders})")
            params.extend(categories)

        if search_query:
            conditions.append("filename LIKE ?")
            params.append(f"%{search_query}%")

        if sport_filter:
            conditions.append("attempted_sports LIKE ?")
            params.append(f'%"{sport_filter}"%')

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])

        cursor = conn.execute(
            f"""
            SELECT * FROM unmatched_files
            WHERE {where_clause}
            ORDER BY last_seen DESC
            LIMIT ? OFFSET ?
            """,
            params,
        )
        return [self._row_to_record(row) for row in cursor]

    def get_count(
        self,
        *,
        include_hidden: bool = False,
        include_manually_matched: bool = False,
        categories: list[FileCategory] | None = None,
        search_query: str | None = None,
        sport_filter: str | None = None,
    ) -> int:
        """Get count of unmatched files with optional filtering.

        Args:
            include_hidden: Include hidden files
            include_manually_matched: Include manually matched files
            categories: Filter by file categories
            search_query: Filter by filename search
            sport_filter: Filter by attempted sport

        Returns:
            Number of matching records
        """
        conn = self._get_connection()
        conditions = []
        params: list = []

        if not include_hidden:
            conditions.append("hidden = 0")

        if not include_manually_matched:
            conditions.append("manually_matched = 0")

        if categories:
            placeholders = ",".join("?" * len(categories))
            conditions.append(f"file_category IN ({placeholders})")
            params.extend(categories)

        if search_query:
            conditions.append("filename LIKE ?")
            params.append(f"%{search_query}%")

        if sport_filter:
            conditions.append("attempted_sports LIKE ?")
            params.append(f'%"{sport_filter}"%')

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cursor = conn.execute(
            f"SELECT COUNT(*) as count FROM unmatched_files WHERE {where_clause}",
            params,
        )
        return cursor.fetchone()["count"]

    def get_category_counts(
        self,
        *,
        include_hidden: bool = False,
        include_manually_matched: bool = False,
    ) -> dict[FileCategory, int]:
        """Get counts of unmatched files by category.

        Args:
            include_hidden: Include hidden files
            include_manually_matched: Include manually matched files

        Returns:
            Dictionary mapping category to count
        """
        conn = self._get_connection()
        conditions = []

        if not include_hidden:
            conditions.append("hidden = 0")

        if not include_manually_matched:
            conditions.append("manually_matched = 0")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cursor = conn.execute(
            f"""
            SELECT file_category, COUNT(*) as count
            FROM unmatched_files
            WHERE {where_clause}
            GROUP BY file_category
            """
        )
        return {row["file_category"]: row["count"] for row in cursor}

    def mark_manually_matched(
        self,
        source_path: str,
        show_slug: str,
        season: int,
        episode: int,
    ) -> bool:
        """Mark a file as manually matched.

        Args:
            source_path: Path to the source file
            show_slug: The show slug it was matched to
            season: The season index
            episode: The episode index

        Returns:
            True if a record was updated, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            UPDATE unmatched_files
            SET manually_matched = 1,
                matched_show_slug = ?,
                matched_season = ?,
                matched_episode = ?,
                matched_at = ?
            WHERE source_path = ?
            """,
            (show_slug, season, episode, datetime.now(), source_path),
        )
        conn.commit()
        return cursor.rowcount > 0

    def hide_file(self, source_path: str) -> bool:
        """Hide a file from the unmatched list.

        Args:
            source_path: Path to the source file

        Returns:
            True if a record was updated, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "UPDATE unmatched_files SET hidden = 1 WHERE source_path = ?",
            (source_path,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def unhide_file(self, source_path: str) -> bool:
        """Unhide a previously hidden file.

        Args:
            source_path: Path to the source file

        Returns:
            True if a record was updated, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "UPDATE unmatched_files SET hidden = 0 WHERE source_path = ?",
            (source_path,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def delete_by_source(self, source_path: str) -> bool:
        """Delete a record by source path.

        Args:
            source_path: The source file path to delete

        Returns:
            True if a record was deleted, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM unmatched_files WHERE source_path = ?",
            (source_path,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def delete_stale(self, older_than: datetime) -> int:
        """Delete records not seen since the given time.

        Args:
            older_than: Delete records with last_seen before this time

        Returns:
            Number of records deleted
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM unmatched_files WHERE last_seen < ? AND manually_matched = 0",
            (older_than,),
        )
        conn.commit()
        return cursor.rowcount

    def clear(self) -> int:
        """Delete all records.

        Returns:
            Number of records deleted
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM unmatched_files")
        conn.commit()
        return cursor.rowcount

    def iter_all(self) -> Iterator[UnmatchedFileRecord]:
        """Iterate over all records.

        Yields:
            UnmatchedFileRecord for each record in the database
        """
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM unmatched_files ORDER BY last_seen DESC")
        for row in cursor:
            yield self._row_to_record(row)

    def get_stats(self) -> dict[str, int | dict]:
        """Get statistics about unmatched files.

        Returns:
            Dictionary with counts:
            - total: Total number of records
            - by_category: Dict of category -> count
            - manually_matched: Number manually matched
            - hidden: Number hidden
        """
        conn = self._get_connection()

        # Total count
        cursor = conn.execute("SELECT COUNT(*) as count FROM unmatched_files")
        total = cursor.fetchone()["count"]

        # By category
        cursor = conn.execute("SELECT file_category, COUNT(*) as count FROM unmatched_files GROUP BY file_category")
        by_category = {row["file_category"]: row["count"] for row in cursor}

        # Manually matched
        cursor = conn.execute("SELECT COUNT(*) as count FROM unmatched_files WHERE manually_matched = 1")
        manually_matched = cursor.fetchone()["count"]

        # Hidden
        cursor = conn.execute("SELECT COUNT(*) as count FROM unmatched_files WHERE hidden = 1")
        hidden = cursor.fetchone()["count"]

        return {
            "total": total,
            "by_category": by_category,
            "manually_matched": manually_matched,
            "hidden": hidden,
        }


def get_file_size_safe(path: str | Path) -> int:
    """Get file size, returning 0 if the file doesn't exist.

    Args:
        path: Path to the file

    Returns:
        File size in bytes, or 0 if not accessible
    """
    try:
        return os.path.getsize(path)
    except OSError:
        return 0
