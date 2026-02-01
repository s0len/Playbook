"""Tests for TheTVSportsDB API response models."""

from __future__ import annotations

from datetime import date

from playbook.tvsportsdb.models import (
    EpisodeResponse,
    PaginatedResponse,
    SeasonResponse,
    ShowResponse,
    TeamAliasResponse,
)


class TestEpisodeResponse:
    """Tests for EpisodeResponse model."""

    def test_minimal_episode(self) -> None:
        """Test episode with only required fields."""
        episode = EpisodeResponse(
            id=1,
            season_id=10,
            number=1,
            title="Free Practice 1",
        )
        assert episode.id == 1
        assert episode.season_id == 10
        assert episode.number == 1
        assert episode.title == "Free Practice 1"
        assert episode.summary is None
        assert episode.url_poster is None
        assert episode.originally_available is None
        assert episode.aliases == []

    def test_full_episode(self) -> None:
        """Test episode with all fields populated."""
        episode = EpisodeResponse(
            id=1,
            season_id=10,
            number=1,
            title="Free Practice 1",
            summary="First practice session at Melbourne",
            url_poster="https://example.com/poster.jpg",
            originally_available=date(2026, 3, 5),
            aliases=["FP1", "Practice 1", "P1"],
        )
        assert episode.id == 1
        assert episode.summary == "First practice session at Melbourne"
        assert episode.url_poster == "https://example.com/poster.jpg"
        assert episode.originally_available == date(2026, 3, 5)
        assert episode.aliases == ["FP1", "Practice 1", "P1"]

    def test_episode_from_dict(self) -> None:
        """Test creating episode from API response dict."""
        data = {
            "id": 100,
            "season_id": 1,
            "number": 5,
            "title": "Qualifying",
            "aliases": ["Quali", "Q"],
            "extra_field": "ignored",  # Should be ignored due to extra="ignore"
        }
        episode = EpisodeResponse.model_validate(data)
        assert episode.id == 100
        assert episode.title == "Qualifying"
        assert episode.aliases == ["Quali", "Q"]


class TestSeasonResponse:
    """Tests for SeasonResponse model."""

    def test_minimal_season(self) -> None:
        """Test season with only required fields."""
        season = SeasonResponse(
            id=1,
            show_id=100,
            number=1,
            title="Australian Grand Prix",
            sort_title="01 - Australian Grand Prix",
        )
        assert season.id == 1
        assert season.show_id == 100
        assert season.number == 1
        assert season.title == "Australian Grand Prix"
        assert season.sort_title == "01 - Australian Grand Prix"
        assert season.summary is None
        assert season.episodes == []
        assert season.aliases == []

    def test_season_with_episodes(self) -> None:
        """Test season with nested episodes."""
        season = SeasonResponse(
            id=1,
            show_id=100,
            number=1,
            title="Australian Grand Prix",
            sort_title="01 - Australian Grand Prix",
            episodes=[
                EpisodeResponse(id=1, season_id=1, number=1, title="FP1"),
                EpisodeResponse(id=2, season_id=1, number=2, title="FP2"),
            ],
        )
        assert len(season.episodes) == 2
        assert season.episodes[0].title == "FP1"
        assert season.episodes[1].title == "FP2"

    def test_season_with_aliases(self) -> None:
        """Test season with aliases for location variations."""
        season = SeasonResponse(
            id=1,
            show_id=100,
            number=1,
            title="Australian Grand Prix",
            sort_title="01 - Australian Grand Prix",
            aliases=["Australian GP", "Melbourne", "Albert Park"],
        )
        assert season.aliases == ["Australian GP", "Melbourne", "Albert Park"]


class TestShowResponse:
    """Tests for ShowResponse model."""

    def test_minimal_show(self) -> None:
        """Test show with only required fields."""
        show = ShowResponse(
            id=1,
            slug="formula-1-2026",
            title="Formula 1 2026",
            sort_title="Formula 1 2026",
        )
        assert show.id == 1
        assert show.slug == "formula-1-2026"
        assert show.title == "Formula 1 2026"
        assert show.season_count == 0
        assert show.episode_count == 0
        assert show.seasons == []

    def test_full_show(self) -> None:
        """Test show with all fields and nested data."""
        show = ShowResponse(
            id=1,
            slug="formula-1-2026",
            title="Formula 1 2026",
            sort_title="Formula 1 2026",
            summary="The 2026 Formula 1 World Championship",
            url_poster="https://example.com/f1-poster.jpg",
            url_background="https://example.com/f1-background.jpg",
            season_count=24,
            episode_count=144,
            seasons=[
                SeasonResponse(
                    id=1,
                    show_id=1,
                    number=1,
                    title="Australian Grand Prix",
                    sort_title="01 - Australian Grand Prix",
                ),
            ],
        )
        assert show.season_count == 24
        assert show.episode_count == 144
        assert len(show.seasons) == 1
        assert show.seasons[0].title == "Australian Grand Prix"


class TestTeamAliasResponse:
    """Tests for TeamAliasResponse model."""

    def test_team_alias(self) -> None:
        """Test basic team alias."""
        alias = TeamAliasResponse(
            canonical_name="Los Angeles Lakers",
            alias="LAL",
            sport_slug="nba-2025-2026",
        )
        assert alias.canonical_name == "Los Angeles Lakers"
        assert alias.alias == "LAL"
        assert alias.sport_slug == "nba-2025-2026"

    def test_team_alias_without_sport(self) -> None:
        """Test team alias without sport slug (global alias)."""
        alias = TeamAliasResponse(
            canonical_name="New York Yankees",
            alias="Yankees",
        )
        assert alias.canonical_name == "New York Yankees"
        assert alias.alias == "Yankees"
        assert alias.sport_slug is None


class TestPaginatedResponse:
    """Tests for PaginatedResponse generic model."""

    def test_paginated_shows(self) -> None:
        """Test paginated response containing shows."""
        data = {
            "items": [
                {"id": 1, "slug": "f1-2026", "title": "F1 2026", "sort_title": "F1 2026"},
                {"id": 2, "slug": "ufc-2026", "title": "UFC 2026", "sort_title": "UFC 2026"},
            ],
            "total": 100,
            "skip": 0,
            "limit": 10,
        }
        response = PaginatedResponse[ShowResponse].model_validate(data)
        assert len(response.items) == 2
        assert response.total == 100
        assert response.skip == 0
        assert response.limit == 10
        assert response.items[0].slug == "f1-2026"

    def test_paginated_team_aliases(self) -> None:
        """Test paginated response containing team aliases."""
        data = {
            "items": [
                {"canonical_name": "Lakers", "alias": "LAL", "sport_slug": "nba"},
                {"canonical_name": "Celtics", "alias": "BOS", "sport_slug": "nba"},
            ],
            "total": 2,
            "skip": 0,
            "limit": 100,
        }
        response = PaginatedResponse[TeamAliasResponse].model_validate(data)
        assert len(response.items) == 2
        assert response.items[0].alias == "LAL"
        assert response.items[1].alias == "BOS"

    def test_empty_paginated_response(self) -> None:
        """Test empty paginated response."""
        data = {
            "items": [],
            "total": 0,
            "skip": 0,
            "limit": 100,
        }
        response = PaginatedResponse[ShowResponse].model_validate(data)
        assert response.items == []
        assert response.total == 0
