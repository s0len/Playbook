"""File match processing including link creation and overwrite decisions.

This module handles the processing of file matches including creating symlinks
or hard links, making overwrite decisions based on quality indicators, updating
the processed file cache, and cleaning up old destinations when files move.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Set

from .cache import CachedFileRecord, ProcessedFileCache
from .models import ProcessingStats, SportFileMatch
from .notifications import NotificationEvent
from .utils import link_file, sha1_of_file

LOGGER = logging.getLogger(__name__)


# Functions to be extracted from processor.py:
# - handle_match() (from _handle_match)
# - should_overwrite_existing() (from _should_overwrite_existing)
# - specificity_score() (from _specificity_score)
# - alias_candidates() (from _alias_candidates)
# - season_cache_key() (from _season_cache_key)
# - episode_cache_key() (from _episode_cache_key)
# - cleanup_old_destination() (from _cleanup_old_destination)
# - record_destination_touch() (from _record_destination_touch)
