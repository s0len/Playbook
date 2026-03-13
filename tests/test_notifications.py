from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from playbook.config import NotificationSettings
from playbook.notifications import NotificationEvent, NotificationService


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = json.dumps(payload) if payload is not None else ""

    def json(self) -> dict[str, Any]:
        if self._payload is None:
            raise ValueError("No JSON payload")
        return self._payload


def _build_event(
    destination: str = "Demo.mkv",
    action: str = "link",
    event_type: str = "new",
    match_details: dict[str, Any] | None = None,
) -> NotificationEvent:
    return NotificationEvent(
        sport_id="demo",
        sport_name="Demo Sport",
        show_title="Demo Series",
        season="Season 1",
        session="Qualifying",
        episode="Qualifying",
        summary="Session summary",
        destination=destination,
        source="source.mkv",
        action=action,
        link_mode="hardlink",
        timestamp=dt.datetime.now(dt.UTC),
        event_type=event_type,
        match_details=match_details or {},
    )


_DEFAULT_TARGET = {"type": "discord", "webhook_url": "https://discord.test/webhook"}


def test_notification_service_sends_discord_message(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: list[dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    service.notify(_build_event())

    assert len(calls) == 1
    request = calls[0]
    assert request["method"] == "POST"
    assert request["url"] == "https://discord.test/webhook"
    payload = request["json"]
    assert payload["embeds"][0]["fields"][0]["value"] == "Demo Sport"
    assert payload["content"] == "[NEW] Demo Sport: Qualifying"
    embed = payload["embeds"][0]
    assert "description" not in embed
    field_names = [field["name"] for field in embed["fields"]]
    assert "Session" not in field_names
    assert "Action" not in field_names
    destination_field = next(field for field in embed["fields"] if field["name"] == "Destination")
    assert destination_field["value"] == "Demo"


def test_notification_service_mentions_opt_in_roles(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        mentions={"demo": "<@&42>"},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: list[dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    service.notify(_build_event())

    payload = calls[0]["json"]
    assert payload["content"].startswith("<@&42> [NEW] Demo Sport: Qualifying")


def test_bare_role_id_auto_wrapped_in_mention_format(tmp_path, monkeypatch) -> None:
    """Bare numeric Discord IDs should be auto-wrapped as <@&ID> role mentions."""
    settings = NotificationSettings(
        mentions={"demo": "123456789"},  # bare ID, no <@&...> wrapper
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: list[dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    service.notify(_build_event())

    payload = calls[0]["json"]
    # Should have been auto-wrapped from "123456789" to "<@&123456789>"
    assert "<@&123456789>" in payload["content"]


def test_normalize_mention_function() -> None:
    from playbook.notifications.utils import normalize_mention

    # Bare numeric ID -> role mention
    assert normalize_mention("123456789") == "<@&123456789>"
    # Already formatted -> unchanged
    assert normalize_mention("<@&123456789>") == "<@&123456789>"
    assert normalize_mention("<@123456789>") == "<@123456789>"
    assert normalize_mention("<#123456789>") == "<#123456789>"
    # @here / @everyone -> unchanged
    assert normalize_mention("@here") == "@here"
    assert normalize_mention("@everyone") == "@everyone"
    # Whitespace trimmed
    assert normalize_mention("  123456789  ") == "<@&123456789>"


def test_notification_service_mentions_handle_variant_ids(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        mentions={"premier_league": "<@&123>"},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: list[dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    event = _build_event()
    event.sport_id = "premier_league_2025_26"
    service.notify(event)

    payload = calls[0]["json"]
    assert payload["content"].startswith("<@&123> [NEW]")


def test_notification_service_mentions_support_wildcards(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        mentions={"formula1_*": "<@&999>", "default": "@here"},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: list[dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    event = _build_event()
    event.sport_id = "formula1_2025"
    service.notify(event)

    payload = calls[0]["json"]
    assert payload["content"].startswith("<@&999> [NEW]")


def test_notification_service_throttle_supports_variant_ids(tmp_path) -> None:
    settings = NotificationSettings(
        throttle={"premier_league": 30, "default": 60},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    assert service._resolve_throttle("premier_league_2025_26") == 30


def test_notification_service_throttle_supports_wildcards(tmp_path) -> None:
    settings = NotificationSettings(
        throttle={"formula1_*": 12, "default": 60},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    assert service._resolve_throttle("formula1_2026") == 12


def test_notification_service_throttle_prefers_specific_wildcard(tmp_path) -> None:
    settings = NotificationSettings(
        throttle={"formula1_*": 12, "formula1_2025*": 25, "default": 60},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    assert service._resolve_throttle("formula1_2025_sprint") == 25


def test_notification_service_throttle_applies_default_and_sport_limit(tmp_path) -> None:
    settings = NotificationSettings(
        throttle={"formula1": 25, "default": 10},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    assert service._resolve_throttle("formula1") == 10


def test_notification_service_throttle_limits_notifications_per_day(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        throttle={"demo": 1},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: list[dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    first = _build_event()
    first.timestamp = dt.datetime(2026, 3, 6, 9, 0, tzinfo=dt.UTC)
    second = _build_event(destination="Demo-2.mkv")
    second.timestamp = dt.datetime(2026, 3, 6, 10, 0, tzinfo=dt.UTC)

    service.notify(first)
    service.notify(second)

    assert len(calls) == 1


def test_notification_service_throttle_resets_next_day(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        throttle={"demo": 1},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: list[dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    first = _build_event()
    first.timestamp = dt.datetime(2026, 3, 6, 9, 0, tzinfo=dt.UTC)
    second = _build_event(destination="Demo-next-day.mkv")
    second.timestamp = dt.datetime(2026, 3, 7, 9, 0, tzinfo=dt.UTC)

    service.notify(first)
    service.notify(second)

    assert len(calls) == 2


def test_discord_target_reads_webhook_from_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PLAYBOOK_DISCORD_WEBHOOK", "https://discord.test/env")
    settings = NotificationSettings(
        targets=[{"type": "discord", "webhook_env": "PLAYBOOK_DISCORD_WEBHOOK"}],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: list[dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    service.notify(_build_event())

    assert calls and calls[0]["url"] == "https://discord.test/env"


def test_discord_target_skips_when_env_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PLAYBOOK_DISCORD_WEBHOOK", raising=False)
    settings = NotificationSettings(
        targets=[{"type": "discord", "webhook_env": "PLAYBOOK_DISCORD_WEBHOOK"}],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    def fake_request(method, url, json=None, timeout=None, headers=None):
        raise AssertionError("Request should not be sent when env var is missing")

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    service.notify(_build_event())


def test_discord_targets_support_per_target_mentions(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        mentions={"default": "@here"},
        targets=[
            {
                "type": "discord",
                "webhook_url": "https://discord.test/a",
                "mentions": {"demo": " <@&1> "},
            },
            {
                "type": "discord",
                "webhook_url": "https://discord.test/b",
            },
        ],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: list[dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    service.notify(_build_event())

    by_url = {call["url"]: call["json"]["content"] for call in calls}
    assert by_url["https://discord.test/a"].startswith("<@&1>")
    assert by_url["https://discord.test/b"].startswith("@here")


def test_notification_service_handles_rate_limiting(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    responses = [
        FakeResponse(429, {"retry_after": 0.3}, headers={"Retry-After": "0.2"}),
        FakeResponse(204),
    ]
    request_calls: list[str] = []
    sleep_calls: list[float] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        request_calls.append(method)
        return responses.pop(0)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)
    monkeypatch.setattr("playbook.notifications.discord.time.sleep", lambda seconds: sleep_calls.append(seconds))

    service.notify(_build_event())

    assert request_calls == ["POST", "POST"]
    assert sleep_calls and sleep_calls[0] >= 1.0


def test_notification_service_skips_non_new_events(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    def fake_request(method, url, json=None, timeout=None, headers=None):
        raise AssertionError("Request should not be sent")

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)
    service.notify(_build_event(event_type="refresh"))


def test_autoscan_target_posts_manual_trigger(tmp_path, monkeypatch) -> None:
    rewrite_from = str(tmp_path / "dest")
    settings = NotificationSettings(
        targets=[
            {
                "type": "autoscan",
                "url": "http://autoscan.test:3030",
                "rewrite": [
                    {
                        "from": rewrite_from,
                        "to": "/mnt/unionfs",
                    }
                ],
            }
        ],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: list[dict[str, Any]] = []

    def fake_post(url, params=None, auth=None, timeout=None, verify=None):
        calls.append({"url": url, "params": params, "auth": auth, "timeout": timeout, "verify": verify})

        class _Response:
            status_code = 200
            text = ""

        return _Response()

    monkeypatch.setattr("playbook.notifications.autoscan.requests.post", fake_post)

    destination_file = Path(rewrite_from) / "Show" / "Episode.mkv"
    event = _build_event(
        match_details={"destination_path": str(destination_file)},
    )
    service.notify(event)

    assert len(calls) == 1
    request = calls[0]
    assert request["url"] == "http://autoscan.test:3030/triggers/manual"
    assert ("dir", "/mnt/unionfs/Show") in request["params"]
    assert request["auth"] is None


def test_disabled_target_does_not_send_notifications(tmp_path, monkeypatch) -> None:
    """Targets with enabled=False should not send notifications."""
    settings = NotificationSettings(
        targets=[
            {"type": "discord", "webhook_url": "https://discord.test/webhook", "enabled": False},
        ],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    def fake_request(method, url, json=None, timeout=None, headers=None):
        raise AssertionError("Request should not be sent when target is disabled")

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    # Should not raise because target is disabled
    service.notify(_build_event())
