from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
from requests.exceptions import RequestException

from .types import NotificationEvent, NotificationTarget
from .utils import _flatten_event, _render_template

LOGGER = logging.getLogger(__name__)


class GenericWebhookTarget(NotificationTarget):
    """Generic webhook notification target with configurable method, headers, and template."""

    name = "webhook"

    def __init__(
        self,
        url: Optional[str],
        *,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        template: Optional[Any] = None,
    ) -> None:
        self.url = url.strip() if isinstance(url, str) else None
        self.method = method.upper()
        self.headers = {str(k): str(v) for k, v in (headers or {}).items()}
        self.template = template

    def enabled(self) -> bool:
        return bool(self.url)

    def send(self, event: NotificationEvent) -> None:
        if not self.enabled():
            return
        payload = self._build_payload(event)
        try:
            response = requests.request(
                self.method,
                self.url,
                json=payload,
                headers=self.headers or None,
                timeout=10,
            )
        except RequestException as exc:
            LOGGER.warning("Failed to send webhook notification: %s", exc)
            return

        if response.status_code >= 400:
            LOGGER.warning("Webhook %s responded with %s: %s", self.url, response.status_code, response.text)

    def _build_payload(self, event: NotificationEvent) -> Any:
        data = _flatten_event(event)
        template = self.template
        if template is None:
            return data
        return _render_template(template, data)
