from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, replace
from pathlib import Path

from .utils import ensure_directory

LOGGER = logging.getLogger(__name__)


@dataclass
class MetadataHttpEntry:
    etag: str | None = None
    last_modified: str | None = None
    status_code: int | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "etag": self.etag,
            "last_modified": self.last_modified,
            "status_code": self.status_code,
        }


class MetadataHttpCache:
    """Persists HTTP cache metadata (ETag / Last-Modified) for metadata feeds."""

    def __init__(self, cache_dir: Path, filename: str = "metadata-http.json") -> None:
        self.cache_dir = cache_dir
        self.filename = filename
        self.path = self.cache_dir / "state" / self.filename
        self._entries: dict[str, MetadataHttpEntry] = {}
        self._dirty = False
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to load metadata HTTP cache %s: %s", self.path, exc)
            return

        if not isinstance(payload, dict):
            LOGGER.warning("Ignoring malformed metadata HTTP cache %s", self.path)
            return

        entries: dict[str, MetadataHttpEntry] = {}
        for url, data in payload.items():
            if not isinstance(url, str) or not isinstance(data, dict):
                continue
            entries[url] = MetadataHttpEntry(
                etag=data.get("etag"),
                last_modified=data.get("last_modified"),
                status_code=data.get("status_code"),
            )
        self._entries = entries

    def get(self, url: str) -> MetadataHttpEntry | None:
        with self._lock:
            entry = self._entries.get(url)
            if entry is None:
                return None
            return replace(entry)

    def update(
        self,
        url: str,
        *,
        etag: str | None,
        last_modified: str | None,
        status_code: int | None,
    ) -> None:
        with self._lock:
            entry = self._entries.get(url)
            if entry is None:
                entry = MetadataHttpEntry()
                self._entries[url] = entry
            entry.etag = etag or entry.etag
            entry.last_modified = last_modified or entry.last_modified
            entry.status_code = status_code
            self._dirty = True

    def clear_failure(self, url: str) -> None:
        with self._lock:
            entry = self._entries.get(url)
            if entry is None:
                return
            entry.status_code = None
            self._dirty = True

    def invalidate(self, url: str) -> None:
        with self._lock:
            if url in self._entries:
                del self._entries[url]
                self._dirty = True

    def save(self) -> None:
        with self._lock:
            if not self._dirty:
                return
            ensure_directory(self.path.parent)
            serialised = {url: entry.to_dict() for url, entry in self._entries.items()}
            try:
                with self.path.open("w", encoding="utf-8") as handle:
                    json.dump(serialised, handle, indent=2, ensure_ascii=False, sort_keys=True)
                self._dirty = False
            except Exception as exc:  # noqa: BLE001
                LOGGER.error("Failed to write metadata HTTP cache %s: %s", self.path, exc)
