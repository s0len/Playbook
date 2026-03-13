"""Kometa integration editor."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from nicegui import ui

from ....app_button import app_button, neutralize_button_utilities
from ..form_renderer import (
    nested_set,
    render_fields,
    render_key_value_field,
    render_list_field,
    render_toggle_row,
)

if TYPE_CHECKING:
    from playbook.gui.settings_state.settings_state import SettingsFormState

INTEGRATION_META = {
    "key": "kometa",
    "label": "Kometa",
    "icon": "movie_filter",
    "description": "Trigger Kometa runs for Plex metadata management",
    "config_path": "settings.kometa_trigger",
    "env_vars": [],
}

_K8S_FIELDS = [
    {
        "key": "namespace",
        "label": "Namespace",
        "type": "text",
        "placeholder": "media",
        "row": 1,
    },
    {
        "key": "cronjob_name",
        "label": "CronJob Name",
        "type": "text",
        "placeholder": "kometa-sport",
        "row": 1,
    },
    {
        "key": "job_name_prefix",
        "label": "Job Name Prefix",
        "type": "text",
        "placeholder": "kometa-sport-triggered-by-playbook",
    },
]

_DOCKER_FIELDS = [
    {
        "key": "docker_binary",
        "label": "Docker Binary",
        "type": "text",
        "placeholder": "docker",
        "row": 1,
    },
    {
        "key": "docker_image",
        "label": "Docker Image",
        "type": "text",
        "placeholder": "kometateam/kometa",
        "row": 1,
    },
    {
        "key": "docker_config_path",
        "label": "Config Path (host)",
        "type": "text",
        "row": 2,
    },
    {
        "key": "docker_config_container_path",
        "label": "Config Path (container)",
        "type": "text",
        "placeholder": "/config",
        "row": 2,
    },
    {
        "key": "docker_volume_mode",
        "label": "Volume Mode",
        "type": "select",
        "options": ["rw", "ro"],
        "row": 3,
        "width": "w-24",
    },
    {
        "key": "docker_libraries",
        "label": "Libraries",
        "type": "text",
        "row": 3,
    },
    {
        "key": "docker_container_name",
        "label": "Container Name",
        "type": "text",
        "row": 4,
    },
    {
        "key": "docker_remove_container",
        "label": "Remove Container After Run",
        "type": "toggle",
        "description": "Automatically remove the container when it exits",
    },
    {
        "key": "docker_interactive",
        "label": "Interactive Mode",
        "type": "toggle",
        "description": "Run container in interactive mode",
    },
    {
        "key": "docker_exec_python",
        "label": "Python Executable",
        "type": "text",
        "placeholder": "python3",
        "row": 5,
    },
    {
        "key": "docker_exec_script",
        "label": "Exec Script",
        "type": "text",
        "placeholder": "/app/kometa/kometa.py",
        "row": 5,
    },
]

_DOCKER_LIST_FIELDS = [
    {
        "key": "docker_exec_command",
        "label": "Exec Command",
        "type": "list",
        "description": "Custom command to execute",
        "placeholder": "arg",
    },
    {
        "key": "docker_extra_args",
        "label": "Extra Arguments",
        "type": "list",
        "description": "Additional Docker arguments",
        "placeholder": "--arg",
    },
]


def is_active(data: dict) -> bool:
    return bool(data.get("enabled"))


def summary(data: dict) -> str:
    if not data.get("enabled"):
        return "Disabled"
    mode = data.get("mode", "kubernetes")
    if mode == "kubernetes":
        ns = data.get("namespace", "media")
        cj = data.get("cronjob_name", "kometa-sport")
        return f"Kubernetes \u2014 {ns}/{cj}"
    image = data.get("docker_image", "kometateam/kometa")
    return f"Docker \u2014 {image}"


def open_dialog(state: SettingsFormState, data: dict, on_save) -> None:
    config_path = INTEGRATION_META["config_path"]
    working: dict[str, Any] = copy.deepcopy(data) if isinstance(data, dict) else {}

    with (
        ui.dialog() as dialog,
        ui.card().classes("glass-card settings-surface w-[780px] max-w-[96vw] max-h-[90vh] p-5"),
    ):
        with ui.row().classes("w-full items-start justify-between mb-3"):
            with ui.column().classes("gap-0"):
                ui.label("Kometa Integration").classes("text-2xl font-semibold text-slate-100")
                ui.label(INTEGRATION_META["description"]).classes("text-sm text-slate-400")
            neutralize_button_utilities(ui.button(icon="close", on_click=dialog.close).props("flat round dense"))

        with ui.scroll_area().classes("w-full").style("max-height: 60vh"):
            form_container = ui.column().classes("w-full gap-5 pr-2")

            def render_form() -> None:
                form_container.clear()
                with form_container:
                    # Enable toggle
                    render_toggle_row(
                        working,
                        "enabled",
                        "Enable Kometa",
                        INTEGRATION_META["description"],
                        on_change=lambda _: render_form(),
                    )
                    if not working.get("enabled"):
                        return

                    # Mode selector
                    ui.separator().classes("my-1")
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("settings").classes("text-slate-400 text-lg")
                        ui.label("General").classes("text-sm font-semibold text-slate-300")

                    current_mode = working.get("mode", "kubernetes")

                    def on_mode_change(e):
                        nested_set(working, "mode", e.value)
                        render_form()

                    ui.select(
                        ["kubernetes", "docker"],
                        value=current_mode,
                        on_change=on_mode_change,
                    ).classes("w-48 settings-input").props("outlined dense label='Mode'")

                    # Mode-specific sections
                    if current_mode == "kubernetes":
                        ui.separator().classes("my-1")
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("cloud").classes("text-slate-400 text-lg")
                            ui.label("Kubernetes").classes("text-sm font-semibold text-slate-300")
                        render_fields(working, _K8S_FIELDS)
                    else:
                        ui.separator().classes("my-1")
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("inventory_2").classes("text-slate-400 text-lg")
                            ui.label("Docker").classes("text-sm font-semibold text-slate-300")
                        render_fields(working, _DOCKER_FIELDS)

                        for list_field in _DOCKER_LIST_FIELDS:
                            render_list_field(working, list_field)

                        ui.separator().classes("my-1")
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("data_object").classes("text-slate-400 text-lg")
                            ui.label("Environment Variables").classes("text-sm font-semibold text-slate-300")
                        render_key_value_field(working, "docker_env", "Variable", "Value")

            render_form()

        def save() -> None:
            state.set_value(config_path, copy.deepcopy(working))
            dialog.close()
            on_save()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            app_button("Cancel", on_click=dialog.close, variant="outline", props="outline")
            app_button("Save", icon="save", on_click=save, variant="primary")

    dialog.open()
