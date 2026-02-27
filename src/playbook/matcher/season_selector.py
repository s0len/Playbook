"""Season selection logic based on pattern configuration.

This module handles resolving which season a file belongs to based on
the configured season selector mode (round, key, title, sequential, date, week).
"""

from __future__ import annotations

import logging
import re
import unicodedata

from ..config import SeasonSelector
from ..models import Season, Show
from ..utils import normalize_token
from .date_utils import parse_date_string

_ALPHA_NUMERIC_PREFIX = re.compile(r"^([a-z]+\d+)")
_WORD_SPLIT = re.compile(r"[^a-zA-Z0-9\u00C0-\u024F]+")
_MIN_WORD_LEN = 4

LOGGER = logging.getLogger(__name__)


def _extract_significant_words(text: str) -> set[str]:
    """Extract normalized words (≥ _MIN_WORD_LEN chars) from text.

    Uses NFD decomposition + combining mark removal so that e.g.
    'Österreich' becomes 'osterreich' and 'España' becomes 'espana'.
    """
    # NFD decompose then strip combining marks to get base letters
    decomposed = unicodedata.normalize("NFD", text)
    stripped = re.sub(r"[\u0300-\u036f]", "", decomposed)
    words = _WORD_SPLIT.split(stripped)
    result: set[str] = set()
    for w in words:
        lowered = w.lower()
        if len(lowered) >= _MIN_WORD_LEN:
            result.add(lowered)
    return result


_MIN_PREFIX_LEN = 6


def _common_prefix_len(a: str, b: str) -> int:
    """Return the length of the common prefix between two strings."""
    limit = min(len(a), len(b))
    for i in range(limit):
        if a[i] != b[i]:
            return i
    return limit


def _word_overlap_score(words_a: set[str], words_b: set[str]) -> int:
    """Count matching words between two sets using exact and common-prefix matching.

    Exact matches count for any word ≥ _MIN_WORD_LEN.
    Common-prefix matches require the shared prefix to be ≥ _MIN_PREFIX_LEN to
    avoid false positives like 'grand' matching 'grande' across unrelated GPs.
    This handles cases like 'portugal'↔'portuguese' (share 'portug', 6 chars).
    """
    score = 0
    for wa in words_a:
        for wb in words_b:
            if wa == wb:
                score += 1
                break
            if _common_prefix_len(wa, wb) >= _MIN_PREFIX_LEN:
                score += 1
                break
    return score


def resolve_selector_value(
    selector: SeasonSelector,
    match_groups: dict[str, str],
    default_group: str,
) -> str | None:
    """Resolve the value for a season selector from match groups.

    Args:
        selector: The season selector configuration
        match_groups: Dictionary of regex capture groups
        default_group: Default group name to use if selector.group is None

    Returns:
        Resolved value string or None
    """
    if selector.value_template:
        try:
            formatted = selector.value_template.format(**match_groups)
        except KeyError:
            return None
        formatted = formatted.strip()
        return formatted or None
    key = selector.group or default_group
    if key is None:
        return None
    value = match_groups.get(key)
    # Try fallback groups if primary group has no value
    if value is None and selector.fallback_groups:
        for fallback_key in selector.fallback_groups:
            value = match_groups.get(fallback_key)
            if value is not None:
                break
    if value is None:
        return None
    return value


def select_season(show: Show, selector: SeasonSelector, match_groups: dict[str, str]) -> Season | None:
    """Select the appropriate season based on selector mode and match groups.

    Supports modes: sequential, round, week, key, title, date

    Args:
        show: The show containing seasons to select from
        selector: Season selector configuration
        match_groups: Dictionary of regex capture groups

    Returns:
        Matched Season or None if no match found
    """
    mode = selector.mode

    if mode == "sequential":
        raw_value = resolve_selector_value(selector, match_groups, "season") or "0"
        index = int(raw_value)
        for season in show.seasons:
            if season.index == index:
                return season
        return None

    if mode == "round":
        value = resolve_selector_value(selector, match_groups, "round")
        if value is None:
            return None
        try:
            round_number = int(value)
        except ValueError:
            return None
        round_number += selector.offset
        for season in show.seasons:
            candidates = [season.round_number, season.display_number]
            candidates = [num for num in candidates if num is not None]
            if round_number in candidates:
                return season
        if 0 < round_number <= len(show.seasons):
            return show.seasons[round_number - 1]
        return None

    if mode == "week":
        value = resolve_selector_value(selector, match_groups, "week")
        if value is None:
            return None
        try:
            week_number = int(value)
        except ValueError:
            return None
        week_number += selector.offset
        # Match against display_number (most common for week-based seasons)
        for season in show.seasons:
            if season.display_number == week_number:
                return season
        # Fallback: match against "Week N" title pattern
        week_title = f"Week {week_number}"
        normalized_week = normalize_token(week_title)
        for season in show.seasons:
            if normalize_token(season.title) == normalized_week:
                return season
        return None

    if mode == "key":
        key = resolve_selector_value(selector, match_groups, "season")
        if key is None:
            return None
        for season in show.seasons:
            if season.key == key:
                return season
        mapped = selector.mapping.get(key)
        if mapped:
            for season in show.seasons:
                if season.index == mapped:
                    return season
        return None

    if mode == "title":
        title = resolve_selector_value(selector, match_groups, "season")
        if not title:
            return None
        if selector.aliases:
            alias_target = selector.aliases.get(title)
            if alias_target is None:
                normalized_title = normalize_token(title)
                for alias_key, mapped_title in selector.aliases.items():
                    if normalize_token(alias_key) == normalized_title:
                        alias_target = mapped_title
                        break
            if alias_target:
                title = alias_target
        normalized = normalize_token(title)
        for season in show.seasons:
            if normalize_token(season.title) == normalized:
                return season
        for season in show.seasons:
            season_normalized = normalize_token(season.title)
            if normalized and (normalized in season_normalized or season_normalized in normalized):
                return season
        # Check against season aliases from API metadata
        for season in show.seasons:
            for alias in season.metadata.get("aliases", []):
                alias_normalized = normalize_token(alias)
                if alias_normalized == normalized:
                    return season
        for season in show.seasons:
            for alias in season.metadata.get("aliases", []):
                alias_normalized = normalize_token(alias)
                if normalized and (normalized in alias_normalized or alias_normalized in normalized):
                    return season
        mapped = selector.mapping.get(title)
        if mapped:
            desired_round = int(mapped)
            for season in show.seasons:
                if season.round_number == desired_round or season.display_number == desired_round:
                    return season
        # Fallback 1: try matching by round_number using the "season" capture group
        season_value = match_groups.get("season")
        if season_value is not None:
            try:
                round_number = int(season_value)
                for season in show.seasons:
                    if season.round_number == round_number or season.display_number == round_number:
                        return season
            except (ValueError, TypeError):
                pass
        # Fallback 2: prefix match — extract alpha+number prefix from normalized title
        # and match against season titles starting with the same prefix.
        # e.g., "ufc306prelims" → prefix "ufc306" matches "ufc306omalleyvsdvalishvili"
        prefix_match = _ALPHA_NUMERIC_PREFIX.match(normalized)
        if prefix_match:
            prefix = prefix_match.group(1)
            prefix_len = len(prefix)
            for season in show.seasons:
                sn = normalize_token(season.title)
                if sn.startswith(prefix) and (len(sn) == prefix_len or not sn[prefix_len].isdigit()):
                    return season
            # If we found a prefix (e.g., "ufc325") but no season matched it,
            # do NOT fall through to word-level matching.  The prefix is the
            # definitive identifier and word-level matching would cause false
            # positives for rematches (e.g., "volkanovski vs lopes" appearing in
            # both UFC 314 and UFC 325).
            return None
        # Fallback 3 (last resort): word-level matching — extract significant words
        # and score overlap.  Only used when no alpha+numeric prefix is present
        # (e.g., non-English location names for MotoGP).
        # e.g., "Grande Prémio de Portugal" shares "portug*" with "Portuguese Grand Prix"
        title_words = _extract_significant_words(title)
        if title_words:
            best_season: Season | None = None
            best_score = 0
            second_best_score = 0
            for season in show.seasons:
                season_words = _extract_significant_words(season.title)
                score = _word_overlap_score(title_words, season_words)
                for alias in season.metadata.get("aliases", []):
                    alias_words = _extract_significant_words(alias)
                    alias_score = _word_overlap_score(title_words, alias_words)
                    score = max(score, alias_score)
                if score > best_score:
                    second_best_score = best_score
                    best_score = score
                    best_season = season
                elif score > second_best_score:
                    second_best_score = score
            if best_season is not None and best_score > 0 and best_score > second_best_score:
                return best_season
        return None

    if mode == "date":
        raw_value = resolve_selector_value(selector, match_groups, "date")
        if not raw_value:
            return None
        parsed = parse_date_string(raw_value)
        if not parsed:
            return None
        for season in show.seasons:
            for episode in season.episodes:
                if episode.originally_available == parsed:
                    return season
        return None

    if mode == "global_episode":
        value = resolve_selector_value(selector, match_groups, "episode_number")
        if value is None:
            return None
        try:
            episode_number = int(value)
        except ValueError:
            return None
        for season in show.seasons:
            for episode in season.episodes:
                if episode.display_number == episode_number:
                    return season
        return None

    LOGGER.warning("Unknown season selector mode '%s'", mode)
    return None
