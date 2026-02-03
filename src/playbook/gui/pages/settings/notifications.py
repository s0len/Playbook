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

if TYPE_CHECKING:
    from ...state.settings_state import SettingsFormState


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
            ui.label("Configure per-sport throttling to limit notifications").classes(
                "text-sm text-slate-600 dark:text-slate-400 mb-2"
            )

            throttle_data = state.get_value("settings.notifications.throttle", {}) or {}

            if throttle_data:
                with ui.column().classes("w-full gap-2"):
                    for sport_id, limit in throttle_data.items():
                        with ui.row().classes("w-full items-center gap-2"):
                            ui.label(sport_id).classes("flex-1 text-sm font-mono")
                            ui.input(value=str(limit)).classes("w-24").props('outlined dense type="number"')
                            ui.label("per day").classes("text-xs text-slate-500")
            else:
                ui.label("No rate limits configured").classes("text-sm text-slate-500 italic")

            with ui.row().classes("w-full mt-2"):
                ui.button("Add Rate Limit", icon="add").props("flat dense").classes("text-blue-600")

        # Mentions Configuration
        with settings_card(
            "Mentions",
            icon="alternate_email",
            description="Configure mentions for Discord notifications",
            collapsible=True,
            default_expanded=False,
        ):
            mentions_data = state.get_value("settings.notifications.mentions", {}) or {}

            if mentions_data:
                with ui.column().classes("w-full gap-2"):
                    for event_type, mention in mentions_data.items():
                        with ui.row().classes("w-full items-center gap-2"):
                            ui.label(event_type).classes("w-32 text-sm font-mono")
                            ui.input(value=mention, placeholder="@user or @role").classes("flex-1").props(
                                "outlined dense"
                            )
            else:
                ui.label("No mentions configured").classes("text-sm text-slate-500 italic")

            with ui.row().classes("w-full mt-2"):
                ui.button("Add Mention", icon="add").props("flat dense").classes("text-blue-600")

            # Help text
            with ui.expansion(text="Mention Format Help", icon="help").props("dense").classes("mt-2"):
                with ui.column().classes("gap-1 text-xs"):
                    ui.label("Discord user mention: <@USER_ID>").classes("text-slate-600 dark:text-slate-400")
                    ui.label("Discord role mention: <@&ROLE_ID>").classes("text-slate-600 dark:text-slate-400")
                    ui.label("Event types: new, upgrade, error").classes("text-slate-600 dark:text-slate-400")
