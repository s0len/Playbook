"""Autoscan integration editor."""

from __future__ import annotations

import asyncio
import copy
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from nicegui import context, ui

from ....app_button import app_button, neutralize_button_utilities
from ....utils import safe_notify
from ..form_renderer import render_fields, render_toggle_row

if TYPE_CHECKING:
    from playbook.gui.settings_state.settings_state import SettingsFormState

INTEGRATION_META = {
    "key": "autoscan",
    "label": "Autoscan",
    "icon": "radar",
    "description": "Use Autoscan for more efficient library scanning",
    "config_path": "settings.integrations.autoscan",
    "env_vars": [],
}

_SECTIONS = [
    {
        "title": "Connection",
        "icon": "link",
        "fields": [
            {
                "key": "url",
                "label": "Autoscan URL",
                "type": "text",
                "placeholder": "http://localhost:3030",
                "row": 1,
            },
            {
                "key": "trigger",
                "label": "Trigger",
                "type": "select",
                "options": ["manual", "inotify"],
                "row": 1,
                "width": "w-40",
            },
            {"key": "username", "label": "Username", "type": "text", "row": 2},
            {"key": "password", "label": "Password", "type": "password", "row": 2},
            {
                "key": "timeout",
                "label": "Timeout (seconds)",
                "type": "number",
                "placeholder": "10",
                "row": 3,
                "width": "w-32",
            },
            {
                "key": "verify_ssl",
                "label": "Verify SSL",
                "type": "toggle",
                "description": "Verify SSL certificates",
                "row": 3,
            },
        ],
    },
    {
        "title": "Path Rewriting",
        "icon": "swap_horiz",
        "description": "Map paths if Autoscan sees files at different paths than Playbook",
        "fields": [
            {"key": "rewrite", "type": "rewrite_rules"},
        ],
    },
]


def is_active(data: dict) -> bool:
    return bool(data.get("enabled"))


def summary(data: dict) -> str:
    url = data.get("url") or ""
    trigger = data.get("trigger") or ""
    parts = []
    if url:
        parts.append(url)
    if trigger:
        parts.append(f"Trigger: {trigger}")
    return " \u2014 ".join(parts) if parts else "Not configured"


def open_dialog(state: SettingsFormState, data: dict, on_save) -> None:
    config_path = INTEGRATION_META["config_path"]
    working: dict[str, Any] = copy.deepcopy(data) if isinstance(data, dict) else {}

    with (
        ui.dialog() as dialog,
        ui.card().classes("glass-card settings-surface w-[780px] max-w-[96vw] max-h-[90vh] p-5"),
    ):
        with ui.row().classes("w-full items-start justify-between mb-3"):
            with ui.column().classes("gap-0"):
                ui.label("Autoscan Integration").classes("text-2xl font-semibold text-slate-100")
                ui.label(INTEGRATION_META["description"]).classes("text-sm text-slate-400")
            neutralize_button_utilities(ui.button(icon="close", on_click=dialog.close).props("flat round dense"))

        with ui.scroll_area().classes("w-full").style("max-height: 60vh"):
            form_container = ui.column().classes("w-full gap-5 pr-2")

            def render_form() -> None:
                form_container.clear()
                with form_container:
                    render_toggle_row(
                        working,
                        "enabled",
                        "Enable Autoscan",
                        INTEGRATION_META["description"],
                        on_change=lambda _: render_form(),
                    )
                    if not working.get("enabled"):
                        return
                    for section in _SECTIONS:
                        _render_section(working, section)

            render_form()

        def save() -> None:
            state.set_value(config_path, copy.deepcopy(working))
            dialog.close()
            on_save()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            app_button("Cancel", on_click=dialog.close, variant="outline", props="outline")
            test_btn = app_button(
                "Test Connection",
                icon="cable",
                on_click=lambda: _test_connection(working, test_btn),
                variant="outline",
                props="outline",
            )
            app_button("Save", icon="save", on_click=save, variant="primary")

    dialog.open()


def _render_section(working: dict[str, Any], section: dict[str, Any]) -> None:
    ui.separator().classes("my-1")
    with ui.row().classes("items-center gap-2"):
        if section.get("icon"):
            ui.icon(section["icon"]).classes("text-slate-400 text-lg")
        ui.label(section["title"]).classes("text-sm font-semibold text-slate-300")
    if section.get("description"):
        ui.label(section["description"]).classes("text-xs text-slate-500 mb-1")
    render_fields(working, section.get("fields", []))


def _test_connection(working: dict[str, Any], btn) -> None:
    url = working.get("url") or ""
    trigger = working.get("trigger") or "manual"

    if not url:
        ui.notify("Autoscan URL is required to test connection", type="warning")
        return

    btn.props("loading")
    client = context.client

    endpoint = f"{url.rstrip('/')}/triggers/{trigger}"
    username = working.get("username")
    password = working.get("password")
    timeout = 5.0
    verify_ssl = working.get("verify_ssl", True)

    def do_test():
        import requests
        from requests.auth import HTTPBasicAuth

        auth = HTTPBasicAuth(str(username or ""), str(password or "")) if username or password else None
        resp = requests.post(endpoint, params={"dir": "/test"}, auth=auth, timeout=timeout, verify=verify_ssl)
        return resp.status_code

    async def async_test():
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            status = await loop.run_in_executor(executor, do_test)
            if status < 400:
                safe_notify(client, f"Connected! Status: {status}", type="positive")
            else:
                safe_notify(client, f"Server responded with status {status}", type="warning")
        except Exception as exc:
            safe_notify(client, f"Connection failed: {exc}", type="negative")
        finally:
            executor.shutdown(wait=False)
            btn.props(remove="loading")

    asyncio.create_task(async_test())
