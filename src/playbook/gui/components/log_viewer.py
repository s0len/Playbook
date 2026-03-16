"""
Log viewer component for the Playbook GUI.

Provides log_line() for rendering individual entries with structured
parsing of LogBlockBuilder messages (Run Recap, Processing Details, etc.).
"""

from __future__ import annotations

import re
from html import escape as _h

from nicegui import ui

from ..state import LogEntry, gui_state
from .app_button import neutralize_button_utilities

# ---------------------------------------------------------------------------
# Reusable log_viewer widget (used by dashboard, etc.)
# ---------------------------------------------------------------------------


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
            entry_level = level_order.get(entry.level, 1)
            if entry_level < min_level:
                continue
            if sport_filter != "ALL":
                if (
                    sport_filter.lower() not in entry.message.lower()
                    and sport_filter.lower() not in entry.logger_name.lower()
                ):
                    continue
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


# ---------------------------------------------------------------------------
# Structured block parser — turns LogBlockBuilder output into data
# ---------------------------------------------------------------------------

_KV_RE = re.compile(r"^\s+(\S[^:]*?)\s*:\s*(.+)$")


def _parse_block(message: str) -> tuple[str, dict[str, str], list[tuple[str, list[str]]]] | None:
    """Parse a LogBlockBuilder message into (title, fields, sections).

    Returns None if the message is not a structured block.
    """
    if "\n" not in message:
        return None

    title = ""
    fields: dict[str, str] = {}
    sections: list[tuple[str, list[str]]] = []
    current_section: str | None = None
    current_items: list[str] = []

    for line in message.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.replace("-", "") == "":
            continue

        # Section header: non-indented, ends with colon, no internal colon
        if not line.startswith(" ") and stripped.endswith(":") and ":" not in stripped[:-1]:
            if current_section:
                sections.append((current_section, current_items))
            current_section = stripped[:-1]
            current_items = []
            continue

        # Section bullet item
        if current_section and stripped.startswith("- "):
            current_items.append(stripped[2:])
            continue

        # Key-value pair (indented)
        kv = _KV_RE.match(line)
        if kv:
            fields[kv.group(1).strip()] = kv.group(2).strip()
            continue

        # Title: first non-indented, non-dash line
        if not title and not line.startswith(" "):
            title = stripped

    if current_section:
        sections.append((current_section, current_items))

    return (title, fields, sections) if title and fields else None


# ---------------------------------------------------------------------------
# Level styling constants
# ---------------------------------------------------------------------------

LEVEL_CSS_KEY = {
    "DEBUG": "debug",
    "INFO": "info",
    "WARNING": "warning",
    "ERROR": "error",
    "CRITICAL": "error",
}

LEVEL_BADGE_TEXT = {
    "DEBUG": "DBG",
    "INFO": "INFO",
    "WARNING": "WARN",
    "ERROR": "ERR",
    "CRITICAL": "CRIT",
}


# ---------------------------------------------------------------------------
# Structured renderers (HTML-based for performance)
# ---------------------------------------------------------------------------

_RECAP_KEYS = ["Duration", "Processed", "Skipped", "Ignored", "Warnings", "Errors", "Destinations", "Plex Sync"]


def _pill_html(key: str, value: str) -> str:
    """Generate HTML for a stat pill: value + label, colored by meaning."""
    cls = "log-pill"
    if key in ("Warnings",) and value != "0":
        cls += " log-pill-warning"
    elif key in ("Errors",) and value != "0":
        cls += " log-pill-error"
    elif key == "Duration":
        cls += " log-pill-accent"
    return (
        f'<span class="{cls}">'
        f'<span class="log-pill-value">{_h(value)}</span>'
        f'<span class="log-pill-label">{_h(key.lower())}</span>'
        f"</span>"
    )


def _render_recap(time_str: str, level_key: str, badge_text: str, fields: dict[str, str]) -> None:
    """Render Run Recap as a card with stat pills."""
    pills = [_pill_html(k, fields[k]) for k in _RECAP_KEYS if k in fields]
    html = (
        f'<div class="log-block-content">'
        f'<div class="log-block-title">Run Recap</div>'
        f'<div class="log-stats-row">{"".join(pills)}</div>'
        f"</div>"
    )
    with ui.row().classes(f"w-full log-entry log-entry-{level_key} log-entry-recap"):
        ui.label(time_str).classes("log-timestamp")
        ui.label(badge_text).classes(f"log-badge log-badge-{level_key}")
        ui.html(html, sanitize=False).classes("min-w-0 flex-1")


def _render_processing(time_str: str, level_key: str, badge_text: str, fields: dict[str, str]) -> None:
    """Render Processing Details as compact source -> destination."""
    source = _h(fields.get("Source", ""))
    parts: list[str] = []
    if dest := fields.get("Destination", ""):
        parts.append(f'<span class="log-detail-dest">\u2192 {_h(dest)}</span>')
    if quality := fields.get("Quality", ""):
        parts.append(f'<span class="log-detail-tag">{_h(quality)}</span>')
    if upgrade := fields.get("Upgrade", ""):
        parts.append(f'<span class="log-detail-tag log-detail-upgrade">{_h(upgrade)}</span>')
    if action := fields.get("Action", ""):
        parts.append(f'<span class="log-detail-action">{_h(action)}</span>')

    sep = '<span class="log-sep">\u00b7</span>'
    html = (
        f'<div class="log-block-content">'
        f'<div class="log-processing-source">{source}</div>'
        f'<div class="log-processing-meta">{sep.join(parts)}</div>'
        f"</div>"
    )
    with ui.row().classes(f"w-full log-entry log-entry-{level_key}"):
        ui.label(time_str).classes("log-timestamp")
        ui.label(badge_text).classes(f"log-badge log-badge-{level_key}")
        ui.html(html, sanitize=False).classes("min-w-0 flex-1")


def _render_summary(time_str: str, level_key: str, badge_text: str, fields: dict[str, str]) -> None:
    """Render Summary as compact inline stats."""
    parts = [
        f'<span class="log-summary-stat">'
        f'<span class="log-pill-value">{_h(fields[k])}</span> {_h(k.lower())}'
        f"</span>"
        for k in ["Processed", "Skipped", "Ignored"]
        if k in fields
    ]
    sep = '<span class="log-sep">\u00b7</span>'
    html = (
        f'<div class="log-summary-content">'
        f'<span class="log-block-title">Summary</span>'
        f'<span class="log-sep">\u2014</span>'
        f"{sep.join(parts)}"
        f"</div>"
    )
    with ui.row().classes(f"w-full log-entry log-entry-{level_key} log-entry-recap"):
        ui.label(time_str).classes("log-timestamp")
        ui.label(badge_text).classes(f"log-badge log-badge-{level_key}")
        ui.html(html, sanitize=False).classes("min-w-0 flex-1")


def _render_generic_block(
    time_str: str, level_key: str, badge_text: str, title: str, fields: dict[str, str]
) -> None:
    """Render any other structured block as title + inline key-value pairs."""
    parts = [
        f'<span class="log-summary-stat">'
        f'<span class="log-pill-value">{_h(v)}</span> {_h(k.lower())}'
        f"</span>"
        for k, v in fields.items()
    ]
    sep = '<span class="log-sep">\u00b7</span>'
    html = (
        f'<div class="log-summary-content">'
        f'<span class="log-block-title">{_h(title)}</span>'
        f'<span class="log-sep">\u2014</span>'
        f"{sep.join(parts)}"
        f"</div>"
    )
    with ui.row().classes(f"w-full log-entry log-entry-{level_key}"):
        ui.label(time_str).classes("log-timestamp")
        ui.label(badge_text).classes(f"log-badge log-badge-{level_key}")
        ui.html(html, sanitize=False).classes("min-w-0 flex-1")


# ---------------------------------------------------------------------------
# Main entry point — dispatches to structured or generic renderer
# ---------------------------------------------------------------------------


def log_line(entry: LogEntry) -> None:
    """Render a single log entry.

    Structured messages (from LogBlockBuilder) are parsed and rendered
    with stat pills / compact layouts. Everything else renders as plain text.
    """
    level_key = LEVEL_CSS_KEY.get(entry.level, "info")
    badge_text = LEVEL_BADGE_TEXT.get(entry.level, entry.level[:4])
    time_str = entry.timestamp.strftime("%H:%M:%S")

    # Try structured parsing first
    parsed = _parse_block(entry.message)
    if parsed:
        title, fields, _sections = parsed
        if title == "Run Recap":
            _render_recap(time_str, level_key, badge_text, fields)
            return
        if title == "Processing Details":
            _render_processing(time_str, level_key, badge_text, fields)
            return
        if title == "Summary":
            _render_summary(time_str, level_key, badge_text, fields)
            return
        _render_generic_block(time_str, level_key, badge_text, title, fields)
        return

    # Plain unstructured message
    with ui.row().classes(f"w-full log-entry log-entry-{level_key}"):
        ui.label(time_str).classes("log-timestamp")
        ui.label(badge_text).classes(f"log-badge log-badge-{level_key}")
        ui.label(entry.message).classes(f"log-msg log-msg-{level_key}")


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
        neutralize_button_utilities(
            ui.button(icon="delete", on_click=lambda: gui_state.log_buffer.clear()).props("flat")
        ).classes("text-gray-500")

    return row
