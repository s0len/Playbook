from __future__ import annotations

from pathlib import Path

from playbook.cache import CachedFileRecord, ProcessedFileCache
from playbook.metadata import MetadataChangeResult


def test_remove_by_metadata_changes_drops_only_matching_entries(tmp_path) -> None:
    cache = ProcessedFileCache(tmp_path)
    cache._records = {
        "/videos/demo1.mkv": CachedFileRecord(
            mtime_ns=1,
            size=100,
            destination="/library/demo1.mkv",
            sport_id="demo",
            season_key="01",
            episode_key="episode1",
        ),
        "/videos/demo2.mkv": CachedFileRecord(
            mtime_ns=2,
            size=200,
            destination="/library/demo2.mkv",
            sport_id="demo",
            season_key="02",
            episode_key="episode2",
        ),
        "/videos/other.mkv": CachedFileRecord(
            mtime_ns=3,
            size=300,
            destination="/library/other.mkv",
            sport_id="other",
            season_key="99",
            episode_key="episodeA",
        ),
    }

    change = MetadataChangeResult(
        updated=True,
        changed_seasons={"01"},
        changed_episodes={},
        invalidate_all=False,
    )

    removed = cache.remove_by_metadata_changes({"demo": change})

    assert "/videos/demo1.mkv" in removed
    assert "/videos/demo2.mkv" not in removed
    assert "/videos/other.mkv" not in removed
    assert "/videos/demo2.mkv" in cache._records
    assert "/videos/other.mkv" in cache._records


def test_remove_by_metadata_changes_respects_episode_scope(tmp_path) -> None:
    cache = ProcessedFileCache(tmp_path)
    cache._records = {
        "/videos/demo1.mkv": CachedFileRecord(
            mtime_ns=1,
            size=100,
            destination="/library/demo1.mkv",
            sport_id="demo",
            season_key="01",
            episode_key="episode1",
        ),
        "/videos/demo2.mkv": CachedFileRecord(
            mtime_ns=2,
            size=200,
            destination="/library/demo2.mkv",
            sport_id="demo",
            season_key="01",
            episode_key="episode2",
        ),
    }

    change = MetadataChangeResult(
        updated=True,
        changed_seasons=set(),
        changed_episodes={"01": {"episode1"}},
        invalidate_all=False,
    )

    removed = cache.remove_by_metadata_changes({"demo": change})

    assert "/videos/demo1.mkv" in removed
    assert "/videos/demo2.mkv" not in removed


def test_remove_by_metadata_changes_drops_legacy_entries_without_ownership(tmp_path) -> None:
    cache = ProcessedFileCache(tmp_path)
    cache._records = {
        "/videos/legacy.mkv": CachedFileRecord(
            mtime_ns=1,
            size=100,
            destination="/library/legacy.mkv",
        )
    }

    change = MetadataChangeResult(
        updated=True,
        changed_seasons={"01"},
        changed_episodes={},
        invalidate_all=False,
    )

    removed = cache.remove_by_metadata_changes({"demo": change})

    assert "/videos/legacy.mkv" in removed
    assert "/videos/legacy.mkv" not in cache._records


def test_is_processed_removes_entry_for_missing_source_file(tmp_path) -> None:
    """Test that is_processed() lazily removes cache entries when source file is missing."""
    cache = ProcessedFileCache(tmp_path)

    # Create a path to a non-existent file
    missing_file = tmp_path / "missing_video.mkv"

    # Add a cache record for the missing file
    cache._records[str(missing_file)] = CachedFileRecord(
        mtime_ns=123456789,
        size=1000,
        destination="/library/output.mkv",
        sport_id="demo",
        season_key="01",
        episode_key="episode1",
    )

    # Ensure the file doesn't exist
    assert not missing_file.exists()

    # Verify the record is initially in the cache
    assert str(missing_file) in cache._records

    # Reset dirty flag to verify it gets set
    cache._dirty = False

    # Call is_processed() on the missing file
    result = cache.is_processed(missing_file)

    # Verify the method returns False
    assert result is False

    # Verify the cache entry was removed
    assert str(missing_file) not in cache._records

    # Verify the dirty flag was set to True
    assert cache._dirty is True


def test_is_processed_with_existing_file(tmp_path) -> None:
    """Test that is_processed() correctly handles existing source files."""
    cache = ProcessedFileCache(tmp_path)

    # Create a real test file
    test_file = tmp_path / "test_video.mkv"
    test_file.write_bytes(b"test content")

    # Get the file's actual stats
    stat = test_file.stat()

    # Test case 1: File matches cache - should return True
    cache._records[str(test_file)] = CachedFileRecord(
        mtime_ns=stat.st_mtime_ns,
        size=stat.st_size,
        destination="/library/output.mkv",
        sport_id="demo",
        season_key="01",
        episode_key="episode1",
    )

    result = cache.is_processed(test_file)
    assert result is True
    # Record should still be in cache
    assert str(test_file) in cache._records

    # Test case 2: File has different mtime - should return False but NOT remove entry
    cache._records[str(test_file)] = CachedFileRecord(
        mtime_ns=stat.st_mtime_ns + 1000000,  # Different mtime
        size=stat.st_size,
        destination="/library/output.mkv",
        sport_id="demo",
        season_key="01",
        episode_key="episode1",
    )

    result = cache.is_processed(test_file)
    assert result is False
    # Record should still be in cache (not removed for modified files)
    assert str(test_file) in cache._records

    # Test case 3: File has different size - should return False but NOT remove entry
    cache._records[str(test_file)] = CachedFileRecord(
        mtime_ns=stat.st_mtime_ns,
        size=stat.st_size + 100,  # Different size
        destination="/library/output.mkv",
        sport_id="demo",
        season_key="01",
        episode_key="episode1",
    )

    result = cache.is_processed(test_file)
    assert result is False
    # Record should still be in cache (not removed for modified files)
    assert str(test_file) in cache._records

