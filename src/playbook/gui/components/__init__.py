"""
Reusable UI components for the Playbook GUI.

Components:
    - header: Navigation header with links to all pages
    - stats_card: Statistics display cards
    - activity_feed: Real-time activity list
    - log_viewer: Log display with filtering
    - progress_bar: Styled progress bars
    - status_chip: Status indicator chips
    - episode_row: Episode row with status
    - season_section: Collapsible season with episodes
"""

from __future__ import annotations

from .activity_feed import activity_feed, activity_item
from .episode_row import episode_detail_dialog, episode_row
from .header import header
from .log_viewer import log_viewer
from .progress_bar import mini_progress_bar, progress_bar, progress_with_counts
from .season_section import season_section, seasons_list
from .stats_card import stats_card
from .status_chip import link_mode_chip, status_chip, status_icon

__all__ = [
    # Layout
    "header",
    # Cards
    "stats_card",
    # Activity
    "activity_feed",
    "activity_item",
    # Logs
    "log_viewer",
    # Progress
    "progress_bar",
    "mini_progress_bar",
    "progress_with_counts",
    # Status
    "status_chip",
    "status_icon",
    "link_mode_chip",
    # Episodes
    "episode_row",
    "episode_detail_dialog",
    # Seasons
    "season_section",
    "seasons_list",
]
