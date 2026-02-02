"""Tests for persistence layer."""

from datetime import datetime
from pathlib import Path

import pytest

from playbook.persistence import ProcessedFileRecord, ProcessedFileStore


@pytest.fixture
def store(tmp_path: Path) -> ProcessedFileStore:
    """Create a temporary ProcessedFileStore."""
    db_path = tmp_path / "test.db"
    return ProcessedFileStore(db_path)


@pytest.fixture
def sample_record() -> ProcessedFileRecord:
    """Create a sample ProcessedFileRecord."""
    return ProcessedFileRecord(
        source_path="/source/f1/race.mkv",
        destination_path="/dest/F1/2024/Race.mkv",
        sport_id="f1",
        show_id="formula-1-2024",
        season_index=0,
        episode_index=5,
        processed_at=datetime(2024, 3, 15, 10, 30, 0),
        checksum="abc123",
        status="linked",
    )


class TestProcessedFileStore:
    """Tests for ProcessedFileStore."""

    def test_record_and_retrieve_by_source(
        self, store: ProcessedFileStore, sample_record: ProcessedFileRecord
    ) -> None:
        """Test recording and retrieving a file by source path."""
        store.record_processed(sample_record)

        retrieved = store.get_by_source(sample_record.source_path)
        assert retrieved is not None
        assert retrieved.source_path == sample_record.source_path
        assert retrieved.destination_path == sample_record.destination_path
        assert retrieved.sport_id == sample_record.sport_id
        assert retrieved.show_id == sample_record.show_id
        assert retrieved.season_index == sample_record.season_index
        assert retrieved.episode_index == sample_record.episode_index
        assert retrieved.checksum == sample_record.checksum
        assert retrieved.status == sample_record.status

    def test_get_by_source_returns_none_for_missing(
        self, store: ProcessedFileStore
    ) -> None:
        """Test that get_by_source returns None for missing records."""
        result = store.get_by_source("/nonexistent/file.mkv")
        assert result is None

    def test_upsert_updates_existing_record(
        self, store: ProcessedFileStore, sample_record: ProcessedFileRecord
    ) -> None:
        """Test that recording the same source path updates the existing record."""
        store.record_processed(sample_record)

        # Update the record
        updated = ProcessedFileRecord(
            source_path=sample_record.source_path,
            destination_path="/new/dest/file.mkv",
            sport_id=sample_record.sport_id,
            show_id=sample_record.show_id,
            season_index=sample_record.season_index,
            episode_index=sample_record.episode_index,
            processed_at=datetime.now(),
            checksum="new_checksum",
            status="copied",
        )
        store.record_processed(updated)

        retrieved = store.get_by_source(sample_record.source_path)
        assert retrieved is not None
        assert retrieved.destination_path == "/new/dest/file.mkv"
        assert retrieved.checksum == "new_checksum"
        assert retrieved.status == "copied"

    def test_get_by_show(self, store: ProcessedFileStore) -> None:
        """Test retrieving records by show ID."""
        show_id = "formula-1-2024"

        # Add multiple records for the same show
        for i in range(3):
            record = ProcessedFileRecord(
                source_path=f"/source/f1/episode{i}.mkv",
                destination_path=f"/dest/F1/2024/Episode{i}.mkv",
                sport_id="f1",
                show_id=show_id,
                season_index=0,
                episode_index=i,
                processed_at=datetime.now(),
            )
            store.record_processed(record)

        # Add a record for a different show
        other_record = ProcessedFileRecord(
            source_path="/source/nba/game.mkv",
            destination_path="/dest/NBA/2024/Game.mkv",
            sport_id="nba",
            show_id="nba-2024",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
        )
        store.record_processed(other_record)

        results = store.get_by_show(show_id)
        assert len(results) == 3
        assert all(r.show_id == show_id for r in results)

    def test_get_by_season(self, store: ProcessedFileStore) -> None:
        """Test retrieving records by show and season."""
        show_id = "formula-1-2024"

        # Add records for season 0
        for i in range(2):
            record = ProcessedFileRecord(
                source_path=f"/source/f1/s0e{i}.mkv",
                destination_path=f"/dest/F1/2024/S0E{i}.mkv",
                sport_id="f1",
                show_id=show_id,
                season_index=0,
                episode_index=i,
                processed_at=datetime.now(),
            )
            store.record_processed(record)

        # Add records for season 1
        for i in range(3):
            record = ProcessedFileRecord(
                source_path=f"/source/f1/s1e{i}.mkv",
                destination_path=f"/dest/F1/2024/S1E{i}.mkv",
                sport_id="f1",
                show_id=show_id,
                season_index=1,
                episode_index=i,
                processed_at=datetime.now(),
            )
            store.record_processed(record)

        results = store.get_by_season(show_id, 0)
        assert len(results) == 2
        assert all(r.season_index == 0 for r in results)

        results = store.get_by_season(show_id, 1)
        assert len(results) == 3
        assert all(r.season_index == 1 for r in results)

    def test_get_by_sport(self, store: ProcessedFileStore) -> None:
        """Test retrieving records by sport ID."""
        # Add F1 records
        for i in range(2):
            record = ProcessedFileRecord(
                source_path=f"/source/f1/race{i}.mkv",
                destination_path=f"/dest/F1/Race{i}.mkv",
                sport_id="f1",
                show_id="formula-1-2024",
                season_index=0,
                episode_index=i,
                processed_at=datetime.now(),
            )
            store.record_processed(record)

        # Add NBA record
        record = ProcessedFileRecord(
            source_path="/source/nba/game.mkv",
            destination_path="/dest/NBA/Game.mkv",
            sport_id="nba",
            show_id="nba-2024",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
        )
        store.record_processed(record)

        f1_results = store.get_by_sport("f1")
        assert len(f1_results) == 2
        assert all(r.sport_id == "f1" for r in f1_results)

        nba_results = store.get_by_sport("nba")
        assert len(nba_results) == 1
        assert nba_results[0].sport_id == "nba"

    def test_get_by_status(self, store: ProcessedFileStore) -> None:
        """Test retrieving records by status."""
        # Add linked record
        linked = ProcessedFileRecord(
            source_path="/source/linked.mkv",
            destination_path="/dest/linked.mkv",
            sport_id="f1",
            show_id="show1",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
            status="linked",
        )
        store.record_processed(linked)

        # Add error record
        error = ProcessedFileRecord(
            source_path="/source/error.mkv",
            destination_path="/dest/error.mkv",
            sport_id="f1",
            show_id="show1",
            season_index=0,
            episode_index=1,
            processed_at=datetime.now(),
            status="error",
            error_message="Failed to create link",
        )
        store.record_processed(error)

        linked_results = store.get_by_status("linked")
        assert len(linked_results) == 1
        assert linked_results[0].status == "linked"

        error_results = store.get_errors()
        assert len(error_results) == 1
        assert error_results[0].status == "error"
        assert error_results[0].error_message == "Failed to create link"

    def test_get_recent(self, store: ProcessedFileStore) -> None:
        """Test retrieving recent records with limit."""
        # Add 5 records
        for i in range(5):
            record = ProcessedFileRecord(
                source_path=f"/source/file{i}.mkv",
                destination_path=f"/dest/file{i}.mkv",
                sport_id="f1",
                show_id="show1",
                season_index=0,
                episode_index=i,
                processed_at=datetime(2024, 1, 1, i, 0, 0),
            )
            store.record_processed(record)

        # Get last 3
        results = store.get_recent(limit=3)
        assert len(results) == 3

    def test_get_stats(self, store: ProcessedFileStore) -> None:
        """Test getting statistics."""
        # Add records with different statuses and sports
        records = [
            ProcessedFileRecord(
                source_path="/source/f1a.mkv",
                destination_path="/dest/f1a.mkv",
                sport_id="f1",
                show_id="show1",
                season_index=0,
                episode_index=0,
                processed_at=datetime.now(),
                status="linked",
            ),
            ProcessedFileRecord(
                source_path="/source/f1b.mkv",
                destination_path="/dest/f1b.mkv",
                sport_id="f1",
                show_id="show1",
                season_index=0,
                episode_index=1,
                processed_at=datetime.now(),
                status="linked",
            ),
            ProcessedFileRecord(
                source_path="/source/nba.mkv",
                destination_path="/dest/nba.mkv",
                sport_id="nba",
                show_id="show2",
                season_index=0,
                episode_index=0,
                processed_at=datetime.now(),
                status="error",
                error_message="Test error",
            ),
        ]
        for record in records:
            store.record_processed(record)

        stats = store.get_stats()
        assert stats["total"] == 3
        assert stats["by_status"]["linked"] == 2
        assert stats["by_status"]["error"] == 1
        assert stats["by_sport"]["f1"] == 2
        assert stats["by_sport"]["nba"] == 1

    def test_delete_by_source(
        self, store: ProcessedFileStore, sample_record: ProcessedFileRecord
    ) -> None:
        """Test deleting a record by source path."""
        store.record_processed(sample_record)
        assert store.get_by_source(sample_record.source_path) is not None

        deleted = store.delete_by_source(sample_record.source_path)
        assert deleted is True
        assert store.get_by_source(sample_record.source_path) is None

        # Deleting again should return False
        deleted = store.delete_by_source(sample_record.source_path)
        assert deleted is False

    def test_delete_by_show(self, store: ProcessedFileStore) -> None:
        """Test deleting all records for a show."""
        show_id = "formula-1-2024"

        # Add records for the show
        for i in range(3):
            record = ProcessedFileRecord(
                source_path=f"/source/f1/ep{i}.mkv",
                destination_path=f"/dest/F1/Ep{i}.mkv",
                sport_id="f1",
                show_id=show_id,
                season_index=0,
                episode_index=i,
                processed_at=datetime.now(),
            )
            store.record_processed(record)

        # Add record for different show
        other_record = ProcessedFileRecord(
            source_path="/source/other.mkv",
            destination_path="/dest/other.mkv",
            sport_id="nba",
            show_id="nba-2024",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
        )
        store.record_processed(other_record)

        deleted = store.delete_by_show(show_id)
        assert deleted == 3

        # Verify show records are gone
        assert len(store.get_by_show(show_id)) == 0

        # Verify other show is unaffected
        assert len(store.get_by_show("nba-2024")) == 1

    def test_clear(self, store: ProcessedFileStore) -> None:
        """Test clearing all records."""
        # Add some records
        for i in range(5):
            record = ProcessedFileRecord(
                source_path=f"/source/file{i}.mkv",
                destination_path=f"/dest/file{i}.mkv",
                sport_id="f1",
                show_id="show1",
                season_index=0,
                episode_index=i,
                processed_at=datetime.now(),
            )
            store.record_processed(record)

        deleted = store.clear()
        assert deleted == 5

        stats = store.get_stats()
        assert stats["total"] == 0

    def test_iter_all(self, store: ProcessedFileStore) -> None:
        """Test iterating over all records."""
        # Add records
        for i in range(3):
            record = ProcessedFileRecord(
                source_path=f"/source/file{i}.mkv",
                destination_path=f"/dest/file{i}.mkv",
                sport_id="f1",
                show_id="show1",
                season_index=0,
                episode_index=i,
                processed_at=datetime.now(),
            )
            store.record_processed(record)

        records = list(store.iter_all())
        assert len(records) == 3

    def test_persists_across_close_and_reopen(self, tmp_path: Path) -> None:
        """Test that data persists when store is closed and reopened."""
        db_path = tmp_path / "persist_test.db"

        # Create store and add record
        store1 = ProcessedFileStore(db_path)
        record = ProcessedFileRecord(
            source_path="/source/persist.mkv",
            destination_path="/dest/persist.mkv",
            sport_id="f1",
            show_id="show1",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
        )
        store1.record_processed(record)
        store1.close()

        # Reopen store and verify data
        store2 = ProcessedFileStore(db_path)
        retrieved = store2.get_by_source("/source/persist.mkv")
        assert retrieved is not None
        assert retrieved.destination_path == "/dest/persist.mkv"
        store2.close()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that the store creates parent directories if they don't exist."""
        db_path = tmp_path / "nested" / "dirs" / "test.db"
        store = ProcessedFileStore(db_path)

        # Just verify it doesn't raise
        record = ProcessedFileRecord(
            source_path="/source/test.mkv",
            destination_path="/dest/test.mkv",
            sport_id="f1",
            show_id="show1",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
        )
        store.record_processed(record)

        assert db_path.exists()
        store.close()
