"""Tests for TVSportsDB adapter module."""

from __future__ import annotations

from datetime import date

from playbook.tvsportsdb.adapter import TVSportsDBAdapter
from playbook.tvsportsdb.models import (
    EpisodeResponse,
    SeasonResponse,
    ShowResponse,
    TeamAliasResponse,
)


class TestTVSportsDBAdapter:
    """Tests for API response to Playbook model adapter."""

    def test_to_show_mapping(self) -> None:
        """Test ShowResponse maps correctly to Show model."""
        adapter = TVSportsDBAdapter()
        response = ShowResponse(
            id=1,
            slug="formula-1-2026",
            title="Formula 1 2026",
            sort_title="F1 2026",
            summary="The 2026 F1 Championship",
            url_poster="https://example.com/poster.jpg",
            url_background="https://example.com/bg.jpg",
            season_count=24,
            episode_count=144,
            seasons=[
                SeasonResponse(
                    id=10,
                    show_id=1,
                    number=1,
                    title="Australian Grand Prix",
                    sort_title="01 - Australian GP",
                ),
            ],
        )

        show = adapter.to_show(response)

        assert show.key == "formula-1-2026"
        assert show.title == "Formula 1 2026"
        assert show.summary == "The 2026 F1 Championship"
        assert len(show.seasons) == 1
        assert show.metadata["id"] == 1
        assert show.metadata["slug"] == "formula-1-2026"
        assert show.metadata["sort_title"] == "F1 2026"
        assert show.metadata["url_poster"] == "https://example.com/poster.jpg"
        assert show.metadata["url_background"] == "https://example.com/bg.jpg"
        assert show.metadata["season_count"] == 24
        assert show.metadata["episode_count"] == 144

    def test_to_season_mapping(self) -> None:
        """Test SeasonResponse maps correctly to Season model."""
        adapter = TVSportsDBAdapter()
        response = SeasonResponse(
            id=10,
            show_id=1,
            number=3,
            title="Monaco Grand Prix",
            sort_title="03 - Monaco GP",
            summary="The jewel of F1",
            url_poster="https://example.com/monaco.jpg",
            aliases=["Monaco GP", "Monte Carlo"],
            episodes=[
                EpisodeResponse(id=100, season_id=10, number=1, title="FP1"),
            ],
        )

        season = adapter.to_season(response, index=3)

        assert season.key == "3"  # String of season number
        assert season.title == "Monaco Grand Prix"
        assert season.summary == "The jewel of F1"
        assert season.index == 3
        assert season.sort_title == "03 - Monaco GP"
        assert season.display_number == 3
        assert season.round_number == 3
        assert len(season.episodes) == 1
        assert season.metadata["id"] == 10
        assert season.metadata["show_id"] == 1
        assert season.metadata["number"] == 3
        assert season.metadata["url_poster"] == "https://example.com/monaco.jpg"
        assert season.metadata["aliases"] == ["Monaco GP", "Monte Carlo"]

    def test_to_episode_mapping(self) -> None:
        """Test EpisodeResponse maps correctly to Episode model."""
        adapter = TVSportsDBAdapter()
        response = EpisodeResponse(
            id=100,
            season_id=10,
            number=1,
            title="Free Practice 1",
            summary="First practice session",
            url_poster="https://example.com/fp1.jpg",
            originally_available=date(2026, 3, 5),
            aliases=["FP1", "Practice 1", "P1"],
        )

        episode = adapter.to_episode(response, index=1)

        assert episode.title == "Free Practice 1"
        assert episode.summary == "First practice session"
        assert episode.originally_available == date(2026, 3, 5)
        assert episode.index == 1
        assert episode.display_number == 1
        assert episode.aliases == ["FP1", "Practice 1", "P1"]
        assert episode.metadata["id"] == 100
        assert episode.metadata["season_id"] == 10
        assert episode.metadata["number"] == 1
        assert episode.metadata["url_poster"] == "https://example.com/fp1.jpg"

    def test_to_episode_with_aliases(self) -> None:
        """Test that episode aliases are correctly preserved."""
        adapter = TVSportsDBAdapter()
        response = EpisodeResponse(
            id=1,
            season_id=1,
            number=6,
            title="Qualifying",
            aliases=["Quali", "Q", "Qualy", "Qualifying Session"],
        )

        episode = adapter.to_episode(response, index=6)

        assert episode.aliases == ["Quali", "Q", "Qualy", "Qualifying Session"]
        # Aliases should be a new list, not the same reference
        assert episode.aliases is not response.aliases

    def test_to_episode_without_aliases(self) -> None:
        """Test episode without aliases gets empty list."""
        adapter = TVSportsDBAdapter()
        response = EpisodeResponse(
            id=1,
            season_id=1,
            number=1,
            title="Race",
        )

        episode = adapter.to_episode(response, index=1)

        assert episode.aliases == []

    def test_to_team_alias_map(self) -> None:
        """Test team aliases convert to lookup dictionary."""
        adapter = TVSportsDBAdapter()
        aliases = [
            TeamAliasResponse(canonical_name="Los Angeles Lakers", alias="LAL", sport_slug="nba"),
            TeamAliasResponse(canonical_name="Los Angeles Lakers", alias="Lakers", sport_slug="nba"),
            TeamAliasResponse(canonical_name="Boston Celtics", alias="BOS", sport_slug="nba"),
            TeamAliasResponse(canonical_name="Boston Celtics", alias="Celtics", sport_slug="nba"),
        ]

        result = adapter.to_team_alias_map(aliases)

        assert result["lal"] == "Los Angeles Lakers"
        assert result["lakers"] == "Los Angeles Lakers"
        assert result["bos"] == "Boston Celtics"
        assert result["celtics"] == "Boston Celtics"

    def test_to_team_alias_map_lowercase_keys(self) -> None:
        """Test that alias keys are normalized to lowercase."""
        adapter = TVSportsDBAdapter()
        aliases = [
            TeamAliasResponse(canonical_name="New York Yankees", alias="NYY", sport_slug="mlb"),
            TeamAliasResponse(canonical_name="New York Yankees", alias="Yankees", sport_slug="mlb"),
            TeamAliasResponse(canonical_name="New York Yankees", alias="NY Yankees", sport_slug="mlb"),
        ]

        result = adapter.to_team_alias_map(aliases)

        # Keys should be lowercase
        assert "nyy" in result
        assert "NYY" not in result
        assert "yankees" in result
        assert "ny yankees" in result

    def test_to_team_alias_map_empty(self) -> None:
        """Test empty alias list returns empty dict."""
        adapter = TVSportsDBAdapter()
        result = adapter.to_team_alias_map([])
        assert result == {}

    def test_seasons_sorted_by_number(self) -> None:
        """Test that seasons are sorted by number in output."""
        adapter = TVSportsDBAdapter()
        response = ShowResponse(
            id=1,
            slug="test-show",
            title="Test Show",
            sort_title="Test Show",
            seasons=[
                SeasonResponse(id=3, show_id=1, number=3, title="Season 3", sort_title="S3"),
                SeasonResponse(id=1, show_id=1, number=1, title="Season 1", sort_title="S1"),
                SeasonResponse(id=2, show_id=1, number=2, title="Season 2", sort_title="S2"),
            ],
        )

        show = adapter.to_show(response)

        # Seasons should be sorted by number
        assert show.seasons[0].title == "Season 1"
        assert show.seasons[1].title == "Season 2"
        assert show.seasons[2].title == "Season 3"

        # Index should be 1-based sequential
        assert show.seasons[0].index == 1
        assert show.seasons[1].index == 2
        assert show.seasons[2].index == 3

    def test_episodes_sorted_by_number(self) -> None:
        """Test that episodes are sorted by number in output."""
        adapter = TVSportsDBAdapter()
        response = SeasonResponse(
            id=1,
            show_id=1,
            number=1,
            title="Season 1",
            sort_title="S1",
            episodes=[
                EpisodeResponse(id=5, season_id=1, number=5, title="Race"),
                EpisodeResponse(id=1, season_id=1, number=1, title="FP1"),
                EpisodeResponse(id=3, season_id=1, number=3, title="FP3"),
            ],
        )

        season = adapter.to_season(response, index=1)

        # Episodes should be sorted by number
        assert season.episodes[0].title == "FP1"
        assert season.episodes[1].title == "FP3"
        assert season.episodes[2].title == "Race"

        # Index should be 1-based sequential
        assert season.episodes[0].index == 1
        assert season.episodes[1].index == 2
        assert season.episodes[2].index == 3
