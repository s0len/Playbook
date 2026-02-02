"""
Status chip components for the Playbook GUI.
"""

from __future__ import annotations

from typing import Literal

from nicegui import ui

StatusType = Literal["matched", "missing", "error", "enabled", "disabled"]


def status_chip(
    status: StatusType,
    *,
    text: str | None = None,
    show_icon: bool = True,
) -> ui.element:
    """Create a color-coded status chip.

    Args:
        status: The status type
        text: Custom text (defaults to status name)
        show_icon: Whether to show status icon

    Returns:
        The chip container element
    """
    # Status configurations
    config = {
        "matched": {
            "icon": "check_circle",
            "text": "Matched",
            "class": "status-chip status-chip-matched",
        },
        "missing": {
            "icon": "radio_button_unchecked",
            "text": "Missing",
            "class": "status-chip status-chip-missing",
        },
        "error": {
            "icon": "error",
            "text": "Error",
            "class": "status-chip status-chip-error",
        },
        "enabled": {
            "icon": "check_circle",
            "text": "Enabled",
            "class": "status-chip status-chip-matched",
        },
        "disabled": {
            "icon": "cancel",
            "text": "Disabled",
            "class": "status-chip status-chip-missing",
        },
    }

    conf = config.get(status, config["missing"])
    display_text = text or conf["text"]

    with ui.element("div").classes(conf["class"]) as container:
        if show_icon:
            ui.icon(conf["icon"]).classes("text-sm")
        ui.label(display_text)

    return container


def status_icon(
    status: StatusType,
    *,
    size: str = "text-lg",
) -> ui.icon:
    """Create a status icon without text.

    Args:
        status: The status type
        size: Icon size class

    Returns:
        The icon element
    """
    icons = {
        "matched": ("check_circle", "text-green-600 dark:text-green-400"),
        "missing": ("radio_button_unchecked", "text-slate-400 dark:text-slate-500"),
        "error": ("error", "text-red-600 dark:text-red-400"),
        "enabled": ("check_circle", "text-green-600 dark:text-green-400"),
        "disabled": ("cancel", "text-slate-400 dark:text-slate-500"),
    }

    icon_name, color_class = icons.get(status, icons["missing"])
    return ui.icon(icon_name).classes(f"{size} {color_class}")


def link_mode_chip(mode: str) -> ui.element:
    """Create a chip showing the link mode.

    Args:
        mode: Link mode (hardlink, copy, symlink)

    Returns:
        The chip element
    """
    icons = {
        "hardlink": "link",
        "copy": "file_copy",
        "symlink": "shortcut",
    }

    icon = icons.get(mode, "link")

    with ui.element("div").classes("status-chip status-chip-missing") as container:
        ui.icon(icon).classes("text-sm")
        ui.label(mode.capitalize())

    return container
