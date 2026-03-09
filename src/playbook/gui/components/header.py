"""
Navigation sidebar component for the Playbook GUI.
"""

from __future__ import annotations

from nicegui import ui

from ..state import gui_state

NAV_ITEMS = [
    ("/", "dashboard", "Dashboard"),
    ("/sports", "emoji_events", "Sports"),
    ("/unmatched", "help_outline", "Unmatched"),
    ("/config", "settings", "Settings"),
    ("/logs", "article", "Logs"),
]


def header(current_path: str = "/") -> None:
    """Render the left navigation sidebar with icon + text labels.

    Args:
        current_path: The current page path for active state highlighting
    """
    drawer = (
        ui.left_drawer(value=False)
        .props("show-if-above width=200 bordered=false breakpoint=1024")
        .classes("playbook-sidebar")
    )
    with drawer:
        with ui.column().classes("w-full h-full p-4 gap-0"):
            # Logo section
            with ui.link(target="/").classes("no-underline flex items-center gap-3 mb-6"):
                ui.image("/icon.png").classes("w-8 h-8 rounded-xl object-cover")
                ui.label("Playbook").classes("text-base font-semibold text-white/90")

            # Navigation items
            with ui.column().classes("w-full gap-1"):
                for path, icon_name, label in NAV_ITEMS:
                    _sidebar_item(path, icon_name, label, _is_active(path, current_path), drawer)

            ui.space()

            # Status indicator at very bottom
            _status_indicator()

    # Mobile hamburger button (fixed position, visible only on small screens via CSS)
    ui.button(icon="menu", on_click=drawer.toggle).props("flat round dense").classes("mobile-hamburger")


def _is_active(nav_path: str, current_path: str) -> bool:
    """Check if a nav item should be marked active."""
    if nav_path == "/":
        return current_path == "/"
    return current_path == nav_path or current_path.startswith(nav_path + "/")


def _sidebar_item(target: str, icon_name: str, label: str, is_active: bool, drawer=None) -> None:
    """Render a single sidebar nav item with icon + text."""
    cls = "sidebar-nav-item" + (" sidebar-nav-item-active" if is_active else "")

    def on_click():
        # Close drawer on mobile after navigation
        if drawer is not None:
            drawer.run_method("hide")

    with ui.link(target=target).classes("no-underline w-full").on("click", on_click):
        with ui.element("div").classes(cls):
            ui.icon(icon_name).classes("text-[20px]")
            ui.label(label).classes("text-sm")


def _status_indicator() -> None:
    """Show processing status indicator with text label."""
    with ui.row().classes("items-center gap-2 mt-3 px-3 py-2"):
        status_icon = ui.icon("circle").classes("text-[10px] text-slate-400")
        status_label = ui.label("Idle").classes("text-xs text-white/40")

        last_status = [None]

        def update_status() -> None:
            try:
                current = gui_state.is_processing
                if current != last_status[0]:
                    last_status[0] = current
                    if current:
                        status_icon.classes(replace="text-[10px] app-text-success animate-pulse")
                        status_label.text = "Processing"
                        status_label.classes(replace="text-xs app-text-success")
                    else:
                        status_icon.classes(replace="text-[10px] text-slate-400")
                        status_label.text = "Idle"
                        status_label.classes(replace="text-xs text-white/40")
            except (RuntimeError, KeyError):
                pass

        ui.timer(1.0, update_status)
        update_status()
