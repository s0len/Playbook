"""Season selection logic based on pattern configuration.

This module handles resolving which season a file belongs to based on
the configured season selector mode (round, key, title, sequential, date, week).
"""

from __future__ import annotations

import logging
from typing import Any

from ..config import SeasonSelector
from ..models import Season, Show
from ..utils import normalize_token
from .date_utils import parse_date_string

LOGGER = logging.getLogger(__name__)


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
        mapped = selector.mapping.get(title)
        if mapped:
            desired_round = int(mapped)
            for season in show.seasons:
                if season.round_number == desired_round or season.display_number == desired_round:
                    return season
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

    LOGGER.warning("Unknown season selector mode '%s'", mode)
    return None
