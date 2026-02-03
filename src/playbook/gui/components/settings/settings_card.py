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
    card_classes = "glass-card w-full opacity-60" if disabled else "glass-card w-full"

    with ui.card().classes(card_classes):
        if collapsible:
            with (
                ui.expansion(
                    text="",
                    value=default_expanded,
                )
                .classes("w-full")
                .props("dense expand-separator")
            ):
                # Custom header
                with ui.row().classes("w-full items-center gap-2").slot("header"):
                    if icon:
                        ui.icon(icon).classes("text-slate-500 dark:text-slate-400")
                    with ui.column().classes("gap-0 flex-1"):
                        with ui.row().classes("items-center gap-2"):
                            ui.label(title).classes("text-lg font-semibold text-slate-700 dark:text-slate-200")
                            if modified:
                                ui.badge("Modified").props("color=warning").classes("text-xs")
                        if description:
                            ui.label(description).classes("text-sm text-slate-500 dark:text-slate-400")

                # Content area
                with ui.column().classes("w-full gap-4 pt-2") as content:
                    yield content
        else:
            # Non-collapsible header
            with ui.row().classes("items-center gap-2 mb-4"):
                if icon:
                    ui.icon(icon).classes("text-slate-500 dark:text-slate-400 text-xl")
                with ui.column().classes("gap-0 flex-1"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label(title).classes("text-lg font-semibold text-slate-700 dark:text-slate-200")
                        if modified:
                            ui.badge("Modified").props("color=warning").classes("text-xs")
                    if description:
                        ui.label(description).classes("text-sm text-slate-500 dark:text-slate-400")

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
            ui.icon(icon).classes("text-slate-400 dark:text-slate-500 text-lg")
        ui.label(title).classes("text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide")
    if description:
        ui.label(description).classes("text-xs text-slate-500 dark:text-slate-400 mb-2")
