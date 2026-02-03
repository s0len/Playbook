"""
Settings select component for dropdown selections.

Provides styled dropdown selectors with validation feedback.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nicegui import ui

if TYPE_CHECKING:
    from playbook.gui.state.settings_state import SettingsFormState


def settings_select(
    state: SettingsFormState,
    path: str,
    label: str,
    options: list[str] | list[dict[str, Any]],
    *,
    description: str | None = None,
    disabled: bool = False,
    clearable: bool = False,
    on_change: Callable[[Any], None] | None = None,
    width: str = "w-full",
) -> ui.select:
    """Create a dropdown select bound to settings state.

    Args:
        state: SettingsFormState instance
        path: Dotted path to the setting
        label: Display label for the select
        options: List of options (strings or dicts with 'label' and 'value' keys)
        description: Optional description text
        disabled: Whether the select is disabled
        clearable: Whether the selection can be cleared
        on_change: Optional callback when value changes
        width: Tailwind width class

    Returns:
        The NiceGUI select element
    """
    current_value = state.get_value(path)
    is_modified = state.is_field_modified(path)
    error = state.get_validation_error(path)

    with ui.column().classes(f"{width} gap-1"):
        # Label row
        with ui.row().classes("items-center gap-2"):
            ui.label(label).classes("text-sm font-medium text-slate-700 dark:text-slate-200")
            if is_modified:
                ui.icon("edit").classes("text-amber-500 text-xs")

        # Select
        select_props = "outlined dense"
        if error and error.severity == "error":
            select_props += " error"
        if clearable:
            select_props += " clearable"

        def handle_change(e) -> None:
            state.set_value(path, e.value)
            if on_change:
                on_change(e.value)

        select = (
            ui.select(
                options=options,
                value=current_value,
                on_change=handle_change,
            )
            .classes("w-full")
            .props(select_props)
        )

        if disabled:
            select.disable()

        # Description or error
        if error:
            error_classes = (
                "text-xs text-red-600 dark:text-red-400"
                if error.severity == "error"
                else "text-xs text-amber-600 dark:text-amber-400"
            )
            ui.label(error.message).classes(error_classes)
        elif description:
            ui.label(description).classes("text-xs text-slate-500 dark:text-slate-400")

    return select


def settings_radio(
    state: SettingsFormState,
    path: str,
    label: str,
    options: list[str] | list[dict[str, Any]],
    *,
    description: str | None = None,
    disabled: bool = False,
    horizontal: bool = True,
    on_change: Callable[[Any], None] | None = None,
) -> ui.radio:
    """Create a radio button group bound to settings state.

    Args:
        state: SettingsFormState instance
        path: Dotted path to the setting
        label: Display label for the radio group
        options: List of options
        description: Optional description text
        disabled: Whether the radio is disabled
        horizontal: Whether to display options horizontally
        on_change: Optional callback when value changes

    Returns:
        The NiceGUI radio element
    """
    current_value = state.get_value(path)
    is_modified = state.is_field_modified(path)

    with ui.column().classes("w-full gap-2"):
        # Label row
        with ui.row().classes("items-center gap-2"):
            ui.label(label).classes("text-sm font-medium text-slate-700 dark:text-slate-200")
            if is_modified:
                ui.icon("edit").classes("text-amber-500 text-xs")

        def handle_change(e) -> None:
            state.set_value(path, e.value)
            if on_change:
                on_change(e.value)

        radio_props = "dense"
        if horizontal:
            radio_props += " inline"

        radio = (
            ui.radio(
                options=options,
                value=current_value,
                on_change=handle_change,
            )
            .props(radio_props)
            .classes("text-slate-700 dark:text-slate-200")
        )

        if disabled:
            radio.disable()

        if description:
            ui.label(description).classes("text-xs text-slate-500 dark:text-slate-400")

    return radio
