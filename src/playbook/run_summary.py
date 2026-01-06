"""Logging summaries, run recaps, and statistics formatting.

This module handles formatting and logging processing summaries including detailed
activity reports, run recaps with statistics, error summaries, and activity detection.
It provides utilities for formatting counts, messages, and Plex sync errors in a
consistent, readable format for logging output.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from .models import ProcessingStats
    from .plex_metadata_sync import PlexSyncStats

from .logging_utils import LogBlockBuilder

LOGGER = logging.getLogger(__name__)


# Functions to be extracted from processor.py:
# - format_log() (from _format_log)
# - format_inline_log() (from _format_inline_log)
# - has_activity() (from _has_activity)
# - has_detailed_activity() (from _has_detailed_activity)
# - filtered_ignored_details() (from _filtered_ignored_details)
# - summarize_counts() (from _summarize_counts)
# - summarize_messages() (from _summarize_messages)
# - summarize_plex_errors() (from _summarize_plex_errors)
# - extract_error_context() (from _extract_error_context)
# - log_detailed_summary() (from _log_detailed_summary)
# - log_run_recap() (from _log_run_recap)
