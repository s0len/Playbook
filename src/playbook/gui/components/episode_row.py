"""
Episode row component for the Playbook GUI.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from nicegui import ui

from .app_button import neutralize_button_utilities
from .status_chip import status_icon

if TYPE_CHECKING:
    from playbook.persistence import ProcessedFileRecord

    from ..data.sport_data import EpisodeMatchStatus

LOGGER = logging.getLogger(__name__)


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
        ui.label(code).classes("font-mono text-sm app-text-muted w-16 shrink-0")

        # Episode title
        ui.label(episode.episode_title).classes("flex-1 truncate")

        # Quality score badge (if matched and has score)
        if episode.status == "matched" and episode.record and episode.record.quality_score is not None:
            score = episode.record.quality_score
            score_class = _quality_score_class(score)
            ui.badge(str(score)).classes(f"text-xs app-badge {score_class}")

        # File count badge (if multiple files tracked)
        if episode.file_count > 1:
            ui.badge(f"{episode.file_count} files").classes("text-xs app-badge app-badge-muted")

        # Air date
        if episode.air_date:
            date_str = episode.air_date.strftime("%b %d, %Y")
            ui.label(date_str).classes("text-sm app-text-muted w-28 shrink-0 text-right")

        # View button for matched episodes
        if episode.status == "matched" and on_click:
            view_button = neutralize_button_utilities(
                ui.button(icon="visibility", on_click=lambda: on_click(episode)).props("flat dense round")
            )
            view_button.classes("episode-row-action-btn app-text-muted")

    if on_click and episode.status == "matched":
        row.on("click", lambda: on_click(episode))

    return row


def _quality_score_class(score: int) -> str:
    """Get semantic badge class for a quality score."""
    if score >= 500:
        return "app-badge-success"
    if score >= 400:
        return "app-badge-success"
    if score >= 300:
        return "app-badge-muted"
    if score >= 200:
        return "app-badge-warning"
    return "app-badge-danger"


def _parse_quality_info(record: ProcessedFileRecord) -> dict | None:
    """Parse quality_info JSON from a record."""
    if not record.quality_info:
        return None
    try:
        return json.loads(record.quality_info)
    except (json.JSONDecodeError, TypeError):
        return None


def _format_quality_tags(quality: dict) -> list[tuple[str, str]]:
    """Format quality info dict into displayable (label, class) tag pairs."""
    tags: list[tuple[str, str]] = []

    if resolution := quality.get("resolution"):
        badge_class = "app-badge-success" if "2160" in resolution else "app-badge-muted"
        tags.append((resolution, badge_class))

    if frame_rate := quality.get("frame_rate"):
        if frame_rate and int(frame_rate) >= 50:
            tags.append((f"{frame_rate}fps", "app-badge-muted"))

    if source := quality.get("source"):
        tags.append((source, "app-badge-muted"))

    if codec := quality.get("codec"):
        tags.append((codec, "app-badge-muted"))

    if hdr := quality.get("hdr_format"):
        tags.append((str(hdr), "app-badge-warning"))

    if bit_depth := quality.get("bit_depth"):
        if bit_depth == 10:
            tags.append(("10-bit", "app-badge-success"))

    if audio := quality.get("audio"):
        tags.append((audio, "app-badge-muted"))

    if broadcaster := quality.get("broadcaster"):
        tags.append((broadcaster, "app-badge-muted"))

    if quality.get("is_proper"):
        tags.append(("PROPER", "app-badge-danger"))
    if quality.get("is_repack"):
        tags.append(("REPACK", "app-badge-danger"))

    if group := quality.get("release_group"):
        tags.append((group, "app-badge-muted"))

    return tags


def episode_detail_dialog(episode: EpisodeMatchStatus) -> None:
    """Show a dialog with episode file details and all tracked candidates.

    Args:
        episode: Episode match status with record(s)
    """
    if not episode.record:
        ui.notify("No file record available", type="warning")
        return

    all_records = episode.all_records if episode.all_records else [episode.record]

    with ui.dialog() as dialog, ui.card().classes("glass-card w-[800px] max-w-full max-h-[80vh] view-shell"):
        # Header
        with ui.row().classes("w-full items-center justify-between mb-4"):
            with ui.column().classes("gap-0"):
                ui.label(episode.episode_title).classes("text-xl font-semibold")
                if episode.air_date:
                    ui.label(episode.air_date.strftime("%b %d, %Y")).classes("text-sm app-text-muted")
            neutralize_button_utilities(ui.button(icon="close", on_click=dialog.close).props("flat round dense"))

        # Destination
        _detail_row("Destination", episode.record.destination_path, mono=True)
        ui.separator().classes("my-2")

        # File candidates table
        candidates_container = ui.column().classes("w-full gap-0")

        def render_candidates() -> None:
            candidates_container.clear()
            with candidates_container:
                header_text = f"Tracked Files ({len(all_records)})" if len(all_records) > 1 else "Source File"
                ui.label(header_text).classes("text-sm font-semibold app-text-muted mb-2")

                for idx, record in enumerate(all_records):
                    is_active = record.source_path == episode.record.source_path
                    on_promote = None
                    if not is_active and len(all_records) > 1:

                        def make_promote_handler(rec=record):
                            def handler():
                                _promote_file(rec, episode, dialog)

                            return handler

                        on_promote = make_promote_handler()
                    _file_candidate_row(record, rank=idx + 1, is_active=is_active, on_promote=on_promote)

        render_candidates()

    dialog.open()


def _file_candidate_row(
    record: ProcessedFileRecord,
    *,
    rank: int,
    is_active: bool,
    on_promote: callable | None = None,
) -> None:
    """Render a single file candidate row with quality details."""
    border_class = "border-l-4 border-white/20" if is_active else "border-l-4 border-transparent"
    bg_class = "app-alert app-alert-success" if is_active else ""

    with ui.column().classes(f"w-full p-3 rounded {border_class} {bg_class} gap-2 mb-1"):
        # Top row: rank, filename, score
        with ui.row().classes("w-full items-center gap-2"):
            # Rank badge
            if is_active:
                ui.icon("check_circle").classes("app-text-success text-lg")
            else:
                ui.label(f"#{rank}").classes("text-xs font-mono app-text-muted w-6 text-center")

            # Filename (just the name, not full path)
            filename = Path(record.source_path).name
            ui.label(filename).classes("flex-1 text-sm font-mono truncate")

            # Quality score
            if record.quality_score is not None:
                score_class = _quality_score_class(record.quality_score)
                ui.badge(f"Score: {record.quality_score}").classes(f"app-badge {score_class}")

            # Status chip
            status_classes = {
                "linked": "app-badge-success",
                "copied": "app-badge-muted",
                "symlinked": "app-badge-muted",
                "skipped": "app-badge-warning",
                "superseded": "app-badge-warning",
                "error": "app-badge-danger",
            }
            chip_class = status_classes.get(record.status, "app-badge-muted")
            ui.badge(record.status).classes(f"app-badge {chip_class}")

            # Make Primary button for non-active candidates
            if on_promote:
                neutralize_button_utilities(
                    ui.button("Make Primary", icon="swap_horiz", on_click=on_promote).props("flat dense no-caps")
                ).classes("text-xs text-slate-400 hover:text-slate-200")

        # Quality tags row
        quality = _parse_quality_info(record)
        if quality:
            tags = _format_quality_tags(quality)
            if tags:
                with ui.row().classes("flex-wrap gap-1 ml-8"):
                    for label, color in tags:
                        ui.badge(label).classes(f"text-xs app-badge {color}")

        # Metadata row
        with ui.row().classes("ml-8 gap-4"):
            ui.label(record.processed_at.strftime("%Y-%m-%d %H:%M")).classes("text-xs app-text-muted")
            if record.error_message:
                ui.label(record.error_message).classes("text-xs app-text-danger")


def _promote_file(record: ProcessedFileRecord, episode: EpisodeMatchStatus, dialog) -> None:
    """Promote a file to be the primary (active) link for an episode.

    Replaces the destination file with a link to the selected source.
    """
    from ..state import gui_state

    source = Path(record.source_path)
    destination = Path(record.destination_path)

    if not source.exists():
        ui.notify(f"Source file not found: {source.name}", type="negative")
        return

    # Determine link mode from config
    link_mode = "hardlink"
    if gui_state.config and gui_state.config.settings:
        link_mode = gui_state.config.settings.link_mode or "hardlink"

    try:
        # Remove existing destination
        if destination.exists():
            destination.unlink()

        # Create new link
        from playbook.utils import link_file

        result = link_file(source, destination, mode=link_mode)
        if not result.created:
            ui.notify(f"Failed to link file: {result.reason}", type="negative")
            return

        # Update the store: mark promoted file as linked, demote old primary to superseded
        store = gui_state.processed_store
        if store:
            old_primary = episode.record
            if old_primary and old_primary.source_path != record.source_path:
                store.update_status(old_primary.source_path, "superseded")
            store.update_status(record.source_path, "linked")

        ui.notify(f"Switched primary to {source.name}", type="positive")
        LOGGER.info("Promoted %s as primary for %s", source.name, destination)

        # Close and refresh page
        dialog.close()
        ui.navigate.reload()

    except Exception as e:
        LOGGER.exception("Failed to promote file: %s", e)
        ui.notify(f"Error: {e}", type="negative")


def _detail_row(label: str, value: str, *, mono: bool = False) -> None:
    """Create a detail row with label and value."""
    with ui.row().classes("w-full items-start gap-2"):
        ui.label(f"{label}:").classes("text-sm font-medium app-text-muted w-24 shrink-0")
        value_classes = "text-sm break-all"
        if mono:
            value_classes += " font-mono"
        ui.label(value).classes(value_classes)
