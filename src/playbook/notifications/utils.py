from __future__ import annotations

import logging
from typing import Any

from requests import Response

from .types import NotificationEvent

LOGGER = logging.getLogger(__name__)


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
