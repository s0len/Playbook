"""Shared field rendering utilities for integration editor modals.

All functions operate on a `working: dict[str, Any]` (the modal's local copy),
NOT on SettingsFormState directly. This keeps them stateless and reusable.
"""

from __future__ import annotations

import os
from typing import Any

from nicegui import ui

from ..app_button import neutralize_button_utilities

# ---------------------------------------------------------------------------
# Nested dict helpers
# ---------------------------------------------------------------------------


def nested_get(data: dict, dotted_key: str, default: Any = None) -> Any:
    """Read a value from a nested dict using dotted key."""
    keys = dotted_key.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return default
    return current


def nested_set(data: dict, dotted_key: str, value: Any) -> None:
    """Write a value into a nested dict using dotted key."""
    keys = dotted_key.split(".")
    current = data
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value


# ---------------------------------------------------------------------------
# Env var placeholder
# ---------------------------------------------------------------------------


def get_env_placeholder(env_var: str | None, fallback: str, *, mask: bool = False) -> str:
    """Get placeholder showing env var value if set."""
    if not env_var:
        return fallback
    value = os.environ.get(env_var)
    if value:
        if mask:
            return f"From {env_var}: {'*' * min(8, len(value))}"
        return f"From {env_var}: {value}"
    return fallback


# ---------------------------------------------------------------------------
# Field renderers
# ---------------------------------------------------------------------------


def render_fields(working: dict[str, Any], fields: list[dict[str, Any]]) -> None:
    """Render fields, grouping by row number where specified."""
    rows: dict[int | None, list[dict[str, Any]]] = {}
    for field_def in fields:
        row = field_def.get("row")
        rows.setdefault(row, []).append(field_def)

    for row_key in sorted(rows, key=lambda x: (x is None, x)):
        group = rows[row_key]
        if len(group) == 1 and group[0].get("type") in ("rewrite_rules", "list"):
            render_single_field(working, group[0])
        elif row_key is not None:
            with ui.row().classes("w-full gap-4"):
                for field_def in group:
                    render_single_field(working, field_def)
        else:
            for field_def in group:
                render_single_field(working, field_def)


def render_single_field(working: dict[str, Any], field_def: dict[str, Any]) -> None:
    """Render one field."""
    ftype = field_def.get("type", "text")
    key = field_def["key"]

    if ftype == "rewrite_rules":
        render_rewrite_rules(working, key)
        return

    if ftype == "list":
        render_list_field(working, field_def)
        return

    if ftype == "toggle":
        render_toggle_row(
            working,
            key,
            field_def.get("label", key),
            field_def.get("description", ""),
        )
        return

    if ftype == "select":
        options = field_def.get("options", [])
        current = nested_get(working, key, options[0] if options else "")

        def on_change(e, k=key):
            nested_set(working, k, e.value)

        width = field_def.get("width", "flex-1")
        ui.select(
            options,
            value=current,
            on_change=on_change,
        ).classes(f"{width} settings-input").props(f"outlined dense label='{field_def.get('label', key)}'")
        return

    # Text / password / number
    label = field_def.get("label", key)
    env_var = field_def.get("env")
    placeholder = field_def.get("placeholder", "")
    if env_var:
        placeholder = get_env_placeholder(env_var, placeholder, mask=(ftype == "password"))
    current = nested_get(working, key, "")

    input_props = "outlined dense"
    if ftype == "password":
        input_props += ' type="password"'
    elif ftype == "number":
        input_props += ' type="number"'

    def on_change(e, k=key):
        nested_set(working, k, e.value)

    width = field_def.get("width", "flex-1")
    ui.input(
        value=str(current) if current else "",
        label=label,
        placeholder=placeholder,
        on_change=on_change,
    ).classes(f"{width} settings-input").props(input_props)


# ---------------------------------------------------------------------------
# Toggle row
# ---------------------------------------------------------------------------


def render_toggle_row(
    working: dict[str, Any],
    key: str,
    label: str,
    description: str,
    *,
    on_change=None,
) -> None:
    """Render a toggle row with label and description."""
    current = bool(nested_get(working, key))

    def _on_change(e, k=key):
        nested_set(working, k, bool(e.value))
        if on_change:
            on_change(e)

    with ui.row().classes("w-full items-center justify-between rounded-lg border border-white/10 p-3"):
        with ui.column().classes("gap-0"):
            ui.label(label).classes("text-sm font-medium text-slate-200")
            if description:
                ui.label(description).classes("text-xs text-slate-400")
        ui.switch(value=current, on_change=_on_change).classes("settings-toggle")


# ---------------------------------------------------------------------------
# Rewrite rules (from -> to pairs)
# ---------------------------------------------------------------------------


def render_rewrite_rules(working: dict[str, Any], key: str) -> None:
    """Render an inline rewrite rules editor within the modal."""
    rules_container = ui.column().classes("w-full gap-2")

    def refresh_rules() -> None:
        rules_container.clear()
        current_rules = nested_get(working, key) or []
        if not isinstance(current_rules, list):
            current_rules = []

        with rules_container:
            ui.label("Path Rewriting").classes("text-xs text-slate-500 mb-1")

            for idx, rule in enumerate(current_rules):
                if not isinstance(rule, dict):
                    continue
                with ui.row().classes("w-full items-center gap-2"):
                    from_input = (
                        ui.input(value=rule.get("from", ""), placeholder="/data/destination")
                        .classes("flex-1")
                        .props("dense outlined")
                    )
                    ui.icon("arrow_forward").classes("text-slate-400")
                    to_input = (
                        ui.input(value=rule.get("to", ""), placeholder="/mnt/plex/media")
                        .classes("flex-1")
                        .props("dense outlined")
                    )

                    def make_update(index, f_inp, t_inp):
                        def handler(_):
                            cur = nested_get(working, key) or []
                            if index < len(cur):
                                cur[index] = {"from": f_inp.value, "to": t_inp.value}
                                nested_set(working, key, cur)

                        return handler

                    from_input.on("blur", make_update(idx, from_input, to_input))
                    to_input.on("blur", make_update(idx, from_input, to_input))

                    def make_delete(index):
                        def handler():
                            cur = nested_get(working, key) or []
                            if index < len(cur):
                                cur.pop(index)
                                nested_set(working, key, cur)
                                refresh_rules()

                        return handler

                    neutralize_button_utilities(
                        ui.button(icon="delete", on_click=make_delete(idx)).props("flat dense")
                    ).classes("app-text-danger")

            def add_rule():
                cur = nested_get(working, key) or []
                if not isinstance(cur, list):
                    cur = []
                cur.append({"from": "", "to": ""})
                nested_set(working, key, cur)
                refresh_rules()

            neutralize_button_utilities(
                ui.button("Add Rewrite Rule", icon="add", on_click=add_rule).props("flat dense")
            ).classes("mt-1")

    refresh_rules()


# ---------------------------------------------------------------------------
# List field (e.g. sports filter)
# ---------------------------------------------------------------------------


def render_list_field(working: dict[str, Any], field_def: dict[str, Any]) -> None:
    """Render a simple string-list editor."""
    key = field_def["key"]
    label = field_def.get("label", key)
    description = field_def.get("description", "")
    placeholder = field_def.get("placeholder", "")

    list_container = ui.column().classes("w-full gap-2")

    def refresh_list() -> None:
        list_container.clear()
        current = nested_get(working, key) or []
        if not isinstance(current, list):
            current = []

        with list_container:
            if label:
                ui.label(label).classes("text-xs font-medium text-slate-400")
            if description:
                ui.label(description).classes("text-xs text-slate-500")

            for idx, item in enumerate(current):
                with ui.row().classes("w-full items-center gap-2"):
                    inp = ui.input(value=str(item), placeholder=placeholder).classes("flex-1").props("dense outlined")

                    def make_update(index, input_el):
                        def handler(_):
                            cur = nested_get(working, key) or []
                            if index < len(cur):
                                cur[index] = input_el.value
                                nested_set(working, key, cur)

                        return handler

                    inp.on("blur", make_update(idx, inp))

                    def make_delete(index):
                        def handler():
                            cur = nested_get(working, key) or []
                            if index < len(cur):
                                cur.pop(index)
                                nested_set(working, key, cur)
                                refresh_list()

                        return handler

                    neutralize_button_utilities(
                        ui.button(icon="delete", on_click=make_delete(idx)).props("flat dense")
                    ).classes("app-text-danger")

            def add_item():
                cur = nested_get(working, key) or []
                if not isinstance(cur, list):
                    cur = []
                cur.append("")
                nested_set(working, key, cur)
                refresh_list()

            neutralize_button_utilities(
                ui.button(f"Add {label}" if label else "Add", icon="add", on_click=add_item).props("flat dense")
            ).classes("mt-1")

    refresh_list()


# ---------------------------------------------------------------------------
# Key-value field (e.g. docker_env)
# ---------------------------------------------------------------------------


def render_key_value_field(
    working: dict[str, Any],
    key: str,
    key_label: str = "Key",
    value_label: str = "Value",
) -> None:
    """Render a key-value pair editor within a modal."""
    kv_container = ui.column().classes("w-full gap-2")

    def refresh_kv() -> None:
        kv_container.clear()
        current = nested_get(working, key) or {}
        if not isinstance(current, dict):
            current = {}

        with kv_container:
            if current:
                with ui.row().classes("w-full items-center gap-2 text-xs font-medium text-slate-500"):
                    ui.label(key_label).classes("flex-1")
                    ui.label(value_label).classes("flex-1")
                    ui.label("").classes("w-8")

                for k, v in list(current.items()):
                    with ui.row().classes("w-full items-center gap-2"):
                        key_inp = ui.input(value=k).classes("flex-1").props("dense outlined")
                        val_inp = ui.input(value=str(v)).classes("flex-1").props("dense outlined")

                        def make_update(old_key, k_inp, v_inp):
                            def handler(_):
                                cur = nested_get(working, key) or {}
                                if not isinstance(cur, dict):
                                    cur = {}
                                new_key = k_inp.value
                                new_val = v_inp.value
                                if old_key != new_key:
                                    cur.pop(old_key, None)
                                cur[new_key] = new_val
                                nested_set(working, key, cur)

                            return handler

                        key_inp.on("blur", make_update(k, key_inp, val_inp))
                        val_inp.on("blur", make_update(k, key_inp, val_inp))

                        def make_delete(del_key):
                            def handler():
                                cur = nested_get(working, key) or {}
                                cur.pop(del_key, None)
                                nested_set(working, key, cur)
                                refresh_kv()

                            return handler

                        neutralize_button_utilities(
                            ui.button(icon="delete", on_click=make_delete(k)).props("flat dense")
                        ).classes("app-text-danger")

            def add_entry():
                cur = nested_get(working, key) or {}
                if not isinstance(cur, dict):
                    cur = {}
                counter = 1
                while f"key{counter}" in cur:
                    counter += 1
                cur[f"key{counter}"] = ""
                nested_set(working, key, cur)
                refresh_kv()

            neutralize_button_utilities(
                ui.button("Add Entry", icon="add", on_click=add_entry).props("flat dense")
            ).classes("mt-1")

    refresh_kv()
