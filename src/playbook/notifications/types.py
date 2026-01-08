from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any


@dataclass
class BatchRequest:
    action: str  # "POST" or "PATCH"
    sport_id: str
    sport_name: str
    bucket_date: date
    message_id: str | None
    events: list[dict[str, Any]]


@dataclass
class NotificationEvent:
    sport_id: str
    sport_name: str
    show_title: str
    season: str
    session: str
    episode: str
    summary: str | None
    destination: str
    source: str
    action: str
    link_mode: str
    replaced: bool = False
    skip_reason: str | None = None
    trace_path: str | None = None
    match_details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_type: str = "unknown"  # new, changed, refresh, skipped, error, dry-run


class NotificationTarget:
    name: str = "target"

    def enabled(self) -> bool:
        return True

    def send(self, event: NotificationEvent) -> None:
        raise NotImplementedError
