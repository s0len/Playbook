from __future__ import annotations

import argparse
from pathlib import Path

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
