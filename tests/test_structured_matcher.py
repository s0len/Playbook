"""Tests for structured filename matching, particularly for NBA games."""

from __future__ import annotations

import datetime as dt

import pytest

from playbook.parsers.structured_filename import StructuredName, _parse_date_candidates
from playbook.matcher import (
    _build_team_alias_lookup,
    _extract_teams_from_text,
    _score_structured_match,
)
from playbook.models import Episode, Season, Show
from playbook.team_aliases import get_team_alias_map


class TestNBATrailingDateParsing:
    """Tests for parsing trailing DD MM dates from NBA filenames."""

    def test_trailing_date_22_12_parses_as_december_22(self) -> None:
        """Verify '22 12' at end of filename parses as December 22."""
        text = "NBA RS 2025 Indiana Pacers vs Boston Celtics 22 12"
        parsed_date, year = _parse_date_candidates(text)

        assert year == 2025
        assert parsed_date == dt.date(2025, 12, 22), (
            f"Expected 2025-12-22, got {parsed_date}. "
            "Trailing '22 12' should parse as day=22, month=12."
        )

    def test_trailing_date_with_quality_suffix(self) -> None:
        """Verify trailing date parsing works with quality suffixes."""
        text = "NBA RS 2025 Utah Jazz vs Denver Nuggets 22 12 720p"
        parsed_date, year = _parse_date_candidates(text)

        assert year == 2025
        assert parsed_date == dt.date(2025, 12, 22)

    def test_trailing_date_with_fps_suffix(self) -> None:
        """Verify trailing date parsing works with FPS suffixes."""
        text = "NBA RS 2025 Orlando Magic vs Golden State Warriors 22 12 60fps"
        parsed_date, year = _parse_date_candidates(text)

        assert year == 2025
        assert parsed_date == dt.date(2025, 12, 22)

    def test_trailing_date_with_language_suffix(self) -> None:
        """Verify trailing date parsing works with language code suffixes."""
        text = "NBA RS 2025 Phoenix Suns vs Dallas Mavericks 15 01 EN"
        parsed_date, year = _parse_date_candidates(text)

        assert year == 2025
        assert parsed_date == dt.date(2025, 1, 15)

    def test_trailing_date_01_12_parses_as_december_1(self) -> None:
        """Verify single-digit day parsing works."""
        text = "NBA RS 2025 Los Angeles Lakers vs Chicago Bulls 01 12"
        parsed_date, year = _parse_date_candidates(text)

        assert year == 2025
        assert parsed_date == dt.date(2025, 12, 1)

    def test_trailing_date_with_separator_underscores(self) -> None:
        """Verify date parsing works with underscores as separators."""
        text = "NBA_RS_2025_Boston_Celtics_vs_Miami_Heat_22_12"
        parsed_date, year = _parse_date_candidates(text)

        assert year == 2025
        assert parsed_date == dt.date(2025, 12, 22)

    def test_invalid_month_returns_none(self) -> None:
        """Verify invalid month (13+) does not produce a date."""
        text = "NBA RS 2025 Team A vs Team B 22 15"
        parsed_date, year = _parse_date_candidates(text)

        assert year == 2025
        assert parsed_date is None, "Month 15 is invalid and should not produce a date"

    def test_invalid_day_returns_none(self) -> None:
        """Verify invalid day (32+) does not produce a date."""
        text = "NBA RS 2025 Team A vs Team B 32 12"
        parsed_date, year = _parse_date_candidates(text)

        assert year == 2025
        assert parsed_date is None, "Day 32 is invalid and should not produce a date"


class TestNBAStructuredMatching:
    """Tests for NBA structured filename matching to episodes."""

    def _create_nba_show_with_episodes(
        self, episodes: list[tuple[str, dt.date]]
    ) -> tuple[Show, Season]:
        """Helper to create a show with the specified episodes."""
        episode_list = [
            Episode(
                title=title,
                summary=None,
                originally_available=date,
                index=idx + 1,
            )
            for idx, (title, date) in enumerate(episodes)
        ]

        season = Season(
            key="week9",
            title="Week 9",
            summary=None,
            index=9,
            episodes=episode_list,
        )

        show = Show(
            key="nba",
            title="NBA",
            summary=None,
            seasons=[season],
        )

        return show, season

    def test_pacers_vs_celtics_matches_correct_episode(self) -> None:
        """Verify Pacers vs Celtics file matches the correct episode, not Celtics vs Heat."""
        show, season = self._create_nba_show_with_episodes([
            ("Boston Celtics vs Miami Heat", dt.date(2024, 12, 22)),
            ("Indiana Pacers vs Boston Celtics", dt.date(2024, 12, 22)),
        ])

        alias_lookup = _build_team_alias_lookup(show, get_team_alias_map("nba"))

        # File for Pacers vs Celtics
        structured = StructuredName(
            raw="NBA RS 2024 Indiana Pacers vs Boston Celtics 22 12",
            date=dt.date(2024, 12, 22),
            teams=["Indiana Pacers", "Boston Celtics"],
        )

        # Should NOT match Celtics vs Heat (only one team overlaps)
        celtics_heat = season.episodes[0]
        score_wrong = _score_structured_match(structured, season, celtics_heat, alias_lookup)
        assert score_wrong == 0.0, (
            f"Expected 0.0 for wrong episode (Celtics vs Heat), got {score_wrong}. "
            "Only 'Celtics' overlaps - should not match."
        )

        # Should match Pacers vs Celtics (both teams match)
        pacers_celtics = season.episodes[1]
        score_correct = _score_structured_match(structured, season, pacers_celtics, alias_lookup)
        assert score_correct > 0.0, (
            f"Expected positive score for correct episode, got {score_correct}. "
            "Both teams match - should match."
        )

    def test_jazz_vs_nuggets_matches_correct_episode(self) -> None:
        """Verify Jazz vs Nuggets file matches correctly."""
        show, season = self._create_nba_show_with_episodes([
            ("Utah Jazz vs Denver Nuggets", dt.date(2024, 12, 22)),
            ("Denver Nuggets vs Los Angeles Lakers", dt.date(2024, 12, 22)),
        ])

        alias_lookup = _build_team_alias_lookup(show, get_team_alias_map("nba"))

        structured = StructuredName(
            raw="NBA RS 2024 Utah Jazz vs Denver Nuggets 22 12",
            date=dt.date(2024, 12, 22),
            teams=["Utah Jazz", "Denver Nuggets"],
        )

        # Should match Jazz vs Nuggets
        jazz_nuggets = season.episodes[0]
        score_correct = _score_structured_match(structured, season, jazz_nuggets, alias_lookup)
        assert score_correct > 0.0

        # Should NOT match Nuggets vs Lakers (only one team overlaps)
        nuggets_lakers = season.episodes[1]
        score_wrong = _score_structured_match(structured, season, nuggets_lakers, alias_lookup)
        assert score_wrong == 0.0

    def test_magic_vs_warriors_matches_correct_episode(self) -> None:
        """Verify Magic vs Warriors file matches correctly."""
        show, season = self._create_nba_show_with_episodes([
            ("Orlando Magic vs Golden State Warriors", dt.date(2024, 12, 22)),
            ("Golden State Warriors vs Phoenix Suns", dt.date(2024, 12, 22)),
        ])

        alias_lookup = _build_team_alias_lookup(show, get_team_alias_map("nba"))

        structured = StructuredName(
            raw="NBA RS 2024 Orlando Magic vs Golden State Warriors 22 12",
            date=dt.date(2024, 12, 22),
            teams=["Orlando Magic", "Golden State Warriors"],
        )

        # Should match Magic vs Warriors
        magic_warriors = season.episodes[0]
        score_correct = _score_structured_match(structured, season, magic_warriors, alias_lookup)
        assert score_correct > 0.0

        # Should NOT match Warriors vs Suns
        warriors_suns = season.episodes[1]
        score_wrong = _score_structured_match(structured, season, warriors_suns, alias_lookup)
        assert score_wrong == 0.0

    def test_date_mismatch_returns_zero(self) -> None:
        """Verify that date mismatch returns zero score even if teams match."""
        show, season = self._create_nba_show_with_episodes([
            ("Boston Celtics vs Miami Heat", dt.date(2024, 12, 20)),  # Different date
        ])

        alias_lookup = _build_team_alias_lookup(show, get_team_alias_map("nba"))

        structured = StructuredName(
            raw="NBA RS 2024 Boston Celtics vs Miami Heat 25 12",  # Dec 25
            date=dt.date(2024, 12, 25),
            teams=["Boston Celtics", "Miami Heat"],
        )

        episode = season.episodes[0]
        score = _score_structured_match(structured, season, episode, alias_lookup)

        assert score == 0.0, (
            f"Expected 0.0 for date mismatch (Dec 25 vs Dec 20), got {score}. "
            "Dates more than 2 days apart should not match."
        )

    def test_date_within_tolerance_matches(self) -> None:
        """Verify that dates within 2-day tolerance still match."""
        show, season = self._create_nba_show_with_episodes([
            ("Boston Celtics vs Miami Heat", dt.date(2024, 12, 22)),
        ])

        alias_lookup = _build_team_alias_lookup(show, get_team_alias_map("nba"))

        # Date is 1 day off (Dec 21 vs Dec 22)
        structured = StructuredName(
            raw="NBA RS 2024 Boston Celtics vs Miami Heat 21 12",
            date=dt.date(2024, 12, 21),
            teams=["Boston Celtics", "Miami Heat"],
        )

        episode = season.episodes[0]
        score = _score_structured_match(structured, season, episode, alias_lookup)

        assert score > 0.0, (
            "Dates within 2-day tolerance should match. "
            f"Dec 21 vs Dec 22 (1 day difference) got score {score}"
        )

    def test_same_teams_different_dates_disambiguate(self) -> None:
        """Verify that same teams playing on different dates match to correct episode."""
        show, season = self._create_nba_show_with_episodes([
            ("Boston Celtics vs Miami Heat", dt.date(2024, 12, 15)),  # First game
            ("Boston Celtics vs Miami Heat", dt.date(2024, 12, 22)),  # Rematch
        ])

        alias_lookup = _build_team_alias_lookup(show, get_team_alias_map("nba"))

        # File for December 22 game
        structured = StructuredName(
            raw="NBA RS 2024 Boston Celtics vs Miami Heat 22 12",
            date=dt.date(2024, 12, 22),
            teams=["Boston Celtics", "Miami Heat"],
        )

        # First game (Dec 15) should not match
        first_game = season.episodes[0]
        score_first = _score_structured_match(structured, season, first_game, alias_lookup)
        assert score_first == 0.0, "Dec 22 file should not match Dec 15 episode"

        # Second game (Dec 22) should match
        second_game = season.episodes[1]
        score_second = _score_structured_match(structured, season, second_game, alias_lookup)
        assert score_second > 0.0, "Dec 22 file should match Dec 22 episode"


class TestNBATeamAliasResolution:
    """Tests for NBA team alias resolution in structured matching."""

    def test_nickname_resolves_in_matching(self) -> None:
        """Verify team nicknames resolve correctly during matching."""
        show, season = TestNBAStructuredMatching()._create_nba_show_with_episodes([
            ("Boston Celtics vs Miami Heat", dt.date(2024, 12, 22)),
        ])

        alias_lookup = _build_team_alias_lookup(show, get_team_alias_map("nba"))

        # File uses nicknames
        structured = StructuredName(
            raw="NBA RS 2024 Celtics vs Heat 22 12",
            date=dt.date(2024, 12, 22),
            teams=["Celtics", "Heat"],
        )

        episode = season.episodes[0]
        score = _score_structured_match(structured, season, episode, alias_lookup)

        assert score > 0.0, (
            f"Nicknames 'Celtics vs Heat' should match 'Boston Celtics vs Miami Heat'. "
            f"Got score {score}"
        )

    def test_abbreviation_resolves_in_matching(self) -> None:
        """Verify team abbreviations resolve correctly during matching."""
        show, season = TestNBAStructuredMatching()._create_nba_show_with_episodes([
            ("Los Angeles Lakers vs Chicago Bulls", dt.date(2024, 12, 22)),
        ])

        alias_lookup = _build_team_alias_lookup(show, get_team_alias_map("nba"))

        # File uses abbreviations
        structured = StructuredName(
            raw="NBA RS 2024 LAL vs CHI 22 12",
            date=dt.date(2024, 12, 22),
            teams=["LAL", "CHI"],
        )

        episode = season.episodes[0]
        score = _score_structured_match(structured, season, episode, alias_lookup)

        assert score > 0.0, (
            f"Abbreviations 'LAL vs CHI' should match 'Los Angeles Lakers vs Chicago Bulls'. "
            f"Got score {score}"
        )

    def test_city_names_resolve_in_matching(self) -> None:
        """Verify city names resolve correctly during matching."""
        show, season = TestNBAStructuredMatching()._create_nba_show_with_episodes([
            ("Denver Nuggets vs Phoenix Suns", dt.date(2024, 12, 22)),
        ])

        alias_lookup = _build_team_alias_lookup(show, get_team_alias_map("nba"))

        # File uses city names
        structured = StructuredName(
            raw="NBA RS 2024 Denver vs Phoenix 22 12",
            date=dt.date(2024, 12, 22),
            teams=["Denver", "Phoenix"],
        )

        episode = season.episodes[0]
        score = _score_structured_match(structured, season, episode, alias_lookup)

        assert score > 0.0, (
            f"City names 'Denver vs Phoenix' should match 'Denver Nuggets vs Phoenix Suns'. "
            f"Got score {score}"
        )


class TestExtractTeamsFromText:
    """Tests for _extract_teams_from_text helper function."""

    def test_extracts_teams_from_vs_format(self) -> None:
        """Verify teams are extracted from 'Team A vs Team B' format."""
        alias_lookup = get_team_alias_map("nba")
        teams = _extract_teams_from_text("Boston Celtics vs Miami Heat", alias_lookup)

        assert len(teams) == 2
        assert "Boston Celtics" in teams
        assert "Miami Heat" in teams

    def test_extracts_teams_from_at_format(self) -> None:
        """Verify teams are extracted from 'Team A at Team B' format."""
        alias_lookup = get_team_alias_map("nba")
        teams = _extract_teams_from_text("Boston Celtics at Miami Heat", alias_lookup)

        assert len(teams) == 2
        assert "Boston Celtics" in teams
        assert "Miami Heat" in teams

    def test_resolves_nicknames_to_canonical(self) -> None:
        """Verify nicknames are resolved to canonical team names."""
        alias_lookup = get_team_alias_map("nba")
        teams = _extract_teams_from_text("Celtics vs Heat", alias_lookup)

        assert len(teams) == 2
        assert "Boston Celtics" in teams
        assert "Miami Heat" in teams
from playbook.config import DestinationTemplates, MetadataConfig, SportConfig
from playbook.matcher import match_file_to_episode
from playbook.models import Episode, Season, Show


def _sport(sport_id: str, *, alias_map: str | None = None) -> SportConfig:
    return SportConfig(
        id=sport_id,
        name=sport_id,
        metadata=MetadataConfig(url="https://example.com"),
        patterns=[],
        team_alias_map=alias_map,
        destination=DestinationTemplates(),
    )


def _episode(title: str, when: dt.date, aliases: list[str] | None = None, index: int = 1) -> Episode:
    return Episode(
        title=title,
        summary=None,
        originally_available=when,
        index=index,
        metadata={},
        display_number=index,
        aliases=aliases or [],
    )


def _season(key: str, title: str, episodes: list[Episode]) -> Season:
    return Season(
        key=key,
        title=title,
        summary=None,
        index=1,
        episodes=episodes,
        sort_title=None,
        display_number=1,
        round_number=None,
        metadata={},
    )


def _show(title: str, seasons: list[Season]) -> Show:
    return Show(key=title.lower().replace(" ", "_"), title=title, summary=None, seasons=seasons, metadata={})


def test_structured_match_premier_league_date_and_aliases() -> None:
    sport = _sport("premier_league", alias_map="premier_league")
    season = _season(
        "mw14",
        "Matchweek 14",
        [
            _episode(
                "Liverpool vs Sunderland",
                dt.date(2025, 12, 3),
                aliases=["Liverpool v Sunderland", "Liverpool versus Sunderland"],
                index=1,
            )
        ],
    )
    show = _show("Premier League 2025-26", [season])

    filename = "EPL 2025 12 03 Liverpool vs Sunderland 2160p50 x264 EN SKY.mkv"
    result = match_file_to_episode(filename, sport, show, patterns=[])
    assert result is not None
    assert result["episode"].title == "Liverpool vs Sunderland"
    assert result["season"].title == "Matchweek 14"


def test_structured_match_nhl_abbreviations() -> None:
    sport = _sport("nhl", alias_map="nhl")
    season = _season(
        "nhl-week-7",
        "Week 7",
        [
            _episode(
                "New Jersey Devils vs Philadelphia Flyers",
                dt.date(2025, 11, 22),
                aliases=["NJD vs PHI", "Devils vs Flyers"],
                index=1,
            )
        ],
    )
    show = _show("NHL 2025-26", [season])

    filename = "NHL-2025-11-22_NJD@PHI.mkv"
    result = match_file_to_episode(filename, sport, show, patterns=[])
    assert result is not None
    assert result["episode"].title == "New Jersey Devils vs Philadelphia Flyers"


def test_structured_match_with_provider_plus_and_trailing_date_tokens() -> None:
    sport = _sport("nhl", alias_map="nhl")
    season = _season(
        "nhl-week-12",
        "Week 12",
        [
            _episode(
                "Chicago Blackhawks vs Los Angeles Kings",
                dt.date(2025, 12, 4),
                aliases=["CHI vs LAK"],
                index=1,
            )
        ],
    )
    show = _show("NHL 2025-26", [season])

    filename = "NHL RS 2025 Chicago Blackhawks vs Los Angeles Kings 04 12 720pEN60fps ESPN+.mkv"
    result = match_file_to_episode(filename, sport, show, patterns=[])
    assert result is not None
    assert result["episode"].title == "Chicago Blackhawks vs Los Angeles Kings"

