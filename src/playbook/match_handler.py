"""File match processing including link creation and overwrite decisions.

This module handles the processing of file matches including creating symlinks
or hard links, making overwrite decisions based on quality indicators, updating
the processed file cache, and cleaning up old destinations when files move.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from .cache import CachedFileRecord, ProcessedFileCache
from .models import ProcessingStats, SportFileMatch
from .notifications import NotificationEvent
from .utils import link_file, normalize_token, sha1_of_file

LOGGER = logging.getLogger(__name__)


def specificity_score(value: str) -> int:
    """Calculate a specificity score for a file or episode name.

    Higher scores indicate more specific names (e.g., with part numbers,
    stage indicators, or other distinguishing markers). This helps determine
    which file should take priority when multiple files could match the same
    destination.

    Args:
        value: The file or episode name to score.

    Returns:
        An integer specificity score (higher is more specific).
    """
    if not value:
        return 0

    score = 0
    lower = value.lower()

    # Digits are strong indicators of specificity
    digit_count = sum(ch.isdigit() for ch in value)
    score += digit_count * 2

    # Separators also add specificity
    score += lower.count(".") + lower.count("-") + lower.count("_")

    # Part indicators
    if re.search(r"\bpart[\s._-]*\d+\b", lower):
        score += 2
    if re.search(r"\bstage[\s._-]*\d+\b", lower):
        score += 1
    if re.search(r"\b(?:heat|round|leg|match|session)[\s._-]*\d+\b", lower):
        score += 1
    if re.search(r"(?:^|[\s._-])(qf|sf|q|fp|sp)[\s._-]*\d+\b", lower):
        score += 1

    # Spelled-out numbers
    spelled_markers = (
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "first",
        "second",
        "third",
        "fourth",
        "fifth",
        "sixth",
        "seventh",
        "eighth",
        "ninth",
        "tenth",
    )
    for marker in spelled_markers:
        if re.search(rf"\b{marker}\b", lower):
            score += 1

    return score


def alias_candidates(match: SportFileMatch) -> List[str]:
    """Get all possible alias candidates for a matched file.

    This includes the episode's canonical title, its configured aliases,
    and any session-specific aliases from the pattern configuration.

    Args:
        match: The matched file to get alias candidates for.

    Returns:
        A deduplicated list of alias candidates in priority order.
    """
    candidates: List[str] = []

    canonical = match.episode.title
    if canonical:
        candidates.append(canonical)

    candidates.extend(match.episode.aliases)

    session_aliases = match.pattern.session_aliases
    if canonical in session_aliases:
        candidates.extend(session_aliases[canonical])
    else:
        canonical_token = normalize_token(canonical) if canonical else ""
        for key, aliases in session_aliases.items():
            if canonical_token and normalize_token(key) == canonical_token:
                candidates.extend(aliases)
                break

    # Deduplicate while preserving order and skip falsy values
    seen: Set[str] = set()
    unique_candidates: List[str] = []
    for value in candidates:
        if not value:
            continue
        if value not in seen:
            seen.add(value)
            unique_candidates.append(value)

    return unique_candidates


def season_cache_key(match: SportFileMatch) -> Optional[str]:
    """Generate a cache key for a season.

    The cache key is used to track processed files across different runs.
    It prefers explicit season keys, then display numbers, and falls back
    to season index.

    Args:
        match: The matched file containing season information.

    Returns:
        A string cache key for the season, or None if the season has no key.
    """
    season = match.season
    key = season.key
    if key is not None:
        return str(key)
    if season.display_number is not None:
        return f"display:{season.display_number}"
    return f"index:{season.index}"


def episode_cache_key(match: SportFileMatch) -> str:
    """Generate a cache key for an episode.

    The cache key is used to track processed files across different runs.
    It prefers metadata IDs (id, guid, episode_id, uuid), then display number,
    then title, and falls back to episode index.

    Args:
        match: The matched file containing episode information.

    Returns:
        A string cache key for the episode.
    """
    episode = match.episode
    metadata = episode.metadata or {}
    for field in ("id", "guid", "episode_id", "uuid"):
        value = metadata.get(field)
        if value:
            return f"{field}:{value}"
    if episode.display_number is not None:
        return f"display:{episode.display_number}"
    if episode.title:
        return f"title:{episode.title}"
    return f"index:{episode.index}"


# Functions to be extracted from processor.py:
# - handle_match() (from _handle_match)
# - should_overwrite_existing() (from _should_overwrite_existing)
# - cleanup_old_destination() (from _cleanup_old_destination)
# - record_destination_touch() (from _record_destination_touch)
