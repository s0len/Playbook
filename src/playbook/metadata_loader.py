"""Parallel metadata loading and fingerprint tracking.

This module handles loading sport configurations and show metadata in parallel,
tracking metadata fingerprints to detect changes, and building SportRuntime
objects that contain the compiled pattern matchers for each sport.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .metadata import SportConfig, Show
from .patterns import PatternRuntime

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SportRuntime:
    """Runtime state for a loaded sport configuration.

    Holds the sport configuration, show metadata, compiled pattern matchers,
    and set of valid file extensions for this sport.
    """
    sport: SportConfig
    show: Show
    patterns: List[PatternRuntime]
    extensions: Set[str]


# Functions to be extracted from processor.py:
# - load_sports() (from _load_sports)
