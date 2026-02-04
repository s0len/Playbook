"""
Navigation header component for the Playbook GUI.
"""

from __future__ import annotations

from pathlib import Path

from nicegui import ui

from ..state import gui_state
from ..theme import is_dark_mode, set_theme_preference

# Logo path relative to package
LOGO_PATH = Path(__file__).parent.parent.parent.parent.parent / "docs" / "assets" / "logo.png"


def header(dark_mode: ui.dark_mode | None = None) -> None:
    """Render the navigation header with links to all pages.

    Args:
        dark_mode: Optional dark_mode controller for theme toggle
    """
    with ui.header().classes("nav-header text-white shadow-lg"):
        with ui.row().classes("w-full max-w-7xl mx-auto items-center px-4 py-2"):
            # Logo and title
            with ui.link(target="/").classes("no-underline"):
                with ui.row().classes("items-center gap-2"):
                    if LOGO_PATH.exists():
                        ui.image(str(LOGO_PATH)).classes("w-7 h-7")
                    else:
                        ui.icon("sports").classes("text-2xl text-white")
                    ui.label("Playbook").classes("text-xl font-bold text-white")

            ui.space()

            # Navigation links
            with ui.row().classes("gap-1"):
                _nav_link("Dashboard", "/", "dashboard")
                _nav_link("Logs", "/logs", "article")
                _nav_link("Config", "/config", "settings")
                _nav_link("Sports", "/sports", "emoji_events")
                _nav_link("Unmatched", "/unmatched", "help_outline")

            ui.space()

            # Dark mode toggle and status indicator
            with ui.row().classes("items-center gap-3"):
                _dark_mode_toggle(dark_mode)
                _status_indicator()


def _nav_link(label: str, target: str, icon: str) -> None:
    """Create a navigation link with icon."""
    with ui.link(target=target).classes("text-white no-underline"):
        with ui.row().classes("nav-link items-center gap-1"):
            ui.icon(icon).classes("text-lg")
            ui.label(label).classes("text-sm font-medium")


def _dark_mode_toggle(dark_mode: ui.dark_mode | None) -> None:
    """Create a dark mode toggle button."""
    # Track the current state
    is_dark = is_dark_mode()

    # Create the icon that will update
    icon_name = "light_mode" if is_dark else "dark_mode"

    def toggle() -> None:
        nonlocal is_dark
        is_dark = not is_dark

        # Update theme preference (server-side storage)
        set_theme_preference("dark" if is_dark else "light")

        # Toggle NiceGUI dark mode
        if dark_mode is not None:
            dark_mode.toggle()

        # Update icon
        toggle_icon.props(f"icon={'light_mode' if is_dark else 'dark_mode'}")

        # Store in localStorage for instant access on page load (prevents FOUC)
        theme_value = "dark" if is_dark else "light"
        ui.run_javascript(f"localStorage.setItem('playbook-theme', '{theme_value}');")

    toggle_icon = (
        ui.button(icon=icon_name, on_click=toggle).props("flat round dense").classes("dark-mode-toggle text-white")
    )
    toggle_icon.tooltip("Toggle dark mode")


def _status_indicator() -> None:
    """Show processing status indicator."""
    with ui.row().classes("items-center gap-2 ml-2"):
        status_icon = ui.icon("circle").classes("text-sm")
        status_label = ui.label("Idle").classes("text-xs text-slate-300")

        def update_status() -> None:
            try:
                if gui_state.is_processing:
                    status_icon.classes(replace="text-green-400 animate-pulse text-sm")
                    status_label.text = "Processing"
                else:
                    status_icon.classes(replace="text-slate-400 text-sm")
                    status_label.text = "Idle"
            except (RuntimeError, KeyError):
                pass

        ui.timer(1.0, update_status)
        update_status()
