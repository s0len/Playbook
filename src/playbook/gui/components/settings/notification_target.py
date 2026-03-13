"""Notification target editor component with card list + modal editing."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from nicegui import ui

from ..app_button import app_button, neutralize_button_utilities

if TYPE_CHECKING:
    from playbook.gui.settings_state.settings_state import SettingsFormState


NOTIFICATION_TYPES = {
    "discord": {
        "label": "Discord",
        "icon": "chat",
        "fields": [
            {
                "key": "webhook_url",
                "label": "Webhook URL",
                "type": "text",
                "placeholder": "https://discord.com/api/webhooks/...",
            },
            {"key": "webhook_env", "label": "Webhook Env Var", "type": "text", "placeholder": "DISCORD_WEBHOOK_URL"},
            {"key": "mentions", "label": "Mentions", "type": "text", "placeholder": "@user or @role"},
        ],
    },
    "webhook": {
        "label": "Webhook",
        "icon": "webhook",
        "fields": [
            {"key": "url", "label": "URL", "type": "text", "required": True},
            {"key": "method", "label": "Method", "type": "select", "options": ["POST", "PUT", "PATCH"]},
        ],
    },
    "email": {
        "label": "Email",
        "icon": "email",
        "fields": [
            {"key": "smtp_host", "label": "SMTP Host", "type": "text", "required": True},
            {"key": "smtp_port", "label": "SMTP Port", "type": "number"},
            {"key": "from_addr", "label": "From Address", "type": "text", "required": True},
            {"key": "to_addr", "label": "To Address", "type": "text", "required": True},
            {"key": "username", "label": "Username", "type": "text"},
            {"key": "password", "label": "Password", "type": "password"},
        ],
    },
}


def _preferred_discord_env_key() -> str | None:
    for key in ("DISCORD_WEBHOOK_URL",):
        raw = os.environ.get(key)
        if raw and raw.strip():
            return key
    return None


def _default_target_for_type(target_type: str) -> dict[str, Any]:
    normalized = target_type.strip().lower()
    target: dict[str, Any] = {
        "type": normalized,
        "enabled": True,
    }
    if normalized == "discord":
        target["webhook_env"] = _preferred_discord_env_key() or "DISCORD_WEBHOOK_URL"
    return target


def _masked_value(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        return ""
    try:
        parsed = urlparse(value)
        if not parsed.scheme:
            return "configured"
        host = parsed.netloc or "configured"
        return f"{parsed.scheme}://{host}/..."
    except Exception:  # noqa: BLE001
        return "configured"


def _target_summary(target: dict[str, Any]) -> str:
    target_type = (target.get("type") or "").lower()
    if target_type == "discord":
        webhook_env = str(target.get("webhook_env") or "").strip()
        webhook_url = str(target.get("webhook_url") or "").strip()
        mentions = str(target.get("mentions") or "").strip()
        source = webhook_env if webhook_env else _masked_value(webhook_url)
        summary = f"Source: {source or 'not configured'}"
        if mentions:
            summary += f" - Mentions: {mentions}"
        return summary

    for key in ("url", "smtp_host", "to_addr", "library_name", "library_id"):
        value = str(target.get(key) or "").strip()
        if value:
            return f"{key.replace('_', ' ').title()}: {_masked_value(value) if key == 'url' else value}"
    return "Not configured"


def notification_target_editor(
    state: SettingsFormState,
    path: str,
    *,
    disabled: bool = False,
    on_change: Callable[[list[dict]], None] | None = None,
) -> ui.column:
    """Create a notification target list editor."""
    container = ui.column().classes("w-full gap-4")

    def _get_targets() -> list[dict[str, Any]]:
        raw = state.get_value(path, []) or []
        return raw if isinstance(raw, list) else []

    def _set_targets(targets: list[dict[str, Any]]) -> None:
        state.set_value(path, targets)
        if on_change:
            on_change(targets)

    def refresh_editor() -> None:
        container.clear()
        with container:
            _render_editor()

    def _open_target_dialog(index: int | None = None) -> None:
        targets = _get_targets()
        is_new = index is None
        working = dict(targets[index]) if index is not None else _default_target_for_type("discord")

        with ui.dialog() as dialog, ui.card().classes("glass-card settings-surface w-[780px] max-w-[96vw] p-5"):
            with ui.row().classes("w-full items-start justify-between mb-3"):
                with ui.column().classes("gap-0"):
                    ui.label("New Notification Target" if is_new else "Edit Notification Target").classes(
                        "text-2xl font-semibold text-slate-100"
                    )
                    ui.label("Update delivery settings for this target").classes("text-sm text-slate-400")
                neutralize_button_utilities(ui.button(icon="close", on_click=dialog.close).props("flat round dense"))

            form_container = ui.column().classes("w-full gap-3")

            def render_form() -> None:
                form_container.clear()
                with form_container:
                    current_type = str(working.get("type", "discord"))
                    type_options = {key: value["label"] for key, value in NOTIFICATION_TYPES.items()}

                    def on_type_change(e) -> None:
                        new_type = str(e.value or "discord")
                        defaults = _default_target_for_type(new_type)
                        defaults["enabled"] = working.get("enabled", True)
                        working.clear()
                        working.update(defaults)
                        render_form()

                    ui.select(type_options, value=current_type, on_change=on_type_change).classes(
                        "w-64 settings-input"
                    ).props("outlined dense label='Type'")

                    enabled = bool(working.get("enabled", True))

                    def on_enabled_change(e) -> None:
                        working["enabled"] = bool(e.value)

                    with ui.row().classes("w-full items-center justify-between rounded-lg border border-white/10 p-3"):
                        with ui.column().classes("gap-0"):
                            ui.label("Enabled").classes("text-sm font-medium text-slate-200")
                            ui.label("Toggle delivery for this target").classes("text-xs text-slate-400")
                        ui.switch(value=enabled, on_change=on_enabled_change).classes("settings-toggle")

                    for field_def in NOTIFICATION_TYPES.get(current_type, NOTIFICATION_TYPES["webhook"])["fields"]:
                        key = field_def["key"]
                        label = field_def["label"]
                        field_type = field_def.get("type", "text")
                        placeholder = field_def.get("placeholder", "")
                        current_value = working.get(key, "")

                        if field_type == "select":
                            options = field_def.get("options", [])

                            def on_select_change(e, k=key) -> None:
                                working[k] = e.value

                            ui.select(
                                options,
                                value=current_value or (options[0] if options else ""),
                                on_change=on_select_change,
                            ).classes("w-full settings-input").props(f"outlined dense label='{label}'")
                            continue

                        input_props = "outlined dense"
                        if field_type == "password":
                            input_props += ' type="password"'
                        elif field_type == "number":
                            input_props += ' type="number"'

                        def on_input_change(e, k=key) -> None:
                            working[k] = e.value

                        ui.input(
                            value=str(current_value) if current_value else "",
                            label=label,
                            placeholder=placeholder,
                            on_change=on_input_change,
                        ).classes("w-full settings-input").props(input_props)

            render_form()

            def save_target() -> None:
                current_type = str(working.get("type", "discord"))
                fields = NOTIFICATION_TYPES.get(current_type, NOTIFICATION_TYPES["webhook"])["fields"]
                for field in fields:
                    if field.get("required") and not str(working.get(field["key"], "")).strip():
                        ui.notify(f"{field['label']} is required", type="warning")
                        return

                updated = _get_targets()
                if index is None:
                    updated.append(dict(working))
                else:
                    updated[index] = dict(working)
                _set_targets(updated)
                dialog.close()
                refresh_editor()

            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                app_button("Cancel", on_click=dialog.close, variant="outline", props="outline")
                app_button("Save", icon="save", on_click=save_target, variant="primary")

        dialog.open()

    def _render_editor() -> None:
        targets = _get_targets()
        discord_env_key = _preferred_discord_env_key()

        with ui.row().classes("w-full items-center justify-between"):
            with ui.row().classes("items-center gap-2"):
                ui.label("Notification Targets").classes("text-sm font-semibold text-slate-200")
                ui.badge(str(len(targets))).classes("text-xs app-badge app-badge-muted")

            if not disabled:
                neutralize_button_utilities(
                    ui.button(icon="add", on_click=lambda: _open_target_dialog()).props("flat dense")
                )

        if discord_env_key:
            with ui.row().classes("items-center gap-2"):
                ui.icon("check_circle").classes("app-text-success text-sm")
                ui.label(f"Detected Discord webhook env: {discord_env_key}").classes("text-xs text-slate-400")

        if not targets:
            with ui.card().classes("w-full p-4 settings-inline-card"):
                ui.label("No notification targets configured").classes("text-sm text-slate-400 italic")
                if not disabled:
                    neutralize_button_utilities(
                        ui.button(
                            text="Add Notification Target", icon="add", on_click=lambda: _open_target_dialog()
                        ).props("flat dense")
                    )
            return

        for idx, target in enumerate(targets):
            target_type = str(target.get("type", "webhook")).lower()
            if target_type not in NOTIFICATION_TYPES:
                continue  # silently skip removed/unknown types (e.g. plex_scan, autoscan)
            type_config = NOTIFICATION_TYPES[target_type]
            enabled = bool(target.get("enabled", True))

            with ui.card().classes("w-full p-4 settings-inline-card"):
                with ui.row().classes("w-full items-start justify-between gap-3"):
                    with ui.column().classes("gap-1 flex-1 min-w-0"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon(type_config["icon"]).classes("text-slate-300")
                            ui.label(type_config["label"]).classes("text-lg font-medium text-slate-100")
                            badge_class = "app-badge app-badge-muted"
                            if enabled:
                                badge_class = "app-badge app-chip-active"
                            ui.badge("Enabled" if enabled else "Disabled").classes(f"text-xs {badge_class}")
                        ui.label(_target_summary(target)).classes("text-xs text-slate-400 break-all")

                    if not disabled:
                        with ui.row().classes("gap-1"):
                            neutralize_button_utilities(
                                ui.button(icon="edit", on_click=lambda i=idx: _open_target_dialog(i)).props(
                                    "flat dense"
                                )
                            )

                            def _toggle(i=idx) -> None:
                                updated = _get_targets()
                                updated[i]["enabled"] = not bool(updated[i].get("enabled", True))
                                _set_targets(updated)
                                refresh_editor()

                            neutralize_button_utilities(
                                ui.button(icon="visibility" if enabled else "visibility_off", on_click=_toggle).props(
                                    "flat dense"
                                )
                            )

                            def _delete(i=idx) -> None:
                                updated = _get_targets()
                                updated.pop(i)
                                _set_targets(updated)
                                refresh_editor()

                            neutralize_button_utilities(
                                ui.button(icon="delete", on_click=_delete).props("flat dense")
                            ).classes("app-text-danger")

    with container:
        _render_editor()

    return container
