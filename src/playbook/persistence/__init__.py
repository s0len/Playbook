"""Persistence layer for processed file tracking.

This package provides SQLite-backed storage for tracking processed files,
enabling GUI visualization and manual file management capabilities.

Public API:
- ProcessedFileRecord: Record of a processed file
- ProcessedFileStore: SQLite-backed store for processed file records

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

from .processed_store import ProcessedFileRecord, ProcessedFileStore

__all__ = [
    "ProcessedFileRecord",
    "ProcessedFileStore",
]
