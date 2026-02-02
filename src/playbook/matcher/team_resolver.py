"""Team name resolution and noise stripping utilities.

This module handles team name canonicalization through alias lookups
and noise word stripping from team names in filenames.
"""

from __future__ import annotations

import re

from ..team_aliases import get_team_alias_map
from ..utils import normalize_token
from .similarity import token_similarity

# Regex pattern to extract teams from matchup strings
TEAM_PATTERN = re.compile(r"(?P<a>[A-Za-z0-9 .&'/-]+?)\s+(?:vs|v|at|@)\s+(?P<b>[A-Za-z0-9 .&'/-]+)", re.IGNORECASE)

# Noise provider tokens to strip from team names
NOISE_PROVIDERS = {"sky", "fubo", "espn", "espn+", "espnplus", "tsn", "nbcsn", "fox", "verum"}


def strip_team_noise(value: str) -> str:
    """Strip noise (resolution, fps, providers, etc.) from team name.

    Args:
        value: Raw team name string

    Returns:
        Cleaned team name
    """
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
        if lowered.replace("+", "") in NOISE_PROVIDERS:
            break
        if lowered in {"proper", "repack", "web", "hdtv"}:
            break
        cleaned.append(token)
    return " ".join(cleaned).strip()


def extract_teams_from_text(text: str, alias_lookup: dict[str, str]) -> list[str]:
    """Extract team names from matchup text like "Team A vs Team B".

    Args:
        text: Text containing a matchup pattern
        alias_lookup: Team alias lookup dictionary

    Returns:
        List of resolved team names (0-2 teams)
    """
    match = TEAM_PATTERN.search(text)
    if not match:
        return []
    teams: list[str] = []
    for key in ("a", "b"):
        raw_team = strip_team_noise(match.group(key))
        normalized = normalize_token(raw_team)
        mapped = alias_lookup.get(normalized, raw_team.strip())
        if mapped:
            teams.append(mapped)
    return teams


def build_team_alias_lookup(show, base: dict[str, str]) -> dict[str, str]:
    """Build an extended team alias lookup from show metadata.

    Adds team names found in episode titles and aliases to the base lookup.

    Args:
        show: Show containing seasons and episodes
        base: Base team alias map from configuration

    Returns:
        Extended alias lookup dictionary
    """
    lookup = dict(base)
    for season in show.seasons:
        for episode in season.episodes:
            episode_teams = extract_teams_from_text(episode.title, lookup)
            for team in episode_teams:
                token = normalize_token(team)
                if token and token not in lookup:
                    lookup[token] = team
            for alias in episode.aliases:
                alias_teams = extract_teams_from_text(alias, lookup)
                if episode_teams and alias_teams and len(alias_teams) == len(episode_teams):
                    for canonical, alias_team in zip(episode_teams, alias_teams):
                        token = normalize_token(alias_team)
                        if token and token not in lookup:
                            lookup[token] = canonical
                alias_token = normalize_token(alias)
                if alias_token and alias_token not in lookup:
                    lookup[alias_token] = episode.title
    return lookup


def canonicalize_team(value: str | None, alias_lookup: dict[str, str]) -> str | None:
    """Canonicalize a team name through the alias lookup.

    Args:
        value: Raw team name
        alias_lookup: Team alias lookup dictionary

    Returns:
        Canonical team name or None
    """
    if not value:
        return None
    if not alias_lookup:
        return None
    normalized_team = normalize_token(value)
    if not normalized_team:
        return None
    return alias_lookup.get(normalized_team)
