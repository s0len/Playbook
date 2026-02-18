"""Parallel metadata loading and fingerprint tracking.

This module handles loading sport configurations and show metadata in parallel
from the TVSportsDB API, tracking metadata fingerprints to detect changes,
and building SportRuntime objects that contain the compiled pattern matchers
for each sport.

For sports with show_slug_template (dynamic year support), metadata is loaded
on-demand when a file is matched and the year is captured from the filename.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .logging_utils import render_fields_block
from .matcher import compile_patterns
from .metadata import (
    MetadataChangeResult,
    MetadataFetchStatistics,
    MetadataFingerprintStore,
    compute_show_fingerprint,
)
from .tvsportsdb import TVSportsDBAdapter, TVSportsDBClient
from .tvsportsdb.client import TVSportsDBError, TVSportsDBNotFoundError

if TYPE_CHECKING:
    from .config import Settings, SportConfig
    from .matcher import PatternRuntime
    from .models import Show

LOGGER = logging.getLogger(__name__)


@dataclass
class SportRuntime:
    """Runtime state for a loaded sport configuration.

    Holds the sport configuration, show metadata, compiled pattern matchers,
    and set of valid file extensions for this sport.

    For sports with show_slug_template, the show field may be None initially
    and is loaded dynamically when a year is captured during matching.
    """

    sport: SportConfig
    show: Show | None  # May be None for template-based sports until year is known
    patterns: list[PatternRuntime]
    extensions: set[str]
    is_dynamic: bool = False  # True if this sport uses show_slug_template


class DynamicMetadataLoader:
    """Thread-safe loader for on-demand metadata fetching.

    Used by sports with show_slug_template to load metadata when the year
    is first captured from a filename during matching.
    """

    def __init__(self, settings: Settings, cache_dir: Path | None = None):
        """Initialize the dynamic loader.

        Args:
            settings: Application settings (includes TVSportsDB config)
            cache_dir: Optional cache directory override
        """
        self._settings = settings
        self._cache_dir = cache_dir if cache_dir is not None else settings.cache_dir
        self._cache: dict[str, Show] = {}  # Keyed by show_slug
        self._lock = threading.Lock()
        self._client: TVSportsDBClient | None = None
        self._adapter = TVSportsDBAdapter()
        self._stats = MetadataFetchStatistics()
        self._failed_slugs: set[str] = set()  # Track slugs that failed to load

    def _get_client(self) -> TVSportsDBClient:
        """Get or create the API client (lazy initialization)."""
        if self._client is None:
            self._client = TVSportsDBClient(
                cache_dir=self._cache_dir,
                ttl_hours=self._settings.tvsportsdb.ttl_hours,
                timeout=self._settings.tvsportsdb.timeout,
            )
        return self._client

    def load_show(
        self,
        show_slug: str,
        season_overrides: dict | None = None,
    ) -> Show | None:
        """Load show metadata for the given slug, with caching.

        Args:
            show_slug: The TVSportsDB show slug to fetch
            season_overrides: Optional season overrides to apply

        Returns:
            Show model if successful, None if not found or error
        """
        # Check cache first (thread-safe)
        with self._lock:
            if show_slug in self._cache:
                return self._cache[show_slug]
            if show_slug in self._failed_slugs:
                return None

        # Load from API
        client = self._get_client()
        try:
            response = client.get_show(show_slug, include_episodes=True)
            self._stats.record_network_request()
            show = self._adapter.to_show(response)

            # Apply season overrides
            if season_overrides:
                _apply_season_overrides(show, season_overrides)

            # Cache the result
            with self._lock:
                self._cache[show_slug] = show

            LOGGER.debug(
                render_fields_block(
                    "Dynamic Metadata Loaded",
                    {"Slug": show_slug, "Show": show.title},
                    pad_top=False,
                )
            )
            return show

        except TVSportsDBNotFoundError:
            LOGGER.debug("Show not found in TVSportsDB: %s", show_slug)
            with self._lock:
                self._failed_slugs.add(show_slug)
            self._stats.record_failure()
            return None

        except TVSportsDBError as exc:
            LOGGER.warning("Failed to fetch show from TVSportsDB: %s - %s", show_slug, exc)
            with self._lock:
                self._failed_slugs.add(show_slug)
            self._stats.record_failure()
            return None

    def get_show_for_year(
        self,
        sport: SportConfig,
        year: int,
    ) -> Show | None:
        """Load show metadata for a sport and year combination.

        Uses the sport's show_slug_template to resolve the slug.

        Args:
            sport: Sport configuration with show_slug_template
            year: Year captured from filename

        Returns:
            Show model if successful, None if not found
        """
        show_slug = sport.resolve_show_slug(year)
        if not show_slug:
            return None
        return self.load_show(show_slug, sport.season_overrides)

    def invalidate_cache(self) -> None:
        """Invalidate all cached metadata (in-memory and SQLite)."""
        with self._lock:
            self._cache.clear()
            self._failed_slugs.clear()
        # Ensure the client exists so we can clear the shared SQLite cache.
        # Static sports (like UFC variants) share the same cache DB file.
        client = self._get_client()
        client.invalidate_cache()

    def close(self) -> None:
        """Close the API client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    @property
    def stats(self) -> MetadataFetchStatistics:
        """Get fetch statistics."""
        return self._stats


@dataclass
class MetadataLoadResult:
    """Result of loading sports metadata.

    Contains the loaded sport runtimes, metadata change tracking information,
    and fetch statistics for cache performance monitoring.
    """

    runtimes: list[SportRuntime]
    changed_sports: list[tuple[str, str]]  # List of (sport_id, sport_name)
    change_map: dict[str, MetadataChangeResult]
    fetch_stats: MetadataFetchStatistics


def _load_show_from_api(
    client: TVSportsDBClient,
    adapter: TVSportsDBAdapter,
    sport: SportConfig,
    stats: MetadataFetchStatistics,
) -> Show | None:
    """Load show metadata from TVSportsDB API.

    Args:
        client: API client instance
        adapter: Response adapter
        sport: Sport configuration with show_slug
        stats: Statistics tracker

    Returns:
        Show model if successful, None otherwise
    """
    try:
        response = client.get_show(sport.show_slug, include_episodes=True)
        stats.record_network_request()
        show = adapter.to_show(response)

        # Apply season overrides from sport config
        if sport.season_overrides:
            _apply_season_overrides(show, sport.season_overrides)

        return show
    except TVSportsDBNotFoundError:
        LOGGER.warning("Show not found in TVSportsDB: %s", sport.show_slug)
        stats.record_failure()
        return None
    except TVSportsDBError as exc:
        LOGGER.error("Failed to fetch show from TVSportsDB: %s - %s", sport.show_slug, exc)
        stats.record_failure()
        return None


def _apply_season_overrides(show: Show, overrides: dict) -> None:
    """Apply season overrides from sport config to show model.

    Args:
        show: Show model to modify
        overrides: Dict mapping season title to override dict
    """
    for season in show.seasons:
        override = overrides.get(season.title, {})
        if not override:
            continue

        if "round" in override:
            season.round_number = int(override["round"])
        if "season_number" in override:
            season.display_number = int(override["season_number"])


def load_sports(
    sports: list[SportConfig],
    settings: Settings,
    metadata_fingerprints: MetadataFingerprintStore,
    cache_dir: Path | None = None,
) -> MetadataLoadResult:
    """Load sports metadata in parallel with fingerprint tracking.

    This function loads metadata for all enabled sports concurrently using a
    thread pool, computes fingerprints to detect metadata changes, compiles
    pattern matchers, and returns the complete runtime state along with change
    tracking information.

    Args:
        sports: List of sport configurations to load
        settings: Application settings (includes TVSportsDB config)
        metadata_fingerprints: Store for tracking metadata fingerprints
        cache_dir: Optional cache directory override (defaults to settings.cache_dir)

    Returns:
        MetadataLoadResult containing:
        - runtimes: List of successfully loaded SportRuntime objects
        - changed_sports: List of (sport_id, sport_name) tuples for sports with metadata changes
        - change_map: Dict mapping sport_id to MetadataChangeResult for changed sports
        - fetch_stats: Statistics about metadata cache hits/misses/errors

    Note:
        Sports that fail to load are logged and skipped. The result will only
        contain successfully loaded sports.
    """
    runtimes: list[SportRuntime] = []
    changed_sports: list[tuple[str, str]] = []
    change_map: dict[str, MetadataChangeResult] = {}
    fetch_stats = MetadataFetchStatistics()

    # Log disabled sports
    disabled_sports = [sport for sport in sports if not sport.enabled]
    for sport in disabled_sports:
        LOGGER.debug(render_fields_block("Skipping Disabled Sport", {"Sport": sport.id}, pad_top=True))

    # Filter to enabled sports and separate static vs dynamic
    enabled_sports = [sport for sport in sports if sport.enabled]

    # Static sports have a concrete show_slug to load upfront
    # Dynamic sports have show_slug_template and load metadata on-demand
    static_sports = [s for s in enabled_sports if s.show_slug]
    dynamic_sports = [s for s in enabled_sports if not s.show_slug and s.show_slug_template]

    if not enabled_sports:
        return MetadataLoadResult(
            runtimes=runtimes,
            changed_sports=changed_sports,
            change_map=change_map,
            fetch_stats=fetch_stats,
        )

    # Initialize API client for static sports
    effective_cache_dir = cache_dir if cache_dir is not None else settings.cache_dir
    shows: dict[str, Show] = {}

    # Load metadata for static sports in parallel
    if static_sports:
        client = TVSportsDBClient(
            cache_dir=effective_cache_dir,
            ttl_hours=settings.tvsportsdb.ttl_hours,
            timeout=settings.tvsportsdb.timeout,
        )
        adapter = TVSportsDBAdapter()
        max_workers = min(8, max(1, len(static_sports)))

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {}
                for sport in static_sports:
                    fields = {"Sport": sport.name, "Slug": sport.show_slug}
                    LOGGER.debug(render_fields_block("Loading Metadata", fields, pad_top=True))
                    future = executor.submit(
                        _load_show_from_api,
                        client,
                        adapter,
                        sport,
                        fetch_stats,
                    )
                    future_map[future] = sport

                for future in as_completed(future_map):
                    sport = future_map[future]
                    try:
                        show = future.result()
                    except Exception as exc:  # pragma: no cover - defensive
                        LOGGER.error(
                            render_fields_block(
                                "Failed To Load Metadata",
                                {
                                    "Sport": sport.id,
                                    "Name": sport.name,
                                    "Slug": sport.show_slug,
                                    "Error": exc,
                                },
                                pad_top=True,
                            )
                        )
                        continue

                    if show is not None:
                        shows[sport.id] = show
        finally:
            client.close()

    # Build runtimes for static sports and track fingerprint changes
    for sport in static_sports:
        show = shows.get(sport.id)
        if show is None:
            continue
        patterns = compile_patterns(sport)
        extensions = {ext.lower() for ext in sport.source_extensions}

        # Compute and track metadata fingerprint
        try:
            cached_fingerprint = metadata_fingerprints.get(sport.id)
            fingerprint = compute_show_fingerprint(show, sport.show_slug, cached_fingerprint)
        except Exception as exc:  # pragma: no cover - defensive, should not happen
            LOGGER.warning(
                render_fields_block(
                    "Failed To Compute Metadata Fingerprint",
                    {
                        "Sport": sport.id,
                        "Error": exc,
                    },
                    pad_top=True,
                )
            )
        else:
            change = metadata_fingerprints.update(sport.id, fingerprint)
            if change.updated:
                changed_sports.append((sport.id, sport.name))
                change_map[sport.id] = change

        runtimes.append(SportRuntime(sport=sport, show=show, patterns=patterns, extensions=extensions))

    # Build runtimes for dynamic sports (metadata loaded on-demand during matching)
    for sport in dynamic_sports:
        patterns = compile_patterns(sport)
        extensions = {ext.lower() for ext in sport.source_extensions}
        LOGGER.debug(
            render_fields_block(
                "Dynamic Sport Registered",
                {"Sport": sport.name, "Template": sport.show_slug_template},
                pad_top=True,
            )
        )
        runtimes.append(SportRuntime(sport=sport, show=None, patterns=patterns, extensions=extensions, is_dynamic=True))

    # Log metadata fetch statistics (DEBUG level - not useful at INFO)
    if fetch_stats.has_activity():
        snapshot = fetch_stats.snapshot()
        LOGGER.debug(
            render_fields_block(
                "Metadata API",
                {
                    "Requests": snapshot["network_requests"],
                    "Failures": snapshot["failures"],
                },
                pad_top=False,
            )
        )

    return MetadataLoadResult(
        runtimes=runtimes,
        changed_sports=changed_sports,
        change_map=change_map,
        fetch_stats=fetch_stats,
    )
