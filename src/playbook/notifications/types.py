from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


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
    # Quality and replacement context
    replace_reason: str | None = None  # quality_upgrade, mismatch_correction, proper_repack, legacy
    quality_str: str | None = None  # Human-readable quality line: "1080p · WEB-DL · x265 · AAC · F1TV"
    old_quality_str: str | None = None  # Previous file's quality line (for upgrades)
    quality_score: int | None = None  # Numeric quality score
    old_quality_score: int | None = None  # Previous file's quality score
    file_size: int | None = None  # Source file size in bytes
    old_file_size: int | None = None  # Previous file size in bytes


class NotificationTarget:
    name: str = "target"
    _enabled: bool = True

    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def send(self, event: NotificationEvent) -> None:
        raise NotImplementedError
