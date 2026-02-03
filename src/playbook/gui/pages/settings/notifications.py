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


def _render_throttle_editor(state: SettingsFormState) -> None:
    """Render the throttle/rate limit editor."""
    container = ui.column().classes("w-full gap-4")

    def refresh() -> None:
        container.clear()
        with container:
            _render_throttle_content()

    def _render_throttle_content() -> None:
        ui.label("Configure per-sport throttling to limit notifications").classes(
            "text-sm text-slate-600 dark:text-slate-400"
        )

        throttle_data = state.get_value("settings.notifications.throttle", {}) or {}

        if throttle_data:
            with ui.column().classes("w-full gap-2"):
                for sport_id in list(throttle_data.keys()):
                    limit = throttle_data[sport_id]
                    with ui.row().classes("w-full items-center gap-2"):
                        ui.label(sport_id).classes("flex-1 text-sm font-mono")

                        def on_limit_change(e, sid=sport_id) -> None:
                            try:
                                data = state.get_value("settings.notifications.throttle", {}) or {}
                                data[sid] = int(e.value) if e.value else 0
                                state.set_value("settings.notifications.throttle", data)
                            except ValueError:
                                pass

                        ui.input(value=str(limit), on_change=on_limit_change).classes("w-24").props(
                            'outlined dense type="number"'
                        )
                        ui.label("per day").classes("text-xs text-slate-500")

                        def on_delete(sid=sport_id) -> None:
                            data = state.get_value("settings.notifications.throttle", {}) or {}
                            if sid in data:
                                del data[sid]
                                state.set_value("settings.notifications.throttle", data)
                            refresh()

                        ui.button(icon="delete", on_click=on_delete).props("flat dense color=negative")
        else:
            ui.label("No rate limits configured").classes("text-sm text-slate-500 italic")

        # Add new rate limit
        with ui.row().classes("w-full items-end gap-2 mt-2"):
            new_sport = ui.input(label="Sport ID", placeholder="formula1").classes("flex-1").props("outlined dense")
            new_limit = ui.input(label="Limit", value="10").classes("w-24").props('outlined dense type="number"')

            def add_throttle() -> None:
                sport_id = new_sport.value.strip() if new_sport.value else ""
                if not sport_id:
                    ui.notify("Please enter a sport ID", type="warning")
                    return
                try:
                    limit_val = int(new_limit.value) if new_limit.value else 10
                except ValueError:
                    limit_val = 10

                data = state.get_value("settings.notifications.throttle", {}) or {}
                data[sport_id] = limit_val
                state.set_value("settings.notifications.throttle", data)
                refresh()

            ui.button("Add", icon="add", on_click=add_throttle).props("flat dense").classes("text-blue-600")

    with container:
        _render_throttle_content()


def _render_mentions_editor(state: SettingsFormState) -> None:
    """Render the mentions editor."""
    container = ui.column().classes("w-full gap-4")

    def refresh() -> None:
        container.clear()
        with container:
            _render_mentions_content()

    def _render_mentions_content() -> None:
        mentions_data = state.get_value("settings.notifications.mentions", {}) or {}

        if mentions_data:
            with ui.column().classes("w-full gap-3"):
                for sport_id in list(mentions_data.keys()):
                    mention = mentions_data[sport_id]
                    with ui.row().classes("w-full items-center gap-2"):
                        ui.label(sport_id).classes("w-40 shrink-0 text-sm font-mono truncate")

                        def on_mention_change(e, sid=sport_id) -> None:
                            data = state.get_value("settings.notifications.mentions", {}) or {}
                            data[sid] = e.value or ""
                            state.set_value("settings.notifications.mentions", data)

                        ui.input(value=mention, placeholder="<@&ROLE_ID>", on_change=on_mention_change).classes(
                            "flex-1"
                        ).props("outlined dense")

                        def on_delete(sid=sport_id) -> None:
                            data = state.get_value("settings.notifications.mentions", {}) or {}
                            if sid in data:
                                del data[sid]
                                state.set_value("settings.notifications.mentions", data)
                            refresh()

                        ui.button(icon="delete", on_click=on_delete).props("flat dense color=negative")
        else:
            ui.label("No mentions configured").classes("text-sm text-slate-500 italic")

        # Add new mention
        with ui.row().classes("w-full items-end gap-2 mt-2"):
            new_sport = ui.input(label="Sport ID", placeholder="formula1").classes("w-40").props("outlined dense")
            new_mention = ui.input(label="Mention", placeholder="<@&ROLE_ID>").classes("flex-1").props("outlined dense")

            def add_mention() -> None:
                sport_id = new_sport.value.strip() if new_sport.value else ""
                mention_val = new_mention.value.strip() if new_mention.value else ""
                if not sport_id:
                    ui.notify("Please enter a sport ID", type="warning")
                    return
                if not mention_val:
                    ui.notify("Please enter a mention", type="warning")
                    return

                data = state.get_value("settings.notifications.mentions", {}) or {}
                data[sport_id] = mention_val
                state.set_value("settings.notifications.mentions", data)
                refresh()

            ui.button("Add", icon="add", on_click=add_mention).props("flat dense").classes("text-blue-600")

    with container:
        _render_mentions_content()
