"""
Playbook Web GUI using NiceGUI.

This package provides a web-based interface for monitoring and managing Playbook,
including real-time processing dashboard, log viewer, configuration editor,
and sports management.

Public API:
    - run_with_gui: Main entry point to run Playbook with GUI enabled
    - GUIState: Shared state between Processor and GUI
    - create_app: Create and configure the NiceGUI application
"""

from __future__ import annotations

from .app import create_app, run_with_gui
from .state import GUIState, gui_state

__all__ = [
    "create_app",
    "run_with_gui",
    "GUIState",
    "gui_state",
]
