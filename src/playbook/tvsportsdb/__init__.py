"""TVSportsDB API client package.

This package provides a client for fetching sports metadata from the
TVSportsDB REST API, replacing the previous YAML-based metadata system.
"""

from __future__ import annotations

from .adapter import TVSportsDBAdapter
from .cache import TVSportsDBCache
from .client import TVSportsDBClient
from .models import (
    EpisodeResponse,
    PaginatedResponse,
    SeasonResponse,
    ShowResponse,
    TeamAliasResponse,
)

__all__ = [
    "TVSportsDBAdapter",
    "TVSportsDBCache",
    "TVSportsDBClient",
    "EpisodeResponse",
    "PaginatedResponse",
    "SeasonResponse",
    "ShowResponse",
    "TeamAliasResponse",
]
