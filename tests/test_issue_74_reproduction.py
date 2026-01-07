"""Reproduction tests for Issue #74 - NBA/NFL pattern matching regression.

These tests verify that specific NBA and NFL filenames from Issue #74 fail to match
the current pattern configurations. Once the patterns are fixed, these tests should
be updated to expect matches.

Current failing filenames:
- NBA RS 2025 Philadelphia 76ers vs Milwaukee Bucks 05 12 720pEN60fps FDSN.mkv
- NFL 2025 2026 Week 18 New Orleans Saints @ Atlanta Falcons 720p 60fps MKV H 264 EN.mkv
- NFL 2025 2026 Week 18 Dallas Cowboys @ New York Giants 04 01 1080pEN30fps.mkv

Test Status:
- NBA test: PASSES via structured matcher fallback (regex patterns don't match)
- NFL tests: FAIL (neither regex patterns nor structured matcher work)

The NFL failures demonstrate the bug. The NBA filename works via the structured
matcher fallback, but the regex patterns should be fixed for proper support.
"""

from __future__ import annotations

import datetime as dt
from copy import deepcopy

import pytest

from playbook.config import (
    DestinationTemplates,
    MetadataConfig,
    SportConfig,
    _build_pattern_config,
)
from playbook.matcher import compile_patterns, match_file_to_episode
from playbook.models import Episode, Season, Show
from playbook.pattern_templates import load_builtin_pattern_sets


def _build_sport_from_pattern_sets(sport_id: str, pattern_set_names: list[str]) -> SportConfig:
    """Build a SportConfig from one or more built-in pattern sets."""
    pattern_definitions: list[dict[str, object]] = []
    builtin_sets = load_builtin_pattern_sets()

    for set_name in pattern_set_names:
        if set_name not in builtin_sets:
            raise AssertionError(f"Unknown pattern_set '{set_name}'")
        pattern_definitions.extend(deepcopy(builtin_sets[set_name]))

    patterns = sorted(
        (_build_pattern_config(pattern) for pattern in pattern_definitions),
        key=lambda cfg: cfg.priority,
    )

    return SportConfig(
        id=sport_id,
        name=sport_id,
        enabled=True,
        metadata=MetadataConfig(url="https://example.com"),
        patterns=patterns,
        destination=DestinationTemplates(),
        source_globs=[],
        source_extensions=[".mkv", ".mp4", ".ts", ".m4v", ".avi"],
        link_mode="hardlink",
        allow_unmatched=False,
    )


def _build_nba_show() -> Show:
    """Build a minimal NBA show for testing Issue #74 filenames."""
    # Create seasons and episodes that should match the test filenames
    seasons = [
        Season(
            key="1",
            title="Week 1",
            summary=None,
            index=1,
            display_number=1,
            round_number=None,
            sort_title=None,
            episodes=[
                Episode(
                    title="Philadelphia 76ers at Milwaukee Bucks",
                    summary=None,
                    originally_available=dt.date(2025, 12, 5),
                    index=1,
                    metadata={},
                    display_number=None,
                    aliases=[
                        "Philadelphia 76ers vs Milwaukee Bucks",
                        "76ers at Bucks",
                        "76ers vs Bucks",
                    ],
                ),
            ],
            metadata={},
        ),
    ]

    return Show(
        key="nba_2025_26",
        title="NBA 2025-26",
        summary=None,
        seasons=seasons,
        metadata={},
    )


def _build_nfl_show() -> Show:
    """Build a minimal NFL show for testing Issue #74 filenames."""
    # Create Week 18 season with the test matchups
    seasons = [
        Season(
            key="18",
            title="Week 18",
            summary=None,
            index=18,
            display_number=18,
            round_number=None,
            sort_title=None,
            episodes=[
                Episode(
                    title="New Orleans Saints at Atlanta Falcons",
                    summary=None,
                    originally_available=dt.date(2026, 1, 4),
                    index=1,
                    metadata={},
                    display_number=None,
                    aliases=[
                        "New Orleans Saints vs Atlanta Falcons",
                        "Saints at Falcons",
                        "Saints vs Falcons",
                    ],
                ),
                Episode(
                    title="Dallas Cowboys at New York Giants",
                    summary=None,
                    originally_available=dt.date(2026, 1, 4),
                    index=2,
                    metadata={},
                    display_number=None,
                    aliases=[
                        "Dallas Cowboys vs New York Giants",
                        "Cowboys at Giants",
                        "Cowboys vs Giants",
                    ],
                ),
            ],
            metadata={},
        ),
    ]

    return Show(
        key="nfl_2025_26",
        title="NFL 2025-26",
        summary=None,
        seasons=seasons,
        metadata={},
    )


# Issue #74 failing filenames
ISSUE_74_NBA_FILENAMES = [
    "NBA RS 2025 Philadelphia 76ers vs Milwaukee Bucks 05 12 720pEN60fps FDSN.mkv",
]

ISSUE_74_NFL_FILENAMES = [
    "NFL 2025 2026 Week 18 New Orleans Saints @ Atlanta Falcons 720p 60fps MKV H 264 EN.mkv",
    "NFL 2025 2026 Week 18 Dallas Cowboys @ New York Giants 04 01 1080pEN30fps.mkv",
]


class TestIssue74NBAReproduction:
    """Reproduction tests for NBA pattern matching failures in Issue #74."""

    @pytest.fixture
    def nba_sport(self) -> SportConfig:
        """Create NBA sport config with current patterns."""
        return _build_sport_from_pattern_sets("nba_regular_season", ["nba"])

    @pytest.fixture
    def nba_show(self) -> Show:
        """Create NBA show with Issue #74 test data."""
        return _build_nba_show()

    @pytest.mark.parametrize("filename", ISSUE_74_NBA_FILENAMES)
    def test_nba_space_separated_filename_matches(
        self, nba_sport: SportConfig, nba_show: Show, filename: str
    ) -> None:
        """Verify NBA space-separated filenames match (Issue #74).

        Note: This test currently PASSES via the structured matcher fallback,
        even though the NBA regex patterns do not support:
        - Space-separated format (vs dot-separated)
        - RS (Regular Season) prefix
        - Trailing date format (DD MM)

        The structured matcher parses team names and matches against episode
        titles/aliases, providing a workaround. However, regex patterns should
        be fixed for explicit and reliable pattern support.
        """
        patterns = compile_patterns(nba_sport)
        diagnostics: list = []

        result = match_file_to_episode(
            filename,
            nba_sport,
            nba_show,
            patterns,
            diagnostics=diagnostics,
        )

        assert result is not None, (
            f"Issue #74: NBA filename '{filename}' did not match any pattern. "
            f"This is the bug we need to fix. Diagnostics: {diagnostics}"
        )


class TestIssue74NFLReproduction:
    """Reproduction tests for NFL pattern matching failures in Issue #74."""

    @pytest.fixture
    def nfl_sport(self) -> SportConfig:
        """Create NFL sport config with current patterns."""
        return _build_sport_from_pattern_sets("nfl_regular_season", ["nfl"])

    @pytest.fixture
    def nfl_show(self) -> Show:
        """Create NFL show with Issue #74 test data."""
        return _build_nfl_show()

    @pytest.mark.parametrize("filename", ISSUE_74_NFL_FILENAMES)
    def test_nfl_week_based_filename_matches(
        self, nfl_sport: SportConfig, nfl_show: Show, filename: str
    ) -> None:
        """Verify NFL week-based filenames match (Issue #74).

        This test currently FAILS because the NFL patterns do not support:
        - Space-separated format (vs dot-separated)
        - Week N format (vs date-based)
        - Season span format (YYYY YYYY)
        - @ symbol as separator (vs "vs" or "at")
        - Trailing date format (DD MM)

        After fix: These filenames should match successfully.
        """
        patterns = compile_patterns(nfl_sport)
        diagnostics: list = []

        result = match_file_to_episode(
            filename,
            nfl_sport,
            nfl_show,
            patterns,
            diagnostics=diagnostics,
        )

        assert result is not None, (
            f"Issue #74: NFL filename '{filename}' did not match any pattern. "
            f"This is the bug we need to fix. Diagnostics: {diagnostics}"
        )
