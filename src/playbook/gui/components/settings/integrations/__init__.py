"""Integration editor registry and card list component."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from nicegui import ui

from ...app_button import neutralize_button_utilities
from . import autoscan_editor, kometa_editor, plex_editor, tvsportsdb_editor

if TYPE_CHECKING:
    from playbook.gui.settings_state.settings_state import SettingsFormState

# Ordered list of all integration editor modules
INTEGRATIONS = [
    tvsportsdb_editor,
    plex_editor,
    autoscan_editor,
    kometa_editor,
]


def integration_editor(state: SettingsFormState) -> ui.column:
    """Render the integration card list."""
    container = ui.column().classes("w-full gap-4")

    def refresh() -> None:
        container.clear()
        with container:
            _render_cards(state, refresh)

    with container:
        _render_cards(state, refresh)

    return container


def _render_cards(state: SettingsFormState, refresh_fn) -> None:
    """Render one card per integration."""
    for mod in INTEGRATIONS:
        meta = mod.INTEGRATION_META
        config_path = meta["config_path"]
        data = state.get_value(config_path) or {}
        if not isinstance(data, dict):
            data = {}
        active = mod.is_active(data)

        env_vars = meta.get("env_vars", [])
        detected_envs = [v for v in env_vars if os.environ.get(v)]

        with ui.card().classes("w-full p-4 settings-inline-card"):
            with ui.row().classes("w-full items-start justify-between gap-3"):
                with ui.column().classes("gap-1 flex-1 min-w-0"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon(meta["icon"]).classes("text-slate-300")
                        ui.label(meta["label"]).classes("text-lg font-medium text-slate-100")
                        badge_class = "app-badge app-chip-active" if active else "app-badge app-badge-muted"
                        ui.badge("Active" if active else "Inactive").classes(f"text-xs {badge_class}")
                    ui.label(mod.summary(data)).classes("text-xs text-slate-400 break-all")
                    if detected_envs:
                        with ui.row().classes("items-center gap-1 mt-1"):
                            ui.icon("check_circle").classes("app-text-success text-xs")
                            ui.label(f"Env: {', '.join(detected_envs)}").classes("text-xs text-slate-500")

                with ui.row().classes("gap-1"):
                    neutralize_button_utilities(
                        ui.button(
                            icon="edit",
                            on_click=lambda m=mod: m.open_dialog(
                                state, state.get_value(m.INTEGRATION_META["config_path"]) or {}, refresh_fn
                            ),
                        ).props("flat dense")
                    )
