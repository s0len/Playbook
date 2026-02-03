"""Config persistence utilities for the Playbook GUI.

Handles saving configuration changes back to the YAML file.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

import yaml

LOGGER = logging.getLogger(__name__)


def save_sport_source_globs(
    config_path: Path,
    sport_id: str,
    extra_source_globs: list[str],
    disabled_source_globs: list[str],
) -> None:
    """Save source glob changes for a sport to the config file.

    This function:
    1. Creates a backup of the config file
    2. Loads the YAML preserving structure
    3. Updates the sport's extra_source_globs and disabled_source_globs
    4. Removes the legacy source_globs field if present (migration to new format)
    5. Saves the updated config

    Args:
        config_path: Path to the config YAML file
        sport_id: The sport identifier to update
        extra_source_globs: List of custom user-added globs
        disabled_source_globs: List of disabled glob patterns
    """
    # Create backup
    backup_path = config_path.parent / f"{config_path.stem}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    shutil.copy2(config_path, backup_path)
    LOGGER.info("Created backup at %s", backup_path)

    # Load config preserving comments and structure as much as possible
    with open(config_path) as f:
        content = f.read()

    # Parse YAML
    data = yaml.safe_load(content)

    # Find and update the sport
    sports = data.get("sports", [])
    sport_found = False

    for sport in sports:
        if sport.get("id") == sport_id:
            sport_found = True

            # Remove legacy source_globs field if it exists (migration to new format)
            if "source_globs" in sport:
                del sport["source_globs"]

            # Update the new fields
            if extra_source_globs:
                sport["extra_source_globs"] = extra_source_globs
            elif "extra_source_globs" in sport:
                del sport["extra_source_globs"]

            if disabled_source_globs:
                sport["disabled_source_globs"] = disabled_source_globs
            elif "disabled_source_globs" in sport:
                del sport["disabled_source_globs"]

            break

    if not sport_found:
        raise ValueError(f"Sport '{sport_id}' not found in config")

    # Write updated config
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    LOGGER.info("Saved source glob changes for sport %s", sport_id)
