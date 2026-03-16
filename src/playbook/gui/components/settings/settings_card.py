"""
Settings card component for collapsible sections.

Provides a styled card wrapper for grouping related settings.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from nicegui import ui


@contextmanager
def settings_card(
    title: str,
    *,
    icon: str | None = None,
    description: str | None = None,
    collapsible: bool = False,
    default_expanded: bool = True,
    modified: bool = False,
    disabled: bool = False,
) -> Generator[ui.column, None, None]:
    """Create a settings section card with optional collapsibility.

    Args:
        title: Section title
        icon: Optional icon name (Material Icons)
        description: Optional description text below title
        collapsible: Whether the section can be collapsed
        default_expanded: Initial expanded state (if collapsible)
        modified: Whether to show modified indicator
        disabled: Whether the section is disabled

    Yields:
        The column container for section content
    """
    card_classes = "glass-card settings-surface w-full opacity-60" if disabled else "glass-card settings-surface w-full"

    with ui.card().classes(card_classes):
        if collapsible:
            expansion = (
                ui.expansion(
                    text="",
                    value=default_expanded,
                )
                .classes("w-full")
                .props("dense expand-separator")
            )
            with expansion:
                # Custom header in the header slot
                with expansion.add_slot("header"):
                    with ui.row().classes("w-full items-center gap-2"):
                        if icon:
                            ui.icon(icon).classes("app-text-muted")
                        with ui.column().classes("gap-0 flex-1"):
                            with ui.row().classes("items-center gap-2"):
                                ui.label(title).classes("text-lg font-semibold")
                                if modified:
                                    ui.badge("Modified").classes("text-xs app-badge app-badge-muted")
                            if description:
                                ui.label(description).classes("text-sm app-text-muted")

                # Content area
                with ui.column().classes("w-full gap-4 pt-2") as content:
                    yield content
        else:
            # Non-collapsible header
            with ui.row().classes("items-center gap-2 mb-4"):
                if icon:
                    ui.icon(icon).classes("app-text-muted text-xl")
                with ui.column().classes("gap-0 flex-1"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label(title).classes("text-lg font-semibold")
                        if modified:
                            ui.badge("Modified").classes("text-xs app-badge app-badge-muted")
                    if description:
                        ui.label(description).classes("text-sm app-text-muted")

            # Content area
            with ui.column().classes("w-full gap-4") as content:
                yield content


def settings_section_header(
    title: str,
    *,
    icon: str | None = None,
    description: str | None = None,
) -> None:
    """Render a subsection header within a settings card.

    Args:
        title: Section title
        icon: Optional icon name
        description: Optional description
    """
    with ui.row().classes("items-center gap-2 mt-2"):
        if icon:
            ui.icon(icon).classes("app-text-muted text-lg")
        ui.label(title).classes("text-sm font-semibold app-text-muted")
    if description:
        ui.label(description).classes("text-xs app-text-muted mb-2")
