from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(slots=True)
class StructuredName:
    """Represents a parsed structured filename with extracted components."""

    raw: str
    date: Optional[dt.date] = None
    teams: List[str] = field(default_factory=list)
    sport: Optional[str] = None
    season_type: Optional[str] = None
    year: Optional[int] = None


def _parse_date_candidates(text: str) -> Tuple[Optional[dt.date], Optional[int]]:
    """Parse date candidates from structured filename text.

    Handles various date formats including:
    - Standalone 4-digit year (e.g., "2025" in "NBA RS 2025 Team A vs Team B")
    - Trailing DD MM format after team names (e.g., "22 12" at end of filename)
    - Combined DD MM with standalone year (e.g., "2025 ... 22 12" -> 2025-12-22)

    Args:
        text: The filename text to parse

    Returns:
        Tuple of (parsed_date, year) where either may be None if not found
    """
    # Normalize separators - replace common separators with spaces for easier parsing
    normalized = re.sub(r"[._-]+", " ", text)

    # Extract standalone 4-digit year (typically appears after sport code)
    # Pattern: 4 digits that look like a year (1900-2099)
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", normalized)
    standalone_year: Optional[int] = None
    if year_match:
        standalone_year = int(year_match.group(1))

    parsed_date: Optional[dt.date] = None

    # Try to find trailing DD MM pattern (appears after team names, before quality tags)
    # Examples: "Team A vs Team B 22 12 720pEN60fps" -> day=22, month=12
    # Match pattern: space + 1-2 digits + space + 1-2 digits + (space or end or quality tag)
    # The pattern should NOT match resolution/quality codes like "720p" or "60fps"
    trailing_date_pattern = re.search(
        r"\s+(?P<d>\d{1,2})\s+(?P<m>\d{1,2})(?:\s+\d{3,4}p|\s+\d{2,3}fps|\s+[A-Z]{2,}|\s*$)",
        normalized,
    )

    if trailing_date_pattern and standalone_year:
        day_str = trailing_date_pattern.group("d")
        month_str = trailing_date_pattern.group("m")
        try:
            day = int(day_str)
            month = int(month_str)
            # Validate reasonable day/month values
            if 1 <= day <= 31 and 1 <= month <= 12:
                try:
                    parsed_date = dt.date(standalone_year, month, day)
                except ValueError:
                    # Invalid date combination (e.g., Feb 30)
                    pass
        except ValueError:
            pass

    # Also try DD-MM or DD.MM or DD/MM format with standalone year
    if parsed_date is None and standalone_year:
        fragment_match = re.search(
            r"(?P<d>\d{1,2})[.\-/\s](?P<m>\d{1,2})(?!\d)",
            normalized,
        )
        if fragment_match:
            # Skip if this looks like the year we already found
            full_match = fragment_match.group(0)
            if str(standalone_year) not in full_match:
                day_str = fragment_match.group("d")
                month_str = fragment_match.group("m")
                try:
                    day = int(day_str)
                    month = int(month_str)
                    if 1 <= day <= 31 and 1 <= month <= 12:
                        try:
                            parsed_date = dt.date(standalone_year, month, day)
                        except ValueError:
                            pass
                except ValueError:
                    pass

    return parsed_date, standalone_year
