"""Pydantic models for TheTVSportsDB API responses."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class EpisodeResponse(BaseModel):
    """API response model for an episode."""

    model_config = ConfigDict(extra="ignore")

    id: int
    season_id: int
    number: int
    title: str
    summary: str | None = None
    url_poster: str | None = None
    originally_available: date | None = None
    aliases: list[str] = Field(default_factory=list)


class SeasonResponse(BaseModel):
    """API response model for a season."""

    model_config = ConfigDict(extra="ignore")

    id: int
    show_id: int
    number: int
    title: str
    sort_title: str
    summary: str | None = None
    url_poster: str | None = None
    aliases: list[str] = Field(default_factory=list)
    episodes: list[EpisodeResponse] = Field(default_factory=list)


class ShowResponse(BaseModel):
    """API response model for a show."""

    model_config = ConfigDict(extra="ignore")

    id: int
    slug: str
    title: str
    sort_title: str
    summary: str | None = None
    url_poster: str | None = None
    url_background: str | None = None
    season_count: int = 0
    episode_count: int = 0
    seasons: list[SeasonResponse] = Field(default_factory=list)


class TeamAliasResponse(BaseModel):
    """API response model for a team alias."""

    model_config = ConfigDict(extra="ignore")

    canonical_name: str
    alias: str
    sport_slug: str | None = None


class PaginatedResponse[T](BaseModel):
    """Generic paginated API response wrapper."""

    model_config = ConfigDict(extra="ignore")

    items: list[T]
    total: int
    skip: int = 0
    limit: int = 100
