"""
Utility functions for the Playbook GUI.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from nicegui import ui

LOGGER = logging.getLogger(__name__)


def safe_timer(interval: float, callback: Callable[[], Any], *, once: bool = False) -> ui.timer:
    """Create a timer that safely handles client disconnection.

    Wraps the callback to catch exceptions when the client has disconnected,
    and deactivates the timer on disconnect.

    Args:
        interval: Timer interval in seconds
        callback: Function to call on each interval
        once: If True, timer only fires once

    Returns:
        The created timer element
    """
    timer_ref: list[ui.timer | None] = [None]

    @wraps(callback)
    def safe_callback() -> None:
        # Check if timer is still active
        if timer_ref[0] is not None and not timer_ref[0].active:
            return
        try:
            callback()
        except (RuntimeError, KeyError):
            # Client disconnected or element deleted
            if timer_ref[0] is not None:
                timer_ref[0].active = False

    timer = ui.timer(interval, safe_callback, once=once)
    timer_ref[0] = timer

    # Deactivate timer when client disconnects
    def on_disconnect() -> None:
        try:
            timer.active = False
        except Exception:
            pass

    try:
        client = ui.context.client
        client.on_disconnect(on_disconnect)
    except Exception:
        # Context not available
        pass

    return timer


def safe_notify(
    client,
    message: str,
    *,
    type: str = "info",  # noqa: A002
    position: str = "bottom",
    **kwargs,
) -> None:
    """Safely send a notification to a client that may have disconnected.

    Use this for notifications after async operations where the client
    may have closed the browser tab or navigated away.

    Args:
        client: The NiceGUI client to notify
        message: The notification message
        type: Notification type (info, positive, negative, warning)
        position: Notification position
        **kwargs: Additional arguments passed to ui.notify
    """
    # Check if client is deleted before attempting to use it
    # NiceGUI uses _deleted (private attribute) to track deleted clients
    if getattr(client, "_deleted", False):
        LOGGER.debug("Skipping notification - client disconnected: %s", message)
        return
    try:
        with client:
            ui.notify(message, type=type, position=position, **kwargs)
    except Exception:
        # Client disconnected or other error - silently ignore
        LOGGER.debug("Failed to send notification (client likely disconnected): %s", message)


def suppress_nicegui_disconnect_errors() -> None:
    """Suppress NiceGUI 'parent slot deleted' errors in logging.

    These errors occur normally when users navigate away from pages
    with active timers and are not actual problems.
    """
    import logging

    class DisconnectErrorFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return not (record.name == "nicegui" and "parent slot" in str(record.msg).lower())

    # Add filter to nicegui logger
    nicegui_logger = logging.getLogger("nicegui")
    nicegui_logger.addFilter(DisconnectErrorFilter())
