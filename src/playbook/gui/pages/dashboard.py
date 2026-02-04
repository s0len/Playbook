"""
Dashboard page for the Playbook GUI.

Displays real-time processing statistics, activity feed, and quick actions.
"""

from __future__ import annotations

import asyncio
import logging

from nicegui import ui

from ..components import activity_feed, stats_card
from ..state import gui_state
from ..utils import safe_timer

LOGGER = logging.getLogger(__name__)


def _safe_notify(message: str, type: str = "info") -> None:
    """Safely call ui.notify, handling deleted UI context."""
    try:
        ui.notify(message, type=type)
    except RuntimeError as e:
        if "deleted" in str(e):
            # User navigated away, ignore
            LOGGER.debug("Notification skipped (UI context deleted): %s", message)
        else:
            raise


def dashboard_page() -> None:
    """Render the main dashboard page."""
    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-6"):
        # Page title
        ui.label("Dashboard").classes("text-3xl font-bold text-slate-800 dark:text-slate-100")

        # Stats cards row
        with ui.row().classes("w-full gap-4 flex-wrap"):
            _stats_cards()

        # Main content: Activity feed + Quick actions
        with ui.row().classes("w-full gap-4"):
            # Activity feed (left, wider)
            with ui.card().classes("glass-card flex-1 min-w-96"):
                with ui.row().classes("items-center justify-between mb-2"):
                    ui.label("Recent Activity").classes("text-xl font-semibold text-slate-700 dark:text-slate-200")
                    _refresh_button()
                activity_feed(max_items=15)

            # Quick actions + Status (right, narrower)
            with ui.column().classes("w-72 gap-4"):
                _quick_actions_card()
                _status_card()


def _stats_cards() -> None:
    """Create the row of statistics cards."""

    def get_processed() -> int:
        # Use persistent store for accurate count across restarts
        if gui_state.processed_store:
            stats = gui_state.processed_store.get_stats()
            return stats.get("total", 0)
        # Fallback to in-memory state
        if gui_state.processor:
            return len(gui_state.processor._state.touched_destinations)
        return 0

    def get_events_count() -> int:
        # Recent events from memory (session only)
        return len(gui_state.recent_events)

    def get_sports_count() -> int:
        if not gui_state.config:
            return 0
        return len([s for s in gui_state.config.sports if s.enabled])

    def get_errors() -> int:
        # Use persistent store for error count
        if gui_state.processed_store:
            stats = gui_state.processed_store.get_stats()
            by_status = stats.get("by_status", {})
            return by_status.get("error", 0)
        # Fallback to in-memory events
        return sum(1 for e in gui_state.recent_events if e.action == "error")

    stats_card("Processed", get_processed, color="green", icon="check_circle")
    stats_card("Events", get_events_count, color="blue", icon="notifications")
    stats_card("Active Sports", get_sports_count, color="purple", icon="emoji_events")
    stats_card("Errors", get_errors, color="red", icon="error")


def _quick_actions_card() -> None:
    """Create the quick actions card."""
    with ui.card().classes("glass-card w-full"):
        ui.label("Quick Actions").classes("text-xl font-semibold text-slate-700 dark:text-slate-200 mb-3")

        with ui.column().classes("w-full gap-2"):
            # Run Now button
            ui.button(
                "Run Now",
                icon="play_arrow",
                on_click=_trigger_run,
            ).classes("w-full").props("color=primary")

            # Clear Cache button
            ui.button(
                "Clear Cache",
                icon="delete_sweep",
                on_click=_clear_cache,
            ).classes("w-full").props("color=warning outline")

            # Refresh Metadata button
            ui.button(
                "Refresh Metadata",
                icon="refresh",
                on_click=_refresh_metadata,
            ).classes("w-full").props("color=secondary outline")


def _status_card() -> None:
    """Create the status/info card."""
    with ui.card().classes("glass-card w-full"):
        ui.label("Status").classes("text-xl font-semibold text-slate-700 dark:text-slate-200 mb-3")

        with ui.column().classes("w-full gap-2"):
            # Processing status
            with ui.row().classes("items-center gap-2"):
                status_icon = ui.icon("circle").classes("text-sm")
                status_label = ui.label("Idle").classes("text-slate-700 dark:text-slate-300")

                def update_status() -> None:
                    try:
                        if gui_state.is_processing:
                            status_icon.classes(replace="text-green-500 animate-pulse text-sm")
                            status_label.text = "Processing..."
                        else:
                            status_icon.classes(replace="text-slate-400 text-sm")
                            status_label.text = "Idle"
                    except (RuntimeError, KeyError):
                        # Client disconnected - timer will be cleaned up
                        pass

                safe_timer(1.0, update_status)
                update_status()

            # Last run time
            with ui.row().classes("items-center gap-2 text-sm text-slate-600 dark:text-slate-400"):
                ui.icon("schedule").classes("text-lg")
                last_run_label = ui.label("Never")

                def update_last_run() -> None:
                    try:
                        if gui_state.last_run_at:
                            last_run_label.text = gui_state.last_run_at.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            last_run_label.text = "Never"
                    except (RuntimeError, KeyError):
                        # Client disconnected - timer will be cleaned up
                        pass

                safe_timer(5.0, update_last_run)
                update_last_run()

            # Run count
            with ui.row().classes("items-center gap-2 text-sm text-slate-600 dark:text-slate-400"):
                ui.icon("replay").classes("text-lg")
                run_count_label = ui.label("0 runs")

                def update_run_count() -> None:
                    try:
                        run_count_label.text = f"{gui_state.run_count} runs"
                    except (RuntimeError, KeyError):
                        # Client disconnected - timer will be cleaned up
                        pass

                safe_timer(5.0, update_run_count)
                update_run_count()

            # Config path
            if gui_state.config_path:
                with ui.row().classes("items-center gap-2 text-sm text-slate-600 dark:text-slate-400"):
                    ui.icon("description").classes("text-lg")
                    ui.label(str(gui_state.config_path.name)).classes("truncate")


def _refresh_button() -> None:
    """Create a small refresh button."""
    ui.button(icon="refresh", on_click=lambda: None).props("flat dense").classes("text-slate-500 dark:text-slate-400")


async def _trigger_run() -> None:
    """Trigger a manual processing run."""
    if not gui_state.processor:
        _safe_notify("Processor not initialized", type="warning")
        return

    if gui_state.is_processing:
        _safe_notify("Processing already in progress", type="info")
        return

    _safe_notify("Starting processing run...", type="info")
    gui_state.set_processing(True)

    try:
        # Run processor in background
        await asyncio.get_event_loop().run_in_executor(None, gui_state.processor.process_all)
        _safe_notify("Processing complete", type="positive")
    except Exception as e:
        LOGGER.exception("Processing error: %s", e)
        _safe_notify(f"Processing error: {e}", type="negative")
    finally:
        gui_state.set_processing(False)


async def _clear_cache() -> None:
    """Clear the processed file cache."""
    if not gui_state.processor:
        _safe_notify("Processor not initialized", type="warning")
        return

    _safe_notify("Clearing cache...", type="info")

    try:
        # Run cache clear in background to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None, gui_state.processor.clear_processed_cache
        )
        gui_state.recent_events.clear()
        _safe_notify("Cache cleared", type="positive")
    except Exception as e:
        LOGGER.exception("Error clearing cache: %s", e)
        _safe_notify(f"Error clearing cache: {e}", type="negative")


async def _refresh_metadata() -> None:
    """Trigger metadata refresh."""
    _safe_notify("Metadata refresh will happen on next run", type="info")
