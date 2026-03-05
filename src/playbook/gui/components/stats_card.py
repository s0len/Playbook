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
    color: str = "accent",
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
    surface_classes = {
        "accent": "app-stat-surface-accent",
        "success": "app-stat-surface-success",
        "warning": "app-stat-surface-warning",
        "danger": "app-stat-surface-danger",
        "muted": "app-stat-surface-muted",
    }
    icon_classes = {
        "accent": "app-stat-icon-accent",
        "success": "app-text-success",
        "warning": "app-text-warning",
        "danger": "app-text-danger",
        "muted": "app-stat-icon-muted",
    }

    # Backward compatibility aliases
    alias_map = {
        "blue": "accent",
        "green": "success",
        "yellow": "warning",
        "red": "danger",
        "gray": "muted",
        "purple": "muted",
    }
    tone = alias_map.get(color, color)
    base_class = surface_classes.get(tone, surface_classes["accent"])
    icon_class = icon_classes.get(tone, icon_classes["accent"])

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
