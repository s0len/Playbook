from __future__ import annotations

import argparse
from io import StringIO
from typing import List, Tuple

import pytest
from rich.console import Console

from playbook.command_help import (
    COMMAND_HELP,
    CommandHelp,
    get_command_help,
)
from playbook.help_formatter import RichHelpFormatter, render_extended_examples


class TestCommandHelp:
    """Test the CommandHelp dataclass and data integrity."""

    def test_command_help_dataclass_creation(self) -> None:
        """Test that CommandHelp dataclass can be created with valid data."""
        help_content = CommandHelp(
            examples=[("Test example", "playbook run")],
            brief_examples=[("Brief example", "playbook run --dry-run")],
            extended_examples=[("Extended example", "playbook run --verbose")],
            env_vars=[("CONFIG_PATH", "Path to config file")],
            tips=["Always test with --dry-run first"],
        )

        assert len(help_content.examples) == 1
        assert len(help_content.brief_examples) == 1
        assert len(help_content.extended_examples) == 1
        assert len(help_content.env_vars) == 1
        assert len(help_content.tips) == 1

    def test_command_help_empty_defaults(self) -> None:
        """Test that CommandHelp has empty list defaults for all fields."""
        help_content = CommandHelp()

        assert help_content.examples == []
        assert help_content.brief_examples == []
        assert help_content.extended_examples == []
        assert help_content.env_vars == []
        assert help_content.tips == []

    def test_get_command_help_run(self) -> None:
        """Test retrieving help content for 'run' command."""
        help_content = get_command_help("run")

        assert isinstance(help_content, CommandHelp)
        assert len(help_content.brief_examples) > 0
        assert len(help_content.extended_examples) > 0
        assert len(help_content.env_vars) > 0
        assert len(help_content.tips) > 0

    def test_get_command_help_validate_config(self) -> None:
        """Test retrieving help content for 'validate-config' command."""
        help_content = get_command_help("validate-config")

        assert isinstance(help_content, CommandHelp)
        assert len(help_content.brief_examples) > 0
        assert len(help_content.extended_examples) > 0
        assert len(help_content.env_vars) > 0
        assert len(help_content.tips) > 0

    def test_get_command_help_kometa_trigger(self) -> None:
        """Test retrieving help content for 'kometa-trigger' command."""
        help_content = get_command_help("kometa-trigger")

        assert isinstance(help_content, CommandHelp)
        assert len(help_content.brief_examples) > 0
        assert len(help_content.extended_examples) > 0
        assert len(help_content.env_vars) > 0
        assert len(help_content.tips) > 0

    def test_get_command_help_invalid_command(self) -> None:
        """Test that getting help for invalid command raises KeyError."""
        with pytest.raises(KeyError):
            get_command_help("invalid-command")

    def test_command_help_registry_has_all_commands(self) -> None:
        """Test that COMMAND_HELP registry contains all expected commands."""
        expected_commands = ["run", "validate-config", "kometa-trigger"]

        for command in expected_commands:
            assert command in COMMAND_HELP
            assert isinstance(COMMAND_HELP[command], CommandHelp)


class TestRichHelpFormatter:
    """Test the RichHelpFormatter class."""

    def test_formatter_initialization(self) -> None:
        """Test that RichHelpFormatter can be initialized."""
        formatter = RichHelpFormatter(prog="playbook")

        assert formatter is not None
        assert formatter._examples == []
        assert formatter._env_vars == []
        assert formatter._tips == []

    def test_formatter_with_custom_width(self) -> None:
        """Test formatter with custom terminal width."""
        formatter = RichHelpFormatter(prog="playbook", width=80)

        assert formatter is not None
        assert formatter._width == 80

    def test_formatter_add_examples(self) -> None:
        """Test adding examples to the formatter."""
        formatter = RichHelpFormatter(prog="playbook")
        examples = [
            ("Example 1", "playbook run"),
            ("Example 2", "playbook run --dry-run"),
        ]

        formatter.add_examples(examples)

        assert formatter._examples == examples

    def test_formatter_add_environment_variables(self) -> None:
        """Test adding environment variables to the formatter."""
        formatter = RichHelpFormatter(prog="playbook")
        env_vars = [
            ("CONFIG_PATH", "Path to config file"),
            ("DRY_RUN", "Enable dry-run mode"),
        ]

        formatter.add_environment_variables(env_vars)

        assert formatter._env_vars == env_vars

    def test_formatter_add_tips(self) -> None:
        """Test adding tips to the formatter."""
        formatter = RichHelpFormatter(prog="playbook")
        tips = [
            "Always test with --dry-run first",
            "Use --verbose for debugging",
        ]

        formatter.add_tips(tips)

        assert formatter._tips == tips

    def test_formatter_produces_output(self) -> None:
        """Test that RichHelpFormatter produces formatted output."""
        # Create a simple parser
        parser = argparse.ArgumentParser(
            prog="playbook",
            description="Test program",
            formatter_class=RichHelpFormatter,
        )
        parser.add_argument("--dry-run", action="store_true", help="Dry run mode")

        # Get the help output
        help_output = parser.format_help()

        assert help_output is not None
        assert len(help_output) > 0
        assert "playbook" in help_output

    def test_formatter_gracefully_handles_non_tty(self, monkeypatch) -> None:
        """Test that formatter falls back to standard help for non-TTY environments."""
        # Create a formatter with a non-TTY console
        console = Console(file=StringIO(), force_terminal=False)
        formatter = RichHelpFormatter(prog="playbook", console=console)

        # Create a simple parser
        parser = argparse.ArgumentParser(
            prog="playbook",
            description="Test program",
            formatter_class=lambda prog: RichHelpFormatter(prog=prog, console=console),
        )
        parser.add_argument("--dry-run", action="store_true", help="Dry run mode")

        # Get the help output
        help_output = parser.format_help()

        # Should still produce output (fallback to standard argparse)
        assert help_output is not None
        assert len(help_output) > 0
        assert "playbook" in help_output

    def test_formatter_with_examples_and_env_vars(self) -> None:
        """Test formatter with examples and environment variables produces output."""
        console = Console(file=StringIO(), force_terminal=True)
        formatter = RichHelpFormatter(prog="playbook", console=console)

        # Add content
        formatter.add_examples([("Example", "playbook run")])
        formatter.add_environment_variables([("CONFIG_PATH", "Config file path")])
        formatter.add_tips(["Test with --dry-run first"])

        # Create a parser to trigger format_help
        parser = argparse.ArgumentParser(
            prog="playbook",
            description="Test program",
            formatter_class=lambda prog: formatter,
        )

        # Get the help output
        help_output = parser.format_help()

        # Verify output is generated
        assert help_output is not None
        assert len(help_output) > 0


class TestRenderExtendedExamples:
    """Test the render_extended_examples function."""

    def test_render_extended_examples_basic(self) -> None:
        """Test rendering extended examples without errors."""
        console = Console(file=StringIO(), force_terminal=True)
        examples: List[Tuple[str, str]] = [
            ("Basic usage", "playbook run"),
            ("Dry run", "playbook run --dry-run"),
        ]

        # Should not raise any exceptions
        render_extended_examples("run", examples, console=console)

        # Get the captured output
        output = console.file.getvalue()
        assert len(output) > 0

    def test_render_extended_examples_with_docker(self) -> None:
        """Test rendering examples that include Docker commands."""
        console = Console(file=StringIO(), force_terminal=True)
        examples: List[Tuple[str, str]] = [
            ("CLI usage", "playbook run --dry-run"),
            ("Docker usage", "docker run playbook playbook run"),
        ]

        render_extended_examples("run", examples, console=console)

        output = console.file.getvalue()
        assert "Docker" in output or "docker" in output.lower()

    def test_render_extended_examples_with_kubernetes(self) -> None:
        """Test rendering examples that include Kubernetes commands."""
        console = Console(file=StringIO(), force_terminal=True)
        examples: List[Tuple[str, str]] = [
            ("CLI usage", "playbook run --dry-run"),
            ("Kubernetes usage", "kubectl exec pod -- playbook run"),
        ]

        render_extended_examples("run", examples, console=console)

        output = console.file.getvalue()
        assert "Kubernetes" in output or "kubectl" in output.lower()

    def test_render_extended_examples_with_python(self) -> None:
        """Test rendering examples that include Python module commands."""
        console = Console(file=StringIO(), force_terminal=True)
        examples: List[Tuple[str, str]] = [
            ("CLI usage", "playbook run --dry-run"),
            ("Python module", "python -m playbook.cli run"),
        ]

        render_extended_examples("run", examples, console=console)

        output = console.file.getvalue()
        assert "Python" in output or "python" in output.lower()

    def test_render_extended_examples_empty_list(self) -> None:
        """Test rendering with empty examples list."""
        console = Console(file=StringIO(), force_terminal=True)
        examples: List[Tuple[str, str]] = []

        # Should not raise any exceptions
        render_extended_examples("run", examples, console=console)

        output = console.file.getvalue()
        # Should still produce some output (header)
        assert len(output) > 0

    def test_render_extended_examples_mixed_categories(self) -> None:
        """Test rendering examples from multiple categories."""
        console = Console(file=StringIO(), force_terminal=True)
        examples: List[Tuple[str, str]] = [
            ("Basic CLI", "playbook run"),
            ("Docker example", "docker run playbook"),
            ("Kubernetes example", "kubectl exec pod -- playbook"),
            ("Python module", "python -m playbook.cli run"),
        ]

        render_extended_examples("run", examples, console=console)

        output = console.file.getvalue()
        # Should contain sections for different categories
        assert len(output) > 0

    def test_render_extended_examples_uses_console_parameter(self) -> None:
        """Test that render_extended_examples uses provided console."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)
        examples: List[Tuple[str, str]] = [("Test", "playbook run")]

        render_extended_examples("test-command", examples, console=console)

        # Output should be in the provided StringIO
        output = string_io.getvalue()
        assert len(output) > 0
        assert "test-command" in output

    def test_render_extended_examples_creates_console_when_none(self) -> None:
        """Test that render_extended_examples creates console when None provided."""
        examples: List[Tuple[str, str]] = [("Test", "playbook run")]

        # Should not raise any exceptions when console=None
        render_extended_examples("run", examples, console=None)


class TestHelpFormatterIntegration:
    """Integration tests for help formatter with argparse."""

    def test_help_formatter_integrates_with_parser(self) -> None:
        """Test that RichHelpFormatter integrates properly with ArgumentParser."""
        parser = argparse.ArgumentParser(
            prog="playbook",
            description="Playbook CLI",
            formatter_class=RichHelpFormatter,
        )
        parser.add_argument("--config", help="Config file path")
        parser.add_argument("--dry-run", action="store_true", help="Dry run mode")

        help_output = parser.format_help()

        assert "playbook" in help_output
        assert "--config" in help_output
        assert "--dry-run" in help_output

    def test_help_formatter_with_subparsers(self) -> None:
        """Test that RichHelpFormatter works with subparsers."""
        parser = argparse.ArgumentParser(
            prog="playbook",
            formatter_class=RichHelpFormatter,
        )
        subparsers = parser.add_subparsers(dest="command")

        run_parser = subparsers.add_parser(
            "run",
            formatter_class=RichHelpFormatter,
            help="Run the processor",
        )
        run_parser.add_argument("--watch", action="store_true", help="Watch mode")

        # Get main help
        main_help = parser.format_help()
        assert "playbook" in main_help

        # Get subcommand help
        run_help = run_parser.format_help()
        assert "--watch" in run_help

    def test_help_formatter_preserves_argument_groups(self) -> None:
        """Test that RichHelpFormatter preserves argument groups."""
        parser = argparse.ArgumentParser(
            prog="playbook",
            formatter_class=RichHelpFormatter,
        )

        required = parser.add_argument_group("required arguments")
        required.add_argument("--config", required=True, help="Config file")

        optional = parser.add_argument_group("optional arguments")
        optional.add_argument("--dry-run", action="store_true", help="Dry run")

        help_output = parser.format_help()

        # Groups should be present in output
        assert "--config" in help_output
        assert "--dry-run" in help_output
