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


def skip_reason_for_source_file(path: Path) -> Optional[str]:
    """Check if a source file should be skipped.

    Args:
        path: Path to the source file

    Returns:
        A string describing why the file should be skipped, or None if it should be processed
    """
    name = path.name
    if name.startswith("._") and len(name) > 2:
        return "macOS resource fork (._ prefix)"
    return None


def matches_globs(path: Path, sport: SportConfig) -> bool:
    """Check if a file matches any of the sport's glob patterns.

    Args:
        path: Path to the source file
        sport: Sport configuration containing glob patterns

    Returns:
        True if the file matches any glob pattern or if no patterns are defined
    """
    if not sport.source_globs:
        return True
    filename = path.name
    return any(fnmatch(filename, pattern) for pattern in sport.source_globs)


def should_suppress_sample_ignored(source_path: Path) -> bool:
    """Check if a file appears to be a sample file based on its name.

    Args:
        source_path: Path to the source file

    Returns:
        True if the file name contains 'sample' (case-insensitive)
    """
    name = source_path.name.lower()
    return bool(SAMPLE_FILENAME_PATTERN.search(name))


# Functions to be extracted from processor.py:
# - gather_source_files() (from _gather_source_files)
