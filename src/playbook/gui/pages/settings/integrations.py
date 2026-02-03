"""
Integrations settings tab for the Settings page.

Handles Plex integration settings.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from nicegui import ui

from ...components.settings import (
    list_editor,
    settings_card,
    settings_input,
    settings_toggle,
)

if TYPE_CHECKING:
    from ...settings_state.settings_state import SettingsFormState


def _get_env_placeholder(env_var: str, default: str, mask: bool = False) -> str:
    """Get placeholder text showing env var value if set."""
    value = os.environ.get(env_var)
    if value:
        if mask:
            return f"From {env_var}: {'*' * min(8, len(value))}"
        return f"From {env_var}: {value}"
    return default


def integrations_tab(state: SettingsFormState) -> None:
    """Render the Integrations settings tab.

    Args:
        state: Settings form state
    """
    with ui.column().classes("w-full gap-6"):
        # Plex Library Scan Section
        _render_plex_scan_section(state)

        # Plex Metadata Sync Section
        _render_plex_section(state)


def _has_plex_scan_target(state: SettingsFormState) -> bool:
    """Check if a plex_scan notification target exists."""
    targets = state.get_value("settings.notifications.targets", []) or []
    return any(t.get("type") in ("plex_scan", "plex") for t in targets if isinstance(t, dict))


def _get_plex_scan_target(state: SettingsFormState) -> dict | None:
    """Get the plex_scan notification target if it exists."""
    targets = state.get_value("settings.notifications.targets", []) or []
    for t in targets:
        if isinstance(t, dict) and t.get("type") in ("plex_scan", "plex"):
            return t
    return None


def _add_plex_scan_target(state: SettingsFormState) -> None:
    """Add a plex_scan notification target."""
    targets = state.get_value("settings.notifications.targets", []) or []
    if not isinstance(targets, list):
        targets = []

    # Don't add if already exists
    if _has_plex_scan_target(state):
        return

    # Add new plex_scan target (uses env vars by default)
    targets.append({"type": "plex_scan", "enabled": True})
    state.set_value("settings.notifications.targets", targets)


def _remove_plex_scan_target(state: SettingsFormState) -> None:
    """Remove the plex_scan notification target."""
    targets = state.get_value("settings.notifications.targets", []) or []
    if not isinstance(targets, list):
        return

    # Filter out plex_scan targets
    new_targets = [t for t in targets if not (isinstance(t, dict) and t.get("type") in ("plex_scan", "plex"))]
    state.set_value("settings.notifications.targets", new_targets)


def _render_plex_scan_section(state: SettingsFormState) -> None:
    """Render Plex library scan settings."""
    with settings_card(
        "Plex Library Scan",
        icon="refresh",
        description="Trigger Plex to scan for new files",
    ):
        # Check for env vars
        has_plex_env = any(os.environ.get(v) for v in ["PLEX_URL", "PLEX_TOKEN"])
        scan_enabled = _has_plex_scan_target(state)

        def on_scan_toggle(enabled: bool) -> None:
            if enabled:
                _add_plex_scan_target(state)
            else:
                _remove_plex_scan_target(state)

        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-1"):
                ui.label("Enable Plex Scan").classes("text-sm font-medium text-slate-700 dark:text-slate-200")
                ui.label("Trigger partial library scan when files are linked").classes(
                    "text-xs text-slate-500 dark:text-slate-400"
                )
            ui.switch(value=scan_enabled, on_change=lambda e: on_scan_toggle(e.value))

        if has_plex_env:
            with ui.row().classes("w-full items-center gap-2 p-2 rounded bg-green-50 dark:bg-green-900/20 mt-2"):
                ui.icon("check_circle").classes("text-green-500")
                ui.label("Will use PLEX_URL and PLEX_TOKEN from environment").classes(
                    "text-sm text-green-700 dark:text-green-300"
                )
        elif not scan_enabled:
            with ui.row().classes("w-full items-center gap-2 p-2 rounded bg-amber-50 dark:bg-amber-900/20 mt-2"):
                ui.icon("warning").classes("text-amber-500")
                ui.label("Set PLEX_URL and PLEX_TOKEN environment variables, or configure in Notifications").classes(
                    "text-sm text-amber-700 dark:text-amber-300"
                )


def _render_plex_section(state: SettingsFormState) -> None:
    """Render Plex metadata sync settings."""
    # Container for dynamic content that depends on enabled state
    container = ui.column().classes("w-full gap-6")

    def render_plex_content() -> None:
        """Render the plex section content."""
        container.clear()
        plex_enabled = state.get_value("settings.plex_metadata_sync.enabled", False)

        with container:
            with settings_card(
                "Plex Metadata Sync",
                icon="live_tv",
                description="Sync metadata to your Plex library",
            ):

                def on_enable_change(enabled: bool) -> None:
                    # Re-render to update disabled states
                    render_plex_content()

                settings_toggle(
                    state,
                    "settings.plex_metadata_sync.enabled",
                    "Enable Plex Sync",
                    description="Automatically update Plex metadata after processing files",
                    on_change=on_enable_change,
                )

                # Check for env vars
                has_plex_env = any(os.environ.get(v) for v in ["PLEX_URL", "PLEX_TOKEN"])
                if has_plex_env and not state.get_value("settings.plex_metadata_sync.url"):
                    with ui.row().classes("w-full items-center gap-2 p-2 rounded bg-blue-50 dark:bg-blue-900/20"):
                        ui.icon("info").classes("text-blue-500")
                        ui.label("Plex settings detected from environment variables").classes(
                            "text-sm text-blue-700 dark:text-blue-300"
                        )

                with ui.column().classes("w-full gap-4 mt-4"):
                    with ui.row().classes("w-full gap-4"):
                        settings_input(
                            state,
                            "settings.plex_metadata_sync.url",
                            "Plex URL",
                            description="URL of your Plex server",
                            placeholder=_get_env_placeholder("PLEX_URL", "http://localhost:32400"),
                            disabled=not plex_enabled,
                            width="flex-1",
                        )
                        settings_input(
                            state,
                            "settings.plex_metadata_sync.token",
                            "Plex Token",
                            description="Your Plex authentication token",
                            placeholder=_get_env_placeholder("PLEX_TOKEN", "xxxxxxxxxxxx", mask=True),
                            input_type="password",
                            disabled=not plex_enabled,
                            width="w-48",
                        )

                    with ui.row().classes("w-full gap-4"):
                        settings_input(
                            state,
                            "settings.plex_metadata_sync.library_id",
                            "Library ID",
                            description="Numeric ID of the library to sync",
                            placeholder=_get_env_placeholder("PLEX_LIBRARY_ID", "1"),
                            disabled=not plex_enabled,
                            width="w-32",
                        )
                        settings_input(
                            state,
                            "settings.plex_metadata_sync.library_name",
                            "Library Name",
                            description="Alternative: use library name instead of ID",
                            placeholder=_get_env_placeholder("PLEX_LIBRARY_NAME", "Sports"),
                            disabled=not plex_enabled,
                            width="flex-1",
                        )

                    with ui.row().classes("w-full gap-4"):
                        settings_input(
                            state,
                            "settings.plex_metadata_sync.timeout",
                            "Timeout (seconds)",
                            description="API request timeout",
                            input_type="number",
                            placeholder="15",
                            disabled=not plex_enabled,
                            width="w-32",
                        )
                        settings_input(
                            state,
                            "settings.plex_metadata_sync.scan_wait",
                            "Scan Wait (seconds)",
                            description="Wait time after triggering scan",
                            input_type="number",
                            placeholder="5",
                            disabled=not plex_enabled,
                            width="w-32",
                        )

                    with ui.row().classes("w-full gap-4"):
                        settings_toggle(
                            state,
                            "settings.plex_metadata_sync.force",
                            "Force Sync",
                            description="Update all metadata, not just new items",
                            disabled=not plex_enabled,
                        )
                        settings_toggle(
                            state,
                            "settings.plex_metadata_sync.dry_run",
                            "Dry Run",
                            description="Preview changes without applying",
                            disabled=not plex_enabled,
                        )
                        settings_toggle(
                            state,
                            "settings.plex_metadata_sync.lock_poster_fields",
                            "Lock Poster Fields",
                            description="Prevent Plex from overwriting posters",
                            disabled=not plex_enabled,
                        )

                    # Sports filter
                    list_editor(
                        state,
                        "settings.plex_metadata_sync.sports",
                        "Sports Filter",
                        description="Only sync these sports (empty = all sports)",
                        placeholder="f1",
                        disabled=not plex_enabled,
                    )

    # Initial render
    render_plex_content()
