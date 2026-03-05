"""
Log viewer component for the Playbook GUI.
"""

from __future__ import annotations

from nicegui import ui

from ..state import LogEntry, gui_state


def log_viewer(
    level_filter: str = "INFO",
    sport_filter: str = "ALL",
    search_query: str = "",
    max_lines: int = 200,
    auto_scroll: bool = True,
) -> ui.column:
    """Create a log viewer with filtering capabilities.

    Args:
        level_filter: Minimum log level to show (DEBUG, INFO, WARNING, ERROR)
        sport_filter: Sport ID to filter by, or "ALL"
        search_query: Search string to filter logs
        max_lines: Maximum number of log lines to display
        auto_scroll: Whether to auto-scroll to newest entries

    Returns:
        The log container element
    """
    log_container = ui.column().classes("w-full font-mono text-sm glass-card p-3 rounded h-96 overflow-auto")

    level_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
    min_level = level_order.get(level_filter, 1)

    def get_filtered_logs() -> list[LogEntry]:
        """Get logs filtered by current criteria."""
        filtered = []
        for entry in gui_state.log_buffer:
            # Level filter
            entry_level = level_order.get(entry.level, 1)
            if entry_level < min_level:
                continue

            # Sport filter (check if sport ID appears in logger name or message)
            if sport_filter != "ALL":
                if (
                    sport_filter.lower() not in entry.message.lower()
                    and sport_filter.lower() not in entry.logger_name.lower()
                ):
                    continue

            # Search filter
            if search_query:
                if search_query.lower() not in entry.message.lower():
                    continue

            filtered.append(entry)

            if len(filtered) >= max_lines:
                break

        return filtered

    def refresh() -> None:
        log_container.clear()
        logs = get_filtered_logs()
        with log_container:
            if not logs:
                ui.label("No logs matching filters").classes("text-gray-500 italic")
            else:
                for entry in logs:
                    log_line(entry)

        if auto_scroll:
            log_container.scroll_to(percent=0)

    ui.timer(1.0, refresh)
    refresh()

    return log_container


LEVEL_STYLES = {
    "DEBUG": ("app-alert app-alert-info app-text-muted", "app-text-muted"),
    "INFO": ("app-alert app-alert-success app-text-success", "app-text-success"),
    "WARNING": ("app-alert app-alert-warning app-text-warning", "app-text-warning"),
    "ERROR": ("app-alert app-alert-danger app-text-danger", "app-text-danger"),
    "CRITICAL": ("app-alert app-alert-danger app-text-danger", "app-text-danger"),
}


def log_line(entry: LogEntry) -> None:
    """Render a single log line with qui-style colored level badge.

    Args:
        entry: The log entry to display
    """
    badge_cls, msg_cls = LEVEL_STYLES.get(entry.level, ("app-alert app-alert-info app-text-muted", "app-text-muted"))
    time_str = entry.timestamp.strftime("%H:%M:%S")

    with ui.row().classes("w-full gap-2 items-center py-0.5 hover:bg-white/5 px-1"):
        # Timestamp
        ui.label(time_str).classes("text-xs app-text-muted shrink-0 font-mono")
        # Level badge
        ui.label(entry.level).classes(
            f"w-12 text-center text-[10px] uppercase font-semibold rounded px-1 py-0.5 shrink-0 {badge_cls}"
        )
        # Message
        ui.label(entry.message).classes(f"text-xs whitespace-nowrap font-mono {msg_cls}")


def log_filters(
    on_level_change: callable,
    on_sport_change: callable,
    on_search_change: callable,
    sports: list[str] | None = None,
) -> ui.row:
    """Create log filter controls.

    Args:
        on_level_change: Callback when level filter changes
        on_sport_change: Callback when sport filter changes
        on_search_change: Callback when search query changes
        sports: List of sport IDs for the sport filter dropdown

    Returns:
        The filter controls row
    """
    sports = sports or []

    with ui.row().classes("w-full gap-2 items-center flex-wrap") as row:
        # Level filter
        ui.select(
            ["DEBUG", "INFO", "WARNING", "ERROR"],
            value="INFO",
            label="Level",
            on_change=lambda e: on_level_change(e.value),
        ).classes("w-28")

        # Sport filter
        sport_options = ["ALL"] + sports
        ui.select(
            sport_options,
            value="ALL",
            label="Sport",
            on_change=lambda e: on_sport_change(e.value),
        ).classes("w-36")

        # Search
        ui.input(
            placeholder="Search logs...",
            on_change=lambda e: on_search_change(e.value),
        ).classes("flex-1 min-w-48")

        # Clear button
        ui.button(icon="delete", on_click=lambda: gui_state.log_buffer.clear()).props("flat").classes("text-gray-500")

    return row
