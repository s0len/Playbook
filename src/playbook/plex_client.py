from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)

# Plex metadata type codes from openapi.json
PLEX_TYPE_SHOW = 2
PLEX_TYPE_SEASON = 3
PLEX_TYPE_EPISODE = 4

# Default retry configuration
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5
RETRY_STATUS_CODES = frozenset({500, 502, 503, 504, 429})


class PlexApiError(RuntimeError):
    """Raised when Plex API requests fail."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PlexRateLimitError(PlexApiError):
    """Raised when Plex returns 429 Too Many Requests."""


def _build_url(base_url: str, path: str) -> str:
    normalized = base_url.rstrip("/") + "/"
    return urljoin(normalized, path.lstrip("/"))


def _sanitize_url_for_logging(url: str) -> str:
    """Remove sensitive query parameters from URL for safe logging."""
    # Remove X-Plex-Token from URL if present (shouldn't be, but defensive)
    return re.sub(r"[?&]X-Plex-Token=[^&]*", "", url)


def _parse_json_response(response: requests.Response) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError as exc:  # pragma: no cover - defensive
        snippet = response.text[:500]
        raise PlexApiError(
            f"Failed to parse Plex response as JSON ({response.status_code}): {snippet}",
            status_code=response.status_code,
        ) from exc


def validate_plex_url(url: str | None) -> bool:
    """Validate that URL is a valid http/https URL."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:  # noqa: BLE001 - defensive
        return False


@dataclass
class PlexLibrary:
    key: str
    title: str
    type: str | None


@dataclass
class PlexSyncStats:
    """Track statistics for a Plex sync operation."""

    shows_updated: int = 0
    shows_skipped: int = 0
    seasons_updated: int = 0
    seasons_skipped: int = 0
    seasons_not_found: int = 0
    episodes_updated: int = 0
    episodes_skipped: int = 0
    episodes_not_found: int = 0
    assets_updated: int = 0
    assets_failed: int = 0
    api_calls: int = 0
    errors: list[str] = field(default_factory=list)

    def has_activity(self) -> bool:
        return any(
            (
                self.shows_updated,
                self.seasons_updated,
                self.episodes_updated,
                self.assets_updated,
                self.errors,
            )
        )

    def summary(self) -> dict[str, Any]:
        return {
            "shows": {"updated": self.shows_updated, "skipped": self.shows_skipped},
            "seasons": {
                "updated": self.seasons_updated,
                "skipped": self.seasons_skipped,
                "not_found": self.seasons_not_found,
            },
            "episodes": {
                "updated": self.episodes_updated,
                "skipped": self.episodes_skipped,
                "not_found": self.episodes_not_found,
            },
            "assets": {"updated": self.assets_updated, "failed": self.assets_failed},
            "api_calls": self.api_calls,
            "errors": len(self.errors),
        }


@dataclass
class SearchResult:
    """Capture search diagnostics for debugging failed lookups."""

    searched_title: str
    library_id: str
    close_matches: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None


class PlexClient:
    """Thin wrapper around Plex HTTP endpoints defined in openapi.json.

    Token is passed via X-Plex-Token header (not query params) for security.
    Includes automatic retries with exponential backoff for transient failures.

    Title Case Preservation:
        Plex automatically normalizes titles (e.g., "NTT" → "Ntt"). Use the
        update_metadata() method with lock_fields=True to override this
        normalization and preserve the original casing from your metadata.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 15.0,
        session: requests.Session | None = None,
        max_retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        rate_limit_delay: float = 0.0,
    ) -> None:
        if not validate_plex_url(base_url):
            raise PlexApiError(f"Invalid Plex URL: {base_url}")

        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time: float = 0.0

        self.session = session or requests.Session()
        if session is None:
            # Configure retry strategy
            retry_strategy = Retry(
                total=max_retries,
                backoff_factor=backoff_factor,
                status_forcelist=list(RETRY_STATUS_CODES),
                allowed_methods=["GET", "PUT", "POST", "DELETE"],
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=10)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

    def _apply_rate_limit(self) -> None:
        """Apply rate limiting delay between requests if configured."""
        if self.rate_limit_delay <= 0:
            return
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        allow_error: bool = False,
        **kwargs: Any,
    ) -> requests.Response:
        self._apply_rate_limit()

        url = _build_url(self.base_url, path)
        merged_params = dict(params or {})
        # Token goes in header, NOT query params (security)
        merged_headers = {
            "Accept": "application/json",
            "X-Plex-Token": self.token,
        }
        if headers:
            merged_headers.update(headers)

        # Log sanitized URL only
        LOGGER.debug("Plex %s %s", method.upper(), _sanitize_url_for_logging(url))

        try:
            response = self.session.request(
                method,
                url,
                params=merged_params,
                headers=merged_headers,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise PlexApiError(f"Plex request failed: {exc}") from exc
        finally:
            self._last_request_time = time.monotonic()

        if response.status_code == 429:
            raise PlexRateLimitError(
                "Plex rate limit exceeded (429)",
                status_code=429,
            )

        if not allow_error and response.status_code >= 400:
            snippet = response.text[:200]
            raise PlexApiError(
                f"Plex request failed ({response.status_code}): {snippet}",
                status_code=response.status_code,
            )

        return response

    def list_libraries(self, *, type_filter: str | None = None) -> list[PlexLibrary]:
        """List all Plex libraries, optionally filtered by type."""
        response = self._request("GET", "/library/sections")
        payload = _parse_json_response(response)
        container = payload.get("MediaContainer", {})
        directories = container.get("Directory", []) or []
        libraries: list[PlexLibrary] = []
        for entry in directories:
            key = entry.get("key")
            title = entry.get("title")
            lib_type = entry.get("type")
            if key is None or title is None:
                continue
            if type_filter and lib_type != type_filter:
                continue
            libraries.append(PlexLibrary(key=str(key), title=str(title), type=lib_type))
        return libraries

    def find_library(
        self,
        *,
        library_id: str | None,
        library_name: str | None,
        require_type: str | None = "show",
    ) -> str:
        """Find a library by ID or name, optionally requiring a specific type."""
        if library_id:
            # If ID provided, validate it exists and optionally check type
            if require_type:
                libraries = self.list_libraries(type_filter=require_type)
                for lib in libraries:
                    if lib.key == str(library_id):
                        return lib.key
                # ID not found in filtered list; check if it exists at all
                all_libs = self.list_libraries()
                for lib in all_libs:
                    if lib.key == str(library_id):
                        raise PlexApiError(
                            f"Library '{library_id}' exists but is type '{lib.type}', not '{require_type}'"
                        )
                raise PlexApiError(f"Library with ID '{library_id}' not found")
            return str(library_id)

        libraries = self.list_libraries(type_filter=require_type)
        if not library_name:
            raise PlexApiError("Library id or name is required to target Plex")

        for library in libraries:
            if library.title.lower() == library_name.lower():
                return library.key

        available = ", ".join(lib.title for lib in libraries) or "(none)"
        type_msg = f" of type '{require_type}'" if require_type else ""
        raise PlexApiError(f"Plex library '{library_name}'{type_msg} not found (available: {available})")

    def search_show(self, library_id: str, title: str) -> SearchResult:
        """Search for a TV show by title in a library.

        Uses fuzzy matching to handle variations in title formatting:
        - Case insensitive
        - Normalizes hyphens, spaces, and underscores

        The search is done in multiple passes to handle Plex's search behavior:
        1. First try exact title search
        2. Then try with simplified title (first word + numbers only)
        3. Finally do fuzzy matching on results

        Returns:
            SearchResult with result set if match found, or close_matches
            populated with similar titles for debugging when no match.
        """

        # Normalize for fuzzy matching (lowercase, remove hyphens/spaces/underscores)
        def normalize(text: str) -> str:
            return text.lower().replace("-", "").replace(" ", "").replace("_", "")

        target_normalized = normalize(title)
        target_lower = title.lower()

        # Try multiple search strategies
        search_terms = [title]

        # Add simplified search term: extract first word and any numbers
        # e.g., "NHL 2025-2026" -> "NHL 2025" (more likely to match "NHL 2025 2026")
        words = title.split()
        if len(words) > 1:
            # Try first word + first number sequence
            first_word = words[0]
            numbers = re.findall(r"\d+", title)
            if numbers:
                simplified = f"{first_word} {numbers[0]}"
                if simplified.lower() != title.lower():
                    search_terms.append(simplified)

        all_entries: list[dict[str, Any]] = []
        seen_keys: set = set()

        for search_term in search_terms:
            params = {
                "type": PLEX_TYPE_SHOW,
                "title": search_term,
            }
            response = self._request("GET", f"/library/sections/{library_id}/all", params=params)
            payload = _parse_json_response(response)
            metadata_entries = payload.get("MediaContainer", {}).get("Metadata") or []

            for entry in metadata_entries:
                key = entry.get("ratingKey")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    all_entries.append(entry)

        # First pass: exact match (case-insensitive)
        for entry in all_entries:
            entry_title = str(entry.get("title", ""))
            if entry_title.lower() == target_lower:
                return SearchResult(
                    searched_title=title,
                    library_id=library_id,
                    result=entry,
                )

        # Second pass: fuzzy match (normalized - removes hyphens/spaces/underscores)
        for entry in all_entries:
            entry_title = str(entry.get("title", ""))
            if normalize(entry_title) == target_normalized:
                LOGGER.debug(
                    "Fuzzy matched Plex show '%s' to metadata title '%s'",
                    entry_title,
                    title,
                )
                return SearchResult(
                    searched_title=title,
                    library_id=library_id,
                    result=entry,
                )

        # No match found - collect close matches for diagnostics
        close_matches = [str(e.get("title", "?")) for e in all_entries[:5]]

        if close_matches:
            LOGGER.debug(
                "No match for '%s' among Plex results: %s",
                title,
                close_matches,
            )

        return SearchResult(
            searched_title=title,
            library_id=library_id,
            close_matches=close_matches,
            result=None,
        )

    def get_metadata(self, rating_key: str) -> dict[str, Any] | None:
        """Get full metadata for an item by rating key."""
        response = self._request("GET", f"/library/metadata/{rating_key}", allow_error=True)
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise PlexApiError(
                f"Failed to get metadata for {rating_key}: {response.status_code}",
                status_code=response.status_code,
            )
        payload = _parse_json_response(response)
        metadata_list = payload.get("MediaContainer", {}).get("Metadata") or []
        return metadata_list[0] if metadata_list else None

    def list_children(self, rating_key: str) -> list[dict[str, Any]]:
        """List children of an item (e.g., seasons of a show, episodes of a season)."""
        response = self._request("GET", f"/library/metadata/{rating_key}/children")
        payload = _parse_json_response(response)
        return list(payload.get("MediaContainer", {}).get("Metadata") or [])

    def update_metadata(
        self,
        rating_key: str,
        params: dict[str, Any],
        *,
        lock_fields: bool = True,
    ) -> bool:
        """Update metadata fields for an item.

        This method overrides Plex's automatic metadata normalization. For example,
        Plex automatically converts "NTT" to "Ntt" in titles. When lock_fields=True
        (the default), the exact casing provided in params is preserved and locked
        to prevent Plex agents from overwriting it.

        Args:
            rating_key: The Plex rating key of the item.
            params: Dict of field names to values. Use Plex field names (title, sortTitle, etc.)
                    The exact casing provided here will be preserved when lock_fields=True.
            lock_fields: If True, lock fields to prevent Plex agents from overwriting.
                        This is essential for preserving acronym casing like "NTT".

        Returns:
            True if update was performed, False if nothing to update.

        Example:
            # Preserve "NTT" acronym casing (prevents Plex from changing it to "Ntt")
            client.update_metadata(show_key, {"title": "NTT IndyCar Series 2025"})
        """
        clean_params: dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            if key == "type":
                clean_params[key] = value
                continue
            # Add the field value
            clean_params[f"{key}.value"] = value
            # Lock the field to prevent agent overwrites
            if lock_fields:
                clean_params[f"{key}.locked"] = 1

        if not clean_params or (len(clean_params) == 1 and "type" in clean_params):
            return False

        self._request("PUT", f"/library/metadata/{rating_key}", params=clean_params)
        return True

    def unlock_field(self, rating_key: str, field: str) -> None:
        """Unlock a metadata field to allow updates.

        Args:
            rating_key: The Plex rating key of the item.
            field: Field name to unlock (e.g., 'thumb' for poster, 'title', etc.)
        """
        params = {f"{field}.locked": 0}
        self._request("PUT", f"/library/metadata/{rating_key}", params=params)

    def lock_field(self, rating_key: str, field: str) -> None:
        """Lock a metadata field to prevent agent overwrites.

        Args:
            rating_key: The Plex rating key of the item.
            field: Field name to lock (e.g., 'thumb' for poster, 'title', etc.)
        """
        params = {f"{field}.locked": 1}
        self._request("PUT", f"/library/metadata/{rating_key}", params=params)

    def set_asset(self, rating_key: str, element: str, url: str) -> bool:
        """Set an artwork asset (poster/thumb, art/background) from a URL.

        Args:
            rating_key: The Plex rating key of the item.
            element: Asset type - use 'thumb' for poster, 'art' for background.
            url: URL to the image.

        Returns:
            True if successful.
        """
        valid_elements = {"thumb", "art", "banner", "clearLogo", "theme"}
        if element not in valid_elements:
            raise PlexApiError(f"Invalid asset element '{element}'; valid: {valid_elements}")

        params = {"url": url}
        self._request("PUT", f"/library/metadata/{rating_key}/{element}", params=params)
        return True

    def refresh_metadata(self, rating_key: str) -> None:
        """Trigger a metadata refresh for an item."""
        self._request("PUT", f"/library/metadata/{rating_key}/refresh")

    def scan_library(self, library_id: str) -> None:
        """Trigger a library scan to detect new/changed files.

        This is important to call before syncing metadata if files were
        recently added, so Plex knows about them.
        """
        LOGGER.debug("Triggering Plex library scan for library %s", library_id)
        self._request("GET", f"/library/sections/{library_id}/refresh")

    def is_library_scanning(self, library_id: str) -> bool:
        """Check if a library is currently scanning."""
        response = self._request("GET", f"/library/sections/{library_id}")
        payload = _parse_json_response(response)
        container = payload.get("MediaContainer", {})
        directories = container.get("Directory", []) or []
        for directory in directories:
            if str(directory.get("key")) == str(library_id):
                return directory.get("scanning", False)
        # Also check top-level
        return container.get("scanning", False)
