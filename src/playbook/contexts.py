"""Typed context dataclasses for template rendering and tracing.

This module provides strongly-typed dataclasses for contexts used in
destination path building and debug tracing. These replace generic
dict[str, Any] types for better type safety and IDE support.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MatchContext:
    """Template variables for destination path construction.

    This dataclass contains all variables available for rendering
    destination templates. Variables come from sport config, show metadata,
    season/episode info, and regex capture groups.

    Example:
        context = MatchContext(
            sport_id="f1",
            show_title="Formula 1",
            season_title="2024 Bahrain Grand Prix",
            episode_title="Free Practice 1",
            ...
        )
        path = render_template("{show_title}/{season_title}/{episode_title}", context.as_template_dict())
    """

    # Sport info
    sport_id: str
    sport_name: str

    # Show info
    show_id: str
    show_key: str
    show_title: str

    # Season info
    season_key: str
    season_title: str
    season_index: int
    season_number: int

    # Episode info
    episode_title: str
    episode_index: int
    episode_number: int

    # Source file info
    extension: str
    suffix: str
    source_filename: str
    source_stem: str
    relative_source: str

    # Optional fields with defaults (must come after required fields)
    season_round: int | str | None = None
    season_sort_title: str | None = None
    season_slug: str | None = None
    season_year: int | None = None
    episode_summary: str | None = None
    episode_slug: str | None = None
    episode_originally_available: str | None = None
    originally_available: str | None = None  # Alias for episode_originally_available
    source_path: str | None = None
    destination_path: str | None = None
    destination_dir: str | None = None

    # Regex capture groups (for custom template vars)
    groups: dict[str, Any] = field(default_factory=dict)

    def as_template_dict(self) -> dict[str, Any]:
        """Convert to dict for Jinja template rendering.

        Returns a flat dictionary with all non-None fields, with regex capture
        groups merged at the top level for easy access in templates.
        """
        result = asdict(self)
        # Remove the nested groups key
        groups = result.pop("groups", {})
        # Filter out None values (for backwards compatibility)
        result = {k: v for k, v in result.items() if v is not None}
        # Merge regex groups at top level (they can override default values)
        for key, value in groups.items():
            if key not in result:
                result[key] = value
        return result


@dataclass
class TraceContext:
    """Debug/diagnostic information for trace output.

    This dataclass captures all information needed for debugging
    pattern matching issues. It's written to JSON files when
    trace output is enabled.

    Example:
        trace = TraceContext(
            filename="F1.2024.R01.FP1.mkv",
            sport_id="f1",
            status="matched",
            ...
        )
    """

    filename: str
    sport_id: str | None = None
    sport_name: str | None = None
    source_name: str | None = None
    status: str | None = None
    reason: str | None = None
    patterns: list[str] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    destination: str | None = None
    match_context: MatchContext | None = None

    def as_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        result = asdict(self)
        # Handle nested MatchContext
        if result.get("match_context") is not None:
            result["match_context"] = result["match_context"].as_template_dict()
        return result
