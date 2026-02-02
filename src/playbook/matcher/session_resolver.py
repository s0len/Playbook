"""Session lookup and resolution utilities.

This module provides functions for resolving session names through the
SessionLookupIndex, including fuzzy matching support.
"""

from __future__ import annotations

try:
    from rapidfuzz.distance import DamerauLevenshtein
except ImportError:  # pragma: no cover - optional dependency
    DamerauLevenshtein = None  # type: ignore[assignment]

from ..config import PatternConfig
from ..models import Season
from ..session_index import SessionLookupIndex
from ..utils import normalize_token
from .core import DEFAULT_GENERIC_SESSION_ALIASES
from .similarity import token_similarity, tokens_close


def resolve_session_lookup(session_lookup: SessionLookupIndex, token: str) -> str | None:
    """Resolve a session token to its canonical title via the session lookup.

    First tries exact match, then fuzzy matching for tokens >= 4 chars.

    Args:
        session_lookup: The session lookup index
        token: Normalized session token to resolve

    Returns:
        Canonical session title or None if not found
    """
    # Try exact match first
    direct = session_lookup.get_direct(token)
    if direct:
        return direct

    if len(token) < 4:
        return None

    best_key: str | None = None
    best_score = 0.0

    # Use index to get only candidates matching first-char and length constraints
    for candidate in session_lookup.get_candidates(token):
        if len(candidate) < 4:
            continue
        if not tokens_close(candidate, token):
            continue
        score = token_similarity(candidate, token)
        if DamerauLevenshtein:
            distance = DamerauLevenshtein.distance(candidate, token)
            if distance <= 1:
                score = max(score, 0.92)
        if score > best_score:
            best_key = candidate
            best_score = score

    if best_key is not None and best_score >= 0.85:
        return session_lookup.get_direct(best_key)
    return None


def build_session_lookup(pattern: PatternConfig, season: Season) -> SessionLookupIndex:
    """Build a session lookup index for a pattern and season.

    Indexes episode titles and aliases for fast lookup during matching.

    Args:
        pattern: The pattern configuration
        season: The season to build the index for

    Returns:
        SessionLookupIndex populated with episode titles and aliases
    """
    index = SessionLookupIndex()

    # Add episode titles and aliases
    for episode in season.episodes:
        normalized = normalize_token(episode.title)
        index.add(normalized, episode.title)
        for alias in episode.aliases:
            index.add(normalize_token(alias), episode.title)

    # Add pattern-specific session aliases
    for canonical, aliases in pattern.session_aliases.items():
        normalized = normalize_token(canonical)
        # Only add if not already present (equivalent to setdefault behavior)
        if index.get_direct(normalized) is None:
            index.add(normalized, canonical)
        for alias in aliases:
            normalized_alias = normalize_token(alias)
            if index.get_direct(normalized_alias) is None:
                index.add(normalized_alias, canonical)

    # Add default generic session aliases for common motorsport terms.
    # These aliases normalize various spellings/formats to canonical session names.
    # The canonical names can then be used by pattern-specific session_aliases.
    # Only add if not already defined by the pattern's session_aliases.
    for canonical, aliases in DEFAULT_GENERIC_SESSION_ALIASES.items():
        normalized_canonical = normalize_token(canonical)
        # Skip if the pattern already defines this canonical name
        if normalized_canonical and index.get_direct(normalized_canonical) is not None:
            continue
        # Add the canonical name itself
        if normalized_canonical:
            index.add(normalized_canonical, canonical)
        # Add all aliases pointing to the canonical name
        for alias in aliases:
            normalized_alias = normalize_token(alias)
            if normalized_alias and index.get_direct(normalized_alias) is None:
                index.add(normalized_alias, canonical)

    return index
