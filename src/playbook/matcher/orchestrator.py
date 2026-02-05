"""Main matcher orchestration - compiles patterns and coordinates matching.

This module provides the main entry points for the matcher package:
- compile_patterns: Compile pattern configs into PatternRuntime objects
- match_file_to_episode: Match a filename to an episode
"""

from __future__ import annotations

import logging
from typing import Any

from ..config import SportConfig
from ..models import Episode, Season, Show
from ..session_index import SessionLookupIndex
from ..utils import normalize_token
from .core import PatternRuntime
from .episode_selector import find_episode_across_seasons, select_episode
from .season_selector import select_season
from .session_resolver import build_session_lookup
from .structured import structured_match

LOGGER = logging.getLogger(__name__)


def compile_patterns(sport: SportConfig) -> list[PatternRuntime]:
    """Compile pattern configurations into runtime objects.

    Creates PatternRuntime objects with compiled regex patterns.
    Session lookup indices are built lazily when needed for each season.

    Args:
        sport: Sport configuration containing pattern definitions

    Returns:
        List of PatternRuntime objects ready for matching
    """
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
    """Match a filename to an episode in a show.

    Tries structured matching first (for team sports), then pattern-based
    matching with various fallback strategies.

    Args:
        filename: Filename to match (without path)
        sport: Sport configuration
        show: Show to match against
        patterns: List of compiled PatternRuntime objects
        diagnostics: Optional list to collect diagnostic messages
        trace: Optional trace dict for debugging
        suppress_warnings: If True, suppress warning-level logs

    Returns:
        Match dict with season, episode, pattern, groups - or None if no match
    """
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
            titles.append("...")
        return ", ".join(titles) if titles else "none"

    # Try structured matching first (for team sports)
    structured_result = structured_match(
        filename,
        sport,
        show,
        diagnostics=diagnostics,
        trace=trace,
    )
    if structured_result:
        return structured_result

    # Pattern-based matching
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

        # Check if captured year matches sport's variant year (for year-based filtering)
        # This prevents a 2026 file from being matched by a 2025 sport variant
        if sport.variant_year is not None and "year" in groups:
            try:
                captured_year = int(groups["year"])
                if captured_year != sport.variant_year:
                    if trace_attempts is not None:
                        trace_attempts.append(
                            {
                                "pattern": descriptor,
                                "regex": pattern_runtime.config.regex,
                                "status": "year-mismatch",
                                "captured_year": captured_year,
                                "variant_year": sport.variant_year,
                            }
                        )
                    continue  # Skip this sport variant, let another variant handle it
            except (ValueError, TypeError):
                pass  # Non-numeric year, proceed normally

        # Ensure date_year is set if we have year/month/day groups
        if "date_year" not in groups and {"year", "month", "day"}.issubset(groups.keys()):
            groups["date_year"] = groups["year"]

        fallback_by_matchup = bool(pattern_runtime.config.metadata_filters.get("fallback_matchup_season"))
        season = select_season(show, pattern_runtime.config.season_selector, groups)
        episode: Episode | None = None
        episode_trace: dict[str, Any] | None = None

        # Cross-season matchup fallback if season selection failed
        if not season and fallback_by_matchup:
            fallback = find_episode_across_seasons(
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

        # Episode selection
        if episode is None:
            pattern_runtime.session_lookup = build_session_lookup(pattern_runtime.config, season)
            episode_trace = {}
            episode = select_episode(
                pattern_runtime.config,
                season,
                pattern_runtime.session_lookup,
                groups,
                trace=episode_trace,
            )

        # Cross-season matchup fallback if episode selection failed
        if not episode and fallback_by_matchup:
            fallback = find_episode_across_seasons(
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
                    display_items.append("...")
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

        # Success! We have a match
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

    # No match found
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
