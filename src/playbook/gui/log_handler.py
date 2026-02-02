"""
Custom logging handler for forwarding logs to the GUI.

This module provides a logging.Handler subclass that forwards
log records to the GUI state buffer for real-time display.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import GUIState


class GUILogHandler(logging.Handler):
    """Forwards log records to GUI state buffer.

    This handler captures log records and adds them to the GUI state's
    log buffer, enabling real-time log display in the web interface.
    """

    def __init__(self, gui_state: GUIState, level: int = logging.NOTSET) -> None:
        """Initialize the handler.

        Args:
            gui_state: The GUIState instance to forward logs to
            level: Minimum log level to capture (default: NOTSET = all levels)
        """
        super().__init__(level)
        self._gui_state = gui_state
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        """Forward a log record to the GUI state.

        Args:
            record: The log record to forward
        """
        try:
            msg = self.format(record)
            self._gui_state.add_log(
                level=record.levelname,
                message=msg,
                logger_name=record.name,
            )
        except Exception:
            self.handleError(record)


def install_gui_log_handler(gui_state: GUIState, level: int = logging.DEBUG) -> GUILogHandler:
    """Install the GUI log handler on the root logger.

    Args:
        gui_state: The GUIState instance to forward logs to
        level: Minimum log level to capture

    Returns:
        The installed GUILogHandler instance
    """
    handler = GUILogHandler(gui_state, level)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    return handler


def remove_gui_log_handler(handler: GUILogHandler) -> None:
    """Remove the GUI log handler from the root logger.

    Args:
        handler: The handler to remove
    """
    root_logger = logging.getLogger()
    root_logger.removeHandler(handler)
