"""Processing state management for a single processing run.

This module provides the ProcessingState dataclass which holds all mutable
state during a processing run. This separates state from configuration in
the Processor class, making state management cleaner and enabling easier
reset between runs in watch mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .metadata import MetadataChangeResult, MetadataFetchStatistics
    from .persistence import ProcessedFileRecord
    from .plex_metadata_sync import PlexSyncStats


@dataclass
class ProcessingState:
    """Mutable state for a single processing run.

    This dataclass holds all state that changes during processing.
    It should be reset between runs in watch mode to ensure clean
    processing each time.

    Attributes:
        kometa_trigger_fired: Whether Kometa was triggered this run
        kometa_trigger_needed: Whether Kometa needs to be triggered
        plex_sync_ran: Whether Plex sync has run this run
        touched_destinations: Set of destination paths that were touched
        sports_with_processed_files: Sports that had files processed
        metadata_changed_sports: List of (sport_id, sport_name) for changed metadata
        metadata_change_map: Map of sport_id to metadata change details
        metadata_fetch_stats: Statistics about metadata fetching
        stale_destinations: Map of source key to old destination path
        stale_records: Map of source key to stale processed file record
        plex_sync_stats: Statistics from Plex sync (if run)
        previous_summary: Previous summary counts for deduplication
    """

    # Trigger state
    kometa_trigger_fired: bool = False
    kometa_trigger_needed: bool = False
    plex_sync_ran: bool = False

    # Accumulated during run
    touched_destinations: set[str] = field(default_factory=set)
    sports_with_processed_files: set[str] = field(default_factory=set)

    # Metadata changes
    metadata_changed_sports: list[tuple[str, str]] = field(default_factory=list)
    metadata_change_map: dict[str, MetadataChangeResult] = field(default_factory=dict)
    metadata_fetch_stats: MetadataFetchStatistics | None = None

    # Stale file handling
    stale_destinations: dict[str, Path] = field(default_factory=dict)
    stale_records: dict[str, ProcessedFileRecord] = field(default_factory=dict)

    # Results
    plex_sync_stats: PlexSyncStats | None = None
    previous_summary: tuple[int, int, int] | None = None

    def reset(self) -> None:
        """Reset state for a new processing run.

        This clears all accumulated state except previous_summary,
        which is intentionally preserved for deduplication across runs.
        """
        self.kometa_trigger_fired = False
        self.kometa_trigger_needed = False
        self.plex_sync_ran = False
        self.touched_destinations.clear()
        self.sports_with_processed_files.clear()
        self.metadata_changed_sports.clear()
        self.metadata_change_map.clear()
        self.metadata_fetch_stats = None
        self.stale_destinations.clear()
        self.stale_records.clear()
        self.plex_sync_stats = None
        # Note: previous_summary intentionally NOT reset (deduplication)
