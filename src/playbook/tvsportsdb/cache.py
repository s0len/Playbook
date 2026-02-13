"""SQLite-backed response caching for TVSportsDB API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ..persistence import CacheEntry, MetadataCacheStore

if TYPE_CHECKING:
    from .models import SeasonResponse, ShowResponse, TeamAliasResponse

LOGGER = logging.getLogger(__name__)


class TVSportsDBCache:
    """SQLite-backed cache for TVSportsDB API responses.

    Caches show, season, and team alias data with configurable TTL
    and support for HTTP conditional requests via ETag.
    """

    def __init__(self, cache_dir: Path, ttl_hours: int = 2) -> None:
        """Initialize the cache.

        Args:
            cache_dir: Directory for the cache database
            ttl_hours: Time-to-live in hours for cached entries
        """
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        # Store database in cache_dir/metadata.db
        db_path = cache_dir / "metadata.db"
        self._store = MetadataCacheStore(db_path, ttl_hours=ttl_hours)

    def _make_key(self, category: str, identifier: str) -> str:
        """Build a cache key from category and identifier."""
        return f"{category}/{identifier}"

    # --- Show methods ---

    def get_show(self, slug: str) -> ShowResponse | None:
        """Get cached show by slug.

        Args:
            slug: Show slug (e.g., "formula-1-2025")

        Returns:
            ShowResponse if cached and not expired, else None
        """
        from .models import ShowResponse

        key = self._make_key("shows", slug)
        entry = self._store.get(key)
        if entry is None:
            return None

        try:
            return ShowResponse.model_validate(entry.content)
        except Exception as exc:
            LOGGER.debug("Failed to parse cached show %s: %s", slug, exc)
            return None

    def get_show_entry(self, slug: str, *, include_expired: bool = False) -> CacheEntry | None:
        """Get the raw cache entry for a show.

        This is useful for conditional requests where you need the ETag
        even if the content is expired.

        Args:
            slug: Show slug
            include_expired: If True, returns expired entries

        Returns:
            CacheEntry if found, else None
        """
        key = self._make_key("shows", slug)
        return self._store.get(key, include_expired=include_expired)

    def save_show(
        self,
        slug: str,
        show: ShowResponse,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> None:
        """Save show to cache.

        Args:
            slug: Show slug
            show: Show response to cache
            etag: Optional ETag from HTTP response
            last_modified: Optional Last-Modified from HTTP response
        """
        key = self._make_key("shows", slug)
        self._store.set(
            key,
            show.model_dump(mode="json"),
            etag=etag,
            last_modified=last_modified,
        )

    def refresh_show_ttl(self, slug: str) -> bool:
        """Refresh the TTL for a show (e.g., after a 304 response).

        Args:
            slug: Show slug

        Returns:
            True if entry was found and updated
        """
        key = self._make_key("shows", slug)
        return self._store.refresh_ttl(key)

    # --- Season methods ---

    def get_season(self, show_slug: str, season_number: int) -> SeasonResponse | None:
        """Get cached season by show slug and season number.

        Args:
            show_slug: Show slug
            season_number: Season number

        Returns:
            SeasonResponse if cached and not expired, else None
        """
        from .models import SeasonResponse

        key = self._make_key("seasons", f"{show_slug}_s{season_number}")
        entry = self._store.get(key)
        if entry is None:
            return None

        try:
            return SeasonResponse.model_validate(entry.content)
        except Exception as exc:
            LOGGER.debug("Failed to parse cached season %s/%d: %s", show_slug, season_number, exc)
            return None

    def get_season_entry(
        self,
        show_slug: str,
        season_number: int,
        *,
        include_expired: bool = False,
    ) -> CacheEntry | None:
        """Get the raw cache entry for a season.

        Args:
            show_slug: Show slug
            season_number: Season number
            include_expired: If True, returns expired entries

        Returns:
            CacheEntry if found, else None
        """
        key = self._make_key("seasons", f"{show_slug}_s{season_number}")
        return self._store.get(key, include_expired=include_expired)

    def save_season(
        self,
        show_slug: str,
        season_number: int,
        season: SeasonResponse,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> None:
        """Save season to cache.

        Args:
            show_slug: Show slug
            season_number: Season number
            season: Season response to cache
            etag: Optional ETag from HTTP response
            last_modified: Optional Last-Modified from HTTP response
        """
        key = self._make_key("seasons", f"{show_slug}_s{season_number}")
        self._store.set(
            key,
            season.model_dump(mode="json"),
            etag=etag,
            last_modified=last_modified,
        )

    def refresh_season_ttl(self, show_slug: str, season_number: int) -> bool:
        """Refresh the TTL for a season.

        Args:
            show_slug: Show slug
            season_number: Season number

        Returns:
            True if entry was found and updated
        """
        key = self._make_key("seasons", f"{show_slug}_s{season_number}")
        return self._store.refresh_ttl(key)

    # --- Team alias methods ---

    def get_team_aliases(self, sport_slug: str) -> list[TeamAliasResponse] | None:
        """Get cached team aliases by sport slug.

        Args:
            sport_slug: Sport/show slug

        Returns:
            List of team aliases if cached and not expired, else None
        """
        from .models import TeamAliasResponse

        key = self._make_key("team_aliases", sport_slug)
        entry = self._store.get(key)
        if entry is None:
            return None

        try:
            return [TeamAliasResponse.model_validate(item) for item in entry.content]
        except Exception as exc:
            LOGGER.debug("Failed to parse cached team aliases for %s: %s", sport_slug, exc)
            return None

    def save_team_aliases(
        self,
        sport_slug: str,
        aliases: list[TeamAliasResponse],
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> None:
        """Save team aliases to cache.

        Args:
            sport_slug: Sport/show slug
            aliases: List of team aliases to cache
            etag: Optional ETag from HTTP response
            last_modified: Optional Last-Modified from HTTP response
        """
        key = self._make_key("team_aliases", sport_slug)
        self._store.set(
            key,
            [alias.model_dump(mode="json") for alias in aliases],
            etag=etag,
            last_modified=last_modified,
        )

    # --- Invalidation methods ---

    def invalidate_show(self, slug: str) -> None:
        """Remove cached show and all its seasons.

        Args:
            slug: Show slug
        """
        # Delete the show
        self._store.delete(self._make_key("shows", slug))
        # Delete all seasons for this show
        self._store.invalidate_by_prefix(f"seasons/{slug}_")

    def invalidate_by_sport(self, sport_slug: str) -> int:
        """Invalidate all cached data for a sport.

        Args:
            sport_slug: Sport/show slug (e.g., "ufc-2025")

        Returns:
            Number of entries deleted
        """
        count = 0
        # Delete shows matching this slug
        count += self._store.invalidate_by_prefix(f"shows/{sport_slug}")
        # Delete seasons matching this slug
        count += self._store.invalidate_by_prefix(f"seasons/{sport_slug}_")
        # Delete team aliases
        count += self._store.delete(self._make_key("team_aliases", sport_slug))
        return count

    def invalidate_all(self) -> int:
        """Remove all cached data.

        Returns:
            Number of entries deleted
        """
        return self._store.clear()

    def invalidate_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries deleted
        """
        return self._store.invalidate_expired()

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return self._store.get_stats()

    def close(self) -> None:
        """Close the cache store."""
        self._store.close()
