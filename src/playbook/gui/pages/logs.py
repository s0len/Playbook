"""
Logs page for the Playbook GUI.

Displays real-time log streaming with filtering capabilities.
Styled to match qui's log viewer aesthetic.
"""

from __future__ import annotations

from nicegui import ui

from ..components.log_viewer import log_line
from ..state import LogEntry, gui_state
from ..utils import safe_timer

MAX_LOG_LINES = 500


def logs_page() -> None:
    """Render the logs page."""
    state = {
        "level_filter": "INFO",
        "sport_filter": "ALL",
        "search_query": "",
        "auto_scroll": True,
        "paused": False,
    }

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
        # Header
        ui.label("Logs").classes("text-3xl font-bold text-slate-800 dark:text-slate-100")
        ui.label("Real-time application logs.").classes("text-sm text-slate-500 dark:text-slate-400 -mt-2")

        # Toolbar
        with ui.card().classes("glass-card w-full"):
            with ui.row().classes("w-full gap-3 items-center flex-wrap"):
                # Connection indicator
                with ui.row().classes("items-center gap-1.5 mr-2"):
                    ui.icon("circle").classes("text-[8px] text-green-400")
                    ui.label("Connected").classes("text-xs text-green-400")

                # Search input
                ui.input(
                    placeholder="Search logs...",
                    on_change=lambda e: _update_filter(state, "search_query", e.value or ""),
                ).props('dense outlined').classes("flex-1 min-w-48")

                # Level filter
                ui.select(
                    {
                        "DEBUG": "Debug",
                        "INFO": "All Levels",
                        "WARNING": "Warning+",
                        "ERROR": "Error+",
                    },
                    value=state["level_filter"],
                    on_change=lambda e: _update_filter(state, "level_filter", e.value),
                ).props("dense outlined").classes("w-32")

                # Sport filter
                sport_options = {"ALL": "All Sports"} | {s: s for s in _get_sport_ids()}
                ui.select(
                    sport_options,
                    value=state["sport_filter"],
                    on_change=lambda e: _update_filter(state, "sport_filter", e.value),
                ).props("dense outlined").classes("w-36")

                # Clear button
                ui.button(
                    "Clear",
                    on_click=lambda: _clear_logs(),
                ).props("flat dense").classes("text-slate-500 dark:text-slate-400 text-xs")

                # Auto-scroll toggle
                with ui.row().classes("items-center gap-1.5"):
                    ui.switch(
                        value=state["auto_scroll"],
                        on_change=lambda e: _update_filter(state, "auto_scroll", e.value),
                    ).props("dense")
                    ui.label("Auto-scroll").classes("text-xs text-slate-500 dark:text-slate-400")

        # Log viewport
        with ui.card().classes("glass-card w-full"):
            log_scroll = (
                ui.scroll_area()
                .classes("w-full font-mono text-xs log-container text-slate-100 rounded-lg")
                .style("height: 600px; max-height: 70vh;")
            )
            with log_scroll:
                log_container = ui.column().classes("w-full p-3 gap-0")

            # Footer
            with ui.row().classes(
                "w-full justify-center items-center mt-2 text-xs text-slate-500 dark:text-slate-400"
            ):
                log_count_label = ui.label(f"Showing 0 of 0 entries ({MAX_LOG_LINES} max)")

            def refresh_logs() -> None:
                if state["paused"]:
                    return

                try:
                    logs = _get_filtered_logs(
                        level_filter=state["level_filter"],
                        sport_filter=state["sport_filter"],
                        search_query=state["search_query"],
                        max_lines=MAX_LOG_LINES,
                    )

                    log_container.clear()
                    with log_container:
                        if not logs:
                            ui.label("No logs matching filters").classes("text-slate-500 italic py-4")
                        else:
                            for entry in logs:
                                log_line(entry)

                    total_logs = len(gui_state.log_buffer)
                    filtered_count = len(logs)
                    log_count_label.text = (
                        f"Showing {filtered_count} of {total_logs} entries ({MAX_LOG_LINES} max)"
                    )

                    if state["auto_scroll"]:
                        log_scroll.scroll_to(percent=0)
                except (RuntimeError, KeyError):
                    pass

            safe_timer(1.0, refresh_logs)
            refresh_logs()


def _update_filter(state: dict, key: str, value) -> None:
    """Update a filter value."""
    state[key] = value


def _clear_logs() -> None:
    """Clear all logs from buffer."""
    gui_state.log_buffer.clear()
    ui.notify("Logs cleared", type="info")


def _get_sport_ids() -> list[str]:
    """Get list of configured sport IDs."""
    if not gui_state.config:
        return []
    return [sport.id for sport in gui_state.config.sports]


def _get_filtered_logs(
    level_filter: str,
    sport_filter: str,
    search_query: str,
    max_lines: int,
) -> list[LogEntry]:
    """Get logs filtered by current criteria."""
    level_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
    min_level = level_order.get(level_filter, 1)

    filtered = []
    for entry in gui_state.log_buffer:
        entry_level = level_order.get(entry.level, 1)
        if entry_level < min_level:
            continue

        if sport_filter != "ALL":
            sport_lower = sport_filter.lower()
            if sport_lower not in entry.message.lower() and sport_lower not in entry.logger_name.lower():
                continue

        if search_query:
            if search_query.lower() not in entry.message.lower():
                continue

        filtered.append(entry)

        if len(filtered) >= max_lines:
            break

    return filtered
