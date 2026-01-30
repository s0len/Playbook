"""Tests for TheTVSportsDB client module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from playbook.tvsportsdb.client import (
    TVSportsDBClient,
    TVSportsDBError,
    TVSportsDBNotFoundError,
)


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client."""
    with patch("playbook.tvsportsdb.client.httpx.Client") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def client(tmp_path, mock_httpx_client):
    """Create a TVSportsDBClient with mocked HTTP client."""
    return TVSportsDBClient(
        base_url="https://api.example.com/v1",
        cache_dir=tmp_path,
        ttl_hours=12,
        timeout=30.0,
    )


class TestTVSportsDBClient:
    """Tests for the API client."""

    def test_get_show_success(self, client, mock_httpx_client) -> None:
        """Test successful show fetch."""
        show_data = {
            "id": 1,
            "slug": "formula-1-2026",
            "title": "Formula 1 2026",
            "sort_title": "Formula 1 2026",
            "summary": "F1 2026 Season",
            "season_count": 24,
            "episode_count": 144,
            "seasons": [
                {
                    "id": 10,
                    "show_id": 1,
                    "number": 1,
                    "title": "Australian GP",
                    "sort_title": "01 - Australian GP",
                    "episodes": [],
                }
            ],
        }
        season_data = {
            "id": 10,
            "show_id": 1,
            "number": 1,
            "title": "Australian GP",
            "sort_title": "01 - Australian GP",
            "episodes": [
                {"id": 100, "season_id": 10, "number": 1, "title": "FP1"},
                {"id": 101, "season_id": 10, "number": 2, "title": "FP2"},
            ],
        }

        mock_response_show = MagicMock()
        mock_response_show.status_code = 200
        mock_response_show.json.return_value = show_data
        mock_response_show.raise_for_status = MagicMock()

        mock_response_season = MagicMock()
        mock_response_season.status_code = 200
        mock_response_season.json.return_value = season_data
        mock_response_season.raise_for_status = MagicMock()

        mock_httpx_client.request.side_effect = [mock_response_show, mock_response_season]

        show = client.get_show("formula-1-2026", include_episodes=True)

        assert show.id == 1
        assert show.slug == "formula-1-2026"
        assert show.title == "Formula 1 2026"
        assert len(show.seasons) == 1
        assert len(show.seasons[0].episodes) == 2
        assert show.seasons[0].episodes[0].title == "FP1"

    def test_get_show_not_found(self, client, mock_httpx_client) -> None:
        """Test 404 handling for show not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(TVSportsDBNotFoundError) as exc_info:
            client.get_show("nonexistent-show")

        assert "Resource not found" in str(exc_info.value)

    def test_get_show_cached(self, tmp_path, mock_httpx_client) -> None:
        """Test that cached show doesn't make HTTP request."""
        # First, save data to cache manually
        client = TVSportsDBClient(
            base_url="https://api.example.com/v1",
            cache_dir=tmp_path,
            ttl_hours=12,
        )
        from playbook.tvsportsdb.models import ShowResponse

        cached_show = ShowResponse(
            id=1,
            slug="cached-show",
            title="Cached Show",
            sort_title="Cached Show",
        )
        client.cache.save_show("cached-show", cached_show)

        # Request should use cache, not HTTP
        show = client.get_show("cached-show", include_episodes=False)

        # HTTP client should not have been called
        mock_httpx_client.request.assert_not_called()
        assert show.slug == "cached-show"
        assert show.title == "Cached Show"

    def test_get_season_success(self, client, mock_httpx_client) -> None:
        """Test successful season fetch."""
        season_data = {
            "id": 10,
            "show_id": 1,
            "number": 1,
            "title": "Australian GP",
            "sort_title": "01 - Australian GP",
            "episodes": [
                {"id": 100, "season_id": 10, "number": 1, "title": "FP1", "aliases": ["Practice 1"]},
                {"id": 101, "season_id": 10, "number": 2, "title": "FP2"},
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = season_data
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.request.return_value = mock_response

        season = client.get_season("formula-1-2026", 1)

        assert season.id == 10
        assert season.title == "Australian GP"
        assert len(season.episodes) == 2
        assert season.episodes[0].aliases == ["Practice 1"]

    def test_get_team_aliases_success(self, client, mock_httpx_client) -> None:
        """Test successful team aliases fetch."""
        aliases_data = {
            "items": [
                {"canonical_name": "Lakers", "alias": "LAL", "sport_slug": "nba"},
                {"canonical_name": "Celtics", "alias": "BOS", "sport_slug": "nba"},
            ],
            "total": 2,
            "skip": 0,
            "limit": 1000,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = aliases_data
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.request.return_value = mock_response

        aliases = client.get_team_aliases("nba-2025")

        assert len(aliases) == 2
        assert aliases[0].alias == "LAL"
        assert aliases[1].alias == "BOS"

    def test_list_shows_success(self, client, mock_httpx_client) -> None:
        """Test listing shows."""
        shows_data = {
            "items": [
                {"id": 1, "slug": "f1-2026", "title": "F1 2026", "sort_title": "F1 2026"},
                {"id": 2, "slug": "ufc-2026", "title": "UFC 2026", "sort_title": "UFC 2026"},
            ],
            "total": 100,
            "skip": 0,
            "limit": 10,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = shows_data
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.request.return_value = mock_response

        shows = client.list_shows(limit=10)

        assert len(shows) == 2
        assert shows[0].slug == "f1-2026"
        assert shows[1].slug == "ufc-2026"

    def test_search_episodes_by_title(self, client, mock_httpx_client) -> None:
        """Test searching episodes by title."""
        episodes_data = {
            "items": [
                {"id": 1, "season_id": 10, "number": 1, "title": "Qualifying"},
                {"id": 2, "season_id": 10, "number": 2, "title": "Sprint Qualifying"},
            ],
            "total": 2,
            "skip": 0,
            "limit": 100,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = episodes_data
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.request.return_value = mock_response

        episodes = client.search_episodes("formula-1-2026", title="Qualifying")

        assert len(episodes) == 2
        mock_httpx_client.request.assert_called_once()
        call_kwargs = mock_httpx_client.request.call_args
        assert call_kwargs[1]["params"]["title"] == "Qualifying"

    def test_search_episodes_by_date(self, client, mock_httpx_client) -> None:
        """Test searching episodes by date."""
        episodes_data = {
            "items": [
                {"id": 1, "season_id": 10, "number": 1, "title": "FP1"},
            ],
            "total": 1,
            "skip": 0,
            "limit": 100,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = episodes_data
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.request.return_value = mock_response

        episodes = client.search_episodes("formula-1-2026", date="2026-03-05")

        assert len(episodes) == 1
        call_kwargs = mock_httpx_client.request.call_args
        assert call_kwargs[1]["params"]["date"] == "2026-03-05"

    def test_invalidate_cache_specific_show(self, tmp_path) -> None:
        """Test invalidating a specific show's cache."""
        client = TVSportsDBClient(
            base_url="https://api.example.com/v1",
            cache_dir=tmp_path,
            ttl_hours=12,
        )
        from playbook.tvsportsdb.models import ShowResponse

        show = ShowResponse(id=1, slug="test", title="Test", sort_title="Test")
        client.cache.save_show("test", show)
        assert client.cache.get_show("test") is not None

        client.invalidate_cache("test")
        assert client.cache.get_show("test") is None

    def test_invalidate_cache_all(self, tmp_path) -> None:
        """Test invalidating all cached data."""
        client = TVSportsDBClient(
            base_url="https://api.example.com/v1",
            cache_dir=tmp_path,
            ttl_hours=12,
        )
        from playbook.tvsportsdb.models import SeasonResponse, ShowResponse

        show = ShowResponse(id=1, slug="test", title="Test", sort_title="Test")
        season = SeasonResponse(id=1, show_id=1, number=1, title="S1", sort_title="S1")
        client.cache.save_show("test", show)
        client.cache.save_season("test", 1, season)

        client.invalidate_cache()

        assert client.cache.get_show("test") is None
        assert client.cache.get_season("test", 1) is None

    def test_context_manager(self, tmp_path, mock_httpx_client) -> None:
        """Test client works as context manager."""
        with TVSportsDBClient(
            base_url="https://api.example.com/v1",
            cache_dir=tmp_path,
            ttl_hours=12,
        ) as client:
            assert client is not None

        mock_httpx_client.close.assert_called_once()

    def test_base_url_trailing_slash_stripped(self, tmp_path) -> None:
        """Test that trailing slash is stripped from base URL."""
        with patch("playbook.tvsportsdb.client.httpx.Client"):
            client = TVSportsDBClient(
                base_url="https://api.example.com/v1/",
                cache_dir=tmp_path,
                ttl_hours=12,
            )
            assert client.base_url == "https://api.example.com/v1"


class TestRetryLogic:
    """Tests for retry logic in the client."""

    @patch("playbook.tvsportsdb.client.time.sleep")
    def test_retry_on_rate_limit(self, mock_sleep, client, mock_httpx_client) -> None:
        """Test retry on 429 rate limit response."""
        # First call returns 429, second returns success
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "1"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "id": 1,
            "slug": "test",
            "title": "Test",
            "sort_title": "Test",
            "seasons": [],
        }
        success_response.raise_for_status = MagicMock()

        mock_httpx_client.request.side_effect = [rate_limit_response, success_response]

        show = client.get_show("test", include_episodes=False)

        assert show.slug == "test"
        assert mock_httpx_client.request.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch("playbook.tvsportsdb.client.time.sleep")
    def test_retry_on_request_error(self, mock_sleep, client, mock_httpx_client) -> None:
        """Test retry on network error."""
        # First two calls fail, third succeeds
        mock_httpx_client.request.side_effect = [
            httpx.RequestError("Connection failed"),
            httpx.RequestError("Connection failed"),
            MagicMock(
                status_code=200,
                json=lambda: {"id": 1, "slug": "test", "title": "Test", "sort_title": "Test", "seasons": []},
                raise_for_status=MagicMock(),
            ),
        ]

        show = client.get_show("test", include_episodes=False)

        assert show.slug == "test"
        assert mock_httpx_client.request.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("playbook.tvsportsdb.client.time.sleep")
    def test_max_retries_exceeded(self, mock_sleep, client, mock_httpx_client) -> None:
        """Test error after max retries exceeded."""
        mock_httpx_client.request.side_effect = httpx.RequestError("Connection failed")

        with pytest.raises(TVSportsDBError) as exc_info:
            client.get_show("test")

        assert "after 3 attempts" in str(exc_info.value)
        assert mock_httpx_client.request.call_count == 3

    def test_404_not_retried(self, client, mock_httpx_client) -> None:
        """Test that 404 errors are not retried."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(TVSportsDBNotFoundError):
            client.get_show("nonexistent")

        # Should only be called once, not retried
        assert mock_httpx_client.request.call_count == 1
