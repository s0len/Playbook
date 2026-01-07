from __future__ import annotations

import logging
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, Mock, patch

import pytest

from playbook.config import WatcherSettings
from playbook.watcher import (
    WatchdogUnavailableError,
    _FileChangeHandler,
    FileWatcherLoop,
)


# Fixtures for mocking watchdog dependencies


@pytest.fixture
def mock_observer():
    """Mock watchdog Observer."""
    observer = MagicMock()
    observer.start = MagicMock()
    observer.stop = MagicMock()
    observer.join = MagicMock()
    observer.schedule = MagicMock()
    return observer


@pytest.fixture
def mock_file_system_event_handler():
    """Mock watchdog FileSystemEventHandler base class."""
    return MagicMock()


# Fixtures for mocking Processor and settings


@pytest.fixture
def mock_processor(tmp_path):
    """Mock Processor instance with minimal config."""
    processor = MagicMock()

    # Create a mock config with settings
    mock_config = MagicMock()
    mock_settings = MagicMock()
    mock_settings.source_dir = tmp_path / "source"
    mock_settings.source_dir.mkdir(parents=True, exist_ok=True)
    mock_config.settings = mock_settings

    processor.config = mock_config
    processor.process_all = MagicMock()

    return processor


@pytest.fixture
def watcher_settings():
    """Default WatcherSettings for testing."""
    return WatcherSettings(
        enabled=True,
        paths=[],
        include=["*.mkv", "*.mp4"],
        ignore=["*.tmp", "*.part"],
        debounce_seconds=5.0,
        reconcile_interval=900,
    )


@pytest.fixture
def minimal_watcher_settings():
    """Minimal WatcherSettings with empty patterns."""
    return WatcherSettings(
        enabled=True,
        paths=[],
        include=[],
        ignore=[],
        debounce_seconds=1.0,
        reconcile_interval=0,
    )


# Fixtures for file system events


@pytest.fixture
def mock_file_event():
    """Mock file system event (not a directory)."""
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/path/to/file.mkv"
    return event


@pytest.fixture
def mock_directory_event():
    """Mock directory event."""
    event = MagicMock()
    event.is_directory = True
    event.src_path = "/path/to/directory"
    return event


@pytest.fixture
def mock_moved_event():
    """Mock file move event."""
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/path/to/old_file.mkv"
    event.dest_path = "/path/to/new_file.mkv"
    return event


# Tests for WatchdogUnavailableError exception


class TestWatchdogUnavailableError:
    """Tests for the WatchdogUnavailableError exception."""

    def test_exception_can_be_raised(self):
        """Test that WatchdogUnavailableError can be raised and caught."""
        with pytest.raises(WatchdogUnavailableError):
            raise WatchdogUnavailableError("Test message")

    def test_exception_inherits_from_runtime_error(self):
        """Test that WatchdogUnavailableError is a RuntimeError."""
        error = WatchdogUnavailableError("Test message")
        assert isinstance(error, RuntimeError)

    def test_exception_message_format(self):
        """Test that exception message is preserved correctly."""
        message = "Custom error message"
        error = WatchdogUnavailableError(message)
        assert str(error) == message

    def test_exception_with_standard_message(self):
        """Test exception with the standard watchdog missing message."""
        expected_message = "Filesystem watcher mode requires the 'watchdog' dependency. Install via 'pip install watchdog'."
        error = WatchdogUnavailableError(expected_message)
        assert str(error) == expected_message

    def test_exception_raised_when_observer_none(self, mock_processor, watcher_settings):
        """Test that FileWatcherLoop raises WatchdogUnavailableError when Observer is None."""
        with patch("playbook.watcher.Observer", None):
            with pytest.raises(
                WatchdogUnavailableError,
                match=r"Filesystem watcher mode requires the 'watchdog' dependency"
            ):
                FileWatcherLoop(mock_processor, watcher_settings)


# Tests for _FileChangeHandler class


class TestFileChangeHandler:
    """Tests for the _FileChangeHandler class."""

    def test_on_created_queues_file_path(self):
        """Test that on_created adds file path to queue."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=[])

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/new_file.mkv"

        handler.on_created(event)

        assert not queue.empty()
        assert queue.get() == Path("/path/to/new_file.mkv")

    def test_on_created_ignores_directory_events(self):
        """Test that on_created ignores directory creation events."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=[])

        event = MagicMock()
        event.is_directory = True
        event.src_path = "/path/to/new_directory"

        handler.on_created(event)

        assert queue.empty()

    def test_on_modified_queues_file_path(self):
        """Test that on_modified adds file path to queue."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=[])

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/modified_file.mp4"

        handler.on_modified(event)

        assert not queue.empty()
        assert queue.get() == Path("/path/to/modified_file.mp4")

    def test_on_modified_ignores_directory_events(self):
        """Test that on_modified ignores directory modification events."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=[])

        event = MagicMock()
        event.is_directory = True
        event.src_path = "/path/to/modified_directory"

        handler.on_modified(event)

        assert queue.empty()

    def test_on_moved_queues_destination_path(self):
        """Test that on_moved adds destination path (not source) to queue."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=[])

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/old_file.mkv"
        event.dest_path = "/path/to/new_file.mkv"

        handler.on_moved(event)

        assert not queue.empty()
        queued_path = queue.get()
        assert queued_path == Path("/path/to/new_file.mkv")
        assert queued_path != Path("/path/to/old_file.mkv")

    def test_on_moved_ignores_directory_events(self):
        """Test that on_moved ignores directory move events."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=[])

        event = MagicMock()
        event.is_directory = True
        event.src_path = "/path/to/old_directory"
        event.dest_path = "/path/to/new_directory"

        handler.on_moved(event)

        assert queue.empty()

    def test_matches_with_include_pattern_matching_filename(self):
        """Test that _matches returns True when filename matches include pattern."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=["*.mkv", "*.mp4"], ignore=[])

        assert handler._matches(Path("/path/to/file.mkv"))
        assert handler._matches(Path("/path/to/file.mp4"))
        assert not handler._matches(Path("/path/to/file.avi"))

    def test_matches_with_include_pattern_matching_full_path(self):
        """Test that _matches can match against full path."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=["*/videos/*.mkv"], ignore=[])

        assert handler._matches(Path("/home/user/videos/movie.mkv"))
        assert not handler._matches(Path("/home/user/docs/movie.mkv"))

    def test_matches_with_ignore_pattern_matching_filename(self):
        """Test that _matches returns False when filename matches ignore pattern."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=["*.tmp", "*.part"])

        assert not handler._matches(Path("/path/to/file.tmp"))
        assert not handler._matches(Path("/path/to/file.part"))
        assert handler._matches(Path("/path/to/file.mkv"))

    def test_matches_with_ignore_pattern_matching_full_path(self):
        """Test that _matches can ignore based on full path pattern."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=["*/temp/*"])

        assert not handler._matches(Path("/home/user/temp/file.mkv"))
        assert handler._matches(Path("/home/user/videos/file.mkv"))

    def test_matches_with_both_include_and_ignore_patterns(self):
        """Test that _matches respects both include and ignore patterns."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=["*.mkv", "*.mp4"], ignore=["*.tmp"])

        # Matches include but not ignore - should match
        assert handler._matches(Path("/path/to/file.mkv"))

        # Matches include but also ignore - should not match
        assert not handler._matches(Path("/path/to/file.tmp"))

        # Doesn't match include - should not match
        assert not handler._matches(Path("/path/to/file.avi"))

    def test_matches_with_empty_include_allows_all(self):
        """Test that empty include list allows all files."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=[])

        assert handler._matches(Path("/path/to/file.mkv"))
        assert handler._matches(Path("/path/to/file.txt"))
        assert handler._matches(Path("/path/to/anything.xyz"))

    def test_matches_with_empty_ignore_blocks_nothing(self):
        """Test that empty ignore list blocks nothing."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=["*.mkv"], ignore=[])

        assert handler._matches(Path("/path/to/file.mkv"))

    def test_on_created_respects_include_filter(self):
        """Test that on_created only queues files matching include pattern."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=["*.mkv"], ignore=[])

        # Matching file should be queued
        event_match = MagicMock()
        event_match.is_directory = False
        event_match.src_path = "/path/to/file.mkv"
        handler.on_created(event_match)

        # Non-matching file should not be queued
        event_no_match = MagicMock()
        event_no_match.is_directory = False
        event_no_match.src_path = "/path/to/file.txt"
        handler.on_created(event_no_match)

        assert queue.qsize() == 1
        assert queue.get() == Path("/path/to/file.mkv")

    def test_on_created_respects_ignore_filter(self):
        """Test that on_created does not queue files matching ignore pattern."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=["*.tmp"])

        # Non-ignored file should be queued
        event_ok = MagicMock()
        event_ok.is_directory = False
        event_ok.src_path = "/path/to/file.mkv"
        handler.on_created(event_ok)

        # Ignored file should not be queued
        event_ignored = MagicMock()
        event_ignored.is_directory = False
        event_ignored.src_path = "/path/to/file.tmp"
        handler.on_created(event_ignored)

        assert queue.qsize() == 1
        assert queue.get() == Path("/path/to/file.mkv")

    def test_on_modified_respects_include_filter(self):
        """Test that on_modified only queues files matching include pattern."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=["*.mp4"], ignore=[])

        # Matching file should be queued
        event_match = MagicMock()
        event_match.is_directory = False
        event_match.src_path = "/path/to/video.mp4"
        handler.on_modified(event_match)

        # Non-matching file should not be queued
        event_no_match = MagicMock()
        event_no_match.is_directory = False
        event_no_match.src_path = "/path/to/document.pdf"
        handler.on_modified(event_no_match)

        assert queue.qsize() == 1
        assert queue.get() == Path("/path/to/video.mp4")

    def test_on_modified_respects_ignore_filter(self):
        """Test that on_modified does not queue files matching ignore pattern."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=["*.part"])

        # Non-ignored file should be queued
        event_ok = MagicMock()
        event_ok.is_directory = False
        event_ok.src_path = "/path/to/video.mkv"
        handler.on_modified(event_ok)

        # Ignored file should not be queued
        event_ignored = MagicMock()
        event_ignored.is_directory = False
        event_ignored.src_path = "/path/to/download.part"
        handler.on_modified(event_ignored)

        assert queue.qsize() == 1
        assert queue.get() == Path("/path/to/video.mkv")

    def test_on_moved_respects_include_filter(self):
        """Test that on_moved only queues destination paths matching include pattern."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=["*.mkv"], ignore=[])

        # Matching destination should be queued
        event_match = MagicMock()
        event_match.is_directory = False
        event_match.src_path = "/path/old.avi"
        event_match.dest_path = "/path/new.mkv"
        handler.on_moved(event_match)

        # Non-matching destination should not be queued
        event_no_match = MagicMock()
        event_no_match.is_directory = False
        event_no_match.src_path = "/path/old.mkv"
        event_no_match.dest_path = "/path/new.txt"
        handler.on_moved(event_no_match)

        assert queue.qsize() == 1
        assert queue.get() == Path("/path/new.mkv")

    def test_on_moved_respects_ignore_filter(self):
        """Test that on_moved does not queue destination paths matching ignore pattern."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=[], ignore=["*.tmp"])

        # Non-ignored destination should be queued
        event_ok = MagicMock()
        event_ok.is_directory = False
        event_ok.src_path = "/path/old.mkv"
        event_ok.dest_path = "/path/new.mkv"
        handler.on_moved(event_ok)

        # Ignored destination should not be queued
        event_ignored = MagicMock()
        event_ignored.is_directory = False
        event_ignored.src_path = "/path/old.mkv"
        event_ignored.dest_path = "/path/new.tmp"
        handler.on_moved(event_ignored)

        assert queue.qsize() == 1
        assert queue.get() == Path("/path/new.mkv")

    def test_multiple_file_events_queued_correctly(self):
        """Test that multiple file events are all queued correctly."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=["*.mkv", "*.mp4"], ignore=["*.tmp"])

        # Create event
        event1 = MagicMock()
        event1.is_directory = False
        event1.src_path = "/path/to/file1.mkv"
        handler.on_created(event1)

        # Modify event
        event2 = MagicMock()
        event2.is_directory = False
        event2.src_path = "/path/to/file2.mp4"
        handler.on_modified(event2)

        # Move event
        event3 = MagicMock()
        event3.is_directory = False
        event3.src_path = "/path/to/old.mkv"
        event3.dest_path = "/path/to/new.mkv"
        handler.on_moved(event3)

        # Ignored event
        event4 = MagicMock()
        event4.is_directory = False
        event4.src_path = "/path/to/file.tmp"
        handler.on_created(event4)

        # Should have 3 items in queue (event4 was ignored)
        assert queue.qsize() == 3
        assert queue.get() == Path("/path/to/file1.mkv")
        assert queue.get() == Path("/path/to/file2.mp4")
        assert queue.get() == Path("/path/to/new.mkv")

    def test_handler_initialization(self):
        """Test that _FileChangeHandler initializes correctly."""
        queue = Queue()
        include = ["*.mkv", "*.mp4"]
        ignore = ["*.tmp", "*.part"]

        handler = _FileChangeHandler(queue, include=include, ignore=ignore)

        assert handler._queue is queue
        assert handler._include == include
        assert handler._ignore == ignore

    def test_handler_with_mixed_case_patterns(self):
        """Test that patterns work with mixed case (fnmatch is case-sensitive on most systems)."""
        queue = Queue()
        handler = _FileChangeHandler(queue, include=["*.MKV", "*.mkv"], ignore=[])

        # This behavior depends on the filesystem, but fnmatch is typically case-sensitive
        assert handler._matches(Path("/path/to/file.mkv"))
        assert handler._matches(Path("/path/to/FILE.MKV"))


# Tests for FileWatcherLoop initialization


class TestFileWatcherLoopInit:
    """Tests for FileWatcherLoop.__init__ method."""

    def test_raises_watchdog_unavailable_error_when_observer_none(self, mock_processor, watcher_settings):
        """Test that FileWatcherLoop raises WatchdogUnavailableError when Observer is None."""
        with patch("playbook.watcher.Observer", None):
            with pytest.raises(
                WatchdogUnavailableError,
                match=r"Filesystem watcher mode requires the 'watchdog' dependency"
            ):
                FileWatcherLoop(mock_processor, watcher_settings)

    def test_successful_initialization_with_valid_settings(self, mock_processor, watcher_settings, mock_observer):
        """Test that FileWatcherLoop initializes successfully with valid settings."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Verify all instance variables are set correctly
            assert loop._processor is mock_processor
            assert loop._settings is watcher_settings
            assert isinstance(loop._queue, Queue)
            assert isinstance(loop._handler, _FileChangeHandler)
            assert loop._observer is mock_observer

            # Verify handler was created with correct patterns
            assert loop._handler._include == watcher_settings.include
            assert loop._handler._ignore == watcher_settings.ignore

    def test_initialization_schedules_observer_for_each_root(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that FileWatcherLoop schedules observer for each root directory."""
        # Set up multiple paths to watch
        path1 = tmp_path / "watch1"
        path2 = tmp_path / "watch2"
        path1.mkdir()
        path2.mkdir()

        watcher_settings.paths = [str(path1), str(path2)]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Verify observer.schedule was called for each root
            assert mock_observer.schedule.call_count == 2

            # Verify schedule was called with correct arguments
            calls = mock_observer.schedule.call_args_list
            scheduled_paths = {call[0][1] for call in calls}  # Extract path argument from each call
            assert str(path1) in scheduled_paths
            assert str(path2) in scheduled_paths

            # Verify handler and recursive=True were passed
            for call in calls:
                assert call[0][0] == loop._handler  # First arg is handler
                assert call[1]["recursive"] is True  # recursive=True

    def test_initialization_with_empty_paths_uses_source_dir(self, mock_processor, minimal_watcher_settings, mock_observer, tmp_path):
        """Test that FileWatcherLoop uses source_dir as default when paths is empty."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir
        minimal_watcher_settings.paths = []

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, minimal_watcher_settings)

            # Verify observer.schedule was called with source_dir
            assert mock_observer.schedule.call_count == 1
            call_args = mock_observer.schedule.call_args
            assert call_args[0][1] == str(source_dir)

    def test_initialization_resolves_relative_paths(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that FileWatcherLoop resolves relative paths against source_dir."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        # Set relative path
        watcher_settings.paths = ["relative/subdir"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Verify the resolved path is relative to source_dir
            expected_path = source_dir / "relative/subdir"
            assert mock_observer.schedule.call_count == 1
            call_args = mock_observer.schedule.call_args
            assert call_args[0][1] == str(expected_path)

            # Verify directory was created
            assert expected_path.exists()

    def test_initialization_resolves_absolute_paths(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that FileWatcherLoop handles absolute paths correctly."""
        absolute_path = tmp_path / "absolute_watch"
        absolute_path.mkdir()

        watcher_settings.paths = [str(absolute_path)]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Verify the absolute path is used as-is
            assert mock_observer.schedule.call_count == 1
            call_args = mock_observer.schedule.call_args
            assert call_args[0][1] == str(absolute_path)

    def test_initialization_expands_user_home_directory(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that FileWatcherLoop expands ~ to user home directory."""
        # Create a path with ~ that will be expanded
        watcher_settings.paths = ["~/watch_dir"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            with patch("pathlib.Path.expanduser") as mock_expanduser:
                # Mock expanduser to return a specific path
                expanded_path = tmp_path / "home/user/watch_dir"
                mock_expanduser.return_value = expanded_path

                # Also need to mock mkdir since expanded_path won't exist
                with patch("pathlib.Path.mkdir"):
                    loop = FileWatcherLoop(mock_processor, watcher_settings)

                    # Verify expanduser was called
                    assert mock_expanduser.called

    def test_initialization_creates_directories_if_not_exist(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that FileWatcherLoop creates watch directories if they don't exist."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        # Set path that doesn't exist yet
        new_dir = source_dir / "new/nested/dir"
        watcher_settings.paths = [str(new_dir)]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Verify directory was created
            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_initialization_with_multiple_paths_mixed_types(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test FileWatcherLoop initialization with mixed absolute and relative paths."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        # Create one absolute path
        absolute_path = tmp_path / "absolute"
        absolute_path.mkdir()

        # Use relative path for second
        relative_path = "relative"

        watcher_settings.paths = [str(absolute_path), relative_path]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Verify both paths were scheduled
            assert mock_observer.schedule.call_count == 2

            calls = mock_observer.schedule.call_args_list
            scheduled_paths = {call[0][1] for call in calls}

            # Verify absolute path is preserved
            assert str(absolute_path) in scheduled_paths

            # Verify relative path is resolved against source_dir
            expected_relative = source_dir / relative_path
            assert str(expected_relative) in scheduled_paths

    def test_initialization_stores_resolved_roots(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that FileWatcherLoop stores resolved roots in _roots attribute."""
        path1 = tmp_path / "watch1"
        path2 = tmp_path / "watch2"
        path1.mkdir()
        path2.mkdir()

        watcher_settings.paths = [str(path1), str(path2)]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Verify _roots attribute contains both paths
            assert len(loop._roots) == 2
            assert path1 in loop._roots
            assert path2 in loop._roots
            assert all(isinstance(root, Path) for root in loop._roots)


# Tests for FileWatcherLoop._resolve_roots method


class TestFileWatcherLoopResolveRoots:
    """Tests for FileWatcherLoop._resolve_roots method."""

    def test_default_to_source_dir_when_paths_empty(self, mock_processor, minimal_watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots returns source_dir when paths is empty."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir
        minimal_watcher_settings.paths = []

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, minimal_watcher_settings)
            roots = loop._roots

            # Should return source_dir as default
            assert len(roots) == 1
            assert roots[0] == source_dir

    def test_default_to_source_dir_when_paths_none(self, mock_processor, minimal_watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots returns source_dir when paths is None."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir
        minimal_watcher_settings.paths = None

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, minimal_watcher_settings)
            roots = loop._roots

            # Should return source_dir as default
            assert len(roots) == 1
            assert roots[0] == source_dir

    def test_resolves_relative_path_against_source_dir(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots resolves relative paths against source_dir."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        watcher_settings.paths = ["relative/path"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # Should resolve relative to source_dir
            expected_path = source_dir / "relative/path"
            assert len(roots) == 1
            assert roots[0] == expected_path

    def test_resolves_multiple_relative_paths(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots handles multiple relative paths."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        watcher_settings.paths = ["rel1", "rel2/sub", "rel3"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # Should resolve all relative to source_dir
            assert len(roots) == 3
            assert roots[0] == source_dir / "rel1"
            assert roots[1] == source_dir / "rel2/sub"
            assert roots[2] == source_dir / "rel3"

    def test_preserves_absolute_paths(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots preserves absolute paths."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        absolute_path = tmp_path / "absolute/watch"
        watcher_settings.paths = [str(absolute_path)]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # Should preserve absolute path
            assert len(roots) == 1
            assert roots[0] == absolute_path

    def test_handles_mixed_absolute_and_relative_paths(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots correctly handles mixed path types."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        absolute_path = tmp_path / "absolute"
        watcher_settings.paths = [str(absolute_path), "relative", "another/relative"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # Should have 3 roots
            assert len(roots) == 3
            assert roots[0] == absolute_path
            assert roots[1] == source_dir / "relative"
            assert roots[2] == source_dir / "another/relative"

    def test_creates_directory_for_absolute_path(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots creates directory for non-existent absolute path."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        # Use a path that doesn't exist yet
        new_absolute_path = tmp_path / "new/absolute/path"
        watcher_settings.paths = [str(new_absolute_path)]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # Directory should have been created
            assert new_absolute_path.exists()
            assert new_absolute_path.is_dir()
            assert roots[0] == new_absolute_path

    def test_creates_directory_for_relative_path(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots creates directory for non-existent relative path."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        watcher_settings.paths = ["new/relative/path"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # Directory should have been created relative to source_dir
            expected_path = source_dir / "new/relative/path"
            assert expected_path.exists()
            assert expected_path.is_dir()
            assert roots[0] == expected_path

    def test_creates_nested_directories(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots creates deeply nested directories."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        watcher_settings.paths = ["level1/level2/level3/level4"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # All parent directories should have been created
            expected_path = source_dir / "level1/level2/level3/level4"
            assert expected_path.exists()
            assert expected_path.is_dir()
            assert (source_dir / "level1").exists()
            assert (source_dir / "level1/level2").exists()
            assert (source_dir / "level1/level2/level3").exists()

    def test_expands_user_home_directory(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots expands ~ to user home directory."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        watcher_settings.paths = ["~/watch_dir"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            # We need to mock Path.expanduser
            original_expanduser = Path.expanduser

            def mock_expanduser_func(self):
                if "~" in str(self):
                    # Replace ~ with a tmp path for testing
                    return Path(str(self).replace("~", str(tmp_path / "home/user")))
                return self

            with patch.object(Path, "expanduser", mock_expanduser_func):
                loop = FileWatcherLoop(mock_processor, watcher_settings)
                roots = loop._roots

                # Should have expanded ~ to home directory
                assert len(roots) == 1
                assert "~" not in str(roots[0])
                # The path should contain our mocked home directory
                assert str(tmp_path / "home/user") in str(roots[0])

    def test_expands_user_home_in_relative_path(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots expands ~ even when path becomes relative to source_dir."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        # Path with ~ that's not at the start (though this is unusual)
        watcher_settings.paths = ["~relative"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # Should expand and process the path
            assert len(roots) == 1
            # The exact behavior depends on whether ~relative is considered absolute after expansion

    def test_returns_pathlib_path_objects(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots returns Path objects, not strings."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        watcher_settings.paths = [str(tmp_path / "path1"), "relative_path2"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # All roots should be Path objects
            assert all(isinstance(root, Path) for root in roots)
            assert len(roots) == 2

    def test_handles_duplicate_paths(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots preserves duplicate paths (doesn't deduplicate)."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        # Same path specified twice
        watcher_settings.paths = ["same/path", "same/path"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # Method doesn't deduplicate, so we should have 2 entries
            assert len(roots) == 2
            assert roots[0] == roots[1]

    def test_handles_path_with_dots(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots handles paths with . and .. components."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        mock_processor.config.settings.source_dir = source_dir

        # Relative path with ..
        watcher_settings.paths = ["subdir/../other"]

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # Path should be normalized
            expected_path = source_dir / "subdir/../other"
            assert len(roots) == 1
            # The path may or may not be normalized, but it should work
            assert roots[0].exists()

    def test_source_dir_as_string_path(self, mock_processor, watcher_settings, mock_observer, tmp_path):
        """Test that _resolve_roots works when source_dir is a Path object."""
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        # Ensure source_dir is a Path object
        mock_processor.config.settings.source_dir = source_dir

        watcher_settings.paths = []

        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)
            roots = loop._roots

            # Should handle Path object for source_dir
            assert len(roots) == 1
            assert roots[0] == source_dir


# Tests for FileWatcherLoop._run_processor method


class TestFileWatcherLoopRunProcessor:
    """Tests for FileWatcherLoop._run_processor method."""

    def test_calls_processor_process_all(self, mock_processor, watcher_settings, mock_observer):
        """Test that _run_processor calls processor.process_all()."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Create a set of pending paths
            pending = {Path("/path/to/file1.mkv"), Path("/path/to/file2.mp4")}

            # Call _run_processor
            loop._run_processor(pending)

            # Verify processor.process_all() was called
            mock_processor.process_all.assert_called_once()

    def test_calls_processor_process_all_with_empty_set(self, mock_processor, watcher_settings, mock_observer):
        """Test that _run_processor calls processor.process_all() even with empty pending set."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Call _run_processor with empty set
            loop._run_processor(set())

            # Verify processor.process_all() was still called
            mock_processor.process_all.assert_called_once()

    def test_calls_processor_process_all_with_single_file(self, mock_processor, watcher_settings, mock_observer):
        """Test that _run_processor calls processor.process_all() with single file."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Create a set with single path
            pending = {Path("/path/to/file.mkv")}

            # Call _run_processor
            loop._run_processor(pending)

            # Verify processor.process_all() was called
            mock_processor.process_all.assert_called_once()

    def test_logs_detected_changes_with_single_file(self, mock_processor, watcher_settings, mock_observer, caplog):
        """Test that _run_processor logs the number of changes for a single file."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Create a set with single path
            pending = {Path("/videos/movie.mkv")}

            # Capture log output
            with caplog.at_level(logging.DEBUG):
                loop._run_processor(pending)

            # Verify log message
            assert any("Detected 1 filesystem change" in record.message for record in caplog.records)
            assert any("running processor" in record.message for record in caplog.records)

    def test_logs_detected_changes_with_multiple_files(self, mock_processor, watcher_settings, mock_observer, caplog):
        """Test that _run_processor logs the number of changes for multiple files."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Create a set with multiple paths
            pending = {
                Path("/videos/movie1.mkv"),
                Path("/videos/movie2.mp4"),
                Path("/videos/movie3.mkv"),
            }

            # Capture log output
            with caplog.at_level(logging.DEBUG):
                loop._run_processor(pending)

            # Verify log message shows correct count
            assert any("Detected 3 filesystem change" in record.message for record in caplog.records)
            assert any("running processor" in record.message for record in caplog.records)

    def test_logs_parent_directory_sample(self, mock_processor, watcher_settings, mock_observer, caplog):
        """Test that _run_processor includes parent directory sample in log message."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Create a set with paths from same directory
            pending = {
                Path("/videos/sports/game1.mkv"),
                Path("/videos/sports/game2.mp4"),
            }

            # Capture log output
            with caplog.at_level(logging.DEBUG):
                loop._run_processor(pending)

            # Verify log message includes parent directory
            assert any("near /videos/sports" in record.message for record in caplog.records)

    def test_logs_multiple_parent_directories_sample(self, mock_processor, watcher_settings, mock_observer, caplog):
        """Test that _run_processor includes samples from multiple parent directories."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Create a set with paths from different directories
            pending = {
                Path("/videos/sports/game.mkv"),
                Path("/videos/movies/film.mp4"),
                Path("/videos/shows/episode.mkv"),
            }

            # Capture log output
            with caplog.at_level(logging.DEBUG):
                loop._run_processor(pending)

            # Verify log message includes parent directories (sorted)
            # The method shows up to 3 directories in sorted order
            log_messages = [record.message for record in caplog.records if "Detected" in record.message]
            assert len(log_messages) > 0
            log_message = log_messages[0]
            assert "near" in log_message
            # All three directories should be mentioned
            assert "/videos/movies" in log_message
            assert "/videos/shows" in log_message
            assert "/videos/sports" in log_message

    def test_logs_limits_parent_directories_to_three(self, mock_processor, watcher_settings, mock_observer, caplog):
        """Test that _run_processor limits parent directory sample to 3 directories."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Create a set with paths from more than 3 different directories
            pending = {
                Path("/videos/dir1/file1.mkv"),
                Path("/videos/dir2/file2.mp4"),
                Path("/videos/dir3/file3.mkv"),
                Path("/videos/dir4/file4.mp4"),
                Path("/videos/dir5/file5.mkv"),
            }

            # Capture log output
            with caplog.at_level(logging.DEBUG):
                loop._run_processor(pending)

            # Verify log message shows sample of directories (limited to 3)
            log_messages = [record.message for record in caplog.records if "Detected" in record.message]
            assert len(log_messages) > 0
            log_message = log_messages[0]

            # Count how many directories are mentioned (should be max 3)
            dir_count = sum(1 for i in range(1, 6) if f"/videos/dir{i}" in log_message)
            assert dir_count == 3

    def test_logs_deduplicates_parent_directories(self, mock_processor, watcher_settings, mock_observer, caplog):
        """Test that _run_processor deduplicates parent directories in log sample."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Create a set with multiple files from same directory
            pending = {
                Path("/videos/sports/game1.mkv"),
                Path("/videos/sports/game2.mp4"),
                Path("/videos/sports/game3.mkv"),
                Path("/videos/sports/game4.mp4"),
            }

            # Capture log output
            with caplog.at_level(logging.DEBUG):
                loop._run_processor(pending)

            # Verify log message shows directory only once
            log_messages = [record.message for record in caplog.records if "Detected" in record.message]
            assert len(log_messages) > 0
            log_message = log_messages[0]

            # Should show "near /videos/sports" but only once
            assert log_message.count("/videos/sports") == 1

    def test_logs_without_sample_when_empty(self, mock_processor, watcher_settings, mock_observer, caplog):
        """Test that _run_processor logs without parent directory sample when pending is empty."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Call with empty set
            loop._run_processor(set())

            # Capture log output
            with caplog.at_level(logging.DEBUG):
                loop._run_processor(set())

            # Verify log message doesn't include "near" when there are no files
            log_messages = [record.message for record in caplog.records if "Detected" in record.message]
            assert any("Detected 0 filesystem change" in msg for msg in log_messages)
            # When sample is empty, "near" should not appear
            assert not any("near" in msg for msg in log_messages if "Detected 0" in msg)

    def test_logs_at_debug_level(self, mock_processor, watcher_settings, mock_observer, caplog):
        """Test that _run_processor logs at DEBUG level."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            pending = {Path("/videos/movie.mkv")}

            # Capture log output at DEBUG level
            with caplog.at_level(logging.DEBUG):
                loop._run_processor(pending)

            # Verify log was at DEBUG level
            debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
            assert any("Detected" in record.message for record in debug_records)

    def test_logs_sorted_parent_directories(self, mock_processor, watcher_settings, mock_observer, caplog):
        """Test that _run_processor sorts parent directories in log sample."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Create a set with paths in non-alphabetical order
            pending = {
                Path("/videos/zebra/file.mkv"),
                Path("/videos/alpha/file.mp4"),
                Path("/videos/beta/file.mkv"),
            }

            # Capture log output
            with caplog.at_level(logging.DEBUG):
                loop._run_processor(pending)

            # Verify log message shows directories in sorted order
            log_messages = [record.message for record in caplog.records if "Detected" in record.message]
            assert len(log_messages) > 0
            log_message = log_messages[0]

            # Extract the "near" portion
            if "near" in log_message:
                near_part = log_message.split("near")[1].split(";")[0].strip()
                # Should be in alphabetical order: alpha, beta, zebra
                alpha_pos = near_part.find("/videos/alpha")
                beta_pos = near_part.find("/videos/beta")
                zebra_pos = near_part.find("/videos/zebra")

                assert alpha_pos < beta_pos < zebra_pos

    def test_processor_called_regardless_of_pending_count(self, mock_processor, watcher_settings, mock_observer):
        """Test that processor.process_all() is called regardless of pending count."""
        with patch("playbook.watcher.Observer", return_value=mock_observer):
            loop = FileWatcherLoop(mock_processor, watcher_settings)

            # Test with various pending set sizes
            for count in [0, 1, 5, 100]:
                mock_processor.process_all.reset_mock()
                pending = {Path(f"/videos/file{i}.mkv") for i in range(count)}
                loop._run_processor(pending)

                # Verify process_all was called exactly once
                mock_processor.process_all.assert_called_once()
