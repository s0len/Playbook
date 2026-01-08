from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from playbook.config import SportConfig
from playbook.file_discovery import (
    SAMPLE_FILENAME_PATTERN,
    gather_source_files,
    matches_globs,
    should_suppress_sample_ignored,
    skip_reason_for_source_file,
)
from playbook.models import ProcessingStats


class TestSampleFilenamePattern:
    """Test the SAMPLE_FILENAME_PATTERN regex."""

    def test_matches_sample_lowercase(self) -> None:
        """Test that the pattern matches 'sample' (lowercase)."""
        assert SAMPLE_FILENAME_PATTERN.search("sample") is not None

    def test_matches_sample_in_filename(self) -> None:
        """Test that the pattern matches 'sample' within a filename."""
        assert SAMPLE_FILENAME_PATTERN.search("movie.sample.mkv") is not None
        assert SAMPLE_FILENAME_PATTERN.search("sample.video.mp4") is not None
        assert SAMPLE_FILENAME_PATTERN.search("video-sample.avi") is not None

    def test_does_not_match_substring_sample(self) -> None:
        """Test that the pattern does not match 'sample' as part of another word."""
        assert SAMPLE_FILENAME_PATTERN.search("samplefile") is None
        assert SAMPLE_FILENAME_PATTERN.search("filesample") is None
        assert SAMPLE_FILENAME_PATTERN.search("samplevideo") is None
        assert SAMPLE_FILENAME_PATTERN.search("resample") is None

    def test_matches_sample_with_boundaries(self) -> None:
        """Test that the pattern matches 'sample' with word boundaries."""
        assert SAMPLE_FILENAME_PATTERN.search("_sample_") is not None
        assert SAMPLE_FILENAME_PATTERN.search("-sample-") is not None
        assert SAMPLE_FILENAME_PATTERN.search(".sample.") is not None
        assert SAMPLE_FILENAME_PATTERN.search(" sample ") is not None


class TestSkipReasonForSourceFile:
    """Test skip_reason_for_source_file function."""

    def test_returns_none_for_normal_file(self) -> None:
        """Test that normal files return None (should not be skipped)."""
        path = Path("/foo/bar/normal_file.mkv")
        assert skip_reason_for_source_file(path) is None

    def test_returns_none_for_file_starting_with_dot(self) -> None:
        """Test that files starting with a single dot are not skipped."""
        path = Path("/foo/bar/.hidden")
        assert skip_reason_for_source_file(path) is None

    def test_detects_macos_resource_fork(self) -> None:
        """Test that macOS resource forks (._ prefix) are detected."""
        path = Path("/foo/bar/._resource_fork")
        reason = skip_reason_for_source_file(path)
        assert reason is not None
        assert "resource fork" in reason.lower()
        assert "._" in reason

    def test_detects_resource_fork_with_extension(self) -> None:
        """Test that resource forks with file extensions are detected."""
        path = Path("/foo/bar/._video.mkv")
        reason = skip_reason_for_source_file(path)
        assert reason is not None
        assert "resource fork" in reason.lower()

    def test_does_not_detect_underscore_only(self) -> None:
        """Test that a file named exactly '._' is not detected (must have at least one more char)."""
        path = Path("/foo/bar/._")
        # This should return None because len(name) > 2 check requires at least 3 chars
        assert skip_reason_for_source_file(path) is None

    def test_detects_resource_fork_in_subdirectory(self) -> None:
        """Test that resource forks in any subdirectory are detected."""
        path = Path("/foo/bar/baz/._file.mp4")
        reason = skip_reason_for_source_file(path)
        assert reason is not None


class TestMatchesGlobs:
    """Test matches_globs function."""

    def test_returns_true_when_no_globs_defined(self) -> None:
        """Test that files match when sport has no source_globs defined."""
        sport = Mock(spec=SportConfig)
        sport.source_globs = []
        path = Path("/foo/bar/any_file.mkv")
        assert matches_globs(path, sport) is True

    def test_returns_true_when_globs_is_none(self) -> None:
        """Test that files match when sport.source_globs is None."""
        sport = Mock(spec=SportConfig)
        sport.source_globs = None
        path = Path("/foo/bar/any_file.mkv")
        assert matches_globs(path, sport) is True

    def test_matches_simple_wildcard_pattern(self) -> None:
        """Test matching against simple wildcard patterns."""
        sport = Mock(spec=SportConfig)
        sport.source_globs = ["*.mkv"]

        assert matches_globs(Path("/foo/bar/video.mkv"), sport) is True
        assert matches_globs(Path("/foo/bar/video.mp4"), sport) is False

    def test_matches_multiple_patterns(self) -> None:
        """Test matching against multiple glob patterns."""
        sport = Mock(spec=SportConfig)
        sport.source_globs = ["*.mkv", "*.mp4", "*.avi"]

        assert matches_globs(Path("/foo/bar/video.mkv"), sport) is True
        assert matches_globs(Path("/foo/bar/video.mp4"), sport) is True
        assert matches_globs(Path("/foo/bar/video.avi"), sport) is True
        assert matches_globs(Path("/foo/bar/video.ts"), sport) is False

    def test_matches_complex_pattern(self) -> None:
        """Test matching against complex glob patterns."""
        sport = Mock(spec=SportConfig)
        sport.source_globs = ["NBA*.mkv", "*-NFL-*.mp4"]

        assert matches_globs(Path("/foo/bar/NBA_2024_Finals.mkv"), sport) is True
        assert matches_globs(Path("/foo/bar/Game-NFL-Week1.mp4"), sport) is True
        assert matches_globs(Path("/foo/bar/MLB_Game.mkv"), sport) is False

    def test_only_checks_filename_not_full_path(self) -> None:
        """Test that glob matching only considers the filename, not the full path."""
        sport = Mock(spec=SportConfig)
        sport.source_globs = ["*.mkv"]

        # Even though path contains 'mkv' in directory name, only filename matters
        assert matches_globs(Path("/foo/mkv/video.mp4"), sport) is False
        assert matches_globs(Path("/foo/mkv/video.mkv"), sport) is True

    def test_case_sensitive_matching(self) -> None:
        """Test that glob matching is case-sensitive."""
        sport = Mock(spec=SportConfig)
        sport.source_globs = ["*.mkv"]

        # fnmatch is case-sensitive on Unix-like systems
        assert matches_globs(Path("/foo/bar/video.mkv"), sport) is True
        # This behavior depends on the OS, but we test current behavior
        assert matches_globs(Path("/foo/bar/video.MKV"), sport) is False


class TestShouldSuppressSampleIgnored:
    """Test should_suppress_sample_ignored function."""

    def test_returns_false_for_normal_file(self) -> None:
        """Test that normal files are not detected as samples."""
        assert should_suppress_sample_ignored(Path("/foo/bar/video.mkv")) is False
        assert should_suppress_sample_ignored(Path("/foo/bar/episode01.mp4")) is False

    def test_detects_sample_lowercase(self) -> None:
        """Test that 'sample' (lowercase) is detected."""
        assert should_suppress_sample_ignored(Path("/foo/bar/sample.mkv")) is True
        assert should_suppress_sample_ignored(Path("/foo/bar/video.sample.mp4")) is True
        assert should_suppress_sample_ignored(Path("/foo/bar/sample-video.avi")) is True

    def test_detects_sample_uppercase(self) -> None:
        """Test that 'SAMPLE' (uppercase) is detected (case-insensitive)."""
        assert should_suppress_sample_ignored(Path("/foo/bar/SAMPLE.mkv")) is True
        assert should_suppress_sample_ignored(Path("/foo/bar/VIDEO.SAMPLE.mp4")) is True

    def test_detects_sample_mixed_case(self) -> None:
        """Test that 'Sample' (mixed case) is detected."""
        assert should_suppress_sample_ignored(Path("/foo/bar/Sample.mkv")) is True
        assert should_suppress_sample_ignored(Path("/foo/bar/Video.SaMpLe.mp4")) is True

    def test_does_not_detect_sample_substring(self) -> None:
        """Test that 'sample' as part of another word is not detected."""
        assert should_suppress_sample_ignored(Path("/foo/bar/samplefile.mkv")) is False
        assert should_suppress_sample_ignored(Path("/foo/bar/resample.mp4")) is False
        assert should_suppress_sample_ignored(Path("/foo/bar/samplevideo.avi")) is False

    def test_detects_sample_with_separators(self) -> None:
        """Test that 'sample' with word separators is detected."""
        assert should_suppress_sample_ignored(Path("/foo/bar/video_sample_720p.mkv")) is True
        assert should_suppress_sample_ignored(Path("/foo/bar/video-sample-1080p.mp4")) is True
        assert should_suppress_sample_ignored(Path("/foo/bar/video.sample.ts")) is True

    def test_only_checks_filename_not_path(self) -> None:
        """Test that only the filename is checked, not the directory path."""
        # 'sample' in directory path should not trigger detection
        assert should_suppress_sample_ignored(Path("/sample/video.mkv")) is False
        assert should_suppress_sample_ignored(Path("/foo/sample/video.mp4")) is False
        # But 'sample' in filename should trigger detection
        assert should_suppress_sample_ignored(Path("/foo/bar/sample.mkv")) is True


class TestGatherSourceFiles:
    """Test gather_source_files function."""

    def test_returns_empty_list_when_source_dir_missing(self, tmp_path) -> None:
        """Test that an empty list is returned when source directory doesn't exist."""
        non_existent_dir = tmp_path / "does_not_exist"
        result = list(gather_source_files(non_existent_dir))
        assert result == []

    def test_logs_warning_when_source_dir_missing(self, tmp_path, caplog) -> None:
        """Test that a warning is logged when source directory doesn't exist."""
        import logging

        non_existent_dir = tmp_path / "does_not_exist"
        with caplog.at_level(logging.WARNING):
            list(gather_source_files(non_existent_dir))

        assert "Source Directory Missing" in caplog.text or "missing" in caplog.text.lower()

    def test_registers_warning_in_stats_when_source_dir_missing(self, tmp_path) -> None:
        """Test that a warning is registered in stats when source directory doesn't exist."""
        non_existent_dir = tmp_path / "does_not_exist"
        stats = ProcessingStats()

        list(gather_source_files(non_existent_dir, stats))

        assert len(stats.warnings) == 1
        assert "missing" in stats.warnings[0].lower()

    def test_yields_files_from_root_directory(self, tmp_path) -> None:
        """Test that files in the root source directory are yielded."""
        # Create test files
        file1 = tmp_path / "video1.mkv"
        file2 = tmp_path / "video2.mp4"
        file1.write_text("content")
        file2.write_text("content")

        result = list(gather_source_files(tmp_path))

        assert len(result) == 2
        assert file1 in result
        assert file2 in result

    def test_yields_files_from_subdirectories(self, tmp_path) -> None:
        """Test that files in subdirectories are yielded (recursive)."""
        # Create nested directory structure
        subdir1 = tmp_path / "subdir1"
        subdir2 = tmp_path / "subdir1" / "subdir2"
        subdir1.mkdir()
        subdir2.mkdir()

        file1 = tmp_path / "root.mkv"
        file2 = subdir1 / "sub1.mp4"
        file3 = subdir2 / "sub2.avi"
        file1.write_text("content")
        file2.write_text("content")
        file3.write_text("content")

        result = list(gather_source_files(tmp_path))

        assert len(result) == 3
        assert file1 in result
        assert file2 in result
        assert file3 in result

    def test_filters_out_directories(self, tmp_path) -> None:
        """Test that directories are not yielded, only files."""
        # Create directory and file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        file1 = tmp_path / "video.mkv"
        file1.write_text("content")

        result = list(gather_source_files(tmp_path))

        assert len(result) == 1
        assert file1 in result
        assert subdir not in result

    def test_filters_out_symlinks(self, tmp_path) -> None:
        """Test that symlinks are filtered out and logged."""
        # Create a regular file and a symlink to it
        regular_file = tmp_path / "regular.mkv"
        regular_file.write_text("content")

        symlink_file = tmp_path / "symlink.mkv"
        symlink_file.symlink_to(regular_file)

        result = list(gather_source_files(tmp_path))

        # Only the regular file should be yielded
        assert len(result) == 1
        assert regular_file in result
        assert symlink_file not in result

    def test_filters_out_macos_resource_forks(self, tmp_path) -> None:
        """Test that macOS resource forks are filtered out."""
        # Create regular file and resource fork
        regular_file = tmp_path / "video.mkv"
        resource_fork = tmp_path / "._video.mkv"
        regular_file.write_text("content")
        resource_fork.write_text("content")

        result = list(gather_source_files(tmp_path))

        # Only the regular file should be yielded
        assert len(result) == 1
        assert regular_file in result
        assert resource_fork not in result

    def test_logs_debug_for_skipped_symlinks(self, tmp_path, caplog) -> None:
        """Test that debug messages are logged for skipped symlinks."""
        import logging

        regular_file = tmp_path / "regular.mkv"
        regular_file.write_text("content")

        symlink_file = tmp_path / "symlink.mkv"
        symlink_file.symlink_to(regular_file)

        with caplog.at_level(logging.DEBUG):
            list(gather_source_files(tmp_path))

        assert "symlink" in caplog.text.lower()

    def test_logs_debug_for_skipped_resource_forks(self, tmp_path, caplog) -> None:
        """Test that debug messages are logged for skipped resource forks."""
        import logging

        resource_fork = tmp_path / "._video.mkv"
        resource_fork.write_text("content")

        with caplog.at_level(logging.DEBUG):
            list(gather_source_files(tmp_path))

        assert "resource fork" in caplog.text.lower() or "._" in caplog.text

    def test_yields_files_in_consistent_order(self, tmp_path) -> None:
        """Test that files are yielded in a consistent order (by rglob)."""
        # Create multiple files
        file1 = tmp_path / "a.mkv"
        file2 = tmp_path / "b.mp4"
        file3 = tmp_path / "c.avi"
        file1.write_text("content")
        file2.write_text("content")
        file3.write_text("content")

        result1 = list(gather_source_files(tmp_path))
        result2 = list(gather_source_files(tmp_path))

        # Results should be consistent across multiple calls
        # Note: rglob order may not be alphabetical, but should be consistent
        assert result1 == result2

    def test_handles_large_directory_tree(self, tmp_path) -> None:
        """Test that large directory trees are handled correctly."""
        # Create a moderately large directory tree
        files = []
        for i in range(10):
            subdir = tmp_path / f"subdir{i}"
            subdir.mkdir()
            for j in range(5):
                file = subdir / f"video{j}.mkv"
                file.write_text("content")
                files.append(file)

        result = list(gather_source_files(tmp_path))

        assert len(result) == 50
        for expected_file in files:
            assert expected_file in result

    def test_works_without_stats_parameter(self, tmp_path) -> None:
        """Test that the function works correctly when stats parameter is None."""
        file1 = tmp_path / "video.mkv"
        file1.write_text("content")

        # Should not raise an error when stats is None
        result = list(gather_source_files(tmp_path, stats=None))

        assert len(result) == 1
        assert file1 in result

    def test_handles_empty_directory(self, tmp_path) -> None:
        """Test that an empty directory returns an empty list."""
        result = list(gather_source_files(tmp_path))
        assert result == []

    def test_handles_directory_with_only_subdirectories(self, tmp_path) -> None:
        """Test that a directory with only subdirectories (no files) returns empty list."""
        subdir1 = tmp_path / "subdir1"
        subdir2 = tmp_path / "subdir2"
        subdir1.mkdir()
        subdir2.mkdir()

        result = list(gather_source_files(tmp_path))
        assert result == []

    def test_yields_generator_not_list(self, tmp_path) -> None:
        """Test that gather_source_files returns an iterable (generator or list)."""
        file1 = tmp_path / "video.mkv"
        file1.write_text("content")

        # Call without list() to check the return type
        result = gather_source_files(tmp_path)

        # Should be iterable
        from collections.abc import Iterable
        assert isinstance(result, Iterable)

    def test_filters_multiple_types_in_same_directory(self, tmp_path) -> None:
        """Test filtering when directory contains mixed file types to filter."""
        # Create regular files, symlinks, and resource forks
        regular1 = tmp_path / "video1.mkv"
        regular2 = tmp_path / "video2.mp4"
        resource_fork = tmp_path / "._video1.mkv"
        regular1.write_text("content")
        regular2.write_text("content")
        resource_fork.write_text("content")

        symlink = tmp_path / "link.mkv"
        symlink.symlink_to(regular1)

        result = list(gather_source_files(tmp_path))

        # Only regular files should be yielded
        assert len(result) == 2
        assert regular1 in result
        assert regular2 in result
        assert resource_fork not in result
        assert symlink not in result
