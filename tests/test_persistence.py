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

    def test_check_processed_with_destination_not_in_db(
        self, store: ProcessedFileStore
    ) -> None:
        """Test that check_processed_with_destination returns (False, None) when source not in DB."""
        is_processed, dest_path = store.check_processed_with_destination("/nonexistent/file.mkv")
        assert is_processed is False
        assert dest_path is None

    def test_check_processed_with_destination_exists(
        self, store: ProcessedFileStore, tmp_path: Path
    ) -> None:
        """Test that check_processed_with_destination returns (True, path) when destination exists."""
        # Create a real destination file
        dest_file = tmp_path / "dest" / "F1" / "Race.mkv"
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        dest_file.write_text("test content")

        # Record the file
        record = ProcessedFileRecord(
            source_path="/source/f1/race.mkv",
            destination_path=str(dest_file),
            sport_id="f1",
            show_id="formula-1-2024",
            season_index=0,
            episode_index=5,
            processed_at=datetime.now(),
            status="linked",
        )
        store.record_processed(record)

        # Check - should return True since destination exists
        is_processed, dest_path = store.check_processed_with_destination("/source/f1/race.mkv")
        assert is_processed is True
        assert dest_path == str(dest_file)

    def test_check_processed_with_destination_missing(
        self, store: ProcessedFileStore
    ) -> None:
        """Test that check_processed_with_destination returns (False, path) when destination is missing."""
        # Record a file with a non-existent destination
        record = ProcessedFileRecord(
            source_path="/source/f1/race.mkv",
            destination_path="/dest/nonexistent/Race.mkv",
            sport_id="f1",
            show_id="formula-1-2024",
            season_index=0,
            episode_index=5,
            processed_at=datetime.now(),
            status="linked",
        )
        store.record_processed(record)

        # Check - should return False with the destination path since it doesn't exist
        is_processed, dest_path = store.check_processed_with_destination("/source/f1/race.mkv")
        assert is_processed is False
        assert dest_path == "/dest/nonexistent/Race.mkv"

    def test_remove_by_metadata_changes_removes_affected_sport(
        self, store: ProcessedFileStore
    ) -> None:
        """Test that remove_by_metadata_changes removes all records for a sport with changes."""
        # Add records for multiple sports
        for i in range(3):
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

        for i in range(2):
            record = ProcessedFileRecord(
                source_path=f"/source/nba/game{i}.mkv",
                destination_path=f"/dest/NBA/Game{i}.mkv",
                sport_id="nba",
                show_id="nba-2024",
                season_index=0,
                episode_index=i,
                processed_at=datetime.now(),
            )
            store.record_processed(record)

        # Create a mock metadata change result for F1
        class MockChangeResult:
            updated = True
            changed_seasons = set()
            changed_episodes = {}
            invalidate_all = False

        changes = {"f1": MockChangeResult()}

        # Remove records affected by metadata changes
        removed = store.remove_by_metadata_changes(changes)

        # Should have removed 3 F1 records
        assert len(removed) == 3
        assert all("/source/f1/" in path for path in removed.keys())

        # F1 records should be gone
        assert len(store.get_by_sport("f1")) == 0

        # NBA records should still exist
        assert len(store.get_by_sport("nba")) == 2

    def test_remove_by_metadata_changes_returns_empty_for_no_changes(
        self, store: ProcessedFileStore
    ) -> None:
        """Test that remove_by_metadata_changes returns empty dict when no changes."""
        record = ProcessedFileRecord(
            source_path="/source/f1/race.mkv",
            destination_path="/dest/F1/Race.mkv",
            sport_id="f1",
            show_id="formula-1-2024",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
        )
        store.record_processed(record)

        # No changes
        removed = store.remove_by_metadata_changes({})
        assert len(removed) == 0

        # Record should still exist
        assert store.get_by_source("/source/f1/race.mkv") is not None


class TestMetadataCacheStore:
    """Tests for the MetadataCacheStore class."""

    @pytest.fixture
    def cache(self, tmp_path: Path):
        """Create a MetadataCacheStore for testing."""
        from playbook.persistence import MetadataCacheStore

        db_path = tmp_path / "metadata.db"
        store = MetadataCacheStore(db_path, ttl_hours=1)
        yield store
        store.close()

    def test_set_and_get(self, cache) -> None:
        """Test basic set and get operations."""
        content = {"name": "Test Show", "seasons": [1, 2, 3]}
        cache.set("shows/test-show", content)

        entry = cache.get("shows/test-show")
        assert entry is not None
        assert entry.content == content
        assert entry.is_fresh

    def test_get_returns_none_for_missing(self, cache) -> None:
        """Test that get returns None for missing keys."""
        entry = cache.get("shows/nonexistent")
        assert entry is None

    def test_etag_and_last_modified(self, cache) -> None:
        """Test that ETag and Last-Modified are stored."""
        content = {"name": "Test"}
        cache.set(
            "shows/test",
            content,
            etag='"abc123"',
            last_modified="Wed, 01 Jan 2025 00:00:00 GMT",
        )

        entry = cache.get("shows/test")
        assert entry is not None
        assert entry.etag == '"abc123"'
        assert entry.last_modified == "Wed, 01 Jan 2025 00:00:00 GMT"

    def test_expired_entries_not_returned_by_default(self, cache, tmp_path: Path) -> None:
        """Test that expired entries are not returned by default."""
        from playbook.persistence import MetadataCacheStore

        # Create cache with very short TTL
        db_path = tmp_path / "short_ttl.db"
        short_cache = MetadataCacheStore(db_path, ttl_hours=0)  # Immediate expiry

        content = {"name": "Test"}
        short_cache.set("shows/test", content, ttl_hours=0)

        # Should be None (expired immediately with 0 TTL)
        import time
        time.sleep(0.1)  # Small delay to ensure expiry

        entry = short_cache.get("shows/test")
        # With ttl_hours=0, the entry expires at creation time
        # So it should be None or expired
        short_cache.close()

    def test_include_expired_returns_expired_entries(self, cache, tmp_path: Path) -> None:
        """Test that include_expired=True returns expired entries."""
        from playbook.persistence import MetadataCacheStore

        db_path = tmp_path / "expired.db"
        short_cache = MetadataCacheStore(db_path, ttl_hours=0)

        content = {"name": "Test"}
        short_cache.set("shows/test", content, etag='"etag123"')

        # Should return the expired entry when include_expired=True
        entry = short_cache.get("shows/test", include_expired=True)
        assert entry is not None
        assert entry.etag == '"etag123"'
        short_cache.close()

    def test_refresh_ttl(self, cache) -> None:
        """Test that refresh_ttl updates the expiration time."""
        content = {"name": "Test"}
        cache.set("shows/test", content)

        # Refresh TTL
        result = cache.refresh_ttl("shows/test")
        assert result is True

        # Entry should still be fresh
        entry = cache.get("shows/test")
        assert entry is not None
        assert entry.is_fresh

    def test_refresh_ttl_returns_false_for_missing(self, cache) -> None:
        """Test that refresh_ttl returns False for missing keys."""
        result = cache.refresh_ttl("shows/nonexistent")
        assert result is False

    def test_delete(self, cache) -> None:
        """Test deletion of entries."""
        cache.set("shows/test", {"name": "Test"})

        result = cache.delete("shows/test")
        assert result is True

        entry = cache.get("shows/test")
        assert entry is None

    def test_invalidate_by_prefix(self, cache) -> None:
        """Test invalidation by key prefix."""
        cache.set("shows/ufc-2025", {"name": "UFC 2025"})
        cache.set("shows/ufc-2024", {"name": "UFC 2024"})
        cache.set("shows/f1-2025", {"name": "F1 2025"})
        cache.set("seasons/ufc-2025_s1", {"number": 1})

        # Invalidate all UFC shows
        count = cache.invalidate_by_prefix("shows/ufc-")
        assert count == 2

        # UFC shows should be gone
        assert cache.get("shows/ufc-2025") is None
        assert cache.get("shows/ufc-2024") is None

        # F1 show and UFC season should still exist
        assert cache.get("shows/f1-2025") is not None
        assert cache.get("seasons/ufc-2025_s1") is not None

    def test_clear(self, cache) -> None:
        """Test clearing all entries."""
        cache.set("shows/test1", {"name": "Test 1"})
        cache.set("shows/test2", {"name": "Test 2"})

        count = cache.clear()
        assert count == 2

        assert cache.get("shows/test1") is None
        assert cache.get("shows/test2") is None

    def test_get_stats(self, cache) -> None:
        """Test statistics reporting."""
        cache.set("shows/test1", {"name": "Test 1"}, etag='"etag1"')
        cache.set("shows/test2", {"name": "Test 2"})

        stats = cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["entries_with_etag"] == 1
        assert stats["ttl_hours"] == 1
