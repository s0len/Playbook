from __future__ import annotations

import logging

import requests
from requests.exceptions import RequestException

from .types import NotificationEvent, NotificationTarget

LOGGER = logging.getLogger(__name__)


class SlackTarget(NotificationTarget):
    """Slack webhook notification target with optional template support."""

    name = "slack"

    def __init__(self, webhook_url: str | None, template: str | None = None) -> None:
        self.webhook_url = webhook_url.strip() if isinstance(webhook_url, str) else None
        self.template = template

    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def send(self, event: NotificationEvent) -> None:
        if not self.enabled():
            return
        payload = {"text": self._render(event)}
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
        except RequestException as exc:
            LOGGER.warning("Failed to send Slack notification: %s", exc)
            return

        if response.status_code >= 400:
            LOGGER.warning("Slack webhook responded with %s: %s", response.status_code, response.text)

    def _render(self, event: NotificationEvent) -> str:
        if self.template:
            return self.template.format(
                sport=event.sport_name,
                season=event.season,
                session=event.session,
                episode=event.episode,
                destination=event.destination,
                source=event.source,
                action=event.action,
                link_mode=event.link_mode,
                skip_reason=event.skip_reason or "",
            )
        base = f"{event.sport_name}: {event.episode} ({event.session})"
        if event.action == "error":
            return f":warning: Failed {base}{' - ' + event.skip_reason if event.skip_reason else ''}"
        if event.action == "skipped":
            return f":information_source: Skipped {base}{' - ' + event.skip_reason if event.skip_reason else ''}"
        if event.action == "dry-run":
            return f":grey_question: [Dry-Run] {base} via {event.link_mode}"
        replaced = " (replaced)" if event.replaced else ""
        return f":white_check_mark: {base} {event.action} via {event.link_mode}{replaced} → {event.destination}"
