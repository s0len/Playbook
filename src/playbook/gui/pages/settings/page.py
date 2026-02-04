"""
Main Settings page with tabbed navigation.

Provides the complete Settings GUI with sidebar navigation and form-based configuration.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from nicegui import ui

from ...settings_state.settings_state import SETTINGS_TABS, SettingsFormState
from ...state import gui_state
from .advanced import advanced_tab
from .general import general_tab
from .integrations import integrations_tab
from .notifications import notifications_tab
from .quality import quality_tab
from .watcher import watcher_tab

LOGGER = logging.getLogger(__name__)

# Tab renderers
TAB_RENDERERS = {
    "general": general_tab,
    "quality": quality_tab,
    "notifications": notifications_tab,
    "watcher": watcher_tab,
    "integrations": integrations_tab,
    "advanced": advanced_tab,
}


def settings_page() -> None:
    """Render the Settings page with tabbed navigation."""
    # Initialize settings state
    state = SettingsFormState()

    # Load current configuration
    if gui_state.config_path:
        state.load_from_yaml(gui_state.config_path)
    else:
        ui.notify("No configuration file loaded", type="warning")

    with ui.column().classes("w-full max-w-7xl mx-auto p-4 gap-4"):
        # Page header
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Settings").classes("text-3xl font-bold text-slate-800 dark:text-slate-100")

            # Action buttons
            with ui.row().classes("items-center gap-2"):
                # Modified indicator
                modified_indicator = ui.label("").classes("text-sm text-amber-600 dark:text-amber-400")

                def update_modified_indicator() -> None:
                    if state.is_modified:
                        modified_indicator.text = "Modified"
                        modified_indicator.classes(replace="text-sm text-amber-600 dark:text-amber-400")
                    else:
                        modified_indicator.text = ""

                # Register state callback
                state.register_callback(lambda t, d: update_modified_indicator())

                # Reset button
                ui.button(
                    "Reset",
                    icon="undo",
                    on_click=lambda: _reset_changes(state),
                ).props("outline")

                # Save button
                ui.button(
                    "Save",
                    icon="save",
                    on_click=lambda: _save_changes(state),
                ).props("color=primary")

        # Main content area
        with ui.row().classes("w-full gap-6"):
            # Sidebar navigation
            sidebar_container = ui.column().classes("w-48 shrink-0 gap-1")

            def render_sidebar() -> None:
                """Render the sidebar navigation."""
                sidebar_container.clear()
                with sidebar_container:
                    for tab_id, tab_label, tab_icon in SETTINGS_TABS:
                        _render_tab_button(state, tab_id, tab_label, tab_icon)

            # Content area
            content_container = ui.column().classes("flex-1 min-w-0")

            def render_content() -> None:
                """Render the content for the active tab."""
                content_container.clear()
                with content_container:
                    # Breadcrumb
                    active_label = next(
                        (label for tid, label, _ in SETTINGS_TABS if tid == state.active_tab), "Settings"
                    )
                    with ui.row().classes("items-center gap-2 mb-4"):
                        ui.label("Settings").classes("text-sm text-slate-500 dark:text-slate-400")
                        ui.icon("chevron_right").classes("text-slate-400")
                        ui.label(active_label).classes("text-sm font-medium text-slate-700 dark:text-slate-200")

                    # Tab content
                    renderer = TAB_RENDERERS.get(state.active_tab, general_tab)
                    renderer(state)

            # Initial render
            render_sidebar()
            render_content()

            # Update sidebar and content when tab changes
            def on_state_update(event_type: str, data) -> None:
                if event_type == "tab_changed":
                    render_sidebar()
                    render_content()

            state.register_callback(on_state_update)


def _render_tab_button(state: SettingsFormState, tab_id: str, tab_label: str, tab_icon: str) -> None:
    """Render a sidebar tab button."""
    is_active = state.active_tab == tab_id

    # Check if tab has modified fields
    tab_prefixes = {
        "general": ["settings.source_dir", "settings.destination_dir", "settings.cache_dir", "settings.dry_run"],
        "quality": ["settings.quality_profile"],
        "notifications": ["settings.notifications"],
        "watcher": ["settings.file_watcher"],
        "integrations": ["settings.plex_sync", "settings.kometa_trigger", "settings.tvsportsdb"],
    }

    has_modifications = any(
        any(path.startswith(prefix) for prefix in tab_prefixes.get(tab_id, [])) for path in state.modified_paths
    )

    # Button styling
    if is_active:
        btn_classes = "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
    else:
        btn_classes = "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"

    with (
        ui.button(on_click=lambda t=tab_id: state.set_active_tab(t))
        .classes(f"w-full justify-start px-3 py-2 rounded-lg {btn_classes}")
        .props("flat")
    ):
        with ui.row().classes("w-full items-center gap-3"):
            ui.icon(tab_icon).classes("text-lg w-5 text-center")
            ui.label(tab_label.upper()).classes("text-sm flex-1 text-left")
            if has_modifications:
                ui.badge("", color="amber").props("dense rounded")


def _save_changes(state: SettingsFormState) -> None:
    """Save configuration changes asynchronously."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    if not state.config_path:
        ui.notify("No configuration file to save", type="warning")
        return

    ui.notify("Saving configuration...", type="info")
    config_path = state.config_path

    def do_save():
        """Synchronous save operation."""
        # Create backup first
        try:
            backup_path = _create_backup(config_path)
            if backup_path:
                LOGGER.info("Created backup: %s", backup_path)
        except Exception as e:
            LOGGER.warning("Failed to create backup: %s", e)

        # Save
        if not state.save():
            return False, "Failed to save configuration"

        # Reload the processor config if available
        if gui_state.processor:
            try:
                from playbook.config import load_config

                new_config = load_config(config_path)
                gui_state.config = new_config
                LOGGER.info("Reloaded configuration after save")
            except Exception as e:
                LOGGER.warning("Failed to reload configuration: %s", e)
                return True, "Configuration saved but reload failed. Restart may be needed."

        return True, None

    async def async_save():
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            success, warning = await loop.run_in_executor(executor, do_save)
            if success:
                if warning:
                    ui.notify(warning, type="warning")
                else:
                    ui.notify("Configuration saved successfully", type="positive")
            else:
                ui.notify(warning or "Failed to save configuration", type="negative")
        except Exception as e:
            LOGGER.exception("Save failed: %s", e)
            ui.notify(f"Save failed: {e}", type="negative")
        finally:
            executor.shutdown(wait=False)

    asyncio.create_task(async_save())


def _reset_changes(state: SettingsFormState) -> None:
    """Reset all changes to original values."""
    state.reset_to_original()
    ui.notify("Changes reset to original values", type="info")
    ui.navigate.to("/config")  # Refresh page


def _create_backup(config_path: Path) -> Path | None:
    """Create a timestamped backup of the config file."""
    if not config_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = config_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    backup_name = f"{config_path.stem}_{timestamp}{config_path.suffix}"
    backup_path = backup_dir / backup_name

    shutil.copy2(config_path, backup_path)
    return backup_path
