"""Plex integration editor."""

from __future__ import annotations

import asyncio
import copy
import os
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from nicegui import context, ui

from ....utils import safe_notify
from ...app_button import app_button, neutralize_button_utilities
from ..form_renderer import nested_get, render_fields, render_toggle_row

if TYPE_CHECKING:
    from playbook.gui.settings_state.settings_state import SettingsFormState

INTEGRATION_META = {
    "key": "plex",
    "label": "Plex",
    "icon": "live_tv",
    "description": "Connect to your Plex server for library scans and metadata sync",
    "config_path": "settings.integrations.plex",
    "env_vars": ["PLEX_URL", "PLEX_TOKEN", "PLEX_LIBRARY_NAME", "PLEX_LIBRARY_ID"],
}

_SECTIONS = [
    {
        "title": "Connection",
        "icon": "link",
        "fields": [
            {
                "key": "url",
                "label": "Plex URL",
                "type": "text",
                "placeholder": "http://localhost:32400",
                "env": "PLEX_URL",
                "row": 1,
            },
            {
                "key": "token",
                "label": "Plex Token",
                "type": "password",
                "env": "PLEX_TOKEN",
                "row": 1,
            },
            {
                "key": "library_id",
                "label": "Library ID",
                "type": "text",
                "placeholder": "1",
                "env": "PLEX_LIBRARY_ID",
                "width": "w-32",
                "row": 2,
            },
            {
                "key": "library_name",
                "label": "Library Name",
                "type": "text",
                "placeholder": "Sports",
                "env": "PLEX_LIBRARY_NAME",
                "row": 2,
            },
        ],
    },
    {
        "title": "Library Scan on Activity",
        "icon": "refresh",
        "description": "Trigger Plex to scan for new files when they are linked",
        "toggle_key": "scan_on_activity.enabled",
        "fields": [
            {"key": "scan_on_activity.rewrite", "type": "rewrite_rules"},
        ],
    },
    {
        "title": "Metadata Sync",
        "icon": "cloud_sync",
        "description": "Push titles, summaries, and posters from TVSportsDB to Plex",
        "toggle_key": "metadata_sync.enabled",
        "fields": [
            {
                "key": "metadata_sync.timeout",
                "label": "Timeout (seconds)",
                "type": "number",
                "placeholder": "15",
                "row": 1,
                "width": "w-32",
            },
            {
                "key": "metadata_sync.scan_wait",
                "label": "Scan Wait (seconds)",
                "type": "number",
                "placeholder": "5",
                "row": 1,
                "width": "w-32",
            },
            {
                "key": "metadata_sync.force",
                "label": "Force Sync",
                "type": "toggle",
                "description": "Update all metadata, not just changed items",
            },
            {
                "key": "metadata_sync.dry_run",
                "label": "Dry Run",
                "type": "toggle",
                "description": "Preview changes without applying",
            },
            {
                "key": "metadata_sync.lock_poster_fields",
                "label": "Lock Poster Fields",
                "type": "toggle",
                "description": "Prevent Plex from overwriting posters",
            },
            {
                "key": "metadata_sync.sports",
                "label": "Sports Filter",
                "type": "list",
                "description": "Only sync these sports (empty = all)",
                "placeholder": "formula1",
            },
        ],
    },
]


def is_active(data: dict) -> bool:
    return bool(nested_get(data, "scan_on_activity.enabled")) or bool(nested_get(data, "metadata_sync.enabled"))


def summary(data: dict) -> str:
    url = data.get("url") or os.environ.get("PLEX_URL") or ""
    lib = data.get("library_name") or os.environ.get("PLEX_LIBRARY_NAME") or ""
    features: list[str] = []
    if nested_get(data, "scan_on_activity.enabled"):
        features.append("Scan")
    if nested_get(data, "metadata_sync.enabled"):
        features.append("Metadata Sync")
    parts = []
    if url:
        parts.append(url)
    if lib:
        parts.append(f"Library: {lib}")
    if features:
        parts.append(" + ".join(features))
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
                ui.label("Plex Integration").classes("text-2xl font-semibold text-slate-100")
                ui.label(INTEGRATION_META["description"]).classes("text-sm text-slate-400")
            neutralize_button_utilities(ui.button(icon="close", on_click=dialog.close).props("flat round dense"))

        with ui.scroll_area().classes("w-full").style("max-height: 60vh"):
            form_container = ui.column().classes("w-full gap-5 pr-2")

            def render_form() -> None:
                form_container.clear()
                with form_container:
                    for section in _SECTIONS:
                        _render_section(working, section, render_form)

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


def _render_section(working: dict[str, Any], section: dict[str, Any], refresh_fn) -> None:
    ui.separator().classes("my-1")
    with ui.row().classes("items-center gap-2"):
        if section.get("icon"):
            ui.icon(section["icon"]).classes("text-slate-400 text-lg")
        ui.label(section["title"]).classes("text-sm font-semibold text-slate-300")
    if section.get("description"):
        ui.label(section["description"]).classes("text-xs text-slate-500 mb-1")
    toggle_key = section.get("toggle_key")
    if toggle_key:
        render_toggle_row(
            working,
            toggle_key,
            f"Enable {section['title']}",
            section.get("description", ""),
            on_change=lambda _: refresh_fn(),
        )
        if not nested_get(working, toggle_key):
            return
    render_fields(working, section.get("fields", []))


def _test_connection(working: dict[str, Any], btn) -> None:
    url = working.get("url") or os.environ.get("PLEX_URL") or ""
    token = working.get("token") or os.environ.get("PLEX_TOKEN") or ""

    if not url or not token:
        ui.notify("URL and token are required to test connection", type="warning")
        return

    btn.props("loading")
    client = context.client

    def do_test():
        from playbook.plex_client import PlexClient

        plex = PlexClient(url, token, timeout=5.0)
        libs = plex.list_libraries()
        return len(libs)

    async def async_test():
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            count = await loop.run_in_executor(executor, do_test)
            safe_notify(client, f"Connected! Found {count} libraries", type="positive")
        except Exception as exc:
            safe_notify(client, f"Connection failed: {exc}", type="negative")
        finally:
            executor.shutdown(wait=False)
            btn.props(remove="loading")

    asyncio.create_task(async_test())
