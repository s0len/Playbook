"""
Notifications settings tab for the Settings page.

Handles notification targets and delivery settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ...components.settings import (
    notification_target_editor,
    settings_card,
    settings_input,
    settings_toggle,
)
from ...state import gui_state

if TYPE_CHECKING:
    from ...settings_state.settings_state import SettingsFormState


def notifications_tab(state: SettingsFormState) -> None:
    """Render the Notifications settings tab.

    Args:
        state: Settings form state
    """
    with ui.column().classes("w-full gap-6"):
        # General Notification Settings
        with settings_card(
            "Notification Behavior", icon="notifications", description="Control how notifications are sent"
        ):
            with ui.row().classes("w-full gap-6"):
                with ui.column().classes("flex-1 gap-4"):
                    settings_toggle(
                        state,
                        "settings.notifications.summary_mode",
                        "Summary Mode",
                        description="Send one summary notification per scan instead of per-file",
                    )
                    settings_toggle(
                        state,
                        "settings.notifications.batch_daily",
                        "Batch Daily",
                        description="Batch notifications and send once daily",
                    )

                with ui.column().classes("flex-1 gap-4"):
                    # Flush time (only relevant when batch_daily is true)
                    batch_enabled = state.get_value("settings.notifications.batch_daily", False)
                    settings_input(
                        state,
                        "settings.notifications.flush_time",
                        "Daily Send Time",
                        description="Time to send daily batch (HH:MM format)",
                        placeholder="00:00",
                        disabled=not batch_enabled,
                    )

        # Notification Targets
        with settings_card("Notification Targets", icon="send", description="Configure where notifications are sent"):
            notification_target_editor(
                state,
                "settings.notifications.targets",
            )

        # Throttling Settings
        with settings_card(
            "Rate Limiting",
            icon="speed",
            description="Prevent notification flooding",
            collapsible=True,
            default_expanded=False,
        ):
            _render_throttle_editor(state)

        # Mentions Configuration
        with settings_card(
            "Mentions",
            icon="alternate_email",
            description="Configure mentions for Discord notifications",
            collapsible=True,
            default_expanded=False,
        ):
            _render_mentions_editor(state)

            # Help text
            with ui.expansion(text="Mention Format Help", icon="help").props("dense").classes("mt-2"):
                with ui.column().classes("gap-1 text-xs"):
                    ui.label("Discord user mention: <@USER_ID>").classes("text-slate-600 dark:text-slate-400")
                    ui.label("Discord role mention: <@&ROLE_ID>").classes("text-slate-600 dark:text-slate-400")
                    ui.label("Sport IDs: formula1, nhl, nba, ufc, etc.").classes("text-slate-600 dark:text-slate-400")


def _get_sport_ids() -> list[str]:
    """Get all enabled sport IDs from the running config."""
    if gui_state.config and gui_state.config.sports:
        return [s.id for s in gui_state.config.sports if s.enabled]
    return []


def _get_sport_name(sport_id: str) -> str:
    """Get the display name for a sport ID."""
    if gui_state.config and gui_state.config.sports:
        for s in gui_state.config.sports:
            if s.id == sport_id:
                return s.name
    return sport_id


def _render_throttle_editor(state: SettingsFormState) -> None:
    """Render the throttle/rate limit editor.

    Shows all configured sports pre-populated. Each sport gets a number
    input for its daily limit. Empty/0 means no limit for that sport.
    """
    throttle_data = state.get_value("settings.notifications.throttle", {}) or {}
    sport_ids = _get_sport_ids()

    ui.label("Configure per-sport daily notification limits").classes("text-sm text-slate-600 dark:text-slate-400")

    # Default limit row
    with ui.row().classes("w-full items-center gap-2"):
        ui.label("default").classes("flex-1 text-sm font-medium text-slate-300")

        def on_default_change(e) -> None:
            try:
                data = state.get_value("settings.notifications.throttle", {}) or {}
                data["default"] = int(e.value) if e.value else 0
                state.set_value("settings.notifications.throttle", data)
            except ValueError:
                pass

        default_val = throttle_data.get("default", 5)
        ui.input(value=str(default_val), on_change=on_default_change).classes("w-24").props(
            'outlined dense type="number"'
        )
        ui.label("per day").classes("text-xs text-slate-500")

    # One row per sport
    with ui.column().classes("w-full gap-2"):
        for sid in sport_ids:
            with ui.row().classes("w-full items-center gap-2"):
                ui.label(_get_sport_name(sid)).classes("flex-1 text-sm text-slate-400")

                def on_limit_change(e, sport_id=sid) -> None:
                    try:
                        data = state.get_value("settings.notifications.throttle", {}) or {}
                        val = int(e.value) if e.value else 0
                        if val > 0:
                            data[sport_id] = val
                        else:
                            data.pop(sport_id, None)
                        state.set_value("settings.notifications.throttle", data)
                    except ValueError:
                        pass

                current = throttle_data.get(sid, "")
                ui.input(
                    value=str(current) if current else "",
                    placeholder="default",
                    on_change=on_limit_change,
                ).classes("w-24").props('outlined dense type="number"')
                ui.label("per day").classes("text-xs text-slate-500")


def _render_mentions_editor(state: SettingsFormState) -> None:
    """Render the mentions editor.

    Shows all configured sports pre-populated. Each sport gets a text
    input for its Discord mention. Empty means no mention for that sport.
    """
    mentions_data = state.get_value("settings.notifications.mentions", {}) or {}
    sport_ids = _get_sport_ids()

    with ui.column().classes("w-full gap-3"):
        for sid in sport_ids:
            with ui.row().classes("w-full items-center gap-2"):
                ui.label(_get_sport_name(sid)).classes("w-40 shrink-0 text-sm text-slate-400 truncate")

                def on_mention_change(e, sport_id=sid) -> None:
                    data = state.get_value("settings.notifications.mentions", {}) or {}
                    val = (e.value or "").strip()
                    if val:
                        data[sport_id] = val
                    else:
                        data.pop(sport_id, None)
                    state.set_value("settings.notifications.mentions", data)

                current = mentions_data.get(sid, "")
                ui.input(
                    value=current,
                    placeholder="<@&ROLE_ID>",
                    on_change=on_mention_change,
                ).classes("flex-1").props("outlined dense")
