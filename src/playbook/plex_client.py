from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin

import requests

LOGGER = logging.getLogger(__name__)


class PlexApiError(RuntimeError):
    """Raised when Plex API requests fail."""


def _build_url(base_url: str, path: str) -> str:
    normalized = base_url.rstrip("/") + "/"
    return urljoin(normalized, path.lstrip("/"))


def _parse_json_response(response: requests.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        snippet = response.text[:500]
        raise PlexApiError(f"Failed to parse Plex response as JSON ({response.status_code}): {snippet}") from exc


@dataclass(slots=True)
class PlexLibrary:
    key: str
    title: str
    type: Optional[str]


class PlexClient:
    """Thin wrapper around Plex HTTP endpoints defined in openapi.json."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session = session or requests.Session()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        allow_error: bool = False,
        **kwargs: Any,
    ) -> requests.Response:
        url = _build_url(self.base_url, path)
        merged_params = dict(params or {})
        merged_params["X-Plex-Token"] = self.token
        merged_headers = {"Accept": "application/json"}
        if headers:
            merged_headers.update(headers)

        LOGGER.debug("Plex %s %s", method.upper(), url)
        response = self.session.request(
            method,
            url,
            params=merged_params,
            headers=merged_headers,
            timeout=self.timeout,
            **kwargs,
        )

        if not allow_error and response.status_code >= 400:
            snippet = response.text[:200]
            raise PlexApiError(f"Plex request failed ({response.status_code}): {snippet}")

        return response

    def list_libraries(self) -> List[PlexLibrary]:
        response = self._request("GET", "/library/sections")
        payload = _parse_json_response(response)
        container = payload.get("MediaContainer", {})
        directories = container.get("Directory", []) or []
        libraries: List[PlexLibrary] = []
        for entry in directories:
            key = entry.get("key")
            title = entry.get("title")
            if key is None or title is None:
                continue
            libraries.append(PlexLibrary(key=str(key), title=str(title), type=entry.get("type")))
        return libraries

    def find_library(self, *, library_id: Optional[str], library_name: Optional[str]) -> str:
        if library_id:
            return str(library_id)
        libraries = self.list_libraries()
        if not library_name:
            raise PlexApiError("Library id or name is required to target Plex")
        for library in libraries:
            if library.title.lower() == library_name.lower():
                return library.key
        available = ", ".join(lib.title for lib in libraries) or "(none)"
        raise PlexApiError(f"Plex library '{library_name}' not found (available: {available})")

    def search_show(self, library_id: str, title: str) -> Optional[Dict[str, Any]]:
        params = {
            "type": 2,  # show
            "title": title,
        }
        response = self._request("GET", f"/library/sections/{library_id}/all", params=params)
        payload = _parse_json_response(response)
        metadata_entries: Iterable[Dict[str, Any]] = (
            payload.get("MediaContainer", {}).get("Metadata") or []
        )
        for entry in metadata_entries:
            if str(entry.get("title", "")).lower() == title.lower():
                return entry
        return next(iter(metadata_entries), None)

    def list_children(self, rating_key: str) -> List[Dict[str, Any]]:
        response = self._request("GET", f"/library/metadata/{rating_key}/children")
        payload = _parse_json_response(response)
        return list(payload.get("MediaContainer", {}).get("Metadata") or [])

    def update_metadata(self, rating_key: str, params: Dict[str, Any]) -> None:
        clean_params = {key: value for key, value in params.items() if value is not None}
        if not clean_params:
            return
        self._request("PUT", f"/library/metadata/{rating_key}", params=clean_params)

    def set_asset(self, rating_key: str, element: str, url: str) -> None:
        params = {"url": url}
        self._request("PUT", f"/library/metadata/{rating_key}/{element}", params=params)


