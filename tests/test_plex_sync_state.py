"""Tests for Plex sync state tracking."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.playbook.plex_sync_state import (
    PlexSyncState,
    PlexSyncStateStore,
    SportSyncState,
)


class TestSportSyncState:
    """Tests for SportSyncState dataclass."""

    def test_basic_creation(self) -> None:
        state = SportSyncState(
            fingerprint="abc123",
            synced_at="2024-01-01T00:00:00Z",
            shows_synced=1,
            seasons_synced=2,
            episodes_synced=10,
        )
        assert state.fingerprint == "abc123"
        assert state.synced_at == "2024-01-01T00:00:00Z"
        assert state.shows_synced == 1
        assert state.seasons_synced == 2
        assert state.episodes_synced == 10


class TestPlexSyncState:
    """Tests for PlexSyncState."""

    def test_needs_sync_never_synced(self) -> None:
        """Sport needs sync if never synced before."""
        state = PlexSyncState()
        assert state.needs_sync("nhl", "fp123") is True

    def test_needs_sync_fingerprint_changed(self) -> None:
        """Sport needs sync if fingerprint changed."""
        state = PlexSyncState()
        state.mark_synced("nhl", "old_fp")
        assert state.needs_sync("nhl", "new_fp") is True

    def test_needs_sync_unchanged(self) -> None:
        """Sport doesn't need sync if fingerprint unchanged."""
        state = PlexSyncState()
        state.mark_synced("nhl", "fp123")
        assert state.needs_sync("nhl", "fp123") is False

    def test_mark_synced_sets_state(self) -> None:
        """mark_synced creates proper state entry."""
        state = PlexSyncState()
        state.mark_synced("nhl", "fp123", shows=1, seasons=2, episodes=10)

        assert "nhl" in state.sports
        sport_state = state.sports["nhl"]
        assert sport_state.fingerprint == "fp123"
        assert sport_state.shows_synced == 1
        assert sport_state.seasons_synced == 2
        assert sport_state.episodes_synced == 10
        assert sport_state.synced_at  # Should have timestamp

    def test_mark_synced_marks_dirty(self) -> None:
        """mark_synced sets dirty flag."""
        state = PlexSyncState()
        assert state.is_dirty is False
        state.mark_synced("nhl", "fp123")
        assert state.is_dirty is True

    def test_get_unsynced_sports(self) -> None:
        """get_unsynced_sports returns sports needing sync."""
        state = PlexSyncState()
        state.mark_synced("nhl", "fp_nhl")
        state.mark_synced("nfl", "fp_nfl_old")

        # nhl unchanged, nfl changed, mlb never synced
        fingerprints = {
            "nhl": "fp_nhl",  # unchanged
            "nfl": "fp_nfl_new",  # changed
            "mlb": "fp_mlb",  # new
        }
        sport_ids = {"nhl", "nfl", "mlb"}

        unsynced = state.get_unsynced_sports(sport_ids, fingerprints)
        assert unsynced == {"nfl", "mlb"}


class TestPlexSyncStateStore:
    """Tests for PlexSyncStateStore persistence."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """State can be saved and loaded."""
        store = PlexSyncStateStore(tmp_path)
        store.mark_synced("nhl", "fp123", shows=1, seasons=2, episodes=10)
        store.save()

        # Create new store and load
        store2 = PlexSyncStateStore(tmp_path)
        assert store2.needs_sync("nhl", "fp123") is False
        assert store2.needs_sync("nhl", "fp_different") is True
        assert store2.needs_sync("nfl", "anything") is True

    def test_load_empty_creates_fresh(self, tmp_path: Path) -> None:
        """Loading without file creates fresh state."""
        store = PlexSyncStateStore(tmp_path)
        assert store.needs_sync("nhl", "fp123") is True  # Never synced

    def test_load_corrupt_file_creates_fresh(self, tmp_path: Path) -> None:
        """Corrupt file creates fresh state."""
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "plex-sync-state.json").write_text("not valid json {{{")

        store = PlexSyncStateStore(tmp_path)
        assert store.needs_sync("nhl", "fp123") is True  # Treated as never synced

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        """save() creates state directory if needed."""
        store = PlexSyncStateStore(tmp_path)
        store.mark_synced("nhl", "fp123")
        store.save()

        assert (tmp_path / "state" / "plex-sync-state.json").exists()

    def test_save_skipped_if_not_dirty(self, tmp_path: Path) -> None:
        """save() does nothing if state not dirty."""
        store = PlexSyncStateStore(tmp_path)
        store.save()
        # File shouldn't exist since nothing was modified
        assert not (tmp_path / "state" / "plex-sync-state.json").exists()

    def test_file_format(self, tmp_path: Path) -> None:
        """Verify the JSON file format."""
        store = PlexSyncStateStore(tmp_path)
        store.mark_synced("nhl", "fp123", shows=1, seasons=2, episodes=10)
        store.save()

        with (tmp_path / "state" / "plex-sync-state.json").open() as f:
            data = json.load(f)

        assert "sports" in data
        assert "nhl" in data["sports"]
        assert data["sports"]["nhl"]["fingerprint"] == "fp123"
        assert data["sports"]["nhl"]["shows_synced"] == 1
        assert data["sports"]["nhl"]["seasons_synced"] == 2
        assert data["sports"]["nhl"]["episodes_synced"] == 10
        assert "synced_at" in data["sports"]["nhl"]

