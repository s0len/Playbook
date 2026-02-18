"""
Integrations settings tab for the Settings page.

Handles Plex and Autoscan integration settings using the new
settings.integrations structure.
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
        # Plex Integration Section
        _render_plex_section(state)

        # Autoscan Integration Section
        _render_autoscan_section(state)


def _render_plex_section(state: SettingsFormState) -> None:
    """Render Plex integration settings."""
    container = ui.column().classes("w-full gap-6")

    def render_plex_content() -> None:
        """Render the plex section content."""
        container.clear()

        with container:
            with settings_card(
                "Plex Integration",
                icon="live_tv",
                description="Connect to your Plex server for library scans and metadata sync",
            ):
                # Check for env vars
                has_plex_env = any(os.environ.get(v) for v in ["PLEX_URL", "PLEX_TOKEN"])
                if has_plex_env:
                    with ui.row().classes("w-full items-center gap-2 p-2 rounded bg-blue-50 dark:bg-blue-900/20 mb-4"):
                        ui.icon("info").classes("text-blue-500")
                        ui.label("Plex settings detected from environment variables").classes(
                            "text-sm text-blue-700 dark:text-blue-300"
                        )

                # Connection Settings
                ui.label("Connection Settings").classes("text-sm font-semibold text-slate-600 dark:text-slate-300 mb-2")

                with ui.column().classes("w-full gap-4"):
                    with ui.row().classes("w-full gap-4"):
                        settings_input(
                            state,
                            "settings.integrations.plex.url",
                            "Plex URL",
                            description="URL of your Plex server",
                            placeholder=_get_env_placeholder("PLEX_URL", "http://localhost:32400"),
                            width="flex-1",
                        )
                        settings_input(
                            state,
                            "settings.integrations.plex.token",
                            "Plex Token",
                            description="Your Plex authentication token",
                            placeholder=_get_env_placeholder("PLEX_TOKEN", "xxxxxxxxxxxx", mask=True),
                            input_type="password",
                            width="w-48",
                        )

                    with ui.row().classes("w-full gap-4"):
                        settings_input(
                            state,
                            "settings.integrations.plex.library_id",
                            "Library ID",
                            description="Numeric ID of the library",
                            placeholder=_get_env_placeholder("PLEX_LIBRARY_ID", "1"),
                            width="w-32",
                        )
                        settings_input(
                            state,
                            "settings.integrations.plex.library_name",
                            "Library Name",
                            description="Or use library name instead of ID",
                            placeholder=_get_env_placeholder("PLEX_LIBRARY_NAME", "Sports"),
                            width="flex-1",
                        )

            # Scan on Activity Section
            _render_plex_scan_section(state, render_plex_content)

            # Metadata Sync Section
            _render_plex_metadata_sync_section(state, render_plex_content)

    render_plex_content()


def _render_plex_scan_section(state: SettingsFormState, refresh_callback) -> None:
    """Render Plex library scan on activity settings."""
    scan_enabled = state.get_value("settings.integrations.plex.scan_on_activity.enabled", False)

    with settings_card(
        "Library Scan on Activity",
        icon="refresh",
        description="Trigger Plex to scan for new files when they are linked",
    ):

        def on_scan_toggle(enabled: bool) -> None:
            refresh_callback()

        settings_toggle(
            state,
            "settings.integrations.plex.scan_on_activity.enabled",
            "Enable Scan on Activity",
            description="Automatically trigger partial library scans when files are processed",
            on_change=on_scan_toggle,
        )

        if scan_enabled:
            ui.separator().classes("my-4")
            ui.label("Path Rewriting").classes("text-sm font-semibold text-slate-600 dark:text-slate-300 mb-2")
            ui.label("Map paths if Plex sees files at different paths than Playbook").classes(
                "text-xs text-slate-500 dark:text-slate-400 mb-2"
            )

            _render_rewrite_rules(state, "settings.integrations.plex.scan_on_activity.rewrite")


def _render_plex_metadata_sync_section(state: SettingsFormState, refresh_callback) -> None:
    """Render Plex metadata sync settings."""
    sync_enabled = state.get_value("settings.integrations.plex.metadata_sync.enabled", False)

    with settings_card(
        "Metadata Sync",
        icon="cloud_sync",
        description="Push titles, summaries, and posters from TVSportsDB to Plex",
    ):

        def on_sync_toggle(enabled: bool) -> None:
            refresh_callback()

        settings_toggle(
            state,
            "settings.integrations.plex.metadata_sync.enabled",
            "Enable Metadata Sync",
            description="Automatically sync metadata after processing files",
            on_change=on_sync_toggle,
        )

        if sync_enabled:
            ui.separator().classes("my-4")

            with ui.column().classes("w-full gap-4"):
                with ui.row().classes("w-full gap-4"):
                    settings_input(
                        state,
                        "settings.integrations.plex.metadata_sync.timeout",
                        "Timeout (seconds)",
                        description="API request timeout",
                        input_type="number",
                        placeholder="15",
                        width="w-32",
                    )
                    settings_input(
                        state,
                        "settings.integrations.plex.metadata_sync.scan_wait",
                        "Scan Wait (seconds)",
                        description="Wait for Plex to scan before syncing",
                        input_type="number",
                        placeholder="5",
                        width="w-32",
                    )

                with ui.row().classes("w-full gap-4"):
                    settings_toggle(
                        state,
                        "settings.integrations.plex.metadata_sync.force",
                        "Force Sync",
                        description="Update all metadata, not just changed items",
                    )
                    settings_toggle(
                        state,
                        "settings.integrations.plex.metadata_sync.dry_run",
                        "Dry Run",
                        description="Preview changes without applying",
                    )
                    settings_toggle(
                        state,
                        "settings.integrations.plex.metadata_sync.lock_poster_fields",
                        "Lock Poster Fields",
                        description="Prevent Plex from overwriting posters",
                    )

                # Sports filter
                list_editor(
                    state,
                    "settings.integrations.plex.metadata_sync.sports",
                    "Sports Filter",
                    description="Only sync these sports (empty = all sports)",
                    placeholder="formula1",
                )


def _render_autoscan_section(state: SettingsFormState) -> None:
    """Render Autoscan integration settings."""
    container = ui.column().classes("w-full gap-6")

    def render_autoscan_content() -> None:
        """Render the autoscan section content."""
        container.clear()
        autoscan_enabled = state.get_value("settings.integrations.autoscan.enabled", False)

        with container:
            with settings_card(
                "Autoscan Integration",
                icon="radar",
                description="Use Autoscan for more efficient library scanning",
            ):

                def on_enable_change(enabled: bool) -> None:
                    render_autoscan_content()

                settings_toggle(
                    state,
                    "settings.integrations.autoscan.enabled",
                    "Enable Autoscan",
                    description="Use Autoscan instead of direct Plex API for library scans",
                    on_change=on_enable_change,
                )

                if autoscan_enabled:
                    ui.separator().classes("my-4")

                    with ui.column().classes("w-full gap-4"):
                        with ui.row().classes("w-full gap-4"):
                            settings_input(
                                state,
                                "settings.integrations.autoscan.url",
                                "Autoscan URL",
                                description="URL of your Autoscan server",
                                placeholder="http://localhost:3030",
                                width="flex-1",
                            )
                            settings_input(
                                state,
                                "settings.integrations.autoscan.trigger",
                                "Trigger Endpoint",
                                description="Trigger type (manual, sonarr, etc.)",
                                placeholder="manual",
                                width="w-32",
                            )

                        with ui.row().classes("w-full gap-4"):
                            settings_input(
                                state,
                                "settings.integrations.autoscan.username",
                                "Username",
                                description="Basic auth username (optional)",
                                placeholder="",
                                width="flex-1",
                            )
                            settings_input(
                                state,
                                "settings.integrations.autoscan.password",
                                "Password",
                                description="Basic auth password (optional)",
                                placeholder="",
                                input_type="password",
                                width="flex-1",
                            )

                        with ui.row().classes("w-full gap-4"):
                            settings_input(
                                state,
                                "settings.integrations.autoscan.timeout",
                                "Timeout (seconds)",
                                description="Request timeout",
                                input_type="number",
                                placeholder="10",
                                width="w-32",
                            )
                            settings_toggle(
                                state,
                                "settings.integrations.autoscan.verify_ssl",
                                "Verify SSL",
                                description="Verify SSL certificates",
                            )

                        ui.separator().classes("my-2")
                        ui.label("Path Rewriting").classes(
                            "text-sm font-semibold text-slate-600 dark:text-slate-300 mb-2"
                        )
                        ui.label("Map paths if Autoscan sees files at different paths than Playbook").classes(
                            "text-xs text-slate-500 dark:text-slate-400 mb-2"
                        )

                        _render_rewrite_rules(state, "settings.integrations.autoscan.rewrite")

    render_autoscan_content()


def _render_rewrite_rules(state: SettingsFormState, path: str) -> None:
    """Render path rewrite rules editor.

    Args:
        state: Settings form state
        path: Config path for the rewrite list (e.g., settings.integrations.plex.scan_on_activity.rewrite)
    """
    rules = state.get_value(path, []) or []
    if not isinstance(rules, list):
        rules = []

    rules_container = ui.column().classes("w-full gap-2")

    def refresh_rules() -> None:
        """Refresh the rules display."""
        rules_container.clear()
        current_rules = state.get_value(path, []) or []

        with rules_container:
            for idx, rule in enumerate(current_rules):
                if not isinstance(rule, dict):
                    continue
                from_val = rule.get("from", "")
                to_val = rule.get("to", "")

                with ui.row().classes("w-full items-center gap-2"):
                    from_input = (
                        ui.input(value=from_val, placeholder="/data/destination")
                        .classes("flex-1")
                        .props("dense outlined")
                    )
                    ui.icon("arrow_forward").classes("text-slate-400")
                    to_input = (
                        ui.input(value=to_val, placeholder="/mnt/plex/media").classes("flex-1").props("dense outlined")
                    )

                    def make_update_handler(index: int, from_inp, to_inp):
                        def update_rule(_) -> None:
                            current = state.get_value(path, []) or []
                            if index < len(current):
                                current[index] = {"from": from_inp.value, "to": to_inp.value}
                                state.set_value(path, current)

                        return update_rule

                    from_input.on("blur", make_update_handler(idx, from_input, to_input))
                    to_input.on("blur", make_update_handler(idx, from_input, to_input))

                    def make_delete_handler(index: int):
                        def delete_rule() -> None:
                            current = state.get_value(path, []) or []
                            if index < len(current):
                                current.pop(index)
                                state.set_value(path, current)
                                refresh_rules()

                        return delete_rule

                    ui.button(icon="delete", on_click=make_delete_handler(idx)).props("flat dense").classes(
                        "text-red-500"
                    )

            # Add new rule button
            def add_rule() -> None:
                current = state.get_value(path, []) or []
                current.append({"from": "", "to": ""})
                state.set_value(path, current)
                refresh_rules()

            ui.button("Add Rewrite Rule", icon="add", on_click=add_rule).props("flat dense").classes("mt-2")

    refresh_rules()
