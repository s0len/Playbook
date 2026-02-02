"""Structured filename matching for team sports.

This module provides matching logic for files with structured naming patterns
like "NHL 2025-01-15 Team A vs Team B.mkv" - extracting metadata directly
from the filename structure.
"""

from __future__ import annotations

import re
from typing import Any

from ..config import PatternConfig, SportConfig
from ..models import Episode, Season, Show
from ..parsers.structured_filename import StructuredName, build_canonical_filename, parse_structured_filename
from ..session_index import SessionLookupIndex
from ..team_aliases import get_team_alias_map
from ..utils import normalize_token
from .core import PatternRuntime
from .date_utils import dates_within_proximity
from .similarity import token_similarity
from .team_resolver import build_team_alias_lookup, extract_teams_from_text


def score_structured_match(
    structured: StructuredName, season: Season, episode: Episode, alias_lookup: dict[str, str]
) -> float:
    """Calculate match score between a structured filename and an episode.

    Scores are based on team matches, date proximity, and other factors.

    Args:
        structured: Parsed structured filename
        season: Candidate season
        episode: Candidate episode
        alias_lookup: Team alias lookup dictionary

    Returns:
        Match score between 0.0 and 1.0
    """
    score = 0.0
    episode_teams = extract_teams_from_text(episode.title, alias_lookup)

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
        if not dates_within_proximity(structured.date, episode.originally_available, tolerance_days=2):
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
        if combined and token_similarity(combined, normalize_token(episode.title)) >= 0.7:
            score += 0.3

    # Year-only match (less specific than full date)
    if not structured.date and structured.year and episode.originally_available:
        if episode.originally_available.year == structured.year:
            score += 0.1

    if structured.round and (season.round_number == structured.round or season.display_number == structured.round):
        score += 0.1

    return score


def structured_match(
    filename: str,
    sport: SportConfig,
    show: Show,
    diagnostics: list[tuple[str, str]] | None = None,
    trace: dict[str, Any] | None = None,
) -> dict[str, object] | None:
    """Attempt to match a file using structured filename parsing.

    Parses the filename to extract teams, date, etc. and matches against
    episode metadata.

    Args:
        filename: Filename to match
        sport: Sport configuration
        show: Show to match against
        diagnostics: Optional list to collect diagnostic messages
        trace: Optional trace dict for debugging

    Returns:
        Match dict with season, episode, pattern, groups - or None
    """
    configured_aliases = get_team_alias_map(sport.team_alias_map)
    alias_lookup = build_team_alias_lookup(show, configured_aliases)

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
            score = score_structured_match(structured, season, episode, alias_lookup)
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
