"""File match processing including link creation and overwrite decisions.

This module handles the processing of file matches including creating symlinks
or hard links, making overwrite decisions based on quality indicators, updating
the processed file cache, and cleaning up old destinations when files move.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from .cache import CachedFileRecord, ProcessedFileCache
from .models import ProcessingStats, SportFileMatch
from .notifications import NotificationEvent
from .utils import hash_file, link_file, normalize_token

LOGGER = logging.getLogger(__name__)


def specificity_score(value: str) -> int:
    """Calculate a specificity score for a file or episode name.

    Higher scores indicate more specific names (e.g., with part numbers,
    stage indicators, or other distinguishing markers). This helps determine
    which file should take priority when multiple files could match the same
    destination.

    Args:
        value: The file or episode name to score.

    Returns:
        An integer specificity score (higher is more specific).
    """
    if not value:
        return 0

    score = 0
    lower = value.lower()

    # Digits are strong indicators of specificity
    digit_count = sum(ch.isdigit() for ch in value)
    score += digit_count * 2

    # Separators also add specificity
    score += lower.count(".") + lower.count("-") + lower.count("_")

    # Part indicators
    if re.search(r"\bpart[\s._-]*\d+\b", lower):
        score += 2
    if re.search(r"\bstage[\s._-]*\d+\b", lower):
        score += 1
    if re.search(r"\b(?:heat|round|leg|match|session)[\s._-]*\d+\b", lower):
        score += 1
    if re.search(r"(?:^|[\s._-])(qf|sf|q|fp|sp)[\s._-]*\d+\b", lower):
        score += 1

    # Spelled-out numbers
    spelled_markers = (
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "first",
        "second",
        "third",
        "fourth",
        "fifth",
        "sixth",
        "seventh",
        "eighth",
        "ninth",
        "tenth",
    )
    for marker in spelled_markers:
        if re.search(rf"\b{marker}\b", lower):
            score += 1

    return score


def alias_candidates(match: SportFileMatch) -> list[str]:
    """Get all possible alias candidates for a matched file.

    This includes the episode's canonical title, its configured aliases,
    and any session-specific aliases from the pattern configuration.

    Args:
        match: The matched file to get alias candidates for.

    Returns:
        A deduplicated list of alias candidates in priority order.
    """
    candidates: list[str] = []

    canonical = match.episode.title
    if canonical:
        candidates.append(canonical)

    candidates.extend(match.episode.aliases)

    session_aliases = match.pattern.session_aliases
    if canonical in session_aliases:
        candidates.extend(session_aliases[canonical])
    else:
        canonical_token = normalize_token(canonical) if canonical else ""
        for key, aliases in session_aliases.items():
            if canonical_token and normalize_token(key) == canonical_token:
                candidates.extend(aliases)
                break

    # Deduplicate while preserving order and skip falsy values
    seen: set[str] = set()
    unique_candidates: list[str] = []
    for value in candidates:
        if not value:
            continue
        if value not in seen:
            seen.add(value)
            unique_candidates.append(value)

    return unique_candidates


def season_cache_key(match: SportFileMatch) -> str | None:
    """Generate a cache key for a season.

    The cache key is used to track processed files across different runs.
    It prefers explicit season keys, then display numbers, and falls back
    to season index.

    Args:
        match: The matched file containing season information.

    Returns:
        A string cache key for the season, or None if the season has no key.
    """
    season = match.season
    key = season.key
    if key is not None:
        return str(key)
    if season.display_number is not None:
        return f"display:{season.display_number}"
    return f"index:{season.index}"


def episode_cache_key(match: SportFileMatch) -> str:
    """Generate a cache key for an episode.

    The cache key is used to track processed files across different runs.
    It prefers metadata IDs (id, guid, episode_id, uuid), then display number,
    then title, and falls back to episode index.

    Args:
        match: The matched file containing episode information.

    Returns:
        A string cache key for the episode.
    """
    episode = match.episode
    metadata = episode.metadata or {}
    for field in ("id", "guid", "episode_id", "uuid"):
        value = metadata.get(field)
        if value:
            return f"{field}:{value}"
    if episode.display_number is not None:
        return f"display:{episode.display_number}"
    if episode.title:
        return f"title:{episode.title}"
    return f"index:{episode.index}"


def should_overwrite_existing(match: SportFileMatch) -> bool:
    """Determine if an existing destination file should be overwritten.

    Decides whether to replace an existing destination based on quality
    indicators (repack, proper, 2160p) and specificity of session names.
    A more specific session name (e.g., "Quarter Final 2") should replace
    a less specific one (e.g., "Quarter Final").

    Args:
        match: The matched file to check for overwrite priority.

    Returns:
        True if the source file should replace the existing destination,
        False otherwise.
    """
    source_name = match.source_path.name.lower()

    # Always overwrite for repacks/propers (higher quality releases)
    if any(keyword in source_name for keyword in ("repack", "proper")):
        return True

    # Always overwrite for 4K releases
    if "2160p" in source_name:
        return True

    # Check session specificity
    session_raw = str(match.context.get("session") or "").strip()
    if not session_raw:
        return False

    session_specificity = specificity_score(session_raw)
    if session_specificity == 0:
        return False

    session_token = normalize_token(session_raw)
    candidates = alias_candidates(match)

    baseline_scores = [specificity_score(alias) for alias in candidates if normalize_token(alias) != session_token]

    if not baseline_scores:
        return False

    return session_specificity > min(baseline_scores)


def cleanup_old_destination(
    source_key: str,
    old_destination: Path | None,
    new_destination: Path,
    *,
    dry_run: bool,
    stale_records: dict[str, CachedFileRecord],
    stale_destinations: dict[str, Path],
    format_destination_fn,
    logger,
) -> None:
    """Clean up old destination file when a source file moves to a new destination.

    This removes obsolete symlinks/hardlinks when metadata changes cause a file
    to be re-matched to a different episode or destination path.

    Args:
        source_key: Unique key identifying the source file.
        old_destination: Previous destination path, if any.
        new_destination: New destination path.
        dry_run: If True, only log what would be done.
        stale_records: Dictionary of stale cache records to clean up.
        stale_destinations: Dictionary of stale destination paths to clean up.
        format_destination_fn: Function to format destination paths for display.
        logger: Logger instance for output.
    """
    # Always clean up stale record
    stale_records.pop(source_key, None)

    if not old_destination:
        stale_destinations.pop(source_key, None)
        return

    if old_destination == new_destination:
        stale_destinations.pop(source_key, None)
        return

    if not old_destination.exists() or old_destination.is_dir():
        stale_destinations.pop(source_key, None)
        return

    if dry_run:
        from .logging_utils import render_fields_block

        logger.debug(
            render_fields_block(
                "Dry-Run: Would Remove Obsolete Destination",
                {
                    "Source": source_key,
                    "Old Destination": old_destination,
                    "Replaced With": format_destination_fn(new_destination),
                },
                pad_top=True,
            )
        )
        stale_destinations.pop(source_key, None)
        return

    try:
        old_destination.unlink()
    except OSError as exc:
        from .logging_utils import render_fields_block

        logger.warning(
            render_fields_block(
                "Failed To Remove Obsolete Destination",
                {
                    "Source": source_key,
                    "Old Destination": old_destination,
                    "Error": exc,
                },
                pad_top=True,
            )
        )
    else:
        from .logging_utils import render_fields_block

        logger.debug(
            render_fields_block(
                "Removed Obsolete Destination",
                {
                    "Source": source_key,
                    "Removed": format_destination_fn(old_destination),
                    "Replaced With": format_destination_fn(new_destination),
                },
                pad_top=True,
            )
        )
    finally:
        stale_destinations.pop(source_key, None)


def handle_match(
    match: SportFileMatch,
    stats: ProcessingStats,
    *,
    processed_cache: ProcessedFileCache,
    stale_destinations: dict[str, Path],
    stale_records: dict[str, CachedFileRecord],
    skip_existing: bool,
    dry_run: bool,
    link_mode: str,
    format_destination_fn,
    logger,
) -> tuple[NotificationEvent | None, bool, str | None]:
    """Process a file match: create link, update cache, handle overwrites.

    This is the core file processing logic that:
    - Checks if destination exists and decides whether to overwrite
    - Creates symlink or hardlink to destination
    - Updates processed file cache
    - Cleans up old destinations when files move
    - Creates notification events

    Args:
        match: The matched file to process.
        stats: Processing statistics to update.
        processed_cache: Cache tracking processed files.
        stale_destinations: Dictionary of old destination paths to clean up.
        stale_records: Dictionary of stale cache records.
        skip_existing: If True, skip files with existing destinations.
        dry_run: If True, don't actually create links or modify cache.
        link_mode: Link mode ("symlink", "hardlink", or "copy").
        format_destination_fn: Function to format destination paths for display.
        logger: Logger instance for output.

    Returns:
        Tuple of (notification_event, kometa_trigger_needed, sport_id_if_processed).
        - notification_event: Event describing what happened (or None).
        - kometa_trigger_needed: True if Kometa should be triggered.
        - sport_id_if_processed: Sport ID if file was processed, None otherwise.
    """
    from .logging_utils import render_fields_block

    destination = match.destination_path
    source_key = str(match.source_path)
    old_destination = stale_destinations.get(source_key)

    cache_kwargs = {
        "sport_id": match.sport.id,
        "season_key": season_cache_key(match),
        "episode_key": episode_cache_key(match),
    }

    stale_record = stale_records.get(source_key)
    destination_display = format_destination_fn(destination)

    # Calculate file checksum
    file_checksum: str | None = None
    try:
        file_checksum = hash_file(match.source_path)
    except ValueError as exc:  # pragma: no cover - depends on filesystem state
        logger.debug(
            render_fields_block(
                "Failed To Hash Source",
                {
                    "Source": match.source_path,
                    "Error": exc,
                },
                pad_top=True,
            )
        )

    # Determine event type based on file history
    stored_checksum = processed_cache.get_checksum(match.source_path)
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

    # Create notification event
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

    # Check if destination exists and handle skip/overwrite logic
    replace_existing = False
    if destination.exists():
        if skip_existing:
            if should_overwrite_existing(match):
                replace_existing = True
            else:
                logger.debug(
                    render_fields_block(
                        "Skipping Existing Destination",
                        {
                            "Destination": destination,
                            "Source": match.source_path,
                        },
                        pad_top=True,
                    )
                )
                cleanup_old_destination(
                    source_key,
                    old_destination,
                    destination,
                    dry_run=dry_run,
                    stale_records=stale_records,
                    stale_destinations=stale_destinations,
                    format_destination_fn=format_destination_fn,
                    logger=logger,
                )
                skip_message = f"Destination exists: {destination} (source {match.source_path})"
                stats.register_skipped(skip_message, is_error=False, sport_id=match.sport.id)
                if not dry_run:
                    processed_cache.mark_processed(
                        match.source_path,
                        destination,
                        checksum=file_checksum,
                        **cache_kwargs,
                    )
                event.action = "skipped"
                event.skip_reason = skip_message
                event.event_type = "skipped"
                return event, False, None

    # Handle replace existing destination
    if replace_existing:
        logger.debug(
            render_fields_block(
                "Preparing To Replace Destination",
                {"Destination": destination},
                pad_top=True,
            )
        )
        if not dry_run:
            try:
                destination.unlink()
            except OSError as exc:
                logger.error(
                    render_fields_block(
                        "Failed To Remove Destination",
                        {
                            "Destination": destination,
                            "Error": exc,
                        },
                        pad_top=True,
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
                return event, False, None

    # Log what we're about to do
    logger.debug(
        render_fields_block(
            "Processed",
            {
                "Action": "replace" if replace_existing else "link",
                "Sport": match.sport.id,
                "Season": match.context.get("season_title"),
                "Session": match.context.get("session"),
                "Dest": destination_display,
                "Src": match.source_path.name,
            },
            pad_top=True,
        )
    )

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            render_fields_block(
                "Processing Details",
                {
                    "Source": match.source_path,
                    "Destination": destination,
                    "Link Mode": link_mode,
                    "Replace": replace_existing,
                },
                pad_top=True,
            )
        )

    # Handle dry-run mode
    if dry_run:
        stats.register_processed()
        event.action = "dry-run"
        event.event_type = "dry-run"
        event.replaced = replace_existing
        return event, False, match.sport.id

    # Actually create the link
    result = link_file(match.source_path, destination, mode=link_mode)
    if result.created:
        stats.register_processed()
        processed_cache.mark_processed(
            match.source_path,
            destination,
            checksum=file_checksum,
            **cache_kwargs,
        )
        cleanup_old_destination(
            source_key,
            old_destination,
            destination,
            dry_run=dry_run,
            stale_records=stale_records,
            stale_destinations=stale_destinations,
            format_destination_fn=format_destination_fn,
            logger=logger,
        )
        event.action = link_mode
        event.replaced = replace_existing
        return event, True, match.sport.id
    else:
        failure_message = f"Failed to link {match.source_path} -> {destination}: {result.reason}"
        stats.register_skipped(failure_message, sport_id=match.sport.id)
        if result.reason == "destination-exists":
            processed_cache.mark_processed(
                match.source_path,
                destination,
                checksum=file_checksum,
                **cache_kwargs,
            )
            cleanup_old_destination(
                source_key,
                old_destination,
                destination,
                dry_run=dry_run,
                stale_records=stale_records,
                stale_destinations=stale_destinations,
                format_destination_fn=format_destination_fn,
                logger=logger,
            )
            event.action = "skipped"
            event.skip_reason = failure_message
            event.event_type = "skipped"
            return event, False, None
        event.action = "error"
        event.skip_reason = failure_message
        event.event_type = "error"
        return event, False, None
