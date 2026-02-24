"""
Navigation sidebar component for the Playbook GUI.
"""

from __future__ import annotations

from nicegui import ui

from ..state import gui_state

NAV_ITEMS = [
    ("/", "dashboard", "Dashboard"),
    ("/logs", "article", "Logs"),
    ("/sports", "emoji_events", "Sports"),
    ("/unmatched", "help_outline", "Unmatched"),
]

BOTTOM_ITEMS = [
    ("/config", "settings", "Settings"),
]


def header(current_path: str = "/") -> None:
    """Render the icon-only left navigation sidebar.

    Args:
        current_path: The current page path for active state highlighting
    """
    with (
        ui.left_drawer(value=True).props("persistent show-if-above width=60 bordered=false").classes("playbook-sidebar")
    ):
        with ui.column().classes("w-full h-full items-center py-4 gap-0"):
            # Logo at the top
            with ui.link(target="/").classes("no-underline mb-6"):
                ui.image("/icon.png").classes("w-9 h-9 rounded-xl object-cover")

            # Navigation items
            with ui.column().classes("w-full items-center gap-1"):
                for path, icon_name, label in NAV_ITEMS:
                    _sidebar_item(path, icon_name, label, _is_active(path, current_path))

            ui.space()

            # Bottom items (settings) and status indicator
            with ui.column().classes("w-full items-center gap-1"):
                for path, icon_name, label in BOTTOM_ITEMS:
                    _sidebar_item(path, icon_name, label, _is_active(path, current_path))
            _status_indicator()


def _is_active(nav_path: str, current_path: str) -> bool:
    """Check if a nav item should be marked active."""
    if nav_path == "/":
        return current_path == "/"
    return current_path == nav_path or current_path.startswith(nav_path + "/")


def _sidebar_item(target: str, icon_name: str, label: str, is_active: bool) -> None:
    """Render a single sidebar nav item."""
    cls = "sidebar-nav-item" + (" sidebar-nav-item-active" if is_active else "")
    with ui.link(target=target).classes("no-underline w-full flex justify-center") as link:
        with ui.element("div").classes(cls):
            ui.icon(icon_name).classes("text-[20px]")
    link.tooltip(label).props('anchor="center right" self="center left"')


def _status_indicator() -> None:
    """Show processing status indicator."""
    with ui.column().classes("items-center mt-2"):
        status_icon = ui.icon("circle").classes("text-sm text-slate-400")

        last_status = [None]

        def update_status() -> None:
            try:
                current = gui_state.is_processing
                if current != last_status[0]:
                    last_status[0] = current
                    if current:
                        status_icon.classes(replace="text-green-400 animate-pulse text-sm")
                    else:
                        status_icon.classes(replace="text-slate-400 text-sm")
            except (RuntimeError, KeyError):
                pass

        ui.timer(1.0, update_status)
        update_status()
