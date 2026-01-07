from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .validation import (
    ValidationIssue,
    ValidationReport,
    get_section_display_name,
    group_validation_issues,
)


class ValidationFormatter:
    """Formats validation reports with rich, grouped output.

    This class provides methods to format ValidationReport objects with
    grouped sections, line numbers, and fix suggestions using the Rich library.
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        show_suggestions: bool = True,
        config_data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the ValidationFormatter.

        Args:
            console: Rich Console instance to use for output. If None, creates a new one.
            show_suggestions: Whether to display fix suggestions in the output.
            config_data: Optional configuration data for extracting display names.
        """
        self.console = console or Console()
        self.show_suggestions = show_suggestions
        self.config_data = config_data

    def format_report(self, report: ValidationReport) -> None:
        """Format and display a complete validation report.

        Args:
            report: The ValidationReport to format and display.
        """
        # Display errors if present
        if report.errors:
            self._format_issues(
                issues=report.errors,
                severity="error",
                header_text="Validation Errors",
                header_style="bold red",
            )

        # Display warnings if present
        if report.warnings:
            self._format_issues(
                issues=report.warnings,
                severity="warning",
                header_text="Validation Warnings",
                header_style="bold yellow",
            )

        # Display success message if no errors
        if not report.errors and not report.warnings:
            self.console.print("[bold green]✓ Configuration passed validation.[/bold green]")
        elif not report.errors:
            self.console.print("[bold green]✓ Configuration passed validation (with warnings).[/bold green]")

    def _format_issues(
        self,
        issues: List[ValidationIssue],
        severity: str,
        header_text: str,
        header_style: str,
    ) -> None:
        """Format and display a list of validation issues grouped by section.

        Args:
            issues: List of ValidationIssue objects to format.
            severity: The severity level ("error" or "warning").
            header_text: Text to display in the main header.
            header_style: Rich style string for the header.
        """
        # Print header with count
        count_text = f"{len(issues)} {severity}(s) detected"
        self.console.print(f"\n[{header_style}]{header_text}: {count_text}[/{header_style}]")

        # Group issues by section
        grouped = group_validation_issues(issues)

        # Display each root section
        for root_section, sub_sections in grouped.items():
            self._format_section(root_section, sub_sections, severity)

    def _format_section(
        self,
        root_section: str,
        sub_sections: Dict[str, List[ValidationIssue]],
        severity: str,
    ) -> None:
        """Format and display a single section with its sub-sections.

        Args:
            root_section: The root section name (e.g., "settings", "sports").
            sub_sections: Dictionary mapping sub-section names to issues.
            severity: The severity level ("error" or "warning").
        """
        # Use display name for the root section
        section_display = get_section_display_name(root_section, self.config_data)

        # Create renderables for all sub-sections
        renderables: List[RenderableType] = []

        for sub_section, section_issues in sub_sections.items():
            # Get display name for sub-section
            subsection_display = get_section_display_name(sub_section, self.config_data)

            # Create a table for this sub-section's issues
            table = self._create_issues_table(section_issues, severity)

            # Add sub-section header if it differs from root section
            if sub_section != root_section:
                header = Text(f"→ {subsection_display}", style="bold cyan")
                renderables.append(header)

            renderables.append(table)

        # Create panel with all renderables
        panel_style = "red" if severity == "error" else "yellow"
        panel_title = f"[bold]{section_display}[/bold]"

        panel = Panel(
            Group(*renderables),
            title=panel_title,
            border_style=panel_style,
            padding=(1, 2),
        )

        self.console.print(panel)

    def _create_issues_table(
        self,
        issues: List[ValidationIssue],
        severity: str,
    ) -> Table:
        """Create a Rich table for a list of validation issues.

        Args:
            issues: List of ValidationIssue objects to display.
            severity: The severity level ("error" or "warning").

        Returns:
            A Rich Table object formatted with the issues.
        """
        # Create table with appropriate styling
        table = Table(
            show_header=False,
            show_edge=False,
            pad_edge=False,
            box=None,
            padding=(0, 1),
        )

        # Add columns
        table.add_column("Line", style="dim", width=6, no_wrap=True)
        table.add_column("Path", style="cyan", overflow="fold")
        table.add_column("Message", overflow="fold")

        # Add rows for each issue
        for issue in issues:
            # Format line number
            line_str = f"L{issue.line_number}" if issue.line_number else "—"

            # Format path (remove redundant prefixes for readability)
            path = self._format_path(issue.path)

            # Format message with error code
            message_text = f"{issue.message}"
            if issue.code:
                message_text += f" [dim]({issue.code})[/dim]"

            # Add the main issue row
            table.add_row(line_str, path, message_text)

            # Add fix suggestion if available and enabled
            if self.show_suggestions and issue.fix_suggestion:
                # Add suggestion as a nested row with special styling
                suggestion_text = Text()
                suggestion_text.append("💡 ", style="yellow")
                suggestion_text.append(issue.fix_suggestion, style="italic dim")

                table.add_row("", "", suggestion_text)

        return table

    def _format_path(self, path: str) -> str:
        """Format a path string for display by removing redundant prefixes.

        Args:
            path: The full path string from the ValidationIssue.

        Returns:
            A formatted path string with redundant parts removed.
        """
        # For paths like "settings.notifications.flush_time", we want to show
        # just "notifications.flush_time" when displayed under Settings section
        # For now, just return the path as-is (can be enhanced later)
        return path


__all__ = [
    "ValidationFormatter",
]
