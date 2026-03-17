"""
Statistics display card component for the Playbook GUI.

Redesigned: left accent bar, title-on-top, icon top-right, Quasar color vars.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from ..utils import safe_timer

# Map semantic tones to Quasar CSS variable names
_QUASAR_COLOR_MAP: dict[str, str] = {
    "accent": "--q-primary",
    "success": "--pb-positive",
    "warning": "--pb-warning",
    "danger": "--pb-negative",
    "muted": "--pb-text-muted",
    # Backward compat aliases
    "blue": "--q-primary",
    "green": "--pb-positive",
    "yellow": "--pb-warning",
    "red": "--pb-negative",
    "gray": "--pb-text-muted",
    "purple": "--q-primary",
}


def stats_card(
    title: str,
    value_fn: Callable[[], Any],
    color: str = "accent",
    icon: str | None = None,
    subtitle: str | None = None,
) -> ui.card:
    """Create a statistics card with left accent bar, icon top-right, and auto-updating value.

    Args:
        title: Card title/label
        value_fn: Callable that returns the current value
        color: Semantic color tone (accent, success, warning, danger, muted)
        icon: Optional Material icon name
        subtitle: Optional subtitle text

    Returns:
        The created card element
    """
    color_var = _QUASAR_COLOR_MAP.get(color, "--q-primary")

    with ui.card().classes("stat-card w-48").style(f"border-left: 4px solid var({color_var})") as card:
        with ui.row().classes("w-full items-start justify-between"):
            # Left: title + value
            with ui.column().classes("gap-1 flex-1"):
                ui.label(title).classes("text-xs font-medium uppercase tracking-wide").style(
                    "color: var(--pb-text-muted)"
                )
                value_label = ui.label(str(value_fn())).classes("text-3xl font-bold").style(f"color: var({color_var})")
                if subtitle:
                    ui.label(subtitle).classes("text-xs").style("color: var(--pb-text-muted)")
            # Right: icon
            if icon:
                ui.icon(icon).classes("text-2xl opacity-30")

        def update_value() -> None:
            try:
                value_label.text = str(value_fn())
            except (RuntimeError, KeyError):
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
