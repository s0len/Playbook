from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from playbook.models import ProcessingStats
from playbook.run_summary import (
    extract_error_context,
    filtered_ignored_details,
    has_activity,
    has_detailed_activity,
    summarize_counts,
    summarize_messages,
    summarize_plex_errors,
)


class TestHasActivity:
    """Test has_activity function."""

    def test_returns_false_for_empty_stats(self) -> None:
        """Test that has_activity returns False when stats are empty."""
        stats = ProcessingStats()
        assert has_activity(stats) is False

    def test_returns_true_when_processed(self) -> None:
        """Test that has_activity returns True when files were processed."""
        stats = ProcessingStats(processed=5)
        assert has_activity(stats) is True

    def test_returns_true_when_skipped(self) -> None:
        """Test that has_activity returns True when files were skipped."""
        stats = ProcessingStats(skipped=3)
        assert has_activity(stats) is True

    def test_returns_true_when_ignored(self) -> None:
        """Test that has_activity returns True when files were ignored."""
        stats = ProcessingStats(ignored=2)
        assert has_activity(stats) is True

    def test_returns_true_when_errors(self) -> None:
        """Test that has_activity returns True when there are errors."""
        stats = ProcessingStats(errors=["Error 1", "Error 2"])
        assert has_activity(stats) is True

    def test_returns_true_when_warnings(self) -> None:
        """Test that has_activity returns True when there are warnings."""
        stats = ProcessingStats(warnings=["Warning 1"])
        assert has_activity(stats) is True

    def test_returns_true_when_multiple_activities(self) -> None:
        """Test that has_activity returns True with multiple activities."""
        stats = ProcessingStats(processed=2, skipped=1, warnings=["Warning 1"])
        assert has_activity(stats) is True


class TestHasDetailedActivity:
    """Test has_detailed_activity function."""

    def test_returns_false_for_empty_stats(self) -> None:
        """Test that has_detailed_activity returns False when stats are empty."""
        stats = ProcessingStats()
        assert has_detailed_activity(stats) is False

    def test_returns_false_when_only_processed(self) -> None:
        """Test that has_detailed_activity returns False for only processed files."""
        stats = ProcessingStats(processed=5)
        assert has_detailed_activity(stats) is False

    def test_returns_false_when_only_ignored_without_details(self) -> None:
        """Test that has_detailed_activity returns False for ignored without details."""
        stats = ProcessingStats(ignored=3)
        assert has_detailed_activity(stats) is False

    def test_returns_true_when_errors(self) -> None:
        """Test that has_detailed_activity returns True when there are errors."""
        stats = ProcessingStats(errors=["Error 1"])
        assert has_detailed_activity(stats) is True

    def test_returns_true_when_warnings(self) -> None:
        """Test that has_detailed_activity returns True when there are warnings."""
        stats = ProcessingStats(warnings=["Warning 1"])
        assert has_detailed_activity(stats) is True

    def test_returns_true_when_skipped_details(self) -> None:
        """Test that has_detailed_activity returns True when there are skipped details."""
        stats = ProcessingStats(skipped_details=["Skipped: file.mkv"])
        assert has_detailed_activity(stats) is True

    def test_returns_true_when_ignored_details(self) -> None:
        """Test that has_detailed_activity returns True when there are ignored details."""
        stats = ProcessingStats(ignored_details=["Ignored: file.txt"])
        assert has_detailed_activity(stats) is True

    def test_returns_true_with_multiple_detail_types(self) -> None:
        """Test that has_detailed_activity returns True with multiple detail types."""
        stats = ProcessingStats(
            errors=["Error 1"],
            warnings=["Warning 1"],
            skipped_details=["Skipped: file.mkv"],
        )
        assert has_detailed_activity(stats) is True


class TestFilteredIgnoredDetails:
    """Test filtered_ignored_details function."""

    def test_returns_empty_list_for_empty_stats(self) -> None:
        """Test that filtered_ignored_details returns empty list for empty stats."""
        stats = ProcessingStats()
        result = filtered_ignored_details(stats)
        assert result == []

    def test_preserves_normal_ignored_details(self) -> None:
        """Test that normal ignored details are preserved."""
        stats = ProcessingStats(
            ignored_details=["File already exists", "Pattern did not match"]
        )
        result = filtered_ignored_details(stats)
        assert result == ["File already exists", "Pattern did not match"]

    def test_filters_out_non_video_extension_messages(self) -> None:
        """Test that non-video extension messages are filtered out."""
        stats = ProcessingStats(
            ignored_details=[
                "File already exists",
                "No configured sport accepts extension .txt",
                "No configured sport accepts extension .nfo",
                "Pattern did not match",
            ]
        )
        result = filtered_ignored_details(stats)
        assert result == [
            "File already exists",
            "Pattern did not match",
            "(Suppressed 2 non-video items)",
        ]

    def test_adds_suppressed_samples_count_singular(self) -> None:
        """Test that suppressed samples count is added (singular)."""
        stats = ProcessingStats(
            ignored_details=["File already exists"],
            suppressed_ignored_samples=1,
        )
        result = filtered_ignored_details(stats)
        assert result == ["File already exists", "(Suppressed 1 sample)"]

    def test_adds_suppressed_samples_count_plural(self) -> None:
        """Test that suppressed samples count is added (plural)."""
        stats = ProcessingStats(
            ignored_details=["File already exists"],
            suppressed_ignored_samples=5,
        )
        result = filtered_ignored_details(stats)
        assert result == ["File already exists", "(Suppressed 5 samples)"]

    def test_adds_both_suppression_types(self) -> None:
        """Test that both suppression types are added."""
        stats = ProcessingStats(
            ignored_details=[
                "File already exists",
                "No configured sport accepts extension .txt",
                "No configured sport accepts extension .nfo",
            ],
            suppressed_ignored_samples=3,
        )
        result = filtered_ignored_details(stats)
        assert result == [
            "File already exists",
            "(Suppressed 3 samples)",
            "(Suppressed 2 non-video items)",
        ]

    def test_uses_singular_for_one_non_video_item(self) -> None:
        """Test that singular 'item' is used for one non-video suppression."""
        stats = ProcessingStats(
            ignored_details=["No configured sport accepts extension .txt"]
        )
        result = filtered_ignored_details(stats)
        assert result == ["(Suppressed 1 non-video item)"]


class TestSummarizeCounts:
    """Test summarize_counts function."""

    def test_returns_empty_list_for_zero_total(self) -> None:
        """Test that summarize_counts returns empty list when total is 0."""
        result = summarize_counts({}, 0, "error")
        assert result == []

    def test_returns_empty_list_for_negative_total(self) -> None:
        """Test that summarize_counts returns empty list when total is negative."""
        result = summarize_counts({}, -5, "error")
        assert result == []

    def test_formats_single_sport_with_singular_entry(self) -> None:
        """Test formatting single sport with one entry."""
        counts = {"nba": 1}
        result = summarize_counts(counts, 1, "error")
        assert result == ["nba: 1 entry", "Run with --verbose for per-error details."]

    def test_formats_single_sport_with_plural_entries(self) -> None:
        """Test formatting single sport with multiple entries."""
        counts = {"nba": 5}
        result = summarize_counts(counts, 5, "warning")
        assert result == [
            "nba: 5 entries",
            "Run with --verbose for per-warning details.",
        ]

    def test_formats_multiple_sports_sorted_by_count_descending(self) -> None:
        """Test formatting multiple sports sorted by count (descending)."""
        counts = {"nfl": 3, "nba": 7, "mlb": 1}
        result = summarize_counts(counts, 11, "error")
        assert result == [
            "nba: 7 entries",
            "nfl: 3 entries",
            "mlb: 1 entry",
            "Run with --verbose for per-error details.",
        ]

    def test_formats_multiple_sports_with_alphabetical_tiebreaker(self) -> None:
        """Test that sports with same count are sorted alphabetically."""
        counts = {"nfl": 5, "nba": 5, "mlb": 5}
        result = summarize_counts(counts, 15, "error")
        # Same count, so alphabetical order: mlb, nba, nfl
        assert result == [
            "mlb: 5 entries",
            "nba: 5 entries",
            "nfl: 5 entries",
            "Run with --verbose for per-error details.",
        ]

    def test_adds_other_category_for_unaccounted_entries(self) -> None:
        """Test that 'other' category is added for unaccounted entries."""
        counts = {"nba": 3, "nfl": 2}
        result = summarize_counts(counts, 10, "ignored")
        assert result == [
            "nba: 3 entries",
            "nfl: 2 entries",
            "other: 5 entries",
            "Run with --verbose for per-ignored details.",
        ]

    def test_other_category_uses_singular_for_one_entry(self) -> None:
        """Test that 'other' category uses singular for one entry."""
        counts = {"nba": 5}
        result = summarize_counts(counts, 6, "error")
        assert result == [
            "nba: 5 entries",
            "other: 1 entry",
            "Run with --verbose for per-error details.",
        ]

    def test_verbose_prompt_uses_label(self) -> None:
        """Test that verbose prompt uses the provided label."""
        counts = {"nba": 1}
        result = summarize_counts(counts, 1, "custom-label")
        assert result[-1] == "Run with --verbose for per-custom-label details."


class TestSummarizeMessages:
    """Test summarize_messages function."""

    def test_returns_empty_list_for_empty_entries(self) -> None:
        """Test that summarize_messages returns empty list for empty entries."""
        result = summarize_messages([])
        assert result == []

    def test_formats_single_message_without_count_prefix(self) -> None:
        """Test formatting single unique message without count prefix."""
        entries = ["File not found"]
        result = summarize_messages(entries)
        assert result == ["File not found", "Run with --verbose for per-file details."]

    def test_formats_duplicate_messages_with_count_prefix(self) -> None:
        """Test formatting duplicate messages with count prefix."""
        entries = ["File not found", "File not found", "File not found"]
        result = summarize_messages(entries)
        assert result == [
            "3× File not found",
            "Run with --verbose for per-file details.",
        ]

    def test_sorts_by_count_descending(self) -> None:
        """Test that messages are sorted by count descending."""
        entries = ["Error A", "Error B", "Error B", "Error C", "Error C", "Error C"]
        result = summarize_messages(entries)
        assert result == [
            "3× Error C",
            "2× Error B",
            "Error A",
            "Run with --verbose for per-file details.",
        ]

    def test_sorts_alphabetically_when_counts_equal(self) -> None:
        """Test that messages with equal counts are sorted alphabetically."""
        entries = ["Error B", "Error A", "Error C"]
        result = summarize_messages(entries)
        # All have count 1, so alphabetical: A, B, C
        assert result[0] == "Error A"
        assert result[1] == "Error B"
        assert result[2] == "Error C"

    def test_limits_output_to_default_limit(self) -> None:
        """Test that output is limited to default limit (5)."""
        entries = [f"Error {i}" for i in range(10)]
        result = summarize_messages(entries)
        # 5 messages + 1 "... more" line + 1 verbose prompt = 7 lines
        assert len(result) == 7
        assert result[5] == "... 5 more (use --verbose for full list)"

    def test_limits_output_to_custom_limit(self) -> None:
        """Test that output is limited to custom limit."""
        entries = [f"Error {i}" for i in range(10)]
        result = summarize_messages(entries, limit=3)
        # 3 messages + 1 "... more" line + 1 verbose prompt = 5 lines
        assert len(result) == 5
        assert result[3] == "... 7 more (use --verbose for full list)"

    def test_no_more_line_when_under_limit(self) -> None:
        """Test that no 'more' line is shown when under limit."""
        entries = ["Error A", "Error B", "Error C"]
        result = summarize_messages(entries, limit=5)
        # 3 messages + 1 verbose prompt = 4 lines (no "... more" line)
        assert len(result) == 4
        assert result[-1] == "Run with --verbose for per-file details."
        assert "more" not in result[-2]

    def test_handles_mixed_counts(self) -> None:
        """Test handling mixed message counts."""
        entries = [
            "Error A",
            "Error A",
            "Error A",
            "Error B",
            "Error B",
            "Error C",
        ]
        result = summarize_messages(entries, limit=5)
        assert result[0] == "3× Error A"
        assert result[1] == "2× Error B"
        assert result[2] == "Error C"
        assert result[-1] == "Run with --verbose for per-file details."


class TestExtractErrorContext:
    """Test extract_error_context function."""

    def test_returns_none_for_unrecognized_error(self) -> None:
        """Test that extract_error_context returns None for unrecognized errors."""
        error = "Some random error message"
        result = extract_error_context(error)
        assert result is None

    def test_extracts_show_not_found_without_similar(self) -> None:
        """Test extracting context from 'Show not found' error without similar shows."""
        error = "Show not found: 'NBA Games' in library nba-lib (metadata: https://example.com/metadata.yaml)."
        result = extract_error_context(error)
        assert result == "'NBA Games' | library=nba-lib | source=https://example.com/metadata.yaml"

    def test_extracts_show_not_found_with_similar(self) -> None:
        """Test extracting context from 'Show not found' error with similar shows."""
        error = "Show not found: 'NBA Games' in library nba-lib (metadata: https://example.com/metadata.yaml). Similar: NBA 2023, NBA 2024"
        result = extract_error_context(error)
        assert (
            result
            == "'NBA Games' | library=nba-lib | similar=[NBA 2023, NBA 2024] | source=https://example.com/metadata.yaml"
        )

    def test_extracts_show_not_found_with_long_url(self) -> None:
        """Test that long metadata URLs are truncated for display."""
        error = "Show not found: 'NBA Games' in library nba-lib (metadata: https://example.com/very/long/path/to/metadata/file/that/is/too/long.yaml)."
        result = extract_error_context(error)
        assert result is not None
        # URL should be truncated to last 37 chars with "..." prefix
        assert "..." in result
        assert "source=" in result
        assert len(result.split("source=")[1]) <= 50  # "..." + 37 chars + some buffer

    def test_extracts_season_not_found_without_available(self) -> None:
        """Test extracting context from 'Season not found' error without available seasons."""
        error = "Season not found: Season 2023 in show 'NBA Games' | library=nba-lib | source=https://example.com/metadata.yaml."
        result = extract_error_context(error)
        assert result == "Season 2023 | show='NBA Games' | library=nba-lib"

    def test_extracts_season_not_found_with_available(self) -> None:
        """Test extracting context from 'Season not found' error with available seasons."""
        error = "Season not found: Season 2023 in show 'NBA Games' | library=nba-lib | source=https://example.com/metadata.yaml. Available: 2021, 2022"
        result = extract_error_context(error)
        assert (
            result
            == "Season 2023 | show='NBA Games' | library=nba-lib | plex has=[2021, 2022]"
        )

    def test_extracts_episode_not_found_without_available(self) -> None:
        """Test extracting context from 'Episode not found' error without available episodes."""
        error = "Episode not found: Episode 5 in season 2023 of 'NBA Games' | library=nba-lib | source=https://example.com/metadata.yaml."
        result = extract_error_context(error)
        assert result == "Episode 5 | season=2023 | show='NBA Games'"

    def test_extracts_episode_not_found_with_available(self) -> None:
        """Test extracting context from 'Episode not found' error with available episodes."""
        error = "Episode not found: Episode 5 in season 2023 of 'NBA Games' | library=nba-lib | source=https://example.com/metadata.yaml. Available: 1, 2, 3, 4"
        result = extract_error_context(error)
        assert (
            result
            == "Episode 5 | season=2023 | show='NBA Games' | plex has=[1, 2, 3, 4]"
        )

    def test_handles_season_error_with_extra_spaces(self) -> None:
        """Test handling season error with extra spaces."""
        error = "Season not found:  Season 2023  in show 'NBA Games' | library=nba-lib | source=https://example.com/metadata.yaml. Available: 2021, 2022"
        result = extract_error_context(error)
        assert result is not None
        assert "Season 2023" in result
        assert "show='NBA Games'" in result

    def test_handles_episode_error_with_extra_spaces(self) -> None:
        """Test handling episode error with extra spaces."""
        error = "Episode not found:  Episode 5  in season  2023  of 'NBA Games' | library=nba-lib | source=https://example.com/metadata.yaml."
        result = extract_error_context(error)
        assert result is not None
        assert "Episode 5" in result
        assert "season=2023" in result


class TestSummarizePlexErrors:
    """Test summarize_plex_errors function."""

    def test_returns_empty_list_for_empty_errors(self) -> None:
        """Test that summarize_plex_errors returns empty list for empty errors."""
        result = summarize_plex_errors([])
        assert result == []

    def test_formats_single_error_without_count(self) -> None:
        """Test formatting single error without count prefix."""
        errors = ["Show not found: 'NBA Games' in library nba-lib (metadata: https://example.com/metadata.yaml)."]
        result = summarize_plex_errors(errors)
        assert len(result) == 1
        assert result[0].startswith("- Show not found:")

    def test_groups_errors_by_category(self) -> None:
        """Test that errors are grouped by category."""
        errors = [
            "Show not found: 'NBA Games' in library nba-lib (metadata: https://example.com/metadata.yaml).",
            "Show not found: 'NFL Games' in library nfl-lib (metadata: https://example.com/metadata.yaml).",
            "Season not found: Season 2023 in show 'MLB Games' | library=mlb-lib | source=https://example.com/metadata.yaml.",
        ]
        result = summarize_plex_errors(errors)
        # Should have 2 groups: "Show not found" (2×) and "Season not found" (1×)
        assert len(result) >= 2
        assert any("2× Show not found" in line for line in result)

    def test_shows_context_for_grouped_errors(self) -> None:
        """Test that context is shown for grouped errors."""
        errors = [
            "Show not found: 'NBA Games' in library nba-lib (metadata: https://example.com/metadata.yaml). Similar: NBA 2023",
            "Show not found: 'NFL Games' in library nfl-lib (metadata: https://example.com/metadata.yaml). Similar: NFL 2023",
        ]
        result = summarize_plex_errors(errors)
        # Should show count and context from first error
        assert any("2× Show not found" in line for line in result)
        assert any("└─" in line for line in result)  # Context indicator

    def test_limits_output_to_default_limit(self) -> None:
        """Test that output is limited to default limit (10)."""
        errors = [f"Error type {i}: details" for i in range(15)]
        result = summarize_plex_errors(errors)
        # Should have at most 10 error categories + "... more" line
        assert len(result) <= 12  # 10 categories + context lines

    def test_limits_output_to_custom_limit(self) -> None:
        """Test that output is limited to custom limit."""
        errors = [f"Error type {i}: details" for i in range(10)]
        result = summarize_plex_errors(errors, limit=3)
        # Should show "... more error types" message
        assert any("more error types" in line for line in result)

    def test_shows_remaining_count_when_over_limit(self) -> None:
        """Test that remaining count is shown when over limit."""
        errors = [f"Error type {i}: details" for i in range(15)]
        result = summarize_plex_errors(errors, limit=10)
        # Should show "... 5 more error types"
        assert any("5 more error types" in line for line in result)

    def test_uses_colon_for_category_extraction(self) -> None:
        """Test that category is extracted using colon separator."""
        errors = [
            "Show not found: 'NBA Games' details",
            "Show not found: 'NFL Games' details",
            "Season not found: Season 2023 details",
        ]
        result = summarize_plex_errors(errors)
        # Categories: "Show not found" and "Season not found"
        assert any("Show not found" in line for line in result)
        assert any("Season not found" in line for line in result)

    def test_uses_first_30_chars_for_category_without_colon(self) -> None:
        """Test that first 30 chars are used as category when no colon."""
        errors = [
            "This is a very long error message without a colon separator in it",
            "This is a very long error message without a colon separator in it",
        ]
        result = summarize_plex_errors(errors)
        # Should group both errors together using first 30 chars as category
        assert len(result) >= 1
        assert any("2×" in line for line in result)

    def test_sorts_groups_by_count_descending(self) -> None:
        """Test that error groups are sorted by count descending."""
        errors = [
            "Error A: details",
            "Error B: details",
            "Error B: details",
            "Error B: details",
            "Error C: details",
            "Error C: details",
        ]
        result = summarize_plex_errors(errors)
        # Error B (3×) should come before Error C (2×) and Error A (1×)
        b_index = next(i for i, line in enumerate(result) if "Error B" in line)
        c_index = next(i for i, line in enumerate(result) if "Error C" in line)
        a_index = next(i for i, line in enumerate(result) if "Error A" in line)
        assert b_index < c_index < a_index

    def test_truncates_long_errors_without_context(self) -> None:
        """Test that long errors without extractable context are truncated."""
        long_error = "A" * 100  # 100 character error
        errors = [long_error]
        result = summarize_plex_errors(errors)
        # Should be truncated to 77 chars + "..."
        assert any("..." in line for line in result)

    def test_extracts_context_for_single_error(self) -> None:
        """Test that context is extracted for single error in category."""
        errors = [
            "Show not found: 'NBA Games' in library nba-lib (metadata: https://example.com/metadata.yaml). Similar: NBA 2023"
        ]
        result = summarize_plex_errors(errors)
        # Should extract and display context
        assert len(result) == 1
        assert "Show not found" in result[0]
        assert "'NBA Games'" in result[0]
