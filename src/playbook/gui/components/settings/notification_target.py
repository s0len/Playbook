"""
Notification target editor component.

Provides a polymorphic form for different notification target types.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nicegui import ui

if TYPE_CHECKING:
    from playbook.gui.settings_state.settings_state import SettingsFormState


# Notification target types and their fields
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
    "autoscan": {
        "label": "Autoscan",
        "icon": "radar",
        "fields": [
            {"key": "url", "label": "Autoscan URL", "type": "text", "required": True},
            {"key": "trigger", "label": "Trigger", "type": "select", "options": ["manual", "inotify"]},
            {"key": "username", "label": "Username", "type": "text"},
            {"key": "password", "label": "Password", "type": "password"},
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
    "plex_scan": {
        "label": "Plex Scan",
        "icon": "play_circle",
        "fields": [
            {"key": "url", "label": "Plex URL", "type": "text", "placeholder": "Uses PLEX_URL env if empty"},
            {"key": "token", "label": "Plex Token", "type": "password", "placeholder": "Uses PLEX_TOKEN env if empty"},
            {"key": "library_name", "label": "Library Name", "type": "text", "placeholder": "Uses PLEX_LIBRARY_NAME env if empty"},
            {"key": "library_id", "label": "Library ID", "type": "text", "placeholder": "Uses PLEX_LIBRARY_ID env if empty"},
        ],
    },
}


def notification_target_editor(
    state: SettingsFormState,
    path: str,
    *,
    disabled: bool = False,
    on_change: Callable[[list[dict]], None] | None = None,
) -> ui.column:
    """Create a notification target list editor.

    Manages a list of notification targets where each target can be
    a different type (discord, webhook, autoscan, email).

    Args:
        state: SettingsFormState instance
        path: Dotted path to the targets list
        disabled: Whether the editor is disabled
        on_change: Optional callback when targets change

    Returns:
        The NiceGUI column container
    """
    container = ui.column().classes("w-full gap-4")

    def refresh_editor() -> None:
        """Rebuild the editor UI."""
        container.clear()
        with container:
            _render_editor()

    def _render_editor() -> None:
        """Render the editor content."""
        targets = state.get_value(path, []) or []
        if not isinstance(targets, list):
            targets = []

        # Header with add button
        with ui.row().classes("w-full items-center justify-between"):
            with ui.row().classes("items-center gap-2"):
                ui.label("Notification Targets").classes("text-sm font-semibold text-slate-700 dark:text-slate-200")
                ui.badge(str(len(targets))).props("color=grey-7").classes("text-xs")

            if not disabled:
                with ui.button(icon="add", on_click=lambda: add_target()).props("flat dense"):
                    ui.tooltip("Add notification target")

        # Render each target
        if targets:
            for idx, target in enumerate(targets):
                _render_target(idx, target)
        else:
            with ui.card().classes("w-full p-4 bg-slate-50 dark:bg-slate-800"):
                ui.label("No notification targets configured").classes(
                    "text-sm text-slate-500 dark:text-slate-400 italic"
                )
                ui.label("Click '+' to add a notification target").classes("text-xs text-slate-400 dark:text-slate-500")

    def _render_target(idx: int, target: dict) -> None:
        """Render a single notification target."""
        target_type = target.get("type", "webhook")
        type_config = NOTIFICATION_TYPES.get(target_type, NOTIFICATION_TYPES["webhook"])

        with ui.card().classes("w-full p-4"):
            # Header row with type and actions
            with ui.row().classes("w-full items-center justify-between mb-3"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon(type_config["icon"]).classes("text-slate-500")
                    ui.label(type_config["label"]).classes("font-medium text-slate-700 dark:text-slate-200")
                    if target.get("enabled", True) is False:
                        ui.badge("Disabled").props("color=grey").classes("text-xs")

                if not disabled:
                    with ui.row().classes("gap-1"):
                        # Toggle enabled
                        enabled = target.get("enabled", True)
                        ui.button(
                            icon="visibility" if enabled else "visibility_off",
                            on_click=lambda i=idx: toggle_target(i),
                        ).props("flat dense").classes("text-slate-500")
                        # Delete
                        ui.button(
                            icon="delete",
                            on_click=lambda i=idx: remove_target(i),
                        ).props("flat dense color=negative")

            # Target type selector
            if not disabled:

                def on_type_change(e, i=idx) -> None:
                    update_target_type(i, e.value)

                ui.select(
                    options={k: v["label"] for k, v in NOTIFICATION_TYPES.items()},
                    value=target_type,
                    on_change=on_type_change,
                ).classes("w-48 mb-3").props("outlined dense label='Type'")

            # Type-specific fields - render each field directly
            for field_def in type_config["fields"]:
                _render_field(idx, target, field_def)

    def _render_field(idx: int, target: dict, field_def: dict) -> None:
        """Render a single field for a notification target."""
        field_key = field_def["key"]
        field_type = field_def.get("type", "text")
        field_label = field_def["label"]
        current_value = target.get(field_key, "")

        if field_type == "select":
            options = field_def.get("options", [])

            def on_select_change(e, i=idx, k=field_key) -> None:
                update_target_field(i, k, e.value)

            ui.select(
                options=options,
                value=current_value or (options[0] if options else ""),
                on_change=on_select_change,
                label=field_label,
            ).classes("w-full mb-2").props("outlined dense")
        else:
            input_props = "outlined dense"
            if field_type == "password":
                input_props += ' type="password"'
            elif field_type == "number":
                input_props += ' type="number"'

            def on_input_change(e, i=idx, k=field_key) -> None:
                update_target_field(i, k, e.value)

            inp = (
                ui.input(
                    value=str(current_value) if current_value else "",
                    label=field_label,
                    placeholder=field_def.get("placeholder", ""),
                    on_change=on_input_change,
                )
                .classes("w-full mb-2")
                .props(input_props)
            )

            if disabled:
                inp.disable()

    def add_target() -> None:
        """Add a new notification target."""
        targets = state.get_value(path, []) or []
        if not isinstance(targets, list):
            targets = []

        new_target = {
            "type": "discord",
            "enabled": True,
            "webhook_url": "",
        }
        targets.append(new_target)
        state.set_value(path, targets)
        if on_change:
            on_change(targets)
        refresh_editor()

    def remove_target(idx: int) -> None:
        """Remove a notification target."""
        targets = state.get_value(path, []) or []
        if 0 <= idx < len(targets):
            targets.pop(idx)
            state.set_value(path, targets)
            if on_change:
                on_change(targets)
        refresh_editor()

    def toggle_target(idx: int) -> None:
        """Toggle a target's enabled state."""
        targets = state.get_value(path, []) or []
        if 0 <= idx < len(targets):
            targets[idx]["enabled"] = not targets[idx].get("enabled", True)
            state.set_value(path, targets)
            if on_change:
                on_change(targets)
        refresh_editor()

    def update_target_type(idx: int, new_type: str) -> None:
        """Update a target's type."""
        targets = state.get_value(path, []) or []
        if 0 <= idx < len(targets):
            old_target = targets[idx]
            # Keep enabled state, reset other fields
            targets[idx] = {
                "type": new_type,
                "enabled": old_target.get("enabled", True),
            }
            state.set_value(path, targets)
            if on_change:
                on_change(targets)
        refresh_editor()

    def update_target_field(idx: int, field_key: str, value: Any) -> None:
        """Update a field within a target."""
        targets = state.get_value(path, []) or []
        if 0 <= idx < len(targets):
            targets[idx][field_key] = value
            state.set_value(path, targets)
            if on_change:
                on_change(targets)
        # Don't refresh - just update state

    # Initial render
    with container:
        _render_editor()

    return container
