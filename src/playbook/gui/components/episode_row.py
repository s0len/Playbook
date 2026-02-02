"""
Episode row component for the Playbook GUI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from .status_chip import status_icon

if TYPE_CHECKING:
    from ..data.sport_data import EpisodeMatchStatus


def episode_row(
    episode: EpisodeMatchStatus,
    *,
    season_index: int = 0,
    on_click: callable | None = None,
) -> ui.element:
    """Create an episode row with status indicator.

    Args:
        episode: Episode match status data
        season_index: Season index for display code
        on_click: Optional click handler for viewing details

    Returns:
        The row container element
    """
    # Determine row styling based on status
    status_class = f"episode-row episode-row-{episode.status}"

    if on_click and episode.status == "matched":
        status_class += " cursor-pointer"

    with ui.row().classes(f"{status_class} w-full items-center gap-4") as row:
        # Status icon
        status_icon(episode.status)

        # Episode code
        code = f"S{season_index:02d}{episode.formatted_code}"
        ui.label(code).classes("font-mono text-sm text-slate-500 dark:text-slate-400 w-16 shrink-0")

        # Episode title
        ui.label(episode.episode_title).classes("flex-1 text-slate-800 dark:text-slate-200 truncate")

        # Air date
        if episode.air_date:
            date_str = episode.air_date.strftime("%b %d, %Y")
            ui.label(date_str).classes("text-sm text-slate-500 dark:text-slate-400 w-28 shrink-0 text-right")

        # View button for matched episodes
        if episode.status == "matched" and on_click:
            ui.button(icon="visibility", on_click=lambda: on_click(episode)).props("flat dense round").classes(
                "text-slate-500 dark:text-slate-400"
            )

    if on_click and episode.status == "matched":
        row.on("click", lambda: on_click(episode))

    return row


def episode_detail_dialog(episode: EpisodeMatchStatus) -> None:
    """Show a dialog with episode file details.

    Args:
        episode: Episode match status with record
    """
    if not episode.record:
        ui.notify("No file record available", type="warning")
        return

    record = episode.record

    with ui.dialog() as dialog, ui.card().classes("glass-card w-[600px] max-w-full"):
        # Header
        with ui.row().classes("w-full items-center justify-between mb-4"):
            ui.label(episode.episode_title).classes("text-xl font-semibold text-slate-800 dark:text-slate-200")
            ui.button(icon="close", on_click=dialog.close).props("flat round dense")

        # File details
        with ui.column().classes("w-full gap-3"):
            _detail_row("Status", record.status.capitalize())
            _detail_row("Source", record.source_path, mono=True)
            _detail_row("Destination", record.destination_path, mono=True)
            _detail_row("Sport", record.sport_id)
            _detail_row("Season", f"S{record.season_index:02d}")
            _detail_row("Episode", f"E{record.episode_index:02d}")
            _detail_row("Processed", record.processed_at.strftime("%Y-%m-%d %H:%M:%S"))

            if record.checksum:
                _detail_row("Checksum", record.checksum[:16] + "...", mono=True)

            if record.error_message:
                with ui.row().classes("w-full items-start gap-2 mt-2"):
                    ui.label("Error:").classes("text-sm font-medium text-red-600 dark:text-red-400 w-24 shrink-0")
                    ui.label(record.error_message).classes("text-sm text-red-600 dark:text-red-400 break-all")

    dialog.open()


def _detail_row(label: str, value: str, *, mono: bool = False) -> None:
    """Create a detail row with label and value."""
    with ui.row().classes("w-full items-start gap-2"):
        ui.label(f"{label}:").classes("text-sm font-medium text-slate-600 dark:text-slate-400 w-24 shrink-0")
        value_classes = "text-sm text-slate-800 dark:text-slate-200 break-all"
        if mono:
            value_classes += " font-mono"
        ui.label(value).classes(value_classes)
