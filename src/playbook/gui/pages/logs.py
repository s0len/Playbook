"""
Logs page for the Playbook GUI.

Displays real-time log streaming with filtering capabilities.
"""

from __future__ import annotations

from nicegui import ui

from ..components.log_viewer import log_line
from ..state import LogEntry, gui_state
from ..utils import safe_timer


def logs_page() -> None:
    """Render the logs page."""
    # State for filters
    state = {
        "level_filter": "INFO",
        "sport_filter": "ALL",
        "search_query": "",
        "auto_scroll": True,
        "paused": False,
    }

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
        # Page title
        ui.label("Logs").classes("text-3xl font-bold text-slate-800 dark:text-slate-100")

        # Filter controls
        with ui.card().classes("glass-card w-full"):
            with ui.row().classes("w-full gap-3 items-center flex-wrap"):
                # Level filter
                ui.select(
                    ["DEBUG", "INFO", "WARNING", "ERROR"],
                    value=state["level_filter"],
                    label="Level",
                    on_change=lambda e: _update_filter(state, "level_filter", e.value),
                ).classes("w-28")

                # Sport filter
                sport_options = ["ALL"] + _get_sport_ids()
                ui.select(
                    sport_options,
                    value=state["sport_filter"],
                    label="Sport",
                    on_change=lambda e: _update_filter(state, "sport_filter", e.value),
                ).classes("w-40")

                # Search input
                ui.input(
                    placeholder="Search logs...",
                    on_change=lambda e: _update_filter(state, "search_query", e.value or ""),
                ).classes("flex-1 min-w-48")

                # Auto-scroll toggle
                ui.checkbox(
                    "Auto-scroll",
                    value=state["auto_scroll"],
                    on_change=lambda e: _update_filter(state, "auto_scroll", e.value),
                ).classes("text-slate-700 dark:text-slate-300")

                # Pause toggle
                pause_btn = (
                    ui.button(
                        icon="pause",
                        on_click=lambda: _toggle_pause(state, pause_btn),
                    )
                    .props("flat")
                    .classes("text-slate-600 dark:text-slate-400")
                )

                # Clear button
                ui.button(
                    icon="delete_sweep",
                    on_click=lambda: _clear_logs(),
                ).props("flat").classes("text-slate-600 dark:text-slate-400")

        # Log display
        with ui.card().classes("glass-card w-full"):
            log_scroll = (
                ui.scroll_area()
                .classes("w-full font-mono text-sm log-container text-slate-100 rounded-lg")
                .style("height: 600px; max-height: 70vh;")
            )
            with log_scroll:
                log_container = ui.column().classes("w-full p-3")

            # Stats row
            with ui.row().classes(
                "w-full justify-between items-center mt-2 text-sm text-slate-600 dark:text-slate-400"
            ):
                log_count_label = ui.label("0 entries")
                filter_info = ui.label("")

            def refresh_logs() -> None:
                if state["paused"]:
                    return

                try:
                    logs = _get_filtered_logs(
                        level_filter=state["level_filter"],
                        sport_filter=state["sport_filter"],
                        search_query=state["search_query"],
                        max_lines=300,
                    )

                    log_container.clear()
                    with log_container:
                        if not logs:
                            ui.label("No logs matching filters").classes("text-slate-500 italic py-4")
                        else:
                            for entry in logs:
                                log_line(entry)

                    # Update stats
                    total_logs = len(gui_state.log_buffer)
                    filtered_count = len(logs)
                    log_count_label.text = f"{filtered_count} of {total_logs} entries"

                    # Update filter info
                    filters_active = []
                    if state["level_filter"] != "INFO":
                        filters_active.append(f"level={state['level_filter']}")
                    if state["sport_filter"] != "ALL":
                        filters_active.append(f"sport={state['sport_filter']}")
                    if state["search_query"]:
                        filters_active.append(f"search='{state['search_query']}'")
                    filter_info.text = ", ".join(filters_active) if filters_active else ""

                    # Auto-scroll to top (newest)
                    if state["auto_scroll"]:
                        log_scroll.scroll_to(percent=0)
                except (RuntimeError, KeyError):
                    # Client disconnected - timer will be cleaned up
                    pass

            safe_timer(1.0, refresh_logs)
            refresh_logs()


def _update_filter(state: dict, key: str, value) -> None:
    """Update a filter value."""
    state[key] = value


def _toggle_pause(state: dict, button: ui.button) -> None:
    """Toggle log refresh pause."""
    state["paused"] = not state["paused"]
    if state["paused"]:
        button.props("color=warning")
        button._props["icon"] = "play_arrow"
    else:
        button.props(remove="color")
        button._props["icon"] = "pause"
    button.update()


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
        # Level filter
        entry_level = level_order.get(entry.level, 1)
        if entry_level < min_level:
            continue

        # Sport filter (check if sport ID appears in logger name or message)
        if sport_filter != "ALL":
            sport_lower = sport_filter.lower()
            if sport_lower not in entry.message.lower() and sport_lower not in entry.logger_name.lower():
                continue

        # Search filter
        if search_query:
            if search_query.lower() not in entry.message.lower():
                continue

        filtered.append(entry)

        if len(filtered) >= max_lines:
            break

    return filtered
