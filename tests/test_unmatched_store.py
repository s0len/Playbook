"""Tests for the UnmatchedFileStore persistence layer."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from playbook.persistence import (
    FileCategory,
    MatchAttempt,
    UnmatchedFileRecord,
    UnmatchedFileStore,
    classify_file_category,
    get_file_size_safe,
)


class TestClassifyFileCategory:
    """Tests for the file category classification function."""

    def test_video_extensions(self):
        """Test that common video extensions are classified correctly."""
        assert classify_file_category("movie.mkv") == "video"
        assert classify_file_category("show.mp4") == "video"
        assert classify_file_category("episode.avi") == "video"
        assert classify_file_category("recording.ts") == "video"
        assert classify_file_category("file.m4v") == "video"

    def test_sample_detection(self):
        """Test that sample files are detected regardless of extension."""
        assert classify_file_category("movie.sample.mkv") == "sample"
        assert classify_file_category("movie-sample.mkv") == "sample"
        assert classify_file_category("Sample.mp4") == "sample"
        assert classify_file_category("file_sample.avi") == "sample"

    def test_metadata_extensions(self):
        """Test that metadata extensions are classified correctly."""
        assert classify_file_category("movie.nfo") == "metadata"
        assert classify_file_category("readme.txt") == "metadata"
        assert classify_file_category("poster.jpg") == "metadata"
        assert classify_file_category("subtitle.srt") == "metadata"

    def test_archive_extensions(self):
        """Test that archive extensions are classified correctly."""
        assert classify_file_category("file.rar") == "archive"
        assert classify_file_category("file.zip") == "archive"
        assert classify_file_category("file.7z") == "archive"

    def test_unknown_extension_is_other(self):
        """Test that unknown extensions are classified as other."""
        assert classify_file_category("file.xyz") == "other"
        assert classify_file_category("file.unknown") == "other"
        assert classify_file_category("file") == "other"


class TestGetFileSizeSafe:
    """Tests for the safe file size function."""

    def test_returns_size_for_existing_file(self, tmp_path):
        """Test that file size is returned for existing files."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        assert get_file_size_safe(test_file) == 13

    def test_returns_zero_for_nonexistent_file(self):
        """Test that 0 is returned for nonexistent files."""
        assert get_file_size_safe("/nonexistent/path/file.txt") == 0


class TestMatchAttempt:
    """Tests for the MatchAttempt dataclass."""

    def test_creation_with_defaults(self):
        """Test creating a match attempt with default values."""
        attempt = MatchAttempt(
            sport_id="f1",
            sport_name="Formula 1",
            pattern_description="F1 pattern",
            status="season-unresolved",
        )
        assert attempt.sport_id == "f1"
        assert attempt.captured_groups == {}
        assert attempt.failure_reason == ""
        assert attempt.best_score is None

    def test_creation_with_all_fields(self):
        """Test creating a match attempt with all fields."""
        attempt = MatchAttempt(
            sport_id="f1",
            sport_name="Formula 1",
            pattern_description="F1 pattern",
            status="episode-unresolved",
            captured_groups={"year": "2024", "round": "01"},
            failure_reason="Episode not found: Round 01",
            best_score=0.85,
        )
        assert attempt.captured_groups == {"year": "2024", "round": "01"}
        assert attempt.failure_reason == "Episode not found: Round 01"
        assert attempt.best_score == 0.85


class TestUnmatchedFileStore:
    """Tests for the UnmatchedFileStore class."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary store for testing."""
        db_path = tmp_path / "test.db"
        return UnmatchedFileStore(db_path)

    @pytest.fixture
    def sample_record(self):
        """Create a sample unmatched file record."""
        now = datetime.now()
        return UnmatchedFileRecord(
            source_path="/source/Formula.1.2024.Round01.Race.mkv",
            filename="Formula.1.2024.Round01.Race.mkv",
            first_seen=now,
            last_seen=now,
            file_size=5_000_000_000,
            file_category="video",
            attempted_sports=["f1", "f1tv"],
            match_attempts=[
                MatchAttempt(
                    sport_id="f1",
                    sport_name="Formula 1",
                    pattern_description="F1 Release Pattern",
                    status="episode-unresolved",
                    captured_groups={"year": "2024", "round": "01"},
                    failure_reason="Episode not found: Round01",
                )
            ],
            best_match_sport="f1",
            best_match_score=0.8,
            failure_summary="f1: Episode not found: Round01",
        )

    def test_record_and_retrieve(self, store, sample_record):
        """Test storing and retrieving an unmatched file record."""
        store.record_unmatched(sample_record)

        retrieved = store.get_by_source(sample_record.source_path)
        assert retrieved is not None
        assert retrieved.filename == sample_record.filename
        assert retrieved.file_category == "video"
        assert retrieved.best_match_sport == "f1"
        assert len(retrieved.match_attempts) == 1
        assert retrieved.match_attempts[0].sport_id == "f1"

    def test_get_by_source_returns_none_for_missing(self, store):
        """Test that get_by_source returns None for nonexistent records."""
        result = store.get_by_source("/nonexistent/path")
        assert result is None

    def test_upsert_updates_existing_record(self, store, sample_record):
        """Test that recording the same source path updates the existing record."""
        store.record_unmatched(sample_record)

        # Update with new last_seen and failure summary
        updated_record = UnmatchedFileRecord(
            source_path=sample_record.source_path,
            filename=sample_record.filename,
            first_seen=sample_record.first_seen,
            last_seen=datetime.now() + timedelta(hours=1),
            file_size=sample_record.file_size,
            file_category=sample_record.file_category,
            attempted_sports=["f1"],
            match_attempts=[],
            best_match_sport="f1",
            best_match_score=0.9,
            failure_summary="Updated summary",
        )
        store.record_unmatched(updated_record)

        retrieved = store.get_by_source(sample_record.source_path)
        assert retrieved.failure_summary == "Updated summary"
        assert retrieved.best_match_score == 0.9

    def test_get_all_with_category_filter(self, store):
        """Test filtering by file category."""
        now = datetime.now()

        # Add video file
        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/video.mkv",
                filename="video.mkv",
                first_seen=now,
                last_seen=now,
                file_size=1000,
                file_category="video",
            )
        )

        # Add sample file
        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/sample.mkv",
                filename="sample.mkv",
                first_seen=now,
                last_seen=now,
                file_size=500,
                file_category="sample",
            )
        )

        # Filter by video only
        videos = store.get_all(categories=["video"])
        assert len(videos) == 1
        assert videos[0].file_category == "video"

        # Filter by sample only
        samples = store.get_all(categories=["sample"])
        assert len(samples) == 1
        assert samples[0].file_category == "sample"

        # Get all
        all_files = store.get_all(categories=["video", "sample"])
        assert len(all_files) == 2

    def test_get_all_with_search_query(self, store):
        """Test filtering by search query."""
        now = datetime.now()

        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/Formula.1.2024.mkv",
                filename="Formula.1.2024.mkv",
                first_seen=now,
                last_seen=now,
                file_size=1000,
                file_category="video",
            )
        )

        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/MotoGP.2024.mkv",
                filename="MotoGP.2024.mkv",
                first_seen=now,
                last_seen=now,
                file_size=1000,
                file_category="video",
            )
        )

        # Search for Formula
        results = store.get_all(search_query="Formula")
        assert len(results) == 1
        assert "Formula" in results[0].filename

        # Search for 2024 (should match both)
        results = store.get_all(search_query="2024")
        assert len(results) == 2

    def test_get_all_with_sport_filter(self, store):
        """Test filtering by attempted sport."""
        now = datetime.now()

        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/f1.mkv",
                filename="f1.mkv",
                first_seen=now,
                last_seen=now,
                file_size=1000,
                file_category="video",
                attempted_sports=["f1"],
            )
        )

        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/motogp.mkv",
                filename="motogp.mkv",
                first_seen=now,
                last_seen=now,
                file_size=1000,
                file_category="video",
                attempted_sports=["motogp"],
            )
        )

        # Filter by f1
        results = store.get_all(sport_filter="f1")
        assert len(results) == 1
        assert "f1" in results[0].attempted_sports

    def test_get_count(self, store):
        """Test counting records with filters."""
        now = datetime.now()

        for i in range(10):
            store.record_unmatched(
                UnmatchedFileRecord(
                    source_path=f"/source/file{i}.mkv",
                    filename=f"file{i}.mkv",
                    first_seen=now,
                    last_seen=now,
                    file_size=1000,
                    file_category="video" if i < 7 else "sample",
                )
            )

        assert store.get_count() == 10
        assert store.get_count(categories=["video"]) == 7
        assert store.get_count(categories=["sample"]) == 3

    def test_get_category_counts(self, store):
        """Test getting counts by category."""
        now = datetime.now()

        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/video.mkv",
                filename="video.mkv",
                first_seen=now,
                last_seen=now,
                file_size=1000,
                file_category="video",
            )
        )
        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/sample.mkv",
                filename="sample.mkv",
                first_seen=now,
                last_seen=now,
                file_size=1000,
                file_category="sample",
            )
        )
        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/video2.mkv",
                filename="video2.mkv",
                first_seen=now,
                last_seen=now,
                file_size=1000,
                file_category="video",
            )
        )

        counts = store.get_category_counts()
        assert counts.get("video", 0) == 2
        assert counts.get("sample", 0) == 1

    def test_mark_manually_matched(self, store, sample_record):
        """Test marking a file as manually matched."""
        store.record_unmatched(sample_record)

        result = store.mark_manually_matched(
            sample_record.source_path,
            show_slug="formula-1-2024",
            season=1,
            episode=1,
        )
        assert result is True

        retrieved = store.get_by_source(sample_record.source_path)
        assert retrieved.manually_matched is True
        assert retrieved.matched_show_slug == "formula-1-2024"
        assert retrieved.matched_season == 1
        assert retrieved.matched_episode == 1
        assert retrieved.matched_at is not None

    def test_hide_and_unhide_file(self, store, sample_record):
        """Test hiding and unhiding files."""
        store.record_unmatched(sample_record)

        # Hide the file
        result = store.hide_file(sample_record.source_path)
        assert result is True

        # Should not appear in default listing
        visible = store.get_all()
        assert len(visible) == 0

        # Should appear when including hidden
        all_files = store.get_all(include_hidden=True)
        assert len(all_files) == 1
        assert all_files[0].hidden is True

        # Unhide the file
        result = store.unhide_file(sample_record.source_path)
        assert result is True

        visible = store.get_all()
        assert len(visible) == 1
        assert visible[0].hidden is False

    def test_delete_by_source(self, store, sample_record):
        """Test deleting a record by source path."""
        store.record_unmatched(sample_record)
        assert store.get_by_source(sample_record.source_path) is not None

        result = store.delete_by_source(sample_record.source_path)
        assert result is True
        assert store.get_by_source(sample_record.source_path) is None

    def test_delete_stale(self, store):
        """Test deleting stale records."""
        old_time = datetime.now() - timedelta(days=30)
        recent_time = datetime.now()

        # Add old file
        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/old.mkv",
                filename="old.mkv",
                first_seen=old_time,
                last_seen=old_time,
                file_size=1000,
                file_category="video",
            )
        )

        # Add recent file
        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/recent.mkv",
                filename="recent.mkv",
                first_seen=recent_time,
                last_seen=recent_time,
                file_size=1000,
                file_category="video",
            )
        )

        # Delete files older than 7 days
        cutoff = datetime.now() - timedelta(days=7)
        deleted = store.delete_stale(cutoff)
        assert deleted == 1

        remaining = store.get_all()
        assert len(remaining) == 1
        assert remaining[0].filename == "recent.mkv"

    def test_clear(self, store, sample_record):
        """Test clearing all records."""
        store.record_unmatched(sample_record)
        assert store.get_count() == 1

        deleted = store.clear()
        assert deleted == 1
        assert store.get_count() == 0

    def test_get_stats(self, store):
        """Test getting statistics."""
        now = datetime.now()

        # Add some records
        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/video.mkv",
                filename="video.mkv",
                first_seen=now,
                last_seen=now,
                file_size=1000,
                file_category="video",
            )
        )
        store.record_unmatched(
            UnmatchedFileRecord(
                source_path="/source/sample.mkv",
                filename="sample.mkv",
                first_seen=now,
                last_seen=now,
                file_size=1000,
                file_category="sample",
            )
        )

        # Hide one
        store.hide_file("/source/sample.mkv")

        # Manually match one
        store.mark_manually_matched("/source/video.mkv", "show", 1, 1)

        stats = store.get_stats()
        assert stats["total"] == 2
        assert stats["hidden"] == 1
        assert stats["manually_matched"] == 1
        assert stats["by_category"]["video"] == 1
        assert stats["by_category"]["sample"] == 1

    def test_iter_all(self, store):
        """Test iterating over all records."""
        now = datetime.now()

        for i in range(5):
            store.record_unmatched(
                UnmatchedFileRecord(
                    source_path=f"/source/file{i}.mkv",
                    filename=f"file{i}.mkv",
                    first_seen=now,
                    last_seen=now,
                    file_size=1000,
                    file_category="video",
                )
            )

        records = list(store.iter_all())
        assert len(records) == 5

    def test_pagination(self, store):
        """Test pagination with limit and offset."""
        now = datetime.now()

        for i in range(25):
            store.record_unmatched(
                UnmatchedFileRecord(
                    source_path=f"/source/file{i:02d}.mkv",
                    filename=f"file{i:02d}.mkv",
                    first_seen=now + timedelta(seconds=i),  # Different times for ordering
                    last_seen=now + timedelta(seconds=i),
                    file_size=1000,
                    file_category="video",
                )
            )

        # First page
        page1 = store.get_all(limit=10, offset=0)
        assert len(page1) == 10

        # Second page
        page2 = store.get_all(limit=10, offset=10)
        assert len(page2) == 10

        # Third page (partial)
        page3 = store.get_all(limit=10, offset=20)
        assert len(page3) == 5

        # Pages should not overlap
        page1_paths = {r.source_path for r in page1}
        page2_paths = {r.source_path for r in page2}
        assert page1_paths.isdisjoint(page2_paths)

    def test_persists_across_close_and_reopen(self, tmp_path, sample_record):
        """Test that data persists after closing and reopening the store."""
        db_path = tmp_path / "persist_test.db"

        # Create store, add record, close
        store1 = UnmatchedFileStore(db_path)
        store1.record_unmatched(sample_record)
        store1.close()

        # Reopen and verify
        store2 = UnmatchedFileStore(db_path)
        retrieved = store2.get_by_source(sample_record.source_path)
        assert retrieved is not None
        assert retrieved.filename == sample_record.filename
        store2.close()
