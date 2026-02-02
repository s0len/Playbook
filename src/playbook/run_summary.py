"""Logging summaries, run recaps, and statistics formatting.

This module handles formatting and logging processing summaries including detailed
activity reports, run recaps with statistics, error summaries, and activity detection.
It provides utilities for formatting counts, messages, and Plex sync errors in a
consistent, readable format for logging output.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ProcessingStats
    from .plex_metadata_sync import PlexSyncStats

from .logging_utils import LogBlockBuilder

LOGGER = logging.getLogger(__name__)


def has_activity(stats: ProcessingStats) -> bool:
    """Check if processing stats show any activity.

    Args:
        stats: Processing statistics to check.

    Returns:
        True if there was any processing activity (processed, skipped, ignored, errors, or warnings).
    """
    return bool(stats.processed or stats.skipped or stats.ignored or stats.errors or stats.warnings)


def has_detailed_activity(stats: ProcessingStats) -> bool:
    """Check if processing stats have detailed activity worth logging.

    Args:
        stats: Processing statistics to check.

    Returns:
        True if there are errors, warnings, or detailed skip/ignore information.
    """
    return bool(stats.errors or stats.warnings or stats.skipped_details or stats.ignored_details)


def filtered_ignored_details(stats: ProcessingStats) -> list[str]:
    """Filter ignored details to suppress common non-actionable messages.

    Args:
        stats: Processing statistics containing ignored details.

    Returns:
        Filtered list of ignored details with suppression counts added.
    """
    filtered: list[str] = []
    suppressed_non_video = 0
    for detail in stats.ignored_details:
        if "No configured sport accepts extension" in detail:
            suppressed_non_video += 1
            continue
        filtered.append(detail)
    if stats.suppressed_ignored_samples:
        label = "sample" if stats.suppressed_ignored_samples == 1 else "samples"
        filtered.append(f"(Suppressed {stats.suppressed_ignored_samples} {label})")
    if suppressed_non_video:
        noun = "item" if suppressed_non_video == 1 else "items"
        filtered.append(f"(Suppressed {suppressed_non_video} non-video {noun})")
    return filtered


def summarize_counts(counts: dict[str, int], total: int, label: str) -> list[str]:
    """Summarize counts by sport/category with verbose prompt.

    Args:
        counts: Dictionary mapping sport/category to count.
        total: Total count across all categories.
        label: Label for the type of entries (e.g., "error", "warning", "ignored").

    Returns:
        List of summary lines showing per-sport counts and verbose prompt.
    """
    if total <= 0:
        return []
    lines: list[str] = []
    if counts:
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        for sport, value in ordered:
            suffix = "entry" if value == 1 else "entries"
            lines.append(f"{sport}: {value} {suffix}")
    remainder = total - sum(counts.values())
    if remainder > 0:
        suffix = "entry" if remainder == 1 else "entries"
        lines.append(f"other: {remainder} {suffix}")
    lines.append(f"Run with --verbose for per-{label} details.")
    return lines


def summarize_messages(entries: list[str], *, limit: int = 5) -> list[str]:
    """Summarize messages by grouping duplicates and showing top N.

    Args:
        entries: List of message strings to summarize.
        limit: Maximum number of unique messages to show.

    Returns:
        List of summary lines with duplicate counts and verbose prompt.
    """
    if not entries:
        return []
    counter = Counter(entries)
    ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    lines: list[str] = []
    for text, count in ordered[:limit]:
        prefix = f"{count}× " if count > 1 else ""
        lines.append(f"{prefix}{text}")
    remaining = len(ordered) - limit
    if remaining > 0:
        lines.append(f"... {remaining} more (use --verbose for full list)")
    else:
        lines.append("Run with --verbose for per-file details.")
    return lines


def summarize_plex_errors(errors: list[str], *, limit: int = 10) -> list[str]:
    """Summarize Plex sync errors, grouping by error type.

    Extracts and displays library name, metadata source URL, and close matches
    or available items from error strings for better actionability.

    Args:
        errors: List of Plex sync error strings.
        limit: Maximum number of error groups to show.

    Returns:
        List of formatted summary lines showing grouped errors with context.
    """
    if not errors:
        return []

    # Group errors by type (first part before colon or first few words)
    grouped: dict[str, list[str]] = {}
    for error in errors:
        # Extract error category (e.g., "Show not found", "Season not found", etc.)
        if ":" in error:
            category = error.split(":")[0].strip()
        else:
            # Use first 30 chars as category
            category = error[:30].strip()
        grouped.setdefault(category, []).append(error)

    lines: list[str] = []
    shown = 0
    for category, errs in sorted(grouped.items(), key=lambda x: -len(x[1])):
        if shown >= limit:
            break
        if len(errs) > 1:
            lines.append(f"{len(errs)}× {category}")
            # Extract and display contextual information from first error
            example = errs[0]
            context_info = extract_error_context(example)
            if context_info:
                lines.append(f"    └─ {context_info}")
            else:
                # Fall back to truncated example
                if len(example) > 80:
                    example = example[:77] + "..."
                lines.append(f"    └─ e.g.: {example}")
        else:
            err = errs[0]
            context_info = extract_error_context(err)
            if context_info:
                lines.append(f"- {category}: {context_info}")
            else:
                if len(err) > 80:
                    err = err[:77] + "..."
                lines.append(f"- {err}")
        shown += 1

    remaining = len(grouped) - shown
    if remaining > 0:
        lines.append(f"... {remaining} more error types")

    return lines


def extract_error_context(error: str) -> str | None:
    """Extract actionable context from Plex error strings.

    Parses error strings to extract library name, metadata source URL,
    and similar/available items for display.

    Args:
        error: Plex error string to parse.

    Returns:
        Formatted context string or None if parsing fails.
    """
    # Pattern for "Show not found: '{title}' in library {library_id} (metadata: {url}). Similar: {matches}"
    show_match = re.match(
        r"Show not found:\s*'([^']+)'\s*in library\s*(\S+)\s*\(metadata:\s*([^)]+)\)\.?\s*(.*)",
        error,
    )
    if show_match:
        title, library_id, metadata_url, remainder = show_match.groups()
        parts = [f"'{title}'", f"library={library_id}"]
        # Extract similar shows if present
        if "Similar:" in remainder:
            similar_part = remainder.split("Similar:")[-1].strip()
            if similar_part:
                parts.append(f"similar=[{similar_part}]")
        # Truncate metadata URL for display
        if metadata_url:
            url_display = metadata_url
            if len(url_display) > 40:
                url_display = "..." + url_display[-37:]
            parts.append(f"source={url_display}")
        return " | ".join(parts)

    # Pattern for "Season not found: {info} in show '{title}' | library={id} | source={url}. Available: {seasons}"
    season_match = re.match(
        r"Season not found:\s*([^|]+)\s*in show\s*'([^']+)'\s*\|\s*library=(\S+)\s*\|\s*source=([^.]+)\.?\s*(.*)",
        error,
    )
    if season_match:
        season_info, show_title, library_id, source_url, remainder = season_match.groups()
        parts = [f"{season_info.strip()}", f"show='{show_title}'", f"library={library_id}"]
        # Extract available seasons if present
        if "Available:" in remainder:
            available_part = remainder.split("Available:")[-1].strip()
            if available_part:
                parts.append(f"plex has=[{available_part}]")
        return " | ".join(parts)

    # Pattern for "Episode not found: {info} in season {season} of '{title}' | library={id} | source={url}. Available: {episodes}"
    episode_match = re.match(
        r"Episode not found:\s*([^|]+)\s*in season\s*([^|]+)\s*of\s*'([^']+)'\s*\|\s*library=(\S+)\s*\|\s*source=([^.]+)\.?\s*(.*)",
        error,
    )
    if episode_match:
        episode_info, season_info, show_title, library_id, source_url, remainder = episode_match.groups()
        parts = [
            f"{episode_info.strip()}",
            f"season={season_info.strip()}",
            f"show='{show_title}'",
        ]
        # Extract available episodes if present
        if "Available:" in remainder:
            available_part = remainder.split("Available:")[-1].strip()
            if available_part:
                parts.append(f"plex has=[{available_part}]")
        return " | ".join(parts)

    # No pattern matched - return None to use fallback
    return None


def log_detailed_summary(
    stats: ProcessingStats,
    *,
    plex_sync_stats: PlexSyncStats | None = None,
    level: int = logging.INFO,
) -> None:
    """Log detailed summary of processing results.

    Shows counts for processed, skipped, ignored, warnings, and errors. When in
    DEBUG mode, shows full lists; otherwise shows summarized counts and prompts
    for verbose mode. Always surfaces Plex sync errors if present.

    Args:
        stats: Processing statistics to summarize.
        plex_sync_stats: Optional Plex sync statistics (for error display).
        level: Logging level to use (default INFO).
    """
    show_entries = LOGGER.isEnabledFor(logging.DEBUG)
    builder = LogBlockBuilder("Detailed Summary", pad_top=True)

    fields: dict[str, object] = {
        "Processed": stats.processed,
        "Skipped": stats.skipped,
        "Ignored": stats.ignored,
        "Warnings": len(stats.warnings),
        "Errors": len(stats.errors),
    }

    # Add Plex sync stats if available
    if plex_sync_stats:
        plex_errors = len(plex_sync_stats.errors)
        fields["Plex Sync Errors"] = plex_errors

    builder.add_fields(fields)

    if show_entries:
        builder.add_section("Errors", stats.errors)
        builder.add_section("Warnings", stats.warnings)
        builder.add_section("Skipped", stats.skipped_details)
        builder.add_section("Ignored", filtered_ignored_details(stats))
    else:
        builder.add_section(
            "Errors",
            summarize_counts(stats.errors_by_sport, len(stats.errors), "error"),
        )
        builder.add_section(
            "Warnings",
            summarize_counts(stats.warnings_by_sport, len(stats.warnings), "warning"),
        )
        builder.add_section(
            "Skipped",
            summarize_messages(stats.skipped_details),
        )
        builder.add_section(
            "Ignored",
            summarize_counts(stats.ignored_by_sport, stats.ignored, "ignored"),
        )

    # Always show Plex sync errors (they're important to surface)
    if plex_sync_stats and plex_sync_stats.errors:
        builder.add_section(
            "Plex Sync Errors",
            summarize_plex_errors(plex_sync_stats.errors),
        )

    LOGGER.log(level, builder.render())


def log_run_recap(
    stats: ProcessingStats,
    duration: float,
    *,
    touched_destinations: list[str],
    plex_sync_enabled: bool,
    plex_sync_ran: bool = False,
    plex_sync_stats: PlexSyncStats | None = None,
    plex_sync_dry_run: bool = False,
    global_dry_run: bool = False,
    kometa_enabled: bool = False,
    kometa_fired: bool = False,
) -> None:
    """Log run recap with duration, stats, and follow-up actions.

    Shows overall processing summary including duration, file counts, Plex sync
    status, Kometa trigger status, sample destinations, and any recommended
    follow-up actions based on errors encountered.

    Args:
        stats: Processing statistics.
        duration: Total processing duration in seconds.
        touched_destinations: Sorted list of destination paths that were touched.
        plex_sync_enabled: Whether Plex sync is configured/enabled.
        plex_sync_ran: Whether Plex sync actually ran.
        plex_sync_stats: Optional Plex sync statistics.
        plex_sync_dry_run: Whether Plex sync is in dry-run mode.
        global_dry_run: Whether global dry-run mode is enabled.
        kometa_enabled: Whether Kometa trigger is enabled.
        kometa_fired: Whether Kometa trigger actually fired.
    """
    destinations = sorted(touched_destinations)
    builder = LogBlockBuilder("Run Recap")

    fields: dict[str, object] = {
        "Duration": f"{duration:.2f}s",
        "Processed": stats.processed,
        "Skipped": stats.skipped,
        "Ignored": stats.ignored,
        "Warnings": len(stats.warnings),
        "Errors": len(stats.errors),
        "Destinations": len(destinations),
    }

    # Add Plex sync status
    if plex_sync_enabled:
        if plex_sync_ran and plex_sync_stats:
            plex_summary = plex_sync_stats.summary()
            plex_status = (
                f"{plex_summary['shows']['updated']}/{plex_summary['seasons']['updated']}/"
                f"{plex_summary['episodes']['updated']} (show/season/ep)"
            )
            # Only show actual errors (not "not found" - that's normal)
            if plex_sync_stats.errors:
                plex_status += f" [{len(plex_sync_stats.errors)} errors]"
            fields["Plex Sync"] = plex_status
        elif plex_sync_dry_run or global_dry_run:
            fields["Plex Sync"] = "dry-run"
        else:
            fields["Plex Sync"] = "skipped (no changes)"
    else:
        fields["Plex Sync"] = "disabled"

    # Keep Kometa status for backwards compatibility (may be removed)
    if kometa_enabled:
        fields["Kometa Triggered"] = "yes" if kometa_fired else "no"

    builder.add_fields(fields)
    builder.add_section(
        "Destinations (sample)",
        destinations[:5],
        empty_label="(none)",
    )

    # Show Plex sync errors in detail
    if plex_sync_stats and plex_sync_stats.errors:
        builder.add_section(
            "Plex Sync Errors",
            summarize_plex_errors(plex_sync_stats.errors, limit=5),
        )

    follow_ups: list[str] = []
    if stats.errors:
        follow_ups.append("Resolve processing errors above before next run.")
    if plex_sync_stats and plex_sync_stats.errors:
        follow_ups.append(f"Check Plex library and metadata YAML for {len(plex_sync_stats.errors)} sync error(s).")

    if follow_ups:
        builder.add_section("Follow-Ups", follow_ups)

    LOGGER.info(builder.render())


# Functions still to be extracted from processor.py:
# - format_log() (from _format_log)
# - format_inline_log() (from _format_inline_log)
