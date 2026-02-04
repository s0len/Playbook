"""
Page definitions for the Playbook GUI.

Pages:
    - dashboard: Main dashboard with stats and activity feed
    - logs: Log viewer with filtering
    - config: Configuration editor with validation (legacy)
    - settings: New form-based settings page
    - sports: Sport management and pattern testing
    - unmatched: Unmatched files management and manual matching
"""

from __future__ import annotations

from . import config, dashboard, logs, settings, sports, unmatched

__all__ = [
    "dashboard",
    "logs",
    "config",
    "settings",
    "sports",
    "unmatched",
]
