"""Plex metadata sync - push metadata from remote YAML to Plex.

This module syncs show/season/episode metadata (titles, sort titles, summaries,
dates, posters, backgrounds) from the remote metadata YAML files to Plex.

Shows and seasons are updated on first run or when metadata changes.
Episodes are updated when their content changes (fingerprint-based detection).
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

from .config import AppConfig, PlexSyncSettings, SportConfig
from .metadata import (
    MetadataChangeResult,
    MetadataFingerprintStore,
    ShowFingerprint,
    compute_show_fingerprint,
    load_show,
)
from .models import Episode, Season, Show
from .plex_client import (
    PLEX_TYPE_EPISODE,
    PLEX_TYPE_SEASON,
    PLEX_TYPE_SHOW,
    PlexApiError,
    PlexClient,
    PlexSyncStats,
)
from .plex_sync_state import PlexSyncStateStore
from .utils import env_bool, env_list

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class MappedMetadata:
    """Metadata fields mapped for Plex API update."""

    title: Optional[str]
    sort_title: Optional[str]
    original_title: Optional[str]
    originally_available_at: Optional[str]
    summary: Optional[str]
    poster_url: Optional[str]
    background_url: Optional[str]


def _as_int(value: object) -> Optional[int]:
    """Safely convert value to int."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first(metadata: Dict[str, object], keys: tuple[str, ...]) -> Optional[str]:
    """Get first non-empty value from metadata dict for given keys."""
    for key in keys:
        value = metadata.get(key)
        if value:
            return str(value)
    return None


def _parse_date(value: object) -> Optional[str]:
    """Parse date to ISO format string."""
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    try:
        return dt.date.fromisoformat(str(value).split(" ")[0]).isoformat()
    except ValueError:
        return None


def _resolve_asset_url(base_url: str, value: Optional[str]) -> Optional[str]:
    """Resolve asset path to full URL.
    
    If value is already a full URL, return it as-is.
    If value is a relative path, resolve it relative to the base_url's directory.
    E.g., base_url = "https://example.com/metadata/show/2025.yaml"
          value = "posters/poster.jpg"
          result = "https://example.com/metadata/show/posters/poster.jpg"
    """
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    
    # If value starts with /, it's relative to domain root
    if value.startswith("/"):
        return urljoin(base_url, value)
    
    # For relative paths, resolve relative to base_url's directory
    # If base_url ends with /, it's already a directory URL
    if base_url.endswith("/"):
        return urljoin(base_url, value)
    
    # Otherwise, base_url is a file path; get its directory
    # Add trailing slash to ensure we're treating it as a directory
    base_dir = base_url.rsplit("/", 1)[0] + "/"
    return urljoin(base_dir, value)


def _map_show_metadata(show: Show, base_url: str) -> MappedMetadata:
    """Extract Plex-compatible metadata from Show object."""
    meta = show.metadata or {}
    poster_raw = _first(meta, ("url_poster", "poster", "thumb", "cover"))
    background_raw = _first(meta, ("url_background", "background", "art", "fanart"))
    
    poster_url = _resolve_asset_url(base_url, poster_raw)
    background_url = _resolve_asset_url(base_url, background_raw)
    
    if LOGGER.isEnabledFor(logging.DEBUG):
        LOGGER.debug(
            "Mapping show '%s': poster_raw=%s -> poster_url=%s, background_raw=%s -> background_url=%s",
            show.title,
            poster_raw,
            poster_url,
            background_raw,
            background_url,
        )
    
    return MappedMetadata(
        title=show.title or meta.get("title"),
        sort_title=_first(meta, ("sort_title", "sortTitle", "slug")),
        original_title=_first(meta, ("original_title", "originalTitle")),
        originally_available_at=_parse_date(
            _first(meta, ("originally_available", "originally_available_at"))
        ),
        summary=show.summary or meta.get("summary"),
        poster_url=poster_url,
        background_url=background_url,
    )


def _map_season_metadata(season: Season, base_url: str) -> MappedMetadata:
    """Extract Plex-compatible metadata from Season object."""
    meta = season.metadata or {}
    poster_raw = _first(meta, ("url_poster", "poster", "thumb", "cover"))
    background_raw = _first(meta, ("url_background", "background", "art", "fanart"))
    
    poster_url = _resolve_asset_url(base_url, poster_raw)
    background_url = _resolve_asset_url(base_url, background_raw)
    
    if LOGGER.isEnabledFor(logging.DEBUG) and (poster_url or background_url):
        LOGGER.debug(
            "Mapping season '%s': poster_raw=%s -> poster_url=%s, background_raw=%s -> background_url=%s",
            season.title,
            poster_raw,
            poster_url,
            background_raw,
            background_url,
        )
    
    return MappedMetadata(
        title=season.title or meta.get("title"),
        sort_title=_first(meta, ("sort_title", "sortTitle", "slug")),
        original_title=_first(meta, ("original_title", "originalTitle")),
        originally_available_at=_parse_date(
            _first(meta, ("originally_available", "originally_available_at"))
        ),
        summary=season.summary or meta.get("summary"),
        poster_url=poster_url,
        background_url=background_url,
    )


def _map_episode_metadata(episode: Episode, base_url: str) -> MappedMetadata:
    """Extract Plex-compatible metadata from Episode object."""
    meta = episode.metadata or {}
    poster_raw = _first(meta, ("url_poster", "poster", "thumb", "cover"))
    background_raw = _first(meta, ("url_background", "background", "art", "fanart"))
    
    poster_url = _resolve_asset_url(base_url, poster_raw)
    background_url = _resolve_asset_url(base_url, background_raw)
    
    if LOGGER.isEnabledFor(logging.DEBUG) and (poster_url or background_url):
        LOGGER.debug(
            "Mapping episode '%s': poster_raw=%s -> poster_url=%s, background_raw=%s -> background_url=%s",
            episode.title,
            poster_raw,
            poster_url,
            background_raw,
            background_url,
        )
    
    return MappedMetadata(
        title=episode.title or meta.get("title"),
        sort_title=_first(meta, ("sort_title", "sortTitle", "slug")),
        original_title=_first(meta, ("original_title", "originalTitle")),
        originally_available_at=_parse_date(
            _first(meta, ("originally_available", "originally_available_at"))
            or episode.originally_available
        ),
        summary=episode.summary or meta.get("summary"),
        poster_url=poster_url,
        background_url=background_url,
    )


def _season_identifier(season: Season) -> str:
    """Generate a stable identifier for a season."""
    key = getattr(season, "key", None)
    if key:
        return str(key)
    if season.display_number is not None:
        return f"display:{season.display_number}"
    return f"index:{season.index}"


def _episode_identifier(episode: Episode) -> str:
    """Generate a stable identifier for an episode."""
    metadata = episode.metadata or {}
    for field in ("id", "guid", "episode_id", "uuid"):
        value = metadata.get(field)
        if value:
            return f"{field}:{value}"
    if episode.display_number is not None:
        return f"display:{episode.display_number}"
    if episode.title:
        return f"title:{episode.title}"
    return f"index:{episode.index}"


def _normalize_title(text: str) -> str:
    """Normalize title for fuzzy matching."""
    import re
    # Lowercase, remove punctuation, collapse whitespace
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _match_season_key(plex_seasons: List[Dict[str, object]], season: Season) -> Optional[str]:
    """Find the Plex rating key for a season by matching index or title."""
    target_numbers = {season.display_number, season.index}
    target_numbers = {num for num in target_numbers if num is not None}
    target_title = (season.title or "").lower()
    target_title_normalized = _normalize_title(season.title or "")

    # First pass: exact index match
    for entry in plex_seasons:
        rating_key = entry.get("ratingKey")
        if not rating_key:
            continue
        numbers = {
            _as_int(entry.get("index")),
            _as_int(entry.get("seasonNumber")),
            _as_int(entry.get("parentIndex")),
        }
        if target_numbers & {num for num in numbers if num is not None}:
            return str(rating_key)

    # Second pass: exact title match (case-insensitive)
    for entry in plex_seasons:
        rating_key = entry.get("ratingKey")
        if not rating_key:
            continue
        if target_title and str(entry.get("title") or "").lower() == target_title:
            return str(rating_key)

    # Third pass: fuzzy title match (normalized)
    for entry in plex_seasons:
        rating_key = entry.get("ratingKey")
        if not rating_key:
            continue
        entry_title_normalized = _normalize_title(str(entry.get("title") or ""))
        if target_title_normalized and entry_title_normalized == target_title_normalized:
            LOGGER.debug(
                "Fuzzy matched season '%s' to Plex season '%s'",
                season.title,
                entry.get("title"),
            )
            return str(rating_key)

    return None


def _match_episode_key(plex_episodes: List[Dict[str, object]], episode: Episode) -> Optional[str]:
    """Find the Plex rating key for an episode by matching index or title.

    Uses multiple matching strategies:
    1. Exact index match
    2. Exact title match (case-insensitive)
    3. Fuzzy title match (normalized - removes punctuation)
    4. Partial title match (episode title contained in Plex title or vice versa)
    """
    target_numbers = {episode.display_number, episode.index}
    target_numbers = {num for num in target_numbers if num is not None}
    target_title = (episode.title or "").lower()
    target_title_normalized = _normalize_title(episode.title or "")

    # First pass: exact index match
    for entry in plex_episodes:
        rating_key = entry.get("ratingKey")
        if not rating_key:
            continue
        numbers = {
            _as_int(entry.get("index")),
            _as_int(entry.get("parentIndex")),
        }
        if target_numbers & {num for num in numbers if num is not None}:
            return str(rating_key)

    # Second pass: exact title match (case-insensitive)
    for entry in plex_episodes:
        rating_key = entry.get("ratingKey")
        if not rating_key:
            continue
        if target_title and str(entry.get("title") or "").lower() == target_title:
            return str(rating_key)

    # Third pass: fuzzy title match (normalized)
    for entry in plex_episodes:
        rating_key = entry.get("ratingKey")
        if not rating_key:
            continue
        entry_title_normalized = _normalize_title(str(entry.get("title") or ""))
        if target_title_normalized and entry_title_normalized == target_title_normalized:
            LOGGER.debug(
                "Fuzzy matched episode '%s' to Plex episode '%s'",
                episode.title,
                entry.get("title"),
            )
            return str(rating_key)

    # Fourth pass: partial title match (one contains the other)
    if target_title_normalized:
        for entry in plex_episodes:
            rating_key = entry.get("ratingKey")
            if not rating_key:
                continue
            entry_title_normalized = _normalize_title(str(entry.get("title") or ""))
            if not entry_title_normalized:
                continue
            # Check if one title contains the other
            if (
                target_title_normalized in entry_title_normalized
                or entry_title_normalized in target_title_normalized
            ):
                LOGGER.debug(
                    "Partial matched episode '%s' to Plex episode '%s'",
                    episode.title,
                    entry.get("title"),
                )
                return str(rating_key)

    return None


def _apply_metadata(
    client: PlexClient,
    rating_key: str,
    mapped: MappedMetadata,
    *,
    type_code: int,
    label: str,
    dry_run: bool,
    stats: PlexSyncStats,
) -> bool:
    """Apply metadata to a Plex item.

    Returns True if any updates were made.
    """
    fields = {
        "type": type_code,
        "title": mapped.title,
        "sortTitle": mapped.sort_title,
        "originalTitle": mapped.original_title,
        "originallyAvailableAt": mapped.originally_available_at,
        "summary": mapped.summary,
    }
    # Remove None/empty values (except type)
    fields = {key: value for key, value in fields.items() if value or key == "type"}

    updated = False

    if len(fields) > 1:  # More than just 'type'
        if dry_run:
            LOGGER.info("Dry-run: would update %s %s with %s", label, rating_key, fields)
        else:
            try:
                if client.update_metadata(rating_key, fields, lock_fields=True):
                    LOGGER.info("Updated %s metadata (%s)", label, rating_key)
                    updated = True
                stats.api_calls += 1
            except PlexApiError as exc:
                LOGGER.error("Failed to update %s %s: %s", label, rating_key, exc)
                stats.errors.append(f"{label} {rating_key}: {exc}")

    # Handle assets: poster -> 'thumb', background -> 'art'
    asset_mappings = [
        ("poster_url", "thumb", "poster"),
        ("background_url", "art", "background"),
    ]
    for attr, element, display_name in asset_mappings:
        asset_url = getattr(mapped, attr)
        if not asset_url:
            LOGGER.debug("No %s URL found for %s (%s)", display_name, label, rating_key)
            continue
        if dry_run:
            LOGGER.info("Dry-run: would set %s %s %s to %s", label, rating_key, display_name, asset_url)
        else:
            try:
                client.set_asset(rating_key, element, asset_url)
                LOGGER.info("Set %s %s for %s", display_name, label, rating_key)
                stats.assets_updated += 1
                stats.api_calls += 1
                updated = True
            except PlexApiError as exc:
                LOGGER.error("Failed to set %s %s for %s: %s", label, display_name, rating_key, exc)
                stats.assets_failed += 1
                stats.errors.append(f"{label} {rating_key} {display_name}: {exc}")

    return updated


class PlexMetadataSync:
    """Syncs metadata from remote YAML to Plex.

    Uses fingerprint-based change detection to minimize unnecessary updates.
    Shows/seasons update on first run or when metadata changes.
    Episodes update when their specific content changes.
    """

    def __init__(
        self,
        config: AppConfig,
        *,
        plex_url: Optional[str] = None,
        plex_token: Optional[str] = None,
        library_id: Optional[str] = None,
        library_name: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False,
        timeout: float = 15.0,
        rate_limit_delay: float = 0.1,
        sports_filter: Optional[List[str]] = None,
        scan_wait: Optional[float] = None,
    ) -> None:
        self.config = config
        self.dry_run = dry_run
        self.force = force
        self.sports_filter = sports_filter

        # Resolve settings from config + env vars + explicit params
        plex_cfg = config.settings.plex_sync

        self.plex_url = plex_url or os.getenv("PLEX_URL") or plex_cfg.url
        self.plex_token = plex_token or os.getenv("PLEX_TOKEN") or plex_cfg.token
        self.library_id = library_id or os.getenv("PLEX_LIBRARY_ID") or plex_cfg.library_id
        self.library_name = library_name or os.getenv("PLEX_LIBRARY_NAME") or plex_cfg.library_name

        env_timeout = os.getenv("PLEX_TIMEOUT")
        self.timeout = float(env_timeout) if env_timeout else (timeout or plex_cfg.timeout)
        self.rate_limit_delay = rate_limit_delay
        self.scan_wait = scan_wait if scan_wait is not None else plex_cfg.scan_wait

        self._client: Optional[PlexClient] = None
        self._library_id_resolved: Optional[str] = None
        self._fingerprint_store: Optional[MetadataFingerprintStore] = None
        self._sync_state_store: Optional[PlexSyncStateStore] = None

    @property
    def client(self) -> PlexClient:
        """Lazily create the Plex client."""
        if self._client is None:
            if not self.plex_url or not self.plex_token:
                raise PlexApiError("Plex URL and token are required")
            self._client = PlexClient(
                self.plex_url,
                self.plex_token,
                timeout=self.timeout,
                rate_limit_delay=self.rate_limit_delay,
            )
        return self._client

    @property
    def fingerprint_store(self) -> MetadataFingerprintStore:
        """Lazily create the fingerprint store."""
        if self._fingerprint_store is None:
            self._fingerprint_store = MetadataFingerprintStore(
                self.config.settings.cache_dir,
                filename="plex-metadata-hashes.json",
            )
        return self._fingerprint_store

    @property
    def sync_state_store(self) -> PlexSyncStateStore:
        """Lazily create the sync state store."""
        if self._sync_state_store is None:
            self._sync_state_store = PlexSyncStateStore(
                self.config.settings.cache_dir,
            )
        return self._sync_state_store

    def resolve_library(self) -> str:
        """Resolve and cache the target library ID."""
        if self._library_id_resolved is None:
            if not self.library_id and not self.library_name:
                raise PlexApiError(
                    "Provide a Plex library id or name "
                    "(settings.plex_metadata_sync.library_id/library_name or env PLEX_LIBRARY_ID/PLEX_LIBRARY_NAME)"
                )
            self._library_id_resolved = self.client.find_library(
                library_id=self.library_id,
                library_name=self.library_name,
                require_type="show",
            )
        return self._library_id_resolved

    def get_sports_needing_sync(self) -> Set[str]:
        """Get sport IDs that need syncing (never synced or metadata changed).

        This allows the processor to decide whether to run sync at all.
        """
        sports = self._get_target_sports()
        needing_sync: Set[str] = set()

        for sport in sports:
            # Load show to compute fingerprint
            try:
                show = load_show(self.config.settings, sport.metadata)
                fingerprint = compute_show_fingerprint(show, sport.metadata)
            except Exception as exc:  # noqa: BLE001
                LOGGER.debug("Failed to load metadata for %s: %s", sport.id, exc)
                continue

            # Check if this sport needs syncing (use digest as the fingerprint)
            if self.sync_state_store.needs_sync(sport.id, fingerprint.digest):
                needing_sync.add(sport.id)

        return needing_sync

    def sync_all(self, *, trigger_scan: bool = True) -> PlexSyncStats:
        """Sync all configured sports to Plex.

        Args:
            trigger_scan: If True, trigger a library scan before syncing to ensure
                Plex knows about recently processed files.

        Returns statistics about what was updated.
        """
        stats = PlexSyncStats()

        try:
            library_id = self.resolve_library()
        except PlexApiError as exc:
            LOGGER.error("Failed to resolve Plex library: %s", exc)
            stats.errors.append(f"Library resolution: {exc}")
            return stats

        sports = self._get_target_sports()
        if not sports:
            LOGGER.info("No sports to sync")
            return stats

        # Trigger library scan so Plex picks up newly processed files
        if trigger_scan and not self.dry_run and self.scan_wait > 0:
            try:
                self.client.scan_library(library_id)
                stats.api_calls += 1
                # Wait for Plex to start processing
                LOGGER.info("Waiting %.1fs for Plex to scan new files...", self.scan_wait)
                time.sleep(self.scan_wait)
            except PlexApiError as exc:
                LOGGER.warning("Failed to trigger library scan: %s (continuing anyway)", exc)

        LOGGER.info("Starting Plex metadata sync for %d sport(s)", len(sports))

        for sport in sports:
            try:
                self._sync_sport(sport, library_id, stats)
            except PlexApiError as exc:
                LOGGER.error("Plex API error for sport %s: %s", sport.id, exc)
                stats.errors.append(f"Sport {sport.id}: {exc}")
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Unexpected error syncing %s: %s", sport.id, exc)
                stats.errors.append(f"Sport {sport.id}: {exc}")

        self.fingerprint_store.save()
        self.sync_state_store.save()  # Persist sync state

        if stats.has_activity():
            summary = stats.summary()
            LOGGER.info(
                "Plex sync complete: shows=%d/%d seasons=%d/%d episodes=%d/%d assets=%d",
                summary["shows"]["updated"],
                summary["shows"]["skipped"],
                summary["seasons"]["updated"],
                summary["seasons"]["skipped"],
                summary["episodes"]["updated"],
                summary["episodes"]["skipped"],
                summary["assets"]["updated"],
            )
            # Log not-found items
            not_found_total = summary["seasons"]["not_found"] + summary["episodes"]["not_found"]
            if not_found_total:
                LOGGER.warning(
                    "Plex sync: %d season(s) and %d episode(s) not found in Plex library",
                    summary["seasons"]["not_found"],
                    summary["episodes"]["not_found"],
                )
            # Log errors
            if stats.errors:
                LOGGER.error("Plex sync: %d error(s) occurred", len(stats.errors))
                for error in stats.errors[:10]:  # Show first 10
                    LOGGER.error("  - %s", error)
                if len(stats.errors) > 10:
                    LOGGER.error("  ... and %d more errors", len(stats.errors) - 10)
        else:
            LOGGER.info("Plex sync complete: no updates needed")

        return stats

    def _get_target_sports(self) -> List[SportConfig]:
        """Get list of sports to sync, respecting filter."""
        all_sports = [sport for sport in self.config.sports if sport.enabled]

        if self.sports_filter:
            filter_set = set(self.sports_filter)
            return [sport for sport in all_sports if sport.id in filter_set]

        return all_sports

    def _sync_sport(
        self,
        sport: SportConfig,
        library_id: str,
        stats: PlexSyncStats,
    ) -> None:
        """Sync a single sport to Plex."""
        LOGGER.info("Syncing sport: %s (%s)", sport.id, sport.name)

        # Load metadata from remote YAML
        show = load_show(self.config.settings, sport.metadata)

        # Compute and compare fingerprint
        previous_fingerprint = self.fingerprint_store.get(sport.id)
        fingerprint = compute_show_fingerprint(show, sport.metadata)
        change = self.fingerprint_store.update(sport.id, fingerprint)

        # Check against sync state (tracks actual Plex syncs, not just fingerprints)
        needs_plex_sync = self.sync_state_store.needs_sync(sport.id, fingerprint.digest)
        is_first_sync = needs_plex_sync and previous_fingerprint is None

        LOGGER.debug(
            "Sport %s: needs_plex_sync=%s, fingerprint_changed=%s, is_first_sync=%s",
            sport.id,
            needs_plex_sync,
            change.updated,
            is_first_sync,
        )

        # Find show in Plex
        search_result = self.client.search_show(library_id, show.title)
        stats.api_calls += 1

        if search_result.result is None:
            close_matches_msg = ""
            if search_result.close_matches:
                close_matches_msg = f" (close matches: {search_result.close_matches})"
            LOGGER.warning(
                "Show not found in Plex: '%s' (library %s)%s",
                show.title,
                library_id,
                close_matches_msg,
            )
            stats.errors.append(f"Show not found: {show.title}")
            return

        plex_show = search_result.result
        show_rating = str(plex_show.get("ratingKey"))
        if not show_rating:
            LOGGER.error("Show ratingKey missing for '%s'", show.title)
            stats.errors.append(f"Missing ratingKey: {show.title}")
            return

        base_url = sport.metadata.url

        # Track stats before sync
        shows_before = stats.shows_updated
        seasons_before = stats.seasons_updated
        episodes_before = stats.episodes_updated

        # Sync show metadata (if force, first sync, or sync state says we need it)
        self._sync_show(
            show=show,
            show_rating=show_rating,
            base_url=base_url,
            change=change,
            is_first_sync=is_first_sync or needs_plex_sync,
            stats=stats,
        )

        # Sync seasons and episodes
        self._sync_seasons_and_episodes(
            show=show,
            show_rating=show_rating,
            base_url=base_url,
            fingerprint=fingerprint,
            previous_fingerprint=previous_fingerprint,
            change=change,
            is_first_sync=is_first_sync or needs_plex_sync,
            stats=stats,
        )

        # Mark sport as synced if we made any updates (or dry-run would have)
        shows_synced = stats.shows_updated - shows_before
        seasons_synced = stats.seasons_updated - seasons_before
        episodes_synced = stats.episodes_updated - episodes_before

        if not self.dry_run:
            self.sync_state_store.mark_synced(
                sport.id,
                fingerprint.digest,
                shows=shows_synced,
                seasons=seasons_synced,
                episodes=episodes_synced,
            )

    def _sync_show(
        self,
        *,
        show: Show,
        show_rating: str,
        base_url: str,
        change: MetadataChangeResult,
        is_first_sync: bool,
        stats: PlexSyncStats,
    ) -> None:
        """Sync show-level metadata."""
        should_update = self.force or change.updated or is_first_sync

        if not should_update:
            LOGGER.debug("Show '%s' unchanged, skipping", show.title)
            stats.shows_skipped += 1
            return

        mapped = _map_show_metadata(show, base_url)
        if _apply_metadata(
            self.client,
            show_rating,
            mapped,
            type_code=PLEX_TYPE_SHOW,
            label=f"show '{show.title}'",
            dry_run=self.dry_run,
            stats=stats,
        ):
            stats.shows_updated += 1
        else:
            stats.shows_skipped += 1

    def _sync_seasons_and_episodes(
        self,
        *,
        show: Show,
        show_rating: str,
        base_url: str,
        fingerprint: ShowFingerprint,
        previous_fingerprint: Optional[ShowFingerprint],
        change: MetadataChangeResult,
        is_first_sync: bool,
        stats: PlexSyncStats,
    ) -> None:
        """Sync season and episode metadata."""
        # Fetch Plex seasons once
        plex_seasons = self.client.list_children(show_rating)
        stats.api_calls += 1

        # Debug: log what Plex has
        if LOGGER.isEnabledFor(logging.DEBUG):
            plex_season_info = [
                f"idx={s.get('index')} title='{s.get('title')}' key={s.get('ratingKey')}"
                for s in plex_seasons
            ]
            LOGGER.debug(
                "Plex seasons for '%s': %s",
                show.title,
                plex_season_info[:10],  # Limit to first 10
            )

        # Build season rating key cache
        season_rating_cache: Dict[str, str] = {}
        for season in show.seasons:
            season_id = _season_identifier(season)
            rating_key = _match_season_key(plex_seasons, season)
            if rating_key:
                season_rating_cache[season_id] = rating_key

        # Determine which seasons need updating
        seasons_to_update: Set[str] = set()
        if self.force or change.invalidate_all or is_first_sync:
            seasons_to_update = {_season_identifier(s) for s in show.seasons}
        elif change.changed_seasons:
            seasons_to_update = set(change.changed_seasons)

        # Sync seasons
        for season in show.seasons:
            season_id = _season_identifier(season)
            rating_key = season_rating_cache.get(season_id)

            if not rating_key:
                LOGGER.warning("Season not found in Plex: %s / %s", show.title, season.title)
                stats.seasons_not_found += 1
                continue

            if season_id in seasons_to_update:
                mapped = _map_season_metadata(season, base_url)
                if _apply_metadata(
                    self.client,
                    rating_key,
                    mapped,
                    type_code=PLEX_TYPE_SEASON,
                    label=f"season '{season.title}'",
                    dry_run=self.dry_run,
                    stats=stats,
                ):
                    stats.seasons_updated += 1
                else:
                    stats.seasons_skipped += 1
            else:
                stats.seasons_skipped += 1

        # Sync episodes (with caching to avoid N+1)
        episode_cache: Dict[str, List[Dict[str, Any]]] = {}

        for season in show.seasons:
            season_id = _season_identifier(season)
            rating_key = season_rating_cache.get(season_id)

            if not rating_key:
                continue

            # Fetch and cache episodes for this season
            if season_id not in episode_cache:
                episode_cache[season_id] = self.client.list_children(rating_key)
                stats.api_calls += 1

                # Debug: log what Plex has for this season
                if LOGGER.isEnabledFor(logging.DEBUG):
                    eps = episode_cache[season_id]
                    ep_info = [
                        f"idx={e.get('index')} '{e.get('title', '')[:30]}'"
                        for e in eps[:5]  # First 5
                    ]
                    LOGGER.debug(
                        "Plex episodes for season '%s': %s%s",
                        season.title,
                        ep_info,
                        f" ...and {len(eps) - 5} more" if len(eps) > 5 else "",
                    )

            plex_episodes = episode_cache[season_id]

            # Get previous episode hashes for change detection
            previous_episode_hashes: Dict[str, str] = {}
            if previous_fingerprint:
                previous_episode_hashes = previous_fingerprint.episode_hashes.get(season_id, {})

            current_episode_hashes = fingerprint.episode_hashes.get(season_id, {})

            for episode in season.episodes:
                episode_id = _episode_identifier(episode)
                episode_rating = _match_episode_key(plex_episodes, episode)

                if not episode_rating:
                    LOGGER.warning(
                        "Episode not found in Plex: %s / %s / %s",
                        show.title,
                        season.title,
                        episode.title,
                    )
                    stats.episodes_not_found += 1
                    continue

                # Check if episode changed
                current_hash = current_episode_hashes.get(episode_id)
                previous_hash = previous_episode_hashes.get(episode_id)
                episode_changed = (
                    self.force
                    or is_first_sync
                    or change.invalidate_all
                    or season_id in change.changed_seasons
                    or episode_id in change.changed_episodes.get(season_id, set())
                    or current_hash != previous_hash
                    or previous_hash is None
                )

                if not episode_changed:
                    stats.episodes_skipped += 1
                    continue

                mapped = _map_episode_metadata(episode, base_url)
                if _apply_metadata(
                    self.client,
                    episode_rating,
                    mapped,
                    type_code=PLEX_TYPE_EPISODE,
                    label=f"episode '{episode.title}'",
                    dry_run=self.dry_run,
                    stats=stats,
                ):
                    stats.episodes_updated += 1
                else:
                    stats.episodes_skipped += 1


def create_plex_sync_from_config(config: AppConfig) -> Optional[PlexMetadataSync]:
    """Create a PlexMetadataSync instance from config with env var overrides.

    Returns None if sync is disabled.
    """
    plex_cfg = config.settings.plex_sync

    # Check if enabled
    env_enabled = env_bool("PLEX_SYNC_ENABLED")
    enabled = plex_cfg.enabled if env_enabled is None else env_enabled
    if not enabled:
        return None

    # Resolve settings
    env_force = env_bool("PLEX_FORCE")
    env_dry_run = env_bool("PLEX_SYNC_DRY_RUN")
    env_sports = env_list("PLEX_SPORTS")

    return PlexMetadataSync(
        config=config,
        force=plex_cfg.force if env_force is None else env_force,
        dry_run=plex_cfg.dry_run if env_dry_run is None else env_dry_run,
        sports_filter=env_sports if env_sports is not None else (plex_cfg.sports or None),
    )


# Legacy CLI entrypoint (can be removed once integrated into processor)
def main() -> int:
    """CLI entrypoint for standalone execution."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Sync Plex metadata from remote YAML.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(os.getenv("CONFIG_PATH", "/config/playbook.yaml")),
        help="Path to playbook YAML config",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s\n%(message)s\n",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    from .config import load_config

    try:
        config = load_config(args.config)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Failed to load config: %s", exc)
        return 1

    sync = create_plex_sync_from_config(config)
    if sync is None:
        LOGGER.info(
            "Plex metadata sync is disabled; "
            "set settings.plex_metadata_sync.enabled or PLEX_SYNC_ENABLED=true"
        )
        return 0

    try:
        stats = sync.sync_all()
    except PlexApiError as exc:
        LOGGER.error("Plex sync failed: %s", exc)
        return 2

    return 1 if stats.errors else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
