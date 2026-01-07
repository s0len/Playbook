from __future__ import annotations

import datetime as dt
from pathlib import Path
from unittest.mock import Mock

import pytest

from playbook.destination_builder import (
    build_destination,
    build_match_context,
    format_relative_destination,
)


class TestBuildMatchContext:
    """Test build_match_context function."""

    def test_builds_context_with_all_fields(self) -> None:
        """Test that build_match_context populates all template variables."""
        # Create mock objects
        sport = Mock()
        sport.id = "nba"
        sport.name = "NBA Basketball"

        show = Mock()
        show.key = "nba-2023"
        show.title = "NBA 2023-24"

        season = Mock()
        season.key = "season-1"
        season.title = "Regular Season"
        season.index = 1
        season.display_number = 1
        season.round_number = None
        season.sort_title = "Regular Season"

        episode = Mock()
        episode.title = "Lakers vs Warriors"
        episode.index = 42
        episode.display_number = 42
        episode.summary = "Exciting game between rivals"
        episode.originally_available = dt.date(2024, 1, 15)

        runtime = Mock()
        runtime.sport = sport
        runtime.show = show

        source_path = Path("/source/NBA/game_42.mkv")
        source_dir = Path("/source")
        groups = {"game_id": "42", "team1": "Lakers", "team2": "Warriors"}

        # Build context
        context = build_match_context(
            runtime=runtime,
            source_path=source_path,
            season=season,
            episode=episode,
            groups=groups,
            source_dir=source_dir,
        )

        # Verify all expected fields
        assert context["sport_id"] == "nba"
        assert context["sport_name"] == "NBA Basketball"
        assert context["show_id"] == "nba-2023"
        assert context["show_key"] == "nba-2023"
        assert context["show_title"] == "NBA 2023-24"
        assert context["season_key"] == "season-1"
        assert context["season_title"] == "Regular Season"
        assert context["season_index"] == 1
        assert context["season_number"] == 1
        assert context["season_round"] == 1
        assert context["season_sort_title"] == "Regular Season"
        assert context["season_slug"] == "regular-season"
        assert context["episode_title"] == "Lakers vs Warriors"
        assert context["episode_index"] == 42
        assert context["episode_number"] == 42
        assert context["episode_summary"] == "Exciting game between rivals"
        assert context["episode_slug"] == "lakers-vs-warriors"
        assert context["episode_originally_available"] == "2024-01-15"
        assert context["originally_available"] == "2024-01-15"
        assert context["extension"] == "mkv"
        assert context["suffix"] == ".mkv"
        assert context["source_filename"] == "game_42.mkv"
        assert context["source_stem"] == "game_42"
        assert context["relative_source"] == "NBA/game_42.mkv"

        # Verify regex groups are included
        assert context["game_id"] == "42"
        assert context["team1"] == "Lakers"
        assert context["team2"] == "Warriors"

    def test_extracts_year_from_show_title(self) -> None:
        """Test that year is extracted from show title when present."""
        sport = Mock()
        sport.id = "nba"
        sport.name = "NBA"

        show = Mock()
        show.key = "nba-2023"
        show.title = "NBA 2023-24 Season"

        season = Mock()
        season.key = "s1"
        season.title = "Regular"
        season.index = 1
        season.display_number = 1
        season.round_number = None
        season.sort_title = None

        episode = Mock()
        episode.title = "Game 1"
        episode.index = 1
        episode.display_number = 1
        episode.summary = None
        episode.originally_available = None

        runtime = Mock()
        runtime.sport = sport
        runtime.show = show

        source_path = Path("/source/game.mkv")
        source_dir = Path("/source")

        context = build_match_context(
            runtime=runtime,
            source_path=source_path,
            season=season,
            episode=episode,
            groups={},
            source_dir=source_dir,
        )

        assert context["season_year"] == 2023

    def test_no_year_when_not_in_title(self) -> None:
        """Test that season_year is not set when no year in show title."""
        sport = Mock()
        sport.id = "nba"
        sport.name = "NBA"

        show = Mock()
        show.key = "nba"
        show.title = "NBA Basketball"

        season = Mock()
        season.key = "s1"
        season.title = "Regular"
        season.index = 1
        season.display_number = 1
        season.round_number = None
        season.sort_title = None

        episode = Mock()
        episode.title = "Game 1"
        episode.index = 1
        episode.display_number = 1
        episode.summary = None
        episode.originally_available = None

        runtime = Mock()
        runtime.sport = sport
        runtime.show = show

        source_path = Path("/source/game.mkv")
        source_dir = Path("/source")

        context = build_match_context(
            runtime=runtime,
            source_path=source_path,
            season=season,
            episode=episode,
            groups={},
            source_dir=source_dir,
        )

        assert "season_year" not in context

    def test_handles_none_values_in_optional_fields(self) -> None:
        """Test that None values in optional fields are handled gracefully."""
        sport = Mock()
        sport.id = "nba"
        sport.name = "NBA"

        show = Mock()
        show.key = "nba"
        show.title = "NBA"

        season = Mock()
        season.key = "s1"
        season.title = "Regular"
        season.index = 1
        season.display_number = None
        season.round_number = None
        season.sort_title = None

        episode = Mock()
        episode.title = "Game 1"
        episode.index = 1
        episode.display_number = None
        episode.summary = None
        episode.originally_available = None

        runtime = Mock()
        runtime.sport = sport
        runtime.show = show

        source_path = Path("/source/game.mkv")
        source_dir = Path("/source")

        context = build_match_context(
            runtime=runtime,
            source_path=source_path,
            season=season,
            episode=episode,
            groups={},
            source_dir=source_dir,
        )

        # When display_number is None, falls back to index
        assert context["season_number"] == 1
        assert context["season_round"] == 1
        assert context["episode_number"] == 1
        assert context["episode_summary"] == ""
        assert context["episode_originally_available"] == ""
        assert context["originally_available"] == ""
        assert context["season_sort_title"] == "Regular"

    def test_uses_round_number_when_available(self) -> None:
        """Test that season_round prefers round_number over display_number."""
        sport = Mock()
        sport.id = "nba"
        sport.name = "NBA"

        show = Mock()
        show.key = "nba"
        show.title = "NBA"

        season = Mock()
        season.key = "playoffs"
        season.title = "Playoffs"
        season.index = 2
        season.display_number = 2
        season.round_number = 10
        season.sort_title = None

        episode = Mock()
        episode.title = "Game 1"
        episode.index = 1
        episode.display_number = 1
        episode.summary = None
        episode.originally_available = None

        runtime = Mock()
        runtime.sport = sport
        runtime.show = show

        source_path = Path("/source/game.mkv")
        source_dir = Path("/source")

        context = build_match_context(
            runtime=runtime,
            source_path=source_path,
            season=season,
            episode=episode,
            groups={},
            source_dir=source_dir,
        )

        # season_round should prefer round_number
        assert context["season_round"] == 10
        # season_number should prefer display_number
        assert context["season_number"] == 2

    def test_handles_extension_without_dot(self) -> None:
        """Test that extension field strips the leading dot."""
        sport = Mock()
        sport.id = "nba"
        sport.name = "NBA"

        show = Mock()
        show.key = "nba"
        show.title = "NBA"

        season = Mock()
        season.key = "s1"
        season.title = "Regular"
        season.index = 1
        season.display_number = 1
        season.round_number = None
        season.sort_title = None

        episode = Mock()
        episode.title = "Game 1"
        episode.index = 1
        episode.display_number = 1
        episode.summary = None
        episode.originally_available = None

        runtime = Mock()
        runtime.sport = sport
        runtime.show = show

        source_path = Path("/source/game.mp4")
        source_dir = Path("/source")

        context = build_match_context(
            runtime=runtime,
            source_path=source_path,
            season=season,
            episode=episode,
            groups={},
            source_dir=source_dir,
        )

        assert context["extension"] == "mp4"
        assert context["suffix"] == ".mp4"

    def test_regex_groups_override_defaults(self) -> None:
        """Test that regex capture groups are merged into context."""
        sport = Mock()
        sport.id = "nba"
        sport.name = "NBA"

        show = Mock()
        show.key = "nba"
        show.title = "NBA"

        season = Mock()
        season.key = "s1"
        season.title = "Regular"
        season.index = 1
        season.display_number = 1
        season.round_number = None
        season.sort_title = None

        episode = Mock()
        episode.title = "Game 1"
        episode.index = 1
        episode.display_number = 1
        episode.summary = None
        episode.originally_available = None

        runtime = Mock()
        runtime.sport = sport
        runtime.show = show

        source_path = Path("/source/game.mkv")
        source_dir = Path("/source")
        groups = {"custom_field": "custom_value", "another": "value"}

        context = build_match_context(
            runtime=runtime,
            source_path=source_path,
            season=season,
            episode=episode,
            groups=groups,
            source_dir=source_dir,
        )

        assert context["custom_field"] == "custom_value"
        assert context["another"] == "value"


class TestBuildDestination:
    """Test build_destination function."""

    def test_builds_destination_with_default_templates(self) -> None:
        """Test building destination path with default templates."""
        sport = Mock()
        sport.destination = Mock()
        sport.destination.root_template = None
        sport.destination.season_dir_template = None
        sport.destination.episode_template = None

        runtime = Mock()
        runtime.sport = sport

        pattern = Mock()
        pattern.config = Mock()
        pattern.config.destination_root_template = None
        pattern.config.season_dir_template = None
        pattern.config.filename_template = None

        settings = Mock()
        settings.destination_dir = Path("/dest")
        settings.default_destination = Mock()
        settings.default_destination.root_template = "{show_title}"
        settings.default_destination.season_dir_template = "Season {season_number:02d}"
        settings.default_destination.episode_template = "S{season_number:02d}E{episode_number:02d}.{extension}"

        context = {
            "show_title": "NBA 2023",
            "season_number": 1,
            "episode_number": 5,
            "extension": "mkv",
        }

        destination = build_destination(
            runtime=runtime,
            pattern=pattern,
            context=context,
            settings=settings,
        )

        assert destination == Path("/dest/NBA 2023/Season 01/S01E05.mkv")

    def test_pattern_templates_override_sport_templates(self) -> None:
        """Test that pattern-level templates override sport-level templates."""
        sport = Mock()
        sport.destination = Mock()
        sport.destination.root_template = "{sport_id}"
        sport.destination.season_dir_template = "{season_title}"
        sport.destination.episode_template = "{episode_title}.{extension}"

        runtime = Mock()
        runtime.sport = sport

        pattern = Mock()
        pattern.config = Mock()
        pattern.config.destination_root_template = "{show_title}"
        pattern.config.season_dir_template = "Season {season_number}"
        pattern.config.filename_template = "Episode {episode_number}.{extension}"

        settings = Mock()
        settings.destination_dir = Path("/dest")
        settings.default_destination = Mock()
        settings.default_destination.root_template = "default_root"
        settings.default_destination.season_dir_template = "default_season"
        settings.default_destination.episode_template = "default_episode"

        context = {
            "sport_id": "nba",
            "show_title": "NBA 2023",
            "season_title": "Regular",
            "season_number": 1,
            "episode_title": "Game 1",
            "episode_number": 5,
            "extension": "mkv",
        }

        destination = build_destination(
            runtime=runtime,
            pattern=pattern,
            context=context,
            settings=settings,
        )

        # Should use pattern templates, not sport or default
        assert destination == Path("/dest/NBA 2023/Season 1/Episode 5.mkv")

    def test_sport_templates_override_default_templates(self) -> None:
        """Test that sport-level templates override default templates."""
        sport = Mock()
        sport.destination = Mock()
        sport.destination.root_template = "{sport_name}"
        sport.destination.season_dir_template = "{season_title}"
        sport.destination.episode_template = "{episode_title}.{extension}"

        runtime = Mock()
        runtime.sport = sport

        pattern = Mock()
        pattern.config = Mock()
        pattern.config.destination_root_template = None
        pattern.config.season_dir_template = None
        pattern.config.filename_template = None

        settings = Mock()
        settings.destination_dir = Path("/dest")
        settings.default_destination = Mock()
        settings.default_destination.root_template = "default_root"
        settings.default_destination.season_dir_template = "default_season"
        settings.default_destination.episode_template = "default_episode"

        context = {
            "sport_name": "Basketball",
            "season_title": "Regular",
            "episode_title": "Game 1",
            "extension": "mkv",
        }

        destination = build_destination(
            runtime=runtime,
            pattern=pattern,
            context=context,
            settings=settings,
        )

        # Should use sport templates, not default
        assert destination == Path("/dest/Basketball/Regular/Game 1.mkv")

    def test_sanitizes_path_components(self) -> None:
        """Test that path components are sanitized (special chars removed)."""
        sport = Mock()
        sport.destination = Mock()
        sport.destination.root_template = None
        sport.destination.season_dir_template = None
        sport.destination.episode_template = None

        runtime = Mock()
        runtime.sport = sport

        pattern = Mock()
        pattern.config = Mock()
        pattern.config.destination_root_template = None
        pattern.config.season_dir_template = None
        pattern.config.filename_template = None

        settings = Mock()
        settings.destination_dir = Path("/dest")
        settings.default_destination = Mock()
        settings.default_destination.root_template = "{show_title}"
        settings.default_destination.season_dir_template = "{season_title}"
        settings.default_destination.episode_template = "{episode_title}.{extension}"

        # Include characters that should be sanitized
        context = {
            "show_title": "NBA: 2023/24",
            "season_title": "Regular Season #1",
            "episode_title": "Lakers vs. Warriors (Game 5)",
            "extension": "mkv",
        }

        destination = build_destination(
            runtime=runtime,
            pattern=pattern,
            context=context,
            settings=settings,
        )

        # Sanitization should have removed/replaced special characters
        # The exact sanitization behavior depends on sanitize_component implementation
        # but we can verify the path is valid and doesn't contain problematic chars
        assert destination.is_relative_to(settings.destination_dir)
        # Path should not contain colons (except Windows drive letter)
        path_str = str(destination)
        if not path_str[1:2] == ":":  # Skip Windows drive letter
            assert ":" not in path_str

    def test_prevents_path_traversal(self) -> None:
        """Test that path traversal attempts raise ValueError."""
        sport = Mock()
        sport.destination = Mock()
        sport.destination.root_template = None
        sport.destination.season_dir_template = None
        sport.destination.episode_template = None

        runtime = Mock()
        runtime.sport = sport

        pattern = Mock()
        pattern.config = Mock()
        pattern.config.destination_root_template = None
        pattern.config.season_dir_template = None
        pattern.config.filename_template = None

        settings = Mock()
        settings.destination_dir = Path("/dest")
        settings.default_destination = Mock()
        settings.default_destination.root_template = "{show_title}"
        settings.default_destination.season_dir_template = "{season_title}"
        settings.default_destination.episode_template = "{episode_title}.{extension}"

        # Try to escape destination directory with ..
        context = {
            "show_title": "../../etc",
            "season_title": "passwd",
            "episode_title": "file",
            "extension": "txt",
        }

        with pytest.raises(ValueError, match="escapes destination_dir"):
            build_destination(
                runtime=runtime,
                pattern=pattern,
                context=context,
                settings=settings,
            )

    def test_creates_nested_directory_structure(self) -> None:
        """Test that destination path includes nested directory structure."""
        sport = Mock()
        sport.destination = Mock()
        sport.destination.root_template = None
        sport.destination.season_dir_template = None
        sport.destination.episode_template = None

        runtime = Mock()
        runtime.sport = sport

        pattern = Mock()
        pattern.config = Mock()
        pattern.config.destination_root_template = None
        pattern.config.season_dir_template = None
        pattern.config.filename_template = None

        settings = Mock()
        settings.destination_dir = Path("/media/sports")
        settings.default_destination = Mock()
        settings.default_destination.root_template = "{sport_name}/{show_title}"
        settings.default_destination.season_dir_template = "{season_title}"
        settings.default_destination.episode_template = "{episode_title}.{extension}"

        context = {
            "sport_name": "Basketball",
            "show_title": "NBA 2023-24",
            "season_title": "Regular Season",
            "episode_title": "Game 42",
            "extension": "mkv",
        }

        destination = build_destination(
            runtime=runtime,
            pattern=pattern,
            context=context,
            settings=settings,
        )

        expected = Path("/media/sports/Basketball/NBA 2023-24/Regular Season/Game 42.mkv")
        assert destination == expected


class TestFormatRelativeDestination:
    """Test format_relative_destination function."""

    def test_returns_relative_path_when_under_destination_dir(self) -> None:
        """Test that relative path is returned when destination is under destination_dir."""
        destination = Path("/dest/NBA/Season 01/Game 01.mkv")
        destination_dir = Path("/dest")

        result = format_relative_destination(destination, destination_dir)

        assert result == "NBA/Season 01/Game 01.mkv"

    def test_returns_absolute_path_when_outside_destination_dir(self) -> None:
        """Test that absolute path is returned when destination is outside destination_dir."""
        destination = Path("/other/NBA/Season 01/Game 01.mkv")
        destination_dir = Path("/dest")

        result = format_relative_destination(destination, destination_dir)

        # Should return absolute path since it's not under destination_dir
        assert result == str(destination)

    def test_handles_identical_paths(self) -> None:
        """Test handling when destination equals destination_dir."""
        destination = Path("/dest")
        destination_dir = Path("/dest")

        result = format_relative_destination(destination, destination_dir)

        assert result == "."

    def test_handles_nested_directories(self) -> None:
        """Test relative path with deeply nested directory structure."""
        destination = Path("/dest/sports/basketball/nba/2023/regular/game.mkv")
        destination_dir = Path("/dest")

        result = format_relative_destination(destination, destination_dir)

        assert result == "sports/basketball/nba/2023/regular/game.mkv"

    def test_preserves_filename_with_spaces(self) -> None:
        """Test that filenames with spaces are preserved correctly."""
        destination = Path("/dest/NBA 2023/Season 01/Game 01 - Lakers vs Warriors.mkv")
        destination_dir = Path("/dest")

        result = format_relative_destination(destination, destination_dir)

        assert result == "NBA 2023/Season 01/Game 01 - Lakers vs Warriors.mkv"

    def test_handles_windows_paths(self) -> None:
        """Test handling of Windows-style paths (if applicable)."""
        # This test uses forward slashes but tests the general behavior
        destination = Path("C:/dest/NBA/game.mkv")
        destination_dir = Path("C:/dest")

        result = format_relative_destination(destination, destination_dir)

        # Should return relative path
        assert "NBA" in result
        assert "game.mkv" in result

    def test_handles_trailing_slash_in_destination_dir(self) -> None:
        """Test that trailing slashes don't affect relative path calculation."""
        destination = Path("/dest/NBA/game.mkv")
        destination_dir = Path("/dest/")

        result = format_relative_destination(destination, destination_dir)

        assert result == "NBA/game.mkv"
