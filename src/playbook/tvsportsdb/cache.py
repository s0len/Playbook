"""TTL-based response caching for TheTVSportsDB API."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..utils import ensure_directory

if TYPE_CHECKING:
    from .models import SeasonResponse, ShowResponse, TeamAliasResponse

LOGGER = logging.getLogger(__name__)


def _json_default(obj: Any) -> Any:
    """JSON encoder for datetime and date objects."""
    if isinstance(obj, datetime):
        return obj.isoformat(timespec="seconds")
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class TVSportsDBCache:
    """TTL-based file cache for API responses.

    Caches show, season, and team alias data to disk with configurable TTL.
    """

    def __init__(self, cache_dir: Path, ttl_hours: int = 12) -> None:
        """Initialize the cache.

        Args:
            cache_dir: Directory for cache files
            ttl_hours: Time-to-live in hours for cached entries
        """
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        self._ttl = timedelta(hours=ttl_hours)

    def _cache_path(self, category: str, key: str) -> Path:
        """Build the cache file path for a given category and key."""
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.cache_dir / category / f"{safe_key}.json"

    def _is_valid(self, cache_file: Path) -> bool:
        """Check if a cache file exists and is within TTL."""
        if not cache_file.exists():
            return False

        try:
            with cache_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False

        cached_at_raw = data.get("cached_at")
        if not cached_at_raw:
            return False

        try:
            cached_at = datetime.fromisoformat(cached_at_raw)
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=UTC)
        except (TypeError, ValueError):
            return False

        age = datetime.now(UTC) - cached_at
        return age <= self._ttl

    def _load(self, cache_file: Path) -> dict[str, Any] | None:
        """Load data from cache file if valid."""
        if not self._is_valid(cache_file):
            return None

        try:
            with cache_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("content")
        except (json.JSONDecodeError, OSError) as exc:
            LOGGER.debug("Failed to load cache file %s: %s", cache_file, exc)
            return None

    def _save(self, cache_file: Path, content: dict[str, Any] | list[Any]) -> None:
        """Save data to cache file."""
        ensure_directory(cache_file.parent)
        payload = {
            "cached_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "content": content,
        }
        try:
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, default=_json_default)
        except OSError as exc:
            LOGGER.warning("Failed to write cache file %s: %s", cache_file, exc)

    def get_show(self, slug: str) -> ShowResponse | None:
        """Get cached show by slug."""
        from .models import ShowResponse

        cache_file = self._cache_path("shows", slug)
        data = self._load(cache_file)
        if data is None:
            return None
        try:
            return ShowResponse.model_validate(data)
        except Exception as exc:
            LOGGER.debug("Failed to parse cached show %s: %s", slug, exc)
            return None

    def save_show(self, slug: str, show: ShowResponse) -> None:
        """Save show to cache."""
        cache_file = self._cache_path("shows", slug)
        self._save(cache_file, show.model_dump(mode="json"))

    def get_season(self, show_slug: str, season_number: int) -> SeasonResponse | None:
        """Get cached season by show slug and season number."""
        from .models import SeasonResponse

        key = f"{show_slug}_s{season_number}"
        cache_file = self._cache_path("seasons", key)
        data = self._load(cache_file)
        if data is None:
            return None
        try:
            return SeasonResponse.model_validate(data)
        except Exception as exc:
            LOGGER.debug("Failed to parse cached season %s/%d: %s", show_slug, season_number, exc)
            return None

    def save_season(self, show_slug: str, season_number: int, season: SeasonResponse) -> None:
        """Save season to cache."""
        key = f"{show_slug}_s{season_number}"
        cache_file = self._cache_path("seasons", key)
        self._save(cache_file, season.model_dump(mode="json"))

    def get_team_aliases(self, sport_slug: str) -> list[TeamAliasResponse] | None:
        """Get cached team aliases by sport slug."""
        from .models import TeamAliasResponse

        cache_file = self._cache_path("team_aliases", sport_slug)
        data = self._load(cache_file)
        if data is None:
            return None
        try:
            return [TeamAliasResponse.model_validate(item) for item in data]
        except Exception as exc:
            LOGGER.debug("Failed to parse cached team aliases for %s: %s", sport_slug, exc)
            return None

    def save_team_aliases(self, sport_slug: str, aliases: list[TeamAliasResponse]) -> None:
        """Save team aliases to cache."""
        cache_file = self._cache_path("team_aliases", sport_slug)
        self._save(cache_file, [alias.model_dump(mode="json") for alias in aliases])

    def invalidate_show(self, slug: str) -> None:
        """Remove cached show."""
        cache_file = self._cache_path("shows", slug)
        if cache_file.exists():
            cache_file.unlink()

    def invalidate_all(self) -> None:
        """Remove all cached data."""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
