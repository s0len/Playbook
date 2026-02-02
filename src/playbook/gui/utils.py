"""
Utility functions for the Playbook GUI.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from nicegui import ui

LOGGER = logging.getLogger(__name__)


def safe_timer(interval: float, callback: Callable[[], Any], *, once: bool = False) -> ui.timer:
    """Create a timer that safely handles client disconnection.

    The timer automatically deactivates when the client disconnects,
    preventing "parent slot deleted" errors.

    Args:
        interval: Timer interval in seconds
        callback: Function to call on each interval
        once: If True, timer only fires once

    Returns:
        The created timer element
    """
    timer = ui.timer(interval, callback, once=once)

    # Deactivate timer when client disconnects
    async def on_disconnect() -> None:
        try:
            timer.active = False
        except Exception:
            pass

    try:
        client = ui.context.client
        client.on_disconnect(on_disconnect)
    except Exception:
        # Context not available, timer will clean up naturally
        pass

    return timer
