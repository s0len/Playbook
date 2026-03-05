"""Tests for ManualOverrideStore and processor override integration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from playbook.persistence.manual_override_store import ManualOverrideStore


@pytest.fixture
def store(tmp_path: Path) -> ManualOverrideStore:
    """Create a ManualOverrideStore backed by a temp database."""
    return ManualOverrideStore(tmp_path / "playbook.db")


class TestManualOverrideStore:
    """CRUD operations on ManualOverrideStore."""

    def test_add_and_get(self, store: ManualOverrideStore) -> None:
        store.add_override("race.mkv", "f1", "formula-1", 2024, 3)
        result = store.get_override("race.mkv")
        assert result is not None
        assert result.filename == "race.mkv"
        assert result.sport_id == "f1"
        assert result.show_slug == "formula-1"
        assert result.season_index == 2024
        assert result.episode_index == 3
        assert result.created_at is not None

    def test_get_nonexistent(self, store: ManualOverrideStore) -> None:
        assert store.get_override("nope.mkv") is None

    def test_add_with_source_path(self, store: ManualOverrideStore) -> None:
        store.add_override("race.mkv", "f1", "formula-1", 2024, 3, source_path="/media/race.mkv")
        result = store.get_override("race.mkv")
        assert result is not None
        assert result.source_path == "/media/race.mkv"

    def test_upsert_replaces_existing(self, store: ManualOverrideStore) -> None:
        store.add_override("race.mkv", "f1", "formula-1", 2024, 3)
        store.add_override("race.mkv", "motogp", "motogp-2024", 2024, 5)
        result = store.get_override("race.mkv")
        assert result is not None
        assert result.sport_id == "motogp"
        assert result.show_slug == "motogp-2024"
        assert result.episode_index == 5
        assert store.get_count() == 1

    def test_remove_existing(self, store: ManualOverrideStore) -> None:
        store.add_override("race.mkv", "f1", "formula-1", 2024, 3)
        assert store.remove_override("race.mkv") is True
        assert store.get_override("race.mkv") is None

    def test_remove_nonexistent(self, store: ManualOverrideStore) -> None:
        assert store.remove_override("nope.mkv") is False

    def test_get_all(self, store: ManualOverrideStore) -> None:
        store.add_override("a.mkv", "f1", "f1", 2024, 1)
        store.add_override("b.mkv", "nba", "nba", 2024, 2)
        store.add_override("c.mkv", "nfl", "nfl", 2024, 3)
        results = store.get_all()
        assert len(results) == 3

    def test_get_all_with_pagination(self, store: ManualOverrideStore) -> None:
        for i in range(5):
            store.add_override(f"file{i}.mkv", "f1", "f1", 2024, i)
        assert len(store.get_all(limit=2)) == 2
        assert len(store.get_all(limit=2, offset=3)) == 2

    def test_get_count(self, store: ManualOverrideStore) -> None:
        assert store.get_count() == 0
        store.add_override("a.mkv", "f1", "f1", 2024, 1)
        store.add_override("b.mkv", "nba", "nba", 2024, 2)
        assert store.get_count() == 2

    def test_clear(self, store: ManualOverrideStore) -> None:
        store.add_override("a.mkv", "f1", "f1", 2024, 1)
        store.add_override("b.mkv", "nba", "nba", 2024, 2)

        deleted = store.clear()
        assert deleted == 2
        assert store.get_count() == 0

    def test_close(self, store: ManualOverrideStore) -> None:
        store.add_override("a.mkv", "f1", "f1", 2024, 1)
        store.close()
        # Re-opening should still work (new connection)
        assert store.get_override("a.mkv") is not None


class TestProcessorOverride:
    """Integration tests for override lookup in the processor."""

    def _make_processor_with_override(self, tmp_path, override_data):
        """Create a minimal Processor mock with a real ManualOverrideStore."""
        from playbook.models import Episode, Season, Show
        from playbook.persistence.manual_override_store import ManualOverrideStore

        store = ManualOverrideStore(tmp_path / "playbook.db")
        if override_data:
            store.add_override(**override_data)

        # Build minimal show/season/episode
        episode = Episode(title="Race 3", summary=None, originally_available=None, index=override_data["episode_index"])
        season = Season(
            key="s2024",
            title="2024",
            summary=None,
            index=override_data["season_index"],
            episodes=[episode],
        )
        show = Show(key=override_data["show_slug"], title="Formula 1", summary=None, seasons=[season])

        return store, show, season, episode

    def test_override_found_processes_file(self, tmp_path: Path) -> None:
        """When an override matches, _process_single_file should return True without pattern matching."""
        from playbook.models import ProcessingStats

        override_data = {
            "filename": "race.mkv",
            "sport_id": "f1",
            "show_slug": "formula-1",
            "season_index": 2024,
            "episode_index": 3,
        }
        store, show, season, episode = self._make_processor_with_override(tmp_path, override_data)

        # Mock the Processor just enough
        processor = MagicMock()
        processor.manual_override_store = store
        processor.config.settings.dry_run = False

        # Create a fake runtime
        runtime = MagicMock()
        runtime.sport.id = "f1"
        runtime.is_dynamic = False
        runtime.show = show
        runtime.patterns = [MagicMock()]

        processor._build_context = MagicMock(return_value={"show_title": "Formula 1"})
        processor._build_destination = MagicMock(return_value=Path("/dest/F1/S2024/race.mkv"))
        processor._handle_match = MagicMock(return_value=MagicMock())
        processor._format_log = MagicMock(return_value="log")

        # Import and call the actual method
        from playbook.processor import Processor

        result = Processor._process_override(
            processor, Path("/source/race.mkv"), store.get_override("race.mkv"), [runtime], ProcessingStats()
        )
        assert result is True
        processor._handle_match.assert_called_once()

    def test_override_sport_not_configured_falls_through(self, tmp_path: Path) -> None:
        """When the override sport is not in runtimes, should return False."""
        from playbook.models import ProcessingStats

        override_data = {
            "filename": "race.mkv",
            "sport_id": "f1",
            "show_slug": "formula-1",
            "season_index": 2024,
            "episode_index": 3,
        }
        store, show, season, episode = self._make_processor_with_override(tmp_path, override_data)

        processor = MagicMock()
        processor.manual_override_store = store
        processor._format_log = MagicMock(return_value="log")

        # No runtimes match the override sport
        runtime = MagicMock()
        runtime.sport.id = "nba"

        from playbook.processor import Processor

        result = Processor._process_override(
            processor, Path("/source/race.mkv"), store.get_override("race.mkv"), [runtime], ProcessingStats()
        )
        assert result is False

    def test_override_season_not_found_falls_through(self, tmp_path: Path) -> None:
        """When the override season doesn't exist in metadata, should return False."""
        from playbook.models import Episode, ProcessingStats, Season, Show
        from playbook.persistence.manual_override_store import ManualOverrideStore

        override_data = {
            "filename": "race.mkv",
            "sport_id": "f1",
            "show_slug": "formula-1",
            "season_index": 9999,
            "episode_index": 3,
        }
        store = ManualOverrideStore(tmp_path / "playbook.db")
        store.add_override(**override_data)

        # Show has season 2024 but override asks for 9999
        episode = Episode(title="Race 3", summary=None, originally_available=None, index=3)
        season = Season(key="s2024", title="2024", summary=None, index=2024, episodes=[episode])
        show = Show(key="formula-1", title="Formula 1", summary=None, seasons=[season])

        processor = MagicMock()
        processor.manual_override_store = store
        processor._format_log = MagicMock(return_value="log")

        runtime = MagicMock()
        runtime.sport.id = "f1"
        runtime.is_dynamic = False
        runtime.show = show

        from playbook.processor import Processor

        result = Processor._process_override(
            processor, Path("/source/race.mkv"), store.get_override("race.mkv"), [runtime], ProcessingStats()
        )
        assert result is False
