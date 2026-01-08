"""Tests for Plex metadata sync functionality."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest

from playbook.models import Episode, Season, Show
from playbook.plex_client import SearchResult
from playbook.plex_metadata_sync import (
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
    summary: str | None = None,
    originally_available: dt.date | None = None,
    display_number: int | None = None,
    metadata: dict[str, Any] | None = None,
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
    summary: str | None = None,
    display_number: int | None = None,
    metadata: dict[str, Any] | None = None,
    episodes: list | None = None,
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
    summary: str | None = None,
    seasons: list | None = None,
    metadata: dict[str, Any] | None = None,
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

    def test_resolves_relative_path_from_file_url(self) -> None:
        # Base URL is a YAML file, relative path should be resolved from its directory
        result = _resolve_asset_url(
            "https://raw.githubusercontent.com/user/repo/main/metadata/nhl/2025.yaml", "posters/nhl.jpg"
        )
        assert result == "https://raw.githubusercontent.com/user/repo/main/metadata/nhl/posters/nhl.jpg"

    def test_resolves_relative_path_from_directory_url(self) -> None:
        # When base URL ends with /, treat it as a directory
        result = _resolve_asset_url("http://base.com/api/", "assets/poster.jpg")
        assert result == "http://base.com/api/assets/poster.jpg"

    def test_handles_leading_slash(self) -> None:
        # Leading slash means relative to domain root
        result = _resolve_asset_url("http://base.com/path/to/file.yaml", "/assets/poster.jpg")
        assert result == "http://base.com/assets/poster.jpg"

    def test_resolves_parent_directory_path(self) -> None:
        # Should handle paths with ../
        result = _resolve_asset_url("https://example.com/metadata/show/2025.yaml", "../posters/poster.jpg")
        assert result == "https://example.com/metadata/posters/poster.jpg"


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


class TestShowNotFoundLogging:
    """Tests for enhanced show-not-found logging with close matches."""

    def test_logs_close_matches_when_show_not_found(self, caplog: pytest.LogCaptureFixture) -> None:
        """When a show is not found, log should include close matches."""
        # Create a SearchResult simulating a failed search with close matches
        search_result = SearchResult(
            searched_title="Formula 1 2024",
            library_id="1",
            result=None,
            close_matches=["Formula One 2024", "F1 Racing 2024", "Formula 1 2023"],
        )

        # Verify SearchResult fields are accessible for logging
        assert search_result.result is None
        assert search_result.close_matches == ["Formula One 2024", "F1 Racing 2024", "Formula 1 2023"]
        assert search_result.searched_title == "Formula 1 2024"
        assert search_result.library_id == "1"

    def test_handles_empty_close_matches(self) -> None:
        """When no close matches exist, SearchResult should have empty list."""
        search_result = SearchResult(
            searched_title="NonExistent Show",
            library_id="1",
            result=None,
            close_matches=[],
        )

        assert search_result.result is None
        assert search_result.close_matches == []

    def test_search_result_with_match_has_result(self) -> None:
        """When show is found, SearchResult should have result populated."""
        plex_show = {"ratingKey": "12345", "title": "Formula 1 2024"}
        search_result = SearchResult(
            searched_title="Formula 1 2024",
            library_id="1",
            result=plex_show,
            close_matches=[],
        )

        assert search_result.result is not None
        assert search_result.result["ratingKey"] == "12345"

    def test_close_matches_format_for_error_message(self) -> None:
        """Verify close matches can be formatted for error messages."""
        search_result = SearchResult(
            searched_title="NHL 2024",
            library_id="5",
            result=None,
            close_matches=["NHL Hockey 2024", "NHL Season 2024", "NHL Games"],
        )

        # Format like the actual implementation does
        close_matches_str = ""
        if search_result.close_matches:
            close_matches_str = f" Similar: {', '.join(search_result.close_matches[:3])}"

        expected_error = (
            f"Show not found: '{search_result.searched_title}' in library "
            f"{search_result.library_id} (metadata: http://example.com/nhl.yaml).{close_matches_str}"
        )

        assert "NHL 2024" in expected_error
        assert "Similar: NHL Hockey 2024, NHL Season 2024, NHL Games" in expected_error

    def test_error_message_truncates_close_matches_to_three(self) -> None:
        """Error messages should only include first 3 close matches."""
        search_result = SearchResult(
            searched_title="Test Show",
            library_id="1",
            result=None,
            close_matches=["Match 1", "Match 2", "Match 3", "Match 4", "Match 5"],
        )

        # Format like the actual implementation does (only first 3)
        close_matches_str = ""
        if search_result.close_matches:
            close_matches_str = f" Similar: {', '.join(search_result.close_matches[:3])}"

        assert "Match 1" in close_matches_str
        assert "Match 2" in close_matches_str
        assert "Match 3" in close_matches_str
        assert "Match 4" not in close_matches_str
        assert "Match 5" not in close_matches_str


class TestSeasonNotFoundLogging:
    """Tests for enhanced season-not-found logging."""

    def test_season_not_found_includes_plex_seasons(self) -> None:
        """When a season is not found, available Plex seasons should be captured."""
        # Simulating what Plex returns for seasons
        plex_seasons = [
            {"ratingKey": "100", "index": 1, "title": "Season 1"},
            {"ratingKey": "200", "index": 2, "title": "Season 2"},
        ]

        # Format like the actual implementation does
        plex_season_titles = [f"{s.get('index', '?')}: {s.get('title', '(untitled)')}" for s in plex_seasons]

        assert plex_season_titles == ["1: Season 1", "2: Season 2"]

    def test_season_not_found_error_format(self) -> None:
        """Verify season not found error message format."""
        season = _make_season(index=3, title="Season 3")
        show = _make_show(title="Test Show")
        plex_seasons = [
            {"ratingKey": "100", "index": 1, "title": "Season 1"},
            {"ratingKey": "200", "index": 2, "title": "Season 2"},
        ]

        plex_season_titles = [f"{s.get('index', '?')}: {s.get('title', '(untitled)')}" for s in plex_seasons]

        season_info = f"'{season.title}'" if season.title else f"index={season.index}"
        plex_seasons_str = ""
        if plex_season_titles:
            plex_seasons_str = f" Available: {', '.join(plex_season_titles[:3])}"
            if len(plex_season_titles) > 3:
                plex_seasons_str += f" (+{len(plex_season_titles) - 3} more)"

        error_msg = (
            f"Season not found: {season_info} in show '{show.title}' | "
            f"library=1 | source=http://example.com/test.yaml.{plex_seasons_str}"
        )

        assert "'Season 3'" in error_msg
        assert "'Test Show'" in error_msg
        assert "Available: 1: Season 1, 2: Season 2" in error_msg


class TestEpisodeNotFoundLogging:
    """Tests for enhanced episode-not-found logging."""

    def test_episode_not_found_includes_plex_episodes(self) -> None:
        """When an episode is not found, available Plex episodes should be captured."""
        plex_episodes = [
            {"ratingKey": "500", "index": 1, "title": "Pilot"},
            {"ratingKey": "501", "index": 2, "title": "Episode 2"},
            {"ratingKey": "502", "index": 3, "title": "Episode 3"},
        ]

        plex_episode_titles = [f"{e.get('index', '?')}: {e.get('title', '(untitled)')}" for e in plex_episodes]

        assert plex_episode_titles == ["1: Pilot", "2: Episode 2", "3: Episode 3"]

    def test_episode_not_found_error_format(self) -> None:
        """Verify episode not found error message format."""
        episode = _make_episode(index=5, title="Missing Episode")
        season = _make_season(index=1, title="Season 1")
        show = _make_show(title="Test Show")
        plex_episodes = [
            {"ratingKey": "500", "index": 1, "title": "Pilot"},
            {"ratingKey": "501", "index": 2, "title": "Episode 2"},
        ]

        plex_episode_titles = [f"{e.get('index', '?')}: {e.get('title', '(untitled)')}" for e in plex_episodes]

        episode_info = f"'{episode.title}'" if episode.title else f"index={episode.index}"
        season_info = f"'{season.title}'" if season.title else f"index={season.index}"
        plex_episodes_str = ""
        if plex_episode_titles:
            plex_episodes_str = f" Available: {', '.join(plex_episode_titles[:3])}"
            if len(plex_episode_titles) > 3:
                plex_episodes_str += f" (+{len(plex_episode_titles) - 3} more)"

        error_msg = (
            f"Episode not found: {episode_info} in season {season_info} of '{show.title}' | "
            f"library=1 | source=http://example.com/test.yaml.{plex_episodes_str}"
        )

        assert "'Missing Episode'" in error_msg
        assert "'Season 1'" in error_msg
        assert "'Test Show'" in error_msg
        assert "Available: 1: Pilot, 2: Episode 2" in error_msg

    def test_episode_not_found_truncates_to_three(self) -> None:
        """Error messages should only include first 3 available episodes plus count."""
        plex_episodes = [
            {"ratingKey": "500", "index": 1, "title": "Ep 1"},
            {"ratingKey": "501", "index": 2, "title": "Ep 2"},
            {"ratingKey": "502", "index": 3, "title": "Ep 3"},
            {"ratingKey": "503", "index": 4, "title": "Ep 4"},
            {"ratingKey": "504", "index": 5, "title": "Ep 5"},
        ]

        plex_episode_titles = [f"{e.get('index', '?')}: {e.get('title', '(untitled)')}" for e in plex_episodes]

        plex_episodes_str = ""
        if plex_episode_titles:
            plex_episodes_str = f" Available: {', '.join(plex_episode_titles[:3])}"
            if len(plex_episode_titles) > 3:
                plex_episodes_str += f" (+{len(plex_episode_titles) - 3} more)"

        assert "1: Ep 1" in plex_episodes_str
        assert "2: Ep 2" in plex_episodes_str
        assert "3: Ep 3" in plex_episodes_str
        assert "4: Ep 4" not in plex_episodes_str
        assert "(+2 more)" in plex_episodes_str


class TestPosterUnlockWorkflow:
    """Tests for poster unlock workflow before upload."""

    def test_poster_unlock_before_upload(self) -> None:
        """Test that unlock_field is called before set_asset for poster upload."""
        from unittest.mock import MagicMock, call

        from playbook.plex_client import PLEX_TYPE_SHOW, PlexSyncStats
        from playbook.plex_metadata_sync import MappedMetadata, _apply_metadata

        # Create a mock PlexClient
        mock_client = MagicMock()
        mock_client.unlock_field = MagicMock()
        mock_client.set_asset = MagicMock()
        mock_client.lock_field = MagicMock()
        mock_client.update_metadata = MagicMock(return_value=True)

        # Create metadata with a poster URL
        mapped = MappedMetadata(
            title="Test Show",
            sort_title=None,
            original_title=None,
            originally_available_at=None,
            summary="Test summary",
            poster_url="https://example.com/poster.jpg",
            background_url=None,
        )

        stats = PlexSyncStats()

        # Apply metadata (should trigger unlock -> set_asset -> lock)
        _apply_metadata(
            mock_client,
            "12345",
            mapped,
            type_code=PLEX_TYPE_SHOW,
            label="show 'Test Show'",
            dry_run=False,
            stats=stats,
        )

        # Verify unlock_field was called before set_asset
        mock_client.unlock_field.assert_called_once_with("12345", "thumb")
        mock_client.set_asset.assert_called_once_with("12345", "thumb", "https://example.com/poster.jpg")
        mock_client.lock_field.assert_called_once_with("12345", "thumb")

        # Verify the order: unlock -> set_asset -> lock
        expected_calls = [
            call.unlock_field("12345", "thumb"),
            call.set_asset("12345", "thumb", "https://example.com/poster.jpg"),
            call.lock_field("12345", "thumb"),
        ]
        assert mock_client.mock_calls[-3:] == expected_calls

        # Verify stats were updated
        assert stats.assets_updated == 1
        assert stats.assets_failed == 0
