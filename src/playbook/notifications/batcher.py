from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from ..config import NotificationSettings
from ..utils import ensure_directory
from .types import BatchRequest, NotificationEvent

LOGGER = logging.getLogger(__name__)


class NotificationBatcher:
    """Persisted per-sport batches that group notifications by day."""

    def __init__(self, cache_dir: Path, settings: NotificationSettings) -> None:
        self._settings = settings
        self._path = cache_dir / "state" / "discord-batches.json"
        self._state: Dict[str, Dict[str, Any]] = {}
        self._dirty = False
        self._load()

    def prepare_event(self, event: NotificationEvent, now: datetime) -> BatchRequest:
        sport_id = event.sport_id
        sport_name = event.sport_name
        bucket = self._bucket_date(now)
        bucket_key = bucket.isoformat()

        entry = self._state.get(sport_id)
        if not entry or entry.get("bucket_date") != bucket_key:
            entry = {
                "bucket_date": bucket_key,
                "message_id": None,
                "sport_name": sport_name,
                "events": [],
            }

        event_payload = {
            "sport_id": sport_id,
            "sport_name": sport_name,
            "season": event.season,
            "session": event.session,
            "episode": event.episode,
            "destination": event.destination,
            "source": event.source,
            "summary": event.summary,
            "action": event.action,
            "link_mode": event.link_mode,
            "replaced": event.replaced,
            "skip_reason": event.skip_reason,
            "trace_path": event.trace_path,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
        }

        events = entry["events"]
        events.append(event_payload)
        entry["events"] = events
        entry["sport_name"] = sport_name
        entry["last_event_at"] = event_payload["timestamp"]

        self._state[sport_id] = entry
        self._dirty = True
        self._save()

        message_id = entry.get("message_id")
        action = "PATCH" if message_id else "POST"

        return BatchRequest(
            action=action,
            sport_id=sport_id,
            sport_name=sport_name,
            bucket_date=bucket,
            message_id=message_id,
            events=[dict(item) for item in events],
        )

    def register_message_id(self, sport_id: str, bucket_date: date, message_id: str) -> None:
        entry = self._state.get(sport_id)
        if not entry:
            return
        if entry.get("bucket_date") != bucket_date.isoformat():
            return
        if entry.get("message_id") == message_id:
            return

        entry["message_id"] = message_id
        self._dirty = True
        self._save()

    def _bucket_date(self, now: datetime) -> date:
        local_now = now.astimezone()
        flush_time = self._settings.flush_time
        if flush_time and local_now.time() < flush_time:
            return local_now.date() - timedelta(days=1)
        return local_now.date()

    def _load(self) -> None:
        if not self._path.exists():
            return

        try:
            with self._path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to load notification batch cache %s: %s", self._path, exc)
            return

        if not isinstance(payload, dict):
            LOGGER.warning("Ignoring malformed notification batch cache %s", self._path)
            return

        state: Dict[str, Dict[str, Any]] = {}
        for sport_id, entry in payload.items():
            if not isinstance(sport_id, str) or not isinstance(entry, dict):
                continue

            events_raw = entry.get("events") or []
            if not isinstance(events_raw, list):
                events_raw = []

            events: List[Dict[str, Any]] = []
            for item in events_raw:
                if not isinstance(item, dict):
                    continue
                trace_path = item.get("trace_path")
                trace_str = str(trace_path) if trace_path else None
                events.append(
                    {
                        "sport_id": str(item.get("sport_id") or sport_id),
                        "sport_name": str(item.get("sport_name") or entry.get("sport_name") or ""),
                        "season": item.get("season"),
                        "session": str(item.get("session") or ""),
                        "episode": str(item.get("episode") or ""),
                        "destination": str(item.get("destination") or ""),
                        "source": str(item.get("source") or ""),
                        "summary": item.get("summary"),
                        "action": str(item.get("action") or "link"),
                        "link_mode": str(item.get("link_mode") or ""),
                        "replaced": bool(item.get("replaced") or False),
                        "skip_reason": item.get("skip_reason"),
                        "trace_path": trace_str,
                        "timestamp": str(item.get("timestamp") or ""),
                        "event_type": str(item.get("event_type") or "unknown"),
                    }
                )

            state[sport_id] = {
                "bucket_date": str(entry.get("bucket_date") or ""),
                "message_id": entry.get("message_id"),
                "sport_name": str(entry.get("sport_name") or ""),
                "events": events,
                "last_event_at": str(entry.get("last_event_at") or ""),
            }

        self._state = state

    def _save(self) -> None:
        if not self._dirty:
            return

        ensure_directory(self._path.parent)
        try:
            with self._path.open("w", encoding="utf-8") as handle:
                json.dump(self._state, handle, ensure_ascii=False, indent=2)
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Failed to write notification batch cache %s: %s", self._path, exc)
            return

        self._dirty = False
