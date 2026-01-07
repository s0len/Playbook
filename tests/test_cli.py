from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from unittest import mock

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


# =============================================================================
# Help Tests
# =============================================================================


def test_main_help_succeeds() -> None:
    """Test that 'playbook --help' succeeds and shows help output."""
    with pytest.raises(SystemExit) as exc_info:
        cli.parse_args(["--help"])

    # argparse exits with code 0 for --help
    assert exc_info.value.code == 0


def test_run_help_shows_examples(capsys) -> None:
    """Test that 'playbook run --help' shows brief examples."""
    with pytest.raises(SystemExit) as exc_info:
        cli.parse_args(["run", "--help"])

    assert exc_info.value.code == 0

    # Capture output
    captured = capsys.readouterr()
    help_output = captured.out

    # Verify that brief examples are present
    # Check for "Examples" section header (with emoji)
    assert "Examples" in help_output or "EXAMPLES" in help_output

    # Check for at least one example command from brief_examples
    assert "playbook run --dry-run" in help_output or "dry-run" in help_output


def test_validate_config_help_shows_examples(capsys) -> None:
    """Test that 'playbook validate-config --help' shows brief examples."""
    with pytest.raises(SystemExit) as exc_info:
        cli.parse_args(["validate-config", "--help"])

    assert exc_info.value.code == 0

    # Capture output
    captured = capsys.readouterr()
    help_output = captured.out

    # Verify that brief examples are present
    assert "Examples" in help_output or "EXAMPLES" in help_output

    # Check for validate-config specific content
    assert "validate-config" in help_output


def test_kometa_trigger_help_shows_examples(capsys) -> None:
    """Test that 'playbook kometa-trigger --help' shows brief examples."""
    with pytest.raises(SystemExit) as exc_info:
        cli.parse_args(["kometa-trigger", "--help"])

    assert exc_info.value.code == 0

    # Capture output
    captured = capsys.readouterr()
    help_output = captured.out

    # Verify that brief examples are present
    assert "Examples" in help_output or "EXAMPLES" in help_output

    # Check for kometa-trigger specific content
    assert "kometa-trigger" in help_output


def test_run_examples_flag_shows_extended_content(tmp_path, monkeypatch) -> None:
    """Test that 'playbook run --examples' shows extended examples."""
    # Mock config to avoid needing a real config file
    config_path = tmp_path / "playbook.yaml"
    _write_minimal_config(config_path)

    # Capture console output
    output = io.StringIO()

    with mock.patch("playbook.cli.CONSOLE") as mock_console:
        # Mock console to capture output
        mock_console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n")

        result = cli.main(["run", "--examples", "--config", str(config_path)])

    # Should exit with code 0 after showing examples
    assert result == 0

    # Verify extended examples were shown
    output_text = output.getvalue()

    # Extended examples should include more content than brief examples
    # Check for typical extended example categories
    assert "CLI" in output_text or "Docker" in output_text or "examples" in output_text.lower()


def test_validate_config_examples_flag_shows_extended_content(tmp_path, monkeypatch) -> None:
    """Test that 'playbook validate-config --examples' shows extended examples."""
    config_path = tmp_path / "playbook.yaml"
    _write_minimal_config(config_path)

    # Capture console output
    output = io.StringIO()

    with mock.patch("playbook.cli.CONSOLE") as mock_console:
        mock_console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n")

        result = cli.main(["validate-config", "--examples", "--config", str(config_path)])

    assert result == 0

    output_text = output.getvalue()

    # Check for validate-config specific extended examples
    assert "validate-config" in output_text or "examples" in output_text.lower()


def test_kometa_trigger_examples_flag_shows_extended_content(tmp_path, monkeypatch) -> None:
    """Test that 'playbook kometa-trigger --examples' shows extended examples."""
    config_path = tmp_path / "playbook.yaml"
    _write_minimal_config(config_path)

    # Capture console output
    output = io.StringIO()

    with mock.patch("playbook.cli.CONSOLE") as mock_console:
        mock_console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n")

        result = cli.main(["kometa-trigger", "--examples", "--config", str(config_path)])

    assert result == 0

    output_text = output.getvalue()

    # Check for kometa-trigger specific extended examples
    assert "kometa-trigger" in output_text or "examples" in output_text.lower()


def test_help_includes_environment_variables(capsys) -> None:
    """Test that help output includes environment variables section."""
    with pytest.raises(SystemExit):
        cli.parse_args(["run", "--help"])

    captured = capsys.readouterr()
    help_output = captured.out

    # Check for environment variables section
    assert "Environment" in help_output or "ENVIRONMENT" in help_output


def test_help_includes_tips(capsys) -> None:
    """Test that help output includes tips section."""
    with pytest.raises(SystemExit):
        cli.parse_args(["run", "--help"])

    captured = capsys.readouterr()
    help_output = captured.out

    # Check for tips section
    assert "Tips" in help_output or "TIPS" in help_output or "Tip" in help_output


def test_help_mentions_examples_flag(capsys) -> None:
    """Test that help output mentions the --examples flag for more details."""
    with pytest.raises(SystemExit):
        cli.parse_args(["run", "--help"])

    captured = capsys.readouterr()
    help_output = captured.out

    # Help should mention --examples flag
    assert "--examples" in help_output

