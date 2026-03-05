"""
Season section component for the Playbook GUI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from .episode_row import episode_detail_dialog, episode_row
from .progress_bar import mini_progress_bar

if TYPE_CHECKING:
    from ..data.sport_data import SeasonMatchStatus


def season_section(
    season: SeasonMatchStatus,
    *,
    expanded: bool = False,
) -> ui.expansion:
    """Create a collapsible season section with episodes.

    Args:
        season: Season match status data
        expanded: Whether to start expanded

    Returns:
        The expansion element
    """
    # Determine progress variant
    progress = season.progress
    if progress >= 1.0:
        variant = "success"
    elif progress >= 0.5:
        variant = "info"
    elif progress > 0:
        variant = "warning"
    else:
        variant = "default"

    # Build header content
    header_text = f"{season.formatted_code} - {season.season_title}"

    with ui.expansion(value=expanded).classes("season-section w-full") as expansion:
        # Custom header slot
        with expansion.add_slot("header"):
            with ui.row().classes("w-full items-center gap-4 py-2"):
                # Season title
                ui.label(header_text).classes("font-medium text-slate-800 dark:text-slate-200 flex-1")

                # Progress bar
                mini_progress_bar(progress, variant=variant, width="w-32")

                # Count
                ui.label(f"{season.matched_count}/{season.total_count}").classes(
                    "text-sm text-slate-600 dark:text-slate-400 w-16 text-right"
                )

        # Episode list
        with ui.column().classes("w-full divide-y divide-slate-100 dark:divide-slate-800"):
            for episode in season.episodes:
                episode_row(
                    episode,
                    season_index=season.season_index,
                    on_click=_show_episode_detail if episode.status == "matched" else None,
                )

    return expansion


def _show_episode_detail(episode) -> None:
    """Show episode detail dialog."""
    episode_detail_dialog(episode)


def seasons_list(
    seasons: list[SeasonMatchStatus],
    *,
    expand_recent: bool = True,
    collapse_year_groups: bool = False,
) -> None:
    """Create a list of season sections.

    Inserts year divider headers when seasons have year_label set
    (dynamic sports spanning multiple years).

    Args:
        seasons: List of season match statuses
        expand_recent: Whether to expand the most recent (last) season
        collapse_year_groups: Whether to collapse each year into an expansion panel
    """
    if not seasons:
        ui.label("No seasons available").classes("text-slate-500 dark:text-slate-400 italic py-4")
        return

    with ui.column().classes("w-full gap-4"):
        has_year_labels = any(season.year_label for season in seasons)

        if collapse_year_groups and has_year_labels:
            grouped_seasons: dict[str, list[SeasonMatchStatus]] = {}
            for season in seasons:
                label = season.year_label or "Other"
                grouped_seasons.setdefault(label, []).append(season)

            year_groups = list(grouped_seasons.items())
            for group_index, (year_label, year_seasons) in enumerate(year_groups):
                matched_count = sum(season.matched_count for season in year_seasons)
                total_count = sum(season.total_count for season in year_seasons)
                year_header = f"{year_label} ({matched_count}/{total_count})"

                with ui.expansion(year_header, icon="calendar_month", value=False).classes("w-full"):
                    with ui.column().classes("w-full gap-2"):
                        is_last_group = group_index == len(year_groups) - 1
                        _render_season_group(year_seasons, expand_recent=expand_recent and is_last_group)
            return

        current_year: str | None = None
        for season in seasons:
            if season.year_label and season.year_label != current_year:
                current_year = season.year_label
                with ui.row().classes("w-full items-center gap-3 mt-2"):
                    ui.separator().classes("flex-1")
                    ui.label(current_year).classes("text-lg font-bold text-slate-600 dark:text-slate-300 px-2")
                    ui.separator().classes("flex-1")

        _render_season_group(seasons, expand_recent=expand_recent)


def _render_season_group(seasons: list[SeasonMatchStatus], *, expand_recent: bool) -> None:
    for i, season in enumerate(seasons):
        is_last = i == len(seasons) - 1
        expanded = expand_recent and is_last
        season_section(season, expanded=expanded)
