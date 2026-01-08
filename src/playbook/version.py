"""Version detection from CHANGELOG.md."""

from __future__ import annotations

import re
from pathlib import Path

# Fallback version if CHANGELOG cannot be read
_FALLBACK_VERSION = "unknown"

# Pattern to match version lines like: ## [1.4.0] - 2025-12-04
_VERSION_PATTERN = re.compile(r"^## \[(\d+\.\d+\.\d+)\]")


def _find_changelog() -> Path | None:
    """Find the CHANGELOG.md file relative to the package or repo root."""
    # Try relative to this file (for installed package or dev)
    current_dir = Path(__file__).parent

    # Check various possible locations
    candidates = [
        current_dir.parent.parent / "CHANGELOG.md",  # repo root from src/playbook/
        current_dir / "CHANGELOG.md",  # same directory
        Path("/app/CHANGELOG.md"),  # Docker container path
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def get_version() -> str:
    """Get the current version from CHANGELOG.md.

    Parses the CHANGELOG.md file to find the latest released version.
    The format expected is: ## [X.Y.Z] - YYYY-MM-DD

    Returns:
        The version string (e.g., "1.4.0") or "unknown" if not found.
    """
    changelog_path = _find_changelog()
    if not changelog_path:
        return _FALLBACK_VERSION

    try:
        with open(changelog_path, encoding="utf-8") as f:
            for line in f:
                match = _VERSION_PATTERN.match(line)
                if match:
                    return match.group(1)
    except OSError:
        pass

    return _FALLBACK_VERSION


# Cache the version on module load
__version__ = get_version()
