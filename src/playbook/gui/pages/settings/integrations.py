"""
Integrations settings tab for the Settings page.

Uses a card + modal design consistent with notification targets.
Each integration (Plex, Autoscan) is a single card that opens
a modal editor with all its sub-features.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ...components.settings.integrations import integration_editor

if TYPE_CHECKING:
    from ...settings_state.settings_state import SettingsFormState


def integrations_tab(state: SettingsFormState) -> None:
    """Render the Integrations settings tab."""
    with ui.column().classes("w-full gap-6"):
        integration_editor(state)
