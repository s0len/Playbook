"""HTTP client for TVSportsDB REST API."""

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

# TVSportsDB API endpoint (hardcoded - not configurable)
API_BASE_URL = "https://api.tvsportsdb.com/api/v1"

MAX_RETRIES = 3
RETRY_BACKOFF = 1.0


class TVSportsDBError(Exception):
    """Base exception for TVSportsDB API errors."""


class TVSportsDBNotFoundError(TVSportsDBError):
    """Resource not found (404)."""


class TVSportsDBClient:
    """HTTP client for TVSportsDB REST API.

    Provides methods to fetch shows, seasons, episodes, and team aliases
    with automatic caching, conditional requests, and retry logic.

    The client uses HTTP conditional requests (ETag/If-None-Match) to
    efficiently check for updates without re-downloading unchanged data.
    """

    def __init__(
        self,
        cache_dir: Path,
        ttl_hours: int = 2,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the client.

        Args:
            cache_dir: Directory for caching responses
            ttl_hours: Cache time-to-live in hours (default reduced to 2)
            timeout: HTTP request timeout in seconds
        """
        self.base_url = API_BASE_URL
        self.cache = TVSportsDBCache(cache_dir / "tvsportsdb", ttl_hours)
        self._client = httpx.Client(timeout=timeout)
        self._owns_client = True

    def _request(
        self,
        method: str,
        path: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        **kwargs,
    ) -> httpx.Response | None:
        """Make an HTTP request with retry logic and conditional request support.

        Args:
            method: HTTP method
            path: URL path
            etag: Optional ETag for conditional request (If-None-Match)
            last_modified: Optional Last-Modified for conditional request (If-Modified-Since)
            **kwargs: Additional arguments passed to httpx

        Returns:
            Response object, or None if server returned 304 Not Modified

        Raises:
            TVSportsDBNotFoundError: If resource not found (404)
            TVSportsDBError: On other API errors
        """
        url = f"{self.base_url}{path}"
        last_exception: Exception | None = None
        backoff = RETRY_BACKOFF

        # Add conditional request headers if provided
        headers = kwargs.pop("headers", {})
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        if headers:
            kwargs["headers"] = headers

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.request(method, url, **kwargs)

                # Handle 304 Not Modified - content hasn't changed
                if response.status_code == 304:
                    LOGGER.debug("Content not modified (304): %s", path)
                    return None

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

        Uses conditional requests to efficiently check for updates.

        Args:
            slug: Show slug (e.g., "formula-1-2026")
            include_episodes: If True, fetches episodes for each season

        Returns:
            ShowResponse with populated seasons (and optionally episodes)

        Raises:
            TVSportsDBNotFoundError: If the show doesn't exist
            TVSportsDBError: On API errors
        """
        from .models import ShowResponse

        # Check cache first (including expired entries for conditional requests)
        cached_entry = self.cache.get_show_entry(slug, include_expired=True)

        if cached_entry is not None:
            if cached_entry.is_fresh:
                # Cache is still valid
                LOGGER.debug("Using cached show (fresh): %s", slug)
                return ShowResponse.model_validate(cached_entry.content)

            # Cache expired - try conditional request
            LOGGER.debug("Cache expired, checking for updates: %s", slug)
            response = self._request(
                "GET",
                f"/shows/{slug}",
                etag=cached_entry.etag,
                last_modified=cached_entry.last_modified,
            )

            if response is None:
                # 304 Not Modified - refresh TTL and use cached data
                LOGGER.debug("Content unchanged (304), refreshing TTL: %s", slug)
                self.cache.refresh_show_ttl(slug)
                return ShowResponse.model_validate(cached_entry.content)
        else:
            # No cached entry - make fresh request
            response = self._request("GET", f"/shows/{slug}")

        # Parse new response
        LOGGER.debug("Fetched fresh show data: %s", slug)
        show = ShowResponse.model_validate(response.json())

        if include_episodes:
            # Fetch episodes for each season
            for season in show.seasons:
                try:
                    season_detail = self.get_season(slug, season.number)
                    season.episodes = season_detail.episodes
                except TVSportsDBError as exc:
                    LOGGER.warning("Failed to fetch episodes for %s season %d: %s", slug, season.number, exc)

        # Cache with ETag if provided
        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")
        self.cache.save_show(slug, show, etag=etag, last_modified=last_modified)

        return show

    def get_season(self, slug: str, number: int) -> SeasonResponse:
        """Fetch season with episodes.

        Uses conditional requests to efficiently check for updates.

        Args:
            slug: Show slug
            number: Season number

        Returns:
            SeasonResponse with populated episodes

        Raises:
            TVSportsDBNotFoundError: If the season doesn't exist
            TVSportsDBError: On API errors
        """
        from .models import SeasonResponse

        # Check cache first (including expired entries for conditional requests)
        cached_entry = self.cache.get_season_entry(slug, number, include_expired=True)

        if cached_entry is not None:
            if cached_entry.is_fresh:
                # Cache is still valid
                LOGGER.debug("Using cached season (fresh): %s/season/%d", slug, number)
                return SeasonResponse.model_validate(cached_entry.content)

            # Cache expired - try conditional request
            LOGGER.debug("Cache expired, checking for updates: %s/season/%d", slug, number)
            response = self._request(
                "GET",
                f"/shows/{slug}/seasons/{number}",
                etag=cached_entry.etag,
                last_modified=cached_entry.last_modified,
            )

            if response is None:
                # 304 Not Modified - refresh TTL and use cached data
                LOGGER.debug("Content unchanged (304), refreshing TTL: %s/season/%d", slug, number)
                self.cache.refresh_season_ttl(slug, number)
                return SeasonResponse.model_validate(cached_entry.content)
        else:
            # No cached entry - make fresh request
            response = self._request("GET", f"/shows/{slug}/seasons/{number}")

        # Parse new response
        LOGGER.debug("Fetched fresh season data: %s/season/%d", slug, number)
        season = SeasonResponse.model_validate(response.json())

        # Cache with ETag if provided
        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")
        self.cache.save_season(slug, number, season, etag=etag, last_modified=last_modified)

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
        if response is None:
            # Shouldn't happen for team aliases (no conditional request), but handle it
            return []

        data = PaginatedResponse[TeamAliasResponse].model_validate(response.json())

        # Cache with ETag if provided
        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")
        self.cache.save_team_aliases(sport_slug, data.items, etag=etag, last_modified=last_modified)

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
        if response is None:
            return []
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
        if response is None:
            return []
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
        self.cache.close()

    def __enter__(self) -> TVSportsDBClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()
