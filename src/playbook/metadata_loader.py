"""Parallel metadata loading and fingerprint tracking.

This module handles loading sport configurations and show metadata in parallel,
tracking metadata fingerprints to detect changes, and building SportRuntime
objects that contain the compiled pattern matchers for each sport.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional

from .metadata import SportConfig, Show
from .patterns import PatternRuntime

LOGGER = logging.getLogger(__name__)


# Classes and functions to be extracted from processor.py:
# - SportRuntime (dataclass)
# - load_sports() (from _load_sports)
