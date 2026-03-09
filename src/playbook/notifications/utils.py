from __future__ import annotations

import fnmatch
import logging
from typing import Any

from requests import Response

from .types import NotificationEvent

LOGGER = logging.getLogger(__name__)


# Shared constants and helpers used across notification targets

REPLACE_REASON_LABELS: dict[str, str] = {
    "quality_upgrade": "quality upgrade",
    "proper_repack": "PROPER/REPACK",
    "mismatch_correction": "mismatch corrected",
    "legacy": "replaced existing",
}


def replace_reason_label(reason: str | None) -> str:
    """Get a human-readable label for a replace reason."""
    if not reason:
        return "replaced existing"
    return REPLACE_REASON_LABELS.get(reason, "replaced existing")


def is_wildcard(value: str) -> bool:
    """Check if a string contains wildcard characters."""
    return any(char in value for char in "*?[")


def sport_prefixes(sport_id: str) -> list[str]:
    """Generate parent prefixes for a sport ID.

    E.g. "premier_league_2025_26" -> ["premier_league_2025", "premier_league", "premier"]
    """
    parts = sport_id.split("_")
    prefixes: list[str] = []
    for end in range(len(parts) - 1, 0, -1):
        prefixes.append("_".join(parts[:end]))
    return prefixes


def resolve_sport_match(sport_id: str, mapping: dict[str, Any]) -> Any | None:
    """Resolve a value from a sport-keyed mapping using exact, prefix, and wildcard matching.

    Returns the matched value, or None if no match found.
    """
    # 1. Exact match
    if sport_id in mapping:
        return mapping[sport_id]

    # 2. Parent prefixes
    for candidate in sport_prefixes(sport_id):
        if candidate in mapping:
            return mapping[candidate]

    # 3. Wildcard patterns
    wildcard_matches = [
        (pattern, value)
        for pattern, value in mapping.items()
        if is_wildcard(pattern) and fnmatch.fnmatchcase(sport_id, pattern)
    ]
    if wildcard_matches:
        wildcard_matches.sort(key=lambda item: len(item[0]), reverse=True)
        return wildcard_matches[0][1]

    return None


def _normalize_mentions_map(value: Any) -> dict[str, str]:
    """Normalize a raw mentions configuration into a dictionary of string-to-string mappings."""
    if not value:
        return {}
    if not isinstance(value, dict):
        LOGGER.warning("Ignoring discord target mentions because value is not a mapping")
        return {}
    mentions: dict[str, str] = {}
    for key, raw_value in value.items():
        if raw_value is None:
            continue
        key_str = str(key).strip()
        if not key_str:
            continue
        mention = str(raw_value).strip()
        if not mention:
            continue
        mentions[key_str] = mention
    return mentions


def _flatten_event(event: NotificationEvent) -> dict[str, Any]:
    """Convert a NotificationEvent into a flat dictionary for templating."""
    data = {
        "sport_id": event.sport_id,
        "sport_name": event.sport_name,
        "show_title": event.show_title,
        "season": event.season,
        "session": event.session,
        "episode": event.episode,
        "summary": event.summary,
        "destination": event.destination,
        "source": event.source,
        "action": event.action,
        "link_mode": event.link_mode,
        "replaced": event.replaced,
        "skip_reason": event.skip_reason,
        "trace_path": event.trace_path,
        "timestamp": event.timestamp.isoformat(),
        "event_type": event.event_type,
        "replace_reason": event.replace_reason,
        "quality_str": event.quality_str,
        "old_quality_str": event.old_quality_str,
        "quality_score": event.quality_score,
        "old_quality_score": event.old_quality_score,
        "file_size": event.file_size,
        "old_file_size": event.old_file_size,
    }
    data.update(event.match_details or {})
    return data


def _render_template(template: Any, data: dict[str, Any]) -> Any:
    """Recursively render template structures by formatting strings with the provided data."""
    if isinstance(template, dict):
        return {key: _render_template(value, data) for key, value in template.items()}
    if isinstance(template, list):
        return [_render_template(value, data) for value in template]
    if isinstance(template, str):
        try:
            return template.format(**data)
        except Exception:
            return template
    return template


def _trim(value: str, limit: int) -> str:
    """Trim a string to a maximum length, appending '...' if truncated."""
    stripped = value.strip()
    if len(stripped) <= limit:
        return stripped
    if limit <= 3:
        return stripped[:limit]
    return stripped[: limit - 3] + "..."


def _excerpt_response(response: Response) -> str:
    """Extract a short excerpt from an HTTP response for logging purposes."""
    try:
        text = response.text
    except Exception:  # pragma: no cover - defensive fallback
        return "<no response body>"
    return _trim(text or "<empty>", 200)
