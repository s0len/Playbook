"""Version detection with support for development builds."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# Fallback version if nothing else works
_FALLBACK_VERSION = "unknown"

# Pattern to match version lines like: ## [1.4.0] - 2025-12-04
_VERSION_PATTERN = re.compile(r"^## \[(\d+\.\d+\.\d+)\]")

# Pattern to match unreleased section: ## [Unreleased] or ## Unreleased
_UNRELEASED_PATTERN = re.compile(r"^## \[?Unreleased\]?", re.IGNORECASE)


def _find_changelog() -> Path | None:
    """Find the CHANGELOG.md file relative to the package or repo root."""
    current_dir = Path(__file__).parent

    candidates = [
        current_dir.parent.parent / "CHANGELOG.md",  # repo root from src/playbook/
        current_dir / "CHANGELOG.md",  # same directory
        Path("/app/CHANGELOG.md"),  # Docker container path
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def _get_git_info() -> tuple[str | None, str | None]:
    """Get Git branch and short SHA if available.

    Returns:
        Tuple of (branch_name, short_sha) or (None, None) if not in a Git repo.
    """
    try:
        # Get current branch
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        branch_name = branch.stdout.strip() if branch.returncode == 0 else None

        # Get short SHA
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        short_sha = sha.stdout.strip() if sha.returncode == 0 else None

        return branch_name, short_sha
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, None


def _get_version_from_changelog() -> tuple[str | None, bool]:
    """Get version from CHANGELOG.md.

    Returns:
        Tuple of (version, is_unreleased). Version is None if not found.
    """
    changelog_path = _find_changelog()
    if not changelog_path:
        return None, False

    try:
        with open(changelog_path, encoding="utf-8") as f:
            for line in f:
                # Check for unreleased section first
                if _UNRELEASED_PATTERN.match(line):
                    return None, True

                # Check for version
                match = _VERSION_PATTERN.match(line)
                if match:
                    return match.group(1), False
    except OSError:
        pass

    return None, False


def get_version() -> str:
    """Get the current version string.

    Priority:
    1. BUILD_VERSION environment variable (set during CI/CD)
    2. GIT_BRANCH + GIT_SHA environment variables (Docker build args)
    3. Git branch + SHA from local git repo
    4. CHANGELOG.md version for releases
    5. Fallback to "unknown"

    Returns:
        Version string like "2.0.0", "develop (abc1234)", or "unknown".
    """
    # 1. Check for explicit build version from CI/CD
    build_version = os.environ.get("BUILD_VERSION")
    if build_version:
        return build_version.strip()

    # 2. Check for Docker build args (GIT_BRANCH, GIT_SHA)
    env_branch = os.environ.get("GIT_BRANCH")
    env_sha = os.environ.get("GIT_SHA")
    if env_branch and env_sha:
        return f"{env_branch} ({env_sha})"
    if env_branch:
        return env_branch
    if env_sha:
        return f"dev ({env_sha})"

    # 3. Get CHANGELOG info
    changelog_version, is_unreleased = _get_version_from_changelog()

    # 4. Get Git info from local repo
    branch, sha = _get_git_info()

    # 5. Determine version string
    if branch and branch in ("develop", "dev", "main", "master"):
        # Development/main branch - show branch and SHA
        if sha:
            return f"{branch} ({sha})"
        return branch

    if is_unreleased and sha:
        # Unreleased section in changelog - show as dev with SHA
        return f"dev ({sha})"

    if changelog_version:
        # Release version from changelog
        return changelog_version

    if sha:
        # Fallback to just SHA if we have it
        return f"dev ({sha})"

    return _FALLBACK_VERSION


# Cache the version on module load
__version__ = get_version()
