"""Parallel metadata loading and fingerprint tracking.

This module handles loading sport configurations and show metadata in parallel,
tracking metadata fingerprints to detect changes, and building SportRuntime
objects that contain the compiled pattern matchers for each sport.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .logging_utils import render_fields_block
from .matcher import compile_patterns
from .metadata import (
    MetadataChangeResult,
    MetadataFetchError,
    MetadataFetchStatistics,
    MetadataFingerprintStore,
    compute_show_fingerprint_cached,
    load_show,
)

if TYPE_CHECKING:
    from .cache import MetadataHttpCache
    from .config import AppSettings, SportConfig
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


def load_sports(
    sports: list[SportConfig],
    settings: AppSettings,
    metadata_http_cache: MetadataHttpCache,
    metadata_fingerprints: MetadataFingerprintStore,
) -> MetadataLoadResult:
    """Load sports metadata in parallel with fingerprint tracking.

    This function loads metadata for all enabled sports concurrently using a
    thread pool, computes fingerprints to detect metadata changes, compiles
    pattern matchers, and returns the complete runtime state along with change
    tracking information.

    Args:
        sports: List of sport configurations to load
        settings: Application settings (used for metadata fetching)
        metadata_http_cache: HTTP cache for metadata requests
        metadata_fingerprints: Store for tracking metadata fingerprints

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

    # Load metadata in parallel
    shows: dict[str, Show] = {}
    max_workers = min(8, max(1, len(enabled_sports)))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for sport in enabled_sports:
            LOGGER.debug(render_fields_block("Loading Metadata", {"Sport": sport.name}, pad_top=True))
            future = executor.submit(
                load_show,
                settings,
                sport.metadata,
                http_cache=metadata_http_cache,
                stats=fetch_stats,
            )
            future_map[future] = sport

        for future in as_completed(future_map):
            sport = future_map[future]
            try:
                show = future.result()
            except MetadataFetchError as exc:
                LOGGER.error(
                    render_fields_block(
                        "Failed To Fetch Metadata",
                        {
                            "Sport": sport.id,
                            "Name": sport.name,
                            "Error": exc,
                        },
                        pad_top=True,
                    )
                )
                continue
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.error(
                    render_fields_block(
                        "Failed To Load Metadata",
                        {
                            "Sport": sport.id,
                            "Name": sport.name,
                            "Error": exc,
                        },
                        pad_top=True,
                    )
                )
                continue
            shows[sport.id] = show

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
            fingerprint = compute_show_fingerprint_cached(show, sport.metadata, cached_fingerprint)
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

    # Log metadata cache statistics
    if fetch_stats.has_activity():
        snapshot = fetch_stats.snapshot()
        LOGGER.info(
            render_fields_block(
                "Metadata Cache",
                {
                    "Hits": snapshot["cache_hits"],
                    "Misses": snapshot["cache_misses"],
                    "Refreshed": snapshot["network_requests"],
                    "Not Modified": snapshot["not_modified"],
                    "Stale": snapshot["stale_used"],
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
