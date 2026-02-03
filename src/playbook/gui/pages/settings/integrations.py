"""
Integrations settings tab for the Settings page.

Handles Plex, Kometa, and TVSportsDB integration settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ...components.settings import (
    list_editor,
    settings_card,
    settings_input,
    settings_select,
    settings_toggle,
)

if TYPE_CHECKING:
    from ...state.settings_state import SettingsFormState


def integrations_tab(state: SettingsFormState) -> None:
    """Render the Integrations settings tab.

    Args:
        state: Settings form state
    """
    with ui.column().classes("w-full gap-6"):
        # Plex Sync Section
        _render_plex_section(state)

        # Kometa Section
        _render_kometa_section(state)

        # TVSportsDB Section
        _render_tvsportsdb_section(state)


def _render_plex_section(state: SettingsFormState) -> None:
    """Render Plex sync settings."""
    plex_enabled = state.get_value("settings.plex_sync.enabled", False)

    with settings_card(
        "Plex Metadata Sync",
        icon="live_tv",
        description="Sync metadata to your Plex library",
    ):
        settings_toggle(
            state,
            "settings.plex_sync.enabled",
            "Enable Plex Sync",
            description="Automatically update Plex metadata after processing files",
            on_change=lambda v: ui.navigate.to("/config"),
        )

        with ui.column().classes("w-full gap-4 mt-4"):
            with ui.row().classes("w-full gap-4"):
                settings_input(
                    state,
                    "settings.plex_sync.url",
                    "Plex URL",
                    description="URL of your Plex server",
                    placeholder="http://localhost:32400",
                    disabled=not plex_enabled,
                    width="flex-1",
                )
                settings_input(
                    state,
                    "settings.plex_sync.token",
                    "Plex Token",
                    description="Your Plex authentication token",
                    placeholder="xxxxxxxxxxxx",
                    input_type="password",
                    disabled=not plex_enabled,
                    width="w-48",
                )

            with ui.row().classes("w-full gap-4"):
                settings_input(
                    state,
                    "settings.plex_sync.library_id",
                    "Library ID",
                    description="Numeric ID of the library to sync",
                    placeholder="1",
                    disabled=not plex_enabled,
                    width="w-32",
                )
                settings_input(
                    state,
                    "settings.plex_sync.library_name",
                    "Library Name",
                    description="Alternative: use library name instead of ID",
                    placeholder="Sports",
                    disabled=not plex_enabled,
                    width="flex-1",
                )

            with ui.row().classes("w-full gap-4"):
                settings_input(
                    state,
                    "settings.plex_sync.timeout",
                    "Timeout (seconds)",
                    description="API request timeout",
                    input_type="number",
                    placeholder="15",
                    disabled=not plex_enabled,
                    width="w-32",
                )
                settings_input(
                    state,
                    "settings.plex_sync.scan_wait",
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
                    "settings.plex_sync.force",
                    "Force Sync",
                    description="Update all metadata, not just new items",
                    disabled=not plex_enabled,
                )
                settings_toggle(
                    state,
                    "settings.plex_sync.dry_run",
                    "Dry Run",
                    description="Preview changes without applying",
                    disabled=not plex_enabled,
                )
                settings_toggle(
                    state,
                    "settings.plex_sync.lock_poster_fields",
                    "Lock Poster Fields",
                    description="Prevent Plex from overwriting posters",
                    disabled=not plex_enabled,
                )

            # Sports filter
            list_editor(
                state,
                "settings.plex_sync.sports",
                "Sports Filter",
                description="Only sync these sports (empty = all sports)",
                placeholder="f1",
                disabled=not plex_enabled,
            )


def _render_kometa_section(state: SettingsFormState) -> None:
    """Render Kometa trigger settings."""
    kometa_enabled = state.get_value("settings.kometa_trigger.enabled", False)
    kometa_mode = state.get_value("settings.kometa_trigger.mode", "kubernetes")

    with settings_card(
        "Kometa Trigger",
        icon="movie_filter",
        description="Trigger Kometa runs after processing",
        collapsible=True,
        default_expanded=kometa_enabled,
    ):
        settings_toggle(
            state,
            "settings.kometa_trigger.enabled",
            "Enable Kometa Trigger",
            description="Automatically run Kometa after processing new files",
            on_change=lambda v: ui.navigate.to("/config"),
        )

        with ui.column().classes("w-full gap-4 mt-4"):
            settings_select(
                state,
                "settings.kometa_trigger.mode",
                "Mode",
                options=["kubernetes", "docker"],
                description="How to trigger Kometa",
                disabled=not kometa_enabled,
                width="w-48",
            )

            # Kubernetes-specific settings
            if kometa_mode == "kubernetes":
                with ui.row().classes("w-full gap-4"):
                    settings_input(
                        state,
                        "settings.kometa_trigger.namespace",
                        "Namespace",
                        placeholder="media",
                        disabled=not kometa_enabled,
                        width="w-32",
                    )
                    settings_input(
                        state,
                        "settings.kometa_trigger.cronjob_name",
                        "CronJob Name",
                        placeholder="kometa-sport",
                        disabled=not kometa_enabled,
                        width="flex-1",
                    )
                    settings_input(
                        state,
                        "settings.kometa_trigger.job_name_prefix",
                        "Job Prefix",
                        placeholder="kometa-sport-triggered-by-playbook",
                        disabled=not kometa_enabled,
                        width="flex-1",
                    )

            # Docker-specific settings
            elif kometa_mode == "docker":
                settings_input(
                    state,
                    "settings.kometa_trigger.docker_binary",
                    "Docker Binary",
                    placeholder="docker",
                    disabled=not kometa_enabled,
                )
                settings_input(
                    state,
                    "settings.kometa_trigger.docker_image",
                    "Docker Image",
                    placeholder="kometateam/kometa",
                    disabled=not kometa_enabled,
                )
                settings_input(
                    state,
                    "settings.kometa_trigger.docker_config_path",
                    "Config Path",
                    placeholder="/path/to/kometa/config",
                    disabled=not kometa_enabled,
                )
                settings_input(
                    state,
                    "settings.kometa_trigger.docker_libraries",
                    "Libraries",
                    description="Comma-separated library IDs",
                    placeholder="1,2",
                    disabled=not kometa_enabled,
                )


def _render_tvsportsdb_section(state: SettingsFormState) -> None:
    """Render TVSportsDB API settings."""
    with settings_card(
        "TVSportsDB API",
        icon="sports",
        description="Configure metadata API connection",
        collapsible=True,
        default_expanded=False,
    ):
        with ui.row().classes("w-full gap-4"):
            settings_input(
                state,
                "settings.tvsportsdb.base_url",
                "API URL",
                description="TVSportsDB API base URL",
                placeholder="http://localhost:8000",
                width="flex-1",
            )

        with ui.row().classes("w-full gap-4"):
            settings_input(
                state,
                "settings.tvsportsdb.ttl_hours",
                "Cache TTL (hours)",
                description="How long to cache metadata",
                input_type="number",
                placeholder="12",
                width="w-32",
            )
            settings_input(
                state,
                "settings.tvsportsdb.timeout",
                "Timeout (seconds)",
                description="API request timeout",
                input_type="number",
                placeholder="30",
                width="w-32",
            )
