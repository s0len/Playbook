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
            with ui.column().classes("w-full gap-4"):
                settings_toggle(
                    state,
                    "settings.notifications.scan_summary",
                    "Scan Summary",
                    description="Send a summary notification after each scan with activity",
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


def _get_base_sport_id(sport_id: str) -> str:
    """Extract the base sport ID by stripping trailing year suffixes (e.g. ufc_2025 → ufc)."""
    import re

    return re.sub(r"_\d{4}$", "", sport_id)


def _get_sport_ids() -> list[str]:
    """Get unique base sport IDs from the running config.

    Variants like ufc_2024, ufc_2025 are collapsed to a single 'ufc' entry
    since the throttle engine already supports parent-prefix matching.
    """
    if gui_state.config and gui_state.config.sports:
        seen: set[str] = set()
        result: list[str] = []
        for s in gui_state.config.sports:
            base_id = _get_base_sport_id(s.id)
            if s.enabled and base_id not in seen:
                seen.add(base_id)
                result.append(base_id)
        return result
    return []


def _get_sport_name(sport_id: str) -> str:
    """Get the display name for a base sport ID.

    Strips trailing year from the name (e.g. 'UFC 2025' → 'UFC').
    """
    import re

    if gui_state.config and gui_state.config.sports:
        for s in gui_state.config.sports:
            if _get_base_sport_id(s.id) == sport_id:
                return re.sub(r"\s+\d{4}$", "", s.name)
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
