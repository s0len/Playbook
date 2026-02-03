"""
File Watcher settings tab for the Settings page.

Handles file system monitoring configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ...components.settings import (
    list_editor,
    settings_card,
    settings_input,
    settings_toggle,
)
from ...components.settings.list_editor import glob_pattern_editor

if TYPE_CHECKING:
    from ...settings_state.settings_state import SettingsFormState


def watcher_tab(state: SettingsFormState) -> None:
    """Render the File Watcher settings tab.

    Args:
        state: Settings form state
    """
    # Get enabled state for conditional rendering
    watcher_enabled = state.get_value("settings.file_watcher.enabled", False)

    with ui.column().classes("w-full gap-6"):
        # Enable Watcher Section
        with settings_card(
            "File Watcher",
            icon="visibility",
            description="Monitor directories for new files",
        ):
            settings_toggle(
                state,
                "settings.file_watcher.enabled",
                "Enable File Watcher",
                description="Automatically process new files as they appear",
                on_change=lambda v: ui.navigate.to("/config"),  # Refresh to update disabled states
            )

            if watcher_enabled:
                with ui.row().classes("w-full items-center gap-2 mt-2 p-2 bg-green-50 dark:bg-green-900/20 rounded"):
                    ui.icon("check_circle").classes("text-green-600 dark:text-green-400")
                    ui.label("File watcher is enabled and will monitor for changes").classes(
                        "text-sm text-green-700 dark:text-green-300"
                    )
            else:
                with ui.row().classes("w-full items-center gap-2 mt-2 p-2 bg-slate-50 dark:bg-slate-800 rounded"):
                    ui.icon("info").classes("text-slate-500")
                    ui.label("Enable file watcher to automatically process new files").classes(
                        "text-sm text-slate-600 dark:text-slate-400"
                    )

        # Watch Paths Section
        with settings_card(
            "Watch Paths",
            icon="folder_open",
            description="Directories to monitor for new files",
            disabled=not watcher_enabled,
        ):
            list_editor(
                state,
                "settings.file_watcher.paths",
                "Paths",
                description="List of directories to watch (leave empty to use source_dir)",
                placeholder="/path/to/watch",
                disabled=not watcher_enabled,
            )

        # Include/Exclude Patterns Section
        with settings_card(
            "File Patterns",
            icon="filter_list",
            description="Control which files trigger processing",
            disabled=not watcher_enabled,
        ):
            with ui.row().classes("w-full gap-6"):
                with ui.column().classes("flex-1"):
                    glob_pattern_editor(
                        state,
                        "settings.file_watcher.include",
                        "Include Patterns",
                        description="Only process files matching these patterns (empty = all files)",
                        disabled=not watcher_enabled,
                    )

                with ui.column().classes("flex-1"):
                    glob_pattern_editor(
                        state,
                        "settings.file_watcher.ignore",
                        "Ignore Patterns",
                        description="Skip files matching these patterns",
                        disabled=not watcher_enabled,
                    )

        # Timing Settings Section
        with settings_card(
            "Timing",
            icon="timer",
            description="Control processing timing and delays",
            collapsible=True,
            default_expanded=watcher_enabled,
            disabled=not watcher_enabled,
        ):
            with ui.row().classes("w-full gap-4"):
                settings_input(
                    state,
                    "settings.file_watcher.debounce_seconds",
                    "Debounce (seconds)",
                    description="Wait time after file change before processing",
                    input_type="number",
                    placeholder="5.0",
                    disabled=not watcher_enabled,
                    width="w-48",
                )
                settings_input(
                    state,
                    "settings.file_watcher.reconcile_interval",
                    "Reconcile Interval (seconds)",
                    description="How often to check for missed files",
                    input_type="number",
                    placeholder="900",
                    disabled=not watcher_enabled,
                    width="w-48",
                )

            # Explanation
            with ui.column().classes("mt-4 gap-1"):
                ui.label("Timing Explained:").classes("text-sm font-medium text-slate-700 dark:text-slate-300")
                with ui.column().classes("gap-1 text-xs text-slate-600 dark:text-slate-400"):
                    ui.label(
                        "• Debounce: Prevents processing the same file multiple times during active copying/downloading"
                    )
                    ui.label(
                        "• Reconcile: Periodically scans for files that may have been missed by real-time monitoring"
                    )
                    ui.label("• Lower debounce = faster processing but may catch incomplete files")
                    ui.label("• Higher reconcile = less CPU usage but delayed detection of missed files")
