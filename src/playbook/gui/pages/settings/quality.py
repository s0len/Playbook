"""
Quality profile settings tab for the Settings page.

Handles quality scoring configuration for automatic upgrades.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ...components.settings import (
    settings_card,
    settings_input,
    settings_toggle,
)
from ...components.settings.key_value_editor import quality_score_editor

if TYPE_CHECKING:
    from ...state.settings_state import SettingsFormState


# Default resolution scores
RESOLUTION_PRESETS = {
    "2160p": 400,
    "1080p": 300,
    "720p": 200,
    "576p": 150,
    "480p": 100,
}

# Default source scores
SOURCE_PRESETS = {
    "bluray": 100,
    "webdl": 90,
    "webrip": 70,
    "hdtv": 50,
    "sdtv": 30,
    "dvdrip": 40,
}

# Common release groups
RELEASE_GROUP_PRESETS = {
    "mwr": 50,
    "verum": 40,
    "smcgill1969": 30,
}


def quality_tab(state: SettingsFormState) -> None:
    """Render the Quality Profile settings tab.

    Args:
        state: Settings form state
    """
    # Get current enabled state for conditional rendering
    quality_enabled = state.get_value("settings.quality_profile.enabled", False)

    with ui.column().classes("w-full gap-6"):
        # Enable Quality Profile Section
        with settings_card("Quality Profile", icon="tune", description="Enable automatic quality upgrades"):
            settings_toggle(
                state,
                "settings.quality_profile.enabled",
                "Enable Quality Upgrades",
                description="When enabled, files will be scored and higher-quality versions will replace existing ones",
                on_change=lambda v: ui.navigate.to("/config"),  # Refresh to update disabled states
            )

            with ui.row().classes("w-full gap-4 mt-4"):
                settings_input(
                    state,
                    "settings.quality_profile.cutoff",
                    "Cutoff Score",
                    description="Stop upgrading when this score is reached (except PROPER/REPACK)",
                    input_type="number",
                    placeholder="e.g., 450",
                    disabled=not quality_enabled,
                    width="w-48",
                )
                settings_input(
                    state,
                    "settings.quality_profile.min_score",
                    "Minimum Score",
                    description="Reject files below this score",
                    input_type="number",
                    placeholder="e.g., 200",
                    disabled=not quality_enabled,
                    width="w-48",
                )

        # Resolution Scoring Section
        with settings_card(
            "Resolution Scores",
            icon="aspect_ratio",
            description="Points awarded for video resolution",
            collapsible=True,
            default_expanded=quality_enabled,
            disabled=not quality_enabled,
        ):
            quality_score_editor(
                state,
                "settings.quality_profile.scoring.resolution",
                "Resolution",
                description="Higher resolution = higher score",
                presets=RESOLUTION_PRESETS,
                disabled=not quality_enabled,
            )

        # Source Scoring Section
        with settings_card(
            "Source Scores",
            icon="source",
            description="Points awarded for media source type",
            collapsible=True,
            default_expanded=quality_enabled,
            disabled=not quality_enabled,
        ):
            quality_score_editor(
                state,
                "settings.quality_profile.scoring.source",
                "Source Type",
                description="Bluray and WEB-DL are typically higher quality than HDTV",
                presets=SOURCE_PRESETS,
                disabled=not quality_enabled,
            )

        # Release Group Scoring Section
        with settings_card(
            "Release Group Scores",
            icon="group",
            description="Bonus points for preferred release groups",
            collapsible=True,
            default_expanded=False,
            disabled=not quality_enabled,
        ):
            quality_score_editor(
                state,
                "settings.quality_profile.scoring.release_group",
                "Release Groups",
                description="Add groups you trust for higher quality releases",
                presets=RELEASE_GROUP_PRESETS,
                disabled=not quality_enabled,
            )

        # Bonus Scores Section
        with settings_card(
            "Bonus Scores",
            icon="star",
            description="Additional points for special releases",
            collapsible=True,
            default_expanded=False,
            disabled=not quality_enabled,
        ):
            with ui.row().classes("w-full gap-4"):
                settings_input(
                    state,
                    "settings.quality_profile.scoring.proper_bonus",
                    "PROPER Bonus",
                    description="Bonus for PROPER releases",
                    input_type="number",
                    placeholder="50",
                    disabled=not quality_enabled,
                    width="w-32",
                )
                settings_input(
                    state,
                    "settings.quality_profile.scoring.repack_bonus",
                    "REPACK Bonus",
                    description="Bonus for REPACK releases",
                    input_type="number",
                    placeholder="50",
                    disabled=not quality_enabled,
                    width="w-32",
                )
                settings_input(
                    state,
                    "settings.quality_profile.scoring.hdr_bonus",
                    "HDR Bonus",
                    description="Bonus for HDR content",
                    input_type="number",
                    placeholder="25",
                    disabled=not quality_enabled,
                    width="w-32",
                )

        # Score Calculator (interactive preview)
        if quality_enabled:
            with settings_card("Score Calculator", icon="calculate", description="Preview how files would be scored"):
                with ui.row().classes("w-full items-center gap-2 mb-2"):
                    test_input = (
                        ui.input(
                            placeholder="Enter a filename to test",
                        )
                        .classes("flex-1")
                        .props('outlined dense label="Test Filename"')
                    )
                    ui.button("Calculate", icon="calculate", on_click=lambda: _calculate_score(state, test_input.value))

                ui.label("").bind_text_from(state, "")  # Placeholder for result


def _calculate_score(state: SettingsFormState, filename: str) -> None:
    """Calculate and display quality score for a test filename."""
    if not filename:
        ui.notify("Enter a filename to test", type="warning")
        return

    try:
        from playbook.config import QualityProfile, QualityScoring
        from playbook.quality import extract_quality
        from playbook.quality_scorer import compute_quality_score

        # Build profile from current state
        scoring_data = state.get_value("settings.quality_profile.scoring", {}) or {}
        scoring = QualityScoring(
            resolution=scoring_data.get("resolution", {}),
            source=scoring_data.get("source", {}),
            release_group=scoring_data.get("release_group", {}),
            proper_bonus=int(scoring_data.get("proper_bonus", 50) or 50),
            repack_bonus=int(scoring_data.get("repack_bonus", 50) or 50),
            hdr_bonus=int(scoring_data.get("hdr_bonus", 25) or 25),
        )
        profile = QualityProfile(enabled=True, scoring=scoring)

        # Extract and score
        quality_info = extract_quality(filename)
        score = compute_quality_score(quality_info, profile)

        # Format result
        parts = []
        if quality_info.resolution:
            parts.append(f"{quality_info.resolution}: {score.resolution_score}")
        if quality_info.source:
            parts.append(f"{quality_info.source}: {score.source_score}")
        if quality_info.release_group and score.release_group_score:
            parts.append(f"{quality_info.release_group}: {score.release_group_score}")
        if score.proper_bonus:
            parts.append(f"PROPER: +{score.proper_bonus}")
        if score.repack_bonus:
            parts.append(f"REPACK: +{score.repack_bonus}")
        if score.hdr_bonus:
            parts.append(f"HDR: +{score.hdr_bonus}")

        breakdown = ", ".join(parts) if parts else "No quality attributes detected"
        ui.notify(f"Score: {score.total} ({breakdown})", type="positive", timeout=10000)

    except Exception as e:
        ui.notify(f"Error calculating score: {e}", type="negative")
