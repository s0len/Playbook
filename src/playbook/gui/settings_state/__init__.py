"""
State management modules for the Playbook GUI.

Provides state classes for managing form data, validation, and UI state.
"""

# Re-export gui_state from the legacy module for backwards compatibility
from ..state import gui_state
from .settings_state import SettingsFormState

__all__ = ["SettingsFormState", "gui_state"]
