"""Matcher package for pattern-based file matching.

This package provides the core matching logic for Playbook, including:
- Pattern compilation and runtime management
- Season and episode selection
- Team name resolution
- Structured filename parsing
- Fuzzy matching utilities

Public API:
- PatternRuntime: Runtime representation of a compiled pattern
- compile_patterns: Compile pattern configs for a sport
- match_file_to_episode: Match a filename to an episode

Example:
    from playbook.matcher import compile_patterns, match_file_to_episode

    patterns = compile_patterns(sport_config)
    result = match_file_to_episode(filename, sport_config, show, patterns)
    if result:
        season = result["season"]
        episode = result["episode"]
"""

from .core import DEFAULT_GENERIC_SESSION_ALIASES, PatternRuntime
from .date_utils import dates_within_proximity, parse_date_from_groups, parse_date_string
from .orchestrator import compile_patterns, match_file_to_episode
from .session_resolver import build_session_lookup, resolve_session_lookup
from .similarity import location_matches_title
from .structured import score_structured_match
from .team_resolver import build_team_alias_lookup, extract_teams_from_text, strip_team_noise

# Public API
__all__ = [
    "PatternRuntime",
    "compile_patterns",
    "match_file_to_episode",
]

# Backwards compatibility aliases for internal functions used by tests
# These are prefixed with underscore in the original module
_build_session_lookup = build_session_lookup
_build_team_alias_lookup = build_team_alias_lookup
_dates_within_proximity = dates_within_proximity
_DEFAULT_GENERIC_SESSION_ALIASES = DEFAULT_GENERIC_SESSION_ALIASES
_location_matches_title = location_matches_title
_parse_date_from_groups = parse_date_from_groups
_parse_date_string = parse_date_string
_resolve_session_lookup = resolve_session_lookup
_score_structured_match = score_structured_match
_strip_team_noise = strip_team_noise
_extract_teams_from_text = extract_teams_from_text
