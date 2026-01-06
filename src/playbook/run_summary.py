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
from typing import TYPE_CHECKING, Dict, List, Optional

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
    return bool(
        stats.processed
        or stats.skipped
        or stats.ignored
        or stats.errors
        or stats.warnings
    )


def has_detailed_activity(stats: ProcessingStats) -> bool:
    """Check if processing stats have detailed activity worth logging.

    Args:
        stats: Processing statistics to check.

    Returns:
        True if there are errors, warnings, or detailed skip/ignore information.
    """
    return bool(
        stats.errors
        or stats.warnings
        or stats.skipped_details
        or stats.ignored_details
    )


def filtered_ignored_details(stats: ProcessingStats) -> List[str]:
    """Filter ignored details to suppress common non-actionable messages.

    Args:
        stats: Processing statistics containing ignored details.

    Returns:
        Filtered list of ignored details with suppression counts added.
    """
    filtered: List[str] = []
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


def summarize_counts(counts: Dict[str, int], total: int, label: str) -> List[str]:
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
    lines: List[str] = []
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


def summarize_messages(entries: List[str], *, limit: int = 5) -> List[str]:
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
    lines: List[str] = []
    for text, count in ordered[:limit]:
        prefix = f"{count}× " if count > 1 else ""
        lines.append(f"{prefix}{text}")
    remaining = len(ordered) - limit
    if remaining > 0:
        lines.append(f"... {remaining} more (use --verbose for full list)")
    else:
        lines.append("Run with --verbose for per-file details.")
    return lines


def summarize_plex_errors(errors: List[str], *, limit: int = 10) -> List[str]:
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
    grouped: Dict[str, List[str]] = {}
    for error in errors:
        # Extract error category (e.g., "Show not found", "Season not found", etc.)
        if ":" in error:
            category = error.split(":")[0].strip()
        else:
            # Use first 30 chars as category
            category = error[:30].strip()
        grouped.setdefault(category, []).append(error)

    lines: List[str] = []
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


def extract_error_context(error: str) -> Optional[str]:
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


# Functions still to be extracted from processor.py:
# - format_log() (from _format_log)
# - format_inline_log() (from _format_inline_log)
# - log_detailed_summary() (from _log_detailed_summary)
# - log_run_recap() (from _log_run_recap)
