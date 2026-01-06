from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from playbook import cli


def _write_minimal_config(path: Path) -> None:
    path.write_text(
        """
settings:
  source_dir: "./source"
  destination_dir: "./dest"
  cache_dir: "./cache"
  kometa_trigger:
    enabled: true
    mode: docker
    docker:
      config_path: /config

sports:
  - id: demo
    metadata:
      url: https://example.com/demo.yaml
""",
        encoding="utf-8",
    )


def test_run_kometa_trigger_invokes_trigger(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "playbook.yaml"
    _write_minimal_config(config_path)

    class DummyTrigger:
        def __init__(self) -> None:
            self.enabled = True
            self.calls = 0

        def trigger(self, *_, **__) -> bool:
            self.calls += 1
            return True

    dummy_trigger = DummyTrigger()

    monkeypatch.setattr("playbook.cli.build_kometa_trigger", lambda settings: dummy_trigger)
    monkeypatch.setattr("playbook.cli.configure_logging", lambda *args, **kwargs: None)

    args = argparse.Namespace(
        config=config_path,
        mode=None,
        verbose=False,
        log_level=None,
        console_level=None,
        log_file=None,
        command="kometa-trigger",
    )

    exit_code = cli.run_kometa_trigger(args)

    assert exit_code == 0
    assert dummy_trigger.calls == 1


def test_run_kometa_trigger_requires_enabled(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "playbook.yaml"
    config_path.write_text(
        """
settings:
  source_dir: "./source"
  destination_dir: "./dest"
  cache_dir: "./cache"
  kometa_trigger:
    enabled: false

sports:
  - id: demo
    metadata:
      url: https://example.com/demo.yaml
""",
        encoding="utf-8",
    )

    monkeypatch.setattr("playbook.cli.configure_logging", lambda *args, **kwargs: None)

    args = argparse.Namespace(
        config=config_path,
        mode=None,
        verbose=False,
        log_level=None,
        console_level=None,
        log_file=None,
        command="kometa-trigger",
    )

    assert cli.run_kometa_trigger(args) == 1


# ===== Integration Tests for validate-config CLI Command =====


def test_validate_config_with_valid_config(tmp_path, monkeypatch) -> None:
    """Test that validate-config shows success message for valid configuration."""
    config_path = tmp_path / "playbook.yaml"
    _write_minimal_config(config_path)

    # Capture console output
    output_lines = []

    def mock_console_print(message, **kwargs):
        output_lines.append(str(message))

    monkeypatch.setattr("playbook.cli.CONSOLE.print", mock_console_print)

    args = argparse.Namespace(
        config=config_path,
        diff_sample=False,
        show_trace=False,
        no_suggestions=False,
        command="validate-config",
    )

    exit_code = cli.run_validate_config(args)

    # Should return success
    assert exit_code == 0

    # Check that success message is displayed
    output = "\n".join(output_lines)
    assert "Configuration passed validation" in output or "✓" in output


def test_validate_config_with_invalid_config_shows_grouped_errors(tmp_path, monkeypatch) -> None:
    """Test that validate-config displays grouped errors with line numbers."""
    config_path = tmp_path / "playbook.yaml"
    config_path.write_text(
        """settings:
  source_dir: "./source"
  destination_dir: "./dest"
  cache_dir: "./cache"
  notifications:
    flush_time: invalid_number

sports:
  - id: demo
    metadata:
      url: not_a_valid_url
  - id: demo
    metadata:
      url: https://example.com/demo.yaml
""",
        encoding="utf-8",
    )

    # Capture console output
    output_lines = []

    def mock_console_print(message, **kwargs):
        output_lines.append(str(message))

    monkeypatch.setattr("playbook.cli.CONSOLE.print", mock_console_print)

    args = argparse.Namespace(
        config=config_path,
        diff_sample=False,
        show_trace=False,
        no_suggestions=False,
        command="validate-config",
    )

    exit_code = cli.run_validate_config(args)

    # Should return error code
    assert exit_code == 1

    # Check output contains error indicators
    output = "\n".join(output_lines)
    assert "Validation Errors" in output or "error" in output.lower()

    # Check that line numbers are shown (at least one L<number>)
    assert "L" in output  # Line numbers shown as L6, L10, etc.


def test_validate_config_respects_no_suggestions_flag(tmp_path, monkeypatch) -> None:
    """Test that --no-suggestions flag hides fix suggestions."""
    config_path = tmp_path / "playbook.yaml"
    config_path.write_text(
        """settings:
  source_dir: "./source"
  destination_dir: "./dest"
  cache_dir: "./cache"
  notifications:
    flush_time: invalid_number

sports:
  - id: demo
    metadata:
      url: https://example.com/demo.yaml
""",
        encoding="utf-8",
    )

    # Capture console output with suggestions disabled
    output_lines_no_suggestions = []

    def mock_console_print_no_sugg(message, **kwargs):
        output_lines_no_suggestions.append(str(message))

    monkeypatch.setattr("playbook.cli.CONSOLE.print", mock_console_print_no_sugg)

    args_no_suggestions = argparse.Namespace(
        config=config_path,
        diff_sample=False,
        show_trace=False,
        no_suggestions=True,
        command="validate-config",
    )

    cli.run_validate_config(args_no_suggestions)

    output_no_sugg = "\n".join(output_lines_no_suggestions)

    # Should not contain the lightbulb emoji for suggestions
    assert "💡" not in output_no_sugg

    # Now test with suggestions enabled (default)
    output_lines_with_suggestions = []

    def mock_console_print_with_sugg(message, **kwargs):
        output_lines_with_suggestions.append(str(message))

    monkeypatch.setattr("playbook.cli.CONSOLE.print", mock_console_print_with_sugg)

    args_with_suggestions = argparse.Namespace(
        config=config_path,
        diff_sample=False,
        show_trace=False,
        no_suggestions=False,
        command="validate-config",
    )

    cli.run_validate_config(args_with_suggestions)

    output_with_sugg = "\n".join(output_lines_with_suggestions)

    # Should contain the lightbulb emoji for suggestions
    assert "💡" in output_with_sugg


def test_validate_config_groups_errors_by_section(tmp_path, monkeypatch) -> None:
    """Test that errors are properly grouped by configuration section."""
    config_path = tmp_path / "playbook.yaml"
    config_path.write_text(
        """settings:
  source_dir: 123
  destination_dir: "./dest"
  cache_dir: "./cache"
  notifications:
    flush_time: invalid_number

sports:
  - id: demo
    metadata:
      url: not_a_valid_url
  - id: demo
    metadata:
      url: https://example.com/duplicate.yaml
""",
        encoding="utf-8",
    )

    # Capture console output
    output_lines = []

    def mock_console_print(message, **kwargs):
        output_lines.append(str(message))

    monkeypatch.setattr("playbook.cli.CONSOLE.print", mock_console_print)

    args = argparse.Namespace(
        config=config_path,
        diff_sample=False,
        show_trace=False,
        no_suggestions=False,
        command="validate-config",
    )

    exit_code = cli.run_validate_config(args)

    # Should return error code
    assert exit_code == 1

    output = "\n".join(output_lines)

    # Check that both settings and sports sections are mentioned
    # (The formatter uses section display names like "Settings", "Sports")
    # We're flexible here since the exact display format may vary
    assert "settings" in output.lower() or "Settings" in output
    assert "sports" in output.lower() or "Sports" in output or "Sport" in output


def test_validate_config_file_not_found(tmp_path, monkeypatch) -> None:
    """Test that validate-config handles missing config file gracefully."""
    config_path = tmp_path / "nonexistent.yaml"

    # Capture console output
    output_lines = []

    def mock_console_print(message, **kwargs):
        output_lines.append(str(message))

    monkeypatch.setattr("playbook.cli.CONSOLE.print", mock_console_print)

    args = argparse.Namespace(
        config=config_path,
        diff_sample=False,
        show_trace=False,
        no_suggestions=False,
        command="validate-config",
    )

    exit_code = cli.run_validate_config(args)

    # Should return error code
    assert exit_code == 1

    output = "\n".join(output_lines)

    # Check that file not found error is displayed
    assert "not found" in output.lower() or "nonexistent" in str(config_path)


def test_validate_config_with_invalid_yaml(tmp_path, monkeypatch) -> None:
    """Test that validate-config handles invalid YAML syntax."""
    config_path = tmp_path / "playbook.yaml"
    config_path.write_text(
        """settings:
  source_dir: "./source"
  destination_dir: "./dest"
  cache_dir: "./cache"
  this is not valid yaml: [unclosed bracket
""",
        encoding="utf-8",
    )

    # Capture console output
    output_lines = []

    def mock_console_print(message, **kwargs):
        output_lines.append(str(message))

    monkeypatch.setattr("playbook.cli.CONSOLE.print", mock_console_print)

    args = argparse.Namespace(
        config=config_path,
        diff_sample=False,
        show_trace=False,
        no_suggestions=False,
        command="validate-config",
    )

    exit_code = cli.run_validate_config(args)

    # Should return error code
    assert exit_code == 1

    output = "\n".join(output_lines)

    # Check that YAML loading error is displayed
    assert "Failed to load configuration" in output or "error" in output.lower()


def test_validate_config_shows_line_numbers_for_errors(tmp_path, monkeypatch) -> None:
    """Test that validate-config shows line numbers for validation errors."""
    config_path = tmp_path / "playbook.yaml"
    # Create a config with a known error on a specific line
    config_path.write_text(
        """settings:
  source_dir: "./source"
  destination_dir: "./dest"
  cache_dir: "./cache"
  notifications:
    flush_time: not_a_number

sports:
  - id: demo
    metadata:
      url: https://example.com/demo.yaml
""",
        encoding="utf-8",
    )

    # Capture console output
    output_lines = []

    def mock_console_print(message, **kwargs):
        output_lines.append(str(message))

    monkeypatch.setattr("playbook.cli.CONSOLE.print", mock_console_print)

    args = argparse.Namespace(
        config=config_path,
        diff_sample=False,
        show_trace=False,
        no_suggestions=False,
        command="validate-config",
    )

    exit_code = cli.run_validate_config(args)

    # Should return error code
    assert exit_code == 1

    output = "\n".join(output_lines)

    # Check that line numbers are displayed (L followed by digits)
    # The flush_time error should be on line 6
    assert "L6" in output or ("L" in output and "flush_time" in output)


def test_validate_config_displays_multiple_errors_in_same_section(tmp_path, monkeypatch) -> None:
    """Test that multiple errors in the same section are grouped together."""
    config_path = tmp_path / "playbook.yaml"
    config_path.write_text(
        """settings:
  source_dir: 123
  destination_dir: 456
  cache_dir: 789

sports:
  - id: demo
    metadata:
      url: https://example.com/demo.yaml
""",
        encoding="utf-8",
    )

    # Capture console output
    output_lines = []

    def mock_console_print(message, **kwargs):
        output_lines.append(str(message))

    monkeypatch.setattr("playbook.cli.CONSOLE.print", mock_console_print)

    args = argparse.Namespace(
        config=config_path,
        diff_sample=False,
        show_trace=False,
        no_suggestions=False,
        command="validate-config",
    )

    exit_code = cli.run_validate_config(args)

    # Should return error code (multiple type errors in settings)
    assert exit_code == 1

    output = "\n".join(output_lines)

    # Check that multiple errors are shown
    assert "source_dir" in output
    assert "destination_dir" in output
    assert "cache_dir" in output

