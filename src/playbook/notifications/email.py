from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any, Dict

from .types import NotificationEvent, NotificationTarget
from .utils import _flatten_event

LOGGER = logging.getLogger(__name__)


class EmailTarget(NotificationTarget):
    """Email notification target with SMTP support and optional template customization."""

    name = "email"

    def __init__(self, config: Dict[str, Any]) -> None:
        smtp_config = config.get("smtp") or {}
        self.host = smtp_config.get("host")
        self.port = int(smtp_config.get("port", 587))
        self.username = smtp_config.get("username")
        self.password = smtp_config.get("password")
        self.use_tls = bool(smtp_config.get("use_tls", True))
        self.timeout = int(smtp_config.get("timeout", 10))
        self.sender = config.get("from")
        recipients = config.get("to") or []
        if isinstance(recipients, str):
            recipients = [recipients]
        self.recipients = [addr.strip() for addr in recipients if addr]
        self.subject_template = config.get("subject")
        self.body_template = config.get("body")

    def enabled(self) -> bool:
        return bool(self.host and self.sender and self.recipients)

    def send(self, event: NotificationEvent) -> None:
        if not self.enabled():
            return

        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = ", ".join(self.recipients)
        message["Subject"] = self._compose_subject(event)
        message.set_content(self._compose_body(event))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(message)
        except Exception as exc:  # pragma: no cover - environment dependent
            LOGGER.warning("Failed to send email notification via %s:%s - %s", self.host, self.port, exc)

    def _compose_subject(self, event: NotificationEvent) -> str:
        if self.subject_template:
            return self.subject_template.format(**_flatten_event(event))
        return f"{event.sport_name}: {event.episode} ({event.session}) [{event.action}]"

    def _compose_body(self, event: NotificationEvent) -> str:
        if self.body_template:
            return self.body_template.format(**_flatten_event(event))

        lines = [
            f"Sport: {event.sport_name}",
            f"Season: {event.season}",
            f"Session: {event.session}",
            f"Episode: {event.episode}",
            f"Action: {event.action} ({event.link_mode})",
            f"Destination: {event.destination}",
            f"Source: {event.source}",
        ]
        if event.skip_reason:
            lines.append(f"Reason: {event.skip_reason}")
        if event.trace_path:
            lines.append(f"Trace: {event.trace_path}")
        if event.summary:
            lines.append("")
            lines.append("Summary:")
            lines.append(event.summary)
        return "\n".join(lines)
