from __future__ import annotations

import io
from dataclasses import dataclass

import pytest
from rich.console import Console

from playbook.models import ProcessingStats
from playbook.plex_client import PlexSyncStats
from playbook.summary_table import (
    DIM_COLOR,
    ERROR_COLOR,
    ERROR_SYMBOL,
    IGNORE_SYMBOL,
    SKIP_SYMBOL,
    SUCCESS_COLOR,
    SUCCESS_SYMBOL,
    WARNING_COLOR,
    WARNING_SYMBOL,
    SummaryTableRenderer,
)


# Mock SportConfig for testing
@dataclass
class MockSportConfig:
    id: str
    name: str


class TestColorHelpers:
    """Test color and symbol helper methods."""

    def test_get_status_color_for_zero_values(self) -> None:
        assert SummaryTableRenderer._get_status_color(0) == DIM_COLOR
        assert SummaryTableRenderer._get_status_color(0, is_error=True) == DIM_COLOR
        assert SummaryTableRenderer._get_status_color(0, is_warning=True) == DIM_COLOR

    def test_get_status_color_for_errors(self) -> None:
        assert SummaryTableRenderer._get_status_color(1, is_error=True) == ERROR_COLOR
        assert SummaryTableRenderer._get_status_color(5, is_error=True) == ERROR_COLOR

    def test_get_status_color_for_warnings(self) -> None:
        assert SummaryTableRenderer._get_status_color(1, is_warning=True) == WARNING_COLOR
        assert SummaryTableRenderer._get_status_color(3, is_warning=True) == WARNING_COLOR

    def test_get_status_color_for_success(self) -> None:
        assert SummaryTableRenderer._get_status_color(1) == SUCCESS_COLOR
        assert SummaryTableRenderer._get_status_color(10) == SUCCESS_COLOR

    def test_colorize_value_zero(self) -> None:
        result = SummaryTableRenderer._colorize_value(0)
        assert result == f"[{DIM_COLOR}]0[/{DIM_COLOR}]"

    def test_colorize_value_error(self) -> None:
        result = SummaryTableRenderer._colorize_value(5, is_error=True)
        assert result == f"[{ERROR_COLOR}]5[/{ERROR_COLOR}]"

    def test_colorize_value_warning(self) -> None:
        result = SummaryTableRenderer._colorize_value(3, is_warning=True)
        assert result == f"[{WARNING_COLOR}]3[/{WARNING_COLOR}]"

    def test_colorize_value_success(self) -> None:
        result = SummaryTableRenderer._colorize_value(10)
        assert result == f"[{SUCCESS_COLOR}]10[/{SUCCESS_COLOR}]"


class TestSymbolHelpers:
    """Test symbol/emoji helper methods."""

    def test_get_status_symbol_error(self) -> None:
        assert SummaryTableRenderer._get_status_symbol(is_error=True) == ERROR_SYMBOL

    def test_get_status_symbol_warning(self) -> None:
        assert SummaryTableRenderer._get_status_symbol(is_warning=True) == WARNING_SYMBOL

    def test_get_status_symbol_skip(self) -> None:
        assert SummaryTableRenderer._get_status_symbol(is_skip=True) == SKIP_SYMBOL

    def test_get_status_symbol_ignore(self) -> None:
        assert SummaryTableRenderer._get_status_symbol(is_ignore=True) == IGNORE_SYMBOL

    def test_get_status_symbol_success(self) -> None:
        assert SummaryTableRenderer._get_status_symbol() == SUCCESS_SYMBOL

    def test_colorize_value_with_symbol_zero(self) -> None:
        result = SummaryTableRenderer._colorize_value_with_symbol(0)
        assert result == f"[{DIM_COLOR}]0[/{DIM_COLOR}]"

    def test_colorize_value_with_symbol_error(self) -> None:
        result = SummaryTableRenderer._colorize_value_with_symbol(5, is_error=True)
        assert result == f"[{ERROR_COLOR}]{ERROR_SYMBOL} 5[/{ERROR_COLOR}]"

    def test_colorize_value_with_symbol_warning(self) -> None:
        result = SummaryTableRenderer._colorize_value_with_symbol(3, is_warning=True)
        assert result == f"[{WARNING_COLOR}]{WARNING_SYMBOL} 3[/{WARNING_COLOR}]"

    def test_colorize_value_with_symbol_skip(self) -> None:
        result = SummaryTableRenderer._colorize_value_with_symbol(2, is_skip=True)
        assert result == f"[{SUCCESS_COLOR}]{SKIP_SYMBOL} 2[/{SUCCESS_COLOR}]"

    def test_colorize_value_with_symbol_ignore(self) -> None:
        result = SummaryTableRenderer._colorize_value_with_symbol(4, is_ignore=True)
        assert result == f"[{SUCCESS_COLOR}]{IGNORE_SYMBOL} 4[/{SUCCESS_COLOR}]"

    def test_colorize_value_with_symbol_success(self) -> None:
        result = SummaryTableRenderer._colorize_value_with_symbol(10)
        assert result == f"[{SUCCESS_COLOR}]{SUCCESS_SYMBOL} 10[/{SUCCESS_COLOR}]"


class TestRenderSummaryTable:
    """Test render_summary_table method."""

    def test_render_summary_table_empty_stats(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats()
        table = renderer.render_summary_table(stats)

        assert table is not None
        assert table.title == "Processing Summary"
        # Table should have 2 columns (Metric, Count)
        assert len(table.columns) == 2

    def test_render_summary_table_with_processed_files(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(processed=5)
        table = renderer.render_summary_table(stats)

        # Verify table is created with expected title
        assert table.title == "Processing Summary"

    def test_render_summary_table_with_warnings(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(warnings=["warning 1", "warning 2"])
        table = renderer.render_summary_table(stats)

        assert table is not None

    def test_render_summary_table_with_errors(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(errors=["error 1", "error 2", "error 3"])
        table = renderer.render_summary_table(stats)

        assert table is not None

    def test_render_summary_table_with_plex_sync_stats(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(processed=10)
        plex_sync_stats = PlexSyncStats(errors=["plex error 1", "plex error 2"])

        table = renderer.render_summary_table(stats, plex_sync_stats)

        assert table is not None
        # Should include Plex Sync Errors row

    def test_render_summary_table_without_plex_sync_errors(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(processed=10)
        plex_sync_stats = PlexSyncStats()

        table = renderer.render_summary_table(stats, plex_sync_stats)

        assert table is not None
        # Should not include Plex Sync Errors row when there are no errors

    def test_render_summary_table_mixed_stats(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            processed=10,
            skipped=2,
            ignored=5,
            warnings=["warn1"],
            errors=["err1", "err2"],
        )
        table = renderer.render_summary_table(stats)

        assert table is not None
        assert table.title == "Processing Summary"


class TestRenderRunRecapTable:
    """Test render_run_recap_table method."""

    def test_render_run_recap_table_basic(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(processed=5)
        destinations = ["/dest1", "/dest2"]

        table = renderer.render_run_recap_table(stats, duration=12.34, destinations=destinations)

        assert table is not None
        assert table.title == "Run Recap"
        assert len(table.columns) == 2

    def test_render_run_recap_table_empty_stats(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats()
        destinations = []

        table = renderer.render_run_recap_table(stats, duration=0.0, destinations=destinations)

        assert table is not None

    def test_render_run_recap_table_with_plex_sync_status(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(processed=10)
        destinations = ["/dest1"]

        table = renderer.render_run_recap_table(
            stats,
            duration=15.5,
            destinations=destinations,
            plex_sync_status="Success",
        )

        assert table is not None

    def test_render_run_recap_table_with_kometa_triggered(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(processed=10)
        destinations = ["/dest1"]

        table = renderer.render_run_recap_table(
            stats,
            duration=15.5,
            destinations=destinations,
            kometa_triggered=True,
        )

        assert table is not None

    def test_render_run_recap_table_kometa_not_triggered(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(processed=10)
        destinations = ["/dest1"]

        table = renderer.render_run_recap_table(
            stats,
            duration=15.5,
            destinations=destinations,
            kometa_triggered=False,
        )

        assert table is not None

    def test_render_run_recap_table_full_options(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            processed=10,
            skipped=2,
            ignored=5,
            warnings=["warn1"],
            errors=["err1"],
        )
        destinations = ["/dest1", "/dest2"]

        table = renderer.render_run_recap_table(
            stats,
            duration=25.75,
            destinations=destinations,
            plex_sync_status="Success",
            kometa_triggered=True,
        )

        assert table is not None


class TestRenderSportBreakdownTable:
    """Test render_sport_breakdown_table method."""

    def test_render_sport_breakdown_table_no_activity(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats()
        sports_by_id = {}

        table = renderer.render_sport_breakdown_table(stats, sports_by_id)

        # Should return None when there's no activity
        assert table is None

    def test_render_sport_breakdown_table_single_sport(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            errors_by_sport={"f1": 1},
        )
        sports_by_id = {
            "f1": MockSportConfig(id="f1", name="Formula 1"),
        }

        table = renderer.render_sport_breakdown_table(stats, sports_by_id)

        # Should return None when there's only one sport with activity
        assert table is None

    def test_render_sport_breakdown_table_multiple_sports(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            errors_by_sport={"f1": 2},
            warnings_by_sport={"nascar": 1},
        )
        sports_by_id = {
            "f1": MockSportConfig(id="f1", name="Formula 1"),
            "nascar": MockSportConfig(id="nascar", name="NASCAR"),
        }
        processed_by_sport = {"f1": 10, "nascar": 5}

        table = renderer.render_sport_breakdown_table(stats, sports_by_id, processed_by_sport)

        # Should return a table when there are 2+ sports with activity
        assert table is not None
        assert table.title == "Sport-by-Sport Breakdown"
        assert len(table.columns) == 6

    def test_render_sport_breakdown_table_filters_samples_sport(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            errors_by_sport={"f1": 2},
            warnings_by_sport={"nascar": 1},
            ignored_by_sport={"samples": 10},  # Should be filtered out
        )
        sports_by_id = {
            "f1": MockSportConfig(id="f1", name="Formula 1"),
            "nascar": MockSportConfig(id="nascar", name="NASCAR"),
        }

        table = renderer.render_sport_breakdown_table(stats, sports_by_id)

        # Should return a table (samples sport is filtered out)
        assert table is not None

    def test_render_sport_breakdown_table_with_processed_counts(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            errors_by_sport={"f1": 1},
            warnings_by_sport={"nascar": 2},
        )
        sports_by_id = {
            "f1": MockSportConfig(id="f1", name="Formula 1"),
            "nascar": MockSportConfig(id="nascar", name="NASCAR"),
        }
        processed_by_sport = {"f1": 20, "nascar": 15}

        table = renderer.render_sport_breakdown_table(stats, sports_by_id, processed_by_sport)

        assert table is not None

    def test_render_sport_breakdown_table_without_processed_counts(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            errors_by_sport={"f1": 1},
            warnings_by_sport={"nascar": 2},
        )
        sports_by_id = {
            "f1": MockSportConfig(id="f1", name="Formula 1"),
            "nascar": MockSportConfig(id="nascar", name="NASCAR"),
        }

        table = renderer.render_sport_breakdown_table(stats, sports_by_id, processed_by_sport=None)

        assert table is not None

    def test_render_sport_breakdown_table_sport_name_fallback(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            errors_by_sport={"f1": 1},
            warnings_by_sport={"unknown_sport": 2},
        )
        sports_by_id = {
            "f1": MockSportConfig(id="f1", name="Formula 1"),
            # unknown_sport not in sports_by_id
        }

        table = renderer.render_sport_breakdown_table(stats, sports_by_id)

        # Should use sport ID as name when SportConfig not found
        assert table is not None

    def test_render_sport_breakdown_table_sorted_by_id(self) -> None:
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            errors_by_sport={"zebra": 1},
            warnings_by_sport={"alpha": 2},
        )
        sports_by_id = {
            "zebra": MockSportConfig(id="zebra", name="Zebra Sport"),
            "alpha": MockSportConfig(id="alpha", name="Alpha Sport"),
        }

        table = renderer.render_sport_breakdown_table(stats, sports_by_id)

        # Sports should be sorted by ID (alpha before zebra)
        assert table is not None


class TestPlainTextRendering:
    """Test plain text rendering methods."""

    def test_render_summary_plain_text_empty(self) -> None:
        stats = ProcessingStats()
        result = SummaryTableRenderer.render_summary_plain_text(stats)

        assert "Processing Summary" in result
        assert "Processed        : 0" in result
        assert "Skipped          : 0" in result
        assert "Ignored          : 0" in result
        assert "Warnings         : 0" in result
        assert "Errors           : 0" in result

    def test_render_summary_plain_text_with_stats(self) -> None:
        stats = ProcessingStats(
            processed=10,
            skipped=2,
            ignored=5,
            warnings=["warn1", "warn2"],
            errors=["err1"],
        )
        result = SummaryTableRenderer.render_summary_plain_text(stats)

        assert "Processed        : 10" in result
        assert "Skipped          : 2" in result
        assert "Ignored          : 5" in result
        assert "Warnings         : 2" in result
        assert "Errors           : 1" in result

    def test_render_summary_plain_text_with_plex_errors(self) -> None:
        stats = ProcessingStats(processed=10)
        plex_sync_stats = PlexSyncStats(errors=["plex err1", "plex err2"])

        result = SummaryTableRenderer.render_summary_plain_text(stats, plex_sync_stats)

        assert "Plex Sync Errors : 2" in result

    def test_render_summary_plain_text_without_plex_errors(self) -> None:
        stats = ProcessingStats(processed=10)
        plex_sync_stats = PlexSyncStats()

        result = SummaryTableRenderer.render_summary_plain_text(stats, plex_sync_stats)

        # Should not include Plex Sync Errors line
        assert "Plex Sync Errors" not in result

    def test_render_run_recap_plain_text_basic(self) -> None:
        stats = ProcessingStats(processed=10)
        destinations = ["/dest1", "/dest2"]

        result = SummaryTableRenderer.render_run_recap_plain_text(stats, duration=12.34, destinations=destinations)

        assert "Run Recap" in result
        assert "Duration         : 12.34s" in result
        assert "Processed        : 10" in result
        assert "Destinations     : 2" in result

    def test_render_run_recap_plain_text_with_plex_sync(self) -> None:
        stats = ProcessingStats(processed=10)
        destinations = ["/dest1"]

        result = SummaryTableRenderer.render_run_recap_plain_text(
            stats,
            duration=15.5,
            destinations=destinations,
            plex_sync_status="Success",
        )

        assert "Plex Sync        : Success" in result

    def test_render_run_recap_plain_text_with_kometa(self) -> None:
        stats = ProcessingStats(processed=10)
        destinations = ["/dest1"]

        result = SummaryTableRenderer.render_run_recap_plain_text(
            stats,
            duration=15.5,
            destinations=destinations,
            kometa_triggered=True,
        )

        assert "Kometa Triggered : yes" in result

    def test_render_run_recap_plain_text_kometa_false(self) -> None:
        stats = ProcessingStats(processed=10)
        destinations = ["/dest1"]

        result = SummaryTableRenderer.render_run_recap_plain_text(
            stats,
            duration=15.5,
            destinations=destinations,
            kometa_triggered=False,
        )

        assert "Kometa Triggered : no" in result

    def test_render_sport_breakdown_plain_text_no_activity(self) -> None:
        stats = ProcessingStats()
        sports_by_id = {}

        result = SummaryTableRenderer.render_sport_breakdown_plain_text(stats, sports_by_id)

        # Should return None when there's no activity
        assert result is None

    def test_render_sport_breakdown_plain_text_single_sport(self) -> None:
        stats = ProcessingStats(errors_by_sport={"f1": 1})
        sports_by_id = {
            "f1": MockSportConfig(id="f1", name="Formula 1"),
        }

        result = SummaryTableRenderer.render_sport_breakdown_plain_text(stats, sports_by_id)

        # Should return None when there's only one sport
        assert result is None

    def test_render_sport_breakdown_plain_text_multiple_sports(self) -> None:
        stats = ProcessingStats(
            errors_by_sport={"f1": 2},
            warnings_by_sport={"nascar": 1},
        )
        sports_by_id = {
            "f1": MockSportConfig(id="f1", name="Formula 1"),
            "nascar": MockSportConfig(id="nascar", name="NASCAR"),
        }
        processed_by_sport = {"f1": 10, "nascar": 5}

        result = SummaryTableRenderer.render_sport_breakdown_plain_text(
            stats,
            sports_by_id,
            processed_by_sport,
        )

        assert result is not None
        assert "Sport-by-Sport Breakdown" in result
        assert "f1" in result
        assert "nascar" in result
        assert "Formula 1" in result
        assert "NASCAR" in result

    def test_render_sport_breakdown_plain_text_filters_samples(self) -> None:
        stats = ProcessingStats(
            errors_by_sport={"f1": 2},
            warnings_by_sport={"nascar": 1},
            ignored_by_sport={"samples": 10},
        )
        sports_by_id = {
            "f1": MockSportConfig(id="f1", name="Formula 1"),
            "nascar": MockSportConfig(id="nascar", name="NASCAR"),
        }

        result = SummaryTableRenderer.render_sport_breakdown_plain_text(stats, sports_by_id)

        assert result is not None
        assert "samples" not in result


class TestPrintMethods:
    """Test print_summary_table and print_run_recap_table methods."""

    def test_print_summary_table(self) -> None:
        # Create a console that writes to a string buffer
        string_buffer = io.StringIO()
        console = Console(file=string_buffer, force_terminal=False, width=120)
        renderer = SummaryTableRenderer(console=console)

        stats = ProcessingStats(processed=5, warnings=["warn1"])
        renderer.print_summary_table(stats)

        output = string_buffer.getvalue()
        assert "Processing Summary" in output

    def test_print_run_recap_table(self) -> None:
        # Create a console that writes to a string buffer
        string_buffer = io.StringIO()
        console = Console(file=string_buffer, force_terminal=False, width=120)
        renderer = SummaryTableRenderer(console=console)

        stats = ProcessingStats(processed=10)
        destinations = ["/dest1", "/dest2"]
        renderer.print_run_recap_table(stats, duration=12.5, destinations=destinations)

        output = string_buffer.getvalue()
        assert "Run Recap" in output


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_all_zeros(self) -> None:
        """Test rendering when all stats are zero."""
        renderer = SummaryTableRenderer()
        stats = ProcessingStats()

        # Summary table
        summary_table = renderer.render_summary_table(stats)
        assert summary_table is not None

        # Run recap table
        recap_table = renderer.render_run_recap_table(stats, duration=0.0, destinations=[])
        assert recap_table is not None

        # Plain text
        summary_plain = SummaryTableRenderer.render_summary_plain_text(stats)
        assert "0" in summary_plain

    def test_errors_only(self) -> None:
        """Test rendering when only errors are present."""
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(errors=["error1", "error2", "error3"])

        table = renderer.render_summary_table(stats)
        assert table is not None

    def test_warnings_only(self) -> None:
        """Test rendering when only warnings are present."""
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(warnings=["warn1", "warn2"])

        table = renderer.render_summary_table(stats)
        assert table is not None

    def test_skipped_only(self) -> None:
        """Test rendering when only skipped files are present."""
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(skipped=5)

        table = renderer.render_summary_table(stats)
        assert table is not None

    def test_ignored_only(self) -> None:
        """Test rendering when only ignored files are present."""
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(ignored=10)

        table = renderer.render_summary_table(stats)
        assert table is not None

    def test_large_numbers(self) -> None:
        """Test rendering with large numbers."""
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            processed=99999,
            skipped=12345,
            ignored=54321,
            warnings=["w" + str(i) for i in range(100)],
            errors=["e" + str(i) for i in range(50)],
        )

        table = renderer.render_summary_table(stats)
        assert table is not None

    def test_none_plex_sync_stats(self) -> None:
        """Test rendering with None plex_sync_stats."""
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(processed=5)

        table = renderer.render_summary_table(stats, plex_sync_stats=None)
        assert table is not None

    def test_empty_destinations(self) -> None:
        """Test rendering run recap with empty destinations."""
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(processed=5)

        table = renderer.render_run_recap_table(stats, duration=1.0, destinations=[])
        assert table is not None

    def test_mixed_sport_activity(self) -> None:
        """Test sport breakdown with mixed activity levels."""
        renderer = SummaryTableRenderer()
        stats = ProcessingStats(
            errors_by_sport={"sport1": 5, "sport3": 2},
            warnings_by_sport={"sport2": 3},
        )
        sports_by_id = {
            "sport1": MockSportConfig(id="sport1", name="Sport One"),
            "sport2": MockSportConfig(id="sport2", name="Sport Two"),
            "sport3": MockSportConfig(id="sport3", name="Sport Three"),
        }
        processed_by_sport = {"sport1": 100, "sport2": 200}

        table = renderer.render_sport_breakdown_table(stats, sports_by_id, processed_by_sport)
        assert table is not None
