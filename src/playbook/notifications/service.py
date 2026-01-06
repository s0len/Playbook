from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import NotificationSettings
from .autoscan import AutoscanTarget
from .discord import DiscordTarget
from .email import EmailTarget
from .slack import SlackTarget
from .types import NotificationEvent, NotificationTarget
from .utils import _normalize_mentions_map
from .webhook import GenericWebhookTarget

LOGGER = logging.getLogger(__name__)


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
        self._last_sent: Dict[str, datetime] = {}

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

        successes: List[str] = []
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

    def _build_targets(
        self,
        targets_raw: List[Dict[str, Any]],
        cache_dir: Path,
        destination_dir: Path,
    ) -> List[NotificationTarget]:
        targets: List[NotificationTarget] = []
        configs = list(targets_raw)

        for entry in configs:
            target_type = entry.get("type", "").lower()
            if target_type == "discord":
                webhook = self._discord_webhook_from(entry)
                if webhook:
                    batch = entry.get("batch")
                    mentions_override = _normalize_mentions_map(entry.get("mentions"))
                    targets.append(
                        DiscordTarget(
                            webhook,
                            cache_dir=cache_dir,
                            settings=self._settings,
                            batch=batch if batch is not None else entry.get("batch_daily"),
                            mentions=mentions_override if mentions_override else None,
                        )
                    )
                else:
                    LOGGER.warning("Skipped Discord target because webhook_url was not provided.")
            elif target_type == "slack":
                url = entry.get("webhook_url") or entry.get("url")
                if url:
                    targets.append(SlackTarget(url, template=entry.get("template")))
                else:
                    LOGGER.warning("Skipped Slack target because webhook_url/url was not provided.")
            elif target_type == "webhook":
                url = entry.get("url")
                if url:
                    targets.append(
                        GenericWebhookTarget(
                            url,
                            method=entry.get("method", "POST"),
                            headers=entry.get("headers"),
                            template=entry.get("template"),
                        )
                    )
                else:
                    LOGGER.warning("Skipped webhook target because url was not provided.")
            elif target_type == "autoscan":
                url = entry.get("url")
                if url:
                    targets.append(AutoscanTarget(entry, destination_dir=destination_dir))
                else:
                    LOGGER.warning("Skipped Autoscan target because url was not provided.")
            elif target_type == "email":
                targets.append(EmailTarget(entry))
            else:
                LOGGER.warning("Unknown notification target type '%s'", target_type or "<missing>")

        return [target for target in targets if target.enabled()]

    def _discord_webhook_from(self, entry: Dict[str, Any]) -> Optional[str]:
        webhook = entry.get("webhook_url")
        if isinstance(webhook, str):
            webhook = webhook.strip()
        if webhook:
            return webhook

        env_name = entry.get("webhook_env") or entry.get("webhook_url_env")
        if env_name is None:
            return None

        value: Optional[str] = None
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
