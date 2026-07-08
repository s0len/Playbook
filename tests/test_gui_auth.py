"""Tests for the opt-in GUI authentication layer."""

from __future__ import annotations

import pytest

pytest.importorskip("nicegui")

from playbook.gui import auth
from playbook.gui.auth import (
    GuiAuthConfig,
    is_public_path,
    resolve_auth_config,
    resolve_storage_secret,
    verify_credentials,
)


@pytest.fixture(autouse=True)
def _clear_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test starts from a known, credential-free environment."""
    for var in ("GUI_USERNAME", "GUI_PASSWORD", "GUI_STORAGE_SECRET"):
        monkeypatch.delenv(var, raising=False)
    # Reset the module-level cache so resolution reflects the patched env.
    auth._AUTH = None


class TestResolveAuthConfig:
    def test_disabled_when_no_password(self) -> None:
        cfg = resolve_auth_config()
        assert cfg.enabled is False
        assert cfg.username == "admin"  # default even when auth is off

    def test_enabled_when_password_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GUI_PASSWORD", "s3cret")
        cfg = resolve_auth_config()
        assert cfg.enabled is True
        assert cfg.username == "admin"
        assert cfg.password == "s3cret"

    def test_custom_username(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GUI_USERNAME", "mattias")
        monkeypatch.setenv("GUI_PASSWORD", "pw")
        cfg = resolve_auth_config()
        assert cfg.username == "mattias"

    def test_empty_password_is_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GUI_PASSWORD", "")
        assert resolve_auth_config().enabled is False


class TestVerifyCredentials:
    cfg = GuiAuthConfig(username="admin", password="hunter2")

    def test_correct(self) -> None:
        assert verify_credentials(self.cfg, "admin", "hunter2") is True

    def test_wrong_password(self) -> None:
        assert verify_credentials(self.cfg, "admin", "nope") is False

    def test_wrong_username(self) -> None:
        assert verify_credentials(self.cfg, "root", "hunter2") is False

    def test_empty_inputs(self) -> None:
        assert verify_credentials(self.cfg, "", "") is False

    def test_none_safe(self) -> None:
        # verify_credentials coerces falsy inputs to "" rather than raising.
        assert verify_credentials(self.cfg, None, None) is False  # type: ignore[arg-type]

    def test_non_ascii_password(self) -> None:
        # hmac.compare_digest rejects non-ASCII str; we compare bytes so this works.
        cfg = GuiAuthConfig(username="admin", password="pÄsswörd-café")
        assert verify_credentials(cfg, "admin", "pÄsswörd-café") is True
        assert verify_credentials(cfg, "admin", "wrong") is False


class TestIsPublicPath:
    @pytest.mark.parametrize("path", ["/login", "/healthz", "/icon.png", "/favicon.ico"])
    def test_public_exact(self, path: str) -> None:
        assert is_public_path(path) is True

    @pytest.mark.parametrize("path", ["/_nicegui/version/1/foo.js", "/static/x.css"])
    def test_public_prefixes(self, path: str) -> None:
        assert is_public_path(path) is True

    @pytest.mark.parametrize("path", ["/", "/config", "/sports", "/api/stats", "/unmatched"])
    def test_protected(self, path: str) -> None:
        assert is_public_path(path) is False


class TestStorageSecret:
    HARDCODED = "playbook-gui-storage"  # the value this change removed

    def test_uses_env_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GUI_STORAGE_SECRET", "operator-supplied")
        assert resolve_storage_secret() == "operator-supplied"

    def test_random_and_not_hardcoded(self) -> None:
        secret = resolve_storage_secret()
        assert secret != self.HARDCODED
        assert len(secret) >= 32

    def test_random_differs_between_calls(self) -> None:
        assert resolve_storage_secret() != resolve_storage_secret()


class TestApplyAuth:
    def test_apply_auth_disabled_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        with caplog.at_level(logging.WARNING, logger="playbook.gui.auth"):
            cfg = auth.apply_auth()
        assert cfg.enabled is False
        assert any("authentication is DISABLED" in r.message for r in caplog.records)
