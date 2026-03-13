"""TVSportsDB integration editor."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from nicegui import ui

from ...app_button import app_button, neutralize_button_utilities
from ..form_renderer import render_fields

if TYPE_CHECKING:
    from playbook.gui.settings_state.settings_state import SettingsFormState

INTEGRATION_META = {
    "key": "tvsportsdb",
    "label": "TVSportsDB",
    "icon": "sports",
    "description": "Metadata source for sports shows, seasons, and episodes",
    "config_path": "settings.tvsportsdb",
    "env_vars": [],
}

_SECTIONS = [
    {
        "title": "Connection",
        "icon": "link",
        "fields": [
            {
                "key": "base_url",
                "label": "Base URL",
                "type": "text",
                "placeholder": "http://localhost:8000",
                "row": 1,
            },
            {
                "key": "ttl_hours",
                "label": "Cache TTL (hours)",
                "type": "number",
                "placeholder": "2",
                "row": 2,
                "width": "w-32",
            },
            {
                "key": "timeout",
                "label": "Timeout (seconds)",
                "type": "number",
                "placeholder": "30",
                "row": 2,
                "width": "w-32",
            },
        ],
    },
]


def is_active(data: dict) -> bool:
    return bool(data.get("base_url"))


def summary(data: dict) -> str:
    url = data.get("base_url") or ""
    return url if url else "Not configured"


def open_dialog(state: SettingsFormState, data: dict, on_save) -> None:
    config_path = INTEGRATION_META["config_path"]
    working: dict[str, Any] = copy.deepcopy(data) if isinstance(data, dict) else {}

    with (
        ui.dialog() as dialog,
        ui.card().classes("glass-card settings-surface w-[780px] max-w-[96vw] max-h-[90vh] p-5"),
    ):
        with ui.row().classes("w-full items-start justify-between mb-3"):
            with ui.column().classes("gap-0"):
                ui.label("TVSportsDB Integration").classes("text-2xl font-semibold text-slate-100")
                ui.label(INTEGRATION_META["description"]).classes("text-sm text-slate-400")
            neutralize_button_utilities(ui.button(icon="close", on_click=dialog.close).props("flat round dense"))

        with ui.scroll_area().classes("w-full").style("max-height: 60vh"):
            with ui.column().classes("w-full gap-5 pr-2"):
                for section in _SECTIONS:
                    _render_section(working, section)

        def save() -> None:
            state.set_value(config_path, copy.deepcopy(working))
            dialog.close()
            on_save()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            app_button("Cancel", on_click=dialog.close, variant="outline", props="outline")
            app_button("Save", icon="save", on_click=save, variant="primary")

    dialog.open()


def _render_section(working: dict[str, Any], section: dict[str, Any]) -> None:
    ui.separator().classes("my-1")
    with ui.row().classes("items-center gap-2"):
        if section.get("icon"):
            ui.icon(section["icon"]).classes("text-slate-400 text-lg")
        ui.label(section["title"]).classes("text-sm font-semibold text-slate-300")
    render_fields(working, section.get("fields", []))
