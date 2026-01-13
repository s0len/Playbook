from __future__ import annotations

import datetime as dt
import difflib
import logging
import re
from dataclasses import dataclass
from typing import Any

try:
    from rapidfuzz import fuzz
    from rapidfuzz.distance import DamerauLevenshtein, Levenshtein
except ImportError:  # pragma: no cover - optional dependency
    fuzz = None  # type: ignore[assignment]
    DamerauLevenshtein = None  # type: ignore[assignment]
    Levenshtein = None  # type: ignore[assignment]


def _token_similarity(candidate: str, target: str) -> float:
    if DamerauLevenshtein and Levenshtein:
        similarity = Levenshtein.normalized_similarity(candidate, target)
        if similarity > 1:
            similarity /= 100
        return float(similarity)
    return difflib.SequenceMatcher(None, candidate, target, autojunk=False).ratio()


def _dates_within_proximity(date1: dt.date | None, date2: dt.date | None, tolerance_days: int = 2) -> bool:
    """Check if two dates are within the specified tolerance (in days).

    Returns True if both dates are None, or if they're within tolerance.
    Returns False if only one date is available (can't verify proximity).
    """
    if date1 is None and date2 is None:
        return True
    if date1 is None or date2 is None:
        # Can't verify proximity if only one date is available
        return False
    delta = abs((date1 - date2).days)
    return delta <= tolerance_days


def _parse_date_from_groups(match_groups: dict[str, str]) -> dt.date | None:
    """Extract a date from match groups (day, month, year/date_year)."""
    day_str = match_groups.get("day")
    month_str = match_groups.get("month")
    year_str = match_groups.get("date_year") or match_groups.get("year")

    if not (day_str and month_str and year_str):
        return None

    try:
        day = int(day_str)
        month = int(month_str)
        year = int(year_str)
        return dt.date(year, month, day)
    except (ValueError, TypeError):
        return None


def _location_matches_title(location: str, title: str, threshold: float = 80.0) -> bool:
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


def _tokens_close(candidate: str, target: str) -> bool:
    if len(candidate) < 4 or len(target) < 4:
        return False
    if abs(len(candidate) - len(target)) > 1:
        return False
    if candidate[0] != target[0]:
        return False

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

    return _token_similarity(candidate, target) >= 0.9


def _resolve_session_lookup(session_lookup: SessionLookupIndex, token: str) -> str | None:
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
        if not _tokens_close(candidate, token):
            continue
        score = _token_similarity(candidate, token)
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


from .config import PatternConfig, SeasonSelector, SportConfig
from .models import Episode, Season, Show
from .parsers.structured_filename import StructuredName, build_canonical_filename, parse_structured_filename
from .session_index import SessionLookupIndex
from .team_aliases import get_team_alias_map
from .utils import normalize_token

LOGGER = logging.getLogger(__name__)

_NOISE_TOKENS = (
    "f1live",
    "f1tv",
    "f1kids",
    "sky",
    "intl",
    "international",
    "proper",
    "verum",
)

# Default generic session aliases for common motorsport session terms.
# These are used as fallback mappings when patterns don't define specific aliases.
# Maps canonical session name -> list of common variations/spellings.
_DEFAULT_GENERIC_SESSION_ALIASES: dict[str, list[str]] = {
    "Race": [
        "Race",
        "Main Race",
        "Main.Race",
        "Feature Race",
        "Feature.Race",
        "Main Event",
        "Main.Event",
        "Feature Event",
        "Feature.Event",
        "Grand Prix",
        "GP",
    ],
    "Practice": [
        "Practice",
        "Practice Session",
        "Practice.Session",
        "Free Practice",
        "Free.Practice",
        "FP",
        "Warmup",
        "Warm-up",
        "Warm Up",
    ],
    "Qualifying": [
        "Qualifying",
        "Quali",
        "Qualification",
        "Qualifying Session",
        "Qualifying.Session",
        "Q",
        "Q Session",
    ],
    "Sprint": [
        "Sprint",
        "Sprint Race",
        "Sprint.Race",
        "Sprint Qualifying",
        "Sprint.Qualifying",
        "SQ",
    ],
}


@dataclass
class PatternRuntime:
    config: PatternConfig
    regex: re.Pattern[str]
    session_lookup: SessionLookupIndex


def _build_session_lookup(pattern: PatternConfig, season: Season) -> SessionLookupIndex:
    index = SessionLookupIndex()
    for episode in season.episodes:
        normalized = normalize_token(episode.title)
        index.add(normalized, episode.title)
        for alias in episode.aliases:
            index.add(normalize_token(alias), episode.title)

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
    for canonical, aliases in _DEFAULT_GENERIC_SESSION_ALIASES.items():
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


def _resolve_selector_value(
    selector: SeasonSelector,
    match_groups: dict[str, str],
    default_group: str,
) -> str | None:
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
    if value is None:
        return None
    return value


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y.%m.%d",
    "%Y/%m/%d",
    "%Y %m %d",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%d %m %Y",
)

# Partial date formats (DD MM without year) - European format
_PARTIAL_DATE_FORMATS = (
    "%d %m",
    "%d-%m",
    "%d.%m",
    "%d/%m",
)


def _parse_date_string(value: str, reference_year: int | None = None) -> dt.date | None:
    """Parse a date string into a date object.

    Args:
        value: The date string to parse (e.g., "16 11 2025" or "16 11")
        reference_year: Optional year to use for partial dates (DD MM format).
                        If not provided and the date string lacks a year, parsing will fail.

    Returns:
        A date object if parsing succeeds, None otherwise.
    """
    stripped = value.strip()
    if not stripped:
        return None

    # Try full date formats first
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(stripped, fmt).date()
        except ValueError:
            continue

    # Try partial date formats (DD MM without year) if reference_year is provided
    if reference_year is not None:
        for fmt in _PARTIAL_DATE_FORMATS:
            try:
                parsed = dt.datetime.strptime(stripped, fmt)
                return dt.date(reference_year, parsed.month, parsed.day)
            except ValueError:
                continue

    return None


def _select_season(show: Show, selector: SeasonSelector, match_groups: dict[str, str]) -> Season | None:
    mode = selector.mode
    if mode == "sequential":
        raw_value = _resolve_selector_value(selector, match_groups, "season") or "0"
        index = int(raw_value)
        for season in show.seasons:
            if season.index == index:
                return season
        return None

    if mode == "round":
        value = _resolve_selector_value(selector, match_groups, "round")
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
        value = _resolve_selector_value(selector, match_groups, "week")
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
        key = _resolve_selector_value(selector, match_groups, "season")
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
        title = _resolve_selector_value(selector, match_groups, "season")
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
        mapped = selector.mapping.get(title)
        if mapped:
            desired_round = int(mapped)
            for season in show.seasons:
                if season.round_number == desired_round or season.display_number == desired_round:
                    return season
        return None

    if mode == "date":
        raw_value = _resolve_selector_value(selector, match_groups, "date")
        if not raw_value:
            return None
        parsed = _parse_date_string(raw_value)
        if not parsed:
            return None
        for season in show.seasons:
            for episode in season.episodes:
                if episode.originally_available == parsed:
                    return season
        return None

    LOGGER.warning("Unknown season selector mode '%s'", mode)
    return None


def _select_episode(
    pattern_config: PatternConfig,
    season: Season,
    session_lookup: SessionLookupIndex,
    match_groups: dict[str, str],
    trace: dict[str, Any] | None = None,
) -> Episode | None:
    group = pattern_config.episode_selector.group
    raw_value = match_groups.get(group)
    if raw_value is None:
        default_value = pattern_config.episode_selector.default_value
        if default_value:
            raw_value = default_value
    if raw_value is None:
        if pattern_config.episode_selector.allow_fallback_to_title:
            for candidate in reversed(sorted(session_lookup.keys(), key=len)):
                if candidate and candidate in normalize_token(" ".join(match_groups.values())):
                    raw_value = candidate
                    break
        if raw_value is None:
            return None

    def _strip_noise(normalized: str) -> str:
        # Collapse multiple consecutive whitespace to single space
        result = re.sub(r"\s+", " ", normalized).strip()
        for token in _NOISE_TOKENS:
            if token and token in result:
                result = result.replace(token, "")
        return result

    normalized = _strip_noise(normalize_token(raw_value))
    normalized_without_part: str | None = None
    if "part" in normalized:
        without_trailing = re.sub(r"part\d+$", "", normalized)
        without_embedded = re.sub(r"part\d+", "", without_trailing)
        cleaned = without_embedded.strip()
        normalized_without_part = cleaned or None

    def tokens_match(candidate: str, target: str) -> bool:
        if not candidate or not target:
            return False
        if candidate == target:
            return True
        if candidate.startswith(target) or target.startswith(candidate):
            return True
        return _tokens_close(candidate, target)

    lookup_attempts: list[tuple[str, str, str]] = []
    trace_lookup_records: list[dict[str, str]] = []
    seen_tokens: set[str] = set()

    def add_lookup(label: str, value: str | list[str] | None) -> None:
        if not value:
            return
        if isinstance(value, list):
            for item in value:
                add_lookup(label, item)
            return

        variants: list[str] = []
        source_variants: list[str] = []

        def push_variant(candidate: str | None) -> None:
            if not candidate:
                return
            if candidate in variants:
                return
            variants.append(candidate)
            source_variants.append(candidate)

        push_variant(value)

        split_variants = [segment for segment in re.split(r"[\s._-]+", value) if segment]
        if split_variants:
            push_variant(" ".join(split_variants))
            without_noise_words = " ".join(word for word in split_variants if _strip_noise(normalize_token(word)))
            push_variant(without_noise_words)
            for index in range(1, len(split_variants)):
                truncated = " ".join(split_variants[index:])
                push_variant(truncated)

        for variant in variants:
            normalized_variant = _strip_noise(normalize_token(variant))
            if not normalized_variant or normalized_variant in seen_tokens:
                continue
            seen_tokens.add(normalized_variant)
            lookup_attempts.append((label, variant, normalized_variant))
            if trace is not None:
                trace_lookup_records.append(
                    {
                        "label": label,
                        "value": variant,
                        "normalized": normalized_variant,
                    }
                )

    add_lookup("session", raw_value)

    if normalized_without_part and normalized_without_part not in seen_tokens:
        lookup_attempts.append(("session_without_part", raw_value, normalized_without_part))
        if trace is not None:
            trace_lookup_records.append(
                {
                    "label": "session_without_part",
                    "value": raw_value,
                    "normalized": normalized_without_part,
                }
            )
        seen_tokens.add(normalized_without_part)

    for key, value in match_groups.items():
        if key == group:
            continue
        add_lookup(key, value)

    away_value = match_groups.get("away")
    home_value = match_groups.get("home")
    separator_value = match_groups.get("separator")

    # Strip noise from team names (resolution, fps, providers, etc.)
    if away_value:
        away_value = _strip_team_noise(away_value)
        match_groups["away"] = away_value
    if home_value:
        home_value = _strip_team_noise(home_value)
        match_groups["home"] = home_value

    team_alias_map_name = pattern_config.metadata_filters.get("team_alias_map")
    alias_lookup = get_team_alias_map(team_alias_map_name) if team_alias_map_name else {}

    def canonicalize_team(value: str | None) -> str | None:
        if not value:
            return None
        if not alias_lookup:
            return None
        normalized_team = normalize_token(value)
        if not normalized_team:
            return None
        return alias_lookup.get(normalized_team)

    canonical_away = canonicalize_team(away_value)
    canonical_home = canonicalize_team(home_value)
    if canonical_away:
        away_value = canonical_away
        match_groups["away"] = canonical_away
    if canonical_home:
        home_value = canonical_home
        match_groups["home"] = canonical_home
    if canonical_away and canonical_home:
        canonical_session = f"{canonical_away} vs {canonical_home}"
        match_groups["session"] = canonical_session

    if away_value and home_value:
        separator_candidates: list[str] = []
        if separator_value:
            separator_candidates.append(separator_value)
        separator_candidates.extend(["at", "vs", "v", "@"])
        seen_separators: set[str] = set()
        for separator_candidate in separator_candidates:
            if not separator_candidate:
                continue
            normalized_separator = normalize_token(separator_candidate)
            if normalized_separator in seen_separators:
                continue
            seen_separators.add(normalized_separator)
            add_lookup("away_home", f"{away_value}.{separator_candidate}.{home_value}")
            add_lookup("away_home", f"{away_value} {separator_candidate} {home_value}")
            add_lookup("home_away", f"{home_value}.{separator_candidate}.{away_value}")
            add_lookup("home_away", f"{home_value} {separator_candidate} {away_value}")

    venue_value = match_groups.get("venue")
    if venue_value:
        add_lookup("venue+session", f"{venue_value} {raw_value}")
        add_lookup("session+venue", f"{raw_value} {venue_value}")

    # Parse date from match groups for proximity checking
    parsed_date = _parse_date_from_groups(match_groups)

    def find_episode_for_token(token: str) -> Episode | None:
        # First pass: find episodes that match the token
        matching_episodes: list[Episode] = []
        for episode in season.episodes:
            episode_token = normalize_token(episode.title)
            if tokens_match(episode_token, token):
                matching_episodes.append(episode)
                continue
            alias_tokens = [normalize_token(alias) for alias in episode.aliases]
            if any(tokens_match(alias_token, token) for alias_token in alias_tokens):
                matching_episodes.append(episode)

        if not matching_episodes:
            return None

        # If we have a date from the filename, filter by date proximity
        if parsed_date is not None:
            date_matched = [
                ep
                for ep in matching_episodes
                if _dates_within_proximity(parsed_date, ep.originally_available, tolerance_days=2)
            ]
            if date_matched:
                # Return the closest match by date
                return min(
                    date_matched,
                    key=lambda ep: abs((parsed_date - ep.originally_available).days)
                    if ep.originally_available
                    else 999,
                )
            # No date-matching episodes found - this is likely a mismatch
            # Only return a match if there's exactly one candidate (no ambiguity)
            if len(matching_episodes) == 1:
                return matching_episodes[0]
            return None

        # No date available, return first match (original behavior)
        return matching_episodes[0]

    lookup_attempts.sort(key=lambda item: len(item[2]), reverse=True)

    attempted_variants: list[str] = []

    for label, variant, normalized_variant in lookup_attempts:
        attempted_variants.append(f"{label}:{variant}")
        metadata_title = _resolve_session_lookup(session_lookup, normalized_variant)
        candidate_tokens: list[str] = []
        if metadata_title:
            target_token = normalize_token(metadata_title)
            candidate_tokens.append(target_token)
        candidate_tokens.append(normalized_variant)

        metadata_token = normalize_token(metadata_title) if metadata_title else None

        for token in candidate_tokens:
            if not token:
                continue
            if metadata_token and token == metadata_token:
                episode = next(
                    (item for item in season.episodes if normalize_token(item.title) == metadata_token),
                    None,
                )
                if episode:
                    if trace is not None:
                        trace["match"] = {
                            "label": label,
                            "value": variant,
                            "normalized": normalized_variant,
                            "token": token,
                            "episode_title": episode.title,
                            "matched_via_alias": False,
                        }
                        trace["lookup_attempts"] = trace_lookup_records
                    return episode
            episode = find_episode_for_token(token)
            if episode:
                if trace is not None:
                    trace["match"] = {
                        "label": label,
                        "value": variant,
                        "normalized": normalized_variant,
                        "token": token,
                        "episode_title": episode.title,
                        "matched_via_alias": normalize_token(episode.title) != token,
                    }
                    trace["lookup_attempts"] = trace_lookup_records
                return episode

    # Round-based episode resolution fallback for racing content
    # When session doesn't match episode title (e.g., "Race" vs "The Thermal Club IndyCar Grand Prix"),
    # fallback to finding episode by round number with optional location fuzzy matching
    round_value = match_groups.get("round")
    if round_value:
        try:
            round_number = int(round_value)
            location_value = match_groups.get("location")

            # Find candidate episodes by round number (matching index or display_number)
            round_episodes = [
                ep for ep in season.episodes if ep.index == round_number or ep.display_number == round_number
            ]

            if round_episodes:
                # If location is available, prefer episodes where location appears in title
                if location_value:
                    location_normalized = normalize_token(location_value)
                    if location_normalized:
                        for episode in round_episodes:
                            title_normalized = normalize_token(episode.title)
                            if title_normalized and _location_matches_title(location_normalized, title_normalized):
                                if trace is not None:
                                    trace["match"] = {
                                        "label": "round+location",
                                        "value": f"round={round_value}, location={location_value}",
                                        "normalized": f"{round_number}+{location_normalized}",
                                        "token": title_normalized,
                                        "episode_title": episode.title,
                                        "matched_via_round_fallback": True,
                                    }
                                    trace["lookup_attempts"] = trace_lookup_records
                                return episode

                # No location match found, return first episode for this round
                episode = round_episodes[0]
                if trace is not None:
                    trace["match"] = {
                        "label": "round",
                        "value": round_value,
                        "normalized": str(round_number),
                        "token": normalize_token(episode.title),
                        "episode_title": episode.title,
                        "matched_via_round_fallback": True,
                    }
                    trace["lookup_attempts"] = trace_lookup_records
                return episode
        except ValueError:
            pass  # Round value wasn't a valid integer

    # Date-based episode resolution fallback
    # When session name lookup fails but we have date information (e.g., Figure Skating "16 11"),
    # fallback to finding episode by date proximity
    fallback_date = parsed_date
    if fallback_date is None:
        # Try to parse event_date group if available (partial date like "16 11")
        event_date_value = match_groups.get("event_date")
        if event_date_value:
            # Get reference year from match groups
            reference_year_str = match_groups.get("year") or match_groups.get("date_year")
            reference_year = int(reference_year_str) if reference_year_str else None
            fallback_date = _parse_date_string(event_date_value, reference_year=reference_year)

    if fallback_date is not None:
        # Find episodes with dates within proximity of the fallback date
        date_candidates: list[tuple[Episode, int]] = []
        for episode in season.episodes:
            if episode.originally_available is not None:
                if _dates_within_proximity(fallback_date, episode.originally_available, tolerance_days=2):
                    delta = abs((fallback_date - episode.originally_available).days)
                    date_candidates.append((episode, delta))

        if date_candidates:
            # Sort by closest date match and return the best
            date_candidates.sort(key=lambda item: item[1])
            best_episode, best_delta = date_candidates[0]
            if trace is not None:
                trace["match"] = {
                    "label": "date_fallback",
                    "value": fallback_date.isoformat(),
                    "normalized": fallback_date.isoformat(),
                    "token": normalize_token(best_episode.title),
                    "episode_title": best_episode.title,
                    "matched_via_date_fallback": True,
                    "date_delta_days": best_delta,
                }
                trace["lookup_attempts"] = trace_lookup_records
            return best_episode

    if attempted_variants:
        match_groups["_attempted_session_tokens"] = attempted_variants
    if trace is not None:
        trace.setdefault("match", None)
        trace["lookup_attempts"] = trace_lookup_records
    return None


def _find_episode_across_seasons(
    pattern_config: PatternConfig,
    show: Show,
    match_groups: dict[str, str],
    *,
    exclude_season: Season | None = None,
    trace_enabled: bool = False,
) -> tuple[Season, Episode, dict[str, str], SessionLookupIndex, dict[str, Any] | None] | None:
    for candidate in show.seasons:
        if exclude_season and candidate is exclude_season:
            continue
        candidate_groups = dict(match_groups)
        session_lookup = _build_session_lookup(pattern_config, candidate)
        episode_trace: dict[str, Any] | None = {} if trace_enabled else None
        episode = _select_episode(
            pattern_config,
            candidate,
            session_lookup,
            candidate_groups,
            trace=episode_trace,
        )
        if episode:
            return candidate, episode, candidate_groups, session_lookup, episode_trace
    return None


_TEAM_PATTERN = re.compile(r"(?P<a>[A-Za-z0-9 .&'/-]+?)\s+(?:vs|v|at|@)\s+(?P<b>[A-Za-z0-9 .&'/-]+)", re.IGNORECASE)
_NOISE_PROVIDERS = {"sky", "fubo", "espn", "espn+", "espnplus", "tsn", "nbcsn", "fox", "verum"}


def _strip_team_noise(value: str) -> str:
    tokens = value.split()
    cleaned: list[str] = []
    for token in tokens:
        lowered = token.lower()
        if lowered.isdigit():
            break
        if re.match(r"\d{3,4}p", lowered):
            break
        if re.match(r"\d{2}fps", lowered):
            break
        if lowered.replace("+", "") in _NOISE_PROVIDERS:
            break
        if lowered in {"proper", "repack", "web", "hdtv"}:
            break
        cleaned.append(token)
    return " ".join(cleaned).strip()


def _extract_teams_from_text(text: str, alias_lookup: dict[str, str]) -> list[str]:
    match = _TEAM_PATTERN.search(text)
    if not match:
        return []
    teams: list[str] = []
    for key in ("a", "b"):
        raw_team = _strip_team_noise(match.group(key))
        normalized = normalize_token(raw_team)
        mapped = alias_lookup.get(normalized, raw_team.strip())
        if mapped:
            teams.append(mapped)
    return teams


def _build_team_alias_lookup(show: Show, base: dict[str, str]) -> dict[str, str]:
    lookup = dict(base)
    for season in show.seasons:
        for episode in season.episodes:
            episode_teams = _extract_teams_from_text(episode.title, lookup)
            for team in episode_teams:
                token = normalize_token(team)
                if token and token not in lookup:
                    lookup[token] = team
            for alias in episode.aliases:
                alias_teams = _extract_teams_from_text(alias, lookup)
                if episode_teams and alias_teams and len(alias_teams) == len(episode_teams):
                    for canonical, alias_team in zip(episode_teams, alias_teams):
                        token = normalize_token(alias_team)
                        if token and token not in lookup:
                            lookup[token] = canonical
                alias_token = normalize_token(alias)
                if alias_token and alias_token not in lookup:
                    lookup[alias_token] = episode.title
    return lookup


def _score_structured_match(
    structured: StructuredName, season: Season, episode: Episode, alias_lookup: dict[str, str]
) -> float:
    score = 0.0
    episode_teams = _extract_teams_from_text(episode.title, alias_lookup)
    # Resolve structured teams through alias lookup before comparing
    # This allows "Celtics" to match "Boston Celtics" via the alias map
    structured_tokens = set()
    for team in structured.teams:
        if team:
            normalized = normalize_token(team)
            # Look up the alias to get canonical name, then normalize that
            resolved = alias_lookup.get(normalized, team)
            structured_tokens.add(normalize_token(resolved))
    episode_tokens = {normalize_token(team) for team in episode_teams if team}

    # Date proximity check - critical for sports where same teams play multiple times
    # If both dates are available, they MUST be within proximity for a valid match
    if structured.date and episode.originally_available:
        if not _dates_within_proximity(structured.date, episode.originally_available, tolerance_days=2):
            # Dates are too far apart - this is likely a different game between the same teams
            return 0.0
        # Dates match within proximity - this is a strong indicator
        score += 0.4

    if structured_tokens and episode_tokens:
        if structured_tokens == episode_tokens:
            score += 0.55
        else:
            overlap = structured_tokens.intersection(episode_tokens)

            # For team sports matchups (2+ teams), reject partial matches
            # This prevents matching "Pacers vs Celtics" to "Celtics vs Heat"
            if len(structured.teams) >= 2 and len(overlap) < len(structured_tokens):
                # Partial match - some teams missing
                # This is likely a wrong match (different game, same teams)
                return 0.0

            # All teams present (might be reordered) or single-team content
            if overlap:
                score += 0.35 + 0.05 * len(overlap)
    elif structured_tokens:
        combined = normalize_token(" ".join(structured.teams))
        if combined and _token_similarity(combined, normalize_token(episode.title)) >= 0.7:
            score += 0.3

    # Year-only match (less specific than full date)
    if not structured.date and structured.year and episode.originally_available:
        if episode.originally_available.year == structured.year:
            score += 0.1

    if structured.round and (season.round_number == structured.round or season.display_number == structured.round):
        score += 0.1
    return score


def _structured_match(
    filename: str,
    sport: SportConfig,
    show: Show,
    diagnostics: list[tuple[str, str]] | None = None,
    trace: dict[str, Any] | None = None,
) -> dict[str, object] | None:
    configured_aliases = get_team_alias_map(sport.team_alias_map)
    alias_lookup = _build_team_alias_lookup(show, configured_aliases)

    structured = parse_structured_filename(filename, alias_lookup)
    if not structured:
        return None

    # Validate structured parsing - if a "team" is actually the competition name, parsing failed
    if structured.competition and structured.teams:
        competition_normalized = normalize_token(structured.competition)
        for team in structured.teams:
            if normalize_token(team) == competition_normalized:
                # Parser extracted sport name as a team - this is a parsing error
                # Skip structured matching and fall back to pattern-based matching
                return None

    best: tuple[Season, Episode] | None = None
    best_score = 0.0

    for season in show.seasons:
        for episode in season.episodes:
            score = _score_structured_match(structured, season, episode, alias_lookup)
            if score > best_score:
                best_score = score
                best = (season, episode)

    if best and best_score >= 0.6:
        season, episode = best
        groups: dict[str, object] = {
            "structured_competition": structured.competition,
            "structured_date": structured.date.isoformat() if structured.date else None,
            "structured_matchup": structured.canonical_matchup(),
            "structured_provider": structured.provider,
            "structured_resolution": structured.resolution,
            "structured_fps": structured.fps,
            "structured_canonical": build_canonical_filename(structured),
        }
        groups = {key: value for key, value in groups.items() if value is not None}

        pattern_config = PatternConfig(regex="structured", description="Structured filename matcher")
        pattern = PatternRuntime(
            config=pattern_config,
            regex=re.compile("structured"),
            session_lookup=SessionLookupIndex(),
        )

        if diagnostics is not None:
            diagnostics.append(("info", "Matched via structured filename parser"))

        if trace is not None:
            trace.setdefault("attempts", [])
            trace["attempts"].append(
                {"pattern": "structured", "status": "matched", "groups": dict(groups), "score": best_score}
            )
            trace["status"] = "matched"
            trace["result"] = {
                "season": {
                    "title": season.title,
                    "round_number": season.round_number,
                    "display_number": season.display_number,
                },
                "episode": {
                    "title": episode.title,
                    "index": episode.index,
                    "display_number": episode.display_number,
                },
                "pattern": "structured",
            }

        return {
            "season": season,
            "episode": episode,
            "pattern": pattern,
            "groups": groups,
        }

    return None


def compile_patterns(sport: SportConfig) -> list[PatternRuntime]:
    compiled: list[PatternRuntime] = []
    for pattern in sport.patterns:
        compiled.append(
            PatternRuntime(
                config=pattern,
                regex=pattern.compiled_regex(),
                session_lookup=SessionLookupIndex(),
            )
        )
    return compiled


def match_file_to_episode(
    filename: str,
    sport: SportConfig,
    show: Show,
    patterns: list[PatternRuntime],
    *,
    diagnostics: list[tuple[str, str]] | None = None,
    trace: dict[str, Any] | None = None,
    suppress_warnings: bool = False,
) -> dict[str, object] | None:
    matched_patterns = 0
    failed_resolutions: list[str] = []
    trace_attempts: list[dict[str, Any]] | None = None
    if trace is not None:
        trace_attempts = trace.setdefault("attempts", [])
        trace.setdefault("messages", [])
        trace["matched_patterns"] = 0

    def record(severity: str, message: str) -> None:
        if diagnostics is not None:
            diagnostics.append((severity, message))
        if trace is not None:
            trace["messages"].append({"severity": severity, "message": message})

    def summarize_groups(groups: dict[str, str]) -> str:
        if not groups:
            return "none"
        parts = [f"{key}={value!r}" for key, value in sorted(groups.items()) if not key.startswith("_")]
        return ", ".join(parts)

    def summarize_episode_candidates(season: Season, *, limit: int = 5) -> str:
        titles = [episode.title for episode in season.episodes[:limit]]
        if len(season.episodes) > limit:
            titles.append("…")
        return ", ".join(titles) if titles else "none"

    structured_result = _structured_match(
        filename,
        sport,
        show,
        diagnostics=diagnostics,
        trace=trace,
    )
    if structured_result:
        return structured_result

    for pattern_runtime in patterns:
        descriptor = pattern_runtime.config.description or pattern_runtime.config.regex
        match = pattern_runtime.regex.search(filename)
        if not match:
            if trace_attempts is not None:
                trace_attempts.append(
                    {
                        "pattern": descriptor,
                        "regex": pattern_runtime.config.regex,
                        "status": "regex-no-match",
                    }
                )
            continue

        matched_patterns += 1
        if trace is not None:
            trace["matched_patterns"] = matched_patterns
        groups = {key: value for key, value in match.groupdict().items() if value is not None}
        if "date_year" not in groups and {"year", "month", "day"}.issubset(groups.keys()):
            groups["date_year"] = groups["year"]
        fallback_by_matchup = bool(pattern_runtime.config.metadata_filters.get("fallback_matchup_season"))
        season = _select_season(show, pattern_runtime.config.season_selector, groups)
        episode: Episode | None = None
        episode_trace: dict[str, Any] | None = None
        if not season and fallback_by_matchup:
            fallback = _find_episode_across_seasons(
                pattern_runtime.config,
                show,
                groups,
                trace_enabled=trace is not None,
            )
            if fallback:
                season, episode, groups, pattern_runtime.session_lookup, episode_trace = fallback

        if not season:
            selector = pattern_runtime.config.season_selector
            selector_group = selector.group or selector.mode or "season"
            candidate_value = groups.get(selector.group or selector.mode or "season")
            message = (
                f"{descriptor}: season not resolved "
                f"(selector mode={selector.mode!r}, group={selector_group!r}, "
                f"value={candidate_value!r}, groups={summarize_groups(groups)})"
            )
            LOGGER.debug("Season not resolved for file %s with pattern %s", filename, pattern_runtime.config.regex)
            failed_resolutions.append(message)
            severity = "ignored" if (sport.allow_unmatched or suppress_warnings) else "warning"
            record(severity, message)
            if trace_attempts is not None:
                trace_attempts.append(
                    {
                        "pattern": descriptor,
                        "regex": pattern_runtime.config.regex,
                        "status": "season-unresolved",
                        "season_selector": {
                            "mode": selector.mode,
                            "group": selector.group,
                            "value": candidate_value,
                        },
                        "groups": dict(groups),
                        "message": message,
                    }
                )
            continue

        if episode is None:
            pattern_runtime.session_lookup = _build_session_lookup(pattern_runtime.config, season)
            episode_trace = {}
            episode = _select_episode(
                pattern_runtime.config,
                season,
                pattern_runtime.session_lookup,
                groups,
                trace=episode_trace,
            )

        if not episode and fallback_by_matchup:
            fallback = _find_episode_across_seasons(
                pattern_runtime.config,
                show,
                groups,
                exclude_season=season,
                trace_enabled=trace is not None,
            )
            if fallback:
                season, episode, groups, pattern_runtime.session_lookup, episode_trace = fallback

        if not episode:
            selector = pattern_runtime.config.episode_selector
            raw_value = groups.get(selector.group)
            normalized_value = normalize_token(raw_value) if raw_value else None
            attempted_tokens = groups.pop("_attempted_session_tokens", None)
            attempted_display = ""
            if attempted_tokens:
                max_items = 5
                display_items = list(attempted_tokens[:max_items])
                if len(attempted_tokens) > max_items:
                    display_items.append("…")
                attempted_display = f", attempted={'; '.join(display_items)}"
            message = (
                f"{descriptor}: episode not resolved "
                f"(group={selector.group!r}, raw_value={raw_value!r}, normalized={normalized_value!r}, "
                f"season='{season.title}', candidates={summarize_episode_candidates(season)}, "
                f"groups={summarize_groups(groups)}{attempted_display})"
            )
            LOGGER.debug(
                "Episode not resolved for file %s in season %s using pattern %s",
                filename,
                season.title,
                pattern_runtime.config.regex,
            )
            failed_resolutions.append(message)
            severity = "ignored" if (sport.allow_unmatched or suppress_warnings) else "warning"
            record(severity, message)
            if trace_attempts is not None:
                trace_entry = {
                    "pattern": descriptor,
                    "regex": pattern_runtime.config.regex,
                    "status": "episode-unresolved",
                    "season": {
                        "title": season.title,
                        "round_number": season.round_number,
                        "display_number": season.display_number,
                    },
                    "episode_selector": {
                        "group": selector.group,
                        "allow_fallback_to_title": selector.allow_fallback_to_title,
                    },
                    "groups": dict(groups),
                    "message": message,
                }
                if episode_trace:
                    trace_entry["episode_trace"] = episode_trace
                trace_attempts.append(trace_entry)
            continue

        groups_for_trace = dict(groups)
        result = {
            "season": season,
            "episode": episode,
            "pattern": pattern_runtime,
            "groups": groups,
        }
        if trace_attempts is not None:
            trace_entry = {
                "pattern": descriptor,
                "regex": pattern_runtime.config.regex,
                "status": "matched",
                "groups": groups_for_trace,
                "season": {
                    "title": season.title,
                    "round_number": season.round_number,
                    "display_number": season.display_number,
                },
                "episode": {
                    "title": episode.title,
                    "index": episode.index,
                    "display_number": episode.display_number,
                },
            }
            if episode_trace:
                trace_entry["episode_trace"] = episode_trace
            trace_attempts.append(trace_entry)
            trace["status"] = "matched"
            trace["result"] = {
                "season": trace_entry["season"],
                "episode": trace_entry["episode"],
                "pattern": descriptor,
            }
        return result
    if failed_resolutions:
        log_fn = LOGGER.debug if (sport.allow_unmatched or suppress_warnings) else LOGGER.warning
        log_fn(
            "File %s matched %d pattern(s) but could not resolve:%s%s",
            filename,
            matched_patterns,
            "\n  - " if len(failed_resolutions) > 1 else " ",
            "\n  - ".join(failed_resolutions) if len(failed_resolutions) > 1 else failed_resolutions[0],
        )
        message = f"Matched {matched_patterns} pattern(s) but could not resolve: {'; '.join(failed_resolutions)}"
        severity = "ignored" if (sport.allow_unmatched or suppress_warnings) else "warning"
        record(severity, message)
        if trace is not None:
            trace["status"] = "unresolved"
    elif matched_patterns == 0:
        LOGGER.debug("File %s did not match any configured patterns", filename)
        record("ignored", "Did not match any configured patterns")
        if trace is not None:
            trace["status"] = "no-match"
    return None
