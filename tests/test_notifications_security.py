"""Security-hardening tests: log redaction, SMTP TLS, artwork URL scheme."""

from __future__ import annotations

import datetime as dt
import logging

import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError

from playbook.notifications import NotificationEvent
from playbook.notifications.slack import SlackTarget
from playbook.notifications.utils import redact_url
from playbook.notifications.webhook import GenericWebhookTarget


def _event() -> NotificationEvent:
    return NotificationEvent(
        sport_id="demo",
        sport_name="Demo",
        show_title="Demo",
        season="S1",
        session="Q",
        episode="Q",
        summary="",
        destination="d.mkv",
        source="s.mkv",
        action="link",
        link_mode="hardlink",
        timestamp=dt.datetime.now(dt.UTC),
        event_type="new",
    )


class TestRedactUrl:
    def test_strips_path_and_query(self) -> None:
        assert redact_url("https://discord.com/api/webhooks/123/SECRETTOKEN") == "https://discord.com/…"

    def test_keeps_port(self) -> None:
        assert redact_url("http://ntfy.local:8080/topic?token=abc") == "http://ntfy.local:8080/…"

    def test_none(self) -> None:
        assert redact_url(None) == "<none>"

    def test_garbage(self) -> None:
        assert redact_url("not a url") == "<redacted-url>"

    def test_malformed_port_does_not_raise(self) -> None:
        # A non-numeric port must not raise out of the redactor (it runs in an
        # error-logging path); return the safe sentinel instead.
        assert redact_url("http://host:notaport/hook") == "<redacted-url>"

    def test_ipv6_host_keeps_brackets(self) -> None:
        assert redact_url("http://[::1]:9000/x") == "http://[::1]:9000/…"


class TestWebhookLogRedaction:
    def test_connection_failure_does_not_log_token(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        url = "https://hooks.example.com/services/T00/B11/SUPERSECRETTOKEN"
        target = GenericWebhookTarget(url)

        def boom(*_a, **_k):
            raise RequestsConnectionError(f"Max retries exceeded with url: {url}")

        monkeypatch.setattr("playbook.notifications.webhook.requests.request", boom)
        with caplog.at_level(logging.WARNING, logger="playbook.notifications.webhook"):
            target.send(_event())

        assert "SUPERSECRETTOKEN" not in caplog.text
        assert "hooks.example.com" in caplog.text


class TestSlackLogRedaction:
    def test_connection_failure_does_not_log_token(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        url = "https://hooks.slack.com/services/T00/B11/SLACKSECRET"
        target = SlackTarget(url)

        def boom(*_a, **_k):
            raise RequestsConnectionError(f"Max retries exceeded with url: {url}")

        monkeypatch.setattr("playbook.notifications.slack.requests.post", boom)
        with caplog.at_level(logging.WARNING, logger="playbook.notifications.slack"):
            target.send(_event())

        assert "SLACKSECRET" not in caplog.text
        assert "hooks.slack.com" in caplog.text


class TestSmtpTlsVerification:
    def test_starttls_uses_verifying_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import ssl

        from playbook.notifications.email import EmailTarget

        recorded: dict[str, object] = {}

        class FakeSMTP:
            def __init__(self, *_a, **_k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def starttls(self, context=None):
                recorded["context"] = context

            def login(self, *_a):
                recorded["logged_in"] = True

            def send_message(self, *_a):
                recorded["sent"] = True

        monkeypatch.setattr("playbook.notifications.email.smtplib.SMTP", FakeSMTP)

        target = EmailTarget(
            {
                "smtp": {
                    "host": "smtp.example.com",
                    "port": 587,
                    "username": "u",
                    "password": "p",
                    "use_tls": True,
                },
                "from": "a@example.com",
                "to": ["b@example.com"],
            }
        )
        target.send(_event())

        ctx = recorded.get("context")
        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.check_hostname is True
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert recorded.get("sent") is True


class TestResolveAssetUrlScheme:
    BASE = "https://api.tvsportsdb.com/metadata/ufc/2025.yaml"

    def test_rejects_file_scheme(self) -> None:
        from playbook.plex_metadata_sync import _resolve_asset_url

        assert _resolve_asset_url(self.BASE, "file:///etc/passwd") is None

    def test_allows_https(self) -> None:
        from playbook.plex_metadata_sync import _resolve_asset_url

        assert _resolve_asset_url(self.BASE, "https://cdn.example.com/p.jpg") == "https://cdn.example.com/p.jpg"

    def test_allows_http(self) -> None:
        from playbook.plex_metadata_sync import _resolve_asset_url

        assert _resolve_asset_url(self.BASE, "http://cdn.example.com/p.jpg") == "http://cdn.example.com/p.jpg"

    def test_resolves_relative_to_https_base(self) -> None:
        from playbook.plex_metadata_sync import _resolve_asset_url

        assert _resolve_asset_url(self.BASE, "posters/p.jpg") == "https://api.tvsportsdb.com/metadata/ufc/posters/p.jpg"

    def test_none_value(self) -> None:
        from playbook.plex_metadata_sync import _resolve_asset_url

        assert _resolve_asset_url(self.BASE, None) is None
