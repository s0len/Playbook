from __future__ import annotations

from typing import Any


class TemplateDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_template(template: str, context: dict[str, Any]) -> str:
    enriched = TemplateDict(context)
    return template.format_map(enriched)
