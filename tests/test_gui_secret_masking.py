"""Tests for GUI secret masking (fix #4).

The critical invariant: stored secrets are never sent to the browser, and a
blank password field on save must NOT overwrite the existing secret.
"""

from __future__ import annotations

import pytest

pytest.importorskip("nicegui")

from playbook.gui.components.settings.form_renderer import (
    apply_field_change,
    secret_display_value,
)


class TestSecretDisplayValue:
    def test_password_with_value_renders_blank(self) -> None:
        assert secret_display_value("SUPERSECRET", is_password=True) == ""

    def test_password_empty_renders_blank(self) -> None:
        assert secret_display_value("", is_password=True) == ""

    def test_text_renders_current_value(self) -> None:
        assert secret_display_value("https://plex.local", is_password=False) == "https://plex.local"

    def test_text_empty_renders_blank(self) -> None:
        assert secret_display_value("", is_password=False) == ""

    def test_text_coerces_non_str(self) -> None:
        assert secret_display_value(587, is_password=False) == "587"


class TestApplyFieldChange:
    def test_blank_password_skipped(self) -> None:
        assert apply_field_change("", is_password=True) is False

    def test_nonblank_password_applied(self) -> None:
        assert apply_field_change("new-secret", is_password=True) is True

    def test_blank_text_applied(self) -> None:
        # Non-secret fields can be cleared.
        assert apply_field_change("", is_password=False) is True

    def test_nonblank_text_applied(self) -> None:
        assert apply_field_change("value", is_password=False) is True


class TestSaveFlowInvariant:
    """Simulate the render → edit → save flow on a `working` dict."""

    def _simulate_change(self, working: dict, key: str, new_value: str, is_password: bool) -> None:
        if apply_field_change(new_value, is_password):
            working[key] = new_value

    def test_untouched_secret_preserved(self) -> None:
        working = {"token": "SECRET"}
        # Field renders blank...
        assert secret_display_value(working["token"], True) == ""
        # ...user submits without retyping (blank change).
        self._simulate_change(working, "token", "", is_password=True)
        assert working["token"] == "SECRET"

    def test_new_secret_written(self) -> None:
        working = {"token": "SECRET"}
        self._simulate_change(working, "token", "ROTATED", is_password=True)
        assert working["token"] == "ROTATED"

    def test_text_field_can_be_cleared(self) -> None:
        working = {"url": "https://old.example"}
        self._simulate_change(working, "url", "", is_password=False)
        assert working["url"] == ""
