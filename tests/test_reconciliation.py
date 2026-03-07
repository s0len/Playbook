"""Tests for the reconciliation module (self-correction layers)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from playbook.reconciliation import detect_destination_mismatch, reconcile_stale_records

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    source_path: str = "/src/file.mkv",
    destination_path: str = "/dst/file.mkv",
    show_id: str = "f1",
    season_index: int = 1,
    episode_index: int = 5,
    status: str = "success",
):
    rec = MagicMock()
    rec.source_path = source_path
    rec.destination_path = destination_path
    rec.show_id = show_id
    rec.season_index = season_index
    rec.episode_index = episode_index
    rec.status = status
    return rec


# ---------------------------------------------------------------------------
# reconcile_stale_records
# ---------------------------------------------------------------------------


class TestReconcileStaleRecords:
    def test_removes_records_with_missing_destination(self, tmp_path):
        existing_dest = tmp_path / "exists.mkv"
        existing_dest.touch()
        missing_dest = tmp_path / "gone.mkv"

        rec_ok = _make_record(source_path="/src/a.mkv", destination_path=str(existing_dest))
        rec_stale = _make_record(source_path="/src/b.mkv", destination_path=str(missing_dest))

        store = MagicMock()
        store.iter_all.return_value = [rec_ok, rec_stale]

        removed = reconcile_stale_records(store)

        assert removed == 1
        store.delete_by_source.assert_called_once_with("/src/b.mkv")

    def test_skips_error_records(self, tmp_path):
        missing_dest = tmp_path / "gone.mkv"
        rec_error = _make_record(
            source_path="/src/err.mkv",
            destination_path=str(missing_dest),
            status="error",
        )

        store = MagicMock()
        store.iter_all.return_value = [rec_error]

        removed = reconcile_stale_records(store)

        assert removed == 0
        store.delete_by_source.assert_not_called()

    def test_no_stale_records(self, tmp_path):
        dest = tmp_path / "file.mkv"
        dest.touch()
        rec = _make_record(destination_path=str(dest))

        store = MagicMock()
        store.iter_all.return_value = [rec]

        removed = reconcile_stale_records(store)

        assert removed == 0
        store.delete_by_source.assert_not_called()


# ---------------------------------------------------------------------------
# detect_destination_mismatch
# ---------------------------------------------------------------------------


class TestDetectDestinationMismatch:
    def test_no_existing_record(self):
        store = MagicMock()
        store.get_by_destination.return_value = None

        is_mismatch, record = detect_destination_mismatch(
            Path("/dst/race.mkv"),
            match_episode_index=11,
            match_season_index=1,
            match_show_id="f1",
            processed_store=store,
        )

        assert is_mismatch is False
        assert record is None

    def test_same_episode_no_mismatch(self):
        existing = _make_record(show_id="f1", season_index=1, episode_index=11)
        store = MagicMock()
        store.get_by_destination.return_value = existing

        is_mismatch, record = detect_destination_mismatch(
            Path("/dst/race.mkv"),
            match_episode_index=11,
            match_season_index=1,
            match_show_id="f1",
            processed_store=store,
        )

        assert is_mismatch is False
        assert record is None

    def test_different_episode_is_mismatch(self):
        # FP1 was incorrectly matched to race slot
        existing = _make_record(
            source_path="/src/fp1.mkv",
            show_id="f1",
            season_index=1,
            episode_index=1,  # FP1
        )
        store = MagicMock()
        store.get_by_destination.return_value = existing

        is_mismatch, record = detect_destination_mismatch(
            Path("/dst/race.mkv"),
            match_episode_index=11,  # Race
            match_season_index=1,
            match_show_id="f1",
            processed_store=store,
        )

        assert is_mismatch is True
        assert record is existing

    def test_different_season_is_mismatch(self):
        existing = _make_record(show_id="f1", season_index=2, episode_index=11)
        store = MagicMock()
        store.get_by_destination.return_value = existing

        is_mismatch, record = detect_destination_mismatch(
            Path("/dst/race.mkv"),
            match_episode_index=11,
            match_season_index=1,
            match_show_id="f1",
            processed_store=store,
        )

        assert is_mismatch is True
        assert record is existing

    def test_different_show_is_mismatch(self):
        existing = _make_record(show_id="motogp", season_index=1, episode_index=11)
        store = MagicMock()
        store.get_by_destination.return_value = existing

        is_mismatch, record = detect_destination_mismatch(
            Path("/dst/race.mkv"),
            match_episode_index=11,
            match_season_index=1,
            match_show_id="f1",
            processed_store=store,
        )

        assert is_mismatch is True
        assert record is existing
