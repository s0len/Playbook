"""Metadata fingerprinting and change tracking.

This module handles tracking metadata fingerprints to detect changes,
enabling efficient cache invalidation when show/season/episode data updates.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Episode, Season, Show
from .utils import ensure_directory, hash_text

LOGGER = logging.getLogger(__name__)


class MetadataFetchStatistics:
    """Thread-safe accumulator for metadata fetch metrics."""

    def __init__(self) -> None:
        self.cache_hits = 0
        self.cache_misses = 0
        self.network_requests = 0
        self.not_modified = 0
        self.stale_used = 0
        self.failures = 0
        self._lock = threading.Lock()

    def record_cache_hit(self) -> None:
        with self._lock:
            self.cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self.cache_misses += 1

    def record_network_request(self) -> None:
        with self._lock:
            self.network_requests += 1

    def record_not_modified(self) -> None:
        with self._lock:
            self.not_modified += 1

    def record_stale_used(self) -> None:
        with self._lock:
            self.stale_used += 1

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "network_requests": self.network_requests,
                "not_modified": self.not_modified,
                "stale_used": self.stale_used,
                "failures": self.failures,
            }

    def has_activity(self) -> bool:
        with self._lock:
            return any(
                (
                    self.cache_hits,
                    self.cache_misses,
                    self.network_requests,
                    self.not_modified,
                    self.stale_used,
                    self.failures,
                )
            )


def _json_default(obj: Any) -> Any:
    """JSON encoder for datetime and date objects."""
    if isinstance(obj, dt.datetime):
        return obj.isoformat(timespec="seconds")
    if isinstance(obj, dt.date):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


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


def _clean_season_metadata(metadata: Any) -> Any:
    """Remove nested episode data from season metadata for hashing."""
    if not isinstance(metadata, dict):
        return metadata
    cleaned = dict(metadata)
    cleaned.pop("episodes", None)
    return cleaned


def _clean_episode_metadata(metadata: Any) -> Any:
    """Clean episode metadata for hashing."""
    if not isinstance(metadata, dict):
        return metadata
    return dict(metadata)


@dataclass
class ShowFingerprint:
    """Fingerprint representing the state of show metadata.

    Used to detect changes in metadata content and track which
    seasons/episodes have been modified.
    """

    digest: str
    season_hashes: dict[str, str]
    episode_hashes: dict[str, dict[str, str]]
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "digest": self.digest,
            "seasons": dict(self.season_hashes),
            "episodes": {season: dict(episodes) for season, episodes in self.episode_hashes.items()},
        }
        if self.content_hash is not None:
            result["content_hash"] = self.content_hash
        return result

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ShowFingerprint:
        digest_raw = payload.get("digest")
        digest = str(digest_raw) if digest_raw is not None else ""
        seasons_raw = payload.get("seasons") or {}
        season_hashes = {str(key): str(value) for key, value in seasons_raw.items()}
        episodes_raw = payload.get("episodes") or {}
        episode_hashes: dict[str, dict[str, str]] = {}
        for season_key, mapping in episodes_raw.items():
            if not isinstance(mapping, dict):
                continue
            episode_hashes[str(season_key)] = {str(ep_key): str(ep_hash) for ep_key, ep_hash in mapping.items()}
        content_hash_raw = payload.get("content_hash")
        content_hash = str(content_hash_raw) if content_hash_raw is not None else None
        return cls(digest=digest, season_hashes=season_hashes, episode_hashes=episode_hashes, content_hash=content_hash)


@dataclass
class MetadataChangeResult:
    """Result of comparing metadata fingerprints.

    Indicates whether metadata changed and provides details about
    which seasons/episodes were affected.
    """

    updated: bool
    changed_seasons: set[str]
    changed_episodes: dict[str, set[str]]
    invalidate_all: bool = False


class MetadataFingerprintStore:
    """Persistent store for tracking metadata fingerprints.

    Tracks a lightweight hash of each sport's metadata to detect updates
    and enable efficient cache invalidation.
    """

    def __init__(self, cache_dir: Path, filename: str = "metadata-digests.json") -> None:
        self.cache_dir = cache_dir
        self.filename = filename
        self.path = self.cache_dir / "state" / self.filename
        self._fingerprints: dict[str, ShowFingerprint] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to load metadata fingerprint cache %s: %s", self.path, exc)
            return

        if not isinstance(payload, dict):
            LOGGER.warning("Ignoring malformed metadata fingerprint cache %s", self.path)
            return

        fingerprints: dict[str, ShowFingerprint] = {}
        for key, value in payload.items():
            if not isinstance(key, str):
                continue
            if isinstance(value, str):
                fingerprints[key] = ShowFingerprint(digest=value, season_hashes={}, episode_hashes={})
            elif isinstance(value, dict):
                try:
                    fingerprints[key] = ShowFingerprint.from_dict(value)
                except Exception:  # pragma: no cover - defensive
                    LOGGER.debug("Skipping malformed metadata fingerprint entry for %s", key)
            else:
                LOGGER.debug("Skipping malformed metadata fingerprint entry for %s", key)
        self._fingerprints = fingerprints

    def get(self, key: str) -> ShowFingerprint | None:
        return self._fingerprints.get(key)

    def update(self, key: str, fingerprint: ShowFingerprint) -> MetadataChangeResult:
        """Update fingerprint and return change result."""
        existing = self._fingerprints.get(key)
        if existing is None:
            self._fingerprints[key] = fingerprint
            self._dirty = True
            return MetadataChangeResult(
                updated=True,
                changed_seasons=set(),
                changed_episodes={},
                invalidate_all=False,
            )

        if existing.digest == fingerprint.digest:
            if (
                existing.season_hashes != fingerprint.season_hashes
                or existing.episode_hashes != fingerprint.episode_hashes
            ):
                self._fingerprints[key] = fingerprint
                self._dirty = True
            return MetadataChangeResult(
                updated=False,
                changed_seasons=set(),
                changed_episodes={},
                invalidate_all=False,
            )

        if (not existing.season_hashes and not existing.episode_hashes) or (
            not existing.episode_hashes and any(fingerprint.episode_hashes.values())
        ):
            self._fingerprints[key] = fingerprint
            self._dirty = True
            return MetadataChangeResult(
                updated=True,
                changed_seasons=set(),
                changed_episodes={},
                invalidate_all=True,
            )

        existing_seasons = existing.season_hashes
        new_seasons = fingerprint.season_hashes

        changed_seasons: set[str] = set()
        for season_key, old_hash in existing_seasons.items():
            new_hash = new_seasons.get(season_key)
            if new_hash is None or new_hash != old_hash:
                changed_seasons.add(season_key)

        existing_episodes = existing.episode_hashes
        new_episodes = fingerprint.episode_hashes
        changed_episodes: dict[str, set[str]] = {}

        for season_key, previous_episode_map in existing_episodes.items():
            if season_key in changed_seasons:
                continue
            new_episode_map = new_episodes.get(season_key)
            if new_episode_map is None:
                changed_seasons.add(season_key)
                continue

            episode_changes: set[str] = set()
            for episode_key, old_hash in previous_episode_map.items():
                new_hash = new_episode_map.get(episode_key)
                if new_hash is None or new_hash != old_hash:
                    episode_changes.add(episode_key)

            if episode_changes:
                changed_episodes[season_key] = episode_changes

        self._fingerprints[key] = fingerprint
        self._dirty = True
        return MetadataChangeResult(
            updated=True,
            changed_seasons=changed_seasons,
            changed_episodes=changed_episodes,
            invalidate_all=False,
        )

    def remove(self, key: str) -> None:
        if key in self._fingerprints:
            del self._fingerprints[key]
            self._dirty = True

    def save(self) -> None:
        if not self._dirty:
            return

        ensure_directory(self.path.parent)
        serialised = {key: fp.to_dict() for key, fp in self._fingerprints.items()}
        try:
            with self.path.open("w", encoding="utf-8") as handle:
                json.dump(serialised, handle, ensure_ascii=False, indent=2, sort_keys=True)
            self._dirty = False
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Failed to write metadata fingerprint cache %s: %s", self.path, exc)


def _compute_content_hash(show: Show, show_slug: str) -> str:
    """Compute a quick hash from show metadata and slug.

    This hash captures the inputs that affect the fingerprint:
    - show_slug (identifier for the show)
    - show.metadata (raw metadata content)

    Returns a deterministic SHA1 hash string.
    """
    content_payload = {
        "show_slug": show_slug,
        "metadata": show.metadata,
    }
    serialized = json.dumps(
        content_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )
    return hash_text(serialized)


def compute_show_fingerprint(
    show: Show,
    show_slug: str,
    cached_fingerprint: ShowFingerprint | None = None,
) -> ShowFingerprint:
    """Compute a fingerprint representing the effective metadata for a show.

    If a cached fingerprint is provided and its content_hash matches,
    returns the cached version to avoid recomputation.

    Args:
        show: The show to fingerprint
        show_slug: The show's API slug identifier
        cached_fingerprint: Optional previously cached fingerprint

    Returns:
        ShowFingerprint representing the current state
    """
    content_hash = _compute_content_hash(show, show_slug)

    # Fast path: return cached fingerprint if content hasn't changed
    if cached_fingerprint is not None and cached_fingerprint.content_hash == content_hash:
        return cached_fingerprint

    # Compute full fingerprint
    fingerprint_payload = {
        "show_slug": show_slug,
        "metadata": show.metadata,
    }
    serialized = json.dumps(
        fingerprint_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )
    digest = hash_text(serialized)

    season_hashes: dict[str, str] = {}
    episode_hashes: dict[str, dict[str, str]] = {}

    for season in show.seasons:
        season_key = _season_identifier(season)
        season_payload = {
            "key": season_key,
            "title": season.title,
            "summary": season.summary,
            "index": season.index,
            "display_number": season.display_number,
            "round_number": season.round_number,
            "sort_title": season.sort_title,
            "metadata": _clean_season_metadata(season.metadata),
        }
        season_serialized = json.dumps(
            season_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=_json_default,
        )
        season_hashes[season_key] = hash_text(season_serialized)

        episode_hash_map: dict[str, str] = {}
        for episode in season.episodes:
            episode_payload = {
                "title": episode.title,
                "summary": episode.summary,
                "index": episode.index,
                "display_number": episode.display_number,
                "aliases": episode.aliases,
                "originally_available": (
                    episode.originally_available.isoformat() if episode.originally_available else None
                ),
                "metadata": _clean_episode_metadata(episode.metadata),
            }
            episode_serialized = json.dumps(
                episode_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=_json_default,
            )
            episode_key = _episode_identifier(episode)
            episode_hash_map[episode_key] = hash_text(episode_serialized)
        episode_hashes[season_key] = episode_hash_map

    return ShowFingerprint(
        digest=digest,
        season_hashes=season_hashes,
        episode_hashes=episode_hashes,
        content_hash=content_hash,
    )
