"""
Shared state management between Processor and GUI.

This module provides the GUIState class which bridges the Processor's
processing state with the GUI layer, enabling real-time updates.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playbook.config import AppConfig
    from playbook.notifications import NotificationEvent
    from playbook.persistence import ProcessedFileStore, UnmatchedFileStore
    from playbook.processor import Processor


@dataclass
class LogEntry:
    """A single log entry for GUI display."""

    timestamp: datetime
    level: str
    message: str
    logger_name: str = ""


@dataclass
class GUIState:
    """Shared state between Processor and GUI.

    This dataclass holds references to the processor and maintains
    buffers for real-time GUI updates including activity events
    and log entries.

    Attributes:
        processor: Reference to the Processor instance (set at startup)
        config: Reference to the AppConfig (set at startup)
        config_path: Path to the configuration file
        recent_events: Ring buffer of recent notification events
        log_buffer: Ring buffer of log entries for GUI display
        is_processing: Whether a processing run is currently active
        last_run_at: Timestamp of the last processing run
        run_count: Number of processing runs since startup
    """

    # Reference to processor (set at startup)
    processor: Processor | None = None
    config: AppConfig | None = None
    config_path: Path | None = None
    processed_store: ProcessedFileStore | None = None
    unmatched_store: UnmatchedFileStore | None = None

    # Recent activity (ring buffer)
    recent_events: deque[NotificationEvent] = field(default_factory=lambda: deque(maxlen=100))

    # Log buffer for GUI display
    log_buffer: deque[LogEntry] = field(default_factory=lambda: deque(maxlen=500))

    # Processing status
    is_processing: bool = False
    last_run_at: datetime | None = None
    run_count: int = 0

    # GUI update callbacks (set by app.py)
    _update_callbacks: list[Any] = field(default_factory=list)

    def add_event(self, event: NotificationEvent) -> None:
        """Add event to activity feed and notify GUI."""
        self.recent_events.appendleft(event)
        self._notify_update("event", event)

    def add_log(self, level: str, message: str, logger_name: str = "") -> None:
        """Add log entry to buffer and notify GUI."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            logger_name=logger_name,
        )
        self.log_buffer.appendleft(entry)
        self._notify_update("log", entry)

    def set_processing(self, is_processing: bool) -> None:
        """Update processing status and notify GUI."""
        self.is_processing = is_processing
        if not is_processing:
            self.last_run_at = datetime.now()
            self.run_count += 1
        self._notify_update("status", {"is_processing": is_processing})

    def request_cancel(self) -> bool:
        """Request cancellation of the current processing run.

        Returns:
            True if cancellation was requested, False if no processing is active.
        """
        if not self.is_processing or not self.processor:
            return False
        self.processor.request_cancel()
        return True

    def register_update_callback(self, callback: Any) -> None:
        """Register a callback to be notified of state changes."""
        if callback not in self._update_callbacks:
            self._update_callbacks.append(callback)

    def unregister_update_callback(self, callback: Any) -> None:
        """Unregister a previously registered callback."""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)

    def _notify_update(self, update_type: str, data: Any) -> None:
        """Notify all registered callbacks of a state change."""
        import contextlib

        for callback in self._update_callbacks:
            with contextlib.suppress(Exception):
                callback(update_type, data)

    def get_stats(self) -> dict[str, Any]:
        """Get current processing statistics from the processor."""
        if not self.processor:
            return {
                "processed": 0,
                "skipped": 0,
                "ignored": 0,
                "errors": 0,
                "warnings": 0,
            }

        state = self.processor._state
        return {
            "processed": sum(state.touched_destinations is not None for _ in [1]),  # Placeholder
            "skipped": 0,
            "ignored": 0,
            "errors": 0,
            "warnings": 0,
        }

    def get_sports(self) -> list[dict[str, Any]]:
        """Get list of configured sports with their status."""
        if not self.config:
            return []

        sports = []
        for sport in self.config.sports:
            sports.append(
                {
                    "id": sport.id,
                    "name": sport.name,
                    "show_slug": sport.show_slug,
                    "enabled": sport.enabled,
                    "link_mode": sport.link_mode,
                }
            )
        return sports


# Global state instance
gui_state = GUIState()
