from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class BatchRequest:
    action: str  # "POST" or "PATCH"
    sport_id: str
    sport_name: str
    bucket_date: date
    message_id: Optional[str]
    events: List[Dict[str, Any]]


@dataclass
class NotificationEvent:
    sport_id: str
    sport_name: str
    show_title: str
    season: str
    session: str
    episode: str
    summary: Optional[str]
    destination: str
    source: str
    action: str
    link_mode: str
    replaced: bool = False
    skip_reason: Optional[str] = None
    trace_path: Optional[str] = None
    match_details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = "unknown"  # new, changed, refresh, skipped, error, dry-run


class NotificationTarget:
    name: str = "target"

    def enabled(self) -> bool:
        return True

    def send(self, event: NotificationEvent) -> None:
        raise NotImplementedError
