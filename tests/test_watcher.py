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


# Test infrastructure is now set up for subsequent subtasks
