from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.parse import urljoin

from .config import AppConfig, SportConfig, load_config
from .metadata import MetadataFingerprintStore, compute_show_fingerprint, load_show
from .models import Episode, Season, Show
from .plex_client import PlexApiError, PlexClient

LOGGER = logging.getLogger(__name__)

METADATA_TYPE = {
    "show": 2,
    "season": 3,
    "episode": 4,
}


@dataclass(slots=True)
class MappedMetadata:
    title: Optional[str]
    sort_title: Optional[str]
    original_title: Optional[str]
    originally_available_at: Optional[str]
    summary: Optional[str]
    poster: Optional[str]
    background: Optional[str]


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Plex metadata from remote YAML before Kometa runs.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/config/playbook.yaml"),
        help="Path to playbook YAML config (defaults to /config/playbook.yaml)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s\n%(message)s\n",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _env_bool(name: str) -> Optional[bool]:
    value = os.getenv(name)
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return None


def _env_list(name: str) -> Optional[List[str]]:
    raw = os.getenv(name)
    if raw is None:
        return None
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    return parts or []


def _as_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first(metadata: Dict[str, object], keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = metadata.get(key)
        if value:
            return str(value)
    return None


def _parse_date(value: object) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    try:
        return dt.date.fromisoformat(str(value).split(" ")[0]).isoformat()
    except ValueError:
        return None


def _resolve_asset(base_url: str, value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return urljoin(base_url.rstrip("/") + "/", value.lstrip("/"))


def _map_show_metadata(show: Show, base_url: str) -> MappedMetadata:
    meta = show.metadata or {}
    return MappedMetadata(
        title=show.title or meta.get("title"),
        sort_title=_first(meta, ("sort_title", "sortTitle", "slug")),
        original_title=_first(meta, ("original_title", "originalTitle")),
        originally_available_at=_parse_date(
            _first(meta, ("originally_available", "originally_available_at"))
        ),
        summary=show.summary or meta.get("summary"),
        poster=_resolve_asset(base_url, _first(meta, ("poster", "thumb", "cover"))),
        background=_resolve_asset(base_url, _first(meta, ("background", "art", "fanart"))),
    )


def _map_season_metadata(season: Season, base_url: str) -> MappedMetadata:
    meta = season.metadata or {}
    return MappedMetadata(
        title=season.title or meta.get("title"),
        sort_title=_first(meta, ("sort_title", "sortTitle", "slug")),
        original_title=_first(meta, ("original_title", "originalTitle")),
        originally_available_at=_parse_date(
            _first(meta, ("originally_available", "originally_available_at"))
        ),
        summary=season.summary or meta.get("summary"),
        poster=_resolve_asset(base_url, _first(meta, ("poster", "thumb", "cover"))),
        background=_resolve_asset(base_url, _first(meta, ("background", "art", "fanart"))),
    )


def _map_episode_metadata(episode: Episode, base_url: str) -> MappedMetadata:
    meta = episode.metadata or {}
    return MappedMetadata(
        title=episode.title or meta.get("title"),
        sort_title=_first(meta, ("sort_title", "sortTitle", "slug")),
        original_title=_first(meta, ("original_title", "originalTitle")),
        originally_available_at=_parse_date(
            _first(meta, ("originally_available", "originally_available_at")) or episode.originally_available
        ),
        summary=episode.summary or meta.get("summary"),
        poster=_resolve_asset(base_url, _first(meta, ("poster", "thumb", "cover"))),
        background=_resolve_asset(base_url, _first(meta, ("background", "art", "fanart"))),
    )


def _match_season_key(plex_seasons: List[Dict[str, object]], season: Season) -> Optional[str]:
    target_numbers = {season.display_number, season.index}
    target_numbers = {num for num in target_numbers if num is not None}
    target_title = (season.title or "").lower()
    for entry in plex_seasons:
        rating_key = entry.get("ratingKey")
        if not rating_key:
            continue
        numbers = {
            _as_int(entry.get("index")),
            _as_int(entry.get("seasonNumber")),
            _as_int(entry.get("parentIndex")),
        }
        if target_numbers & {num for num in numbers if num is not None}:
            return str(rating_key)
        if target_title and str(entry.get("title") or "").lower() == target_title:
            return str(rating_key)
    return None


def _match_episode_key(plex_episodes: List[Dict[str, object]], episode: Episode) -> Optional[str]:
    target_numbers = {episode.display_number, episode.index}
    target_numbers = {num for num in target_numbers if num is not None}
    target_title = (episode.title or "").lower()
    for entry in plex_episodes:
        rating_key = entry.get("ratingKey")
        if not rating_key:
            continue
        numbers = {
            _as_int(entry.get("index")),
            _as_int(entry.get("parentIndex")),
        }
        if target_numbers & {num for num in numbers if num is not None}:
            return str(rating_key)
        if target_title and str(entry.get("title") or "").lower() == target_title:
            return str(rating_key)
    return None


def _apply_metadata(
    client: PlexClient,
    rating_key: str,
    mapped: MappedMetadata,
    *,
    type_code: int,
    label: str,
    dry_run: bool,
) -> None:
    fields = {
        "type": type_code,
        "title": mapped.title,
        "sortTitle": mapped.sort_title,
        "originalTitle": mapped.original_title,
        "originallyAvailableAt": mapped.originally_available_at,
        "summary": mapped.summary,
    }
    fields = {key: value for key, value in fields.items() if value}
    if fields:
        if dry_run:
            LOGGER.info("Dry-run: would update %s %s with %s", label, rating_key, fields)
        else:
            client.update_metadata(rating_key, fields)
            LOGGER.info("Updated %s metadata (%s)", label, rating_key)
    for asset_field, element in (("poster", "poster"), ("background", "art")):
        asset_url = getattr(mapped, asset_field)
        if not asset_url:
            continue
        if dry_run:
            LOGGER.info("Dry-run: would set %s %s %s to %s", label, rating_key, element, asset_url)
        else:
            client.set_asset(rating_key, element, asset_url)
            LOGGER.info("Updated %s %s asset (%s)", label, element, rating_key)


def _load_show(config: AppConfig, sport: SportConfig) -> Show:
    return load_show(config.settings, sport.metadata)


def _sync_single_sport(
    *,
    client: PlexClient,
    library_id: str,
    config: AppConfig,
    sport: SportConfig,
    fingerprint_store: MetadataFingerprintStore,
    force: bool,
    dry_run: bool,
) -> None:
    show = _load_show(config, sport)
    previous_fingerprint = fingerprint_store.get(sport.id)
    fingerprint = compute_show_fingerprint(show, sport.metadata)
    change = fingerprint_store.update(sport.id, fingerprint)
    is_first_sync = previous_fingerprint is None

    should_update_show = force or change.updated
    plex_show = client.search_show(library_id, show.title)
    if plex_show is None:
        LOGGER.error("Plex show not found for '%s' in library %s", show.title, library_id)
        return
    show_rating = str(plex_show.get("ratingKey"))
    if not show_rating:
        LOGGER.error("Plex show ratingKey missing for '%s'", show.title)
        return

    base_url = sport.metadata.url
    mapped_show = _map_show_metadata(show, base_url)
    if should_update_show:
        _apply_metadata(client, show_rating, mapped_show, type_code=METADATA_TYPE["show"], label="show", dry_run=dry_run)

    plex_seasons = client.list_children(show_rating)
    seasons_to_update: List[Season] = []
    if force or change.invalidate_all or is_first_sync:
        seasons_to_update = list(show.seasons)
    elif change.changed_seasons:
        seasons_to_update = [season for season in show.seasons if str(season.key) in change.changed_seasons]

    for season in seasons_to_update:
        season_rating = _match_season_key(plex_seasons, season)
        if not season_rating:
            LOGGER.warning("Season not found in Plex for %s: %s", show.title, season.title)
            continue
        mapped_season = _map_season_metadata(season, base_url)
        _apply_metadata(
            client,
            season_rating,
            mapped_season,
            type_code=METADATA_TYPE["season"],
            label=f"season '{season.title}'",
            dry_run=dry_run,
        )

    for season in show.seasons:
        season_rating = _match_season_key(plex_seasons, season)
        if not season_rating:
            LOGGER.warning("Skipping episodes; season not found in Plex for %s: %s", show.title, season.title)
            continue
        plex_episodes = client.list_children(season_rating)
        for episode in season.episodes:
            episode_rating = _match_episode_key(plex_episodes, episode)
            if not episode_rating:
                LOGGER.warning(
                    "Episode not found in Plex for %s / %s: %s",
                    show.title,
                    season.title,
                    episode.title,
                )
                continue
            mapped_episode = _map_episode_metadata(episode, base_url)
            _apply_metadata(
                client,
                episode_rating,
                mapped_episode,
                type_code=METADATA_TYPE["episode"],
                label=f"episode '{episode.title}'",
                dry_run=dry_run,
            )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.verbose)
    try:
        config = load_config(args.config)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Failed to load config: %s", exc)
        return 1

    plex_cfg = config.settings.plex_sync

    env_enabled = _env_bool("PLEX_SYNC_ENABLED")
    enabled = plex_cfg.enabled if env_enabled is None else env_enabled
    if not enabled:
        LOGGER.info("Plex metadata sync is disabled; set settings.plex_metadata_sync.enabled or PLEX_SYNC_ENABLED=true")
        return 0

    plex_url = os.getenv("PLEX_URL") or plex_cfg.url
    plex_token = os.getenv("PLEX_TOKEN") or plex_cfg.token
    plex_library_id = os.getenv("PLEX_LIBRARY_ID") or plex_cfg.library_id
    plex_library_name = os.getenv("PLEX_LIBRARY_NAME") or plex_cfg.library_name

    env_timeout = os.getenv("PLEX_TIMEOUT")
    try:
        timeout = float(env_timeout) if env_timeout is not None else plex_cfg.timeout
    except ValueError:
        LOGGER.error("Invalid PLEX_TIMEOUT value; must be numeric")
        return 1

    env_force = _env_bool("PLEX_FORCE")
    env_dry_run = _env_bool("PLEX_SYNC_DRY_RUN")
    force = plex_cfg.force if env_force is None else env_force
    dry_run = plex_cfg.dry_run if env_dry_run is None else env_dry_run

    env_sports = _env_list("PLEX_SPORTS")
    sports_filter = env_sports if env_sports is not None else plex_cfg.sports

    if not plex_url or not plex_token:
        LOGGER.error("Plex URL and token are required (configure settings.plex_metadata_sync or env PLEX_URL/PLEX_TOKEN)")
        return 1

    if not plex_library_id and not plex_library_name:
        LOGGER.error("Provide a Plex library id or name (settings.plex_metadata_sync.library_id / library_name or env PLEX_LIBRARY_ID / PLEX_LIBRARY_NAME)")
        return 1

    client = PlexClient(plex_url, plex_token, timeout=timeout)
    try:
        library_id = client.find_library(library_id=plex_library_id, library_name=plex_library_name)
    except PlexApiError as exc:
        LOGGER.error("%s", exc)
        return 2

    fingerprint_store = MetadataFingerprintStore(config.settings.cache_dir, filename="plex-metadata-hashes.json")
    sports = (
        [sport for sport in config.sports if sport.id in set(sports_filter)]
        if sports_filter
        else list(config.sports)
    )
    if not sports:
        LOGGER.info("No sports selected; exiting")
        return 0

    for sport in sports:
        try:
            _sync_single_sport(
                client=client,
                library_id=library_id,
                config=config,
                sport=sport,
                fingerprint_store=fingerprint_store,
                force=force,
                dry_run=dry_run,
            )
        except PlexApiError as exc:
            LOGGER.error("Plex API error for sport %s: %s", sport.id, exc)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Unexpected error while syncing %s: %s", sport.id, exc)

    fingerprint_store.save()
    LOGGER.info("Completed Plex metadata sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())

