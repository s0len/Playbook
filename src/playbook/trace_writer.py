"""Debug trace persistence for pattern matching diagnostics.

This module handles persisting debug traces to disk for pattern matching diagnostics.
Traces are JSON files that capture the full matching context for a source file against
a sport, enabling offline analysis of match failures and pattern tuning.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import ensure_directory, sha1_of_text

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TraceOptions:
    """Configuration for debug trace persistence.

    Attributes:
        enabled: Whether trace persistence is enabled.
        output_dir: Directory to write trace files. Defaults to cache_dir/traces if None.
    """
    enabled: bool = False
    output_dir: Optional[Path] = None


# Functions to be extracted from processor.py:
# - persist_trace() (from _persist_trace)
