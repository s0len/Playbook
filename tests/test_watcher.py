from __future__ import annotations

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
