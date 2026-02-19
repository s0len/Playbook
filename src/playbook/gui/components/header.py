"""
Navigation sidebar component for the Playbook GUI.
"""

from __future__ import annotations

from nicegui import ui

from ..state import gui_state
from ..theme import is_dark_mode, set_theme_preference

NAV_ITEMS = [
    ("/", "dashboard", "Dashboard"),
    ("/logs", "article", "Logs"),
    ("/config", "settings", "Config"),
    ("/sports", "emoji_events", "Sports"),
    ("/unmatched", "help_outline", "Unmatched"),
]


def header(dark_mode: ui.dark_mode | None = None, current_path: str = "/") -> None:
    """Render the icon-only left navigation sidebar.

    Args:
        dark_mode: Optional dark_mode controller for theme toggle
        current_path: The current page path for active state highlighting
    """
    with ui.left_drawer(value=True).props("persistent show-if-above width=60 bordered=false").classes(
        "playbook-sidebar"
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

            # Dark mode toggle and status indicator at the bottom
            _dark_mode_toggle(dark_mode)
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
    link.tooltip(label)


def _dark_mode_toggle(dark_mode: ui.dark_mode | None) -> None:
    """Create a dark mode toggle button."""
    is_dark = is_dark_mode()
    icon_name = "light_mode" if is_dark else "dark_mode"

    def toggle() -> None:
        nonlocal is_dark
        is_dark = not is_dark
        set_theme_preference("dark" if is_dark else "light")
        if dark_mode is not None:
            dark_mode.toggle()
        toggle_icon.props(f"icon={'light_mode' if is_dark else 'dark_mode'}")
        theme_value = "dark" if is_dark else "light"
        ui.run_javascript(f"localStorage.setItem('playbook-theme', '{theme_value}');")

    toggle_icon = (
        ui.button(icon=icon_name, on_click=toggle).props("flat round dense").classes("sidebar-icon-btn")
    )
    toggle_icon.tooltip("Toggle dark mode")


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
