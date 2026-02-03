from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import NotificationSettings
from .autoscan import AutoscanTarget
from .discord import DiscordTarget
from .email import EmailTarget
from .plex_scan import PlexScanTarget
from .slack import SlackTarget
from .types import NotificationEvent, NotificationTarget
from .utils import _normalize_mentions_map
from .webhook import GenericWebhookTarget

LOGGER = logging.getLogger(__name__)


class ScanSummary:
    """Aggregates events from a scan for summary notification."""

    def __init__(self) -> None:
        self.events: list[NotificationEvent] = []
        self.by_sport: dict[str, list[NotificationEvent]] = defaultdict(list)

    def add(self, event: NotificationEvent) -> None:
        self.events.append(event)
        self.by_sport[event.sport_id].append(event)

    def clear(self) -> None:
        self.events.clear()
        self.by_sport.clear()

    def __len__(self) -> int:
        return len(self.events)

    def format_discord_embed(self) -> dict[str, Any]:
        """Format summary as a Discord embed."""
        if not self.events:
            return {}

        # Count by sport and type
        lines = []
        total_new = 0
        total_replaced = 0

        for sport_id in sorted(self.by_sport.keys()):
            sport_events = self.by_sport[sport_id]
            sport_name = sport_events[0].sport_name if sport_events else sport_id

            new_count = sum(1 for e in sport_events if e.event_type == "new" and not e.replaced)
            replaced_count = sum(1 for e in sport_events if e.replaced)
            changed_count = sum(1 for e in sport_events if e.event_type == "changed")
            error_count = sum(1 for e in sport_events if e.event_type == "error")

            total_new += new_count + changed_count
            total_replaced += replaced_count

            parts = []
            if new_count:
                parts.append(f"{new_count} new")
            if replaced_count:
                parts.append(f"{replaced_count} replaced")
            if changed_count:
                parts.append(f"{changed_count} changed")
            if error_count:
                parts.append(f"{error_count} errors")

            if parts:
                lines.append(f"**{sport_name}**: {', '.join(parts)}")

        description = "\n".join(lines) if lines else "No files processed"

        return {
            "title": "Playbook Scan Complete",
            "description": description,
            "color": 0x5865F2,  # Discord blurple
            "footer": {"text": f"Total: {total_new} new, {total_replaced} replaced"},
        }


class NotificationService:
    """Orchestrates notification delivery across multiple targets with throttling support."""

    def __init__(
        self,
        settings: NotificationSettings,
        *,
        cache_dir: Path,
        destination_dir: Path,
        enabled: bool = True,
    ) -> None:
        self._settings = settings
        self._enabled = enabled
        self._targets = self._build_targets(
            settings.targets,
            cache_dir,
            destination_dir,
        )
        self._throttle_map = settings.throttle
        self._last_sent: dict[str, datetime] = {}
        self._summary_mode = getattr(settings, "summary_mode", False)
        self._scan_summary = ScanSummary()

    @property
    def enabled(self) -> bool:
        return self._enabled and any(target.enabled() for target in self._targets)

    def notify(self, event: NotificationEvent) -> None:
        if not self.enabled:
            return
        allowed_types = {"new", "changed", "error"}
        event_type = (event.event_type or "unknown").lower()
        if event_type not in allowed_types:
            LOGGER.debug(
                "Skipping notification for %s because event_type is %s",
                event.sport_id,
                event.event_type,
            )
            return

        # In summary mode, collect events instead of sending immediately
        if self._summary_mode:
            self._scan_summary.add(event)
            LOGGER.debug(
                "Collected notification for summary | sport=%s episode=%s event=%s",
                event.sport_id,
                event.episode,
                event.event_type,
            )
            return

        throttle_seconds = self._resolve_throttle(event.sport_id)
        last_event = self._last_sent.get(event.sport_id)
        if throttle_seconds and last_event:
            delta = (event.timestamp - last_event).total_seconds()
            if delta < throttle_seconds:
                LOGGER.debug(
                    "Skipping notification for %s due to throttle (%ss remaining)",
                    event.sport_id,
                    round(throttle_seconds - delta, 2),
                )
                return

        successes: list[str] = []
        for target in self._targets:
            if not target.enabled():
                continue
            try:
                target.send(event)
            except Exception as exc:  # pragma: no cover - defensive logging
                LOGGER.warning("Notification target %s failed: %s", target.name, exc)
            else:
                successes.append(target.name)

        self._last_sent[event.sport_id] = event.timestamp
        if successes:
            LOGGER.debug(
                "Notification dispatched | sport=%s episode=%s event=%s targets=%s",
                event.sport_id,
                event.episode,
                event.event_type,
                ", ".join(successes),
            )
        else:
            LOGGER.debug(
                "Notification skipped or failed for %s (%s) - no targets succeeded",
                event.sport_id,
                event.event_type,
            )

    def send_summary(self) -> None:
        """Send a summary notification for all collected events.

        Only used when summary_mode is enabled. Call at the end of each scan.
        """
        if not self._summary_mode:
            return

        if not self._scan_summary:
            LOGGER.debug("No events to summarize")
            return

        LOGGER.info(
            "Sending summary notification for %d events across %d sports",
            len(self._scan_summary),
            len(self._scan_summary.by_sport),
        )

        embed = self._scan_summary.format_discord_embed()

        successes: list[str] = []
        for target in self._targets:
            if not target.enabled():
                continue
            try:
                # For Discord targets, send the embed directly
                if hasattr(target, "send_embed"):
                    target.send_embed(embed)
                else:
                    # For other targets, create a simple text summary
                    summary_text = self._format_text_summary()
                    target.send_raw(summary_text) if hasattr(target, "send_raw") else None
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Summary notification to %s failed: %s", target.name, exc)
            else:
                successes.append(target.name)

        self._scan_summary.clear()

        if successes:
            LOGGER.debug("Summary notification sent to: %s", ", ".join(successes))

    def _format_text_summary(self) -> str:
        """Format summary as plain text for non-Discord targets."""
        lines = ["Playbook Scan Complete", ""]
        for sport_id in sorted(self._scan_summary.by_sport.keys()):
            events = self._scan_summary.by_sport[sport_id]
            sport_name = events[0].sport_name if events else sport_id
            lines.append(f"  {sport_name}: {len(events)} file(s)")
        return "\n".join(lines)

    def _build_targets(
        self,
        targets_raw: list[dict[str, Any]],
        cache_dir: Path,
        destination_dir: Path,
    ) -> list[NotificationTarget]:
        targets: list[NotificationTarget] = []
        configs = list(targets_raw)

        for entry in configs:
            target_type = entry.get("type", "").lower()
            is_enabled = entry.get("enabled", True)
            target: NotificationTarget | None = None

            if target_type == "discord":
                webhook = self._discord_webhook_from(entry)
                if webhook:
                    batch = entry.get("batch")
                    mentions_override = _normalize_mentions_map(entry.get("mentions"))
                    target = DiscordTarget(
                        webhook,
                        cache_dir=cache_dir,
                        settings=self._settings,
                        batch=batch if batch is not None else entry.get("batch_daily"),
                        mentions=mentions_override if mentions_override else None,
                    )
                else:
                    LOGGER.warning("Skipped Discord target because webhook_url was not provided.")
            elif target_type == "slack":
                url = entry.get("webhook_url") or entry.get("url")
                if url:
                    target = SlackTarget(url, template=entry.get("template"))
                else:
                    LOGGER.warning("Skipped Slack target because webhook_url/url was not provided.")
            elif target_type == "webhook":
                url = entry.get("url")
                if url:
                    target = GenericWebhookTarget(
                        url,
                        method=entry.get("method", "POST"),
                        headers=entry.get("headers"),
                        template=entry.get("template"),
                    )
                else:
                    LOGGER.warning("Skipped webhook target because url was not provided.")
            elif target_type == "autoscan":
                url = entry.get("url")
                if url:
                    target = AutoscanTarget(entry, destination_dir=destination_dir)
                else:
                    LOGGER.warning("Skipped Autoscan target because url was not provided.")
            elif target_type in ("plex_scan", "plex"):
                # PlexScanTarget handles env var fallbacks internally
                target = PlexScanTarget(entry, destination_dir=destination_dir)
                if not target.enabled():
                    LOGGER.warning(
                        "Plex scan target disabled: url/token not found in config or env vars "
                        "(PLEX_URL, PLEX_TOKEN)"
                    )
                    target = None
            elif target_type == "email":
                target = EmailTarget(entry)
            else:
                LOGGER.warning("Unknown notification target type '%s'", target_type or "<missing>")

            # Set enabled state and add to list
            if target is not None:
                target.set_enabled(is_enabled)
                targets.append(target)

        return targets

    def _discord_webhook_from(self, entry: dict[str, Any]) -> str | None:
        webhook = entry.get("webhook_url")
        if isinstance(webhook, str):
            webhook = webhook.strip()
        if webhook:
            return webhook

        env_name = entry.get("webhook_env") or entry.get("webhook_url_env")
        if env_name is None:
            return None

        value: str | None = None
        env_key = str(env_name).strip()
        if env_key:
            raw_value = os.environ.get(env_key)
            if raw_value:
                value = raw_value.strip()
            else:
                LOGGER.warning(
                    "Discord target env var '%s' is not set; skipping target.",
                    env_key,
                )
        return value

    def _resolve_throttle(self, sport_id: str) -> int:
        if not self._throttle_map:
            return 0
        if sport_id in self._throttle_map:
            return max(0, int(self._throttle_map[sport_id]))
        default = self._throttle_map.get("default")
        return max(0, int(default)) if default is not None else 0
