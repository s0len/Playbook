from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.progress import Progress

from .cache import ProcessedFileCache
from .config import AppConfig
from .destination_builder import build_destination, build_match_context, format_relative_destination
from .file_discovery import gather_source_files, matches_globs, should_suppress_sample_ignored
from .kometa_trigger import build_kometa_trigger
from .logging_utils import render_fields_block
from .match_handler import handle_match
from .matcher import PatternRuntime, match_file_to_episode
from .metadata import MetadataFingerprintStore
from .metadata_loader import SportRuntime, load_sports
from .models import ProcessingStats, SportFileMatch
from .notifications import NotificationEvent, NotificationService
from .persistence import ProcessedFileRecord, ProcessedFileStore
from .plex_metadata_sync import PlexMetadataSync, create_plex_sync_from_config
from .post_run_triggers import run_plex_sync_if_needed, trigger_kometa_if_needed
from .processing_state import ProcessingState
from .run_summary import (
    has_activity,
    has_detailed_activity,
    log_detailed_summary,
    log_run_recap,
)
from .trace_writer import TraceOptions, persist_trace
from .utils import ensure_directory

LOGGER = logging.getLogger(__name__)


class Processor:
    def __init__(
        self,
        config: AppConfig,
        *,
        enable_notifications: bool = True,
        trace_options: TraceOptions | None = None,
    ) -> None:
        self.config = config
        if not self.config.settings.dry_run:
            ensure_directory(self.config.settings.destination_dir)
            ensure_directory(self.config.settings.cache_dir)
        self.processed_cache = ProcessedFileCache(self.config.settings.cache_dir)
        self.metadata_fingerprints = MetadataFingerprintStore(self.config.settings.cache_dir)
        self.processed_store = ProcessedFileStore(self.config.settings.cache_dir / "playbook.db")
        self.trace_options = trace_options or TraceOptions()
        settings = self.config.settings
        self.notification_service = NotificationService(
            settings.notifications,
            cache_dir=settings.cache_dir,
            destination_dir=settings.destination_dir,
            enabled=enable_notifications,
        )
        self._kometa_trigger = build_kometa_trigger(settings.kometa_trigger)
        self._plex_sync: PlexMetadataSync | None = create_plex_sync_from_config(config)

        # Mutable processing state (reset between runs)
        self._state = ProcessingState()

    # Backwards-compatible property accessors for tests
    @property
    def _kometa_trigger_fired(self) -> bool:
        return self._state.kometa_trigger_fired

    @_kometa_trigger_fired.setter
    def _kometa_trigger_fired(self, value: bool) -> None:
        self._state.kometa_trigger_fired = value

    @property
    def _kometa_trigger_needed(self) -> bool:
        return self._state.kometa_trigger_needed

    @_kometa_trigger_needed.setter
    def _kometa_trigger_needed(self, value: bool) -> None:
        self._state.kometa_trigger_needed = value

    @staticmethod
    def _format_log(event: str, fields: Mapping[str, object] | None = None) -> str:
        return render_fields_block(event, fields or {}, pad_top=True)

    @staticmethod
    def _format_inline_log(event: str, fields: Mapping[str, object] | None = None) -> str:
        return render_fields_block(event, fields or {}, pad_top=False)

    def _load_sports(self) -> list[SportRuntime]:
        """Load sports metadata in parallel and track changes.

        Delegates to metadata_loader.load_sports() and unpacks results into
        processing state for tracking metadata changes and fetch statistics.

        Returns:
            List of successfully loaded SportRuntime objects
        """
        result = load_sports(
            sports=self.config.sports,
            settings=self.config.settings,
            metadata_fingerprints=self.metadata_fingerprints,
        )

        # Unpack results into processing state
        self._state.metadata_changed_sports = result.changed_sports
        self._state.metadata_change_map = result.change_map
        self._state.metadata_fetch_stats = result.fetch_stats

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
        # Reset state for new run (preserves previous_summary for deduplication)
        self._state.reset()
        runtimes = self._load_sports()

        if self._state.metadata_changed_sports:
            labels = ", ".join(
                f"{sport_id} ({sport_name})" if sport_name and sport_name != sport_id else sport_id
                for sport_id, sport_name in self._state.metadata_changed_sports
            )
            LOGGER.info(
                self._format_log(
                    "Metadata Updated",
                    {
                        "Sports": labels or "(unknown)",
                    },
                )
            )
            removed_records = self.processed_cache.remove_by_metadata_changes(self._state.metadata_change_map)
            self._state.stale_destinations = {
                source: Path(record.destination) for source, record in removed_records.items() if record.destination
            }
            self._state.stale_records = removed_records
        stats = ProcessingStats()
        run_started = time.perf_counter()

        try:
            all_source_files = list(self._gather_source_files(stats))
            filtered_source_files: list[Path] = []
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

            with Progress(disable=not LOGGER.isEnabledFor(logging.INFO)) as progress:
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
            summary_changed = summary_counts != self._state.previous_summary
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
            self._state.previous_summary = summary_counts
            if stats.errors:
                for error in stats.errors:
                    LOGGER.error(
                        self._format_log(
                            "Processing Error",
                            {"Detail": error},
                        )
                    )

            has_details = has_detailed_activity(stats)
            has_errors = bool(stats.errors)
            if LOGGER.isEnabledFor(logging.DEBUG):
                # In DEBUG mode, show detailed summary when there's any activity
                has_issues = has_errors or bool(stats.warnings)
                if has_details or has_issues:
                    level = logging.INFO if has_issues else logging.DEBUG
                    self._log_detailed_summary(stats, level=level)
            elif has_errors:
                # At INFO level, only show detailed summary for actual errors
                # (warnings are already logged individually and counted in Run Recap)
                self._log_detailed_summary(stats)
            self._trigger_post_run_trigger_if_needed(stats)
            # Send summary notification if in summary mode
            self.notification_service.send_summary()
            duration = time.perf_counter() - run_started
            self._log_run_recap(stats, duration)
            return stats
        finally:
            if not self.config.settings.dry_run:
                self.processed_cache.save()
                self.metadata_fingerprints.save()

    def _gather_source_files(self, stats: ProcessingStats | None = None) -> Iterable[Path]:
        """Discover and yield source files for processing.

        Delegates to file_discovery.gather_source_files().
        """
        return gather_source_files(self.config.settings.source_dir, stats)

    def _process_single_file(
        self,
        source_path: Path,
        runtimes: list[SportRuntime],
        stats: ProcessingStats,
        *,
        is_sample_file: bool = False,
    ) -> tuple[bool, list[tuple[str, str, str | None]]]:
        suffix = source_path.suffix.lower()
        matching_runtimes = [runtime for runtime in runtimes if suffix in runtime.extensions]
        ignored_reasons: list[tuple[str, str, str | None]] = []

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
            trace_context: dict[str, Any] | None = None
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

            detection_messages: list[tuple[str, str]] = []
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
                    message = f"{runtime.sport.id}: Unsafe destination for {source_path.name} - {exc}"
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

    def _persist_trace(self, trace: dict[str, Any] | None) -> Path | None:
        return persist_trace(trace, self.trace_options, self.config.settings.cache_dir)

    def _format_ignored_detail(
        self,
        source_path: Path,
        diagnostics: list[tuple[str, str, str | None]],
    ) -> str:
        if not diagnostics:
            return f"{source_path.name}\n  - [IGNORED] No diagnostics recorded"

        lines = [source_path.name]
        seen: set[str] = set()
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
            plex_sync_stats=self._state.plex_sync_stats,
            level=level,
        )

    def _log_run_recap(self, stats: ProcessingStats, duration: float) -> None:
        """Log run recap with duration, stats, and follow-up actions (delegates to run_summary module)."""
        log_run_recap(
            stats,
            duration,
            touched_destinations=sorted(self._state.touched_destinations),
            plex_sync_enabled=self._plex_sync is not None,
            plex_sync_ran=self._state.plex_sync_ran,
            plex_sync_stats=self._state.plex_sync_stats,
            plex_sync_dry_run=self._plex_sync.dry_run if self._plex_sync else False,
            global_dry_run=self.config.settings.dry_run,
            kometa_enabled=self._kometa_trigger.enabled,
            kometa_fired=self._state.kometa_trigger_fired,
        )

    def _build_context(self, runtime: SportRuntime, source_path: Path, season, episode, groups) -> dict[str, object]:
        return build_match_context(
            runtime=runtime,
            source_path=source_path,
            season=season,
            episode=episode,
            groups=groups,
            source_dir=self.config.settings.source_dir,
        )

    def _build_destination(self, runtime: SportRuntime, pattern: PatternRuntime, context: dict[str, object]) -> Path:
        return build_destination(
            runtime=runtime,
            pattern=pattern,
            context=context,
            settings=self.config.settings,
        )

    def _handle_match(self, match: SportFileMatch, stats: ProcessingStats) -> NotificationEvent | None:
        """Process a file match: create link, update cache, handle overwrites.

        Delegates to match_handler.handle_match().
        """
        settings = self.config.settings
        link_mode = (match.sport.link_mode or settings.link_mode).lower()

        event, kometa_trigger_needed, sport_id = handle_match(
            match,
            stats,
            processed_cache=self.processed_cache,
            stale_destinations=self._state.stale_destinations,
            stale_records=self._state.stale_records,
            skip_existing=settings.skip_existing,
            dry_run=settings.dry_run,
            link_mode=link_mode,
            format_destination_fn=self._format_relative_destination,
            logger=LOGGER,
        )

        # Update processing state based on results
        if kometa_trigger_needed and not settings.dry_run:
            self._state.kometa_trigger_needed = True

        if sport_id:
            self._record_destination_touch(match.destination_path)
            self._state.sports_with_processed_files.add(sport_id)

            # Record processed file in persistence store (skip in dry-run mode)
            if not settings.dry_run and event:
                self._record_processed_file(match, event)

        return event

    def _record_processed_file(self, match: SportFileMatch, event: NotificationEvent) -> None:
        """Record a processed file in the persistence store."""
        # Map action to ProcessingStatus
        action_to_status = {
            "hardlink": "linked",
            "copy": "copied",
            "symlink": "symlinked",
            "skipped": "skipped",
            "error": "error",
        }
        status = action_to_status.get(event.action, "linked")

        record = ProcessedFileRecord(
            source_path=str(match.source_path),
            destination_path=str(match.destination_path),
            sport_id=match.sport.id,
            show_id=match.show.key,  # Show model uses 'key' not 'id'
            season_index=match.season.index,
            episode_index=match.episode.index,
            processed_at=datetime.now(),
            checksum=None,  # Checksum is handled by ProcessedFileCache
            status=status,
            error_message=event.skip_reason if status == "error" else None,
        )
        self.processed_store.record_processed(record)

    def _trigger_post_run_trigger_if_needed(self, stats: ProcessingStats) -> None:
        """Run post-run triggers: Plex sync and Kometa (delegates to post_run_triggers module)."""
        # Run Plex metadata sync if enabled and we processed files
        self._run_plex_sync_if_needed(stats)

        # Run Kometa trigger if enabled (legacy, may be removed)
        self._state.kometa_trigger_fired, self._state.kometa_trigger_needed = trigger_kometa_if_needed(
            self._kometa_trigger,
            self._state.kometa_trigger_fired,
            self._state.kometa_trigger_needed,
            global_dry_run=self.config.settings.dry_run,
            stats=stats,
        )

    def _run_plex_sync_if_needed(self, stats: ProcessingStats) -> None:
        """Run Plex metadata sync after file processing (delegates to post_run_triggers module)."""
        self._state.plex_sync_stats, self._state.plex_sync_ran = run_plex_sync_if_needed(
            self._plex_sync,
            self._state.plex_sync_ran,
            global_dry_run=self.config.settings.dry_run,
            sports_with_processed_files=self._state.sports_with_processed_files,
            metadata_changed_sports=self._state.metadata_changed_sports,
        )

    def _format_relative_destination(self, destination: Path) -> str:
        return format_relative_destination(destination, self.config.settings.destination_dir)

    def _record_destination_touch(self, destination: Path) -> None:
        self._state.touched_destinations.add(self._format_relative_destination(destination))
