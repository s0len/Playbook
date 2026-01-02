from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class StructuredName:
    """Represents a parsed structured filename with extracted components."""

    raw: str
    date: Optional[dt.date] = None
    teams: List[str] = field(default_factory=list)
    sport: Optional[str] = None
    season_type: Optional[str] = None
    year: Optional[int] = None
