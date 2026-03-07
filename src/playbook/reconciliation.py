"""Reconciliation between the processed file database and the filesystem.

This module ensures consistency between what the database says exists
and what actually exists on disk. It runs before the main processing
loop to clean up stale records and detect orphan destination files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .persistence import ProcessedFileRecord, ProcessedFileStore

LOGGER = logging.getLogger(__name__)


def reconcile_stale_records(processed_store: ProcessedFileStore) -> int:
    """Remove DB records whose destination files no longer exist on disk.

    When a destination file is deleted (manually, by Plex, or by a bug),
    the DB record becomes stale. Removing it allows the source file to
    re-enter the processing pipeline on the next run.

    Returns:
        Number of stale records removed.
    """
    stale_sources: list[str] = []

    for record in processed_store.iter_all():
        if record.status == "error":
            continue
        if not Path(record.destination_path).exists():
            stale_sources.append(record.source_path)

    for source_path in stale_sources:
        processed_store.delete_by_source(source_path)

    if stale_sources:
        LOGGER.info(
            "Reconciliation: removed %d stale record(s) (destination missing on disk)",
            len(stale_sources),
        )
        for source in stale_sources[:5]:
            LOGGER.debug("  Stale: %s", Path(source).name)
        if len(stale_sources) > 5:
            LOGGER.debug("  ... and %d more", len(stale_sources) - 5)

    return len(stale_sources)


def detect_destination_mismatch(
    destination: Path,
    match_episode_index: int,
    match_season_index: int,
    match_show_id: str,
    processed_store: ProcessedFileStore,
) -> tuple[bool, ProcessedFileRecord | None]:
    """Check if the file at a destination was matched to a different episode.

    This detects the case where Source A was wrongly matched to Episode X,
    and now Source B correctly matches Episode X. The existing file at the
    destination belongs to a different episode than what the current match
    expects.

    Args:
        destination: The destination path that already exists.
        match_episode_index: The episode index the current match targets.
        match_season_index: The season index the current match targets.
        match_show_id: The show ID the current match targets.
        processed_store: The persistence store to look up existing records.

    Returns:
        (is_mismatch, existing_record) — True if the occupant was matched
        to a different episode, along with that record.
    """
    existing_record = processed_store.get_by_destination(str(destination))
    if existing_record is None:
        return False, None

    # If the existing record points to the same episode, it's not a mismatch —
    # it's a legitimate duplicate/quality competition handled elsewhere.
    if (
        existing_record.show_id == match_show_id
        and existing_record.season_index == match_season_index
        and existing_record.episode_index == match_episode_index
    ):
        return False, None

    # The file at this destination was matched to a DIFFERENT episode.
    # This is a mismatch that should be corrected.
    return True, existing_record
