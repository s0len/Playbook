from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    from .config import PatternConfig, SportConfig


@dataclass(slots=True)
class Episode:
    title: str
    summary: Optional[str]
    originally_available: Optional[dt.date]
    index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    display_number: Optional[int] = None
    aliases: List[str] = field(default_factory=list)


@dataclass(slots=True)
class Season:
    key: str
    title: str
    summary: Optional[str]
    index: int
    episodes: List[Episode]
    sort_title: Optional[str] = None
    display_number: Optional[int] = None
    round_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Show:
    key: str
    title: str
    summary: Optional[str]
    seasons: List[Season]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SportFileMatch:
    source_path: Path
    destination_path: Path
    show: Show
    season: Season
    episode: Episode
    pattern: "PatternConfig"
    context: Dict[str, Any]
    sport: "SportConfig"


@dataclass(slots=True)
class ProcessingStats:
    processed: int = 0
    skipped: int = 0
    ignored: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    skipped_details: List[str] = field(default_factory=list)
    ignored_details: List[str] = field(default_factory=list)
    suppressed_ignored_samples: int = 0
    errors_by_sport: Dict[str, int] = field(default_factory=dict)
    warnings_by_sport: Dict[str, int] = field(default_factory=dict)
    ignored_by_sport: Dict[str, int] = field(default_factory=dict)

    def register_processed(self) -> None:
        self.processed += 1

    def register_skipped(self, reason: str, *, is_error: bool = True, sport_id: Optional[str] = None) -> None:
        self.skipped += 1
        self.skipped_details.append(reason)
        if is_error:
            self.register_error(reason, sport_id=sport_id)

    def register_warning(self, message: str, *, sport_id: Optional[str] = None) -> None:
        if message not in self.warnings:
            self.warnings.append(message)
        if sport_id:
            self.warnings_by_sport[sport_id] = self.warnings_by_sport.get(sport_id, 0) + 1

    def register_error(self, message: str, *, sport_id: Optional[str] = None) -> None:
        self.errors.append(message)
        if sport_id:
            self.errors_by_sport[sport_id] = self.errors_by_sport.get(sport_id, 0) + 1

    def register_ignored(
        self,
        detail: Optional[str] = None,
        *,
        suppressed_reason: Optional[str] = None,
        sport_id: Optional[str] = None,
    ) -> None:
        self.ignored += 1
        if detail:
            self.ignored_details.append(detail)
        if suppressed_reason == "sample":
            self.suppressed_ignored_samples += 1
            self.ignored_by_sport["samples"] = self.ignored_by_sport.get("samples", 0) + 1
        elif sport_id:
            self.ignored_by_sport[sport_id] = self.ignored_by_sport.get(sport_id, 0) + 1
