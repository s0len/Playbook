"""Semantic button helper using Quasar's native color system."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

# Quasar color props per variant — ui.colors() sets --q-primary etc.
# so these automatically follow the active theme.
_VARIANT_PROPS: dict[str, str] = {
    "primary": 'color="primary"',
    "danger": 'color="negative"',
    "outline": 'outline color="primary"',
    "flat": "flat",
}


def app_button(
    text: str | None = None,
    *,
    icon: str | None = None,
    on_click: Callable[..., Any] | None = None,
    variant: str = "outline",
    classes: str = "",
    props: str = "",
) -> ui.button:
    """Create a button using Quasar's color system.

    With ui.colors(primary=...) set by the theme, Quasar's color="primary"
    automatically uses the theme's accent color. No need to strip classes.
    """
    button = ui.button(text, icon=icon, on_click=on_click)
    variant_prop = _VARIANT_PROPS.get(variant, "flat")
    button.props(f"no-caps {variant_prop} {props}".strip())
    button.classes(f"app-btn {classes}".strip())
    return button


def neutralize_button_utilities(button: ui.button) -> ui.button:
    """No-op kept for backward compatibility.

    With ui.colors() properly set, bg-primary IS the correct color
    so there's nothing to neutralize.
    """
    return button
