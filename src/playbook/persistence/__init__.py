"""Persistence layer for file tracking and caching.

This package provides SQLite-backed storage for tracking processed and
unmatched files, as well as caching API metadata responses.

Public API:
- ProcessedFileRecord: Record of a processed file
- ProcessedFileStore: SQLite-backed store for processed file records
- UnmatchedFileRecord: Record of a file that failed pattern matching
- UnmatchedFileStore: SQLite-backed store for unmatched file records
- MatchAttempt: Details of a match attempt against a sport
- classify_file_category: Classify a file by extension/name
- get_file_size_safe: Get file size without raising exceptions
- CacheEntry: A cached metadata entry with TTL and HTTP headers
- MetadataCacheStore: SQLite-backed cache for API metadata

Example:
    from playbook.persistence import ProcessedFileStore, ProcessedFileRecord

    store = ProcessedFileStore(Path("/path/to/db"))
    store.record_processed(ProcessedFileRecord(
        source_path="/source/file.mkv",
        destination_path="/dest/file.mkv",
        sport_id="f1",
        ...
    ))
"""

from .metadata_cache import CacheEntry, MetadataCacheStore
from .processed_store import ProcessedFileRecord, ProcessedFileStore
from .unmatched_store import (
    FileCategory,
    MatchAttempt,
    UnmatchedFileRecord,
    UnmatchedFileStore,
    classify_file_category,
    get_file_size_safe,
)

__all__ = [
    "CacheEntry",
    "MetadataCacheStore",
    "ProcessedFileRecord",
    "ProcessedFileStore",
    "UnmatchedFileRecord",
    "UnmatchedFileStore",
    "MatchAttempt",
    "FileCategory",
    "classify_file_category",
    "get_file_size_safe",
]
