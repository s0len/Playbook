"""Semantic button helper to avoid framework default color bleed."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui


def app_button(
    text: str | None = None,
    *,
    icon: str | None = None,
    on_click: Callable[..., Any] | None = None,
    variant: str = "outline",
    classes: str = "",
    props: str = "",
) -> ui.button:
    """Create a button with semantic Playbook styling.

    This strips NiceGUI's default `bg-primary text-white` classes to prevent
    accidental Quasar primary styling from leaking into custom themes.
    """
    button = ui.button(text, icon=icon, on_click=on_click)
    # Force flat button mode so Quasar does not inject standard primary skin.
    button.props("flat")

    # Remove framework default color utility classes explicitly.
    def strip_framework_classes() -> None:
        button.classes(remove="bg-primary")
        button.classes(remove="text-white")

    strip_framework_classes()
    ui.timer(0.05, strip_framework_classes, once=True)
    button.props("no-caps")
    if props:
        button.props(props)
    button.classes(f"app-btn app-btn-{variant} {classes}".strip())
    return button
