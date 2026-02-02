"""
Sports management page for the Playbook GUI.

Displays configured sports with match progress and provides:
- List view with progress tracking
- Detail view with season/episode breakdown
- Pattern tester tool
"""

from __future__ import annotations

import logging
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


def _sports_table() -> None:
    """Create the sports overview table with progress."""
    overviews = get_sports_overview()

    if not overviews:
        ui.label("No sports configured").classes("text-slate-500 dark:text-slate-400 italic py-4")
        return

    # Create table with custom rendering
    columns = [
        {"name": "status", "label": "Status", "field": "status", "align": "center"},
        {"name": "name", "label": "Sport", "field": "name", "align": "left", "sortable": True},
        {"name": "slug", "label": "Show Slug", "field": "slug", "align": "left"},
        {"name": "progress", "label": "Progress", "field": "progress", "align": "center"},
        {"name": "count", "label": "Matched", "field": "count", "align": "center"},
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
                "progress": overview.progress,
                "count": f"{overview.matched_count}/{overview.total_count}",
                "mode": overview.link_mode,
            }
        )

    table = ui.table(
        columns=columns,
        rows=rows,
        row_key="id",
        selection="single",
    ).classes("w-full modern-table")

    # Status badge slot
    table.add_slot(
        "body-cell-status",
        """
        <q-td :props="props">
            <q-badge :color="props.value === 'Enabled' ? 'positive' : 'grey'">
                {{ props.value }}
            </q-badge>
        </q-td>
        """,
    )

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

    # Progress bar slot
    table.add_slot(
        "body-cell-progress",
        """
        <q-td :props="props">
            <q-linear-progress
                :value="props.value"
                :color="props.value >= 1 ? 'positive' : props.value >= 0.5 ? 'primary' : 'warning'"
                class="w-24"
                rounded
                size="8px"
            />
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

    # Row click handler
    table.on("row-click", lambda e: ui.navigate.to(f"/sports/{e.args[1]['id']}"))


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

    try:
        from playbook.matcher import match_file_to_episode
        from playbook.metadata_loader import load_sports

        result = load_sports(
            sports=[sport],
            settings=gui_state.config.settings,
            metadata_fingerprints=None,
        )

        if not result.runtimes:
            with container:
                ui.label("Failed to load sport metadata").classes("text-red-600 dark:text-red-400")
            return

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

        with container:
            if detection:
                _render_match_result(detection, trace, diagnostics)
            else:
                _render_no_match(diagnostics, trace)

    except Exception as e:
        LOGGER.exception("Pattern test error: %s", e)
        with container:
            ui.label(f"Error testing pattern: {e}").classes("text-red-600 dark:text-red-400")


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
