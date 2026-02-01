"""Parallel metadata loading and fingerprint tracking.

This module handles loading sport configurations and show metadata in parallel
from the TheTVSportsDB API, tracking metadata fingerprints to detect changes,
and building SportRuntime objects that contain the compiled pattern matchers
for each sport.
"""

from __future__ import annotations

import logging
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
    """

    sport: SportConfig
    show: Show
    patterns: list[PatternRuntime]
    extensions: set[str]


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
    """Load show metadata from TheTVSportsDB API.

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
        LOGGER.warning("Show not found in TheTVSportsDB: %s", sport.show_slug)
        stats.record_failure()
        return None
    except TVSportsDBError as exc:
        LOGGER.error("Failed to fetch show from TheTVSportsDB: %s - %s", sport.show_slug, exc)
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

    # Filter to enabled sports
    enabled_sports = [sport for sport in sports if sport.enabled]
    if not enabled_sports:
        return MetadataLoadResult(
            runtimes=runtimes,
            changed_sports=changed_sports,
            change_map=change_map,
            fetch_stats=fetch_stats,
        )

    # Initialize API client
    effective_cache_dir = cache_dir if cache_dir is not None else settings.cache_dir
    client = TVSportsDBClient(
        cache_dir=effective_cache_dir,
        ttl_hours=settings.tvsportsdb.ttl_hours,
        timeout=settings.tvsportsdb.timeout,
    )
    adapter = TVSportsDBAdapter()

    # Load metadata in parallel
    shows: dict[str, Show] = {}
    max_workers = min(8, max(1, len(enabled_sports)))

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for sport in enabled_sports:
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

    # Build runtimes and track fingerprint changes
    for sport in enabled_sports:
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

    # Log metadata fetch statistics
    if fetch_stats.has_activity():
        snapshot = fetch_stats.snapshot()
        LOGGER.info(
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
