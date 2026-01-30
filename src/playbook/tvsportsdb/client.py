"""HTTP client for TheTVSportsDB REST API."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from .cache import TVSportsDBCache
from .models import (
    EpisodeResponse,
    PaginatedResponse,
    SeasonResponse,
    ShowResponse,
    TeamAliasResponse,
)

if TYPE_CHECKING:
    pass

LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 1.0


class TVSportsDBError(Exception):
    """Base exception for TVSportsDB API errors."""


class TVSportsDBNotFoundError(TVSportsDBError):
    """Resource not found (404)."""


class TVSportsDBClient:
    """HTTP client for TheTVSportsDB REST API.

    Provides methods to fetch shows, seasons, episodes, and team aliases
    with automatic caching and retry logic.
    """

    def __init__(
        self,
        base_url: str,
        cache_dir: Path,
        ttl_hours: int = 12,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Base URL for the API (e.g., "https://thetvsportsdb.uniflix.vip/api/v1")
            cache_dir: Directory for caching responses
            ttl_hours: Cache time-to-live in hours
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.cache = TVSportsDBCache(cache_dir / "tvsportsdb", ttl_hours)
        self._client = httpx.Client(timeout=timeout)
        self._owns_client = True

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make an HTTP request with retry logic."""
        url = f"{self.base_url}{path}"
        last_exception: Exception | None = None
        backoff = RETRY_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.request(method, url, **kwargs)
                if response.status_code == 404:
                    raise TVSportsDBNotFoundError(f"Resource not found: {path}")
                if response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("Retry-After", backoff))
                    LOGGER.warning("Rate limited, waiting %d seconds", retry_after)
                    time.sleep(retry_after)
                    backoff = min(backoff * 2, 30.0)
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise TVSportsDBNotFoundError(f"Resource not found: {path}") from exc
                last_exception = exc
                if attempt < MAX_RETRIES - 1:
                    LOGGER.debug("Request failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, exc)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30.0)
            except httpx.RequestError as exc:
                last_exception = exc
                if attempt < MAX_RETRIES - 1:
                    LOGGER.debug("Request error (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, exc)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30.0)

        raise TVSportsDBError(f"Failed to fetch {path} after {MAX_RETRIES} attempts") from last_exception

    def get_show(self, slug: str, *, include_episodes: bool = True) -> ShowResponse:
        """Fetch show with seasons.

        Args:
            slug: Show slug (e.g., "formula-1-2026")
            include_episodes: If True, fetches episodes for each season

        Returns:
            ShowResponse with populated seasons (and optionally episodes)

        Raises:
            TVSportsDBNotFoundError: If the show doesn't exist
            TVSportsDBError: On API errors
        """
        # Check cache first
        cached = self.cache.get_show(slug)
        if cached is not None:
            LOGGER.debug("Using cached show: %s", slug)
            return cached

        LOGGER.debug("Fetching show: %s", slug)
        response = self._request("GET", f"/shows/{slug}")
        show = ShowResponse.model_validate(response.json())

        if include_episodes:
            # Fetch episodes for each season
            for season in show.seasons:
                try:
                    season_detail = self.get_season(slug, season.number)
                    season.episodes = season_detail.episodes
                except TVSportsDBError as exc:
                    LOGGER.warning("Failed to fetch episodes for %s season %d: %s", slug, season.number, exc)

        self.cache.save_show(slug, show)
        return show

    def get_season(self, slug: str, number: int) -> SeasonResponse:
        """Fetch season with episodes.

        Args:
            slug: Show slug
            number: Season number

        Returns:
            SeasonResponse with populated episodes

        Raises:
            TVSportsDBNotFoundError: If the season doesn't exist
            TVSportsDBError: On API errors
        """
        # Check cache first
        cached = self.cache.get_season(slug, number)
        if cached is not None:
            LOGGER.debug("Using cached season: %s/season/%d", slug, number)
            return cached

        LOGGER.debug("Fetching season: %s/season/%d", slug, number)
        response = self._request("GET", f"/shows/{slug}/seasons/{number}")
        season = SeasonResponse.model_validate(response.json())

        self.cache.save_season(slug, number, season)
        return season

    def get_team_aliases(self, sport_slug: str) -> list[TeamAliasResponse]:
        """Fetch team aliases for a sport.

        Args:
            sport_slug: Sport/show slug

        Returns:
            List of team alias mappings

        Raises:
            TVSportsDBError: On API errors
        """
        # Check cache first
        cached = self.cache.get_team_aliases(sport_slug)
        if cached is not None:
            LOGGER.debug("Using cached team aliases: %s", sport_slug)
            return cached

        LOGGER.debug("Fetching team aliases: %s", sport_slug)
        response = self._request("GET", "/team-aliases", params={"sport_slug": sport_slug, "limit": 1000})
        data = PaginatedResponse[TeamAliasResponse].model_validate(response.json())

        self.cache.save_team_aliases(sport_slug, data.items)
        return data.items

    def list_shows(self, limit: int = 100) -> list[ShowResponse]:
        """List all available shows.

        Args:
            limit: Maximum number of shows to return

        Returns:
            List of shows (without full season/episode data)

        Raises:
            TVSportsDBError: On API errors
        """
        LOGGER.debug("Listing shows (limit=%d)", limit)
        response = self._request("GET", "/shows", params={"limit": limit})
        data = PaginatedResponse[ShowResponse].model_validate(response.json())
        return data.items

    def search_episodes(
        self,
        slug: str,
        *,
        title: str | None = None,
        date: str | None = None,
    ) -> list[EpisodeResponse]:
        """Search episodes by title or date.

        Args:
            slug: Show slug
            title: Optional title search term
            date: Optional date filter (YYYY-MM-DD)

        Returns:
            List of matching episodes

        Raises:
            TVSportsDBError: On API errors
        """
        params: dict[str, str | int] = {"limit": 100}
        if title:
            params["title"] = title
        if date:
            params["date"] = date

        LOGGER.debug("Searching episodes in %s: %s", slug, params)
        response = self._request("GET", f"/shows/{slug}/episodes", params=params)
        data = PaginatedResponse[EpisodeResponse].model_validate(response.json())
        return data.items

    def invalidate_cache(self, slug: str | None = None) -> None:
        """Invalidate cached data.

        Args:
            slug: Show slug to invalidate, or None to clear all
        """
        if slug:
            self.cache.invalidate_show(slug)
        else:
            self.cache.invalidate_all()

    def close(self) -> None:
        """Close the HTTP client."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> TVSportsDBClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()
