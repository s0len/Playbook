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

from .logging_utils import render_fields_block
from .utils import ensure_directory, sha1_of_text

LOGGER = logging.getLogger(__name__)


@dataclass
class TraceOptions:
    """Configuration for debug trace persistence.

    Attributes:
        enabled: Whether trace persistence is enabled.
        output_dir: Directory to write trace files. Defaults to cache_dir/traces if None.
    """
    enabled: bool = False
    output_dir: Optional[Path] = None


def persist_trace(
    trace: Optional[Dict[str, Any]],
    trace_options: TraceOptions,
    cache_dir: Path,
) -> Optional[Path]:
    """Persist a debug trace to disk for pattern matching diagnostics.

    Args:
        trace: The trace dictionary containing match context and diagnostics.
        trace_options: Configuration for trace persistence.
        cache_dir: Cache directory path for default trace output location.

    Returns:
        Path to the written trace file, or None if trace wasn't persisted.
    """
    if not trace or not trace_options.enabled:
        return None

    output_dir = trace_options.output_dir or (cache_dir / "traces")
    ensure_directory(output_dir)

    trace_key = f"{trace.get('filename', '')}|{trace.get('sport_id', '')}"
    trace_path = output_dir / f"{sha1_of_text(trace_key)}.json"
    trace["trace_path"] = str(trace_path)

    try:
        with trace_path.open("w", encoding="utf-8") as handle:
            json.dump(trace, handle, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug(
            render_fields_block(
                "Failed To Write Trace",
                {
                    "Path": trace_path,
                    "Error": exc,
                },
                pad_top=True,
            )
        )
        return None

    LOGGER.debug(
        render_fields_block(
            "Wrote Match Trace",
            {
                "Path": trace_path,
            },
            pad_top=True,
        )
    )
    return trace_path
