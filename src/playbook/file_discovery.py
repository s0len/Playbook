"""Source file discovery, filtering, and glob matching.

This module handles discovering source files for processing, filtering out
unwanted files (like macOS resource forks and sample files), and matching
files against sport-specific glob patterns to determine which files should
be processed by which sports.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from fnmatch import fnmatch
from pathlib import Path

from .config import SportConfig
from .logging_utils import render_fields_block
from .models import ProcessingStats

LOGGER = logging.getLogger(__name__)

# Regular expression pattern to detect sample/demo files
SAMPLE_FILENAME_PATTERN = re.compile(r"(?<![a-z0-9])sample(?![a-z0-9])")


def skip_reason_for_source_file(path: Path) -> str | None:
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


def matches_globs(path: Path, sport: SportConfig, *, source_dir: Path | None = None) -> bool:
    """Check if a file matches any of the sport's glob patterns.

    Checks filename against ``source_globs`` and, if *source_dir* is provided,
    also checks the relative path against ``source_path_globs``.

    Args:
        path: Path to the source file
        sport: Sport configuration containing glob patterns
        source_dir: Optional source directory for relative-path glob matching

    Returns:
        True if the file matches any glob pattern or if no patterns are defined
    """
    if not sport.source_globs and not sport.source_path_globs:
        return True
    filename = path.name
    if sport.source_globs and any(fnmatch(filename, pattern) for pattern in sport.source_globs):
        return True
    if sport.source_path_globs and source_dir is not None:
        try:
            relative = path.relative_to(source_dir)
        except ValueError:
            return False
        return any(relative.match(pattern) for pattern in sport.source_path_globs)
    return not sport.source_globs and not sport.source_path_globs


def should_suppress_sample_ignored(source_path: Path) -> bool:
    """Check if a file appears to be a sample file based on its name.

    Args:
        source_path: Path to the source file

    Returns:
        True if the file name contains 'sample' (case-insensitive)
    """
    name = source_path.name.lower()
    return bool(SAMPLE_FILENAME_PATTERN.search(name))


def matches_include_ignore_patterns(path: Path, include: list[str], ignore: list[str]) -> bool:
    """Check include/ignore pattern filters using watcher semantics.

    Pattern matching is applied to both filename and full path string.

    Args:
        path: Path to evaluate
        include: Include patterns (empty means include all)
        ignore: Ignore patterns

    Returns:
        True if the file passes filters and should be processed.
    """
    filename = path.name
    target = str(path)

    if include and not any(fnmatch(filename, pattern) or fnmatch(target, pattern) for pattern in include):
        return False
    return not (ignore and any(fnmatch(filename, pattern) or fnmatch(target, pattern) for pattern in ignore))


def gather_source_files(source_dir: Path, stats: ProcessingStats | None = None) -> Iterable[Path]:
    """Discover and yield source files for processing.

    Iterates through the source directory recursively, filtering out:
    - Non-file entries (directories, etc.)
    - Symlinks
    - macOS resource forks (._ prefix)

    Args:
        source_dir: Root directory to scan for source files
        stats: Optional ProcessingStats object to register warnings

    Yields:
        Path objects for each valid source file found

    Returns:
        Empty list if source directory doesn't exist
    """
    if not source_dir.exists():
        LOGGER.warning(
            render_fields_block(
                "Source Directory Missing",
                {"Path": source_dir},
                pad_top=True,
            )
        )
        if stats is not None:
            stats.register_warning(f"Source directory missing: {source_dir}")
        return []

    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue

        if path.is_symlink():
            LOGGER.debug(
                render_fields_block(
                    "Skipping Source File",
                    {
                        "Source": path,
                        "Reason": "symlink",
                    },
                    pad_top=True,
                )
            )
            continue

        skip_reason = skip_reason_for_source_file(path)
        if skip_reason:
            LOGGER.debug(
                render_fields_block(
                    "Skipping Source File",
                    {
                        "Source": path,
                        "Reason": skip_reason,
                    },
                    pad_top=True,
                )
            )
            continue

        yield path
