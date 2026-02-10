"""Date parsing and proximity utilities.

This module provides functions for parsing dates from match groups and
checking if dates are within a specified proximity tolerance.
"""

from __future__ import annotations

import datetime as dt


def dates_within_proximity(date1: dt.date | None, date2: dt.date | None, tolerance_days: int = 2) -> bool:
    """Check if two dates are within the specified tolerance (in days).

    Args:
        date1: First date (or None)
        date2: Second date (or None)
        tolerance_days: Maximum days apart to consider as "within proximity"

    Returns:
        True if both dates are None, or if they're within tolerance.
        False if only one date is available (can't verify proximity).
    """
    if date1 is None and date2 is None:
        return True
    if date1 is None or date2 is None:
        # Can't verify proximity if only one date is available
        return False
    delta = abs((date1 - date2).days)
    return delta <= tolerance_days


def parse_date_from_groups(match_groups: dict[str, str]) -> dt.date | None:
    """Extract a date from match groups (day, month, year/date_year).

    Args:
        match_groups: Dictionary of regex capture groups

    Returns:
        Parsed date or None if parsing fails
    """
    day_str = match_groups.get("day")
    month_str = match_groups.get("month")
    year_str = match_groups.get("date_year") or match_groups.get("year")

    if not (day_str and month_str and year_str):
        return None

    try:
        day = int(day_str)
        month = int(month_str)
        year = int(year_str)
        return dt.date(year, month, day)
    except (ValueError, TypeError):
        return None


# Supported date formats for full dates
DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y.%m.%d",
    "%Y/%m/%d",
    "%Y %m %d",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%d %m %Y",
)

# Partial date formats (DD MM without year) - European format
PARTIAL_DATE_FORMATS = (
    "%d %m",
    "%d-%m",
    "%d.%m",
    "%d/%m",
    "%d_%m",
)


def parse_date_string(value: str, reference_year: int | None = None) -> dt.date | None:
    """Parse a date string into a date object.

    Args:
        value: The date string to parse (e.g., "16 11 2025" or "16 11")
        reference_year: Optional year to use for partial dates (DD MM format).
                        If not provided and the date string lacks a year, parsing will fail.

    Returns:
        A date object if parsing succeeds, None otherwise.
    """
    stripped = value.strip()
    if not stripped:
        return None

    # Try full date formats first
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(stripped, fmt).date()
        except ValueError:
            continue

    # Try partial date formats (DD MM without year) if reference_year is provided
    if reference_year is not None:
        for fmt in PARTIAL_DATE_FORMATS:
            try:
                parsed = dt.datetime.strptime(stripped, fmt)
                return dt.date(reference_year, parsed.month, parsed.day)
            except ValueError:
                continue

    return None
