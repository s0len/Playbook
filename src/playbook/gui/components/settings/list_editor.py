"""
List editor component for array settings.

Provides a dynamic list editor with add/remove functionality.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from nicegui import ui

if TYPE_CHECKING:
    from playbook.gui.state.settings_state import SettingsFormState


def list_editor(
    state: SettingsFormState,
    path: str,
    label: str,
    *,
    description: str | None = None,
    placeholder: str = "Enter value",
    disabled: bool = False,
    on_change: Callable[[list[str]], None] | None = None,
    suggestions: list[str] | None = None,
    max_items: int | None = None,
) -> ui.column:
    """Create a list editor bound to settings state.

    Args:
        state: SettingsFormState instance
        path: Dotted path to the setting (should be a list)
        label: Display label for the editor
        description: Optional description text
        placeholder: Placeholder for new item input
        disabled: Whether the editor is disabled
        on_change: Optional callback when values change
        suggestions: Optional list of suggestions to show
        max_items: Maximum number of items allowed

    Returns:
        The NiceGUI column container
    """
    current_data = state.get_value(path, []) or []
    if not isinstance(current_data, list):
        current_data = [current_data] if current_data else []

    is_modified = state.is_field_modified(path)

    container = ui.column().classes("w-full gap-2")

    def refresh_editor() -> None:
        """Rebuild the editor UI."""
        container.clear()
        with container:
            _render_editor()

    def _render_editor() -> None:
        """Render the editor content."""
        items = state.get_value(path, []) or []
        if not isinstance(items, list):
            items = [items] if items else []

        # Header
        with ui.row().classes("w-full items-center justify-between"):
            with ui.row().classes("items-center gap-2"):
                ui.label(label).classes("text-sm font-semibold text-slate-700 dark:text-slate-200")
                ui.badge(str(len(items))).props("color=grey-7").classes("text-xs")
                if is_modified:
                    ui.icon("edit").classes("text-amber-500 text-xs")

        if description:
            ui.label(description).classes("text-xs text-slate-500 dark:text-slate-400")

        # Current items
        if items:
            with ui.column().classes("w-full gap-1"):
                for idx, item in enumerate(items):
                    _render_item(idx, item)
        else:
            ui.label("No items").classes("text-sm text-slate-500 dark:text-slate-400 italic py-2")

        # Add new item
        if not disabled and (max_items is None or len(items) < max_items):
            with ui.row().classes("w-full items-center gap-2 mt-2"):
                if suggestions:
                    # Use autocomplete select
                    new_input = (
                        ui.select(
                            options=suggestions,
                            with_input=True,
                            new_value_mode="add-unique",
                        )
                        .classes("flex-1")
                        .props(f'outlined dense label="{placeholder}"')
                    )
                else:
                    new_input = ui.input(placeholder=placeholder).classes("flex-1").props("outlined dense")

                def add_item() -> None:
                    value = new_input.value
                    if value:
                        add_list_item(str(value))
                        new_input.value = ""

                ui.button(icon="add", on_click=add_item).props("flat dense").classes("text-blue-600")

    def _render_item(idx: int, item: str) -> None:
        """Render a single list item."""
        with ui.row().classes("w-full items-center gap-2 bg-slate-50 dark:bg-slate-800 rounded px-2 py-1"):
            ui.label(str(item)).classes("flex-1 text-sm text-slate-700 dark:text-slate-200 font-mono")
            if not disabled:
                # Move up
                if idx > 0:
                    ui.button(
                        icon="keyboard_arrow_up",
                        on_click=lambda i=idx: move_item(i, i - 1),
                    ).props("flat dense size=sm")
                # Move down
                items = state.get_value(path, []) or []
                if idx < len(items) - 1:
                    ui.button(
                        icon="keyboard_arrow_down",
                        on_click=lambda i=idx: move_item(i, i + 1),
                    ).props("flat dense size=sm")
                # Delete
                ui.button(
                    icon="close",
                    on_click=lambda i=idx: remove_item(i),
                ).props("flat dense size=sm color=negative")

    def add_list_item(value: str) -> None:
        """Add a new item to the list."""
        items = state.get_value(path, []) or []
        if not isinstance(items, list):
            items = [items] if items else []

        if max_items is not None and len(items) >= max_items:
            ui.notify(f"Maximum {max_items} items allowed", type="warning")
            return

        items.append(value)
        state.set_value(path, items)
        if on_change:
            on_change(items)
        refresh_editor()

    def remove_item(idx: int) -> None:
        """Remove an item from the list."""
        items = state.get_value(path, []) or []
        if 0 <= idx < len(items):
            items.pop(idx)
            state.set_value(path, items)
            if on_change:
                on_change(items)
        refresh_editor()

    def move_item(from_idx: int, to_idx: int) -> None:
        """Move an item within the list."""
        items = state.get_value(path, []) or []
        if 0 <= from_idx < len(items) and 0 <= to_idx < len(items):
            item = items.pop(from_idx)
            items.insert(to_idx, item)
            state.set_value(path, items)
            if on_change:
                on_change(items)
        refresh_editor()

    # Initial render
    with container:
        _render_editor()

    return container


def glob_pattern_editor(
    state: SettingsFormState,
    path: str,
    label: str,
    *,
    description: str | None = None,
    disabled: bool = False,
) -> ui.column:
    """Specialized list editor for glob patterns.

    Args:
        state: SettingsFormState instance
        path: Dotted path to the pattern list
        label: Display label
        description: Optional description
        disabled: Whether disabled

    Returns:
        The editor container
    """
    common_patterns = [
        "**/*.mkv",
        "**/*.mp4",
        "**/*.ts",
        "**/*.avi",
        "**/Sample/**",
        "**/Subs/**",
        "**/Featurettes/**",
    ]

    return list_editor(
        state,
        path,
        label,
        description=description,
        placeholder="*.pattern",
        disabled=disabled,
        suggestions=common_patterns,
    )
