"""Destination path building from match context.

This module handles building destination file paths from match context,
including template rendering and path sanitization to ensure files are
written to safe, properly formatted locations.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .contexts import MatchContext
from .templating import render_template
from .utils import sanitize_component, slugify

if TYPE_CHECKING:
    from .config import Settings
    from .matcher import PatternRuntime
    from .metadata_loader import SportRuntime
    from .models import Episode, Season, Show


def build_match_context(
    runtime: SportRuntime,
    source_path: Path,
    season: Season,
    episode: Episode,
    groups: dict[str, Any],
    source_dir: Path,
    show: Show | None = None,
) -> dict[str, Any]:
    """Build template context from match information.

    Args:
        runtime: The sport runtime containing sport and show metadata
        source_path: Path to the source file
        season: The matched season
        episode: The matched episode
        groups: Regex capture groups from pattern matching
        source_dir: Base source directory for relative path calculation
        show: Optional show override (used for dynamic sports where show is loaded per-file)

    Returns:
        Dictionary containing all template variables for rendering

    Note:
        This function returns a dict for backwards compatibility.
        Internally it uses MatchContext for type safety.
    """
    # Use provided show or fall back to runtime.show
    show = show or runtime.show
    if show is None:
        raise ValueError(f"No show metadata available for sport {runtime.sport.id}")
    sport = runtime.sport

    # Calculate derived values
    season_number = season.display_number if season.display_number is not None else season.index
    season_round = (
        season.round_number
        if season.round_number is not None
        else (season.display_number if season.display_number is not None else season.index)
    )
    episode_number = episode.display_number if episode.display_number is not None else episode.index
    originally_available = episode.originally_available.isoformat() if episode.originally_available else ""

    # Extract year from show title if present
    season_year: int | None = None
    year_match = re.search(r"(\d{4})", show.title)
    if year_match:
        season_year = int(year_match.group(1))

    # Build typed context
    match_context = MatchContext(
        sport_id=sport.id,
        sport_name=sport.name,
        show_id=show.key,
        show_key=show.key,
        show_title=show.title,
        season_key=season.key,
        season_title=season.title,
        season_index=season.index,
        season_number=season_number,
        season_round=season_round,
        season_sort_title=season.sort_title or season.title,
        season_slug=slugify(season.title),
        season_year=season_year,
        episode_title=episode.title,
        episode_index=episode.index,
        episode_number=episode_number,
        episode_summary=episode.summary or "",
        episode_slug=slugify(episode.title),
        episode_originally_available=originally_available,
        originally_available=originally_available,
        extension=source_path.suffix.lstrip("."),
        suffix=source_path.suffix,
        source_filename=source_path.name,
        source_stem=source_path.stem,
        relative_source=str(source_path.relative_to(source_dir)),
        groups=dict(groups),
    )

    # Return as dict for backwards compatibility
    return match_context.as_template_dict()


def build_destination(
    runtime: SportRuntime,
    pattern: PatternRuntime,
    context: dict[str, Any],
    settings: Settings,
) -> Path:
    """Build destination path from context using templates.

    Args:
        runtime: The sport runtime containing sport configuration
        pattern: The matched pattern containing template overrides
        context: Template context variables
        settings: Application settings for destination directory

    Returns:
        Resolved destination path

    Raises:
        ValueError: If the destination path escapes the destination directory
    """
    sport = runtime.sport

    destination_root_template = (
        pattern.config.destination_root_template
        or sport.destination.root_template
        or settings.default_destination.root_template
    )
    season_template = (
        pattern.config.season_dir_template
        or sport.destination.season_dir_template
        or settings.default_destination.season_dir_template
    )
    episode_template = (
        pattern.config.filename_template
        or sport.destination.episode_template
        or settings.default_destination.episode_template
    )

    root_component = sanitize_component(render_template(destination_root_template, context))
    season_component = sanitize_component(render_template(season_template, context))
    episode_filename = render_template(episode_template, context)
    episode_component = sanitize_component(episode_filename)

    destination = settings.destination_dir / root_component / season_component / episode_component

    base_dir = settings.destination_dir.resolve()
    destination_resolved = destination.resolve(strict=False)
    if not destination_resolved.is_relative_to(base_dir):
        raise ValueError(f"destination {destination_resolved} escapes destination_dir {base_dir}")

    return destination


def format_relative_destination(destination: Path, destination_dir: Path) -> str:
    """Format destination path as relative to destination directory.

    Args:
        destination: The destination path to format
        destination_dir: The base destination directory

    Returns:
        Relative path string if possible, absolute path string otherwise
    """
    try:
        relative = destination.relative_to(destination_dir)
    except ValueError:
        return str(destination)
    return str(relative)
