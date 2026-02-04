"""File match processing including link creation and overwrite decisions.

This module handles the processing of file matches including creating symlinks
or hard links, making overwrite decisions based on quality indicators, updating
the processed file cache, and cleaning up old destinations when files move.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from .models import ProcessingStats, SportFileMatch
from .notifications import NotificationEvent
from .persistence import ProcessedFileRecord
from .quality import QualityInfo, extract_quality
from .quality_scorer import QualityScore, compare_quality, compute_quality_score
from .utils import link_file, normalize_token

if TYPE_CHECKING:
    from .config import QualityProfile
    from .persistence import ProcessedFileStore

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

    session_aliases = match.pattern.config.session_aliases
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


def evaluate_quality_upgrade(
    match: SportFileMatch,
    quality_profile: QualityProfile,
    processed_store: ProcessedFileStore | None,
    captured_groups: dict | None = None,
) -> tuple[bool, QualityInfo, QualityScore, str]:
    """Evaluate whether to upgrade based on quality scoring.

    This function extracts quality attributes from the source filename,
    computes a quality score, and compares it against the existing file's
    score (if any) to determine if an upgrade should happen.

    Args:
        match: The matched file to evaluate.
        quality_profile: Quality profile with scoring configuration.
        processed_store: Persistence store for looking up existing quality scores.
        captured_groups: Optional regex capture groups from pattern matching.

    Returns:
        Tuple of:
        - should_upgrade: Whether the file should replace an existing one
        - quality_info: Extracted quality attributes
        - quality_score: Computed quality score
        - reason: Human-readable explanation for the decision
    """
    # Extract quality from the source filename
    quality_info = extract_quality(match.source_path.name, captured_groups)
    quality_score = compute_quality_score(quality_info, quality_profile)

    # Check minimum score threshold first
    if quality_profile.min_score is not None and quality_score.total < quality_profile.min_score:
        reason = f"Below minimum score threshold: {quality_score.total} < {quality_profile.min_score}"
        return False, quality_info, quality_score, reason

    # Look up existing quality score from persistence store
    existing_score: int | None = None
    if processed_store is not None:
        destination_str = str(match.destination_path)
        existing_score = processed_store.get_quality_score(destination_str)

    # Compare quality
    comparison = compare_quality(quality_info, existing_score, quality_profile)

    return comparison.should_upgrade, quality_info, quality_score, comparison.reason


def should_upgrade_with_quality(
    match: SportFileMatch,
    quality_profile: QualityProfile | None,
    processed_store: ProcessedFileStore | None,
    captured_groups: dict | None = None,
) -> tuple[bool, QualityInfo | None, QualityScore | None, str]:
    """Determine if a file should upgrade an existing destination using quality scoring.

    When quality profile is enabled, uses quality-based comparison.
    Otherwise, falls back to legacy should_overwrite_existing logic.

    Args:
        match: The matched file to check.
        quality_profile: Quality profile (None or disabled = use legacy logic).
        processed_store: Persistence store for quality score lookups.
        captured_groups: Optional regex capture groups.

    Returns:
        Tuple of:
        - should_upgrade: Whether the file should replace existing
        - quality_info: Extracted quality info (None if using legacy mode)
        - quality_score: Computed score (None if using legacy mode)
        - reason: Explanation for the decision
    """
    # If quality profile is not enabled, use legacy logic
    if quality_profile is None or not quality_profile.enabled:
        should_upgrade = should_overwrite_existing(match)
        if should_upgrade:
            return True, None, None, "Legacy upgrade (PROPER/REPACK/4K or specificity)"
        return False, None, None, "No upgrade (legacy mode)"

    # Use quality-based evaluation
    return evaluate_quality_upgrade(match, quality_profile, processed_store, captured_groups)


def cleanup_old_destination(
    source_key: str,
    old_destination: Path | None,
    new_destination: Path,
    *,
    dry_run: bool,
    stale_records: dict[str, ProcessedFileRecord],
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
        stale_records: Dictionary of stale records to clean up.
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
        # Use missing_ok=True to handle race condition where file was deleted externally
        old_destination.unlink(missing_ok=True)
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
        return  # Don't log success if we failed
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


def format_quality_summary(
    quality_info: QualityInfo | None,
    quality_score: QualityScore | None,
) -> str | None:
    """Format quality information into a human-readable summary string.

    Args:
        quality_info: Extracted quality attributes.
        quality_score: Computed quality score with breakdown.

    Returns:
        A formatted string like "440 (1080p: 300, webdl: 90, mwr: 50)" or None if no info.
    """
    if quality_score is None:
        return None

    parts = []

    # Resolution
    if quality_info and quality_info.resolution and quality_score.resolution_score > 0:
        parts.append(f"{quality_info.resolution}: {quality_score.resolution_score}")

    # Source
    if quality_info and quality_info.source and quality_score.source_score > 0:
        parts.append(f"{quality_info.source}: {quality_score.source_score}")

    # Release group
    if quality_info and quality_info.release_group and quality_score.release_group_score > 0:
        parts.append(f"{quality_info.release_group}: {quality_score.release_group_score}")

    # Bonuses
    if quality_score.proper_bonus > 0:
        parts.append(f"proper: +{quality_score.proper_bonus}")
    if quality_score.repack_bonus > 0:
        parts.append(f"repack: +{quality_score.repack_bonus}")
    if quality_score.hdr_bonus > 0:
        hdr_label = quality_info.hdr_format if quality_info and quality_info.hdr_format else "hdr"
        parts.append(f"{hdr_label}: +{quality_score.hdr_bonus}")

    if parts:
        return f"{quality_score.total} ({', '.join(parts)})"
    return str(quality_score.total) if quality_score.total > 0 else None


def handle_match(
    match: SportFileMatch,
    stats: ProcessingStats,
    *,
    stale_destinations: dict[str, Path],
    stale_records: dict[str, ProcessedFileRecord],
    skip_existing: bool,
    dry_run: bool,
    link_mode: str,
    format_destination_fn,
    logger,
    quality_profile: QualityProfile | None = None,
    processed_store: ProcessedFileStore | None = None,
    captured_groups: dict | None = None,
) -> tuple[NotificationEvent | None, bool, str | None, QualityInfo | None, QualityScore | None]:
    """Process a file match: create link, update cache, handle overwrites.

    This is the core file processing logic that:
    - Checks if destination exists and decides whether to overwrite
    - Creates symlink or hardlink to destination
    - Cleans up old destinations when files move
    - Creates notification events
    - Extracts and returns quality information when quality profile is enabled

    Args:
        match: The matched file to process.
        stats: Processing statistics to update.
        stale_destinations: Dictionary of old destination paths to clean up.
        stale_records: Dictionary of stale records from metadata changes.
        skip_existing: If True, skip files with existing destinations.
        dry_run: If True, don't actually create links.
        link_mode: Link mode ("symlink", "hardlink", or "copy").
        format_destination_fn: Function to format destination paths for display.
        logger: Logger instance for output.
        quality_profile: Optional quality profile for quality-based upgrades.
        processed_store: Optional persistence store for quality score lookups.
        captured_groups: Optional regex capture groups from pattern matching.

    Returns:
        Tuple of (notification_event, kometa_trigger_needed, sport_id_if_processed, quality_info, quality_score).
        - notification_event: Event describing what happened (or None).
        - kometa_trigger_needed: True if Kometa should be triggered.
        - sport_id_if_processed: Sport ID if file was processed, None otherwise.
        - quality_info: Extracted quality info (None if quality profile disabled).
        - quality_score: Computed quality score (None if quality profile disabled).
    """
    from .logging_utils import render_fields_block

    destination = match.destination_path
    source_key = str(match.source_path)
    old_destination = stale_destinations.get(source_key)

    stale_record = stale_records.get(source_key)
    destination_display = format_destination_fn(destination)

    # Determine event type: "new" for first-time files, "refresh" for re-processing after metadata change
    event_type = "refresh" if stale_record else "new"

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

    # Extract quality information (always extracted for logging, but only used for scoring if profile enabled)
    quality_info: QualityInfo | None = None
    quality_score_obj: QualityScore | None = None
    quality_upgrade_reason: str = ""

    if quality_profile is not None and quality_profile.enabled:
        should_upgrade, quality_info, quality_score_obj, quality_upgrade_reason = should_upgrade_with_quality(
            match, quality_profile, processed_store, captured_groups
        )
    else:
        # Extract quality info even in legacy mode for logging purposes
        quality_info = extract_quality(match.source_path.name, captured_groups)

    # Check if destination exists and handle skip/overwrite logic
    replace_existing = False
    if destination.exists():
        if skip_existing:
            # Use quality-based upgrade decision if profile is enabled
            if quality_profile is not None and quality_profile.enabled:
                should_upgrade, quality_info, quality_score_obj, quality_upgrade_reason = should_upgrade_with_quality(
                    match, quality_profile, processed_store, captured_groups
                )
                if should_upgrade:
                    replace_existing = True
                    logger.debug(
                        render_fields_block(
                            "Quality Upgrade",
                            {
                                "Destination": destination,
                                "Source": match.source_path,
                                "Reason": quality_upgrade_reason,
                                "Score": quality_score_obj.total if quality_score_obj else "N/A",
                            },
                            pad_top=True,
                        )
                    )
                else:
                    # Check min_score rejection - this is a special case
                    if quality_profile.min_score is not None and quality_score_obj is not None:
                        if quality_score_obj.total < quality_profile.min_score:
                            min_score = quality_profile.min_score
                            skip_message = f"Quality below minimum: {quality_score_obj.total} < {min_score}"
                            logger.debug(
                                render_fields_block(
                                    "Rejecting Low Quality File",
                                    {
                                        "Source": match.source_path,
                                        "Score": quality_score_obj.total,
                                        "Min Score": quality_profile.min_score,
                                    },
                                    pad_top=True,
                                )
                            )
                            stats.register_skipped(skip_message, is_error=False, sport_id=match.sport.id)
                            event.action = "skipped"
                            event.skip_reason = skip_message
                            event.event_type = "skipped"
                            return event, False, None, quality_info, quality_score_obj

                    logger.debug(
                        render_fields_block(
                            "Skipping (Quality Not Better)",
                            {
                                "Destination": destination,
                                "Source": match.source_path,
                                "Reason": quality_upgrade_reason,
                            },
                            pad_top=True,
                        )
                    )
            elif should_overwrite_existing(match):
                replace_existing = True

            if not replace_existing:
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
                event.action = "skipped"
                event.skip_reason = skip_message
                event.event_type = "skipped"
                return event, False, None, quality_info, quality_score_obj

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
                # Use missing_ok=True to handle race condition where file was deleted
                # between exists() check and unlink() (e.g., by Plex or user)
                destination.unlink(missing_ok=True)
            except OSError as exc:
                # Only fail for real errors (permissions, etc.), not "file not found"
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
                return event, False, None, quality_info, quality_score_obj

    # Build processing details fields
    quality_summary = format_quality_summary(quality_info, quality_score_obj)
    action_desc = f"{link_mode} ({'replace existing' if replace_existing else 'new file'})"

    # Log at INFO level with quality info when available
    processed_fields: list[tuple[str, object]] = [
        ("Source", match.source_path.name),
        ("Destination", destination_display),
    ]
    if quality_summary:
        processed_fields.append(("Quality", quality_summary))
    if replace_existing and quality_upgrade_reason:
        processed_fields.append(("Upgrade", f"Yes ({quality_upgrade_reason})"))
    processed_fields.append(("Action", action_desc))

    logger.info(
        render_fields_block(
            "Processing Details",
            processed_fields,
            pad_top=True,
        )
    )

    # Handle dry-run mode
    if dry_run:
        stats.register_processed()
        event.action = "dry-run"
        event.event_type = "dry-run"
        event.replaced = replace_existing
        return event, False, match.sport.id, quality_info, quality_score_obj

    # Actually create the link
    result = link_file(match.source_path, destination, mode=link_mode)
    if result.created:
        stats.register_processed()
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
        return event, True, match.sport.id, quality_info, quality_score_obj
    else:
        failure_message = f"Failed to link {match.source_path} -> {destination}: {result.reason}"
        stats.register_skipped(failure_message, sport_id=match.sport.id)
        if result.reason == "destination-exists":
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
            return event, False, None, quality_info, quality_score_obj
        event.action = "error"
        event.skip_reason = failure_message
        event.event_type = "error"
        return event, False, None, quality_info, quality_score_obj
