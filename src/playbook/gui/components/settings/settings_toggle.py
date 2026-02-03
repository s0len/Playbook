"""
Settings toggle component for boolean values.

Provides a styled toggle switch with label and optional description.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from nicegui import ui

if TYPE_CHECKING:
    from playbook.gui.state.settings_state import SettingsFormState


def settings_toggle(
    state: SettingsFormState,
    path: str,
    label: str,
    *,
    description: str | None = None,
    disabled: bool = False,
    on_change: Callable[[bool], None] | None = None,
) -> ui.switch:
    """Create a toggle switch bound to settings state.

    Args:
        state: SettingsFormState instance
        path: Dotted path to the setting (e.g., "settings.dry_run")
        label: Display label for the toggle
        description: Optional description text
        disabled: Whether the toggle is disabled
        on_change: Optional callback when value changes

    Returns:
        The NiceGUI switch element
    """
    current_value = bool(state.get_value(path, False))
    is_modified = state.is_field_modified(path)

    with ui.row().classes("w-full items-start justify-between py-1"):
        with ui.column().classes("gap-0 flex-1"):
            with ui.row().classes("items-center gap-2"):
                ui.label(label).classes("text-sm font-medium text-slate-700 dark:text-slate-200")
                if is_modified:
                    ui.icon("edit").classes("text-amber-500 text-xs")
            if description:
                ui.label(description).classes("text-xs text-slate-500 dark:text-slate-400")

        def handle_change(e) -> None:
            state.set_value(path, e.value)
            if on_change:
                on_change(e.value)

        switch = ui.switch(value=current_value, on_change=handle_change)
        if disabled:
            switch.disable()

    return switch


def settings_toggle_inline(
    state: SettingsFormState,
    path: str,
    label: str,
    *,
    disabled: bool = False,
    on_change: Callable[[bool], None] | None = None,
) -> ui.switch:
    """Create an inline toggle switch (label to the left of switch).

    Args:
        state: SettingsFormState instance
        path: Dotted path to the setting
        label: Display label for the toggle
        disabled: Whether the toggle is disabled
        on_change: Optional callback when value changes

    Returns:
        The NiceGUI switch element
    """
    current_value = bool(state.get_value(path, False))

    def handle_change(e) -> None:
        state.set_value(path, e.value)
        if on_change:
            on_change(e.value)

    with ui.row().classes("items-center gap-2"):
        switch = ui.switch(label, value=current_value, on_change=handle_change)
        switch.classes("text-sm text-slate-700 dark:text-slate-200")
        if disabled:
            switch.disable()

    return switch
