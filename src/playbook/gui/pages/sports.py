"""
Sports management page for the Playbook GUI.

Displays configured sports with match progress and provides:
- List view with progress tracking
- Detail view with season/episode breakdown
- Pattern tester tool
- Bulk actions for selected sports
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from nicegui import ui

from ..components import progress_bar, seasons_list, status_chip
from ..data import get_sport_detail, get_sports_overview
from ..state import gui_state

LOGGER = logging.getLogger(__name__)


def sports_page() -> None:
    """Render the sports management page with list view."""
    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-6"):
        # Page title
        ui.label("Sports").classes("text-3xl font-bold text-slate-800 dark:text-slate-100")

        # Sports table with progress
        with ui.card().classes("glass-card w-full"):
            with ui.row().classes("items-center justify-between mb-4"):
                ui.label("Configured Sports").classes("text-xl font-semibold text-slate-700 dark:text-slate-200")
                ui.button(icon="refresh", on_click=lambda: ui.navigate.to("/sports")).props("flat round dense").classes(
                    "text-slate-500"
                )

            _sports_table()

        # Pattern tester
        with ui.card().classes("glass-card w-full"):
            ui.label("Pattern Tester").classes("text-xl font-semibold text-slate-700 dark:text-slate-200 mb-3")
            _pattern_tester()


def sport_detail_page(sport_id: str) -> None:
    """Render the sport detail page with season/episode tracking.

    Args:
        sport_id: The sport identifier from the URL
    """
    # Load sport detail
    detail = get_sport_detail(sport_id)

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-6"):
        # Back button and header
        with ui.row().classes("w-full items-center gap-4"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/sports")).props("flat round").classes(
                "text-slate-600 dark:text-slate-400"
            )

            if detail:
                ui.label(detail.sport_name).classes("text-3xl font-bold text-slate-800 dark:text-slate-100")
            else:
                ui.label("Sport Not Found").classes("text-3xl font-bold text-slate-800 dark:text-slate-100")

        if not detail:
            with ui.card().classes("glass-card w-full"):
                ui.label(f"Sport '{sport_id}' not found in configuration.").classes(
                    "text-slate-600 dark:text-slate-400 py-4"
                )
            return

        # Overview card
        with ui.card().classes("glass-card w-full"):
            with ui.row().classes("w-full items-center justify-between flex-wrap gap-4"):
                # Info column
                with ui.column().classes("gap-1"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label("Show:").classes("text-sm text-slate-500 dark:text-slate-400")
                        ui.label(detail.show_slug).classes("text-sm font-mono text-slate-700 dark:text-slate-300")

                    with ui.row().classes("items-center gap-2"):
                        status_chip("enabled" if detail.enabled else "disabled")
                        ui.label(f"{detail.link_mode}").classes("text-sm text-slate-500 dark:text-slate-400")

                # Overall progress
                with ui.column().classes("gap-1 min-w-64"):
                    ui.label("Overall Progress").classes("text-sm text-slate-500 dark:text-slate-400")
                    with ui.row().classes("items-center gap-3 w-full"):
                        _progress_variant = _get_progress_variant(detail.overall_progress)
                        progress_bar(
                            detail.overall_progress,
                            variant=_progress_variant,
                            show_value=False,
                        )
                        ui.label(f"{detail.overall_matched}/{detail.overall_total}").classes(
                            "text-lg font-semibold text-slate-700 dark:text-slate-300"
                        )

        # Source Globs
        _source_globs_card(sport_id, detail)

        # Seasons
        with ui.card().classes("glass-card w-full"):
            ui.label("Seasons").classes("text-xl font-semibold text-slate-700 dark:text-slate-200 mb-4")
            seasons_list(detail.seasons, expand_recent=True)

        # Recent matches for this sport
        _recent_matches_card(sport_id)


def _get_progress_variant(progress: float) -> str:
    """Get progress bar variant based on progress value."""
    if progress >= 1.0:
        return "success"
    elif progress >= 0.5:
        return "info"
    elif progress > 0:
        return "warning"
    return "default"


def _toggle_sport_enabled_sync(sport_id: str, enabled: bool) -> bool:
    """Toggle a sport's enabled status in the config (synchronous implementation).

    Args:
        sport_id: The sport identifier
        enabled: New enabled state

    Returns:
        True if successful, False otherwise
    """
    from pathlib import Path

    import yaml

    if not gui_state.config_path:
        LOGGER.error("No config path available")
        return False

    try:
        config_path = Path(gui_state.config_path)
        content = config_path.read_text(encoding="utf-8")
        config = yaml.safe_load(content) or {}

        settings = config.get("settings", {})
        disabled_sports = set(settings.get("disabled_sports", []) or [])

        if enabled:
            # Remove from disabled list
            disabled_sports.discard(sport_id)
        else:
            # Add to disabled list
            disabled_sports.add(sport_id)

        settings["disabled_sports"] = sorted(disabled_sports)
        config["settings"] = settings

        # Write back
        config_path.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False))
        LOGGER.info("Updated sport %s enabled=%s", sport_id, enabled)

        # Reload config in processor
        if gui_state.processor:
            from playbook.config import AppConfig

            gui_state.config = AppConfig.load(config_path)
            gui_state.processor.config = gui_state.config

        return True
    except Exception as e:
        LOGGER.exception("Failed to toggle sport enabled: %s", e)
        return False


def _toggle_sport_enabled(sport_id: str, enabled: bool, sport_name: str = "") -> None:
    """Toggle a sport's enabled status asynchronously.

    Args:
        sport_id: The sport identifier
        enabled: New enabled state
        sport_name: Display name for notifications
    """

    async def async_toggle():
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            success = await loop.run_in_executor(
                executor, lambda: _toggle_sport_enabled_sync(sport_id, enabled)
            )
            if success:
                ui.notify(
                    f"{sport_name or sport_id} {'enabled' if enabled else 'disabled'}",
                    type="positive",
                )
                ui.navigate.to("/sports")
            else:
                ui.notify("Failed to update sport status", type="negative")
        except Exception as e:
            LOGGER.exception("Toggle sport async failed: %s", e)
            ui.notify("Failed to update sport status", type="negative")
        finally:
            executor.shutdown(wait=False)

    asyncio.create_task(async_toggle())


def _bulk_toggle_sports_sync(sport_ids: list[str], enabled: bool) -> bool:
    """Toggle multiple sports' enabled status at once.

    Args:
        sport_ids: List of sport identifiers
        enabled: New enabled state

    Returns:
        True if successful, False otherwise
    """
    from pathlib import Path

    import yaml

    if not gui_state.config_path:
        LOGGER.error("No config path available")
        return False

    try:
        config_path = Path(gui_state.config_path)
        content = config_path.read_text(encoding="utf-8")
        config = yaml.safe_load(content) or {}

        settings = config.get("settings", {})
        disabled_sports = set(settings.get("disabled_sports", []) or [])

        for sport_id in sport_ids:
            if enabled:
                disabled_sports.discard(sport_id)
            else:
                disabled_sports.add(sport_id)

        settings["disabled_sports"] = sorted(disabled_sports)
        config["settings"] = settings

        config_path.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False))
        LOGGER.info("Bulk updated %d sports enabled=%s", len(sport_ids), enabled)

        # Reload config
        if gui_state.processor:
            from playbook.config import AppConfig

            gui_state.config = AppConfig.load(config_path)
            gui_state.processor.config = gui_state.config

        return True
    except Exception as e:
        LOGGER.exception("Failed to bulk toggle sports: %s", e)
        return False


def _bulk_clear_history_sync(sport_ids: list[str]) -> int:
    """Clear processed records for multiple sports.

    Args:
        sport_ids: List of sport identifiers

    Returns:
        Total number of records deleted
    """
    if not gui_state.processed_store:
        return 0

    total_deleted = 0
    for sport_id in sport_ids:
        try:
            deleted = gui_state.processed_store.delete_by_sport(sport_id)
            total_deleted += deleted
            LOGGER.info("Cleared %d records for sport %s", deleted, sport_id)
        except Exception as e:
            LOGGER.warning("Failed to clear records for %s: %s", sport_id, e)

    return total_deleted


def _sports_table() -> None:
    """Create the sports overview table with progress and bulk actions."""
    overviews = get_sports_overview()

    if not overviews:
        ui.label("No sports configured").classes("text-slate-500 dark:text-slate-400 italic py-4")
        return

    # State for tracking selected rows
    selection_state = {"selected": []}

    # Action bar (hidden by default, shown above table when items selected)
    action_bar = ui.row().classes("w-full items-center gap-2 p-3 mb-4 bg-slate-100 dark:bg-slate-800 rounded-lg")
    action_bar.set_visibility(False)

    with action_bar:
        selection_label = ui.label("0 selected").classes("font-medium text-slate-700 dark:text-slate-200 mr-4")

        ui.button("Enable", icon="check_circle", on_click=lambda: _bulk_action("enable", selection_state["selected"])).props(
            "flat dense color=positive"
        )
        ui.button("Disable", icon="cancel", on_click=lambda: _bulk_action("disable", selection_state["selected"])).props(
            "flat dense color=warning"
        )

        ui.separator().props("vertical").classes("mx-2")

        ui.button("Clear History", icon="delete_sweep", on_click=lambda: _bulk_action("clear_history", selection_state["selected"])).props(
            "flat dense color=negative"
        )
        ui.button("Reprocess", icon="refresh", on_click=lambda: _bulk_action("reprocess", selection_state["selected"])).props(
            "flat dense color=info"
        )

        ui.space()

        clear_btn = ui.button("Clear Selection", icon="close", on_click=lambda: table.run_method("clearSelection")).props(
            "flat dense"
        ).classes("text-slate-500")

    # Create table with custom rendering
    columns = [
        {"name": "status", "label": "Status", "field": "status", "align": "center"},
        {"name": "name", "label": "Sport", "field": "name", "align": "left", "sortable": True},
        {"name": "slug", "label": "Show Slug", "field": "slug", "align": "left"},
        {"name": "patterns", "label": "Patterns", "field": "patterns", "align": "center"},
        {"name": "matched", "label": "Matched", "field": "matched", "align": "center", "sortable": True},
        {"name": "mode", "label": "Mode", "field": "mode", "align": "center"},
    ]

    rows = []
    for overview in overviews:
        rows.append(
            {
                "id": overview.sport_id,
                "status": "Enabled" if overview.enabled else "Disabled",
                "name": overview.sport_name,
                "slug": overview.show_slug,
                "patterns": overview.pattern_count,
                "matched": overview.matched_count,
                "mode": overview.link_mode,
            }
        )

    table = ui.table(
        columns=columns,
        rows=rows,
        row_key="id",
        selection="multiple",  # Enable multi-select
    ).classes("w-full modern-table")

    # Status toggle slot
    table.add_slot(
        "body-cell-status",
        """
        <q-td :props="props">
            <q-toggle
                :model-value="props.value === 'Enabled'"
                @update:model-value="() => $parent.$emit('toggle_status', props.row)"
                :color="props.value === 'Enabled' ? 'positive' : 'grey'"
                :label="props.value"
                dense
            />
        </q-td>
        """,
    )

    def on_toggle_status(e) -> None:
        """Handle status toggle."""
        row = e.args
        sport_id = row.get("id")
        sport_name = row.get("name")
        current_status = row.get("status")
        new_enabled = current_status != "Enabled"

        ui.notify(f"Updating {sport_name}...", type="info")
        _toggle_sport_enabled(sport_id, new_enabled, sport_name=sport_name)

    table.on("toggle_status", on_toggle_status)

    # Make name clickable
    table.add_slot(
        "body-cell-name",
        """
        <q-td :props="props">
            <a :href="'/sports/' + props.row.id"
               class="text-blue-600 dark:text-blue-400 hover:underline font-medium">
                {{ props.value }}
            </a>
        </q-td>
        """,
    )

    # Matched count with icon
    table.add_slot(
        "body-cell-matched",
        """
        <q-td :props="props">
            <div class="flex items-center gap-1 justify-center">
                <q-icon name="check_circle" size="xs" :color="props.value > 0 ? 'positive' : 'grey'" />
                <span>{{ props.value }}</span>
            </div>
        </q-td>
        """,
    )

    # Mode chip slot
    table.add_slot(
        "body-cell-mode",
        """
        <q-td :props="props">
            <q-chip
                :icon="props.value === 'hardlink' ? 'link' : props.value === 'copy' ? 'file_copy' : 'shortcut'"
                size="sm"
                dense
            >
                {{ props.value }}
            </q-chip>
        </q-td>
        """,
    )

    # Row click handler (navigate to detail, but not when clicking checkbox)
    table.on("row-click", lambda e: ui.navigate.to(f"/sports/{e.args[1]['id']}"))

    # Track selection changes
    def on_selection(e) -> None:
        selection_state["selected"] = [row["id"] for row in e.args["rows"]] if e.args else []
        update_action_bar()

    table.on("selection", on_selection)

    def update_action_bar() -> None:
        """Update action bar visibility and selection count."""
        count = len(selection_state["selected"])
        if count > 0:
            action_bar.set_visibility(True)
            selection_label.text = f"{count} selected"
        else:
            action_bar.set_visibility(False)


def _bulk_action(action: str, sport_ids: list[str]) -> None:
    """Execute a bulk action on selected sports.

    Args:
        action: The action to perform (enable, disable, clear_history, reprocess)
        sport_ids: List of sport IDs to act on
    """
    if not sport_ids:
        ui.notify("No sports selected", type="warning")
        return

    count = len(sport_ids)

    if action == "enable":
        ui.notify(f"Enabling {count} sports...", type="info")

        async def do_enable():
            loop = asyncio.get_event_loop()
            executor = ThreadPoolExecutor(max_workers=1)
            try:
                success = await loop.run_in_executor(
                    executor, lambda: _bulk_toggle_sports_sync(sport_ids, True)
                )
                if success:
                    ui.notify(f"Enabled {count} sports", type="positive")
                    ui.navigate.to("/sports")
                else:
                    ui.notify("Failed to enable sports", type="negative")
            finally:
                executor.shutdown(wait=False)

        asyncio.create_task(do_enable())

    elif action == "disable":
        ui.notify(f"Disabling {count} sports...", type="info")

        async def do_disable():
            loop = asyncio.get_event_loop()
            executor = ThreadPoolExecutor(max_workers=1)
            try:
                success = await loop.run_in_executor(
                    executor, lambda: _bulk_toggle_sports_sync(sport_ids, False)
                )
                if success:
                    ui.notify(f"Disabled {count} sports", type="positive")
                    ui.navigate.to("/sports")
                else:
                    ui.notify("Failed to disable sports", type="negative")
            finally:
                executor.shutdown(wait=False)

        asyncio.create_task(do_disable())

    elif action == "clear_history":
        # Confirm before clearing
        with ui.dialog() as dialog, ui.card().classes("p-4"):
            ui.label(f"Clear history for {count} sports?").classes("text-lg font-semibold mb-2")
            ui.label("This will delete all processed file records for these sports.").classes(
                "text-slate-600 dark:text-slate-400 mb-4"
            )
            ui.label("Files will be re-matched on the next processing run.").classes(
                "text-sm text-slate-500 dark:text-slate-500 mb-4"
            )

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Clear History", on_click=lambda: _do_clear_history(sport_ids, dialog)).props(
                    "color=negative"
                )

        dialog.open()

    elif action == "reprocess":
        # Clear history then trigger run
        with ui.dialog() as dialog, ui.card().classes("p-4"):
            ui.label(f"Reprocess {count} sports?").classes("text-lg font-semibold mb-2")
            ui.label("This will:").classes("text-slate-600 dark:text-slate-400")
            with ui.column().classes("ml-4 mb-4"):
                ui.label("1. Clear processed history for selected sports").classes("text-sm text-slate-500")
                ui.label("2. Run a full processing scan").classes("text-sm text-slate-500")
            ui.label("Selected sports will be re-matched from scratch.").classes(
                "text-sm text-slate-500 dark:text-slate-500 mb-4"
            )

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Reprocess", on_click=lambda: _do_reprocess(sport_ids, dialog)).props("color=primary")

        dialog.open()


def _do_clear_history(sport_ids: list[str], dialog) -> None:
    """Execute the clear history action."""
    dialog.close()
    ui.notify("Clearing history...", type="info")

    async def do_clear():
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            deleted = await loop.run_in_executor(
                executor, lambda: _bulk_clear_history_sync(sport_ids)
            )
            ui.notify(f"Cleared {deleted} records from {len(sport_ids)} sports", type="positive")
            ui.navigate.to("/sports")
        except Exception as e:
            LOGGER.exception("Clear history error: %s", e)
            ui.notify(f"Error: {e}", type="negative")
        finally:
            executor.shutdown(wait=False)

    asyncio.create_task(do_clear())


def _do_reprocess(sport_ids: list[str], dialog) -> None:
    """Execute the reprocess action (clear history + run)."""
    dialog.close()

    async def do_reprocess():
        # First clear history
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)

        try:
            ui.notify("Clearing history for selected sports...", type="info")
            deleted = await loop.run_in_executor(
                executor, lambda: _bulk_clear_history_sync(sport_ids)
            )
            ui.notify(f"Cleared {deleted} records", type="info")

            # Then trigger a full run
            if gui_state.processor and not gui_state.is_processing:
                ui.notify("Starting processing run...", type="info")
                gui_state.set_processing(True)
                try:
                    stats = await loop.run_in_executor(None, gui_state.processor.process_all)
                    if stats.cancelled:
                        ui.notify("Processing stopped", type="warning")
                    else:
                        ui.notify("Reprocessing complete", type="positive")
                finally:
                    gui_state.set_processing(False)
            else:
                ui.notify("Processor busy or not available - run manually when ready", type="warning")

            ui.navigate.to("/sports")
        except Exception as e:
            LOGGER.exception("Reprocess error: %s", e)
            ui.notify(f"Error: {e}", type="negative")
        finally:
            executor.shutdown(wait=False)

    asyncio.create_task(do_reprocess())


def _source_globs_card(sport_id: str, detail: Any) -> None:
    """Show and manage source glob patterns for a sport.

    Args:
        sport_id: The sport identifier
        detail: SportDetail with source_globs info
    """
    from ..data.sport_data import SourceGlobInfo

    if not detail.source_globs and not detail.pattern_set_names:
        return

    # State for tracking changes
    state = {
        "modified": False,
        "new_glob": "",
    }
    globs_container = None

    def get_sport_config():
        """Get the current sport config."""
        if not gui_state.config:
            return None
        for sport in gui_state.config.sports:
            if sport.id == sport_id:
                return sport
        return None

    def toggle_glob(glob_info: SourceGlobInfo) -> None:
        """Toggle a glob's enabled/disabled state."""
        sport_config = get_sport_config()
        if not sport_config:
            return

        disabled = set(sport_config.disabled_source_globs)
        if glob_info.is_disabled:
            # Enable it (remove from disabled)
            disabled.discard(glob_info.pattern)
        else:
            # Disable it (add to disabled)
            disabled.add(glob_info.pattern)

        sport_config.disabled_source_globs = list(disabled)
        state["modified"] = True
        _refresh_globs_ui()

    def add_custom_glob() -> None:
        """Add a new custom glob pattern."""
        new_pattern = state["new_glob"].strip()
        if not new_pattern:
            ui.notify("Please enter a glob pattern", type="warning")
            return

        sport_config = get_sport_config()
        if not sport_config:
            return

        # Check for duplicate
        existing = set(sport_config.source_globs) | set(sport_config.extra_source_globs)
        if new_pattern in existing:
            ui.notify("This pattern already exists", type="warning")
            return

        sport_config.extra_source_globs = list(sport_config.extra_source_globs) + [new_pattern]
        state["new_glob"] = ""
        state["modified"] = True
        _refresh_globs_ui()
        ui.notify(f"Added: {new_pattern}", type="positive")

    def remove_custom_glob(pattern: str) -> None:
        """Remove a custom glob pattern."""
        sport_config = get_sport_config()
        if not sport_config:
            return

        sport_config.extra_source_globs = [g for g in sport_config.extra_source_globs if g != pattern]
        # Also remove from disabled if it was there
        sport_config.disabled_source_globs = [g for g in sport_config.disabled_source_globs if g != pattern]
        state["modified"] = True
        _refresh_globs_ui()
        ui.notify(f"Removed: {pattern}", type="info")

    def save_changes() -> None:
        """Save changes to the config file."""

        if not gui_state.config or not gui_state.config_path:
            ui.notify("Cannot save: config not loaded", type="negative")
            return

        sport_config = get_sport_config()
        if not sport_config:
            ui.notify("Sport config not found", type="negative")
            return

        # Capture values for background thread
        config_path = gui_state.config_path
        extra_globs = list(sport_config.extra_source_globs)
        disabled_globs = list(sport_config.disabled_source_globs)

        ui.notify("Saving...", type="info")

        def do_save():
            from playbook.gui.config_utils.config_persistence import save_sport_source_globs

            save_sport_source_globs(config_path, sport_id, extra_globs, disabled_globs)

        async def async_save():
            loop = asyncio.get_event_loop()
            executor = ThreadPoolExecutor(max_workers=1)
            try:
                await loop.run_in_executor(executor, do_save)
                state["modified"] = False
                _refresh_globs_ui()
                ui.notify("Source globs saved!", type="positive")
            except Exception as e:
                LOGGER.exception("Failed to save source globs: %s", e)
                ui.notify(f"Failed to save: {e}", type="negative")
            finally:
                executor.shutdown(wait=False)

        asyncio.create_task(async_save())

    def _refresh_globs_ui() -> None:
        """Refresh the globs UI."""
        nonlocal globs_container
        if globs_container:
            globs_container.clear()
            _render_globs_list(globs_container)

    def _render_globs_list(container) -> None:
        """Render the list of globs."""
        from playbook.pattern_templates import get_default_source_globs

        sport_config = get_sport_config()
        if not sport_config:
            return

        default_globs = get_default_source_globs(sport_config.pattern_set_names)
        disabled_set = set(sport_config.disabled_source_globs)

        with container:
            # Default globs section
            if default_globs:
                ui.label("Default Patterns").classes("text-sm font-semibold text-slate-600 dark:text-slate-400 mb-2")
                ui.label("From pattern templates - these are shared with all users").classes(
                    "text-xs text-slate-500 dark:text-slate-500 mb-2"
                )

                for pattern in default_globs:
                    is_disabled = pattern in disabled_set
                    with ui.row().classes("w-full items-center gap-2 py-1"):
                        # Toggle switch
                        ui.switch(
                            value=not is_disabled,
                            on_change=lambda e, p=pattern: toggle_glob(
                                SourceGlobInfo(pattern=p, is_default=True, is_disabled=not e.value)
                            ),
                        ).classes("flex-none")

                        # Pattern text
                        pattern_class = (
                            "font-mono text-sm text-slate-400 dark:text-slate-600 line-through"
                            if is_disabled
                            else "font-mono text-sm text-slate-700 dark:text-slate-300"
                        )
                        ui.label(pattern).classes(pattern_class + " flex-1")

                        # Default badge
                        ui.badge("default", color="blue").classes("flex-none")

            # Custom globs section
            ui.label("Custom Patterns").classes(
                "text-sm font-semibold text-slate-600 dark:text-slate-400 mt-4 mb-2"
            )
            ui.label("Your own patterns - only in your config").classes(
                "text-xs text-slate-500 dark:text-slate-500 mb-2"
            )

            if sport_config.extra_source_globs:
                for pattern in sport_config.extra_source_globs:
                    is_disabled = pattern in disabled_set
                    with ui.row().classes("w-full items-center gap-2 py-1"):
                        # Toggle switch
                        ui.switch(
                            value=not is_disabled,
                            on_change=lambda e, p=pattern: toggle_glob(
                                SourceGlobInfo(pattern=p, is_default=False, is_disabled=not e.value)
                            ),
                        ).classes("flex-none")

                        # Pattern text
                        pattern_class = (
                            "font-mono text-sm text-slate-400 dark:text-slate-600 line-through"
                            if is_disabled
                            else "font-mono text-sm text-slate-700 dark:text-slate-300"
                        )
                        ui.label(pattern).classes(pattern_class + " flex-1")

                        # Custom badge
                        ui.badge("custom", color="green").classes("flex-none")

                        # Remove button
                        ui.button(
                            icon="close",
                            on_click=lambda _, p=pattern: remove_custom_glob(p),
                        ).props("flat round dense size=sm").classes("text-red-500")
            else:
                ui.label("No custom patterns added yet").classes(
                    "text-sm text-slate-400 dark:text-slate-500 italic"
                )

            # Add new pattern input
            with ui.row().classes("w-full items-end gap-2 mt-4"):
                ui.input(
                    label="Add custom pattern",
                    placeholder="e.g. MyTeam.*",
                    on_change=lambda e: state.update({"new_glob": e.value}),
                ).classes("flex-1").bind_value(state, "new_glob")

                ui.button("Add", icon="add", on_click=add_custom_glob).props("color=primary")

            # Save button (shown when modified)
            if state["modified"]:
                with ui.row().classes("w-full justify-end mt-4"):
                    ui.button("Save Changes", icon="save", on_click=save_changes).props(
                        "color=primary"
                    ).classes("animate-pulse")

    # Render the card
    with ui.card().classes("glass-card w-full"):
        with ui.row().classes("w-full items-center justify-between mb-4"):
            ui.label("Source Globs").classes("text-xl font-semibold text-slate-700 dark:text-slate-200")
            if detail.pattern_set_names:
                ui.label(f"Pattern sets: {', '.join(detail.pattern_set_names)}").classes(
                    "text-sm text-slate-500 dark:text-slate-400"
                )

        globs_container = ui.column().classes("w-full gap-1")
        _render_globs_list(globs_container)


def _recent_matches_card(sport_id: str) -> None:
    """Show recent matches for a sport."""
    if not gui_state.processed_store:
        return

    try:
        records = gui_state.processed_store.get_by_sport(sport_id)
        recent = sorted(records, key=lambda r: r.processed_at, reverse=True)[:10]
    except Exception as e:
        LOGGER.warning("Failed to get recent matches: %s", e)
        recent = []

    if not recent:
        return

    with ui.card().classes("glass-card w-full"):
        ui.label("Recent Matches").classes("text-xl font-semibold text-slate-700 dark:text-slate-200 mb-4")

        with ui.column().classes("w-full gap-2"):
            for record in recent:
                with ui.row().classes(
                    "w-full items-center gap-4 p-2 rounded hover:bg-slate-50 dark:hover:bg-slate-800/50"
                ):
                    # Status icon
                    status = "matched" if record.status != "error" else "error"
                    icon_name = "check_circle" if status == "matched" else "error"
                    icon_color = (
                        "text-green-600 dark:text-green-400"
                        if status == "matched"
                        else "text-red-600 dark:text-red-400"
                    )
                    ui.icon(icon_name).classes(f"{icon_color}")

                    # Episode code
                    code = f"S{record.season_index:02d}E{record.episode_index:02d}"
                    ui.label(code).classes("font-mono text-sm text-slate-500 dark:text-slate-400 w-16")

                    # Source filename
                    from pathlib import Path

                    filename = Path(record.source_path).name
                    ui.label(filename).classes("flex-1 text-sm text-slate-700 dark:text-slate-300 truncate")

                    # Timestamp
                    time_str = record.processed_at.strftime("%H:%M")
                    ui.label(time_str).classes("text-xs text-slate-400 dark:text-slate-500")


def _pattern_tester() -> None:
    """Create the pattern tester tool."""
    sport_ids = []
    if gui_state.config:
        sport_ids = [sport.id for sport in gui_state.config.sports if sport.enabled]

    if not sport_ids:
        ui.label("No enabled sports available for testing").classes("text-slate-500 dark:text-slate-400 italic")
        return

    state = {
        "filename": "Formula.1.2025.Round01.Australian.Grand.Prix.Race.1080p.HDTV.mkv",
        "sport_id": sport_ids[0] if sport_ids else "",
    }

    with ui.row().classes("w-full gap-4 items-end"):
        ui.input(
            label="Filename to test",
            value=state["filename"],
            on_change=lambda e: state.update({"filename": e.value}),
        ).classes("flex-1")

        ui.select(
            sport_ids,
            value=state["sport_id"],
            label="Sport",
            on_change=lambda e: state.update({"sport_id": e.value}),
        ).classes("w-48")

        ui.button(
            "Test Match",
            icon="play_arrow",
            on_click=lambda: _test_pattern(state["filename"], state["sport_id"], result_container),
        ).props("color=primary")

    result_container = ui.column().classes("w-full mt-4")


def _test_pattern(filename: str, sport_id: str, container: ui.column) -> None:
    """Test a filename against sport patterns."""
    container.clear()

    if not filename or not sport_id:
        with container:
            ui.label("Please enter a filename and select a sport").classes("text-amber-600 dark:text-amber-400")
        return

    if not gui_state.config:
        with container:
            ui.label("Configuration not loaded").classes("text-red-600 dark:text-red-400")
        return

    sport = None
    for s in gui_state.config.sports:
        if s.id == sport_id:
            sport = s
            break

    if not sport:
        with container:
            ui.label(f"Sport '{sport_id}' not found").classes("text-red-600 dark:text-red-400")
        return

    # Show loading indicator
    with container:
        with ui.row().classes("items-center gap-2"):
            ui.spinner(size="sm")
            ui.label("Testing pattern...").classes("text-slate-500 dark:text-slate-400")

    def run_pattern_test():
        """Run the pattern test in a background thread."""
        from playbook.matcher import match_file_to_episode
        from playbook.metadata_loader import load_sports

        result = load_sports(
            sports=[sport],
            settings=gui_state.config.settings,
            metadata_fingerprints=None,
        )

        if not result.runtimes:
            return None, None, None, "Failed to load sport metadata"

        runtime = result.runtimes[0]
        diagnostics: list[tuple[str, str]] = []
        trace: dict[str, Any] = {}

        detection = match_file_to_episode(
            filename,
            runtime.sport,
            runtime.show,
            runtime.patterns,
            diagnostics=diagnostics,
            trace=trace,
        )

        return detection, diagnostics, trace, None

    async def async_test():
        """Run the test asynchronously."""
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            detection, diagnostics, trace, error = await loop.run_in_executor(executor, run_pattern_test)

            container.clear()
            with container:
                if error:
                    ui.label(error).classes("text-red-600 dark:text-red-400")
                elif detection:
                    _render_match_result(detection, trace, diagnostics)
                else:
                    _render_no_match(diagnostics, trace)

        except Exception as e:
            LOGGER.exception("Pattern test error: %s", e)
            container.clear()
            with container:
                ui.label(f"Error testing pattern: {e}").classes("text-red-600 dark:text-red-400")
        finally:
            executor.shutdown(wait=False)

    asyncio.create_task(async_test())


def _render_match_result(
    detection: dict[str, Any],
    trace: dict[str, Any],
    diagnostics: list[tuple[str, str]],
) -> None:
    """Render a successful match result."""
    with ui.card().classes("w-full bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800"):
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon("check_circle").classes("text-green-600 dark:text-green-400 text-2xl")
            ui.label("Match Found").classes("text-xl font-semibold text-green-800 dark:text-green-300")

        with ui.column().classes("gap-2"):
            season = detection.get("season")
            if season:
                with ui.row().classes("gap-2"):
                    ui.label("Season:").classes("font-semibold w-24 text-slate-700 dark:text-slate-300")
                    ui.label(f"S{season.index:02d} - {season.title}").classes("text-slate-700 dark:text-slate-300")

            episode = detection.get("episode")
            if episode:
                with ui.row().classes("gap-2"):
                    ui.label("Episode:").classes("font-semibold w-24 text-slate-700 dark:text-slate-300")
                    ui.label(f"E{episode.index:02d} - {episode.title}").classes("text-slate-700 dark:text-slate-300")

            pattern = detection.get("pattern")
            if pattern:
                with ui.row().classes("gap-2"):
                    ui.label("Pattern:").classes("font-semibold w-24 text-slate-700 dark:text-slate-300")
                    desc = pattern.config.description or "No description"
                    ui.label(desc).classes("text-slate-600 dark:text-slate-400 text-sm")

            groups = detection.get("groups", {})
            if groups:
                with ui.expansion("Captured Groups", icon="code").classes("w-full mt-2"):
                    with ui.column().classes("gap-1"):
                        for key, value in groups.items():
                            with ui.row().classes("gap-2"):
                                ui.label(f"{key}:").classes("font-mono text-sm w-32 text-slate-600 dark:text-slate-400")
                                ui.label(str(value)).classes("font-mono text-sm")

    if diagnostics:
        _render_diagnostics(diagnostics)


def _render_no_match(
    diagnostics: list[tuple[str, str]],
    trace: dict[str, Any],
) -> None:
    """Render a no-match result."""
    with ui.card().classes("w-full bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800"):
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon("warning").classes("text-amber-600 dark:text-amber-400 text-2xl")
            ui.label("No Match").classes("text-xl font-semibold text-amber-800 dark:text-amber-300")

        ui.label("The filename did not match any patterns for this sport.").classes(
            "text-slate-600 dark:text-slate-400"
        )

    _render_diagnostics(diagnostics)

    if trace:
        with ui.expansion("Match Trace", icon="bug_report").classes("w-full mt-2"):
            with ui.column().classes("gap-1 font-mono text-xs"):
                for key, value in trace.items():
                    if key not in ("diagnostics",):
                        with ui.row().classes("gap-2"):
                            ui.label(f"{key}:").classes("text-slate-600 dark:text-slate-400 w-32")
                            ui.label(str(value)[:100]).classes("text-slate-800 dark:text-slate-200 truncate")


def _render_diagnostics(diagnostics: list[tuple[str, str]]) -> None:
    """Render diagnostic messages."""
    if not diagnostics:
        return

    with ui.expansion("Diagnostics", icon="info").classes("w-full mt-2"):
        with ui.column().classes("gap-1"):
            for severity, message in diagnostics:
                color = {
                    "error": "text-red-600 dark:text-red-400",
                    "warning": "text-amber-600 dark:text-amber-400",
                    "info": "text-blue-600 dark:text-blue-400",
                }.get(severity, "text-slate-600 dark:text-slate-400")

                with ui.row().classes("gap-2"):
                    ui.label(f"[{severity.upper()}]").classes(f"font-mono text-xs w-20 {color}")
                    ui.label(message).classes("text-sm text-slate-700 dark:text-slate-300")
