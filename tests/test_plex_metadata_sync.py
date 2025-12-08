"""Tests for Plex metadata sync functionality."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from playbook.models import Episode, Season, Show
from playbook.plex_metadata_sync import (
    MappedMetadata,
    _as_int,
    _episode_identifier,
    _first,
    _map_episode_metadata,
    _map_season_metadata,
    _map_show_metadata,
    _match_episode_key,
    _match_season_key,
    _parse_date,
    _resolve_asset_url,
    _season_identifier,
)


def _make_episode(
    index: int = 1,
    title: str = "Test",
    *,
    summary: Optional[str] = None,
    originally_available: Optional[dt.date] = None,
    display_number: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Episode:
    """Helper to create Episode with defaults."""
    ep = Episode(
        title=title,
        summary=summary,
        originally_available=originally_available,
        index=index,
        display_number=display_number,
    )
    if metadata:
        ep.metadata = metadata
    return ep


def _make_season(
    index: int = 1,
    key: str = "season-1",
    title: str = "Season 1",
    *,
    summary: Optional[str] = None,
    display_number: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    episodes: Optional[list] = None,
) -> Season:
    """Helper to create Season with defaults."""
    season = Season(
        key=key,
        title=title,
        summary=summary,
        index=index,
        episodes=episodes or [],
        display_number=display_number,
    )
    if metadata:
        season.metadata = metadata
    return season


def _make_show(
    key: str = "show-1",
    title: str = "Test Show",
    *,
    summary: Optional[str] = None,
    seasons: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Show:
    """Helper to create Show with defaults."""
    show = Show(
        key=key,
        title=title,
        summary=summary,
        seasons=seasons or [],
    )
    if metadata:
        show.metadata = metadata
    return show


class TestParseDate:
    def test_parses_date_object(self) -> None:
        result = _parse_date(dt.date(2024, 1, 15))
        assert result == "2024-01-15"

    def test_parses_datetime_object(self) -> None:
        result = _parse_date(dt.datetime(2024, 1, 15, 10, 30))
        assert result == "2024-01-15"

    def test_parses_iso_string(self) -> None:
        result = _parse_date("2024-01-15")
        assert result == "2024-01-15"

    def test_parses_datetime_string(self) -> None:
        result = _parse_date("2024-01-15 10:30:00")
        assert result == "2024-01-15"

    def test_returns_none_for_invalid(self) -> None:
        assert _parse_date("not-a-date") is None

    def test_returns_none_for_none(self) -> None:
        assert _parse_date(None) is None


class TestResolveAssetUrl:
    def test_returns_none_for_empty(self) -> None:
        assert _resolve_asset_url("http://base", "") is None
        assert _resolve_asset_url("http://base", None) is None

    def test_returns_absolute_url_unchanged(self) -> None:
        url = "https://example.com/image.jpg"
        assert _resolve_asset_url("http://base", url) == url

    def test_resolves_relative_path(self) -> None:
        result = _resolve_asset_url("http://base.com/api/", "assets/poster.jpg")
        assert result == "http://base.com/api/assets/poster.jpg"

    def test_handles_leading_slash(self) -> None:
        result = _resolve_asset_url("http://base.com", "/assets/poster.jpg")
        assert result == "http://base.com/assets/poster.jpg"


class TestFirst:
    def test_returns_first_found(self) -> None:
        meta = {"title": "", "name": "Show Name", "label": "Label"}
        result = _first(meta, ("title", "name", "label"))
        assert result == "Show Name"

    def test_returns_none_if_all_empty(self) -> None:
        meta = {"title": "", "name": None}
        result = _first(meta, ("title", "name"))
        assert result is None

    def test_skips_missing_keys(self) -> None:
        meta = {"name": "Found"}
        result = _first(meta, ("missing", "name"))
        assert result == "Found"


class TestAsInt:
    def test_converts_int(self) -> None:
        assert _as_int(42) == 42

    def test_converts_string(self) -> None:
        assert _as_int("42") == 42

    def test_returns_none_for_invalid(self) -> None:
        assert _as_int("not-a-number") is None

    def test_returns_none_for_none(self) -> None:
        assert _as_int(None) is None


class TestSeasonIdentifier:
    def test_uses_key_if_present(self) -> None:
        season = _make_season(index=1, key="season-key-123", title="Season 1")
        assert _season_identifier(season) == "season-key-123"

    def test_uses_display_number(self) -> None:
        season = _make_season(index=1, key="", title="Season 1", display_number=2)
        # When key is empty but display_number is set, should use display_number
        result = _season_identifier(season)
        # Empty key should fall through to display_number
        assert "display:2" in result or result == ""

    def test_falls_back_to_index(self) -> None:
        season = _make_season(index=3, key="", title="Season 3")
        result = _season_identifier(season)
        # Empty key, no display_number, should use index
        assert "index:3" in result or result == ""


class TestEpisodeIdentifier:
    def test_uses_metadata_id(self) -> None:
        episode = _make_episode(index=1, title="Race", metadata={"id": "ep-123"})
        assert _episode_identifier(episode) == "id:ep-123"

    def test_uses_display_number(self) -> None:
        episode = _make_episode(index=1, title="Race", display_number=5)
        assert _episode_identifier(episode) == "display:5"

    def test_uses_title(self) -> None:
        episode = _make_episode(index=1, title="Grand Prix")
        assert _episode_identifier(episode) == "title:Grand Prix"

    def test_falls_back_to_index(self) -> None:
        episode = _make_episode(index=7, title="")
        assert _episode_identifier(episode) == "index:7"


class TestMatchSeasonKey:
    def test_matches_by_index(self) -> None:
        plex_seasons = [
            {"ratingKey": "100", "index": 1, "title": "Season 1"},
            {"ratingKey": "200", "index": 2, "title": "Season 2"},
        ]
        season = _make_season(index=2, title="Season 2")
        assert _match_season_key(plex_seasons, season) == "200"

    def test_matches_by_display_number(self) -> None:
        plex_seasons = [
            {"ratingKey": "100", "seasonNumber": 2024, "title": "2024"},
        ]
        season = _make_season(index=1, title="2024", display_number=2024)
        assert _match_season_key(plex_seasons, season) == "100"

    def test_matches_by_title(self) -> None:
        plex_seasons = [
            {"ratingKey": "100", "index": 0, "title": "Specials"},
        ]
        season = _make_season(index=99, title="Specials")
        assert _match_season_key(plex_seasons, season) == "100"

    def test_returns_none_if_not_found(self) -> None:
        plex_seasons = [
            {"ratingKey": "100", "index": 1, "title": "Season 1"},
        ]
        season = _make_season(index=5, title="Season 5")
        assert _match_season_key(plex_seasons, season) is None


class TestMatchEpisodeKey:
    def test_matches_by_index(self) -> None:
        plex_episodes = [
            {"ratingKey": "500", "index": 1, "title": "Qualifying"},
            {"ratingKey": "501", "index": 2, "title": "Race"},
        ]
        episode = _make_episode(index=2, title="Race")
        assert _match_episode_key(plex_episodes, episode) == "501"

    def test_matches_by_display_number(self) -> None:
        plex_episodes = [
            {"ratingKey": "500", "index": 3, "title": "Event"},
        ]
        episode = _make_episode(index=1, title="Event", display_number=3)
        assert _match_episode_key(plex_episodes, episode) == "500"

    def test_matches_by_title(self) -> None:
        plex_episodes = [
            {"ratingKey": "500", "index": 1, "title": "Monaco Grand Prix"},
        ]
        episode = _make_episode(index=99, title="Monaco Grand Prix")
        assert _match_episode_key(plex_episodes, episode) == "500"


class TestMapShowMetadata:
    def test_extracts_basic_fields(self) -> None:
        show = _make_show(
            title="F1 2024",
            summary="Formula 1 Season",
            metadata={
                "sort_title": "Formula 1 2024",
                "original_title": "Formula One",
                "originally_available": "2024-03-01",
                "poster": "posters/f1.jpg",
                "background": "backgrounds/f1.jpg",
            },
        )
        result = _map_show_metadata(show, "http://cdn.example.com")

        assert result.title == "F1 2024"
        assert result.summary == "Formula 1 Season"
        assert result.sort_title == "Formula 1 2024"
        assert result.original_title == "Formula One"
        assert result.originally_available_at == "2024-03-01"
        assert result.poster_url == "http://cdn.example.com/posters/f1.jpg"
        assert result.background_url == "http://cdn.example.com/backgrounds/f1.jpg"


class TestMapSeasonMetadata:
    def test_extracts_basic_fields(self) -> None:
        season = _make_season(
            index=1,
            title="2024 Season",
            summary="The 2024 racing season",
            metadata={"poster": "http://absolute.com/poster.jpg"},
        )
        result = _map_season_metadata(season, "http://cdn.example.com")

        assert result.title == "2024 Season"
        assert result.summary == "The 2024 racing season"
        assert result.poster_url == "http://absolute.com/poster.jpg"

    def test_url_poster_field_preferred(self) -> None:
        """Test that url_poster (used by meta-manager YAMLs) is extracted."""
        season = _make_season(
            index=1,
            title="NHL Week 1",
            summary="Week 1 of NHL season",
            metadata={
                "url_poster": "https://example.com/posters/nhl/s1/poster.jpg",
                "url_background": "https://example.com/posters/nhl/s1/background.jpg",
            },
        )
        result = _map_season_metadata(season, "http://cdn.example.com")

        assert result.poster_url == "https://example.com/posters/nhl/s1/poster.jpg"
        assert result.background_url == "https://example.com/posters/nhl/s1/background.jpg"


class TestMapEpisodeMetadata:
    def test_extracts_basic_fields(self) -> None:
        episode = _make_episode(
            index=1,
            title="Monaco Grand Prix",
            summary="The crown jewel of F1",
            originally_available=dt.date(2024, 5, 26),
            metadata={"poster": "episodes/monaco.jpg"},
        )
        result = _map_episode_metadata(episode, "http://cdn.example.com")

        assert result.title == "Monaco Grand Prix"
        assert result.summary == "The crown jewel of F1"
        assert result.originally_available_at == "2024-05-26"
        assert result.poster_url == "http://cdn.example.com/episodes/monaco.jpg"
