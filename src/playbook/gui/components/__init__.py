"""
Reusable UI components for the Playbook GUI.

Components:
    - header: Navigation header with links to all pages
    - stats_card: Statistics display cards
    - activity_feed: Real-time activity list
    - log_viewer: Log display with filtering
"""

from __future__ import annotations

from .activity_feed import activity_feed, activity_item
from .header import header
from .log_viewer import log_viewer
from .stats_card import stats_card

__all__ = [
    "header",
    "stats_card",
    "activity_feed",
    "activity_item",
    "log_viewer",
]
