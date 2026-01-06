from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from playbook.config import NotificationSettings
from playbook.notifications import NotificationEvent, NotificationService


class FakeResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = json.dumps(payload) if payload is not None else ""

    def json(self) -> Dict[str, Any]:
        if self._payload is None:
            raise ValueError("No JSON payload")
        return self._payload


def _build_event(
    destination: str = "Demo.mkv",
    action: str = "link",
    event_type: str = "new",
    match_details: Optional[Dict[str, Any]] = None,
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
        timestamp=dt.datetime.now(dt.timezone.utc),
        event_type=event_type,
        match_details=match_details or {},
    )


_DEFAULT_TARGET = {"type": "discord", "webhook_url": "https://discord.test/webhook"}


def test_notification_service_sends_discord_message(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        batch_daily=False,
        flush_time=dt.time(hour=0, minute=0),
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: List[Dict[str, Any]] = []

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
        batch_daily=False,
        flush_time=dt.time(hour=0, minute=0),
        mentions={"demo": "<@&42>"},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: List[Dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    service.notify(_build_event())

    payload = calls[0]["json"]
    assert payload["content"].startswith("<@&42> [NEW] Demo Sport: Qualifying")


def test_notification_service_batches_discord_messages(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        batch_daily=True,
        flush_time=dt.time(hour=0, minute=0),
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    responses = [
        FakeResponse(200, {"id": "message123"}),
        FakeResponse(200, {"id": "message123"}),
    ]
    calls: List[Dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return responses.pop(0)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    service.notify(_build_event(destination="Demo-1.mkv"))
    service.notify(_build_event(destination="Demo-2.mkv"))

    assert [call["method"] for call in calls] == ["POST", "PATCH"]
    assert calls[0]["url"] == "https://discord.test/webhook"
    assert calls[1]["url"].endswith("/messages/message123")
    assert calls[1]["json"]["embeds"][0]["fields"][1]["value"] == "2"

    state_path = tmp_path / "state" / "discord-batches.json"
    assert state_path.exists()
    state = json.loads(state_path.read_text())
    assert state["demo"]["message_id"] == "message123"


def test_notification_service_mentions_apply_to_batches(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        batch_daily=True,
        flush_time=dt.time(hour=0, minute=0),
        mentions={"default": "@here"},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    responses = [
        FakeResponse(200, {"id": "message123"}),
        FakeResponse(200, {"id": "message123"}),
    ]
    calls: List[Dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return responses.pop(0)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    service.notify(_build_event(destination="Demo-1.mkv"))
    service.notify(_build_event(destination="Demo-2.mkv"))

    first_payload = calls[0]["json"]
    assert first_payload["content"].startswith("@here Demo Sport updates")

    state_path = tmp_path / "state" / "discord-batches.json"
    assert state_path.exists()


def test_notification_service_mentions_handle_variant_ids(tmp_path, monkeypatch) -> None:
    settings = NotificationSettings(
        batch_daily=False,
        flush_time=dt.time(hour=0, minute=0),
        mentions={"premier_league": "<@&123>"},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: List[Dict[str, Any]] = []

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
        batch_daily=False,
        flush_time=dt.time(hour=0, minute=0),
        mentions={"formula1_*": "<@&999>", "default": "@here"},
        targets=[_DEFAULT_TARGET],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: List[Dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"method": method, "url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    event = _build_event()
    event.sport_id = "formula1_2025"
    service.notify(event)

    payload = calls[0]["json"]
    assert payload["content"].startswith("<@&999> [NEW]")


def test_discord_target_reads_webhook_from_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PLAYBOOK_DISCORD_WEBHOOK", "https://discord.test/env")
    settings = NotificationSettings(
        batch_daily=False,
        flush_time=dt.time(hour=0, minute=0),
        targets=[{"type": "discord", "webhook_env": "PLAYBOOK_DISCORD_WEBHOOK"}],
    )
    service = NotificationService(
        settings,
        cache_dir=tmp_path,
        destination_dir=tmp_path,
        enabled=True,
    )

    calls: List[Dict[str, Any]] = []

    def fake_request(method, url, json=None, timeout=None, headers=None):
        calls.append({"url": url, "json": json})
        return FakeResponse(204)

    monkeypatch.setattr("playbook.notifications.discord.requests.request", fake_request)

    service.notify(_build_event())

    assert calls and calls[0]["url"] == "https://discord.test/env"


def test_discord_target_skips_when_env_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PLAYBOOK_DISCORD_WEBHOOK", raising=False)
    settings = NotificationSettings(
        batch_daily=False,
        flush_time=dt.time(hour=0, minute=0),
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
        batch_daily=False,
        flush_time=dt.time(hour=0, minute=0),
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

    calls: List[Dict[str, Any]] = []

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
        batch_daily=False,
        flush_time=dt.time(hour=0, minute=0),
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
    request_calls: List[str] = []
    sleep_calls: List[float] = []

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
        batch_daily=False,
        flush_time=dt.time(hour=0, minute=0),
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
        batch_daily=False,
        flush_time=dt.time(hour=0, minute=0),
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

    calls: List[Dict[str, Any]] = []

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

