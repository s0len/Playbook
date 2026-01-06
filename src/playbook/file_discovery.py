"""Source file discovery, filtering, and glob matching.

This module handles discovering source files for processing, filtering out
unwanted files (like macOS resource forks and sample files), and matching
files against sport-specific glob patterns to determine which files should
be processed by which sports.
"""

from __future__ import annotations

import logging
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, Optional

from .config import SportConfig
from .models import ProcessingStats

LOGGER = logging.getLogger(__name__)

# Regular expression pattern to detect sample/demo files
SAMPLE_FILENAME_PATTERN = re.compile(r"(?<![a-z0-9])sample(?![a-z0-9])")


# Functions to be extracted from processor.py:
# - skip_reason_for_source_file() (from _skip_reason_for_source_file)
# - matches_globs() (from _matches_globs)
# - should_suppress_sample_ignored() (from _should_suppress_sample_ignored)
# - gather_source_files() (from _gather_source_files)
