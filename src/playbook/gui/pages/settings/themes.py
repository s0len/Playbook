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
                options=["swizzin", "catppuccin"],
                description="Theme updates immediately in the current session",
                on_change=lambda value: apply_color_theme(str(value or "swizzin")),
            )

            with ui.card().classes("w-full p-4 settings-inline-card"):
                ui.label("Theme Notes").classes("text-sm font-semibold text-slate-200")
                ui.label("Swizzin uses a slate + green accent palette.").classes("text-xs text-slate-400")
                ui.label("Catppuccin uses a slate + mauve accent palette.").classes("text-xs text-slate-400")

        with settings_card("Theme Preview", icon="visibility", description="Quickly compare available accents"):
            with ui.row().classes("w-full gap-3 flex-wrap"):
                with ui.card().classes("settings-inline-card p-3 min-w-[220px]"):
                    ui.label("Swizzin").classes("text-sm font-semibold text-slate-100")
                    with ui.row().classes("items-center gap-2 mt-2"):
                        ui.element("div").classes("w-5 h-5 rounded-full border border-white/20").style(
                            "background:#34d399"
                        )
                        ui.label("Green accent").classes("text-xs text-slate-400")
                    ui.button("Use Swizzin", on_click=lambda: _set_theme(state, "swizzin")).props("flat dense")

                with ui.card().classes("settings-inline-card p-3 min-w-[220px]"):
                    ui.label("Catppuccin").classes("text-sm font-semibold text-slate-100")
                    with ui.row().classes("items-center gap-2 mt-2"):
                        ui.element("div").classes("w-5 h-5 rounded-full border border-white/20").style(
                            "background:#cba6f7"
                        )
                        ui.label("Mauve accent").classes("text-xs text-slate-400")
                    ui.button("Use Catppuccin", on_click=lambda: _set_theme(state, "catppuccin")).props("flat dense")


def _set_theme(state, theme: str) -> None:
    state.set_value("settings.theme", theme)
    apply_color_theme(theme)
