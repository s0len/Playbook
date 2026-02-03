from __future__ import annotations

import datetime as dt
import re
import shlex
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .pattern_templates import expand_regex_with_tokens, load_builtin_pattern_sets
from .utils import load_yaml_file, validate_url


@dataclass
class SeasonSelector:
    mode: str = "round"  # round | key | title | sequential | date
    group: str | None = None
    offset: int = 0
    mapping: dict[str, int] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    value_template: str | None = None


@dataclass
class EpisodeSelector:
    group: str = "session"
    allow_fallback_to_title: bool = True
    default_value: str | None = None


@dataclass
class TVSportsDBConfig:
    """Configuration for TheTVSportsDB API cache and timeout settings."""

    base_url: str = "http://localhost:8000"
    ttl_hours: int = 12
    timeout: float = 30.0


@dataclass
class PlexSyncSettings:
    enabled: bool = False
    url: str | None = None
    token: str | None = None
    library_id: str | None = None
    library_name: str | None = None
    timeout: float = 15.0
    force: bool = False
    dry_run: bool = False
    sports: list[str] = field(default_factory=list)
    scan_wait: float = 5.0  # Seconds to wait after triggering library scan
    lock_poster_fields: bool = False  # Whether to lock poster fields to prevent updates


@dataclass
class PatternConfig:
    regex: str
    description: str | None = None
    season_selector: SeasonSelector = field(default_factory=SeasonSelector)
    episode_selector: EpisodeSelector = field(default_factory=EpisodeSelector)
    session_aliases: dict[str, list[str]] = field(default_factory=dict)
    metadata_filters: dict[str, Any] = field(default_factory=dict)
    filename_template: str | None = None
    season_dir_template: str | None = None
    destination_root_template: str | None = None
    priority: int = 100

    def compiled_regex(self) -> re.Pattern[str]:
        return re.compile(self.regex, re.IGNORECASE)


@dataclass
class MetadataConfig:
    url: str
    show_key: str | None = None
    ttl_hours: int = 12
    headers: dict[str, str] = field(default_factory=dict)
    season_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class DestinationTemplates:
    root_template: str = "{show_title}"
    season_dir_template: str = "{season_number:02d} {season_title}"
    episode_template: str = "{show_title} - S{season_number:02d}E{episode_number:02d} - {episode_title}.{extension}"


@dataclass
class QualityScoring:
    """Quality scoring configuration for upgrade decisions.

    Attributes:
        resolution: Mapping of resolution (e.g., "2160p") to score
        source: Mapping of source type (e.g., "webdl") to score
        release_group: Mapping of release group (e.g., "mwr") to score
        proper_bonus: Bonus points for PROPER releases
        repack_bonus: Bonus points for REPACK releases
        hdr_bonus: Bonus points for HDR content
    """

    resolution: dict[str, int] = field(
        default_factory=lambda: {
            "2160p": 400,
            "1080p": 300,
            "720p": 200,
            "576p": 150,
            "480p": 100,
        }
    )
    source: dict[str, int] = field(
        default_factory=lambda: {
            "bluray": 100,
            "webdl": 90,
            "webrip": 70,
            "hdtv": 50,
            "sdtv": 30,
            "dvdrip": 40,
        }
    )
    release_group: dict[str, int] = field(default_factory=dict)
    proper_bonus: int = 50
    repack_bonus: int = 50
    hdr_bonus: int = 25


@dataclass
class QualityProfile:
    """Quality profile for controlling file upgrade decisions.

    When enabled, files are scored based on quality attributes (resolution,
    source, release group, etc.) and upgrades are allowed when a higher-scoring
    file is found.

    Attributes:
        enabled: Whether quality-based upgrades are enabled
        scoring: Quality scoring configuration
        cutoff: Score threshold - stop upgrading when this score is reached
            (unless PROPER/REPACK which always upgrade)
        min_score: Minimum score required - reject files below this threshold
    """

    enabled: bool = False
    scoring: QualityScoring = field(default_factory=QualityScoring)
    cutoff: int | None = None
    min_score: int | None = None


@dataclass
class NotificationSettings:
    batch_daily: bool = False
    flush_time: dt.time = field(default_factory=lambda: dt.time(hour=0, minute=0))
    targets: list[dict[str, Any]] = field(default_factory=list)
    throttle: dict[str, int] = field(default_factory=dict)
    mentions: dict[str, str] = field(default_factory=dict)
    summary_mode: bool = False  # Send one summary notification per scan instead of per-file


@dataclass
class WatcherSettings:
    enabled: bool = False
    paths: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    debounce_seconds: float = 5.0
    reconcile_interval: int = 900


@dataclass
class KometaTriggerSettings:
    enabled: bool = False
    mode: str = "kubernetes"  # kubernetes | docker
    namespace: str = "media"
    cronjob_name: str = "kometa-sport"
    job_name_prefix: str = "kometa-sport-triggered-by-playbook"
    docker_binary: str = "docker"
    docker_image: str = "kometateam/kometa"
    docker_config_path: str | None = None
    docker_config_container_path: str = "/config"
    docker_volume_mode: str = "rw"
    docker_libraries: str | None = None
    docker_extra_args: list[str] = field(default_factory=list)
    docker_env: dict[str, str] = field(default_factory=dict)
    docker_remove_container: bool = True
    docker_interactive: bool = False
    docker_container_name: str | None = None
    docker_exec_python: str = "python3"
    docker_exec_script: str = "/app/kometa/kometa.py"
    docker_exec_command: list[str] | None = None


@dataclass
class SportConfig:
    id: str
    name: str
    show_slug: str  # Required: TheTVSportsDB show slug (e.g., "formula-1-2026")
    enabled: bool = True
    metadata: MetadataConfig | None = None  # Deprecated: kept for backwards compatibility during transition
    patterns: list[PatternConfig] = field(default_factory=list)
    team_alias_map: str | None = None
    destination: DestinationTemplates = field(default_factory=DestinationTemplates)
    source_globs: list[str] = field(default_factory=list)
    source_extensions: list[str] = field(default_factory=lambda: [".mkv", ".mp4", ".ts", ".m4v", ".avi"])
    link_mode: str = "hardlink"
    allow_unmatched: bool = False
    season_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)  # Moved from MetadataConfig
    quality_profile: QualityProfile | None = None  # Per-sport quality profile override


@dataclass
class Settings:
    source_dir: Path
    destination_dir: Path
    cache_dir: Path
    dry_run: bool = False
    skip_existing: bool = True
    default_destination: DestinationTemplates = field(default_factory=DestinationTemplates)
    link_mode: str = "hardlink"
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    file_watcher: WatcherSettings = field(default_factory=WatcherSettings)
    kometa_trigger: KometaTriggerSettings = field(default_factory=KometaTriggerSettings)
    plex_sync: PlexSyncSettings = field(default_factory=PlexSyncSettings)
    tvsportsdb: TVSportsDBConfig = field(default_factory=TVSportsDBConfig)
    quality_profile: QualityProfile = field(default_factory=QualityProfile)  # Global quality profile


@dataclass
class AppConfig:
    settings: Settings
    sports: list[SportConfig]


def _build_season_selector(data: dict[str, Any]) -> SeasonSelector:
    selector = SeasonSelector(
        mode=data.get("mode", "round"),
        group=data.get("group"),
        offset=int(data.get("offset", 0)),
        mapping={str(k): int(v) for k, v in data.get("mapping", {}).items()},
        aliases={str(k): str(v) for k, v in data.get("aliases", {}).items()},
        value_template=str(data["value_template"]).strip() if data.get("value_template") else None,
    )
    return selector


def _build_episode_selector(data: dict[str, Any]) -> EpisodeSelector:
    return EpisodeSelector(
        group=data.get("group", "session"),
        allow_fallback_to_title=bool(data.get("allow_fallback_to_title", True)),
        default_value=(str(data["default_value"]).strip() if data.get("default_value") else None),
    )


def _build_pattern_config(data: dict[str, Any]) -> PatternConfig:
    raw_regex = str(data["regex"])
    pattern = PatternConfig(
        regex=expand_regex_with_tokens(raw_regex),
        description=data.get("description"),
        season_selector=_build_season_selector(data.get("season_selector", {})),
        episode_selector=_build_episode_selector(data.get("episode_selector", {})),
        session_aliases={key: list(value) for key, value in data.get("session_aliases", {}).items()},
        metadata_filters=data.get("metadata_filters", {}),
        filename_template=data.get("filename_template"),
        season_dir_template=data.get("season_dir_template"),
        destination_root_template=data.get("destination_root_template"),
        priority=int(data.get("priority", 100)),
    )
    return pattern


def _build_metadata_config(data: dict[str, Any]) -> MetadataConfig:
    return MetadataConfig(
        url=data["url"],
        show_key=data.get("show_key"),
        ttl_hours=int(data.get("ttl_hours", 12)),
        headers={str(k): str(v) for k, v in data.get("headers", {}).items()},
        season_overrides=data.get("season_overrides", {}),
    )


def _build_destination_templates(data: dict[str, Any] | None, defaults: DestinationTemplates) -> DestinationTemplates:
    if not data:
        return defaults

    return DestinationTemplates(
        root_template=data.get("root_template", defaults.root_template),
        season_dir_template=data.get("season_dir_template", defaults.season_dir_template),
        episode_template=data.get("episode_template", defaults.episode_template),
    )


def _build_sport_config(
    data: dict[str, Any],
    defaults: DestinationTemplates,
    global_link_mode: str,
    pattern_sets: dict[str, list[dict[str, Any]]],
) -> SportConfig:
    # Handle show_slug - required for API-based metadata
    show_slug = data.get("show_slug")
    if not show_slug:
        raise ValueError(f"Sport '{data.get('id')}' is missing required 'show_slug' field")

    # Build legacy metadata config if present (for backwards compatibility during transition)
    metadata: MetadataConfig | None = None
    if "metadata" in data:
        metadata = _build_metadata_config(data["metadata"])

    destination = _build_destination_templates(data.get("destination"), defaults)
    pattern_definitions: list[dict[str, Any]] = []

    pattern_set_refs = data.get("pattern_sets", []) or []
    if not isinstance(pattern_set_refs, list):
        raise ValueError(f"Sport '{data.get('id')}' must declare 'pattern_sets' as a list when provided")

    for set_name in pattern_set_refs:
        if not isinstance(set_name, str):
            raise ValueError(f"Sport '{data.get('id')}' pattern set names must be strings, got '{set_name}'")
        if set_name not in pattern_sets:
            raise ValueError(f"Unknown pattern set '{set_name}' referenced by sport '{data.get('id')}'")
        pattern_definitions.extend(deepcopy(pattern_sets[set_name]))

    custom_patterns = data.get("file_patterns", []) or []
    pattern_definitions.extend(deepcopy(custom_patterns))

    patterns = sorted((_build_pattern_config(pattern) for pattern in pattern_definitions), key=lambda cfg: cfg.priority)

    # Season overrides can come from the sport config directly or from legacy metadata config
    season_overrides: dict[str, dict[str, Any]] = {}
    if metadata and metadata.season_overrides:
        season_overrides = metadata.season_overrides
    if "season_overrides" in data:
        season_overrides = data["season_overrides"]

    # Parse per-sport quality profile if present
    quality_profile: QualityProfile | None = None
    quality_profile_raw = data.get("quality_profile")
    if quality_profile_raw:
        sport_id = data.get("id", "unknown")
        quality_profile = _build_quality_profile(quality_profile_raw, f"sports[{sport_id}].quality_profile")

    return SportConfig(
        id=data["id"],
        name=data.get("name", data["id"]),
        show_slug=str(show_slug),
        enabled=bool(data.get("enabled", True)),
        metadata=metadata,
        patterns=patterns,
        team_alias_map=data.get("team_alias_map"),
        destination=destination,
        source_globs=list(data.get("source_globs", [])),
        source_extensions=list(data.get("source_extensions", [".mkv", ".mp4", ".ts", ".m4v", ".avi"])),
        link_mode=str(data.get("link_mode", global_link_mode)),
        allow_unmatched=bool(data.get("allow_unmatched", False)),
        season_overrides=season_overrides,
        quality_profile=quality_profile,
    )


def _deep_update(target: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, dict):
            existing = target.get(key)
            if isinstance(existing, dict):
                _deep_update(existing, value)
            else:
                target[key] = deepcopy(value)
        elif isinstance(value, list):
            target[key] = deepcopy(value)
        else:
            target[key] = value
    return target


def _expand_sport_variants(sport_data: dict[str, Any]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = sport_data.get("variants", [])
    if not variants:
        return [sport_data]

    base = {key: deepcopy(value) for key, value in sport_data.items() if key != "variants"}
    expanded: list[dict[str, Any]] = []

    base_id = base.get("id")
    if not base_id:
        raise ValueError("Sport entries with variants must define a base 'id'")

    for variant in variants:
        combined = deepcopy(base)
        _deep_update(combined, {key: value for key, value in variant.items() if key not in {"id_suffix", "year"}})

        variant_id = variant.get("id")
        variant_year = variant.get("year")
        variant_suffix = variant.get("id_suffix") or variant_year

        if variant_id:
            combined_id = variant_id
        elif variant_suffix:
            combined_id = f"{base_id}_{variant_suffix}"
        else:
            raise ValueError(f"Variant for sport '{base_id}' must define 'id', 'id_suffix', or 'year'")

        combined["id"] = combined_id

        if "name" not in combined:
            base_name = base.get("name", base_id)
            if "name" in variant:
                combined["name"] = variant["name"]
            elif variant_year is not None:
                combined["name"] = f"{base_name} {variant_year}"
            elif variant_suffix:
                combined["name"] = f"{base_name} {variant_suffix}"
            else:
                combined["name"] = base_name

        combined.pop("year", None)
        combined.pop("id_suffix", None)
        combined.pop("variants", None)

        expanded.append(combined)

    return expanded


def _parse_time_of_day(value: Any, *, field_name: str) -> dt.time:
    if value is None:
        return dt.time(hour=0, minute=0)
    if isinstance(value, dt.time):
        return value
    if not isinstance(value, str):
        raise ValueError(f"'{field_name}' must be provided as HH:MM or HH:MM:SS")

    parts = value.strip().split(":")
    if len(parts) not in {2, 3}:
        raise ValueError(f"'{field_name}' must be formatted as HH:MM or HH:MM:SS")

    try:
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) == 3 else 0
    except ValueError as exc:  # noqa: PERF203
        raise ValueError(f"'{field_name}' components must be integers") from exc

    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        raise ValueError(f"'{field_name}' contains out-of-range values")

    return dt.time(hour=hour, minute=minute, second=second)


def _ensure_string_list(value: Any, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise ValueError(f"'{field_name}' must be provided as a list of strings")
    result: list[str] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, str):
            raise ValueError(f"'{field_name}[{index}]' must be a string")
        cleaned = entry.strip()
        if cleaned:
            result.append(cleaned)
    return result


def _build_watcher_settings(data: dict[str, Any]) -> WatcherSettings:
    if not data:
        return WatcherSettings()
    if not isinstance(data, dict):
        raise ValueError("'file_watcher' must be provided as a mapping when specified")

    try:
        debounce = float(data.get("debounce_seconds", 5.0))
    except (TypeError, ValueError) as exc:  # noqa: PERF203
        raise ValueError("'file_watcher.debounce_seconds' must be a number") from exc
    if debounce < 0:
        raise ValueError("'file_watcher.debounce_seconds' must be greater than or equal to 0")

    try:
        reconcile = int(data.get("reconcile_interval", 900))
    except (TypeError, ValueError) as exc:  # noqa: PERF203
        raise ValueError("'file_watcher.reconcile_interval' must be an integer") from exc
    if reconcile < 0:
        raise ValueError("'file_watcher.reconcile_interval' must be greater than or equal to 0")

    return WatcherSettings(
        enabled=bool(data.get("enabled", False)),
        paths=_ensure_string_list(data.get("paths"), field_name="file_watcher.paths"),
        include=_ensure_string_list(data.get("include"), field_name="file_watcher.include"),
        ignore=_ensure_string_list(data.get("ignore"), field_name="file_watcher.ignore"),
        debounce_seconds=debounce,
        reconcile_interval=reconcile,
    )


def _build_plex_sync_settings(data: dict[str, Any]) -> PlexSyncSettings:
    if not data:
        return PlexSyncSettings()
    if not isinstance(data, dict):
        raise ValueError("'plex_metadata_sync' must be provided as a mapping when specified")

    timeout_raw = data.get("timeout", 15.0)
    try:
        timeout = float(timeout_raw)
    except (TypeError, ValueError) as exc:  # noqa: PERF203
        raise ValueError("'plex_metadata_sync.timeout' must be a number") from exc

    sports = _ensure_string_list(data.get("sports"), field_name="plex_metadata_sync.sports")

    def _clean_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    url = _clean_str(data.get("url"))
    enabled = bool(data.get("enabled", False))

    # Validate URL format if provided and enabled
    if url and enabled and not validate_url(url):
        raise ValueError(f"'plex_metadata_sync.url' must be a valid http/https URL, got: {url}")

    scan_wait_raw = data.get("scan_wait", 5.0)
    try:
        scan_wait = float(scan_wait_raw)
    except (TypeError, ValueError):
        scan_wait = 5.0

    return PlexSyncSettings(
        enabled=enabled,
        url=url,
        token=_clean_str(data.get("token")),
        library_id=_clean_str(data.get("library_id")),
        library_name=_clean_str(data.get("library_name")),
        timeout=timeout,
        force=bool(data.get("force", False)),
        dry_run=bool(data.get("dry_run", False)),
        sports=sports,
        scan_wait=scan_wait,
        lock_poster_fields=bool(data.get("lock_poster_fields", False)),
    )


def _build_kometa_trigger_settings(data: dict[str, Any]) -> KometaTriggerSettings:
    if not data:
        return KometaTriggerSettings()
    if not isinstance(data, dict):
        raise ValueError("'kometa_trigger' must be provided as a mapping when specified")

    namespace_raw = str(data.get("namespace", "media")).strip()
    cronjob_raw = str(data.get("cronjob_name", "kometa-sport")).strip()
    mode_raw = str(data.get("mode", "kubernetes")).strip().lower()

    namespace = namespace_raw or "media"
    cronjob_name = cronjob_raw or "kometa-sport"
    default_prefix = f"{cronjob_name}-triggered-by-playbook"

    job_name_prefix = str(data.get("job_name_prefix", default_prefix)).strip() or default_prefix

    docker_raw = data.get("docker", {}) or {}
    if not isinstance(docker_raw, dict):
        raise ValueError("'kometa_trigger.docker' must be provided as a mapping when specified")

    docker_config_path = docker_raw.get("config_path")
    if docker_config_path is not None:
        docker_config_path = str(docker_config_path).strip() or None

    docker_libraries = docker_raw.get("libraries")
    if docker_libraries is not None:
        docker_libraries = str(docker_libraries).strip() or None

    extra_args_raw = docker_raw.get("extra_args", []) or []
    if isinstance(extra_args_raw, str):
        extra_args_raw = [extra_args_raw]
    elif not isinstance(extra_args_raw, list):
        raise ValueError("'kometa_trigger.docker.extra_args' must be provided as a list when specified")
    docker_extra_args = _ensure_string_list(extra_args_raw, field_name="kometa_trigger.docker.extra_args")

    docker_env_raw = docker_raw.get("env", {}) or {}
    if not isinstance(docker_env_raw, dict):
        raise ValueError("'kometa_trigger.docker.env' must be provided as a mapping when specified")
    docker_env: dict[str, str] = {}
    for key, value in docker_env_raw.items():
        docker_env[str(key)] = "" if value is None else str(value)

    volume_mode = str(docker_raw.get("volume_mode", "rw")).strip() or "rw"
    container_path_raw = str(docker_raw.get("container_path", "/config")).strip() or "/config"
    container_name = docker_raw.get("container_name")
    if container_name is not None:
        container_name = str(container_name).strip() or None
    exec_python = str(docker_raw.get("exec_python", "python3")).strip() or "python3"
    exec_script = str(docker_raw.get("exec_script", "/app/kometa/kometa.py")).strip() or "/app/kometa/kometa.py"
    exec_command_raw = docker_raw.get("exec_command")
    docker_exec_command: list[str] | None
    if exec_command_raw is None:
        docker_exec_command = None
    else:
        if isinstance(exec_command_raw, str):
            docker_exec_command = shlex.split(exec_command_raw.strip())
        else:
            docker_exec_command = _ensure_string_list(exec_command_raw, field_name="kometa_trigger.docker.exec_command")
        if not docker_exec_command:
            docker_exec_command = None
    if docker_exec_command and ("exec_python" in docker_raw or "exec_script" in docker_raw):
        raise ValueError(
            "Please specify either 'kometa_trigger.docker.exec_command' or the exec_python/exec_script fields, not both."
        )

    return KometaTriggerSettings(
        enabled=bool(data.get("enabled", False)),
        mode=mode_raw or "kubernetes",
        namespace=namespace,
        cronjob_name=cronjob_name,
        job_name_prefix=job_name_prefix,
        docker_binary=str(docker_raw.get("binary", "docker")).strip() or "docker",
        docker_image=str(docker_raw.get("image", "kometateam/kometa")).strip() or "kometateam/kometa",
        docker_config_path=docker_config_path,
        docker_config_container_path=container_path_raw,
        docker_volume_mode=volume_mode,
        docker_libraries=docker_libraries,
        docker_extra_args=docker_extra_args,
        docker_env=docker_env,
        docker_remove_container=bool(docker_raw.get("remove_container", True)),
        docker_interactive=bool(docker_raw.get("interactive", False)),
        docker_container_name=container_name,
        docker_exec_python=exec_python,
        docker_exec_script=exec_script,
        docker_exec_command=docker_exec_command,
    )


def _build_tvsportsdb_config(data: dict[str, Any]) -> TVSportsDBConfig:
    """Build TVSportsDB API configuration."""
    if not data:
        return TVSportsDBConfig()
    if not isinstance(data, dict):
        raise ValueError("'tvsportsdb' must be provided as a mapping when specified")

    base_url = str(data.get("base_url", TVSportsDBConfig.base_url)).strip()
    if not base_url:
        base_url = TVSportsDBConfig.base_url

    try:
        ttl_hours = int(data.get("ttl_hours", 12))
    except (TypeError, ValueError) as exc:
        raise ValueError("'tvsportsdb.ttl_hours' must be an integer") from exc

    try:
        timeout = float(data.get("timeout", 30.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("'tvsportsdb.timeout' must be a number") from exc

    return TVSportsDBConfig(
        base_url=base_url,
        ttl_hours=ttl_hours,
        timeout=timeout,
    )


def _build_quality_scoring(data: dict[str, Any], field_prefix: str = "quality_profile.scoring") -> QualityScoring:
    """Build quality scoring configuration from YAML data."""
    if not data:
        return QualityScoring()
    if not isinstance(data, dict):
        raise ValueError(f"'{field_prefix}' must be provided as a mapping when specified")

    # Parse resolution scores
    resolution_raw = data.get("resolution", {}) or {}
    if not isinstance(resolution_raw, dict):
        raise ValueError(f"'{field_prefix}.resolution' must be a mapping")
    resolution: dict[str, int] = {}
    for key, value in resolution_raw.items():
        try:
            resolution[str(key).lower()] = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"'{field_prefix}.resolution.{key}' must be an integer") from exc

    # Parse source scores
    source_raw = data.get("source", {}) or {}
    if not isinstance(source_raw, dict):
        raise ValueError(f"'{field_prefix}.source' must be a mapping")
    source: dict[str, int] = {}
    for key, value in source_raw.items():
        try:
            source[str(key).lower()] = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"'{field_prefix}.source.{key}' must be an integer") from exc

    # Parse release group scores
    release_group_raw = data.get("release_group", {}) or {}
    if not isinstance(release_group_raw, dict):
        raise ValueError(f"'{field_prefix}.release_group' must be a mapping")
    release_group: dict[str, int] = {}
    for key, value in release_group_raw.items():
        try:
            release_group[str(key).lower()] = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"'{field_prefix}.release_group.{key}' must be an integer") from exc

    # Parse bonus values
    try:
        proper_bonus = int(data.get("proper_bonus", 50))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{field_prefix}.proper_bonus' must be an integer") from exc

    try:
        repack_bonus = int(data.get("repack_bonus", 50))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{field_prefix}.repack_bonus' must be an integer") from exc

    try:
        hdr_bonus = int(data.get("hdr_bonus", 25))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{field_prefix}.hdr_bonus' must be an integer") from exc

    # Use defaults for any missing mappings
    default_scoring = QualityScoring()
    if not resolution:
        resolution = default_scoring.resolution
    if not source:
        source = default_scoring.source

    return QualityScoring(
        resolution=resolution,
        source=source,
        release_group=release_group,
        proper_bonus=proper_bonus,
        repack_bonus=repack_bonus,
        hdr_bonus=hdr_bonus,
    )


def _build_quality_profile(data: dict[str, Any], field_prefix: str = "quality_profile") -> QualityProfile:
    """Build quality profile configuration from YAML data."""
    if not data:
        return QualityProfile()
    if not isinstance(data, dict):
        raise ValueError(f"'{field_prefix}' must be provided as a mapping when specified")

    enabled = bool(data.get("enabled", False))

    scoring = _build_quality_scoring(data.get("scoring", {}), f"{field_prefix}.scoring")

    cutoff: int | None = None
    cutoff_raw = data.get("cutoff")
    if cutoff_raw is not None:
        try:
            cutoff = int(cutoff_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"'{field_prefix}.cutoff' must be an integer") from exc

    min_score: int | None = None
    min_score_raw = data.get("min_score")
    if min_score_raw is not None:
        try:
            min_score = int(min_score_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"'{field_prefix}.min_score' must be an integer") from exc

    return QualityProfile(
        enabled=enabled,
        scoring=scoring,
        cutoff=cutoff,
        min_score=min_score,
    )


def _merge_quality_profile(
    base: QualityProfile,
    override: QualityProfile | None,
) -> QualityProfile:
    """Merge a sport-specific quality profile with the global profile.

    The sport-specific profile's scoring values override the global ones,
    while non-specified values inherit from the global profile.
    """
    if override is None:
        return base

    # Merge scoring dictionaries
    merged_resolution = {**base.scoring.resolution, **override.scoring.resolution}
    merged_source = {**base.scoring.source, **override.scoring.source}
    merged_release_group = {**base.scoring.release_group, **override.scoring.release_group}

    merged_scoring = QualityScoring(
        resolution=merged_resolution,
        source=merged_source,
        release_group=merged_release_group,
        proper_bonus=override.scoring.proper_bonus
        if override.scoring.proper_bonus != 50
        else base.scoring.proper_bonus,
        repack_bonus=override.scoring.repack_bonus
        if override.scoring.repack_bonus != 50
        else base.scoring.repack_bonus,
        hdr_bonus=override.scoring.hdr_bonus if override.scoring.hdr_bonus != 25 else base.scoring.hdr_bonus,
    )

    return QualityProfile(
        enabled=override.enabled if override.enabled else base.enabled,
        scoring=merged_scoring,
        cutoff=override.cutoff if override.cutoff is not None else base.cutoff,
        min_score=override.min_score if override.min_score is not None else base.min_score,
    )


def _build_settings(data: dict[str, Any]) -> Settings:
    destination_defaults = DestinationTemplates(
        root_template=data.get("destination", {}).get("root_template", "{show_title}"),
        season_dir_template=data.get("destination", {}).get(
            "season_dir_template", "{season_number:02d} {season_title}"
        ),
        episode_template=data.get("destination", {}).get(
            "episode_template",
            "{show_title} - S{season_number:02d}E{episode_number:02d} - {episode_title}.{extension}",
        ),
    )

    if "discord_webhook_url" in data:
        raise ValueError(
            "'settings.discord_webhook_url' has been removed. "
            "Please configure Discord webhooks under 'settings.notifications.targets' instead."
        )

    notifications_raw = data.get("notifications", {}) or {}
    if not isinstance(notifications_raw, dict):
        raise ValueError("'notifications' must be provided as a mapping when specified")

    try:
        flush_time = _parse_time_of_day(
            notifications_raw.get("flush_time", "00:00"),
            field_name="notifications.flush_time",
        )
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    targets_raw = notifications_raw.get("targets", []) or []
    if not isinstance(targets_raw, list):
        raise ValueError("'notifications.targets' must be provided as a list when specified")
    targets: list[dict[str, Any]] = []
    for entry in targets_raw:
        if not isinstance(entry, dict):
            raise ValueError("Each entry in 'notifications.targets' must be a mapping")
        target_type = entry.get("type")
        if not isinstance(target_type, str):
            raise ValueError("Notification target entries must include a string 'type'")
        normalized_entry: dict[str, Any] = {str(k): v for k, v in entry.items()}
        normalized_entry["type"] = target_type.strip().lower()
        targets.append(normalized_entry)

    throttle_raw = notifications_raw.get("throttle", {}) or {}
    if not isinstance(throttle_raw, dict):
        raise ValueError("'notifications.throttle' must be provided as a mapping when specified")
    throttle: dict[str, int] = {}
    for key, value in throttle_raw.items():
        try:
            throttle[str(key)] = int(value)
        except (TypeError, ValueError) as exc:  # noqa: PERF203
            raise ValueError(f"'notifications.throttle[{key}]' must be an integer") from exc

    mentions_raw = notifications_raw.get("mentions", {}) or {}
    if not isinstance(mentions_raw, dict):
        raise ValueError("'notifications.mentions' must be provided as a mapping when specified")
    mentions: dict[str, str] = {}
    for key, value in mentions_raw.items():
        if value is None:
            continue
        mention = str(value).strip()
        if not mention:
            continue
        key_str = str(key).strip()
        if not key_str:
            continue
        mentions[key_str] = mention

    notifications = NotificationSettings(
        batch_daily=bool(notifications_raw.get("batch_daily", False)),
        flush_time=flush_time,
        targets=targets,
        throttle=throttle,
        mentions=mentions,
    )

    source_dir = Path(data.get("source_dir", "/data/source")).expanduser()
    destination_dir = Path(data.get("destination_dir", "/data/destination")).expanduser()
    cache_dir = Path(data.get("cache_dir", "/data/cache")).expanduser()
    watcher_settings = _build_watcher_settings(data.get("file_watcher", {}) or {})
    kometa_trigger = _build_kometa_trigger_settings(data.get("kometa_trigger", {}) or {})
    plex_sync = _build_plex_sync_settings(data.get("plex_metadata_sync", {}) or {})
    tvsportsdb = _build_tvsportsdb_config(data.get("tvsportsdb", {}) or {})
    quality_profile = _build_quality_profile(data.get("quality_profile", {}) or {})

    return Settings(
        source_dir=source_dir,
        destination_dir=destination_dir,
        cache_dir=cache_dir,
        dry_run=bool(data.get("dry_run", False)),
        skip_existing=bool(data.get("skip_existing", True)),
        default_destination=destination_defaults,
        link_mode=data.get("link_mode", "hardlink"),
        notifications=notifications,
        file_watcher=watcher_settings,
        kometa_trigger=kometa_trigger,
        plex_sync=plex_sync,
        tvsportsdb=tvsportsdb,
        quality_profile=quality_profile,
    )


def load_config(path: Path) -> AppConfig:
    data = load_yaml_file(path)

    builtin_pattern_sets = {name: deepcopy(patterns) for name, patterns in load_builtin_pattern_sets().items()}
    user_pattern_sets = data.get("pattern_sets", {}) or {}
    if not isinstance(user_pattern_sets, dict):
        raise ValueError("'pattern_sets' must be defined as a mapping of name -> list of patterns")

    for name, patterns in user_pattern_sets.items():
        if patterns is None:
            builtin_pattern_sets[name] = []
            continue
        if not isinstance(patterns, list):
            raise ValueError(f"Pattern set '{name}' must be a list of pattern definitions")
        builtin_pattern_sets[name] = deepcopy(patterns)

    settings = _build_settings(data.get("settings", {}))
    defaults = settings.default_destination
    sports_raw: Iterable[dict[str, Any]] = data.get("sports", [])

    expanded_sports: list[dict[str, Any]] = []
    for sport_data in sports_raw:
        for variant_data in _expand_sport_variants(sport_data):
            expanded_sports.append(variant_data)

    sports = []
    for sport_data in expanded_sports:
        sports.append(_build_sport_config(sport_data, defaults, settings.link_mode, builtin_pattern_sets))

    return AppConfig(settings=settings, sports=sports)
