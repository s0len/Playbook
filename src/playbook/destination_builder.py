"""Destination path building from match context.

This module handles building destination file paths from match context,
including template rendering and path sanitization to ensure files are
written to safe, properly formatted locations.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

from .templating import render_template
from .utils import sanitize_component, slugify


# Functions to be extracted from processor.py:
# - build_match_context() (from _build_context)
# - build_destination() (from _build_destination)
# - format_relative_destination() (from _format_relative_destination)
