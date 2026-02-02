"""Fuzzy string similarity utilities.

This module provides functions for comparing strings using fuzzy matching
techniques. It uses rapidfuzz when available for performance, falling back
to stdlib difflib.
"""

from __future__ import annotations

import difflib

try:
    from rapidfuzz import fuzz
    from rapidfuzz.distance import DamerauLevenshtein, Levenshtein
except ImportError:  # pragma: no cover - optional dependency
    fuzz = None  # type: ignore[assignment]
    DamerauLevenshtein = None  # type: ignore[assignment]
    Levenshtein = None  # type: ignore[assignment]


def token_similarity(candidate: str, target: str) -> float:
    """Calculate normalized similarity between two tokens.

    Uses Levenshtein normalized similarity when rapidfuzz is available,
    otherwise falls back to stdlib SequenceMatcher.

    Args:
        candidate: First string to compare
        target: Second string to compare

    Returns:
        Float between 0.0 and 1.0 where 1.0 is identical
    """
    if DamerauLevenshtein and Levenshtein:
        similarity = Levenshtein.normalized_similarity(candidate, target)
        if similarity > 1:
            similarity /= 100
        return float(similarity)
    return difflib.SequenceMatcher(None, candidate, target, autojunk=False).ratio()


def tokens_close(candidate: str, target: str) -> bool:
    """Check if two tokens are close enough to be considered a match.

    Uses early-exit optimizations (length, first char) before computing
    expensive edit distances. A token is considered close if:
    - Both are >= 4 characters
    - Length difference <= 1
    - First characters match
    - Edit distance is <= 1 or similarity >= 0.92

    Args:
        candidate: First token to compare
        target: Second token to compare

    Returns:
        True if tokens are close enough for fuzzy matching
    """
    if len(candidate) < 4 or len(target) < 4:
        return False
    if abs(len(candidate) - len(target)) > 1:
        return False
    if candidate[0] != target[0]:
        return False

    # Check for simple transposition (two adjacent chars swapped)
    if len(candidate) == len(target):
        differing_indices = [
            idx for idx, (cand_char, targ_char) in enumerate(zip(candidate, target)) if cand_char != targ_char
        ]
        if len(differing_indices) == 2:
            first, second = differing_indices
            if candidate[first] == target[second] and candidate[second] == target[first]:
                return True

    if DamerauLevenshtein and Levenshtein:
        distance = DamerauLevenshtein.distance(candidate, target)
        if distance <= 1:
            return True
        similarity = Levenshtein.normalized_similarity(candidate, target)
        if similarity > 1:
            similarity /= 100
        return similarity >= 0.92

    return token_similarity(candidate, target) >= 0.9


def location_matches_title(location: str, title: str, threshold: float = 80.0) -> bool:
    """Check if a location fuzzy-matches within a title using partial ratio.

    Uses rapidfuzz's partial_ratio for fuzzy substring matching.
    Falls back to simple substring matching if rapidfuzz is not available.

    Args:
        location: The location string to search for (e.g., "Thermal")
        title: The title to search within (e.g., "The Thermal Club IndyCar Grand Prix")
        threshold: Minimum score (0-100) to consider a match (default: 80.0)

    Returns:
        True if location matches within title, False otherwise
    """
    if not location or not title:
        return False

    # Try exact substring match first (fastest)
    if location in title:
        return True

    # Use rapidfuzz partial_ratio for fuzzy matching if available
    if fuzz:
        score = fuzz.partial_ratio(location, title)
        return score >= threshold

    # Fallback to simple substring matching
    return location in title
