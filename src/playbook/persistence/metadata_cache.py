"""SQLite-backed cache for API metadata responses.

This module provides persistence for caching metadata from external APIs
(like TVSportsDB) with support for:
- TTL-based expiration
- HTTP conditional requests (ETag/Last-Modified)
- Efficient invalidation by prefix (e.g., all UFC seasons)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached metadata entry.

    Attributes:
        key: Unique cache key (e.g., "shows/ufc-2025")
        content: JSON content as a dictionary
        etag: HTTP ETag header for conditional requests
        last_modified: HTTP Last-Modified header for conditional requests
        fetched_at: When the content was fetched
        expires_at: When the cache entry expires
    """

    key: str
    content: dict[str, Any] | list[Any]
    etag: str | None
    last_modified: str | None
    fetched_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_fresh(self) -> bool:
        """Check if this entry is still fresh (not expired)."""
        return not self.is_expired


class MetadataCacheStore:
    """SQLite-backed cache for API metadata.

    This store caches API responses with TTL-based expiration and supports
    HTTP conditional requests via ETag and Last-Modified headers.

    The cache key format is "category/identifier", e.g.:
    - "shows/formula-1-2025"
    - "seasons/formula-1-2025_s1"
    - "team_aliases/nfl"

    Example:
        cache = MetadataCacheStore(Path("/cache/metadata.db"), ttl_hours=2)

        # Store a response
        cache.set("shows/ufc-2025", show_data, etag='"abc123"')

        # Retrieve (returns None if expired)
        entry = cache.get("shows/ufc-2025")
        if entry:
            return entry.content

        # Get entry even if expired (for conditional requests)
        entry = cache.get("shows/ufc-2025", include_expired=True)
        if entry and entry.etag:
            # Can make conditional request with If-None-Match
            pass

        # Invalidate by prefix
        cache.invalidate_by_prefix("shows/ufc-")  # All UFC shows
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path, ttl_hours: int = 2) -> None:
        """Initialize the cache store.

        Args:
            db_path: Path to the SQLite database file
            ttl_hours: Default time-to-live in hours for cached entries
        """
        self.db_path = db_path
        self.ttl_hours = ttl_hours
        self._ttl = timedelta(hours=ttl_hours)
        self._local = threading.local()

        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection

    def _init_schema(self) -> None:
        """Initialize the database schema."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

        # Check current version
        cursor = conn.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        current_version = row[0] if row else 0

        if current_version < self.SCHEMA_VERSION:
            # Create or migrate schema
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata_cache (
                    key TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    etag TEXT,
                    last_modified TEXT,
                    fetched_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)

            # Create index for prefix queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_cache_key_prefix
                ON metadata_cache (key)
            """)

            # Update schema version
            conn.execute("DELETE FROM schema_version")
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))
            conn.commit()

    def get(self, key: str, *, include_expired: bool = False) -> CacheEntry | None:
        """Get a cached entry by key.

        Args:
            key: The cache key (e.g., "shows/ufc-2025")
            include_expired: If True, returns expired entries (for conditional requests)

        Returns:
            CacheEntry if found (and not expired, unless include_expired=True), else None
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT key, content, etag, last_modified, fetched_at, expires_at
            FROM metadata_cache
            WHERE key = ?
            """,
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        entry = CacheEntry(
            key=row["key"],
            content=json.loads(row["content"]),
            etag=row["etag"],
            last_modified=row["last_modified"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
        )

        if not include_expired and entry.is_expired:
            return None

        return entry

    def set(
        self,
        key: str,
        content: dict[str, Any] | list[Any],
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        ttl_hours: int | None = None,
    ) -> None:
        """Store content in the cache.

        Args:
            key: The cache key (e.g., "shows/ufc-2025")
            content: The content to cache (will be JSON serialized)
            etag: Optional ETag header from the response
            last_modified: Optional Last-Modified header from the response
            ttl_hours: Override the default TTL for this entry
        """
        now = datetime.now(UTC)
        ttl = timedelta(hours=ttl_hours) if ttl_hours is not None else self._ttl
        expires_at = now + ttl

        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO metadata_cache
            (key, content, etag, last_modified, fetched_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                json.dumps(content, ensure_ascii=False),
                etag,
                last_modified,
                now.isoformat(),
                expires_at.isoformat(),
            ),
        )
        conn.commit()

    def refresh_ttl(self, key: str, ttl_hours: int | None = None) -> bool:
        """Refresh the TTL for an existing entry (e.g., after a 304 response).

        Args:
            key: The cache key
            ttl_hours: Override the default TTL

        Returns:
            True if the entry was found and updated, False otherwise
        """
        now = datetime.now(UTC)
        ttl = timedelta(hours=ttl_hours) if ttl_hours is not None else self._ttl
        expires_at = now + ttl

        conn = self._get_connection()
        cursor = conn.execute(
            """
            UPDATE metadata_cache
            SET expires_at = ?
            WHERE key = ?
            """,
            (expires_at.isoformat(), key),
        )
        conn.commit()
        return cursor.rowcount > 0

    def delete(self, key: str) -> bool:
        """Delete a specific cache entry.

        Args:
            key: The cache key to delete

        Returns:
            True if an entry was deleted, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM metadata_cache WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0

    def invalidate_by_prefix(self, prefix: str) -> int:
        """Invalidate all entries matching a key prefix.

        Args:
            prefix: The key prefix (e.g., "shows/ufc-" to invalidate all UFC shows)

        Returns:
            Number of entries deleted
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM metadata_cache WHERE key LIKE ?",
            (f"{prefix}%",),
        )
        conn.commit()
        return cursor.rowcount

    def invalidate_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries deleted
        """
        now = datetime.now(UTC)
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM metadata_cache WHERE expires_at < ?",
            (now.isoformat(),),
        )
        conn.commit()
        return cursor.rowcount

    def clear(self) -> int:
        """Clear all cached entries.

        Returns:
            Number of entries deleted
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM metadata_cache")
        conn.commit()
        return cursor.rowcount

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        now = datetime.now(UTC)
        conn = self._get_connection()

        cursor = conn.execute("SELECT COUNT(*) FROM metadata_cache")
        total = cursor.fetchone()[0]

        cursor = conn.execute(
            "SELECT COUNT(*) FROM metadata_cache WHERE expires_at >= ?",
            (now.isoformat(),),
        )
        fresh = cursor.fetchone()[0]

        cursor = conn.execute(
            "SELECT COUNT(*) FROM metadata_cache WHERE expires_at < ?",
            (now.isoformat(),),
        )
        expired = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM metadata_cache WHERE etag IS NOT NULL")
        with_etag = cursor.fetchone()[0]

        return {
            "total_entries": total,
            "fresh_entries": fresh,
            "expired_entries": expired,
            "entries_with_etag": with_etag,
            "ttl_hours": self.ttl_hours,
        }

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
