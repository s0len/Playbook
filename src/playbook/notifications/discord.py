from __future__ import annotations

import contextlib
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from requests import Response
from requests.exceptions import RequestException

from ..config import NotificationSettings
from .types import NotificationEvent, NotificationTarget
from .utils import _excerpt_response, _trim, normalize_mention, replace_reason_label, resolve_sport_match

LOGGER = logging.getLogger(__name__)


def _format_file_size(size_bytes: int | None) -> str | None:
    """Format file size as human-readable string."""
    if size_bytes is None:
        return None
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class DiscordTarget(NotificationTarget):
    """Discord webhook notification target with mentions."""

    name = "discord"

    def __init__(
        self,
        webhook_url: str | None,
        *,
        settings: NotificationSettings,
        mentions: dict[str, str] | None = None,
    ) -> None:
        self.webhook_url = webhook_url.strip() if isinstance(webhook_url, str) else None
        self._settings = settings
        self._mentions_override = dict(mentions or {})

    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def send(self, event: NotificationEvent) -> None:
        if not self.enabled():
            return
        payload = self._build_payload(event, event.timestamp)
        self._send_with_retries("POST", self.webhook_url, payload)

    def send_embed(self, embed: dict[str, Any]) -> None:
        """Send a pre-built embed directly (used for summary notifications)."""
        if not self.enabled():
            return

        if "timestamp" not in embed:
            embed["timestamp"] = datetime.now().isoformat()
        if "footer" not in embed:
            embed["footer"] = {"text": "Playbook"}

        payload = {"embeds": [embed]}
        self._send_with_retries("POST", self.webhook_url, payload)

    def _build_payload(self, event: NotificationEvent, now: datetime) -> dict[str, Any]:
        embed: dict[str, Any] = {
            "title": _trim(f"{event.show_title} – {event.session}", 256),
            "color": self._embed_color(event),
            "timestamp": now.isoformat(),
            "fields": [field for field in self._fields_for_event(event) if field is not None],
            "footer": {"text": "Playbook"},
        }

        indicator = self._event_indicator(event)
        prefix = f"{indicator} " if indicator else ""
        content = _trim(prefix + self._render_content(event), 2000)
        content = self._apply_mention_prefix(content, event.sport_id, limit=2000)
        return {"content": content, "embeds": [embed]}

    def _render_content(self, event: NotificationEvent) -> str:
        base = f"{event.sport_name}: {event.episode}"
        if event.event_type == "error":
            reason = f" — {event.skip_reason}" if event.skip_reason else ""
            return f"{base}{reason}"
        if event.event_type == "dry-run":
            return f"{base} (dry run)"
        if event.replaced and event.replace_reason:
            label = self._replace_reason_label(event.replace_reason)
            return f"{base} ({label})"
        if event.replaced:
            return f"{base} (replaced existing)"
        return base

    def _fields_for_event(self, event: NotificationEvent) -> list[dict[str, Any] | None]:
        destination_label = self._destination_label(event.destination) or event.destination
        fields = [
            self._embed_field("Sport", event.sport_name, inline=True),
            self._embed_field("Season", event.season, inline=True),
            self._embed_field("Episode", event.episode, inline=True),
        ]

        # Quality line
        if event.quality_str:
            fields.append(self._embed_field("Quality", event.quality_str, inline=False))

        # Upgrade comparison for replacements
        if event.replaced and event.replace_reason:
            upgrade_text = self._format_upgrade_text(event)
            if upgrade_text:
                fields.append(self._embed_field("Upgrade", upgrade_text, inline=False))

        # Mismatch explanation
        if event.replace_reason == "mismatch_correction":
            fields.append(self._embed_field("Reason", "Was linked to wrong episode — now fixed", inline=False))

        fields.append(self._embed_field("Destination", destination_label, inline=False))
        fields.append(self._embed_field("Source", event.source, inline=False))

        if event.skip_reason and event.event_type in ("error", "skipped"):
            fields.append(self._embed_field("Reason", event.skip_reason, inline=False))

        return fields

    def _format_upgrade_text(self, event: NotificationEvent) -> str | None:
        """Format the upgrade comparison line."""
        parts: list[str] = []

        # Quality comparison
        if event.old_quality_str and event.quality_str:
            parts.append(f"{event.old_quality_str} → {event.quality_str}")
        elif event.quality_str and event.replace_reason == "quality_upgrade":
            parts.append(event.quality_str)

        # Score comparison
        if event.old_quality_score is not None and event.quality_score is not None:
            delta = event.quality_score - event.old_quality_score
            sign = "+" if delta > 0 else ""
            parts.append(f"Score: {event.old_quality_score} → {event.quality_score} ({sign}{delta})")

        # File size comparison
        old_size = _format_file_size(event.old_file_size)
        new_size = _format_file_size(event.file_size)
        if old_size and new_size:
            parts.append(f"Size: {old_size} → {new_size}")

        return "\n".join(parts) if parts else None

    def _embed_color(self, event: NotificationEvent) -> int:
        if event.event_type == "error" or event.action == "error":
            return 0xED4245  # Red
        if event.event_type == "dry-run" or event.action == "dry-run":
            return 0x95A5A6  # Grey
        if event.action == "skipped":
            return 0xFEE75C  # Yellow
        if event.replaced:
            if event.replace_reason == "mismatch_correction":
                return 0xFEE75C  # Orange/yellow for mismatch fix
            return 0x5865F2  # Blurple for upgrade/proper
        return 0x57F287  # Green for new

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
            match = resolve_sport_match(str(sport_id), mentions)
            if match:
                return normalize_mention(str(match))

        raw = mentions.get("default")
        return normalize_mention(str(raw)) if raw else None

    def _apply_mention_prefix(self, text: str, sport_id: str | None, *, limit: int) -> str:
        mention = self._mention_for_sport(sport_id)
        if not mention:
            return text
        combined = f"{mention} {text}".strip()
        LOGGER.debug("Applying mention '%s' to sport '%s'", mention, sport_id)
        return _trim(combined, limit)

    @staticmethod
    def _event_indicator(event: NotificationEvent) -> str:
        if event.event_type == "error" or event.action == "error":
            return "[ERROR]"
        if event.event_type == "dry-run" or event.action == "dry-run":
            return "[DRY-RUN]"
        if event.action == "skipped":
            return ""
        if event.replaced:
            reason = event.replace_reason or ""
            if reason == "proper_repack":
                return "[PROPER]"
            if reason == "mismatch_correction":
                return "[FIX]"
            if reason in ("quality_upgrade", "legacy"):
                return "[UPGRADE]"
            return "[UPGRADE]"
        return "[NEW]"

    @staticmethod
    def _replace_reason_label(reason: str) -> str:
        return replace_reason_label(reason)

    @staticmethod
    def _destination_label(value: str | None) -> str:
        if not value:
            return ""
        path = Path(value)
        label = path.stem or path.name
        return label

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
            with contextlib.suppress(ValueError):
                wait = max(wait, float(header_retry))

        return max(wait, 1.0)
