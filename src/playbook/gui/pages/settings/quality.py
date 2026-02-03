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
    from ...settings_state.settings_state import SettingsFormState


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

# Frame rate scores (critical for sports)
FRAME_RATE_PRESETS = {
    "60": 100,
    "50": 75,
    "30": 25,
    "25": 0,
    "24": 0,
}

# Codec scores
CODEC_PRESETS = {
    "x265": 25,
    "h265": 25,
    "x264": 0,
    "h264": 0,
    "xvid": -25,
    "divx": -25,
}

# Bit depth scores
BIT_DEPTH_PRESETS = {
    "10": 25,
    "8": 0,
}

# Audio scores
AUDIO_PRESETS = {
    "atmos": 40,
    "truehd": 35,
    "dtshd": 30,
    "ddp51": 25,
    "dd51": 20,
    "eac3": 20,
    "dts": 15,
    "ac3": 10,
    "aac51": 15,
    "aac": 0,
    "mp3": -10,
}

# Broadcaster scores (official sources preferred)
BROADCASTER_PRESETS = {
    "f1tv": 50,
    "skyf1uhd": 50,
    "skyf1": 40,
    "sky": 30,
    "espn": 30,
    "tnt": 25,
    "nbc": 20,
    "cbs": 20,
    "fox": 20,
    "dazn": 25,
    "stan": 20,
}

# Common release groups
RELEASE_GROUP_PRESETS = {
    "mwr": 50,
    "verum": 40,
    "smcgill1969": 30,
    "darksport": 30,
    "f1carreras": 25,
    "gametime": 20,
    "dnu": 20,
}


def quality_tab(state: SettingsFormState) -> None:
    """Render the Quality Profile settings tab.

    Args:
        state: Settings form state
    """
    # Container for dynamic content that depends on enabled state
    container = ui.column().classes("w-full gap-6")

    def render_quality_content() -> None:
        """Render the quality tab content."""
        container.clear()
        quality_enabled = state.get_value("settings.quality_profile.enabled", False)

        with container:
            # Enable Quality Profile Section
            with settings_card("Quality Profile", icon="tune", description="Enable automatic quality upgrades"):

                def on_enable_change(enabled: bool) -> None:
                    # Re-render the tab to update disabled states
                    render_quality_content()

                settings_toggle(
                    state,
                    "settings.quality_profile.enabled",
                    "Enable Quality Upgrades",
                    description="When enabled, files will be scored and higher-quality versions will replace existing ones",
                    on_change=on_enable_change,
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

            # Frame Rate Scoring Section (critical for sports!)
            with settings_card(
                "Frame Rate Scores",
                icon="speed",
                description="Higher frame rate = smoother sports action (critical for fast motion)",
                collapsible=True,
                default_expanded=quality_enabled,
                disabled=not quality_enabled,
            ):
                quality_score_editor(
                    state,
                    "settings.quality_profile.scoring.frame_rate",
                    "Frame Rate",
                    description="60fps is ideal for sports, 50fps is common in Europe",
                    presets=FRAME_RATE_PRESETS,
                    disabled=not quality_enabled,
                )

            # Codec Scoring Section
            with settings_card(
                "Codec Scores",
                icon="movie",
                description="Points awarded for video codec efficiency",
                collapsible=True,
                default_expanded=False,
                disabled=not quality_enabled,
            ):
                quality_score_editor(
                    state,
                    "settings.quality_profile.scoring.codec",
                    "Codec",
                    description="x265/H.265 is more efficient than x264/H.264",
                    presets=CODEC_PRESETS,
                    disabled=not quality_enabled,
                )

            # Bit Depth Scoring Section
            with settings_card(
                "Bit Depth Scores",
                icon="gradient",
                description="10-bit has better color gradients and less banding",
                collapsible=True,
                default_expanded=False,
                disabled=not quality_enabled,
            ):
                quality_score_editor(
                    state,
                    "settings.quality_profile.scoring.bit_depth",
                    "Bit Depth",
                    description="10-bit encoding preserves more color detail",
                    presets=BIT_DEPTH_PRESETS,
                    disabled=not quality_enabled,
                )

            # Audio Scoring Section
            with settings_card(
                "Audio Scores",
                icon="surround_sound",
                description="Points awarded for audio format quality",
                collapsible=True,
                default_expanded=False,
                disabled=not quality_enabled,
            ):
                quality_score_editor(
                    state,
                    "settings.quality_profile.scoring.audio",
                    "Audio Format",
                    description="Surround sound formats (5.1) score higher than stereo",
                    presets=AUDIO_PRESETS,
                    disabled=not quality_enabled,
                )

            # Broadcaster Scoring Section
            with settings_card(
                "Broadcaster Scores",
                icon="tv",
                description="Points for official broadcast sources (F1TV, Sky, ESPN, etc.)",
                collapsible=True,
                default_expanded=False,
                disabled=not quality_enabled,
            ):
                quality_score_editor(
                    state,
                    "settings.quality_profile.scoring.broadcaster",
                    "Broadcaster",
                    description="Official sources like F1TV and Sky typically have better quality",
                    presets=BROADCASTER_PRESETS,
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
                        placeholder="50",
                        disabled=not quality_enabled,
                        width="w-32",
                    )

            # Score Calculator (interactive preview)
            if quality_enabled:
                with settings_card(
                    "Score Calculator", icon="calculate", description="Preview how files would be scored"
                ):
                    with ui.row().classes("w-full items-center gap-2 mb-2"):
                        test_input = (
                            ui.input(
                                placeholder="Enter a filename to test",
                            )
                            .classes("flex-1")
                            .props('outlined dense label="Test Filename"')
                        )
                        ui.button(
                            "Calculate",
                            icon="calculate",
                            on_click=lambda: _calculate_score(state, test_input.value),
                        )

    # Initial render
    render_quality_content()


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
            frame_rate=scoring_data.get("frame_rate", {}),
            codec=scoring_data.get("codec", {}),
            bit_depth=scoring_data.get("bit_depth", {}),
            audio=scoring_data.get("audio", {}),
            broadcaster=scoring_data.get("broadcaster", {}),
            proper_bonus=int(scoring_data.get("proper_bonus", 50) or 50),
            repack_bonus=int(scoring_data.get("repack_bonus", 50) or 50),
            hdr_bonus=int(scoring_data.get("hdr_bonus", 50) or 50),
        )
        profile = QualityProfile(enabled=True, scoring=scoring)

        # Extract and score
        quality_info = extract_quality(filename)
        score = compute_quality_score(quality_info, profile)

        # Format result
        parts = []
        if quality_info.resolution:
            parts.append(f"{quality_info.resolution}: {score.resolution_score}")
        if quality_info.frame_rate and score.frame_rate_score:
            parts.append(f"{quality_info.frame_rate}fps: {score.frame_rate_score}")
        if quality_info.source:
            parts.append(f"{quality_info.source}: {score.source_score}")
        if quality_info.codec and score.codec_score:
            parts.append(f"{quality_info.codec}: {score.codec_score}")
        if quality_info.bit_depth and score.bit_depth_score:
            parts.append(f"{quality_info.bit_depth}bit: {score.bit_depth_score}")
        if quality_info.audio and score.audio_score:
            parts.append(f"{quality_info.audio}: {score.audio_score}")
        if quality_info.broadcaster and score.broadcaster_score:
            parts.append(f"{quality_info.broadcaster}: {score.broadcaster_score}")
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
