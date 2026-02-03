"""Core matcher types and constants.

This module defines the PatternRuntime dataclass and constants used across
the matcher package. PatternRuntime holds a compiled pattern with its
pre-built session lookup index for efficient matching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import PatternConfig
from ..session_index import SessionLookupIndex

# Noise tokens to filter out during session matching
NOISE_TOKENS = (
    "f1live",
    "f1tv",
    "f1kids",
    "sky",
    "intl",
    "international",
    "proper",
    "verum",
)

# Default generic session aliases for common motorsport session terms.
# These are used as fallback mappings when patterns don't define specific aliases.
# Maps canonical session name -> list of common variations/spellings.
DEFAULT_GENERIC_SESSION_ALIASES: dict[str, list[str]] = {
    "Race": [
        "Race",
        "Main Race",
        "Main.Race",
        "Feature Race",
        "Feature.Race",
        "Main Event",
        "Main.Event",
        "Feature Event",
        "Feature.Event",
        "Grand Prix",
        "GP",
    ],
    "Practice": [
        "Practice",
        "Practice Session",
        "Practice.Session",
        "Free Practice",
        "Free.Practice",
        "FP",
        "Warmup",
        "Warm-up",
        "Warm Up",
    ],
    "Qualifying": [
        "Qualifying",
        "Quali",
        "Qualification",
        "Qualifying Session",
        "Qualifying.Session",
        "Q",
        "Q Session",
    ],
    "Sprint": [
        "Sprint",
        "Sprint Race",
        "Sprint.Race",
        "Sprint Qualifying",
        "Sprint.Qualifying",
        "SQ",
    ],
}


@dataclass
class PatternRuntime:
    """Runtime representation of a compiled pattern with session lookup index.

    Attributes:
        config: The pattern configuration from YAML
        regex: The compiled regular expression
        session_lookup: Pre-built session lookup index for this pattern/season
    """

    config: PatternConfig
    regex: re.Pattern[str]
    session_lookup: SessionLookupIndex
