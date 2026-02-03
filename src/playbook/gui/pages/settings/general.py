"""
General settings tab for the Settings page.

Handles directories, execution settings, and template configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ...components.settings import (
    settings_card,
    settings_input,
    settings_path_input,
    settings_select,
    settings_toggle,
)

if TYPE_CHECKING:
    from ...settings_state.settings_state import SettingsFormState


def general_tab(state: SettingsFormState) -> None:
    """Render the General settings tab.

    Args:
        state: Settings form state
    """
    with ui.column().classes("w-full gap-6"):
        # Directories Section
        with settings_card("Directories", icon="folder", description="Configure source, destination, and cache paths"):
            settings_path_input(
                state,
                "settings.source_dir",
                "Source Directory",
                description="Directory containing media files to process",
                required=True,
            )
            settings_path_input(
                state,
                "settings.destination_dir",
                "Destination Directory",
                description="Directory where organized files will be linked",
                required=True,
            )
            settings_path_input(
                state,
                "settings.cache_dir",
                "Cache Directory",
                description="Directory for storing metadata cache and processing state",
                required=True,
            )

        # Execution Settings Section
        with settings_card("Execution", icon="settings", description="Control how files are processed"):
            with ui.row().classes("w-full gap-6"):
                with ui.column().classes("flex-1 gap-4"):
                    settings_toggle(
                        state,
                        "settings.dry_run",
                        "Dry Run",
                        description="Simulate processing without creating links",
                    )
                    settings_toggle(
                        state,
                        "settings.skip_existing",
                        "Skip Existing",
                        description="Skip files that already have a destination link",
                    )

                with ui.column().classes("flex-1 gap-4"):
                    settings_select(
                        state,
                        "settings.link_mode",
                        "Link Mode",
                        options=["hardlink", "symlink", "copy"],
                        description="How to create destination files",
                    )

        # Template Settings Section
        with settings_card(
            "Templates",
            icon="text_fields",
            description="Customize destination path formatting",
            collapsible=True,
            default_expanded=False,
        ):
            settings_input(
                state,
                "settings.default_destination.root_template",
                "Root Template",
                description="Template for show directory name",
                placeholder="{show_title}",
            )
            settings_input(
                state,
                "settings.default_destination.season_dir_template",
                "Season Directory Template",
                description="Template for season directory name",
                placeholder="{season_number:02d} {season_title}",
            )
            settings_input(
                state,
                "settings.default_destination.episode_template",
                "Episode Filename Template",
                description="Template for episode filename",
                placeholder="{show_title} - S{season_number:02d}E{episode_number:02d} - {episode_title}.{extension}",
            )

            # Template variable reference
            with ui.expansion(text="Template Variables Reference", icon="help").props("dense").classes("mt-2"):
                with ui.column().classes("gap-1 text-xs font-mono"):
                    ui.label("{show_title} - Show name").classes("text-slate-600 dark:text-slate-400")
                    ui.label("{season_number} - Season number (use :02d for padding)").classes(
                        "text-slate-600 dark:text-slate-400"
                    )
                    ui.label("{season_title} - Season title").classes("text-slate-600 dark:text-slate-400")
                    ui.label("{episode_number} - Episode number (use :02d for padding)").classes(
                        "text-slate-600 dark:text-slate-400"
                    )
                    ui.label("{episode_title} - Episode title").classes("text-slate-600 dark:text-slate-400")
                    ui.label("{extension} - Original file extension").classes("text-slate-600 dark:text-slate-400")
                    ui.label("{session} - Matched session name").classes("text-slate-600 dark:text-slate-400")
