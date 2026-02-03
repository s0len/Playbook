"""
Settings input component for text and number values.

Provides styled input fields with validation feedback.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nicegui import ui

if TYPE_CHECKING:
    from playbook.gui.settings_state.settings_state import SettingsFormState


def settings_input(
    state: SettingsFormState,
    path: str,
    label: str,
    *,
    description: str | None = None,
    placeholder: str | None = None,
    input_type: str = "text",
    disabled: bool = False,
    required: bool = False,
    validation: Callable[[Any], str | None] | None = None,
    on_change: Callable[[Any], None] | None = None,
    width: str = "w-full",
    suffix: str | None = None,
    prefix: str | None = None,
) -> ui.input:
    """Create a text/number input bound to settings state.

    Args:
        state: SettingsFormState instance
        path: Dotted path to the setting
        label: Display label for the input
        description: Optional description text
        placeholder: Placeholder text
        input_type: Input type (text, number, password)
        disabled: Whether the input is disabled
        required: Whether the field is required
        validation: Optional validation function returning error message or None
        on_change: Optional callback when value changes
        width: Tailwind width class
        suffix: Optional suffix text/unit
        prefix: Optional prefix text

    Returns:
        The NiceGUI input element
    """
    current_value = state.get_value(path, "")
    if current_value is None:
        current_value = ""
    elif not isinstance(current_value, str):
        current_value = str(current_value)

    is_modified = state.is_field_modified(path)
    error = state.get_validation_error(path)

    with ui.column().classes(f"{width} gap-1"):
        # Label row
        with ui.row().classes("items-center gap-2"):
            ui.label(label).classes("text-sm font-medium text-slate-700 dark:text-slate-200")
            if required:
                ui.label("*").classes("text-red-500 text-sm")
            if is_modified:
                ui.icon("edit").classes("text-amber-500 text-xs")

        # Input with optional prefix/suffix
        input_props = "outlined dense"
        if error and error.severity == "error":
            input_props += " error"

        with ui.row().classes("w-full items-center gap-1"):
            if prefix:
                ui.label(prefix).classes("text-sm text-slate-500 dark:text-slate-400")

            def handle_change(e) -> None:
                value = e.value
                # Convert to appropriate type
                if input_type == "number" and value:
                    try:
                        value = float(value) if "." in str(value) else int(value)
                    except (ValueError, TypeError):
                        pass

                # Run validation if provided
                if validation:
                    error_msg = validation(value)
                    if error_msg:
                        state.set_validation_error(path, error_msg)
                    else:
                        state.clear_validation_error(path)

                state.set_value(path, value)
                if on_change:
                    on_change(value)

            input_elem = (
                ui.input(
                    value=current_value,
                    placeholder=placeholder or "",
                    on_change=handle_change,
                )
                .classes("flex-1")
                .props(input_props)
            )

            if input_type == "number":
                input_elem.props('type="number"')
            elif input_type == "password":
                input_elem.props('type="password"')

            if disabled:
                input_elem.disable()

            if suffix:
                ui.label(suffix).classes("text-sm text-slate-500 dark:text-slate-400")

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

    return input_elem


def settings_path_input(
    state: SettingsFormState,
    path: str,
    label: str,
    *,
    description: str | None = None,
    placeholder: str = "/path/to/directory",
    disabled: bool = False,
    required: bool = False,
    on_change: Callable[[str], None] | None = None,
) -> ui.input:
    """Create a path input with file browser hint.

    Args:
        state: SettingsFormState instance
        path: Dotted path to the setting
        label: Display label for the input
        description: Optional description text
        placeholder: Placeholder text
        disabled: Whether the input is disabled
        required: Whether the field is required
        on_change: Optional callback when value changes

    Returns:
        The NiceGUI input element
    """
    current_value = state.get_value(path, "")
    if current_value is None:
        current_value = ""
    elif not isinstance(current_value, str):
        current_value = str(current_value)

    is_modified = state.is_field_modified(path)
    error = state.get_validation_error(path)

    with ui.column().classes("w-full gap-1"):
        # Label row
        with ui.row().classes("items-center gap-2"):
            ui.icon("folder").classes("text-slate-400 text-sm")
            ui.label(label).classes("text-sm font-medium text-slate-700 dark:text-slate-200")
            if required:
                ui.label("*").classes("text-red-500 text-sm")
            if is_modified:
                ui.icon("edit").classes("text-amber-500 text-xs")

        # Input
        input_props = "outlined dense"
        if error and error.severity == "error":
            input_props += " error"

        def handle_change(e) -> None:
            state.set_value(path, e.value)
            if on_change:
                on_change(e.value)

        input_elem = (
            ui.input(
                value=current_value,
                placeholder=placeholder,
                on_change=handle_change,
            )
            .classes("w-full font-mono text-sm")
            .props(input_props)
        )

        if disabled:
            input_elem.disable()

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

    return input_elem


def settings_textarea(
    state: SettingsFormState,
    path: str,
    label: str,
    *,
    description: str | None = None,
    placeholder: str | None = None,
    rows: int = 4,
    disabled: bool = False,
    on_change: Callable[[str], None] | None = None,
) -> ui.textarea:
    """Create a textarea input bound to settings state.

    Args:
        state: SettingsFormState instance
        path: Dotted path to the setting
        label: Display label
        description: Optional description text
        placeholder: Placeholder text
        rows: Number of visible rows
        disabled: Whether the input is disabled
        on_change: Optional callback when value changes

    Returns:
        The NiceGUI textarea element
    """
    current_value = state.get_value(path, "")
    if current_value is None:
        current_value = ""

    is_modified = state.is_field_modified(path)

    with ui.column().classes("w-full gap-1"):
        with ui.row().classes("items-center gap-2"):
            ui.label(label).classes("text-sm font-medium text-slate-700 dark:text-slate-200")
            if is_modified:
                ui.icon("edit").classes("text-amber-500 text-xs")

        def handle_change(e) -> None:
            state.set_value(path, e.value)
            if on_change:
                on_change(e.value)

        textarea = (
            ui.textarea(value=current_value, placeholder=placeholder or "", on_change=handle_change)
            .classes("w-full font-mono text-sm")
            .props(f'outlined dense rows="{rows}"')
        )

        if disabled:
            textarea.disable()

        if description:
            ui.label(description).classes("text-xs text-slate-500 dark:text-slate-400")

    return textarea
