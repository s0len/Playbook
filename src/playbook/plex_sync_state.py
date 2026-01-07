"""Track Plex sync state to detect first-run and changes."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Set

from .utils import ensure_directory

LOGGER = logging.getLogger(__name__)


@dataclass
class SportSyncState:
    """State of a single sport's Plex sync."""

    fingerprint: str  # Metadata fingerprint at time of last successful sync
    synced_at: str  # ISO timestamp of last successful sync
    shows_synced: int = 0
    seasons_synced: int = 0
    episodes_synced: int = 0


@dataclass
class PlexSyncState:
    """Tracks what has been successfully synced to Plex.

    This allows us to:
    1. Detect first-time sync (sport not in state)
    2. Detect metadata changes since last sync
    3. Skip sync only when already synced AND unchanged
    """

    sports: Dict[str, SportSyncState] = field(default_factory=dict)
    _dirty: bool = field(default=False, repr=False)

    def needs_sync(self, sport_id: str, current_fingerprint: str) -> bool:
        """Check if a sport needs to be synced.

        Returns True if:
        - Sport has never been synced (first run)
        - Sport's metadata has changed since last sync
        """
        state = self.sports.get(sport_id)
        if state is None:
            LOGGER.debug("Sport '%s' needs sync: never synced before", sport_id)
            return True
        if state.fingerprint != current_fingerprint:
            LOGGER.debug(
                "Sport '%s' needs sync: fingerprint changed (%s -> %s)",
                sport_id,
                state.fingerprint[:8],
                current_fingerprint[:8],
            )
            return True
        return False

    def mark_synced(
        self,
        sport_id: str,
        fingerprint: str,
        *,
        shows: int = 0,
        seasons: int = 0,
        episodes: int = 0,
    ) -> None:
        """Mark a sport as successfully synced."""
        import datetime as dt

        self.sports[sport_id] = SportSyncState(
            fingerprint=fingerprint,
            synced_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            shows_synced=shows,
            seasons_synced=seasons,
            episodes_synced=episodes,
        )
        self._dirty = True

    def get_unsynced_sports(self, sport_ids: Set[str], fingerprints: Dict[str, str]) -> Set[str]:
        """Get sports that need syncing (never synced or changed)."""
        needs_sync = set()
        for sport_id in sport_ids:
            fingerprint = fingerprints.get(sport_id, "")
            if self.needs_sync(sport_id, fingerprint):
                needs_sync.add(sport_id)
        return needs_sync

    @property
    def is_dirty(self) -> bool:
        return self._dirty


class PlexSyncStateStore:
    """Persistent storage for Plex sync state."""

    def __init__(self, cache_dir: Path, filename: str = "plex-sync-state.json") -> None:
        self.cache_dir = cache_dir
        self.state_file = cache_dir / "state" / filename
        self._state: Optional[PlexSyncState] = None

    @property
    def state(self) -> PlexSyncState:
        if self._state is None:
            self._state = self._load()
        return self._state

    def _load(self) -> PlexSyncState:
        if not self.state_file.exists():
            LOGGER.debug("Plex sync state file not found, starting fresh")
            return PlexSyncState()

        try:
            with self.state_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Failed to load Plex sync state: %s", exc)
            return PlexSyncState()

        sports: Dict[str, SportSyncState] = {}
        for sport_id, sport_data in data.get("sports", {}).items():
            try:
                sports[sport_id] = SportSyncState(
                    fingerprint=sport_data.get("fingerprint", ""),
                    synced_at=sport_data.get("synced_at", ""),
                    shows_synced=sport_data.get("shows_synced", 0),
                    seasons_synced=sport_data.get("seasons_synced", 0),
                    episodes_synced=sport_data.get("episodes_synced", 0),
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed to parse sync state for %s: %s", sport_id, exc)

        return PlexSyncState(sports=sports)

    def save(self) -> None:
        if self._state is None or not self._state.is_dirty:
            return

        ensure_directory(self.state_file.parent)

        data: Dict[str, Any] = {"sports": {}}
        for sport_id, state in self._state.sports.items():
            data["sports"][sport_id] = {
                "fingerprint": state.fingerprint,
                "synced_at": state.synced_at,
                "shows_synced": state.shows_synced,
                "seasons_synced": state.seasons_synced,
                "episodes_synced": state.episodes_synced,
            }

        try:
            with self.state_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._state._dirty = False
            LOGGER.debug("Saved Plex sync state to %s", self.state_file)
        except OSError as exc:
            LOGGER.warning("Failed to save Plex sync state: %s", exc)

    def needs_sync(self, sport_id: str, current_fingerprint: str) -> bool:
        """Check if a sport needs to be synced."""
        return self.state.needs_sync(sport_id, current_fingerprint)

    def mark_synced(
        self,
        sport_id: str,
        fingerprint: str,
        *,
        shows: int = 0,
        seasons: int = 0,
        episodes: int = 0,
    ) -> None:
        """Mark a sport as successfully synced."""
        self.state.mark_synced(
            sport_id,
            fingerprint,
            shows=shows,
            seasons=seasons,
            episodes=episodes,
        )

    def get_unsynced_sports(self, sport_ids: Set[str], fingerprints: Dict[str, str]) -> Set[str]:
        """Get sports that need syncing."""
        return self.state.get_unsynced_sports(sport_ids, fingerprints)

