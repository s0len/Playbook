"""
Statistics display card component for the Playbook GUI.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from ..utils import safe_timer


def stats_card(
    title: str,
    value_fn: Callable[[], Any],
    color: str = "blue",
    icon: str | None = None,
    subtitle: str | None = None,
) -> ui.card:
    """Create a statistics card with auto-updating value.

    Args:
        title: Card title/label
        value_fn: Callable that returns the current value
        color: Tailwind color name (blue, green, yellow, red, gray, purple)
        icon: Optional icon name
        subtitle: Optional subtitle text

    Returns:
        The created card element
    """
    # Light/dark mode compatible color classes
    color_classes = {
        "blue": "bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200",
        "green": "bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800 text-green-800 dark:text-green-200",
        "yellow": "bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200",
        "red": "bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-800 dark:text-red-200",
        "gray": "bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200",
        "purple": "bg-purple-50 dark:bg-purple-900/30 border-purple-200 dark:border-purple-800 text-purple-800 dark:text-purple-200",
    }

    icon_colors = {
        "blue": "text-blue-500 dark:text-blue-400",
        "green": "text-green-500 dark:text-green-400",
        "yellow": "text-amber-500 dark:text-amber-400",
        "red": "text-red-500 dark:text-red-400",
        "gray": "text-slate-500 dark:text-slate-400",
        "purple": "text-purple-500 dark:text-purple-400",
    }

    base_class = color_classes.get(color, color_classes["blue"])
    icon_class = icon_colors.get(color, icon_colors["blue"])

    with ui.card().classes(f"stat-card w-40 border {base_class}") as card:
        with ui.column().classes("items-center py-2 px-3"):
            if icon:
                ui.icon(icon).classes(f"text-3xl {icon_class}")

            value_label = ui.label(str(value_fn())).classes("text-3xl font-bold")
            ui.label(title).classes("text-sm font-medium opacity-80")

            if subtitle:
                ui.label(subtitle).classes("text-xs opacity-60")

        def update_value() -> None:
            try:
                value_label.text = str(value_fn())
            except (RuntimeError, KeyError):
                # Client disconnected or element deleted - timer will be cleaned up
                pass
            except Exception:
                value_label.text = "?"

        safe_timer(2.0, update_value)

    return card


def stats_row(stats: list[dict[str, Any]]) -> None:
    """Create a row of statistics cards.

    Args:
        stats: List of stat definitions with keys: title, value_fn, color, icon
    """
    with ui.row().classes("w-full gap-4 flex-wrap justify-center"):
        for stat in stats:
            stats_card(
                title=stat["title"],
                value_fn=stat["value_fn"],
                color=stat.get("color", "blue"),
                icon=stat.get("icon"),
                subtitle=stat.get("subtitle"),
            )
