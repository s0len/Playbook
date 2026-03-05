"""Theme settings tab for GUI color themes."""

from __future__ import annotations

from nicegui import ui

from ...components.settings import settings_card, settings_select
from ...styles import apply_color_theme


def themes_tab(state) -> None:
    """Render the Themes settings tab."""
    with ui.column().classes("w-full gap-6"):
        with settings_card("Themes", icon="palette", description="Choose your preferred GUI color theme"):
            settings_select(
                state,
                "settings.theme",
                "Theme",
                options={"swizzin": "Swizzin", "catppuccin": "Catppuccin"},
                description="Theme updates immediately in the current session",
                on_change=lambda value: apply_color_theme(str(value or "swizzin")),
            )

            with ui.card().classes("w-full p-4 settings-inline-card"):
                ui.label("Theme Notes").classes("text-sm font-semibold text-slate-200")
                ui.label("Swizzin uses a slate + green accent palette.").classes("text-xs text-slate-400")
                ui.label("Catppuccin uses a slate + mauve accent palette.").classes("text-xs text-slate-400")
