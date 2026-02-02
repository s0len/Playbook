from __future__ import annotations

import fnmatch
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from requests import Response
from requests.exceptions import RequestException

from ..config import NotificationSettings
from .batcher import NotificationBatcher
from .types import BatchRequest, NotificationEvent, NotificationTarget
from .utils import _excerpt_response, _trim

LOGGER = logging.getLogger(__name__)


class DiscordTarget(NotificationTarget):
    """Discord webhook notification target with batch support and mentions."""

    name = "discord"

    def __init__(
        self,
        webhook_url: str | None,
        *,
        cache_dir: Path,
        settings: NotificationSettings,
        batch: bool | None = None,
        mentions: dict[str, str] | None = None,
    ) -> None:
        self.webhook_url = webhook_url.strip() if isinstance(webhook_url, str) else None
        self._settings = settings
        use_batch = batch if batch is not None else settings.batch_daily
        self._batcher: NotificationBatcher | None
        if self.enabled() and use_batch:
            self._batcher = NotificationBatcher(cache_dir, settings)
        else:
            self._batcher = None
        self._mentions_override = dict(mentions or {})

    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def send(self, event: NotificationEvent) -> None:
        if not self.enabled():
            return

        now = event.timestamp
        if self._batcher is not None:
            request = self._batcher.prepare_event(event, now)
            payload = self._build_batch_payload(request, now)
            response = self._send_with_retries(
                request.action,
                self._message_url(request.message_id),
                payload,
            )
            if response is not None and request.action == "POST":
                message_id = self._extract_message_id(response)
                if message_id:
                    self._batcher.register_message_id(request.sport_id, request.bucket_date, message_id)
            return

        payload = self._build_single_payload(event, now)
        self._send_with_retries("POST", self.webhook_url, payload)

    def send_embed(self, embed: dict[str, Any]) -> None:
        """Send a pre-built embed directly (used for summary notifications)."""
        if not self.enabled():
            return

        # Add timestamp if not present
        if "timestamp" not in embed:
            embed["timestamp"] = datetime.now().isoformat()

        # Add footer if not present
        if "footer" not in embed:
            embed["footer"] = {"text": "Playbook"}

        payload = {"embeds": [embed]}
        self._send_with_retries("POST", self.webhook_url, payload)

    def _build_single_payload(self, event: NotificationEvent, now: datetime) -> dict[str, Any]:
        embed: dict[str, Any] = {
            "title": _trim(f"{event.show_title} – {event.session}", 256),
            "color": self._embed_color(event),
            "timestamp": now.isoformat(),
            "fields": [field for field in self._fields_for_event(event) if field is not None],
            "footer": {"text": "Playbook"},
        }

        indicator = self._event_indicator(event.event_type)
        prefix = f"{indicator} " if indicator else ""
        content = _trim(prefix + self._render_content(event), 2000)
        content = self._apply_mention_prefix(content, event.sport_id, limit=2000)
        return {"content": content, "embeds": [embed]}

    def _build_batch_payload(self, request: BatchRequest, now: datetime) -> dict[str, Any]:
        events = request.events
        total = len(events)
        visible_events = events[-20:]

        lines: list[str] = []
        for item in visible_events:
            action = item.get("action", "link")
            indicator = self._event_indicator(item.get("event_type"))
            season_part = f"{item.get('season')} – " if item.get("season") else ""
            reason = f" [{item.get('skip_reason')}]" if item.get("skip_reason") else ""
            destination_label = self._destination_label(item.get("destination"))
            line = (
                f"• {indicator + ' ' if indicator else ''}{season_part}{item.get('episode')} "
                f"({item.get('session')}) [{action}]"
                f"{' — ' + destination_label if destination_label else ''}{reason}"
            )
            lines.append(_trim(line, 190))

        hidden_count = total - len(visible_events)
        if hidden_count > 0:
            lines.append(f"… and {hidden_count} more.")

        description = _trim("\n".join(lines), 2048) if lines else None
        latest_payload = events[-1]
        latest_timestamp = latest_payload.get("timestamp") or now.isoformat()

        fields = [
            self._embed_field("Sport", request.sport_name, inline=True),
            self._embed_field("Updates", str(total), inline=True),
        ]
        latest_value = _trim(
            (
                f"{self._event_indicator(latest_payload.get('event_type'))} "
                f"{latest_payload.get('episode')} ({latest_payload.get('session')}) "
                f"[{latest_payload.get('action')}]"
                f"{' — ' + self._destination_label(latest_payload.get('destination')) if latest_payload.get('destination') else ''}"
            ).strip(),
            1024,
        )
        fields.append(self._embed_field("Latest", latest_value, inline=False))

        embed: dict[str, Any] = {
            "title": _trim(f"{request.sport_name} – {request.bucket_date.isoformat()}", 256),
            "color": 0x5865F2,
            "timestamp": latest_timestamp,
            "fields": [field for field in fields if field is not None],
            "footer": {"text": "Playbook"},
        }
        if description:
            embed["description"] = description

        content = _trim(
            f"{request.sport_name} updates for {request.bucket_date.isoformat()}: {total} item{'s' if total != 1 else ''}",
            limit=2000,
        )
        content = self._apply_mention_prefix(content, request.sport_id, limit=2000)
        return {"content": content, "embeds": [embed]}

    def _render_content(self, event: NotificationEvent) -> str:
        base = f"{event.sport_name}: {event.episode}"
        if event.event_type == "error":
            reason = f" — {event.skip_reason}" if event.skip_reason else ""
            return f"{base}{reason}"
        if event.event_type == "changed" and event.replaced:
            return f"{base} (updated existing copy)"
        if event.event_type == "changed":
            return f"{base} (updated)"
        if event.event_type == "dry-run":
            return f"{base} (dry run)"
        if event.replaced:
            return f"{base} (replaced existing)"
        return base

    def _fields_for_event(self, event: NotificationEvent) -> list[dict[str, Any] | None]:
        destination_label = self._destination_label(event.destination) or event.destination
        fields = [
            self._embed_field("Sport", event.sport_name, inline=True),
            self._embed_field("Season", event.season, inline=True),
            self._embed_field("Episode", event.episode, inline=True),
            self._embed_field("Destination", destination_label, inline=False),
        ]
        if event.skip_reason:
            fields.append(self._embed_field("Reason", event.skip_reason, inline=False))
        if event.trace_path:
            fields.append(self._embed_field("Trace", event.trace_path, inline=False))
        return fields

    def _embed_color(self, event: NotificationEvent) -> int:
        if event.action == "error":
            return 0xED4245
        if event.action == "skipped":
            return 0xFEE75C
        if event.action == "dry-run":
            return 0x95A5A6
        return 0x5865F2

    def _send_with_retries(self, method: str, url: str, payload: dict[str, Any]) -> Response | None:
        attempt = 0
        max_attempts = 5
        backoff = 1.0

        while attempt < max_attempts:
            try:
                response = requests.request(method, url, json=payload, timeout=10)
            except RequestException as exc:
                LOGGER.warning("Failed to send Discord notification: %s", exc)
                return None

            if response.status_code == 429:
                wait_seconds = self._retry_after_seconds(response, backoff)
                LOGGER.warning(
                    "Discord rate limited notification request; retrying in %.2fs (attempt %d/%d)",
                    wait_seconds,
                    attempt + 1,
                    max_attempts,
                )
                time.sleep(wait_seconds)
                attempt += 1
                backoff *= 2
                continue

            if response.status_code >= 400:
                LOGGER.warning(
                    "Discord webhook responded with %s: %s",
                    response.status_code,
                    _excerpt_response(response),
                )
                return None

            return response

        LOGGER.error("Discord notification failed after %d attempts due to rate limiting.", max_attempts)
        return None

    def _message_url(self, message_id: str | None) -> str:
        if not message_id:
            return self.webhook_url
        return f"{self.webhook_url}/messages/{message_id}"

    def _embed_field(self, name: str, value: str | None, *, inline: bool) -> dict[str, Any] | None:
        if value is None:
            return None
        text = _trim(str(value), 1024)
        if not text:
            return None
        return {"name": _trim(name, 256), "value": text, "inline": inline}

    def _mention_for_sport(self, sport_id: str | None) -> str | None:
        base_mentions = getattr(self._settings, "mentions", {}) or {}
        mentions = dict(base_mentions)
        if self._mentions_override:
            mentions.update(self._mentions_override)
        if not mentions:
            return None

        if sport_id:
            sport_id_str = str(sport_id)

            # 1. Exact match
            mention = mentions.get(sport_id_str)
            if mention:
                return mention

            # 2. Parent prefixes (e.g., "premier_league" for "premier_league_2025_26")
            for candidate in self._sport_prefixes(sport_id_str):
                mention = mentions.get(candidate)
                if mention:
                    return mention

            # 3. Wildcard patterns
            wildcard_matches = [
                (pattern, value)
                for pattern, value in mentions.items()
                if self._is_wildcard(pattern) and fnmatch.fnmatchcase(sport_id_str, pattern)
            ]
            if wildcard_matches:
                wildcard_matches.sort(key=lambda item: len(item[0]), reverse=True)
                return wildcard_matches[0][1]

        return mentions.get("default")

    def _apply_mention_prefix(self, text: str, sport_id: str | None, *, limit: int) -> str:
        mention = self._mention_for_sport(sport_id)
        if not mention:
            return text
        combined = f"{mention} {text}".strip()
        LOGGER.debug("Applying mention '%s' to sport '%s'", mention, sport_id)
        return _trim(combined, limit)

    @staticmethod
    def _is_wildcard(value: str) -> bool:
        return any(char in value for char in "*?[")

    @staticmethod
    def _sport_prefixes(sport_id: str) -> list[str]:
        parts = sport_id.split("_")
        prefixes: list[str] = []
        for end in range(len(parts) - 1, 0, -1):
            prefixes.append("_".join(parts[:end]))
        return prefixes

    @staticmethod
    def _event_indicator(event_type: str | None) -> str:
        mapping = {
            "new": "[NEW]",
            "changed": "[UPDATED]",
            "error": "[ERROR]",
        }
        if not event_type:
            return ""
        return mapping.get(str(event_type).lower(), "")

    @staticmethod
    def _destination_label(value: str | None) -> str:
        if not value:
            return ""
        path = Path(value)
        label = path.stem or path.name
        return label

    @staticmethod
    def _extract_message_id(response: Response) -> str | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        message_id = payload.get("id")
        return str(message_id) if message_id else None

    @staticmethod
    def _retry_after_seconds(response: Response, fallback: float) -> float:
        wait = fallback
        try:
            data = response.json()
        except ValueError:
            data = {}

        retry_after = data.get("retry_after")
        if isinstance(retry_after, (int, float)):
            wait = max(wait, float(retry_after))

        header_retry = response.headers.get("Retry-After")
        if header_retry:
            try:
                wait = max(wait, float(header_retry))
            except ValueError:
                pass

        return max(wait, 1.0)
