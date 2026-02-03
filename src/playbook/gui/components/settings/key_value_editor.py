"""
Key-value editor component for dictionary settings.

Provides a dynamic table editor for key-value pairs with add/remove functionality.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nicegui import ui

if TYPE_CHECKING:
    from playbook.gui.state.settings_state import SettingsFormState


def key_value_editor(
    state: SettingsFormState,
    path: str,
    label: str,
    *,
    description: str | None = None,
    key_label: str = "Key",
    value_label: str = "Value",
    key_placeholder: str = "Enter key",
    value_placeholder: str = "Enter value",
    value_type: str = "text",  # text, number
    presets: dict[str, Any] | None = None,
    disabled: bool = False,
    on_change: Callable[[dict[str, Any]], None] | None = None,
) -> ui.column:
    """Create a key-value pair editor bound to settings state.

    Args:
        state: SettingsFormState instance
        path: Dotted path to the setting (should be a dict)
        label: Display label for the editor
        description: Optional description text
        key_label: Label for the key column
        value_label: Label for the value column
        key_placeholder: Placeholder for key input
        value_placeholder: Placeholder for value input
        value_type: Type of value (text or number)
        presets: Optional preset values to show as quick-add buttons
        disabled: Whether the editor is disabled
        on_change: Optional callback when values change

    Returns:
        The NiceGUI column container
    """
    current_data = state.get_value(path, {}) or {}
    if not isinstance(current_data, dict):
        current_data = {}

    is_modified = state.is_field_modified(path)

    # Container for the editor
    container = ui.column().classes("w-full gap-2")

    def refresh_editor() -> None:
        """Rebuild the editor UI."""
        container.clear()
        with container:
            _render_editor()

    def _render_editor() -> None:
        """Render the editor content."""
        data = state.get_value(path, {}) or {}
        if not isinstance(data, dict):
            data = {}

        # Header
        with ui.row().classes("w-full items-center justify-between"):
            with ui.row().classes("items-center gap-2"):
                ui.label(label).classes("text-sm font-semibold text-slate-700 dark:text-slate-200")
                if is_modified:
                    ui.icon("edit").classes("text-amber-500 text-xs")
            if not disabled:
                ui.button(
                    icon="add",
                    on_click=lambda: add_row("", 0 if value_type == "number" else ""),
                ).props("flat dense").classes("text-blue-600")

        if description:
            ui.label(description).classes("text-xs text-slate-500 dark:text-slate-400")

        # Preset buttons
        if presets and not disabled:
            with ui.row().classes("gap-1 flex-wrap"):
                for preset_key, preset_value in presets.items():
                    if preset_key not in data:
                        ui.button(
                            f"+ {preset_key}",
                            on_click=lambda k=preset_key, v=preset_value: add_row(k, v),
                        ).props("flat dense size=sm").classes("text-xs")

        # Table of current values
        if data:
            with ui.column().classes("w-full gap-1"):
                # Header row
                with ui.row().classes(
                    "w-full items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400"
                ):
                    ui.label(key_label).classes("flex-1")
                    ui.label(value_label).classes("w-24")
                    ui.label("").classes("w-8")  # Action column

                # Data rows
                for key, value in data.items():
                    _render_row(key, value)
        else:
            ui.label("No entries").classes("text-sm text-slate-500 dark:text-slate-400 italic py-2")

    def _render_row(key: str, value: Any) -> None:
        """Render a single key-value row."""
        with ui.row().classes("w-full items-center gap-2"):
            # Key input
            ui.input(value=key).classes("flex-1 text-sm").props("outlined dense readonly")

            # Value input
            def on_value_change(e, k=key) -> None:
                data = state.get_value(path, {}) or {}
                new_value = e.value
                if value_type == "number":
                    try:
                        new_value = int(new_value) if new_value else 0
                    except ValueError:
                        new_value = 0
                data[k] = new_value
                state.set_value(path, data)
                if on_change:
                    on_change(data)

            value_input = ui.input(value=str(value), on_change=on_value_change)
            value_input.classes("w-24 text-sm").props("outlined dense")
            if value_type == "number":
                value_input.props('type="number"')
            if disabled:
                value_input.disable()

            # Delete button
            if not disabled:
                ui.button(
                    icon="delete",
                    on_click=lambda k=key: remove_row(k),
                ).props("flat dense color=negative").classes("text-red-500")

    def add_row(new_key: str, new_value: Any) -> None:
        """Add a new key-value pair."""
        data = state.get_value(path, {}) or {}
        if not isinstance(data, dict):
            data = {}

        # Generate unique key if empty
        if not new_key:
            counter = 1
            while f"key{counter}" in data:
                counter += 1
            new_key = f"key{counter}"

        data[new_key] = new_value
        state.set_value(path, data)
        if on_change:
            on_change(data)
        refresh_editor()

    def remove_row(key: str) -> None:
        """Remove a key-value pair."""
        data = state.get_value(path, {}) or {}
        if key in data:
            del data[key]
            state.set_value(path, data)
            if on_change:
                on_change(data)
        refresh_editor()

    # Initial render
    with container:
        _render_editor()

    return container


def quality_score_editor(
    state: SettingsFormState,
    path: str,
    label: str,
    *,
    description: str | None = None,
    presets: dict[str, int] | None = None,
    disabled: bool = False,
) -> ui.column:
    """Specialized key-value editor for quality scores.

    Args:
        state: SettingsFormState instance
        path: Dotted path to the scoring dict
        label: Display label
        description: Optional description
        presets: Preset score values
        disabled: Whether disabled

    Returns:
        The editor container
    """
    return key_value_editor(
        state,
        path,
        label,
        description=description,
        key_label="Name",
        value_label="Score",
        key_placeholder="e.g., mwr",
        value_placeholder="50",
        value_type="number",
        presets=presets,
        disabled=disabled,
    )
