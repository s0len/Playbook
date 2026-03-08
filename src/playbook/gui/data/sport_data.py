"""
Sport data provider for the Playbook GUI.

Combines metadata from TVSportsDB with processed file records
to provide match status tracking for the Sports page.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from playbook.persistence import ProcessedFileRecord

from ..state import gui_state

LOGGER = logging.getLogger(__name__)


MatchStatus = Literal["matched", "missing", "error"]


@dataclass
class EpisodeMatchStatus:
    """Match status for a single episode."""

    episode_index: int
    episode_title: str
    air_date: date | None
    status: MatchStatus
    record: ProcessedFileRecord | None = None
    all_records: list[ProcessedFileRecord] = field(default_factory=list)

    @property
    def formatted_code(self) -> str:
        """Return formatted episode code like E01."""
        return f"E{self.episode_index:02d}"

    @property
    def file_count(self) -> int:
        """Number of source files tracked for this episode."""
        return len(self.all_records)


@dataclass
class SeasonMatchStatus:
    """Match status for a season with all its episodes."""

    season_index: int
    season_title: str
    episodes: list[EpisodeMatchStatus] = field(default_factory=list)
    year_label: str | None = None  # Year grouping for dynamic sports (e.g., "2026")

    @property
    def matched_count(self) -> int:
        """Number of matched episodes."""
        return sum(1 for e in self.episodes if e.status == "matched")

    @property
    def total_count(self) -> int:
        """Total number of episodes."""
        return len(self.episodes)

    @property
    def progress(self) -> float:
        """Progress as a float 0-1."""
        if self.total_count == 0:
            return 0.0
        return self.matched_count / self.total_count

    @property
    def formatted_code(self) -> str:
        """Return formatted season code like S01."""
        return f"S{self.season_index:02d}"


@dataclass
class SourceGlobInfo:
    """Information about a source glob pattern."""

    pattern: str
    is_default: bool  # True if from pattern template, False if user-added
    is_disabled: bool  # True if in disabled_source_globs


@dataclass
class SportDetail:
    """Complete sport detail with all seasons and match status."""

    sport_id: str
    sport_name: str
    show_slug: str
    seasons: list[SeasonMatchStatus] = field(default_factory=list)
    enabled: bool = True
    link_mode: str = "hardlink"
    # Source glob information
    source_globs: list[SourceGlobInfo] = field(default_factory=list)
    pattern_set_names: list[str] = field(default_factory=list)
    metadata_error: str | None = None  # Error message if metadata loading failed

    @property
    def overall_matched(self) -> int:
        """Total matched episodes across all seasons."""
        return sum(s.matched_count for s in self.seasons)

    @property
    def overall_total(self) -> int:
        """Total episodes across all seasons."""
        return sum(s.total_count for s in self.seasons)

    @property
    def overall_progress(self) -> float:
        """Overall progress as a float 0-1."""
        if self.overall_total == 0:
            return 0.0
        return self.overall_matched / self.overall_total

    @property
    def recent_season(self) -> SeasonMatchStatus | None:
        """Get the most recent season (last in list)."""
        return self.seasons[-1] if self.seasons else None


@dataclass
class SportOverview:
    """Summary overview for the sports list page."""

    sport_id: str
    sport_name: str
    show_slug: str
    enabled: bool
    link_mode: str
    pattern_count: int
    extensions: list[str]
    matched_count: int
    total_count: int

    @property
    def progress(self) -> float:
        """Progress as a float 0-1."""
        if self.total_count == 0:
            return 0.0
        return self.matched_count / self.total_count


def get_sport_detail(sport_id: str) -> SportDetail | None:
    """Get detailed sport information with match status.

    Combines sport configuration, show metadata, and processed file records
    to build a complete picture of which episodes have been matched.

    Args:
        sport_id: The sport identifier

    Returns:
        SportDetail with all seasons and episode match status,
        or None if sport not found
    """
    if not gui_state.config:
        LOGGER.debug("get_sport_detail: no config")
        return None

    # Find sport config
    sport_config = None
    for sport in gui_state.config.sports:
        if sport.id == sport_id:
            sport_config = sport
            break

    if not sport_config:
        LOGGER.debug("get_sport_detail: sport %s not found in config", sport_id)
        return None

    # Build source glob info list
    source_glob_info = _build_source_glob_info(sport_config)

    # For display, prefer show_slug, fall back to template
    display_slug = sport_config.show_slug or sport_config.show_slug_template or ""

    # Create base detail
    detail = SportDetail(
        sport_id=sport_config.id,
        sport_name=sport_config.name,
        show_slug=display_slug,
        enabled=sport_config.enabled,
        link_mode=sport_config.link_mode,
        source_globs=source_glob_info,
        pattern_set_names=sport_config.pattern_set_names,
    )

    # Try to load show metadata
    show, metadata_error = _load_show_metadata(sport_config)
    if not show:
        detail.metadata_error = metadata_error or "Failed to load metadata"
        LOGGER.warning("get_sport_detail: failed to load metadata for %s: %s", sport_id, detail.metadata_error)
        return detail

    LOGGER.debug(
        "get_sport_detail: loaded show %s with %d seasons",
        show.key,
        len(show.seasons),
    )

    # Get processed records for this sport and all sibling variants
    # (variants that share the same name and show_slug are merged in the overview)
    sibling_ids = _get_sibling_sport_ids(sport_config)
    records_by_episode: dict[tuple[str, int, int], list[ProcessedFileRecord]] = {}
    for sid in sibling_ids:
        for key, recs in _get_records_by_episode(sid).items():
            records_by_episode.setdefault(key, []).extend(recs)
    # Re-sort merged records by quality_score descending
    for key in records_by_episode:
        records_by_episode[key].sort(key=lambda r: r.quality_score or 0, reverse=True)
    LOGGER.debug(
        "get_sport_detail: found %d episode keys across %d sibling sport(s) %s",
        len(records_by_episode),
        len(sibling_ids),
        sibling_ids,
    )

    # Log sample of record keys for debugging
    if records_by_episode:
        sample_keys = list(records_by_episode.keys())[:5]
        LOGGER.debug("get_sport_detail: sample record keys (season, episode): %s", sample_keys)

    # Build season/episode status
    for season in show.seasons:
        season_status = SeasonMatchStatus(
            season_index=season.index,
            season_title=season.title,
            year_label=season.metadata.get("_year_label"),
        )

        # For dynamic sports, use the season's show_slug to scope record lookups;
        # for static sports the show key is the same for all seasons.
        season_show_slug = season.metadata.get("_show_slug") or show.key

        matched_in_season = 0
        for episode in season.episodes:
            # Check if we have records for this episode
            key = (season_show_slug, season.index, episode.index)
            episode_records = records_by_episode.get(key, [])
            # Best record is first (sorted by quality_score descending)
            best_record = episode_records[0] if episode_records else None

            if best_record:
                if best_record.status == "error":
                    status: MatchStatus = "error"
                elif not Path(best_record.destination_path).exists():
                    # DB says matched but file is gone from disk — treat as missing
                    status = "missing"
                else:
                    status = "matched"
                    matched_in_season += 1
            else:
                status = "missing"

            episode_status = EpisodeMatchStatus(
                episode_index=episode.index,
                episode_title=episode.title,
                air_date=episode.originally_available,
                status=status,
                record=best_record,
                all_records=episode_records,
            )
            season_status.episodes.append(episode_status)

        LOGGER.debug(
            "get_sport_detail: season %d (%s) has %d episodes, %d matched",
            season.index,
            season.title,
            len(season.episodes),
            matched_in_season,
        )
        detail.seasons.append(season_status)

    return detail


def get_sports_overview() -> list[SportOverview]:
    """Get overview information for all sports.

    This function is optimized for fast loading - it only queries the local
    database and does NOT make network requests to load metadata. Total episode
    counts are not available in the list view to avoid blocking the UI.

    Variants that share the same (name, show_slug) are merged into a single
    row with summed matched counts (e.g. NFL 2025 + NFL 2026 → one NFL row).

    Returns:
        List of SportOverview for the sports list page
    """
    if not gui_state.config:
        return []

    # Group variants by (name, show_slug) to merge cross-year duplicates
    merged: dict[tuple[str, str], SportOverview] = {}

    for sport in gui_state.config.sports:
        # Get processed records count from local database only (fast)
        matched_count = 0
        if gui_state.processed_store:
            try:
                records = gui_state.processed_store.get_by_sport(sport.id)
                matched_count = len([r for r in records if r.status != "error"])
            except Exception as e:
                LOGGER.warning("Failed to get processed records for %s: %s", sport.id, e)

        display_slug = sport.show_slug or sport.show_slug_template or ""
        merge_key = (sport.name, display_slug)

        if merge_key in merged:
            # Add matched count to existing entry
            merged[merge_key].matched_count += matched_count
        else:
            merged[merge_key] = SportOverview(
                sport_id=sport.id,
                sport_name=sport.name,
                show_slug=display_slug,
                enabled=sport.enabled,
                link_mode=sport.link_mode,
                pattern_count=len(sport.patterns),
                extensions=sport.source_extensions,
                matched_count=matched_count,
                total_count=0,
            )

    return list(merged.values())


def _load_show_metadata(sport_config) -> tuple:
    """Load show metadata for a sport.

    For dynamic sports (using show_slug_template), loads metadata for all
    tracked years (discovered from processed records and fingerprint store)
    and merges them into a single virtual Show.

    Args:
        sport_config: Sport configuration

    Returns:
        Tuple of (Show model or None, error message or None)
    """
    if not gui_state.config:
        return None, "No configuration available"

    try:
        # For dynamic sports, load metadata for all known years
        if sport_config.show_slug_template and not sport_config.show_slug:
            show, error = _load_dynamic_show_metadata(sport_config)
            return show, error

        # For static sports, use the regular loader
        from playbook.metadata_loader import load_sports

        result = load_sports(
            sports=[sport_config],
            settings=gui_state.config.settings,
            metadata_fingerprints=None,
        )

        if result.runtimes:
            return result.runtimes[0].show, None
        return None, f"No metadata found for slug '{sport_config.show_slug}'"
    except Exception as e:
        LOGGER.warning("Failed to load metadata for %s: %s", sport_config.id, e, exc_info=True)
        return None, f"{type(e).__name__}: {e}"


def _load_dynamic_show_metadata(sport_config) -> tuple:
    """Load and merge metadata for all tracked years of a dynamic sport.

    Discovers years from processed records (show_id field) and also tries
    the current year. Returns a merged Show with year labels on each season
    (stored in season.metadata["_year_label"]) for UI grouping.

    Args:
        sport_config: Sport configuration with show_slug_template

    Returns:
        Tuple of (Merged Show model or None, error message or None)
    """
    from datetime import datetime

    from playbook.metadata_loader import DynamicMetadataLoader
    from playbook.models import Show

    # Discover which years have been processed (check all sibling variants)
    tracked_slugs: set[str] = set()
    if gui_state.processed_store:
        for sid in _get_sibling_sport_ids(sport_config):
            show_ids = gui_state.processed_store.get_show_ids_for_sport(sid)
            tracked_slugs.update(show_ids)

    # Always try current year (may not have processed files yet)
    current_year = datetime.now().year
    current_slug = sport_config.resolve_show_slug(current_year)
    if current_slug:
        tracked_slugs.add(current_slug)

    if not tracked_slugs:
        return None, f"No slugs to try (template: {sport_config.show_slug_template})"

    LOGGER.debug(
        "_load_dynamic_show_metadata: sport=%s slugs_to_try=%s",
        sport_config.id,
        sorted(tracked_slugs),
    )

    loader = DynamicMetadataLoader(
        gui_state.config.settings,
        cache_dir=gui_state.config.settings.cache_dir,
    )
    try:
        shows: list[tuple[str, Show]] = []  # (slug, show) pairs
        failed_slugs: list[str] = []
        for slug in sorted(tracked_slugs):
            try:
                show = loader.load_show(slug, sport_config.season_overrides)
                if show:
                    LOGGER.debug(
                        "_load_dynamic_show_metadata: loaded %s (%d seasons, %d episodes)",
                        slug,
                        len(show.seasons),
                        sum(len(s.episodes) for s in show.seasons),
                    )
                    shows.append((slug, show))
                else:
                    LOGGER.warning("_load_dynamic_show_metadata: slug %s returned no data", slug)
                    failed_slugs.append(slug)
            except Exception as e:
                LOGGER.warning("_load_dynamic_show_metadata: failed to load %s: %s", slug, e, exc_info=True)
                failed_slugs.append(slug)

        if not shows:
            tried = ", ".join(sorted(tracked_slugs))
            return None, f"All slugs failed to load: {tried}"

        # If only one year, return it directly (no year labels needed)
        if len(shows) == 1:
            return shows[0][1], None

        # Merge all years into a single virtual Show with year labels
        merged = Show(
            key=sport_config.id,
            title=sport_config.name,
            summary=None,
            seasons=[],
            metadata={},
        )
        for slug, show in shows:
            # Extract year from slug using the template pattern
            year_label = _extract_year_from_slug(slug, sport_config.show_slug_template) or slug
            for season in show.seasons:
                season.metadata["_year_label"] = year_label
                season.metadata["_show_slug"] = slug
            merged.seasons.extend(show.seasons)

        return merged, None
    finally:
        loader.close()


def _extract_year_from_slug(slug: str, template: str | None) -> str | None:
    """Extract the year portion from a resolved slug using the template.

    E.g., slug="formula-1-2026", template="formula-1-{year}" → "2026"
    """
    if not template or "{year}" not in template:
        return None
    prefix, _, suffix = template.partition("{year}")
    if not slug.startswith(prefix):
        return None
    remainder = slug[len(prefix) :]
    if suffix and remainder.endswith(suffix):
        remainder = remainder[: -len(suffix)]
    return remainder


def _build_source_glob_info(sport_config) -> list[SourceGlobInfo]:
    """Build source glob info list combining defaults, extras, and disabled.

    Args:
        sport_config: Sport configuration

    Returns:
        List of SourceGlobInfo objects
    """
    from playbook.pattern_templates import get_default_source_globs

    disabled_globs = set(sport_config.disabled_source_globs)

    result: list[SourceGlobInfo] = []

    # Add default globs first
    for pattern in get_default_source_globs(sport_config.pattern_set_names):
        if pattern not in {g.pattern for g in result}:  # Avoid duplicates
            result.append(
                SourceGlobInfo(
                    pattern=pattern,
                    is_default=True,
                    is_disabled=pattern in disabled_globs,
                )
            )

    # Add extra (custom) globs
    for pattern in sport_config.extra_source_globs:
        if pattern not in {g.pattern for g in result}:  # Avoid duplicates
            result.append(
                SourceGlobInfo(
                    pattern=pattern,
                    is_default=False,
                    is_disabled=pattern in disabled_globs,
                )
            )

    return result


def _get_sibling_sport_ids(sport_config) -> list[str]:
    """Find all sport config IDs that share the same (name, show_slug) merge key.

    This matches the merge logic in get_sports_overview() so that the detail
    view aggregates records from all variants that appear as one row.
    """
    if not gui_state.config:
        return [sport_config.id]

    display_slug = sport_config.show_slug or sport_config.show_slug_template or ""
    merge_key = (sport_config.name, display_slug)

    siblings = []
    for sport in gui_state.config.sports:
        other_slug = sport.show_slug or sport.show_slug_template or ""
        if (sport.name, other_slug) == merge_key:
            siblings.append(sport.id)

    return siblings or [sport_config.id]


def _get_records_by_episode(sport_id: str) -> dict[tuple[str, int, int], list[ProcessedFileRecord]]:
    """Get processed records indexed by (show_id, season_index, episode_index).

    Returns ALL records per episode (multiple source files may target the same
    episode at different quality levels), sorted by quality_score descending
    so the best file is first.

    Args:
        sport_id: The sport identifier

    Returns:
        Dict mapping (show_id, season_index, episode_index) to list of records
    """
    if not gui_state.processed_store:
        LOGGER.debug("_get_records_by_episode: processed_store is None")
        return {}

    try:
        records = gui_state.processed_store.get_by_sport(sport_id)
        LOGGER.debug(
            "_get_records_by_episode: got %d records from store for sport %s",
            len(records),
            sport_id,
        )
        result: dict[tuple[str, int, int], list[ProcessedFileRecord]] = {}
        for r in records:
            key = (r.show_id, r.season_index, r.episode_index)
            result.setdefault(key, []).append(r)
        # Sort each episode's records: active statuses first, then by quality_score descending
        _ACTIVE_STATUSES = {"linked", "copied", "symlinked"}
        for key in result:
            result[key].sort(key=lambda r: (r.status not in _ACTIVE_STATUSES, -(r.quality_score or 0)))
        return result
    except Exception as e:
        LOGGER.warning("Failed to get processed records for %s: %s", sport_id, e)
        return {}
