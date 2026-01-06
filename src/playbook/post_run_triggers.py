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

LOGGER = logging.getLogger(__name__)


# Functions to be extracted from processor.py:
# - run_plex_sync_if_needed() (from _run_plex_sync_if_needed)
# - trigger_kometa_if_needed() (from _trigger_post_run_trigger_if_needed)
