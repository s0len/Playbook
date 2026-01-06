from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from rich.progress import Progress

from .cache import CachedFileRecord, MetadataHttpCache, ProcessedFileCache
from .config import AppConfig, SportConfig
from .kometa_trigger import build_kometa_trigger
from .logging_utils import LogBlockBuilder, render_fields_block
from .matcher import PatternRuntime, match_file_to_episode
from .metadata import (
    MetadataChangeResult,
    MetadataFetchStatistics,
    MetadataFingerprintStore,
)
from .metadata_loader import MetadataLoadResult, SportRuntime, load_sports
from .models import ProcessingStats, SportFileMatch
from .notifications import NotificationEvent, NotificationService
from .plex_metadata_sync import PlexMetadataSync, PlexSyncStats, create_plex_sync_from_config
from .run_summary import (
    extract_error_context,
    filtered_ignored_details,
    has_activity,
    has_detailed_activity,
    log_detailed_summary,
    log_run_recap,
    summarize_counts,
    summarize_messages,
    summarize_plex_errors,
)
from .file_discovery import gather_source_files, matches_globs, should_suppress_sample_ignored, skip_reason_for_source_file
from .match_handler import (
    alias_candidates,
    episode_cache_key,
    season_cache_key,
    specificity_score,
)
from .destination_builder import build_destination, build_match_context, format_relative_destination
from .trace_writer import TraceOptions, persist_trace
from .post_run_triggers import run_plex_sync_if_needed, trigger_kometa_if_needed
from .utils import ensure_directory, link_file, normalize_token, sha1_of_file, sha1_of_text

LOGGER = logging.getLogger(__name__)


class Processor:
    def __init__(
        self,
        config: AppConfig,
        *,
        enable_notifications: bool = True,
        trace_options: Optional[TraceOptions] = None,
    ) -> None:
        self.config = config
        if not self.config.settings.dry_run:
            ensure_directory(self.config.settings.destination_dir)
            ensure_directory(self.config.settings.cache_dir)
        self.processed_cache = ProcessedFileCache(self.config.settings.cache_dir)
        self.metadata_fingerprints = MetadataFingerprintStore(self.config.settings.cache_dir)
        self.metadata_http_cache = MetadataHttpCache(self.config.settings.cache_dir)
        self.trace_options = trace_options or TraceOptions()
        settings = self.config.settings
        self.notification_service = NotificationService(
            settings.notifications,
            cache_dir=settings.cache_dir,
            destination_dir=settings.destination_dir,
            enabled=enable_notifications,
        )
        self._kometa_trigger = build_kometa_trigger(settings.kometa_trigger)
        self._kometa_trigger_fired = False
        self._kometa_trigger_needed = False
        self._plex_sync: Optional[PlexMetadataSync] = create_plex_sync_from_config(config)
        self._plex_sync_stats: Optional[PlexSyncStats] = None
        self._plex_sync_ran = False
        self._previous_summary: Optional[Tuple[int, int, int]] = None
        self._metadata_changed_sports: List[Tuple[str, str]] = []
        self._metadata_change_map: Dict[str, MetadataChangeResult] = {}
        self._stale_destinations: Dict[str, Path] = {}
        self._stale_records: Dict[str, CachedFileRecord] = {}
        self._metadata_fetch_stats = MetadataFetchStatistics()
        self._touched_destinations: Set[str] = set()
        self._sports_with_processed_files: Set[str] = set()

    @staticmethod
    def _format_log(event: str, fields: Optional[Mapping[str, object]] = None) -> str:
        return render_fields_block(event, fields or {}, pad_top=True)

    @staticmethod
    def _format_inline_log(event: str, fields: Optional[Mapping[str, object]] = None) -> str:
        return render_fields_block(event, fields or {}, pad_top=False)

    def _load_sports(self) -> List[SportRuntime]:
        """Load sports metadata in parallel and track changes.

        Delegates to metadata_loader.load_sports() and unpacks results into
        instance variables for tracking metadata changes and fetch statistics.

        Returns:
            List of successfully loaded SportRuntime objects
        """
        result = load_sports(
            sports=self.config.sports,
            settings=self.config.settings,
            metadata_http_cache=self.metadata_http_cache,
            metadata_fingerprints=self.metadata_fingerprints,
        )

        # Unpack results into instance variables
        self._metadata_changed_sports = result.changed_sports
        self._metadata_change_map = result.change_map
        self._metadata_fetch_stats = result.fetch_stats

        return result.runtimes

    def clear_processed_cache(self) -> None:
        if self.config.settings.dry_run:
            LOGGER.debug(
                self._format_log(
                    "Dry-Run: Skipping Processed Cache Clear",
                    {"Cache": self.processed_cache.cache_path.parent},
                )
            )
            return

        self.processed_cache.clear()
        self.processed_cache.save()
        LOGGER.debug(self._format_log("Processed File Cache Cleared"))

    def process_all(self) -> ProcessingStats:
        self._kometa_trigger_fired = False
        self._kometa_trigger_needed = False
        runtimes = self._load_sports()
        self._stale_destinations = {}
        self._stale_records = {}
        if self._metadata_changed_sports:
            labels = ", ".join(
                f"{sport_id} ({sport_name})" if sport_name and sport_name != sport_id else sport_id
                for sport_id, sport_name in self._metadata_changed_sports
            )
            LOGGER.info(
                self._format_log(
                    "Metadata Updated",
                    {
                        "Sports": labels or "(unknown)",
                    },
                )
            )
            removed_records = self.processed_cache.remove_by_metadata_changes(self._metadata_change_map)
            self._stale_destinations = {
                source: Path(record.destination)
                for source, record in removed_records.items()
                if record.destination
            }
            self._stale_records = removed_records
        stats = ProcessingStats()
        self._touched_destinations = set()
        self._sports_with_processed_files = set()
        run_started = time.perf_counter()

        try:
            all_source_files = list(self._gather_source_files(stats))
            filtered_source_files: List[Path] = []
            skipped_by_cache = 0
            for source_path in all_source_files:
                if self.processed_cache.is_processed(source_path):
                    skipped_by_cache += 1
                    LOGGER.debug(
                        self._format_log(
                            "Skipping Previously Processed File",
                            {"Path": source_path},
                        )
                    )
                    continue
                filtered_source_files.append(source_path)

            file_count = len(filtered_source_files)
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug(
                    self._format_log(
                        "Discovered Candidate Files",
                        {
                            "Total": len(all_source_files),
                            "Skipped Via Cache": skipped_by_cache,
                        },
                    )
                )

            with Progress(disable=not LOGGER.isEnabledFor(logging.DEBUG)) as progress:
                task_id = progress.add_task("Processing", total=file_count)
                for source_path in filtered_source_files:
                    is_sample_file = should_suppress_sample_ignored(source_path)
                    handled, diagnostics = self._process_single_file(
                        source_path,
                        runtimes,
                        stats,
                        is_sample_file=is_sample_file,
                    )
                    if not handled:
                        if is_sample_file:
                            stats.register_ignored(suppressed_reason="sample")
                        else:
                            detail = self._format_ignored_detail(source_path, diagnostics)
                            sport_id = next((sport for _, _, sport in diagnostics if sport), None)
                            stats.register_ignored(detail, sport_id=sport_id)
                    progress.advance(task_id, 1)

            summary_counts = (stats.processed, stats.skipped, stats.ignored)
            summary_changed = summary_counts != self._previous_summary
            should_log_summary = (LOGGER.isEnabledFor(logging.DEBUG) or has_activity(stats)) and summary_changed
            if should_log_summary:
                LOGGER.info(
                    self._format_inline_log(
                        "Summary",
                        {
                            "Processed": stats.processed,
                            "Skipped": stats.skipped,
                            "Ignored": stats.ignored,
                        },
                    )
                )
            self._previous_summary = summary_counts
            if stats.errors:
                for error in stats.errors:
                    LOGGER.error(
                        self._format_log(
                            "Processing Error",
                            {"Detail": error},
                        )
                    )

            has_details = has_detailed_activity(stats)
            has_issues = bool(stats.errors or stats.warnings)
            if LOGGER.isEnabledFor(logging.DEBUG):
                if has_details or has_issues:
                    level = logging.INFO if has_issues else logging.DEBUG
                    self._log_detailed_summary(stats, level=level)
            elif has_issues:
                self._log_detailed_summary(stats)
            self._trigger_post_run_trigger_if_needed(stats)
            duration = time.perf_counter() - run_started
            self._log_run_recap(stats, duration)
            return stats
        finally:
            self.metadata_http_cache.save()
            if not self.config.settings.dry_run:
                self.processed_cache.save()
                self.metadata_fingerprints.save()

    def _gather_source_files(self, stats: Optional[ProcessingStats] = None) -> Iterable[Path]:
        """Discover and yield source files for processing.

        Delegates to file_discovery.gather_source_files().
        """
        return gather_source_files(self.config.settings.source_dir, stats)

    def _process_single_file(
        self,
        source_path: Path,
        runtimes: List[SportRuntime],
        stats: ProcessingStats,
        *,
        is_sample_file: bool = False,
    ) -> Tuple[bool, List[Tuple[str, str, Optional[str]]]]:
        suffix = source_path.suffix.lower()
        matching_runtimes = [runtime for runtime in runtimes if suffix in runtime.extensions]
        ignored_reasons: List[Tuple[str, str, Optional[str]]] = []

        if not matching_runtimes:
            message = f"No configured sport accepts extension '{suffix or '<no extension>'}'"
            ignored_reasons.append(("ignored", message, None))
            LOGGER.debug(
                self._format_log(
                    "Ignoring File",
                    {
                        "Source": source_path,
                        "Reason": message,
                    },
                )
            )
            return False, ignored_reasons

        for runtime in matching_runtimes:
            trace_context: Optional[Dict[str, Any]] = None
            if self.trace_options.enabled:
                trace_context = {
                    "filename": str(source_path),
                    "sport_id": runtime.sport.id,
                    "sport_name": runtime.sport.name,
                    "source_name": source_path.name,
                }
            if not matches_globs(source_path, runtime.sport):
                patterns = runtime.sport.source_globs or ["*"]
                message = f"Excluded by source_globs {patterns}"
                ignored_reasons.append(("ignored", message, runtime.sport.id))
                LOGGER.debug(
                    self._format_log(
                        "Ignoring File For Sport",
                        {
                            "Source": source_path.name,
                            "Sport": runtime.sport.id,
                            "Reason": message,
                        },
                    )
                )
                if trace_context is not None:
                    trace_context.update(
                        {
                            "status": "glob-excluded",
                            "reason": message,
                            "patterns": patterns,
                        }
                    )
                    self._persist_trace(trace_context)
                continue

            detection_messages: List[Tuple[str, str]] = []
            detection = match_file_to_episode(
                source_path.name,
                runtime.sport,
                runtime.show,
                runtime.patterns,
                diagnostics=detection_messages,
                trace=trace_context,
                suppress_warnings=is_sample_file,
            )
            if trace_context is not None:
                trace_context["diagnostics"] = [
                    {"severity": severity, "message": message} for severity, message in detection_messages
                ]
            if detection:
                season = detection["season"]
                episode = detection["episode"]
                pattern = detection["pattern"]
                groups = detection["groups"]

                context = self._build_context(runtime, source_path, season, episode, groups)
                try:
                    destination = self._build_destination(runtime, pattern, context)
                except ValueError as exc:
                    message = (
                        f"{runtime.sport.id}: Unsafe destination for {source_path.name} - {exc}"
                    )
                    LOGGER.error(
                        self._format_log(
                            "Unsafe Destination",
                            {
                                "Source": source_path,
                                "Sport": runtime.sport.id,
                                "Error": exc,
                            },
                        )
                    )
                    stats.register_skipped(message, is_error=True, sport_id=runtime.sport.id)
                    if trace_context is not None:
                        trace_context["status"] = "error"
                        trace_context["error"] = str(exc)
                        trace_context["destination_context"] = context
                        self._persist_trace(trace_context)
                    return False, [("error", message)]

                context["destination_path"] = str(destination)
                context["destination_dir"] = str(destination.parent)
                context["source_path"] = str(source_path)

                match = SportFileMatch(
                    source_path=source_path,
                    destination_path=destination,
                    show=runtime.show,
                    season=season,
                    episode=episode,
                    pattern=pattern,
                    context=context,
                    sport=runtime.sport,
                )

                event = self._handle_match(match, stats)
                if trace_context is not None:
                    trace_context.setdefault("status", event.action if event else "matched")
                    trace_context["destination"] = str(destination)
                    trace_context["context"] = context
                    trace_path = self._persist_trace(trace_context)
                else:
                    trace_path = None
                if event:
                    if trace_path is not None:
                        event.trace_path = str(trace_path)
                    self.notification_service.notify(event)
                return True, []

            if not detection_messages:
                detection_messages.append(("ignored", "No matching pattern resolved to an episode"))

            for severity, message in detection_messages:
                ignored_reasons.append((severity, message, runtime.sport.id))
                LOGGER.debug(
                    self._format_log(
                        "Ignoring Detection",
                        {
                            "Source": source_path.name,
                            "Sport": runtime.sport.id,
                            "Severity": severity,
                            "Reason": message,
                        },
                    )
                )
                if severity == "warning":
                    stats.register_warning(
                        f"{source_path.name}: {runtime.sport.id}: {message}",
                        sport_id=runtime.sport.id,
                    )
                elif severity == "error":
                    stats.register_error(
                        f"{source_path.name}: {runtime.sport.id}: {message}",
                        sport_id=runtime.sport.id,
                    )
            if trace_context is not None:
                trace_context.setdefault("status", "ignored")
                self._persist_trace(trace_context)

        return False, ignored_reasons

    def _persist_trace(self, trace: Optional[Dict[str, Any]]) -> Optional[Path]:
        return persist_trace(trace, self.trace_options, self.config.settings.cache_dir)

    def _format_ignored_detail(
        self,
        source_path: Path,
        diagnostics: List[Tuple[str, str, Optional[str]]],
    ) -> str:
        if not diagnostics:
            return f"{source_path.name}\n  - [IGNORED] No diagnostics recorded"

        lines = [source_path.name]
        seen: Set[str] = set()
        for severity, message, sport_id in diagnostics:
            key = f"{severity}:{sport_id}:{message}"
            if key in seen:
                continue
            seen.add(key)
            prefix = severity.upper()
            if sport_id:
                lines.append(f"  - [{prefix}] {sport_id}: {message}")
            else:
                lines.append(f"  - [{prefix}] {message}")
        return "\n".join(lines)

    def _log_detailed_summary(self, stats: ProcessingStats, *, level: int = logging.INFO) -> None:
        """Log detailed summary of processing results (delegates to run_summary module)."""
        log_detailed_summary(
            stats,
            plex_sync_stats=self._plex_sync_stats,
            level=level,
        )

    def _log_run_recap(self, stats: ProcessingStats, duration: float) -> None:
        """Log run recap with duration, stats, and follow-up actions (delegates to run_summary module)."""
        log_run_recap(
            stats,
            duration,
            touched_destinations=sorted(self._touched_destinations),
            plex_sync_enabled=self._plex_sync is not None,
            plex_sync_ran=self._plex_sync_ran,
            plex_sync_stats=self._plex_sync_stats,
            plex_sync_dry_run=self._plex_sync.dry_run if self._plex_sync else False,
            global_dry_run=self.config.settings.dry_run,
            kometa_enabled=self._kometa_trigger.enabled,
            kometa_fired=self._kometa_trigger_fired,
        )

    def _build_context(self, runtime: SportRuntime, source_path: Path, season, episode, groups) -> Dict[str, object]:
        return build_match_context(
            runtime=runtime,
            source_path=source_path,
            season=season,
            episode=episode,
            groups=groups,
            source_dir=self.config.settings.source_dir,
        )

    def _build_destination(self, runtime: SportRuntime, pattern, context: Dict[str, object]) -> Path:
        return build_destination(
            runtime=runtime,
            pattern=pattern,
            context=context,
            settings=self.config.settings,
        )

    def _handle_match(self, match: SportFileMatch, stats: ProcessingStats) -> Optional[NotificationEvent]:
        destination = match.destination_path
        settings = self.config.settings
        link_mode = (match.sport.link_mode or settings.link_mode).lower()
        source_key = str(match.source_path)
        old_destination = self._stale_destinations.get(source_key)
        cache_kwargs = {
            "sport_id": match.sport.id,
            "season_key": season_cache_key(match),
            "episode_key": episode_cache_key(match),
        }

        stale_record = self._stale_records.get(source_key)

        destination_display = self._format_relative_destination(destination)

        file_checksum: Optional[str] = None
        try:
            file_checksum = sha1_of_file(match.source_path)
        except ValueError as exc:  # pragma: no cover - depends on filesystem state
            LOGGER.debug(
                self._format_log(
                    "Failed To Hash Source",
                    {
                        "Source": match.source_path,
                        "Error": exc,
                    },
                )
            )

        stored_checksum = self.processed_cache.get_checksum(match.source_path)
        previous_checksum = stored_checksum or (stale_record.checksum if stale_record else None)
        previously_seen = bool(stored_checksum or stale_record)
        content_changed = (
            previously_seen
            and file_checksum is not None
            and previous_checksum is not None
            and file_checksum != previous_checksum
        )
        if not previously_seen:
            event_type = "new"
        elif content_changed:
            event_type = "changed"
        else:
            event_type = "refresh"

        destination_display = self._format_relative_destination(destination)
        event = NotificationEvent(
            sport_id=match.sport.id,
            sport_name=match.sport.name,
            show_title=match.show.title,
            season=str(match.context.get("season_title") or match.season.title or "Season"),
            session=str(match.context.get("session") or match.episode.title or "Session"),
            episode=str(match.context.get("episode_title") or match.episode.title or match.episode.title),
            summary=match.context.get("episode_summary") or match.episode.summary,
            destination=destination_display,
            source=match.source_path.name,
            action="link",
            link_mode=link_mode,
            match_details=dict(match.context),
            event_type=event_type,
        )

        replace_existing = False
        if destination.exists():
            if settings.skip_existing:
                if self._should_overwrite_existing(match):
                    replace_existing = True
                else:
                    LOGGER.debug(
                        self._format_log(
                            "Skipping Existing Destination",
                            {
                                "Destination": destination,
                                "Source": match.source_path,
                            },
                        )
                    )
                    self._cleanup_old_destination(
                        source_key,
                        old_destination,
                        destination,
                        dry_run=settings.dry_run,
                    )
                    skip_message = f"Destination exists: {destination} (source {match.source_path})"
                    stats.register_skipped(skip_message, is_error=False, sport_id=match.sport.id)
                    if not settings.dry_run:
                        self.processed_cache.mark_processed(
                            match.source_path,
                            destination,
                            checksum=file_checksum,
                            **cache_kwargs,
                        )
                    event.action = "skipped"
                    event.skip_reason = skip_message
                    event.event_type = "skipped"
                    return event

        if replace_existing:
            LOGGER.debug(
                self._format_log(
                    "Preparing To Replace Destination",
                    {"Destination": destination},
                )
            )
            if not settings.dry_run:
                try:
                    destination.unlink()
                except OSError as exc:
                    LOGGER.error(
                        self._format_log(
                            "Failed To Remove Destination",
                            {
                                "Destination": destination,
                                "Error": exc,
                            },
                        )
                    )
                    stats.register_skipped(
                        f"Failed to replace destination {destination}: {exc}",
                        is_error=True,
                        sport_id=match.sport.id,
                    )
                    event.action = "error"
                    event.skip_reason = f"failed-to-remove: {exc}"
                    event.event_type = "error"
                    return event

        LOGGER.debug(
            self._format_log(
                "Processed",
                {
                    "Action": "replace" if replace_existing else "link",
                    "Sport": match.sport.id,
                    "Season": match.context.get("season_title"),
                    "Session": match.context.get("session"),
                    "Dest": destination_display,
                    "Src": match.source_path.name,
                },
            )
        )

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                self._format_log(
                    "Processing Details",
                    {
                        "Source": match.source_path,
                        "Destination": destination,
                        "Link Mode": link_mode,
                        "Replace": replace_existing,
                    },
                )
            )

        if settings.dry_run:
            stats.register_processed()
            self._record_destination_touch(destination)
            self._sports_with_processed_files.add(match.sport.id)
            event.action = "dry-run"
            event.event_type = "dry-run"
            event.replaced = replace_existing
            return event

        result = link_file(match.source_path, destination, mode=link_mode)
        if result.created:
            stats.register_processed()
            self._record_destination_touch(destination)
            self._sports_with_processed_files.add(match.sport.id)
            self.processed_cache.mark_processed(
                match.source_path,
                destination,
                checksum=file_checksum,
                **cache_kwargs,
            )
            self._cleanup_old_destination(
                source_key,
                old_destination,
                destination,
                dry_run=settings.dry_run,
            )
            event.action = link_mode
            event.replaced = replace_existing
            if not settings.dry_run:
                self._kometa_trigger_needed = True
            return event
        else:
            failure_message = f"Failed to link {match.source_path} -> {destination}: {result.reason}"
            stats.register_skipped(failure_message, sport_id=match.sport.id)
            if result.reason == "destination-exists":
                self.processed_cache.mark_processed(
                    match.source_path,
                    destination,
                    checksum=file_checksum,
                    **cache_kwargs,
                )
                self._cleanup_old_destination(
                    source_key,
                    old_destination,
                    destination,
                    dry_run=settings.dry_run,
                )
                event.action = "skipped"
                event.skip_reason = failure_message
                event.event_type = "skipped"
                return event
            event.action = "error"
            event.skip_reason = failure_message
            event.event_type = "error"
            return event

    def _trigger_post_run_trigger_if_needed(self, stats: ProcessingStats) -> None:
        """Run post-run triggers: Plex sync and Kometa (delegates to post_run_triggers module)."""
        # Run Plex metadata sync if enabled and we processed files
        self._run_plex_sync_if_needed(stats)

        # Run Kometa trigger if enabled (legacy, may be removed)
        self._kometa_trigger_fired, self._kometa_trigger_needed = trigger_kometa_if_needed(
            self._kometa_trigger,
            self._kometa_trigger_fired,
            self._kometa_trigger_needed,
            global_dry_run=self.config.settings.dry_run,
            stats=stats,
        )

    def _run_plex_sync_if_needed(self, stats: ProcessingStats) -> None:
        """Run Plex metadata sync after file processing (delegates to post_run_triggers module)."""
        self._plex_sync_stats, self._plex_sync_ran = run_plex_sync_if_needed(
            self._plex_sync,
            self._plex_sync_ran,
            global_dry_run=self.config.settings.dry_run,
            sports_with_processed_files=self._sports_with_processed_files,
            metadata_changed_sports=self._metadata_changed_sports,
        )

    def _should_overwrite_existing(self, match: SportFileMatch) -> bool:
        source_name = match.source_path.name.lower()
        if any(keyword in source_name for keyword in ("repack", "proper")):
            return True

        if "2160p" in source_name:
            return True

        session_raw = str(match.context.get("session") or "").strip()
        if not session_raw:
            return False

        session_specificity = specificity_score(session_raw)
        if session_specificity == 0:
            return False

        session_token = normalize_token(session_raw)
        candidates = alias_candidates(match)

        baseline_scores = [
            specificity_score(alias)
            for alias in candidates
            if normalize_token(alias) != session_token
        ]

        if not baseline_scores:
            return False

        return session_specificity > min(baseline_scores)

    def _format_relative_destination(self, destination: Path) -> str:
        return format_relative_destination(destination, self.config.settings.destination_dir)

    def _record_destination_touch(self, destination: Path) -> None:
        self._touched_destinations.add(self._format_relative_destination(destination))

    def _cleanup_old_destination(
        self,
        source_key: str,
        old_destination: Optional[Path],
        new_destination: Path,
        *,
        dry_run: bool,
    ) -> None:
        self._stale_records.pop(source_key, None)
        if not old_destination:
            self._stale_destinations.pop(source_key, None)
            return

        if old_destination == new_destination:
            self._stale_destinations.pop(source_key, None)
            return

        if not old_destination.exists() or old_destination.is_dir():
            self._stale_destinations.pop(source_key, None)
            return

        if dry_run:
            LOGGER.debug(
                self._format_log(
                    "Dry-Run: Would Remove Obsolete Destination",
                    {
                        "Source": source_key,
                        "Old Destination": old_destination,
                        "Replaced With": self._format_relative_destination(new_destination),
                    },
                )
            )
            self._stale_destinations.pop(source_key, None)
            return

        try:
            old_destination.unlink()
        except OSError as exc:
            LOGGER.warning(
                self._format_log(
                    "Failed To Remove Obsolete Destination",
                    {
                        "Source": source_key,
                        "Old Destination": old_destination,
                        "Error": exc,
                    },
                )
            )
        else:
            LOGGER.debug(
                self._format_log(
                    "Removed Obsolete Destination",
                    {
                        "Source": source_key,
                        "Removed": self._format_relative_destination(old_destination),
                        "Replaced With": self._format_relative_destination(new_destination),
                    },
                )
            )
        finally:
            self._stale_destinations.pop(source_key, None)
