"""
Styled progress bar component for the Playbook GUI.
"""

from __future__ import annotations

from typing import Literal

from nicegui import ui

ProgressVariant = Literal["success", "warning", "info", "error", "default"]


def progress_bar(
    value: float,
    *,
    variant: ProgressVariant = "default",
    show_value: bool = True,
    size: str = "md",
    label: str | None = None,
) -> ui.linear_progress:
    """Create a styled progress bar.

    Args:
        value: Progress value from 0.0 to 1.0
        variant: Color variant (success, warning, info, error, default)
        show_value: Whether to show percentage text
        size: Size variant (sm, md, lg)
        label: Optional label to show alongside progress

    Returns:
        The created progress bar element
    """
    # Size classes
    size_classes = {
        "sm": "h-1",
        "md": "h-2",
        "lg": "h-3",
    }

    # Variant to CSS class mapping
    variant_classes = {
        "success": "progress-success",
        "warning": "progress-warning",
        "info": "progress-info",
        "error": "progress-error",
        "default": "progress-info",
    }

    # Quasar color mapping for the progress bar
    color_map = {
        "success": "positive",
        "warning": "warning",
        "info": "primary",
        "error": "negative",
        "default": "primary",
    }

    height_class = size_classes.get(size, size_classes["md"])
    variant_class = variant_classes.get(variant, variant_classes["default"])
    color = color_map.get(variant, "primary")

    with ui.row().classes("w-full items-center gap-3"):
        if label:
            ui.label(label).classes("text-sm text-slate-600 dark:text-slate-400 w-24 shrink-0")

        progress = (
            ui.linear_progress(value=value, show_value=False)
            .classes(f"flex-1 modern-progress {variant_class} {height_class}")
            .props(f"color={color}")
        )

        if show_value:
            percentage = int(value * 100)
            ui.label(f"{percentage}%").classes("text-sm font-medium text-slate-700 dark:text-slate-300 w-12 text-right")

    return progress


def mini_progress_bar(
    value: float,
    *,
    variant: ProgressVariant = "default",
    width: str = "w-24",
) -> ui.linear_progress:
    """Create a compact progress bar for table cells.

    Args:
        value: Progress value from 0.0 to 1.0
        variant: Color variant
        width: Width class

    Returns:
        The created progress bar element
    """
    variant_classes = {
        "success": "progress-success",
        "warning": "progress-warning",
        "info": "progress-info",
        "error": "progress-error",
        "default": "progress-info",
    }

    color_map = {
        "success": "positive",
        "warning": "warning",
        "info": "primary",
        "error": "negative",
        "default": "primary",
    }

    variant_class = variant_classes.get(variant, variant_classes["default"])
    color = color_map.get(variant, "primary")

    return (
        ui.linear_progress(value=value, show_value=False)
        .classes(f"{width} modern-progress {variant_class} h-1.5")
        .props(f"color={color}")
    )


def progress_with_counts(
    matched: int,
    total: int,
    *,
    variant: ProgressVariant | None = None,
    size: str = "md",
) -> None:
    """Create a progress bar with matched/total counts.

    Args:
        matched: Number of matched items
        total: Total number of items
        variant: Color variant (auto-selected if None)
        size: Size variant
    """
    value = 0.0 if total == 0 else matched / total

    # Auto-select variant based on progress
    if variant is None:
        if value >= 1.0:
            variant = "success"
        elif value >= 0.5:
            variant = "info"
        elif value > 0:
            variant = "warning"
        else:
            variant = "default"

    with ui.row().classes("w-full items-center gap-3"):
        progress_bar(value, variant=variant, show_value=False, size=size)
        ui.label(f"{matched}/{total}").classes("text-sm font-medium text-slate-600 dark:text-slate-400 shrink-0")
