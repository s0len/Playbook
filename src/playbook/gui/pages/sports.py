"""
Sports management page for the Playbook GUI.

Displays configured sports with stats and provides a pattern tester tool.
"""

from __future__ import annotations

import logging
from typing import Any

from nicegui import ui

from ..state import gui_state

LOGGER = logging.getLogger(__name__)


def sports_page() -> None:
    """Render the sports management page."""
    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-6"):
        # Page title
        ui.label("Sports").classes("text-3xl font-bold text-gray-800")

        # Sports table
        with ui.card().classes("w-full"):
            ui.label("Configured Sports").classes("text-xl font-semibold text-gray-700 mb-3")
            _sports_table()

        # Pattern tester
        with ui.card().classes("w-full"):
            ui.label("Pattern Tester").classes("text-xl font-semibold text-gray-700 mb-3")
            _pattern_tester()


def _sports_table() -> None:
    """Create the sports overview table."""
    sports_data = _get_sports_data()

    if not sports_data:
        ui.label("No sports configured").classes("text-gray-500 italic py-4")
        return

    columns = [
        {"name": "enabled", "label": "Status", "field": "enabled", "align": "center", "sortable": True},
        {"name": "name", "label": "Sport", "field": "name", "align": "left", "sortable": True},
        {"name": "id", "label": "ID", "field": "id", "align": "left"},
        {"name": "show_slug", "label": "Show Slug", "field": "show_slug", "align": "left"},
        {"name": "link_mode", "label": "Link Mode", "field": "link_mode", "align": "center"},
        {"name": "patterns", "label": "Patterns", "field": "patterns", "align": "center"},
        {"name": "extensions", "label": "Extensions", "field": "extensions", "align": "left"},
    ]

    rows = []
    for sport in sports_data:
        rows.append(
            {
                "enabled": "Enabled" if sport["enabled"] else "Disabled",
                "name": sport["name"],
                "id": sport["id"],
                "show_slug": sport["show_slug"],
                "link_mode": sport["link_mode"],
                "patterns": sport["pattern_count"],
                "extensions": ", ".join(sport["extensions"][:3]) + ("..." if len(sport["extensions"]) > 3 else ""),
            }
        )

    table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")
    table.add_slot(
        "body-cell-enabled",
        """
        <q-td :props="props">
            <q-badge :color="props.value === 'Enabled' ? 'green' : 'grey'">
                {{ props.value }}
            </q-badge>
        </q-td>
        """,
    )


def _get_sports_data() -> list[dict[str, Any]]:
    """Get sports data for the table."""
    if not gui_state.config:
        return []

    sports = []
    for sport in gui_state.config.sports:
        sports.append(
            {
                "id": sport.id,
                "name": sport.name,
                "show_slug": sport.show_slug,
                "enabled": sport.enabled,
                "link_mode": sport.link_mode,
                "pattern_count": len(sport.patterns),
                "extensions": sport.source_extensions,
                "source_globs": sport.source_globs,
            }
        )
    return sports


def _pattern_tester() -> None:
    """Create the pattern tester tool."""
    # Get sport IDs for dropdown
    sport_ids = []
    if gui_state.config:
        sport_ids = [sport.id for sport in gui_state.config.sports if sport.enabled]

    if not sport_ids:
        ui.label("No enabled sports available for testing").classes("text-gray-500 italic")
        return

    # State
    state = {
        "filename": "Formula.1.2025.Round01.Australian.Grand.Prix.Race.1080p.HDTV.mkv",
        "sport_id": sport_ids[0] if sport_ids else "",
    }

    with ui.row().classes("w-full gap-4 items-end"):
        # Filename input
        ui.input(
            label="Filename to test",
            value=state["filename"],
            on_change=lambda e: state.update({"filename": e.value}),
        ).classes("flex-1")

        # Sport selector
        ui.select(
            sport_ids,
            value=state["sport_id"],
            label="Sport",
            on_change=lambda e: state.update({"sport_id": e.value}),
        ).classes("w-48")

        # Test button
        ui.button(
            "Test Match",
            icon="play_arrow",
            on_click=lambda: _test_pattern(state["filename"], state["sport_id"], result_container),
        ).props("color=primary")

    # Results container
    result_container = ui.column().classes("w-full mt-4")


def _test_pattern(filename: str, sport_id: str, container: ui.column) -> None:
    """Test a filename against sport patterns."""
    container.clear()

    if not filename or not sport_id:
        with container:
            ui.label("Please enter a filename and select a sport").classes("text-yellow-600")
        return

    if not gui_state.config:
        with container:
            ui.label("Configuration not loaded").classes("text-red-600")
        return

    # Find sport
    sport = None
    for s in gui_state.config.sports:
        if s.id == sport_id:
            sport = s
            break

    if not sport:
        with container:
            ui.label(f"Sport '{sport_id}' not found").classes("text-red-600")
        return

    try:
        # Import matcher and metadata loader
        from playbook.matcher import match_file_to_episode
        from playbook.metadata_loader import load_sports

        # Load sport metadata
        result = load_sports(
            sports=[sport],
            settings=gui_state.config.settings,
            metadata_fingerprints=None,
        )

        if not result.runtimes:
            with container:
                ui.label("Failed to load sport metadata").classes("text-red-600")
            return

        runtime = result.runtimes[0]

        # Run matcher
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

        with container:
            if detection:
                _render_match_result(detection, trace, diagnostics)
            else:
                _render_no_match(diagnostics, trace)

    except Exception as e:
        LOGGER.exception("Pattern test error: %s", e)
        with container:
            ui.label(f"Error testing pattern: {e}").classes("text-red-600")


def _render_match_result(detection: dict[str, Any], trace: dict[str, Any], diagnostics: list[tuple[str, str]]) -> None:
    """Render a successful match result."""
    with ui.card().classes("w-full bg-green-50 border-green-200"):
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon("check_circle").classes("text-green-600 text-2xl")
            ui.label("Match Found").classes("text-xl font-semibold text-green-800")

        with ui.column().classes("gap-2"):
            # Season info
            season = detection.get("season")
            if season:
                with ui.row().classes("gap-2"):
                    ui.label("Season:").classes("font-semibold w-24")
                    ui.label(f"S{season.index:02d} - {season.title}").classes("text-gray-700")

            # Episode info
            episode = detection.get("episode")
            if episode:
                with ui.row().classes("gap-2"):
                    ui.label("Episode:").classes("font-semibold w-24")
                    ui.label(f"E{episode.index:02d} - {episode.title}").classes("text-gray-700")

            # Pattern used
            pattern = detection.get("pattern")
            if pattern:
                with ui.row().classes("gap-2"):
                    ui.label("Pattern:").classes("font-semibold w-24")
                    desc = pattern.config.description or "No description"
                    ui.label(desc).classes("text-gray-600 text-sm")

            # Captured groups
            groups = detection.get("groups", {})
            if groups:
                with ui.expansion("Captured Groups", icon="code").classes("w-full mt-2"):
                    with ui.column().classes("gap-1"):
                        for key, value in groups.items():
                            with ui.row().classes("gap-2"):
                                ui.label(f"{key}:").classes("font-mono text-sm w-32 text-gray-600")
                                ui.label(str(value)).classes("font-mono text-sm")

    # Show diagnostics if any
    if diagnostics:
        _render_diagnostics(diagnostics)


def _render_no_match(diagnostics: list[tuple[str, str]], trace: dict[str, Any]) -> None:
    """Render a no-match result."""
    with ui.card().classes("w-full bg-yellow-50 border-yellow-200"):
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon("warning").classes("text-yellow-600 text-2xl")
            ui.label("No Match").classes("text-xl font-semibold text-yellow-800")

        ui.label("The filename did not match any patterns for this sport.").classes("text-gray-600")

    _render_diagnostics(diagnostics)

    # Show trace info if available
    if trace:
        with ui.expansion("Match Trace", icon="bug_report").classes("w-full mt-2"):
            with ui.column().classes("gap-1 font-mono text-xs"):
                for key, value in trace.items():
                    if key not in ("diagnostics",):
                        with ui.row().classes("gap-2"):
                            ui.label(f"{key}:").classes("text-gray-600 w-32")
                            ui.label(str(value)[:100]).classes("text-gray-800 truncate")


def _render_diagnostics(diagnostics: list[tuple[str, str]]) -> None:
    """Render diagnostic messages."""
    if not diagnostics:
        return

    with ui.expansion("Diagnostics", icon="info").classes("w-full mt-2"):
        with ui.column().classes("gap-1"):
            for severity, message in diagnostics:
                color = {
                    "error": "text-red-600",
                    "warning": "text-yellow-600",
                    "info": "text-blue-600",
                }.get(severity, "text-gray-600")

                with ui.row().classes("gap-2"):
                    ui.label(f"[{severity.upper()}]").classes(f"font-mono text-xs w-20 {color}")
                    ui.label(message).classes("text-sm text-gray-700")
