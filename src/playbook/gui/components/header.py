"""
Navigation header component for the Playbook GUI.
"""

from __future__ import annotations

from nicegui import ui

from ..state import gui_state


def header() -> None:
    """Render the navigation header with links to all pages."""
    with ui.header().classes("bg-blue-900 text-white shadow-lg"):
        with ui.row().classes("w-full max-w-7xl mx-auto items-center px-4 py-2"):
            # Logo and title
            with ui.row().classes("items-center gap-2"):
                ui.icon("sports_soccer").classes("text-2xl")
                ui.link("Playbook", "/").classes("text-xl font-bold text-white no-underline hover:text-blue-200")

            ui.space()

            # Navigation links
            with ui.row().classes("gap-1"):
                _nav_link("Dashboard", "/", "dashboard")
                _nav_link("Logs", "/logs", "article")
                _nav_link("Config", "/config", "settings")
                _nav_link("Sports", "/sports", "emoji_events")

            ui.space()

            # Status indicator
            with ui.row().classes("items-center gap-2"):
                _status_indicator()


def _nav_link(label: str, target: str, icon: str) -> None:
    """Create a navigation link with icon."""
    with ui.link(target=target).classes("text-white no-underline"):
        with ui.row().classes("items-center gap-1 px-3 py-1 rounded hover:bg-blue-800 transition-colors"):
            ui.icon(icon).classes("text-lg")
            ui.label(label).classes("text-sm font-medium")


def _status_indicator() -> None:
    """Show processing status indicator."""
    status_icon = ui.icon("circle").classes("text-sm")
    status_label = ui.label("Idle").classes("text-xs")

    def update_status() -> None:
        if gui_state.is_processing:
            status_icon.classes(replace="text-green-400 animate-pulse")
            status_label.text = "Processing"
        else:
            status_icon.classes(replace="text-gray-400")
            status_label.text = "Idle"

    ui.timer(1.0, update_status)
    update_status()
