"""Tests for Plex client and metadata sync."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from playbook.plex_client import (
    PLEX_TYPE_EPISODE,
    PLEX_TYPE_SEASON,
    PLEX_TYPE_SHOW,
    PlexApiError,
    PlexClient,
    PlexSyncStats,
    SearchResult,
    validate_plex_url,
)


class TestValidatePlexUrl:
    def test_valid_http_url(self) -> None:
        assert validate_plex_url("http://localhost:32400") is True

    def test_valid_https_url(self) -> None:
        assert validate_plex_url("https://plex.example.com") is True

    def test_valid_url_with_path(self) -> None:
        assert validate_plex_url("http://plex:32400/api") is True

    def test_invalid_no_scheme(self) -> None:
        assert validate_plex_url("localhost:32400") is False

    def test_invalid_file_scheme(self) -> None:
        assert validate_plex_url("file:///etc/passwd") is False

    def test_invalid_empty(self) -> None:
        assert validate_plex_url("") is False

    def test_invalid_none(self) -> None:
        assert validate_plex_url(None) is False

    def test_invalid_just_scheme(self) -> None:
        assert validate_plex_url("http://") is False


class TestPlexClient:
    def test_init_validates_url(self) -> None:
        with pytest.raises(PlexApiError, match="Invalid Plex URL"):
            PlexClient("not-a-url", "token")

    def test_init_accepts_valid_url(self) -> None:
        client = PlexClient("http://localhost:32400", "token123")
        assert client.base_url == "http://localhost:32400"
        assert client.token == "token123"

    def test_token_passed_in_header_not_params(self) -> None:
        """Verify token is sent via header for security."""
        client = PlexClient("http://localhost:32400", "secret-token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"MediaContainer": {}}

        with patch.object(client.session, "request", return_value=mock_response) as mock_req:
            client._request("GET", "/test")

            call_kwargs = mock_req.call_args[1]
            headers = call_kwargs.get("headers", {})
            params = call_kwargs.get("params", {})

            # Token should be in headers
            assert headers.get("X-Plex-Token") == "secret-token"
            # Token should NOT be in params
            assert "X-Plex-Token" not in params

    def test_update_metadata_with_field_locking(self) -> None:
        """Verify field locking is applied."""
        client = PlexClient("http://localhost:32400", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.session, "request", return_value=mock_response) as mock_req:
            client.update_metadata("12345", {"title": "Test", "summary": "A summary"})

            call_kwargs = mock_req.call_args[1]
            params = call_kwargs.get("params", {})

            # Should have .value and .locked for each field
            assert params.get("title.value") == "Test"
            assert params.get("title.locked") == 1
            assert params.get("summary.value") == "A summary"
            assert params.get("summary.locked") == 1

    def test_update_metadata_without_locking(self) -> None:
        """Verify field locking can be disabled."""
        client = PlexClient("http://localhost:32400", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.session, "request", return_value=mock_response) as mock_req:
            client.update_metadata("12345", {"title": "Test"}, lock_fields=False)

            call_kwargs = mock_req.call_args[1]
            params = call_kwargs.get("params", {})

            assert params.get("title.value") == "Test"
            assert "title.locked" not in params

    def test_set_asset_validates_element(self) -> None:
        """Verify invalid asset element names are rejected."""
        client = PlexClient("http://localhost:32400", "token")
        with pytest.raises(PlexApiError, match="Invalid asset element"):
            client.set_asset("12345", "poster", "http://example.com/img.jpg")

    def test_set_asset_accepts_valid_elements(self) -> None:
        """Verify valid asset element names work."""
        client = PlexClient("http://localhost:32400", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.session, "request", return_value=mock_response):
            # thumb is the correct name for poster
            client.set_asset("12345", "thumb", "http://example.com/poster.jpg")
            # art is the correct name for background
            client.set_asset("12345", "art", "http://example.com/bg.jpg")

    def test_unlock_field(self) -> None:
        """Verify unlock_field sends correct parameters."""
        client = PlexClient("http://localhost:32400", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.session, "request", return_value=mock_response) as mock_req:
            client.unlock_field("12345", "thumb")

            call_kwargs = mock_req.call_args[1]
            params = call_kwargs.get("params", {})

            # Should set field.locked to 0
            assert params.get("thumb.locked") == 0

    def test_lock_field(self) -> None:
        """Verify lock_field sends correct parameters."""
        client = PlexClient("http://localhost:32400", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.session, "request", return_value=mock_response) as mock_req:
            client.lock_field("12345", "title")

            call_kwargs = mock_req.call_args[1]
            params = call_kwargs.get("params", {})

            # Should set field.locked to 1
            assert params.get("title.locked") == 1


class TestPlexSyncStats:
    def test_empty_stats_no_activity(self) -> None:
        stats = PlexSyncStats()
        assert stats.has_activity() is False

    def test_stats_with_updates_has_activity(self) -> None:
        stats = PlexSyncStats()
        stats.shows_updated = 1
        assert stats.has_activity() is True

    def test_stats_with_errors_has_activity(self) -> None:
        stats = PlexSyncStats()
        stats.errors.append("Something failed")
        assert stats.has_activity() is True

    def test_summary_returns_dict(self) -> None:
        stats = PlexSyncStats()
        stats.shows_updated = 2
        stats.seasons_updated = 5
        stats.episodes_updated = 20
        stats.api_calls = 50

        summary = stats.summary()
        assert summary["shows"]["updated"] == 2
        assert summary["seasons"]["updated"] == 5
        assert summary["episodes"]["updated"] == 20
        assert summary["api_calls"] == 50


class TestPlexTypeConstants:
    """Verify Plex type constants match openapi.json spec."""

    def test_show_type(self) -> None:
        assert PLEX_TYPE_SHOW == 2

    def test_season_type(self) -> None:
        assert PLEX_TYPE_SEASON == 3

    def test_episode_type(self) -> None:
        assert PLEX_TYPE_EPISODE == 4


class TestSearchResult:
    """Test SearchResult dataclass for search diagnostics."""

    def test_required_fields(self) -> None:
        """SearchResult requires searched_title and library_id."""
        result = SearchResult(searched_title="Test Show", library_id="1")
        assert result.searched_title == "Test Show"
        assert result.library_id == "1"

    def test_default_close_matches_empty_list(self) -> None:
        """close_matches defaults to empty list."""
        result = SearchResult(searched_title="Test", library_id="1")
        assert result.close_matches == []

    def test_default_result_is_none(self) -> None:
        """result defaults to None."""
        result = SearchResult(searched_title="Test", library_id="1")
        assert result.result is None

    def test_with_close_matches(self) -> None:
        """SearchResult can store close match titles."""
        result = SearchResult(
            searched_title="NHL 2025-2026",
            library_id="2",
            close_matches=["NHL 2024-2025", "NHL 2023-2024"],
        )
        assert result.close_matches == ["NHL 2024-2025", "NHL 2023-2024"]

    def test_with_result(self) -> None:
        """SearchResult can store a matched result."""
        metadata = {"ratingKey": "12345", "title": "The Show"}
        result = SearchResult(
            searched_title="The Show",
            library_id="1",
            result=metadata,
        )
        assert result.result is not None
        assert result.result["ratingKey"] == "12345"
        assert result.result["title"] == "The Show"

    def test_all_fields(self) -> None:
        """SearchResult stores all fields correctly."""
        metadata = {"ratingKey": "99", "title": "Found Show"}
        result = SearchResult(
            searched_title="Find Show",
            library_id="3",
            close_matches=["Near Match 1", "Near Match 2"],
            result=metadata,
        )
        assert result.searched_title == "Find Show"
        assert result.library_id == "3"
        assert result.close_matches == ["Near Match 1", "Near Match 2"]
        assert result.result == metadata

    def test_slots_prevents_dynamic_attributes(self) -> None:
        """SearchResult uses slots=True, preventing dynamic attributes."""
        result = SearchResult(searched_title="Test", library_id="1")
        with pytest.raises(AttributeError):
            result.arbitrary_attribute = "should fail"  # type: ignore[attr-defined]


class TestSearchShowFuzzyMatching:
    """Test fuzzy title matching in search_show."""

    def test_exact_match_preferred(self) -> None:
        """Exact case-insensitive match is preferred."""
        client = PlexClient("http://localhost:32400", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "MediaContainer": {
                "Metadata": [
                    {"ratingKey": "100", "title": "NHL 2025-2026"},
                    {"ratingKey": "200", "title": "NHL 2025 2026"},
                ]
            }
        }

        with patch.object(client.session, "request", return_value=mock_response):
            result = client.search_show("1", "NHL 2025-2026")
            assert result.result is not None
            assert result.result["ratingKey"] == "100"

    def test_fuzzy_match_hyphen_vs_space(self) -> None:
        """Fuzzy matching handles hyphen vs space differences."""
        client = PlexClient("http://localhost:32400", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "MediaContainer": {
                "Metadata": [
                    {"ratingKey": "200", "title": "Nhl 2025 2026"},  # Different format
                ]
            }
        }

        with patch.object(client.session, "request", return_value=mock_response):
            # Search with hyphen should still find space version
            result = client.search_show("1", "NHL 2025-2026")
            assert result.result is not None
            assert result.result["ratingKey"] == "200"

    def test_fuzzy_match_case_insensitive(self) -> None:
        """Fuzzy matching is case insensitive."""
        client = PlexClient("http://localhost:32400", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "MediaContainer": {
                "Metadata": [
                    {"ratingKey": "300", "title": "nba 2024 2025"},
                ]
            }
        }

        with patch.object(client.session, "request", return_value=mock_response):
            result = client.search_show("1", "NBA 2024-2025")
            assert result.result is not None
            assert result.result["ratingKey"] == "300"

    def test_no_match_returns_search_result_with_close_matches(self) -> None:
        """When no fuzzy match, return SearchResult with close_matches populated."""
        client = PlexClient("http://localhost:32400", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "MediaContainer": {
                "Metadata": [
                    {"ratingKey": "999", "title": "Completely Different Show"},
                ]
            }
        }

        with patch.object(client.session, "request", return_value=mock_response):
            result = client.search_show("1", "NHL 2025-2026")
            # Should NOT return unrelated shows - prevents Formula 1 matching Formula E
            assert result.result is None
            # But should provide close_matches for debugging
            assert result.close_matches == ["Completely Different Show"]
            assert result.searched_title == "NHL 2025-2026"
            assert result.library_id == "1"

    def test_empty_results_returns_search_result(self) -> None:
        """Empty search results return SearchResult with no result and no close_matches."""
        client = PlexClient("http://localhost:32400", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"MediaContainer": {"Metadata": []}}

        with patch.object(client.session, "request", return_value=mock_response):
            result = client.search_show("1", "NHL 2025-2026")
            assert result.result is None
            assert result.close_matches == []
            assert result.searched_title == "NHL 2025-2026"
