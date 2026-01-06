from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

from .types import NotificationEvent, NotificationTarget
from .utils import _excerpt_response

LOGGER = logging.getLogger(__name__)


class AutoscanTarget(NotificationTarget):
    """Autoscan notification target with path rewriting and authentication support."""

    name = "autoscan"

    def __init__(self, config: Dict[str, Any], *, destination_dir: Path) -> None:
        self._destination_dir = destination_dir
        self._endpoint = self._build_endpoint(config.get("url"), config.get("trigger"))
        self._timeout = self._parse_timeout(config.get("timeout"))
        username = config.get("username")
        password = config.get("password")
        if username or password:
            self._auth = HTTPBasicAuth(str(username or ""), str(password or ""))
        else:
            self._auth = None
        verify_value = config.get("verify_ssl")
        if verify_value is None:
            self._verify_ssl = True
        else:
            self._verify_ssl = bool(verify_value)
        self._rewrite_rules = self._build_rewrite_rules(config.get("rewrite"))

    @staticmethod
    def _build_endpoint(url_value: Any, trigger_value: Any) -> Optional[str]:
        if not url_value:
            return None
        base = str(url_value).strip().rstrip("/")
        if not base:
            return None
        trigger = str(trigger_value or "manual").strip().strip("/")
        if not trigger:
            trigger = "manual"
        return f"{base}/triggers/{trigger}"

    @staticmethod
    def _parse_timeout(value: Any) -> float:
        try:
            timeout = float(value)
        except (TypeError, ValueError):
            return 10.0
        return max(1.0, timeout)

    @staticmethod
    def _build_rewrite_rules(value: Any) -> List[Tuple[str, str]]:
        if not value:
            return []
        entries = value
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            return []
        rules: List[Tuple[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            from_value = str(entry.get("from") or "").strip()
            to_value = str(entry.get("to") or "").strip()
            if not from_value or not to_value:
                continue
            rules.append(
                (
                    AutoscanTarget._normalize_prefix(from_value),
                    AutoscanTarget._normalize_prefix(to_value),
                )
            )
        return rules

    @staticmethod
    def _normalize_prefix(value: str) -> str:
        if value in {"/", "\\"}:
            return value
        return value.rstrip("/\\")

    def enabled(self) -> bool:
        return bool(self._endpoint)

    def send(self, event: NotificationEvent) -> None:
        if not self.enabled():
            return
        if event.event_type not in {"new", "changed"}:
            return

        directory = self._directory_for_event(event)
        if not directory:
            LOGGER.debug(
                "Autoscan target skipped event for %s because no destination directory was available.",
                event.sport_id,
            )
            return

        params = [("dir", directory)]
        try:
            response = requests.post(
                self._endpoint,
                params=params,
                auth=self._auth,
                timeout=self._timeout,
                verify=self._verify_ssl,
            )
        except RequestException as exc:
            LOGGER.warning("Failed to notify Autoscan at %s: %s", self._endpoint, exc)
            return

        if response.status_code >= 400:
            LOGGER.warning(
                "Autoscan webhook responded with %s: %s",
                response.status_code,
                _excerpt_response(response),
            )
        else:
            LOGGER.debug(
                "Autoscan trigger posted for %s (%s)",
                event.sport_id,
                directory,
            )

    def _directory_for_event(self, event: NotificationEvent) -> Optional[str]:
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

        directory = destination_path if destination_path.is_dir() else destination_path.parent
        directory_str = str(directory)
        if not directory_str:
            return None
        return self._apply_rewrite(directory_str)

    def _apply_rewrite(self, path: str) -> str:
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
