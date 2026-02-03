"""Plex scan notification target for triggering partial library scans."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .types import NotificationEvent, NotificationTarget

LOGGER = logging.getLogger(__name__)


class PlexScanTarget(NotificationTarget):
    """Notification target that triggers Plex partial library scans.

    This target uses the Plex API directly to trigger partial scans of specific
    paths when files are added. This is useful for having Plex quickly pick up
    new files without waiting for scheduled library scans.

    Configuration:
        url: Plex server URL (e.g., http://192.168.1.100:32400)
        token: Plex authentication token
        library_id: Library section ID to scan (optional if library_name provided)
        library_name: Library name to scan (optional if library_id provided)
        timeout: Request timeout in seconds (default: 15)
        rewrite: Path rewrite rules (same format as Autoscan)
    """

    name = "plex_scan"

    def __init__(self, config: dict[str, Any], *, destination_dir: Path) -> None:
        self._destination_dir = destination_dir
        self._url = self._normalize_url(config.get("url"))
        self._token = config.get("token")
        self._library_id = config.get("library_id")
        self._library_name = config.get("library_name")
        self._timeout = self._parse_timeout(config.get("timeout"))
        self._rewrite_rules = self._build_rewrite_rules(config.get("rewrite"))
        self._resolved_library_id: str | None = None

    @staticmethod
    def _normalize_url(url: Any) -> str | None:
        if not url:
            return None
        url_str = str(url).strip().rstrip("/")
        return url_str if url_str else None

    @staticmethod
    def _parse_timeout(value: Any) -> float:
        try:
            timeout = float(value)
        except (TypeError, ValueError):
            return 15.0
        return max(1.0, timeout)

    @staticmethod
    def _build_rewrite_rules(value: Any) -> list[tuple[str, str]]:
        if not value:
            return []
        entries = value
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            return []
        rules: list[tuple[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            from_value = str(entry.get("from") or "").strip()
            to_value = str(entry.get("to") or "").strip()
            if not from_value or not to_value:
                continue
            rules.append(
                (
                    PlexScanTarget._normalize_prefix(from_value),
                    PlexScanTarget._normalize_prefix(to_value),
                )
            )
        return rules

    @staticmethod
    def _normalize_prefix(value: str) -> str:
        if value in {"/", "\\"}:
            return value
        return value.rstrip("/\\")

    def enabled(self) -> bool:
        return bool(self._url and self._token and (self._library_id or self._library_name))

    def _get_library_id(self) -> str | None:
        """Get or resolve the library ID."""
        if self._resolved_library_id:
            return self._resolved_library_id

        if self._library_id:
            self._resolved_library_id = str(self._library_id)
            return self._resolved_library_id

        # Need to resolve by name
        if not self._library_name:
            return None

        try:
            from ..plex_client import PlexClient

            client = PlexClient(self._url, self._token, timeout=self._timeout)
            libraries = client.list_libraries(type_filter="show")
            for lib in libraries:
                if lib.title.lower() == self._library_name.lower():
                    self._resolved_library_id = lib.key
                    LOGGER.debug("Resolved Plex library '%s' to ID %s", self._library_name, lib.key)
                    return self._resolved_library_id

            LOGGER.warning("Plex library '%s' not found", self._library_name)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to resolve Plex library: %s", exc)

        return None

    def send(self, event: NotificationEvent) -> None:
        if not self.enabled():
            return
        if event.event_type not in {"new", "changed"}:
            return

        library_id = self._get_library_id()
        if not library_id:
            LOGGER.debug("Plex scan skipped: no library ID available")
            return

        scan_path = self._path_for_event(event)
        if not scan_path:
            LOGGER.debug(
                "Plex scan skipped for %s: no destination path available",
                event.sport_id,
            )
            return

        try:
            from ..plex_client import PlexClient

            client = PlexClient(self._url, self._token, timeout=self._timeout)
            client.scan_library(library_id, path=scan_path)
            LOGGER.debug(
                "Plex partial scan triggered for %s: %s",
                event.sport_id,
                scan_path,
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to trigger Plex scan: %s", exc)

    def _path_for_event(self, event: NotificationEvent) -> str | None:
        """Get the scan path for an event."""
        details = event.match_details or {}
        destination_raw = details.get("destination_path")
        if destination_raw:
            destination_path = Path(str(destination_raw))
        else:
            if not event.destination:
                return None
            destination_path = Path(event.destination)
            if not destination_path.is_absolute():
                destination_path = self._destination_dir / destination_path

        # Scan the parent directory (show folder or season folder)
        directory = destination_path if destination_path.is_dir() else destination_path.parent
        directory_str = str(directory)
        if not directory_str:
            return None
        return self._apply_rewrite(directory_str)

    def _apply_rewrite(self, path: str) -> str:
        """Apply path rewrite rules."""
        for old_prefix, new_prefix in self._rewrite_rules:
            if not old_prefix:
                continue
            if old_prefix in {"/", "\\"} and path.startswith(old_prefix):
                remainder = path[len(old_prefix) :]
                if remainder and remainder[0] not in ("/", "\\"):
                    remainder = f"/{remainder}"
                return f"{new_prefix}{remainder}"
            if path == old_prefix:
                return new_prefix or path
            if path.startswith(f"{old_prefix}/") or path.startswith(f"{old_prefix}\\"):
                remainder = path[len(old_prefix) :]
                return f"{new_prefix}{remainder}"
        return path
