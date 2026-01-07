from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from .config import PatternConfig, SportConfig


@dataclass
class Episode:
    title: str
    summary: str | None
    originally_available: dt.date | None
    index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    display_number: int | None = None
    aliases: list[str] = field(default_factory=list)


@dataclass
class Season:
    key: str
    title: str
    summary: str | None
    index: int
    episodes: list[Episode]
    sort_title: str | None = None
    display_number: int | None = None
    round_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Show:
    key: str
    title: str
    summary: str | None
    seasons: list[Season]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SportFileMatch:
    source_path: Path
    destination_path: Path
    show: Show
    season: Season
    episode: Episode
    pattern: PatternConfig
    context: dict[str, Any]
    sport: SportConfig


@dataclass
class ProcessingStats:
    processed: int = 0
    skipped: int = 0
    ignored: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_details: list[str] = field(default_factory=list)
    ignored_details: list[str] = field(default_factory=list)
    suppressed_ignored_samples: int = 0
    errors_by_sport: dict[str, int] = field(default_factory=dict)
    warnings_by_sport: dict[str, int] = field(default_factory=dict)
    ignored_by_sport: dict[str, int] = field(default_factory=dict)

    def register_processed(self) -> None:
        self.processed += 1

    def register_skipped(self, reason: str, *, is_error: bool = True, sport_id: str | None = None) -> None:
        self.skipped += 1
        self.skipped_details.append(reason)
        if is_error:
            self.register_error(reason, sport_id=sport_id)

    def register_warning(self, message: str, *, sport_id: str | None = None) -> None:
        if message not in self.warnings:
            self.warnings.append(message)
        if sport_id:
            self.warnings_by_sport[sport_id] = self.warnings_by_sport.get(sport_id, 0) + 1

    def register_error(self, message: str, *, sport_id: str | None = None) -> None:
        self.errors.append(message)
        if sport_id:
            self.errors_by_sport[sport_id] = self.errors_by_sport.get(sport_id, 0) + 1

    def register_ignored(
        self,
        detail: str | None = None,
        *,
        suppressed_reason: str | None = None,
        sport_id: str | None = None,
    ) -> None:
        self.ignored += 1
        if detail:
            self.ignored_details.append(detail)
        if suppressed_reason == "sample":
            self.suppressed_ignored_samples += 1
            self.ignored_by_sport["samples"] = self.ignored_by_sport.get("samples", 0) + 1
        elif sport_id:
            self.ignored_by_sport[sport_id] = self.ignored_by_sport.get(sport_id, 0) + 1
