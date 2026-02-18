"""
Unmatched files management page for the Playbook GUI.

Displays files that failed pattern matching with:
- Category filtering (video, sample, metadata, archive)
- Search and sport filtering
- Detailed match failure analysis
- Manual matching capability
"""

from __future__ import annotations

import logging
from datetime import datetime

from nicegui import ui

from ..state import gui_state
from ..utils import safe_notify

LOGGER = logging.getLogger(__name__)

# Default filter state - show only videos, hide samples/metadata/archives
DEFAULT_CATEGORIES = ["video"]


def unmatched_page() -> None:
    """Render the unmatched files management page."""

    # State for filters - use a class instance to allow mutation from nested functions
    class State:
        categories: list = None
        search_query: str = ""
        sport_filter: str = ""
        page: int = 0
        page_size: int = 50
        results_container: ui.column = None
        stats_container: ui.row = None

    state = State()
    state.categories = list(DEFAULT_CATEGORIES)

    def refresh_results():
        """Refresh the results after filter change."""
        if state.results_container:
            state.results_container.clear()
            with state.results_container:
                _render_results_content(state, refresh_results, refresh_page)

    def refresh_page():
        """Full page refresh including stats and results."""
        state.page = 0
        # Refresh stats
        if state.stats_container:
            state.stats_container.clear()
            with state.stats_container:
                _render_stats_content()
        # Refresh results
        refresh_results()

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-6"):
        # Page title with refresh button
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Unmatched Files").classes("text-3xl font-bold text-slate-800 dark:text-slate-100")
            with ui.row().classes("gap-2"):
                ui.button(
                    "Rescan",
                    icon="refresh",
                    on_click=lambda: _trigger_rescan(refresh_page),
                ).props("flat").classes("text-slate-600 dark:text-slate-400")

        # Stats overview
        state.stats_container = ui.row().classes("w-full gap-4 flex-wrap")
        with state.stats_container:
            _render_stats_content()

        # Filters card
        with ui.card().classes("glass-card w-full"):
            _filters_section_v2(state, refresh_results)

        # Results container
        state.results_container = ui.column().classes("w-full gap-4")
        with state.results_container:
            _render_results_content(state, refresh_results, refresh_page)


def _render_stats_content() -> None:
    """Render statistics content inside the stats container."""
    if not gui_state.unmatched_store:
        return

    try:
        stats = gui_state.unmatched_store.get_stats()
        category_counts = gui_state.unmatched_store.get_category_counts()
    except Exception as e:
        LOGGER.warning("Failed to get unmatched stats: %s", e)
        return

    with ui.row().classes("w-full gap-4 flex-wrap"):
        # Total unmatched
        total = stats.get("total", 0)
        hidden = stats.get("hidden", 0)
        _stat_card("Total Unmatched", total - hidden, "help_outline", "amber")

        # Videos
        video_count = category_counts.get("video", 0)
        _stat_card("Videos", video_count, "movie", "blue")

        # Samples
        sample_count = category_counts.get("sample", 0)
        _stat_card("Samples", sample_count, "content_cut", "slate")

        # Other files
        other_count = (
            category_counts.get("metadata", 0) + category_counts.get("archive", 0) + category_counts.get("other", 0)
        )
        _stat_card("Other", other_count, "folder", "slate")


def _stat_card(label: str, value: int, icon: str, color: str) -> None:
    """Render a statistics card."""
    with ui.card().classes("glass-card p-4 min-w-32"):
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon).classes(f"text-{color}-500 dark:text-{color}-400 text-xl")
            with ui.column().classes("gap-0"):
                ui.label(str(value)).classes("text-2xl font-bold text-slate-800 dark:text-slate-100")
                ui.label(label).classes("text-sm text-slate-500 dark:text-slate-400")


def _filters_section_v2(state, on_filter_change) -> None:
    """Render the filters section with reactive updates."""
    # Container for category toggles that can be refreshed
    toggle_container = None

    def refresh_toggles():
        """Refresh toggle button states."""
        nonlocal toggle_container
        if toggle_container:
            toggle_container.clear()
            with toggle_container:
                _render_category_toggles(state, on_filter_change, refresh_toggles)

    with ui.column().classes("w-full gap-4"):
        ui.label("Filters").classes("text-lg font-semibold text-slate-700 dark:text-slate-200")

        # Category toggles container
        toggle_container = ui.row().classes("gap-4 flex-wrap")
        with toggle_container:
            _render_category_toggles(state, on_filter_change, refresh_toggles)

        # Search and sport filter
        with ui.row().classes("w-full gap-4 flex-wrap"):
            # Use on_change parameter for real-time filtering as user types
            def on_search_change(e):
                state.search_query = e.sender.value or ""
                state.page = 0  # Reset to first page on search
                on_filter_change()

            ui.input(
                label="Search filename",
                placeholder="e.g., Formula.1",
                on_change=on_search_change,
            ).classes("flex-1 min-w-48").props('debounce="300"')

            # Sport filter dropdown
            sport_options = ["All Sports"]
            if gui_state.config:
                sport_options.extend([s.id for s in gui_state.config.sports if s.enabled])

            def on_sport_change(e):
                state.sport_filter = "" if e.value == "All Sports" else e.value
                state.page = 0  # Reset to first page on filter change
                on_filter_change()

            ui.select(
                sport_options,
                value="All Sports",
                label="Sport",
                on_change=on_sport_change,
            ).classes("w-48")


def _render_category_toggles(state, on_filter_change, refresh_toggles) -> None:
    """Render the category toggle buttons."""
    ui.label("Categories:").classes("text-sm text-slate-600 dark:text-slate-400 self-center")

    categories_config = [
        ("video", "Videos", "movie"),
        ("sample", "Samples", "content_cut"),
        ("metadata", "Metadata", "description"),
        ("archive", "Archives", "archive"),
        ("other", "Other", "folder"),
    ]

    for category, label, icon in categories_config:
        is_active = category in state.categories

        def make_toggle_handler(cat, st):
            def handler():
                if cat in st.categories:
                    st.categories.remove(cat)
                else:
                    st.categories.append(cat)
                st.page = 0  # Reset to first page on filter change
                refresh_toggles()
                on_filter_change()

            return handler

        btn = ui.button(label, icon=icon, on_click=make_toggle_handler(category, state))
        if is_active:
            btn.props("color=primary")
        else:
            btn.props("flat color=grey")
        btn.classes("text-sm")


def _render_results_content(state, refresh_results, refresh_page) -> None:
    """Render the results list content."""
    if not gui_state.unmatched_store:
        ui.label("Unmatched file store not available").classes("text-slate-500 dark:text-slate-400 italic py-8")
        return

    try:
        categories = state.categories if state.categories else None
        search = state.search_query if state.search_query else None
        sport = state.sport_filter if state.sport_filter else None

        records = gui_state.unmatched_store.get_all(
            categories=categories,
            search_query=search,
            sport_filter=sport,
            limit=state.page_size,
            offset=state.page * state.page_size,
        )
        total_count = gui_state.unmatched_store.get_count(
            categories=categories,
            search_query=search,
            sport_filter=sport,
        )
    except Exception as e:
        LOGGER.exception("Failed to get unmatched files: %s", e)
        ui.label(f"Error loading unmatched files: {e}").classes("text-red-600 dark:text-red-400")
        return

    # Results header
    with ui.row().classes("w-full items-center justify-between"):
        ui.label(f"Showing {len(records)} of {total_count} files").classes("text-sm text-slate-500 dark:text-slate-400")

        # Pagination
        if total_count > state.page_size:
            total_pages = (total_count + state.page_size - 1) // state.page_size
            with ui.row().classes("gap-2 items-center"):

                def go_prev():
                    if state.page > 0:
                        state.page -= 1
                        refresh_results()

                def go_next():
                    if (state.page + 1) * state.page_size < total_count:
                        state.page += 1
                        refresh_results()

                ui.button(
                    icon="chevron_left",
                    on_click=go_prev,
                ).props("flat round dense")

                ui.label(f"Page {state.page + 1} of {total_pages}").classes(
                    "text-sm text-slate-600 dark:text-slate-400"
                )

                ui.button(
                    icon="chevron_right",
                    on_click=go_next,
                ).props("flat round dense")

    if not records:
        with ui.card().classes("glass-card w-full p-8"):
            with ui.column().classes("items-center gap-2"):
                ui.icon("check_circle").classes("text-green-500 text-4xl")
                ui.label("No unmatched files found").classes("text-lg font-medium text-slate-700 dark:text-slate-300")
                ui.label("Try adjusting your filters or run a scan").classes(
                    "text-sm text-slate-500 dark:text-slate-400"
                )
    else:
        # File cards
        for record in records:
            _file_card(record, state, refresh_page)


def _file_card(record, state, refresh_page) -> None:
    """Render a single file card."""
    from playbook.persistence import UnmatchedFileRecord

    record: UnmatchedFileRecord

    with ui.card().classes("glass-card w-full"):
        with ui.row().classes("w-full items-start gap-4"):
            # File icon based on category
            icon_map = {
                "video": ("movie", "blue"),
                "sample": ("content_cut", "amber"),
                "metadata": ("description", "slate"),
                "archive": ("archive", "slate"),
                "other": ("insert_drive_file", "slate"),
            }
            icon_name, icon_color = icon_map.get(record.file_category, ("insert_drive_file", "slate"))
            ui.icon(icon_name).classes(f"text-{icon_color}-500 dark:text-{icon_color}-400 text-2xl mt-1")

            # Main content
            with ui.column().classes("flex-1 gap-1"):
                # Filename
                ui.label(record.filename).classes("text-base font-medium text-slate-800 dark:text-slate-100 break-all")

                # Metadata row
                with ui.row().classes("gap-4 flex-wrap"):
                    # File size
                    size_str = _format_file_size(record.file_size)
                    ui.label(f"Size: {size_str}").classes("text-xs text-slate-500 dark:text-slate-400")

                    # First seen
                    first_seen_str = _format_relative_time(record.first_seen)
                    ui.label(f"First seen: {first_seen_str}").classes("text-xs text-slate-500 dark:text-slate-400")

                    # Category badge
                    ui.badge(record.file_category, color=icon_color).classes("text-xs")

                # Failure summary - shows why the best match failed
                if record.failure_summary:
                    with ui.row().classes("items-start gap-2 mt-2"):
                        ui.icon("warning").classes("text-amber-500 dark:text-amber-400 text-sm mt-0.5")
                        ui.label(record.failure_summary).classes("text-sm text-slate-600 dark:text-slate-400")
                elif record.best_match_sport:
                    # Fallback: show best match sport if no failure summary
                    with ui.row().classes("items-center gap-2 mt-2"):
                        ui.label("Best match:").classes("text-xs text-slate-500 dark:text-slate-400")
                        ui.badge(record.best_match_sport, color="blue").classes("text-xs")

            # Action buttons
            with ui.column().classes("gap-2"):
                ui.button(
                    "Details",
                    icon="info",
                    on_click=lambda r=record: _show_details_dialog(r),
                ).props("flat dense").classes("text-sm")

                ui.button(
                    "Match",
                    icon="link",
                    on_click=lambda r=record, rp=refresh_page: _show_manual_match_dialog_v2(r, rp),
                ).props("flat dense color=primary").classes("text-sm")

                ui.button(
                    "Hide",
                    icon="visibility_off",
                    on_click=lambda r=record, rp=refresh_page: _hide_file_v2(r.source_path, rp),
                ).props("flat dense").classes("text-sm text-slate-500")


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time string."""
    now = datetime.now()
    delta = now - dt

    if delta.days > 30:
        return dt.strftime("%Y-%m-%d")
    elif delta.days > 1:
        return f"{delta.days}d ago"
    elif delta.days == 1:
        return "Yesterday"
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"{hours}h ago"
    elif delta.seconds > 60:
        minutes = delta.seconds // 60
        return f"{minutes}m ago"
    else:
        return "Just now"


async def _trigger_rescan(refresh_callback=None) -> None:
    """Trigger a processing run to rescan files."""
    import asyncio

    from nicegui import context

    if not gui_state.processor:
        ui.notify("Processor not available", type="warning")
        return

    if gui_state.is_processing:
        ui.notify("Scan already in progress", type="warning")
        return

    # Capture client reference before async operation (for notifications after executor completes)
    client = context.client

    ui.notify("Starting scan in background...", type="info")
    gui_state.set_processing(True)

    try:
        # Run process_all in a separate thread
        await asyncio.get_event_loop().run_in_executor(None, gui_state.processor.process_all)
        # Skip UI updates if client disconnected during async operation
        if getattr(client, "_deleted", False):
            LOGGER.debug("Skipping post-scan UI update - client disconnected")
            return
        # Use safe_notify for notification after async operation (client may have disconnected)
        safe_notify(client, "Scan complete!", type="positive")
        # Refresh the page to show updated list
        if refresh_callback:
            refresh_callback()
    except Exception as e:
        LOGGER.exception("Scan failed: %s", e)
        safe_notify(client, f"Scan failed: {e}", type="negative")
    finally:
        gui_state.set_processing(False)


def _hide_file_v2(source_path: str, refresh_page) -> None:
    """Hide a file from the unmatched list."""
    if not gui_state.unmatched_store:
        return

    try:
        gui_state.unmatched_store.hide_file(source_path)
        ui.notify("File hidden", type="info")
        refresh_page()
    except Exception as e:
        LOGGER.exception("Failed to hide file: %s", e)
        ui.notify(f"Failed to hide file: {e}", type="negative")


def _show_details_dialog(record) -> None:
    """Show detailed match analysis dialog."""
    from playbook.persistence import UnmatchedFileRecord

    record: UnmatchedFileRecord

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-3xl"):
        with ui.column().classes("w-full gap-4"):
            # Header
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Match Analysis").classes("text-xl font-semibold text-slate-800 dark:text-slate-100")
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")

            ui.separator()

            # File info
            with ui.column().classes("gap-2"):
                ui.label("File Information").classes("text-lg font-medium text-slate-700 dark:text-slate-200")

                with ui.row().classes("gap-4"):
                    ui.label("Filename:").classes("font-semibold w-24 text-slate-600 dark:text-slate-400")
                    ui.label(record.filename).classes("text-slate-800 dark:text-slate-200 break-all")

                with ui.row().classes("gap-4"):
                    ui.label("Path:").classes("font-semibold w-24 text-slate-600 dark:text-slate-400")
                    ui.label(record.source_path).classes(
                        "text-sm text-slate-600 dark:text-slate-400 break-all font-mono"
                    )

                with ui.row().classes("gap-4"):
                    ui.label("Size:").classes("font-semibold w-24 text-slate-600 dark:text-slate-400")
                    ui.label(_format_file_size(record.file_size)).classes("text-slate-800 dark:text-slate-200")

                with ui.row().classes("gap-4"):
                    ui.label("Category:").classes("font-semibold w-24 text-slate-600 dark:text-slate-400")
                    ui.badge(record.file_category).classes("text-sm")

            ui.separator()

            # Match attempts
            with ui.column().classes("gap-2"):
                attempts_count = len(record.match_attempts)
                sports_count = len(record.attempted_sports)
                ui.label(f"Match Attempts ({attempts_count} patterns across {sports_count} sports)").classes(
                    "text-lg font-medium text-slate-700 dark:text-slate-200"
                )

                if not record.match_attempts:
                    ui.label("No match attempts recorded").classes("text-slate-500 dark:text-slate-400 italic")
                else:
                    for attempt in record.match_attempts:
                        _render_match_attempt(attempt)

            ui.separator()

            # Suggestions
            with ui.column().classes("gap-2"):
                ui.label("Suggestions").classes("text-lg font-medium text-slate-700 dark:text-slate-200")
                _render_suggestions(record)

            # Close button
            with ui.row().classes("w-full justify-end"):
                ui.button("Close", on_click=dialog.close).props("flat")

    dialog.open()


def _render_match_attempt(attempt) -> None:
    """Render a single match attempt."""
    from playbook.persistence import MatchAttempt

    attempt: MatchAttempt

    # Status icon and color
    status_map = {
        "matched": ("check_circle", "green"),
        "episode-unresolved": ("warning", "amber"),
        "season-unresolved": ("warning", "amber"),
        "regex-no-match": ("close", "slate"),
        "glob-excluded": ("block", "slate"),
        "no-match": ("close", "slate"),
    }
    icon_name, color = status_map.get(attempt.status, ("help", "slate"))

    with ui.card().classes(f"w-full border-l-4 border-{color}-400 bg-{color}-50 dark:bg-{color}-900/20"):
        with ui.column().classes("gap-1 p-2"):
            # Header
            with ui.row().classes("items-center gap-2"):
                ui.icon(icon_name).classes(f"text-{color}-500 dark:text-{color}-400")
                ui.label(attempt.sport_name or attempt.sport_id).classes(
                    "font-medium text-slate-800 dark:text-slate-200"
                )
                ui.badge(attempt.status, color=color).classes("text-xs")

            # Pattern info
            if attempt.pattern_description:
                ui.label(f"Pattern: {attempt.pattern_description}").classes(
                    "text-sm text-slate-600 dark:text-slate-400"
                )

            # Failure reason
            if attempt.failure_reason:
                ui.label(attempt.failure_reason).classes("text-sm text-slate-700 dark:text-slate-300 break-all")

            # Captured groups (if any)
            if attempt.captured_groups:
                with ui.expansion("Captured Groups", icon="code").classes("w-full"):
                    with ui.column().classes("gap-1 font-mono text-xs"):
                        for key, value in attempt.captured_groups.items():
                            with ui.row().classes("gap-2"):
                                ui.label(f"{key}:").classes("text-slate-600 dark:text-slate-400 w-24")
                                ui.label(str(value)).classes("text-slate-800 dark:text-slate-200")


def _render_suggestions(record) -> None:
    """Render actionable suggestions based on match failures."""
    from playbook.persistence import UnmatchedFileRecord

    record: UnmatchedFileRecord

    suggestions = []

    # Analyze match attempts to generate suggestions
    has_regex_match = any(a.status in ("episode-unresolved", "season-unresolved") for a in record.match_attempts)
    has_no_regex_match = any(a.status in ("regex-no-match", "no-match") for a in record.match_attempts)
    has_episode_unresolved = any(a.status == "episode-unresolved" for a in record.match_attempts)
    has_season_unresolved = any(a.status == "season-unresolved" for a in record.match_attempts)

    if has_episode_unresolved:
        suggestions.append(
            ("Add episode alias", "The session/episode name wasn't found in metadata. Add an alias to the episode.")
        )

    if has_season_unresolved:
        suggestions.append(
            ("Add season alias", "The season couldn't be resolved. Check the season selector configuration.")
        )

    if has_no_regex_match and not has_regex_match:
        suggestions.append(
            (
                "Check pattern regex",
                "No patterns matched this filename. The file format may not be recognized.",
            )
        )

    if record.file_category == "sample":
        suggestions.append(
            ("Ignore sample files", "This appears to be a sample file. Sample files are filtered by default.")
        )

    if not suggestions:
        suggestions.append(
            ("Manual match", "Use the Manual Match button to manually link this file to a show/episode.")
        )

    for title, description in suggestions:
        with ui.row().classes("items-start gap-2"):
            ui.icon("lightbulb").classes("text-amber-500 text-sm mt-0.5")
            with ui.column().classes("gap-0"):
                ui.label(title).classes("font-medium text-slate-700 dark:text-slate-300")
                ui.label(description).classes("text-sm text-slate-500 dark:text-slate-400")


def _show_manual_match_dialog_v2(record, refresh_page) -> None:
    """Show manual match dialog (v2 with refresh callback)."""
    import re
    from pathlib import Path as _Path

    from playbook.persistence import UnmatchedFileRecord

    record: UnmatchedFileRecord

    if not gui_state.config:
        ui.notify("Configuration not loaded", type="warning")
        return

    # Extract year from filename once (used for dynamic sport slug resolution)
    _year_match = re.search(r"\b(20\d{2})\b", record.filename)
    year_hint: int | None = int(_year_match.group(1)) if _year_match else None

    # State for the dialog
    dialog_state = {
        "sport_id": record.best_match_sport or (gui_state.config.sports[0].id if gui_state.config.sports else ""),
        "season_index": None,
        "episode_index": None,
        "show": None,
        "seasons": [],
        "episodes": [],
    }

    def load_show_data(sport_id: str):
        """Load show data for the selected sport."""
        from playbook.metadata_loader import DynamicMetadataLoader

        if not gui_state.config:
            return

        sport = next((s for s in gui_state.config.sports if s.id == sport_id), None)
        if not sport:
            return

        # Reset state
        dialog_state["show"] = None
        dialog_state["seasons"] = []
        dialog_state["episodes"] = []
        dialog_state["season_index"] = None
        dialog_state["episode_index"] = None

        try:
            loader = DynamicMetadataLoader(settings=gui_state.config.settings)

            if sport.show_slug_template:
                # Dynamic sport – resolve the slug using the year from the filename
                if year_hint is None:
                    ui.notify("Cannot determine year for this sport from the filename", type="warning")
                    return
                show = loader.get_show_for_year(sport, year_hint)
            else:
                # Static sport
                show = loader.load_show(sport.show_slug, sport.season_overrides)

            if show is not None:
                dialog_state["show"] = show
                dialog_state["seasons"] = [(s.index, s.title) for s in show.seasons]
                if dialog_state["seasons"]:
                    dialog_state["season_index"] = dialog_state["seasons"][0][0]
                    load_episodes(dialog_state["season_index"])
                    auto_select_episode()
        except Exception as e:
            LOGGER.exception("Failed to load show data: %s", e)
            ui.notify(f"Failed to load sport data: {e}", type="negative")

    def auto_select_episode():
        """Fuzzy-match the filename against loaded episode titles and pre-select the best hit."""
        if not dialog_state["show"] or not dialog_state["episodes"]:
            return

        try:
            from rapidfuzz import fuzz, process

            season = next(
                (s for s in dialog_state["show"].seasons if s.index == dialog_state["season_index"]),
                None,
            )
            if not season or not season.episodes:
                return

            stem = _Path(record.filename).stem.replace(".", " ").replace("_", " ")
            raw_titles = [e.title for e in season.episodes]
            result = process.extractOne(stem, raw_titles, scorer=fuzz.partial_ratio)
            if result and result[1] >= 30:
                best_title = result[0]
                ep_idx = next((e.index for e in season.episodes if e.title == best_title), None)
                if ep_idx is not None:
                    dialog_state["episode_index"] = ep_idx
        except Exception:
            pass  # Auto-select is best-effort; don't break the dialog

    def load_episodes(season_index: int):
        """Load episodes for the selected season."""
        if not dialog_state["show"]:
            return

        season = next(
            (s for s in dialog_state["show"].seasons if s.index == season_index),
            None,
        )
        if season:
            dialog_state["episodes"] = [(e.index, f"E{e.index:02d} - {e.title}") for e in season.episodes]
            if dialog_state["episodes"]:
                dialog_state["episode_index"] = dialog_state["episodes"][0][0]

    def on_sport_change(e):
        dialog_state["sport_id"] = e.value
        load_show_data(e.value)

        season_select.options = [f"S{i:02d} - {t}" for i, t in dialog_state["seasons"]]
        if dialog_state["seasons"]:
            auto_idx = next(
                (i for i, (si, _) in enumerate(dialog_state["seasons"]) if si == dialog_state["season_index"]), 0
            )
            season_select.value = season_select.options[auto_idx]
        else:
            season_select.value = None

        episode_select.options = [t for _, t in dialog_state["episodes"]]
        if dialog_state["episodes"]:
            ep_auto_idx = next(
                (i for i, (ei, _) in enumerate(dialog_state["episodes"]) if ei == dialog_state["episode_index"]), 0
            )
            episode_select.value = episode_select.options[ep_auto_idx]
        else:
            episode_select.value = None

    def on_season_change(e):
        if dialog_state["seasons"] and e.value:
            try:
                idx = season_select.options.index(e.value)
                dialog_state["season_index"] = dialog_state["seasons"][idx][0]
                load_episodes(dialog_state["season_index"])
                episode_select.options = [t for _, t in dialog_state["episodes"]]
                if dialog_state["episodes"]:
                    episode_select.value = episode_select.options[0]
            except (ValueError, IndexError):
                pass

    def on_episode_change(e):
        if dialog_state["episodes"] and e.value:
            try:
                idx = episode_select.options.index(e.value)
                dialog_state["episode_index"] = dialog_state["episodes"][idx][0]
            except (ValueError, IndexError):
                pass

    async def do_manual_match():
        """Execute the manual match."""
        import asyncio

        from nicegui import context

        if dialog_state["season_index"] is None or dialog_state["episode_index"] is None:
            ui.notify("Please select a season and episode", type="warning")
            return

        # Check if a scan is already running
        if gui_state.is_processing:
            ui.notify("A scan is in progress. Please wait for it to complete.", type="warning")
            return

        sport = next((s for s in gui_state.config.sports if s.id == dialog_state["sport_id"]), None)
        if not sport or not dialog_state["show"]:
            ui.notify("Invalid selection", type="warning")
            return

        season = next(
            (s for s in dialog_state["show"].seasons if s.index == dialog_state["season_index"]),
            None,
        )
        episode = (
            next(
                (e for e in season.episodes if e.index == dialog_state["episode_index"]),
                None,
            )
            if season
            else None
        )

        if not season or not episode:
            ui.notify("Season or episode not found", type="warning")
            return

        # Capture client reference before closing dialog (for notifications after async task)
        client = context.client

        # Close dialog immediately for better UX
        dialog.close()
        ui.notify("Processing match...", type="info")

        # Capture values for the background task
        match_record = record
        match_sport = sport
        match_show = dialog_state["show"]
        match_season = season
        match_episode = episode

        try:
            # Run the match in background thread
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _execute_manual_match(match_record, match_sport, match_show, match_season, match_episode),
            )
            # Skip UI updates if client disconnected during async operation
            if getattr(client, "_deleted", False):
                LOGGER.debug("Skipping post-match UI update - client disconnected")
                return
            # Use safe_notify for notification after dialog is closed (client may have disconnected)
            safe_notify(client, "File matched successfully!", type="positive")
            refresh_page()
        except Exception as e:
            LOGGER.exception("Manual match failed: %s", e)
            safe_notify(client, f"Match failed: {e}", type="negative")

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
        with ui.column().classes("w-full gap-4"):
            # Header
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Manual Match").classes("text-xl font-semibold text-slate-800 dark:text-slate-100")
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")

            ui.separator()

            # File info
            ui.label(f"File: {record.filename}").classes("text-sm text-slate-600 dark:text-slate-400 break-all")

            # Sport selector
            sport_options = [s.id for s in gui_state.config.sports if s.enabled]
            ui.select(
                sport_options,
                value=dialog_state["sport_id"],
                label="Sport",
                on_change=on_sport_change,
            ).classes("w-full")

            # Load initial data
            load_show_data(dialog_state["sport_id"])

            # Season selector
            season_options = [f"S{i:02d} - {t}" for i, t in dialog_state["seasons"]]
            _season_auto_idx = next(
                (i for i, (si, _) in enumerate(dialog_state["seasons"]) if si == dialog_state["season_index"]), 0
            )
            season_select = ui.select(
                season_options,
                value=season_options[_season_auto_idx] if season_options else None,
                label="Season",
                on_change=on_season_change,
            ).classes("w-full")

            # Episode selector
            episode_options = [t for _, t in dialog_state["episodes"]]
            _ep_auto_idx = next(
                (i for i, (ei, _) in enumerate(dialog_state["episodes"]) if ei == dialog_state["episode_index"]), 0
            )
            episode_select = ui.select(
                episode_options,
                value=episode_options[_ep_auto_idx] if episode_options else None,
                label="Episode",
                on_change=on_episode_change,
            ).classes("w-full")

            ui.separator()

            # Preview
            with ui.column().classes("gap-1"):
                ui.label("Destination Preview").classes("text-sm font-medium text-slate-600 dark:text-slate-400")
                ui.label("(Destination will be computed on match)").classes(
                    "text-sm text-slate-500 dark:text-slate-500 italic"
                )

            # Actions
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Match & Process", icon="link", on_click=do_manual_match).props("color=primary")

    dialog.open()


def _execute_manual_match(record, sport, show, season, episode) -> None:
    """Execute the manual match and process the file."""
    from pathlib import Path

    from playbook.destination_builder import build_destination, build_match_context  # noqa: F811
    from playbook.matcher import compile_patterns
    from playbook.models import SportFileMatch
    from playbook.persistence import UnmatchedFileRecord

    record: UnmatchedFileRecord

    if not gui_state.processor or not gui_state.config:
        raise ValueError("Processor or config not available")

    processor = gui_state.processor
    settings = gui_state.config.settings

    # Compile patterns to get a pattern runtime
    patterns = compile_patterns(sport)
    if not patterns:
        raise ValueError("No patterns available for sport")

    pattern = patterns[0]  # Use first pattern for context building

    source_path = Path(record.source_path)

    # Build context
    context = build_match_context(
        runtime=type("Runtime", (), {"sport": sport, "show": show})(),
        source_path=source_path,
        season=season,
        episode=episode,
        groups={},
        source_dir=settings.source_dir,
    )

    # Build destination
    destination = build_destination(
        runtime=type("Runtime", (), {"sport": sport, "show": show})(),
        pattern=pattern,
        context=context,
        settings=settings,
    )

    # Create match object
    match = SportFileMatch(
        source_path=source_path,
        destination_path=destination,
        show=show,
        season=season,
        episode=episode,
        pattern=pattern,
        context=context,
        sport=sport,
    )

    # Process the match
    from playbook.models import ProcessingStats

    stats = ProcessingStats()
    processor._handle_match(match, stats)

    # Mark as manually matched in unmatched store
    if gui_state.unmatched_store:
        gui_state.unmatched_store.mark_manually_matched(
            record.source_path,
            show.key,
            season.index,
            episode.index,
        )
