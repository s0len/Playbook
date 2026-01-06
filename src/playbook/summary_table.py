from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:  # pragma: no cover
    from .models import ProcessingStats
    from .plex_client import PlexSyncStats


# Color constants for status indicators
SUCCESS_COLOR = "green"
WARNING_COLOR = "yellow"
ERROR_COLOR = "red"
DIM_COLOR = "dim"

# Symbol/emoji indicators for quick scanning
SUCCESS_SYMBOL = "✓"
WARNING_SYMBOL = "⚠"
ERROR_SYMBOL = "✗"
SKIP_SYMBOL = "⊘"
IGNORE_SYMBOL = "○"


class SummaryTableRenderer:
    """Renders processing statistics as Rich Tables with color-coded status indicators."""

    def __init__(self, console: Optional[Console] = None) -> None:
        """Initialize the renderer.

        Args:
            console: Optional Rich Console instance. If not provided, creates a new one.
        """
        self.console = console or Console()

    @staticmethod
    def _get_status_color(value: int, *, is_error: bool = False, is_warning: bool = False) -> str:
        """Get the color for a status value.

        Args:
            value: The numeric value to color
            is_error: Whether this represents an error count
            is_warning: Whether this represents a warning count

        Returns:
            Rich color string
        """
        if value == 0:
            return DIM_COLOR
        if is_error:
            return ERROR_COLOR
        if is_warning:
            return WARNING_COLOR
        return SUCCESS_COLOR

    @staticmethod
    def _colorize_value(value: int, *, is_error: bool = False, is_warning: bool = False) -> str:
        """Colorize a numeric value based on its type.

        Args:
            value: The numeric value to colorize
            is_error: Whether this represents an error count
            is_warning: Whether this represents a warning count

        Returns:
            Rich formatted string with color markup
        """
        color = SummaryTableRenderer._get_status_color(value, is_error=is_error, is_warning=is_warning)
        return f"[{color}]{value}[/{color}]"

    @staticmethod
    def _get_status_symbol(
        *,
        is_error: bool = False,
        is_warning: bool = False,
        is_skip: bool = False,
        is_ignore: bool = False,
    ) -> str:
        """Get the symbol/emoji for a status type.

        Args:
            is_error: Whether this represents an error
            is_warning: Whether this represents a warning
            is_skip: Whether this represents a skip
            is_ignore: Whether this represents ignored items

        Returns:
            Symbol string for the status type
        """
        if is_error:
            return ERROR_SYMBOL
        if is_warning:
            return WARNING_SYMBOL
        if is_skip:
            return SKIP_SYMBOL
        if is_ignore:
            return IGNORE_SYMBOL
        return SUCCESS_SYMBOL

    @staticmethod
    def _colorize_value_with_symbol(
        value: int,
        *,
        is_error: bool = False,
        is_warning: bool = False,
        is_skip: bool = False,
        is_ignore: bool = False,
    ) -> str:
        """Colorize a numeric value with a status symbol.

        Args:
            value: The numeric value to colorize
            is_error: Whether this represents an error count
            is_warning: Whether this represents a warning count
            is_skip: Whether this represents a skip count
            is_ignore: Whether this represents an ignore count

        Returns:
            Rich formatted string with symbol and color markup
        """
        if value == 0:
            return f"[{DIM_COLOR}]{value}[/{DIM_COLOR}]"

        symbol = SummaryTableRenderer._get_status_symbol(
            is_error=is_error,
            is_warning=is_warning,
            is_skip=is_skip,
            is_ignore=is_ignore,
        )
        color = SummaryTableRenderer._get_status_color(
            value, is_error=is_error, is_warning=is_warning
        )
        return f"[{color}]{symbol} {value}[/{color}]"

    def render_summary_table(
        self,
        stats: ProcessingStats,
        plex_sync_stats: Optional[PlexSyncStats] = None,
    ) -> Table:
        """Render a summary table of processing statistics.

        Args:
            stats: Processing statistics to render
            plex_sync_stats: Optional Plex sync statistics

        Returns:
            Rich Table instance ready to print
        """
        table = Table(title="Processing Summary", show_header=True, header_style="bold")

        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Count", justify="right")

        # Add processing stats
        table.add_row("Processed", self._colorize_value(stats.processed))
        table.add_row("Skipped", self._colorize_value(stats.skipped, is_warning=True))
        table.add_row("Ignored", self._colorize_value(stats.ignored))
        table.add_row("Warnings", self._colorize_value(len(stats.warnings), is_warning=True))
        table.add_row("Errors", self._colorize_value(len(stats.errors), is_error=True))

        # Add Plex sync errors if available
        if plex_sync_stats and plex_sync_stats.errors:
            plex_errors = len(plex_sync_stats.errors)
            table.add_row("Plex Sync Errors", self._colorize_value(plex_errors, is_error=True))

        return table

    def render_run_recap_table(
        self,
        stats: ProcessingStats,
        duration: float,
        destinations: List[str],
        plex_sync_status: Optional[str] = None,
        kometa_triggered: Optional[bool] = None,
    ) -> Table:
        """Render a run recap table with overall statistics.

        Args:
            stats: Processing statistics
            duration: Duration of the run in seconds
            destinations: List of destination directories touched
            plex_sync_status: Optional Plex sync status message
            kometa_triggered: Optional flag indicating if Kometa was triggered

        Returns:
            Rich Table instance ready to print
        """
        table = Table(title="Run Recap", show_header=True, header_style="bold")

        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right")

        # Add run statistics
        table.add_row("Duration", f"{duration:.2f}s")
        table.add_row("Processed", self._colorize_value(stats.processed))
        table.add_row("Skipped", self._colorize_value(stats.skipped, is_warning=True))
        table.add_row("Ignored", self._colorize_value(stats.ignored))
        table.add_row("Warnings", self._colorize_value(len(stats.warnings), is_warning=True))
        table.add_row("Errors", self._colorize_value(len(stats.errors), is_error=True))
        table.add_row("Destinations", str(len(destinations)))

        # Add Plex sync status if provided
        if plex_sync_status is not None:
            table.add_row("Plex Sync", plex_sync_status)

        # Add Kometa status if provided
        if kometa_triggered is not None:
            table.add_row("Kometa Triggered", "yes" if kometa_triggered else "no")

        return table

    def print_summary_table(
        self,
        stats: ProcessingStats,
        plex_sync_stats: Optional[PlexSyncStats] = None,
    ) -> None:
        """Print a summary table to the console.

        Args:
            stats: Processing statistics to render
            plex_sync_stats: Optional Plex sync statistics
        """
        table = self.render_summary_table(stats, plex_sync_stats)
        self.console.print()
        self.console.print(table)

    def print_run_recap_table(
        self,
        stats: ProcessingStats,
        duration: float,
        destinations: List[str],
        plex_sync_status: Optional[str] = None,
        kometa_triggered: Optional[bool] = None,
    ) -> None:
        """Print a run recap table to the console.

        Args:
            stats: Processing statistics
            duration: Duration of the run in seconds
            destinations: List of destination directories touched
            plex_sync_status: Optional Plex sync status message
            kometa_triggered: Optional flag indicating if Kometa was triggered
        """
        table = self.render_run_recap_table(
            stats,
            duration,
            destinations,
            plex_sync_status,
            kometa_triggered,
        )
        self.console.print()
        self.console.print(table)
