"""
Sport data provider for the Playbook GUI.

Combines metadata from TheTVSportsDB with processed file records
to provide match status tracking for the Sports page.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
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

    @property
    def formatted_code(self) -> str:
        """Return formatted episode code like E01."""
        return f"E{self.episode_index:02d}"


@dataclass
class SeasonMatchStatus:
    """Match status for a season with all its episodes."""

    season_index: int
    season_title: str
    episodes: list[EpisodeMatchStatus] = field(default_factory=list)

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
    show = _load_show_metadata(sport_config)
    if not show:
        LOGGER.warning("get_sport_detail: failed to load metadata for %s", sport_id)
        return detail

    LOGGER.debug(
        "get_sport_detail: loaded show %s with %d seasons",
        show.key,
        len(show.seasons),
    )

    # Get processed records for this sport
    records_by_episode = _get_records_by_episode(sport_id)
    LOGGER.debug(
        "get_sport_detail: found %d processed records for %s",
        len(records_by_episode),
        sport_id,
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
        )

        matched_in_season = 0
        for episode in season.episodes:
            # Check if we have a record for this episode
            key = (season.index, episode.index)
            record = records_by_episode.get(key)

            if record:
                status: MatchStatus = "matched" if record.status != "error" else "error"
                matched_in_season += 1
            else:
                status = "missing"

            episode_status = EpisodeMatchStatus(
                episode_index=episode.index,
                episode_title=episode.title,
                air_date=episode.originally_available,
                status=status,
                record=record,
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

    Returns:
        List of SportOverview for the sports list page
    """
    if not gui_state.config:
        return []

    overviews = []

    for sport in gui_state.config.sports:
        # Get processed records count from local database only (fast)
        matched_count = 0
        if gui_state.processed_store:
            try:
                records = gui_state.processed_store.get_by_sport(sport.id)
                matched_count = len([r for r in records if r.status != "error"])
            except Exception as e:
                LOGGER.warning("Failed to get processed records for %s: %s", sport.id, e)

        # Note: total_count is 0 here - we don't load metadata in the list view
        # to avoid blocking network requests. Full counts are shown in detail view.
        # For display, prefer show_slug, fall back to template
        display_slug = sport.show_slug or sport.show_slug_template or ""

        overview = SportOverview(
            sport_id=sport.id,
            sport_name=sport.name,
            show_slug=display_slug,
            enabled=sport.enabled,
            link_mode=sport.link_mode,
            pattern_count=len(sport.patterns),
            extensions=sport.source_extensions,
            matched_count=matched_count,
            total_count=0,  # Not loaded in list view for performance
        )
        overviews.append(overview)

    return overviews


def _load_show_metadata(sport_config):
    """Load show metadata for a sport.

    For dynamic sports (using show_slug_template), loads metadata for the current year.

    Args:
        sport_config: Sport configuration

    Returns:
        Show model or None
    """
    if not gui_state.config:
        return None

    try:
        # For dynamic sports, try loading metadata for recent years
        if sport_config.show_slug_template and not sport_config.show_slug:
            from datetime import datetime

            from playbook.metadata_loader import DynamicMetadataLoader

            loader = DynamicMetadataLoader(
                gui_state.config.settings,
                cache_dir=gui_state.config.settings.cache_dir,
            )
            try:
                current_year = datetime.now().year
                # Try current year first, then previous year as fallback
                for year in [current_year, current_year - 1]:
                    show = loader.get_show_for_year(sport_config, year)
                    if show:
                        return show
                return None
            finally:
                loader.close()

        # For static sports, use the regular loader
        from playbook.metadata_loader import load_sports

        result = load_sports(
            sports=[sport_config],
            settings=gui_state.config.settings,
            metadata_fingerprints=None,
        )

        if result.runtimes:
            return result.runtimes[0].show
    except Exception as e:
        LOGGER.warning("Failed to load metadata for %s: %s", sport_config.id, e)

    return None


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


def _get_records_by_episode(sport_id: str) -> dict[tuple[int, int], ProcessedFileRecord]:
    """Get processed records indexed by (season_index, episode_index).

    Args:
        sport_id: The sport identifier

    Returns:
        Dict mapping (season_index, episode_index) to record
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
        if records:
            # Log first record for debugging
            r = records[0]
            LOGGER.debug(
                "_get_records_by_episode: sample record - season_index=%d, episode_index=%d, source=%s",
                r.season_index,
                r.episode_index,
                r.source_path,
            )
        return {(r.season_index, r.episode_index): r for r in records}
    except Exception as e:
        LOGGER.warning("Failed to get processed records for %s: %s", sport_id, e)
        return {}
