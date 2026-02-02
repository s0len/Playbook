"""Episode selection logic within a season.

This module handles the complex logic of matching a filename to a specific
episode within a season, including session lookup, team matching, date
proximity checks, and various fallback strategies.
"""

from __future__ import annotations

import re
from typing import Any

from ..config import PatternConfig
from ..models import Episode, Season, Show
from ..session_index import SessionLookupIndex
from ..team_aliases import get_team_alias_map
from ..utils import normalize_token
from .core import NOISE_TOKENS
from .date_utils import dates_within_proximity, parse_date_from_groups, parse_date_string
from .session_resolver import build_session_lookup, resolve_session_lookup
from .similarity import location_matches_title, tokens_close
from .team_resolver import canonicalize_team, strip_team_noise


def _strip_noise(normalized: str) -> str:
    """Strip noise tokens from a normalized session string."""
    # Collapse multiple consecutive whitespace to single space
    result = re.sub(r"\s+", " ", normalized).strip()
    for token in NOISE_TOKENS:
        if token and token in result:
            result = result.replace(token, "")
    return result


def _tokens_match(candidate: str, target: str) -> bool:
    """Check if two tokens match (exact, prefix, or fuzzy)."""
    if not candidate or not target:
        return False
    if candidate == target:
        return True
    if candidate.startswith(target) or target.startswith(candidate):
        return True
    return tokens_close(candidate, target)


def select_episode(
    pattern_config: PatternConfig,
    season: Season,
    session_lookup: SessionLookupIndex,
    match_groups: dict[str, str],
    trace: dict[str, Any] | None = None,
) -> Episode | None:
    """Select the matching episode within a season.

    Tries multiple strategies:
    1. Direct session name lookup
    2. Team-based matchup matching
    3. Round-based fallback (for racing)
    4. Date-based fallback

    Args:
        pattern_config: Pattern configuration with selectors
        season: Season to search within
        session_lookup: Pre-built session lookup index
        match_groups: Regex capture groups from pattern match
        trace: Optional trace dict for debugging

    Returns:
        Matched Episode or None
    """
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

    normalized = _strip_noise(normalize_token(raw_value))
    normalized_without_part: str | None = None
    if "part" in normalized:
        without_trailing = re.sub(r"part\d+$", "", normalized)
        without_embedded = re.sub(r"part\d+", "", without_trailing)
        cleaned = without_embedded.strip()
        normalized_without_part = cleaned or None

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
        away_value = strip_team_noise(away_value)
        match_groups["away"] = away_value
    if home_value:
        home_value = strip_team_noise(home_value)
        match_groups["home"] = home_value

    team_alias_map_name = pattern_config.metadata_filters.get("team_alias_map")
    alias_lookup = get_team_alias_map(team_alias_map_name) if team_alias_map_name else {}

    canonical_away = canonicalize_team(away_value, alias_lookup)
    canonical_home = canonicalize_team(home_value, alias_lookup)
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
    parsed_date = parse_date_from_groups(match_groups)

    def find_episode_for_token(token: str) -> Episode | None:
        # First pass: find episodes that match the token
        matching_episodes: list[Episode] = []
        for episode in season.episodes:
            episode_token = normalize_token(episode.title)
            if _tokens_match(episode_token, token):
                matching_episodes.append(episode)
                continue
            alias_tokens = [normalize_token(alias) for alias in episode.aliases]
            if any(_tokens_match(alias_token, token) for alias_token in alias_tokens):
                matching_episodes.append(episode)

        if not matching_episodes:
            return None

        # If we have a date from the filename, filter by date proximity
        if parsed_date is not None:
            date_matched = [
                ep
                for ep in matching_episodes
                if dates_within_proximity(parsed_date, ep.originally_available, tolerance_days=2)
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
        metadata_title = resolve_session_lookup(session_lookup, normalized_variant)
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
                            if title_normalized and location_matches_title(location_normalized, title_normalized):
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
            fallback_date = parse_date_string(event_date_value, reference_year=reference_year)

    if fallback_date is not None:
        # Find episodes with dates within proximity of the fallback date
        date_candidates: list[tuple[Episode, int]] = []
        for episode in season.episodes:
            if episode.originally_available is not None:
                if dates_within_proximity(fallback_date, episode.originally_available, tolerance_days=2):
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


def find_episode_across_seasons(
    pattern_config: PatternConfig,
    show: Show,
    match_groups: dict[str, str],
    *,
    exclude_season: Season | None = None,
    trace_enabled: bool = False,
) -> tuple[Season, Episode, dict[str, str], SessionLookupIndex, dict[str, Any] | None] | None:
    """Search for an episode across all seasons in a show.

    Used as a fallback when season selection fails or matchup-based matching
    is enabled (for team sports).

    Args:
        pattern_config: Pattern configuration
        show: Show to search across
        match_groups: Regex capture groups
        exclude_season: Season to skip (already checked)
        trace_enabled: Whether to collect trace information

    Returns:
        Tuple of (season, episode, groups, session_lookup, trace) or None
    """
    for candidate in show.seasons:
        if exclude_season and candidate is exclude_season:
            continue
        candidate_groups = dict(match_groups)
        session_lookup = build_session_lookup(pattern_config, candidate)
        episode_trace: dict[str, Any] | None = {} if trace_enabled else None
        episode = select_episode(
            pattern_config,
            candidate,
            session_lookup,
            candidate_groups,
            trace=episode_trace,
        )
        if episode:
            return candidate, episode, candidate_groups, session_lookup, episode_trace
    return None
