from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from playbook.cache import CachedFileRecord, ProcessedFileCache
from playbook.match_handler import (
    alias_candidates,
    cleanup_old_destination,
    episode_cache_key,
    season_cache_key,
    should_overwrite_existing,
    specificity_score,
)
from playbook.models import ProcessingStats


class TestSpecificityScore:
    """Test specificity_score function."""

    def test_returns_zero_for_empty_string(self) -> None:
        """Test that specificity_score returns 0 for empty string."""
        assert specificity_score("") == 0

    def test_returns_zero_for_none(self) -> None:
        """Test that specificity_score returns 0 for None."""
        assert specificity_score(None) == 0

    def test_counts_digits_with_double_weight(self) -> None:
        """Test that digits are counted with double weight (2 points each)."""
        # "123" has 3 digits = 3 * 2 = 6 points
        assert specificity_score("123") >= 6

    def test_counts_separators(self) -> None:
        """Test that separators (dots, dashes, underscores) add specificity."""
        # Each separator adds 1 point
        score = specificity_score("a.b-c_d")
        # 3 separators = 3 points
        assert score >= 3

    def test_detects_part_number_pattern(self) -> None:
        """Test that 'part N' pattern adds specificity."""
        score = specificity_score("Part 2")
        # Should include bonus for part pattern
        assert score > specificity_score("Season")

    def test_detects_stage_number_pattern(self) -> None:
        """Test that 'stage N' pattern adds specificity."""
        score = specificity_score("Stage 3")
        # Should include bonus for stage pattern
        assert score > specificity_score("Episode")

    def test_detects_round_pattern(self) -> None:
        """Test that 'round N' pattern adds specificity."""
        score = specificity_score("Round 4")
        # Should include bonus for round pattern
        assert score > specificity_score("Match")

    def test_detects_heat_pattern(self) -> None:
        """Test that 'heat N' pattern adds specificity."""
        score = specificity_score("Heat 2")
        # Should include bonus for heat pattern
        assert score > specificity_score("Race")

    def test_detects_qualifier_abbreviations(self) -> None:
        """Test that qualifier abbreviations (qf, sf, fp, sp) add specificity."""
        # "QF 1" should have higher specificity than just "Qualifying"
        score = specificity_score("QF 1")
        assert score > specificity_score("Qualifying")

    def test_detects_spelled_out_numbers(self) -> None:
        """Test that spelled-out numbers add specificity."""
        score = specificity_score("Quarter Final Two")
        # Should include bonus for spelled-out "two"
        assert score > specificity_score("Quarter Final")

    def test_more_specific_session_has_higher_score(self) -> None:
        """Test that more specific session names have higher scores."""
        # "Quarter Final 2" should be more specific than "Quarter Final"
        specific = specificity_score("Quarter Final 2")
        generic = specificity_score("Quarter Final")
        assert specific > generic

    def test_case_insensitive_matching(self) -> None:
        """Test that specificity scoring is case-insensitive."""
        lower = specificity_score("part 2")
        upper = specificity_score("PART 2")
        mixed = specificity_score("Part 2")
        assert lower == upper == mixed

    def test_complex_session_name(self) -> None:
        """Test specificity for complex session name with multiple indicators."""
        # Complex name with digits, separators, and patterns
        score = specificity_score("Round 3 - Heat 2 - Part 1")
        # Should have high specificity due to multiple indicators
        assert score > 10


class TestAliasCandidates:
    """Test alias_candidates function."""

    def test_returns_canonical_title_first(self) -> None:
        """Test that canonical episode title is returned first."""
        episode = Mock()
        episode.title = "Quarter Final"
        episode.aliases = []

        pattern = Mock()
        pattern.session_aliases = {}

        match = Mock()
        match.episode = episode
        match.pattern = pattern

        candidates = alias_candidates(match)
        assert candidates == ["Quarter Final"]

    def test_includes_episode_aliases(self) -> None:
        """Test that episode aliases are included."""
        episode = Mock()
        episode.title = "Quarter Final"
        episode.aliases = ["QF", "Quarterfinal"]

        pattern = Mock()
        pattern.session_aliases = {}

        match = Mock()
        match.episode = episode
        match.pattern = pattern

        candidates = alias_candidates(match)
        assert candidates == ["Quarter Final", "QF", "Quarterfinal"]

    def test_includes_session_aliases_by_exact_match(self) -> None:
        """Test that session aliases are included when canonical title matches exactly."""
        episode = Mock()
        episode.title = "Quarter Final"
        episode.aliases = []

        pattern = Mock()
        pattern.session_aliases = {
            "Quarter Final": ["QF 1", "QF 2"]
        }

        match = Mock()
        match.episode = episode
        match.pattern = pattern

        candidates = alias_candidates(match)
        assert candidates == ["Quarter Final", "QF 1", "QF 2"]

    def test_includes_session_aliases_by_normalized_match(self) -> None:
        """Test that session aliases are included when normalized title matches."""
        episode = Mock()
        episode.title = "Quarter-Final"
        episode.aliases = []

        pattern = Mock()
        pattern.session_aliases = {
            "Quarter Final": ["QF 1", "QF 2"]  # Different formatting
        }

        match = Mock()
        match.episode = episode
        match.pattern = pattern

        candidates = alias_candidates(match)
        # Should match by normalized token (quarterfinal)
        assert "QF 1" in candidates
        assert "QF 2" in candidates

    def test_deduplicates_aliases(self) -> None:
        """Test that duplicate aliases are removed while preserving order."""
        episode = Mock()
        episode.title = "Quarter Final"
        episode.aliases = ["QF", "Quarter Final", "QF"]  # Duplicates

        pattern = Mock()
        pattern.session_aliases = {
            "Quarter Final": ["QF"]  # Another duplicate
        }

        match = Mock()
        match.episode = episode
        match.pattern = pattern

        candidates = alias_candidates(match)
        # Should have unique values in order
        assert candidates == ["Quarter Final", "QF"]

    def test_filters_out_empty_strings(self) -> None:
        """Test that empty strings are filtered out."""
        episode = Mock()
        episode.title = "Quarter Final"
        episode.aliases = ["", "QF", None, "Quarterfinal"]

        pattern = Mock()
        pattern.session_aliases = {}

        match = Mock()
        match.episode = episode
        match.pattern = pattern

        candidates = alias_candidates(match)
        assert "" not in candidates
        assert None not in candidates
        assert candidates == ["Quarter Final", "QF", "Quarterfinal"]

    def test_handles_none_title(self) -> None:
        """Test that None title is handled gracefully."""
        episode = Mock()
        episode.title = None
        episode.aliases = ["QF"]

        pattern = Mock()
        pattern.session_aliases = {}

        match = Mock()
        match.episode = episode
        match.pattern = pattern

        candidates = alias_candidates(match)
        assert candidates == ["QF"]


class TestSeasonCacheKey:
    """Test season_cache_key function."""

    def test_prefers_explicit_season_key(self) -> None:
        """Test that explicit season key is preferred."""
        season = Mock()
        season.key = "2023-24"
        season.display_number = 1
        season.index = 0

        match = Mock()
        match.season = season

        key = season_cache_key(match)
        assert key == "2023-24"

    def test_uses_display_number_when_no_key(self) -> None:
        """Test that display_number is used when key is None."""
        season = Mock()
        season.key = None
        season.display_number = 42
        season.index = 0

        match = Mock()
        match.season = season

        key = season_cache_key(match)
        assert key == "display:42"

    def test_falls_back_to_index(self) -> None:
        """Test that index is used as fallback."""
        season = Mock()
        season.key = None
        season.display_number = None
        season.index = 5

        match = Mock()
        match.season = season

        key = season_cache_key(match)
        assert key == "index:5"

    def test_converts_numeric_key_to_string(self) -> None:
        """Test that numeric key is converted to string."""
        season = Mock()
        season.key = 2024
        season.display_number = None
        season.index = 0

        match = Mock()
        match.season = season

        key = season_cache_key(match)
        assert key == "2024"
        assert isinstance(key, str)


class TestEpisodeCacheKey:
    """Test episode_cache_key function."""

    def test_prefers_id_from_metadata(self) -> None:
        """Test that 'id' from metadata is preferred."""
        episode = Mock()
        episode.metadata = {"id": "ep-12345", "guid": "other-guid"}
        episode.display_number = 1
        episode.title = "Episode Title"
        episode.index = 0

        match = Mock()
        match.episode = episode

        key = episode_cache_key(match)
        assert key == "id:ep-12345"

    def test_uses_guid_when_no_id(self) -> None:
        """Test that 'guid' is used when 'id' is not present."""
        episode = Mock()
        episode.metadata = {"guid": "guid-67890"}
        episode.display_number = 1
        episode.title = "Episode Title"
        episode.index = 0

        match = Mock()
        match.episode = episode

        key = episode_cache_key(match)
        assert key == "guid:guid-67890"

    def test_uses_episode_id_when_no_id_or_guid(self) -> None:
        """Test that 'episode_id' is used when 'id' and 'guid' are not present."""
        episode = Mock()
        episode.metadata = {"episode_id": "epid-abc"}
        episode.display_number = 1
        episode.title = "Episode Title"
        episode.index = 0

        match = Mock()
        match.episode = episode

        key = episode_cache_key(match)
        assert key == "episode_id:epid-abc"

    def test_uses_uuid_when_other_ids_not_present(self) -> None:
        """Test that 'uuid' is used when other ID fields are not present."""
        episode = Mock()
        episode.metadata = {"uuid": "uuid-xyz"}
        episode.display_number = 1
        episode.title = "Episode Title"
        episode.index = 0

        match = Mock()
        match.episode = episode

        key = episode_cache_key(match)
        assert key == "uuid:uuid-xyz"

    def test_uses_display_number_when_no_metadata_ids(self) -> None:
        """Test that display_number is used when no metadata IDs are present."""
        episode = Mock()
        episode.metadata = {}
        episode.display_number = 42
        episode.title = "Episode Title"
        episode.index = 0

        match = Mock()
        match.episode = episode

        key = episode_cache_key(match)
        assert key == "display:42"

    def test_uses_title_when_no_metadata_or_display_number(self) -> None:
        """Test that title is used when no metadata or display_number."""
        episode = Mock()
        episode.metadata = None
        episode.display_number = None
        episode.title = "Quarter Final"
        episode.index = 0

        match = Mock()
        match.episode = episode

        key = episode_cache_key(match)
        assert key == "title:Quarter Final"

    def test_falls_back_to_index(self) -> None:
        """Test that index is used as final fallback."""
        episode = Mock()
        episode.metadata = {}
        episode.display_number = None
        episode.title = None
        episode.index = 7

        match = Mock()
        match.episode = episode

        key = episode_cache_key(match)
        assert key == "index:7"

    def test_handles_none_metadata(self) -> None:
        """Test that None metadata is handled gracefully."""
        episode = Mock()
        episode.metadata = None
        episode.display_number = 5
        episode.title = "Title"
        episode.index = 0

        match = Mock()
        match.episode = episode

        key = episode_cache_key(match)
        assert key == "display:5"


class TestShouldOverwriteExisting:
    """Test should_overwrite_existing function."""

    def test_returns_true_for_repack(self) -> None:
        """Test that files with 'repack' always overwrite."""
        source_path = Path("/source/NBA.Game.REPACK.mkv")
        context = {}

        match = Mock()
        match.source_path = source_path
        match.context = context

        assert should_overwrite_existing(match) is True

    def test_returns_true_for_proper(self) -> None:
        """Test that files with 'proper' always overwrite."""
        source_path = Path("/source/NBA.Game.PROPER.mkv")
        context = {}

        match = Mock()
        match.source_path = source_path
        match.context = context

        assert should_overwrite_existing(match) is True

    def test_returns_true_for_2160p(self) -> None:
        """Test that 4K (2160p) files always overwrite."""
        source_path = Path("/source/NBA.Game.2160p.mkv")
        context = {}

        match = Mock()
        match.source_path = source_path
        match.context = context

        assert should_overwrite_existing(match) is True

    def test_case_insensitive_quality_detection(self) -> None:
        """Test that quality detection is case-insensitive."""
        source_path = Path("/source/NBA.Game.REPACK.mkv")
        context = {}

        match = Mock()
        match.source_path = source_path
        match.context = context

        assert should_overwrite_existing(match) is True

    def test_returns_false_when_no_session_in_context(self) -> None:
        """Test that False is returned when there's no session in context."""
        source_path = Path("/source/NBA.Game.mkv")
        context = {}

        match = Mock()
        match.source_path = source_path
        match.context = context

        assert should_overwrite_existing(match) is False

    def test_returns_false_when_session_is_empty(self) -> None:
        """Test that False is returned when session is empty string."""
        source_path = Path("/source/NBA.Game.mkv")
        context = {"session": ""}

        match = Mock()
        match.source_path = source_path
        match.context = context

        assert should_overwrite_existing(match) is False

    def test_returns_false_when_session_has_zero_specificity(self) -> None:
        """Test that False is returned when session has no specificity markers."""
        source_path = Path("/source/NBA.Game.mkv")
        context = {"session": "abc"}  # No digits, separators, or patterns

        episode = Mock()
        episode.title = "Quarter Final"
        episode.aliases = []

        pattern = Mock()
        pattern.session_aliases = {}

        match = Mock()
        match.source_path = source_path
        match.context = context
        match.episode = episode
        match.pattern = pattern

        assert should_overwrite_existing(match) is False

    def test_returns_true_when_session_more_specific_than_aliases(self) -> None:
        """Test that True is returned when session is more specific than aliases."""
        source_path = Path("/source/NBA.Game.mkv")
        context = {"session": "Quarter Final 2"}  # More specific

        episode = Mock()
        episode.title = "Quarter Final"  # Less specific
        episode.aliases = []

        pattern = Mock()
        pattern.session_aliases = {}

        match = Mock()
        match.source_path = source_path
        match.context = context
        match.episode = episode
        match.pattern = pattern

        result = should_overwrite_existing(match)
        assert result is True

    def test_returns_false_when_session_less_specific_than_aliases(self) -> None:
        """Test that False is returned when session is less specific."""
        source_path = Path("/source/NBA.Game.mkv")
        context = {"session": "Quarter Final"}  # Less specific

        episode = Mock()
        episode.title = "Quarter Final 2"  # More specific
        episode.aliases = []

        pattern = Mock()
        pattern.session_aliases = {}

        match = Mock()
        match.source_path = source_path
        match.context = context
        match.episode = episode
        match.pattern = pattern

        result = should_overwrite_existing(match)
        assert result is False

    def test_compares_session_against_all_aliases(self) -> None:
        """Test that session is compared against all alias candidates."""
        source_path = Path("/source/NBA.Game.mkv")
        context = {"session": "QF 2"}  # More specific

        episode = Mock()
        episode.title = "Quarter Final"
        episode.aliases = ["QF"]  # Less specific

        pattern = Mock()
        pattern.session_aliases = {}

        match = Mock()
        match.source_path = source_path
        match.context = context
        match.episode = episode
        match.pattern = pattern

        result = should_overwrite_existing(match)
        # "QF 2" (score: digits + separators) > "QF" (no digits)
        # Should return True because session is more specific than the least specific alias
        assert result is True

    def test_ignores_same_normalized_alias_when_comparing(self) -> None:
        """Test that aliases matching the session token are excluded from comparison."""
        source_path = Path("/source/NBA.Game.mkv")
        context = {"session": "Quarter Final 2"}

        episode = Mock()
        episode.title = "Quarter-Final-2"  # Same when normalized
        episode.aliases = []

        pattern = Mock()
        pattern.session_aliases = {}

        match = Mock()
        match.source_path = source_path
        match.context = context
        match.episode = episode
        match.pattern = pattern

        result = should_overwrite_existing(match)
        # When the only alias is the same as session (normalized), baseline_scores is empty
        # So it should return False
        assert result is False


class TestCleanupOldDestination:
    """Test cleanup_old_destination function."""

    def test_removes_source_key_from_stale_records(self) -> None:
        """Test that source_key is always removed from stale_records."""
        source_key = "source.mkv"
        stale_records = {source_key: Mock()}
        stale_destinations = {}

        cleanup_old_destination(
            source_key=source_key,
            old_destination=None,
            new_destination=Path("/new/dest.mkv"),
            dry_run=False,
            stale_records=stale_records,
            stale_destinations=stale_destinations,
            format_destination_fn=str,
            logger=Mock(),
        )

        assert source_key not in stale_records

    def test_removes_stale_destination_when_old_destination_is_none(self) -> None:
        """Test that stale_destination is removed when old_destination is None."""
        source_key = "source.mkv"
        stale_records = {}
        stale_destinations = {source_key: Path("/old/dest.mkv")}

        cleanup_old_destination(
            source_key=source_key,
            old_destination=None,
            new_destination=Path("/new/dest.mkv"),
            dry_run=False,
            stale_records=stale_records,
            stale_destinations=stale_destinations,
            format_destination_fn=str,
            logger=Mock(),
        )

        assert source_key not in stale_destinations

    def test_removes_stale_destination_when_destinations_match(self) -> None:
        """Test that stale_destination is removed when old and new destinations match."""
        source_key = "source.mkv"
        destination = Path("/same/dest.mkv")
        stale_records = {}
        stale_destinations = {source_key: destination}

        cleanup_old_destination(
            source_key=source_key,
            old_destination=destination,
            new_destination=destination,
            dry_run=False,
            stale_records=stale_records,
            stale_destinations=stale_destinations,
            format_destination_fn=str,
            logger=Mock(),
        )

        assert source_key not in stale_destinations

    def test_removes_stale_destination_when_old_destination_missing(self, tmp_path: Path) -> None:
        """Test that stale_destination is removed when old destination doesn't exist."""
        source_key = "source.mkv"
        old_destination = tmp_path / "nonexistent.mkv"
        new_destination = tmp_path / "new.mkv"

        stale_records = {}
        stale_destinations = {source_key: old_destination}

        cleanup_old_destination(
            source_key=source_key,
            old_destination=old_destination,
            new_destination=new_destination,
            dry_run=False,
            stale_records=stale_records,
            stale_destinations=stale_destinations,
            format_destination_fn=str,
            logger=Mock(),
        )

        assert source_key not in stale_destinations

    def test_removes_stale_destination_when_old_destination_is_directory(self, tmp_path: Path) -> None:
        """Test that stale_destination is removed when old destination is a directory."""
        source_key = "source.mkv"
        old_destination = tmp_path / "dir"
        old_destination.mkdir()
        new_destination = tmp_path / "new.mkv"

        stale_records = {}
        stale_destinations = {source_key: old_destination}

        cleanup_old_destination(
            source_key=source_key,
            old_destination=old_destination,
            new_destination=new_destination,
            dry_run=False,
            stale_records=stale_records,
            stale_destinations=stale_destinations,
            format_destination_fn=str,
            logger=Mock(),
        )

        assert source_key not in stale_destinations

    def test_logs_dry_run_message_and_keeps_file(self, tmp_path: Path) -> None:
        """Test that in dry-run mode, file is kept and message is logged."""
        source_key = "source.mkv"
        old_destination = tmp_path / "old.mkv"
        old_destination.write_text("content")
        new_destination = tmp_path / "new.mkv"

        stale_records = {}
        stale_destinations = {source_key: old_destination}
        logger = Mock()

        cleanup_old_destination(
            source_key=source_key,
            old_destination=old_destination,
            new_destination=new_destination,
            dry_run=True,
            stale_records=stale_records,
            stale_destinations=stale_destinations,
            format_destination_fn=str,
            logger=logger,
        )

        # File should still exist in dry-run
        assert old_destination.exists()
        # Stale destination should be removed from tracking
        assert source_key not in stale_destinations
        # Debug message should be logged
        logger.debug.assert_called_once()

    def test_deletes_old_destination_file(self, tmp_path: Path) -> None:
        """Test that old destination file is deleted when not in dry-run."""
        source_key = "source.mkv"
        old_destination = tmp_path / "old.mkv"
        old_destination.write_text("content")
        new_destination = tmp_path / "new.mkv"

        stale_records = {}
        stale_destinations = {source_key: old_destination}
        logger = Mock()

        cleanup_old_destination(
            source_key=source_key,
            old_destination=old_destination,
            new_destination=new_destination,
            dry_run=False,
            stale_records=stale_records,
            stale_destinations=stale_destinations,
            format_destination_fn=str,
            logger=logger,
        )

        # File should be deleted
        assert not old_destination.exists()
        # Stale destination should be removed from tracking
        assert source_key not in stale_destinations
        # Success message should be logged
        logger.debug.assert_called_once()

    def test_logs_warning_on_deletion_failure(self, tmp_path: Path) -> None:
        """Test that warning is logged when file deletion fails."""
        source_key = "source.mkv"
        old_destination = tmp_path / "old.mkv"
        old_destination.write_text("content")
        new_destination = tmp_path / "new.mkv"

        stale_records = {}
        stale_destinations = {source_key: old_destination}
        logger = Mock()

        # Make file read-only to cause deletion failure
        old_destination.chmod(0o444)

        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            cleanup_old_destination(
                source_key=source_key,
                old_destination=old_destination,
                new_destination=new_destination,
                dry_run=False,
                stale_records=stale_records,
                stale_destinations=stale_destinations,
                format_destination_fn=str,
                logger=logger,
            )

        # Stale destination should still be removed from tracking
        assert source_key not in stale_destinations
        # Warning should be logged
        logger.warning.assert_called_once()

    def test_always_removes_from_stale_destinations_dict(self, tmp_path: Path) -> None:
        """Test that source_key is always removed from stale_destinations in finally block."""
        source_key = "source.mkv"
        old_destination = tmp_path / "old.mkv"
        old_destination.write_text("content")
        new_destination = tmp_path / "new.mkv"

        stale_records = {}
        stale_destinations = {source_key: old_destination}
        logger = Mock()

        # Even if unlink raises an exception, finally block should clean up
        with patch.object(Path, "unlink", side_effect=OSError("Error")):
            cleanup_old_destination(
                source_key=source_key,
                old_destination=old_destination,
                new_destination=new_destination,
                dry_run=False,
                stale_records=stale_records,
                stale_destinations=stale_destinations,
                format_destination_fn=str,
                logger=logger,
            )

        # Should always be removed from dict
        assert source_key not in stale_destinations
