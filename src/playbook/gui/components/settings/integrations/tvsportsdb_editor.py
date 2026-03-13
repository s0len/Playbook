"""TVSportsDB integration card (informational, not editable)."""

from __future__ import annotations

INTEGRATION_META = {
    "key": "tvsportsdb",
    "label": "TVSportsDB",
    "icon": "sports",
    "description": "Metadata source for sports shows, seasons, and episodes",
    "config_path": "settings.tvsportsdb",
    "env_vars": [],
    "website": "https://www.tvsportsdb.com",
}


def is_active(data: dict) -> bool:
    return bool(data.get("base_url"))


def summary(data: dict) -> str:
    return "Connected" if data.get("base_url") else "Not configured"


open_dialog = None  # No editable dialog — card links to website instead
