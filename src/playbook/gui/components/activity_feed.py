"""
Activity feed component for the Playbook GUI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ..state import gui_state

if TYPE_CHECKING:
    from playbook.notifications import NotificationEvent


def activity_feed(max_items: int = 20) -> ui.column:
    """Create an auto-updating activity feed.

    Args:
        max_items: Maximum number of items to display

    Returns:
        The container column element
    """
    feed_container = ui.column().classes("w-full gap-1")

    def refresh() -> None:
        feed_container.clear()
        events = list(gui_state.recent_events)[:max_items]
        with feed_container:
            if not events:
                ui.label("No recent activity").classes("text-gray-500 italic py-4 text-center")
            else:
                for event in events:
                    activity_item(event)

    ui.timer(2.0, refresh)
    refresh()

    return feed_container


def activity_item(event: NotificationEvent) -> None:
    """Render a single activity item.

    Args:
        event: The notification event to display
    """
    action_colors = {
        "hardlink": ("bg-green-100 text-green-800", "link"),
        "copy": ("bg-blue-100 text-blue-800", "content_copy"),
        "symlink": ("bg-purple-100 text-purple-800", "link"),
        "skipped": ("bg-yellow-100 text-yellow-800", "skip_next"),
        "error": ("bg-red-100 text-red-800", "error"),
        "dry-run": ("bg-gray-100 text-gray-800", "visibility"),
    }

    color_class, icon_name = action_colors.get(event.action, ("bg-gray-100 text-gray-800", "help"))

    with ui.row().classes(f"w-full items-center gap-2 p-2 rounded {color_class}"):
        ui.icon(icon_name).classes("text-lg")

        with ui.column().classes("flex-1 gap-0"):
            # Main info line
            with ui.row().classes("items-center gap-2"):
                ui.label(event.sport_name).classes("font-semibold text-sm")
                ui.label(f"S{event.season}").classes("text-xs opacity-70")
                ui.label(event.episode).classes("text-xs")

            # Destination path
            ui.label(event.destination).classes("text-xs opacity-70 truncate max-w-md")

        # Timestamp
        time_str = event.timestamp.strftime("%H:%M:%S")
        ui.label(time_str).classes("text-xs opacity-60")


def activity_summary() -> ui.row:
    """Create a summary row showing counts by action type."""
    with ui.row().classes("w-full gap-4 justify-center py-2") as row:
        events = list(gui_state.recent_events)

        action_counts: dict[str, int] = {}
        for event in events:
            action_counts[event.action] = action_counts.get(event.action, 0) + 1

        for action, count in sorted(action_counts.items()):
            with ui.row().classes("items-center gap-1"):
                ui.label(str(count)).classes("font-bold")
                ui.label(action).classes("text-sm opacity-70")

    return row
