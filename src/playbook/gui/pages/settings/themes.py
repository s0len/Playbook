"""Theme settings tab for GUI color themes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ...components.settings import settings_card, settings_select
from ...styles import apply_color_theme

if TYPE_CHECKING:
    from ...settings_state.settings_state import SettingsFormState


def themes_tab(state: SettingsFormState) -> None:
    """Render the Themes settings tab."""
    current_theme = str(state.get_value("settings.theme", "swizzin") or "swizzin")

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

            with ui.row().classes("w-full gap-4 flex-wrap"):
                _theme_option_card(
                    state,
                    key="swizzin",
                    title="Swizzin",
                    description="Crisp slate surfaces with a green action accent.",
                    swatches=["#34d399", "#2a2a2d", "#e7e7ea"],
                    selected=current_theme == "swizzin",
                )
                _theme_option_card(
                    state,
                    key="catppuccin",
                    title="Catppuccin",
                    description="Slate base with a softer mauve accent treatment.",
                    swatches=["#cba6f7", "#2a2a2d", "#e7e7ea"],
                    selected=current_theme == "catppuccin",
                )

        with settings_card("Theme Notes", icon="info", description="Design intent and behavior"):
            with ui.column().classes("w-full gap-1"):
                ui.label("Swizzin mirrors Qui's clean contrast and restrained highlights.").classes(
                    "text-sm text-slate-300"
                )
                ui.label("Catppuccin keeps layout identical but swaps accents to mauve.").classes(
                    "text-sm text-slate-300"
                )


def _theme_option_card(
    state: SettingsFormState,
    *,
    key: str,
    title: str,
    description: str,
    swatches: list[str],
    selected: bool,
) -> None:
    card_classes = "settings-theme-card"
    if selected:
        card_classes += " settings-theme-card-active"

    with ui.card().classes(f"flex-1 min-w-[280px] p-4 {card_classes}"):
        with ui.row().classes("w-full items-start justify-between"):
            with ui.column().classes("gap-1"):
                ui.label(title).classes("text-xl font-semibold text-slate-100")
                ui.label(description).classes("text-sm text-slate-400")
            if selected:
                ui.badge("Active").classes("app-badge app-badge-success")

        with ui.row().classes("items-center gap-2 mt-3"):
            for swatch in swatches:
                ui.element("div").classes("w-4 h-4 rounded-full border border-white/20").style(f"background:{swatch}")

        action_label = "Selected" if selected else f"Use {title}"
        action_class = "app-btn app-btn-outline" if selected else "app-btn app-btn-primary"
        ui.button(action_label, on_click=lambda t=key: _set_theme(state, t)).props("no-caps").classes(
            f"mt-4 {action_class}"
        )


def _set_theme(state, theme: str) -> None:
    state.set_value("settings.theme", theme)
    apply_color_theme(theme)
