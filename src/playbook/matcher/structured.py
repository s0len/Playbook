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
from .similarity import token_similarity
from .team_resolver import build_team_alias_lookup, extract_teams_from_text

# Maximum distance (in days) between a filename date and an episode date for the
# two to describe the same fixture.
DATE_TOLERANCE_DAYS = 2

# Score awarded for the date term, by absolute day distance. The term is monotonic
# rather than flat so that two fixtures between the same teams a day or two apart
# cannot tie on the date alone - the closer date always wins outright.
DATE_PROXIMITY_SCORES = {0: 0.40, 1: 0.30, 2: 0.20}

# Minimum score for a structured match to be accepted.
MATCH_THRESHOLD = 0.6

# Scores are sums of float literals, so equal candidates compare exactly; the
# epsilon only guards against accumulated representation error.
_SCORE_EPSILON = 1e-9


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
        distance = abs((structured.date - episode.originally_available).days)
        if distance > DATE_TOLERANCE_DAYS:
            # Dates are too far apart - this is likely a different game between the same teams
            return 0.0
        # Dates match within proximity - this is a strong indicator, weighted by how
        # close they are so a back-to-back fixture cannot tie with the exact date.
        score += DATE_PROXIMITY_SCORES.get(distance, min(DATE_PROXIMITY_SCORES.values()))

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

    best_candidates: list[tuple[Season, Episode]] = []
    best_score = 0.0

    for season in show.seasons:
        for episode in season.episodes:
            score = score_structured_match(structured, season, episode, alias_lookup)
            if score <= 0.0:
                continue
            if score > best_score + _SCORE_EPSILON:
                best_score = score
                best_candidates = [(season, episode)]
            elif score >= best_score - _SCORE_EPSILON:
                best_candidates.append((season, episode))

    if best_candidates and best_score >= MATCH_THRESHOLD:
        # Several episodes tied at the top score means the filename does not identify a
        # single fixture - most often duplicated metadata (the same game listed in both a
        # pre-season and a regular-season season), or a dateless filename whose teams meet
        # several times a season. Declining hands the file to the pattern loop rather than
        # picking one at random; if no pattern claims it either, it surfaces as unmatched.
        distinct = {(s.index, s.title, e.index, e.title) for s, e in best_candidates}
        if len(distinct) > 1:
            summary = ", ".join(f"{s.title} / {e.title}" for s, e in best_candidates[:4])
            if len(best_candidates) > 4:
                summary += ", ..."
            if diagnostics is not None:
                diagnostics.append(
                    (
                        "warning",
                        f"Ambiguous structured match: {len(distinct)} candidates tied at "
                        f"score {best_score:.2f} ({summary})",
                    )
                )
            if trace is not None:
                trace.setdefault("attempts", [])
                trace["attempts"].append(
                    {
                        "pattern": "structured",
                        "status": "ambiguous",
                        "score": best_score,
                        "candidates": [
                            {"season": s.title, "episode": e.title, "season_index": s.index}
                            for s, e in best_candidates[:8]
                        ],
                    }
                )
            return None

        season, episode = best_candidates[0]
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
