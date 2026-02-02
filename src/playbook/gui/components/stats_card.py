"""
Statistics display card component for the Playbook GUI.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui


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
        color: Tailwind color name (blue, green, yellow, red, gray)
        icon: Optional icon name
        subtitle: Optional subtitle text

    Returns:
        The created card element
    """
    color_classes = {
        "blue": "bg-blue-50 border-blue-200 text-blue-800",
        "green": "bg-green-50 border-green-200 text-green-800",
        "yellow": "bg-yellow-50 border-yellow-200 text-yellow-800",
        "red": "bg-red-50 border-red-200 text-red-800",
        "gray": "bg-gray-50 border-gray-200 text-gray-800",
        "purple": "bg-purple-50 border-purple-200 text-purple-800",
    }

    icon_colors = {
        "blue": "text-blue-500",
        "green": "text-green-500",
        "yellow": "text-yellow-500",
        "red": "text-red-500",
        "gray": "text-gray-500",
        "purple": "text-purple-500",
    }

    base_class = color_classes.get(color, color_classes["blue"])
    icon_class = icon_colors.get(color, icon_colors["blue"])

    with ui.card().classes(f"w-40 border {base_class}") as card:
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

        ui.timer(2.0, update_value)

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
