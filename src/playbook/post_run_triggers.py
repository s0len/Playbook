"""Post-processing triggers for Plex sync and Kometa.

This module handles post-run triggers that execute after file processing completes,
including Plex metadata synchronization and Kometa triggering for library updates.
The triggers run conditionally based on processing activity, metadata changes, and
configuration settings.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .kometa_trigger import _BaseKometaTrigger
    from .models import ProcessingStats
    from .plex_metadata_sync import PlexMetadataSync, PlexSyncStats

from .logging_utils import render_fields_block
from .plex_client import PlexApiError

LOGGER = logging.getLogger(__name__)


def run_plex_sync_if_needed(
    plex_sync: PlexMetadataSync | None,
    plex_sync_ran: bool,
    *,
    global_dry_run: bool,
    sports_with_processed_files: set[str],
    metadata_changed_sports: list[tuple[str, str]],
) -> tuple[PlexSyncStats | None, bool]:
    """Run Plex metadata sync after file processing.

    Sync runs when:
    1. Files were processed (new files to sync)
    2. Metadata changed in remote YAML
    3. Sports have never been synced to Plex (first-time sync)
    4. Force mode is enabled

    Unless a specific sports_filter is already set, only syncs sports
    that match one of the above criteria.

    Args:
        plex_sync: Plex metadata sync instance (if configured).
        plex_sync_ran: Whether sync has already been run.
        global_dry_run: Global dry-run setting from config.
        sports_with_processed_files: Set of sport IDs with processed files.
        metadata_changed_sports: List of (sport_id, reason) tuples for sports with metadata changes.

    Returns:
        Tuple of (plex_sync_stats, plex_sync_ran_flag).
    """
    from .plex_metadata_sync import PlexSyncStats

    if plex_sync is None:
        return None, plex_sync_ran

    if plex_sync_ran:
        return None, plex_sync_ran

    # Apply dry-run from global settings if not already set
    if global_dry_run and not plex_sync.dry_run:
        plex_sync.dry_run = True

    # Build set of sports needing sync
    active_sports = set(sports_with_processed_files)
    active_sports.update(sport_id for sport_id, _ in metadata_changed_sports)

    # Also include sports that have never been synced to Plex
    try:
        sports_needing_initial_sync = plex_sync.get_sports_needing_sync()
        if sports_needing_initial_sync:
            LOGGER.debug(
                "Sports needing initial/updated Plex sync: %s",
                ", ".join(sorted(sports_needing_initial_sync)),
            )
            active_sports.update(sports_needing_initial_sync)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Failed to check Plex sync state: %s", exc)

    # Skip if no sports need syncing (and no force mode)
    if not active_sports and not plex_sync.force:
        LOGGER.debug(
            render_fields_block(
                "Skipping Plex Sync",
                {"Reason": "No files processed, no metadata changes, all sports already synced"},
                pad_top=True,
            )
        )
        return None, plex_sync_ran

    # Apply sports filter (unless explicit filter is already set)
    if not plex_sync.sports_filter and active_sports:
        plex_sync.sports_filter = sorted(active_sports)
        LOGGER.debug(
            "Plex sync limited to sports with activity or needing sync: %s",
            ", ".join(plex_sync.sports_filter),
        )

    LOGGER.info(
        render_fields_block(
            "Running Plex Metadata Sync",
            {
                "Dry Run": plex_sync.dry_run,
                "Force": plex_sync.force,
                "Sports": plex_sync.sports_filter or "(all)",
            },
            pad_top=True,
        )
    )

    try:
        plex_sync_stats = plex_sync.sync_all()
        return plex_sync_stats, True
    except PlexApiError as exc:
        LOGGER.error(
            render_fields_block(
                "Plex Sync Failed",
                {"Error": str(exc)},
                pad_top=True,
            )
        )
        plex_sync_stats = PlexSyncStats()
        plex_sync_stats.errors.append(str(exc))
        return plex_sync_stats, True
    except Exception as exc:  # noqa: BLE001 - defensive
        LOGGER.exception(
            render_fields_block(
                "Plex Sync Unexpected Error",
                {"Error": str(exc)},
                pad_top=True,
            )
        )
        plex_sync_stats = PlexSyncStats()
        plex_sync_stats.errors.append(f"Unexpected: {exc}")
        return plex_sync_stats, True


def trigger_kometa_if_needed(
    kometa_trigger: _BaseKometaTrigger,
    kometa_trigger_fired: bool,
    kometa_trigger_needed: bool,
    *,
    global_dry_run: bool,
    stats: ProcessingStats,
) -> tuple[bool, bool]:
    """Trigger Kometa post-run if needed.

    Triggers Kometa when:
    - Kometa trigger is enabled
    - Not in dry-run mode
    - Kometa trigger is needed (was marked during processing)
    - Files were processed
    - Hasn't already fired this run

    Args:
        kometa_trigger: Kometa trigger instance.
        kometa_trigger_fired: Whether trigger has already fired this run.
        kometa_trigger_needed: Whether trigger is needed (marked during processing).
        global_dry_run: Global dry-run setting from config.
        stats: Processing statistics.

    Returns:
        Tuple of (kometa_trigger_fired, kometa_trigger_needed).
    """
    if (
        kometa_trigger_fired
        or not kometa_trigger.enabled
        or global_dry_run
        or not kometa_trigger_needed
        or stats.processed <= 0
    ):
        return kometa_trigger_fired, kometa_trigger_needed

    triggered = kometa_trigger.trigger(
        extra_labels={"trigger-mode": "post-run"},
        extra_annotations={"playbook/post-run": "true"},
    )
    if triggered:
        return True, False

    return kometa_trigger_fired, kometa_trigger_needed
