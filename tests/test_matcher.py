from __future__ import annotations

import datetime as dt
import logging
from typing import Dict, List, Tuple

import pytest

from playbook.config import (
    DestinationTemplates,
    EpisodeSelector,
    MetadataConfig,
    PatternConfig,
    SeasonSelector,
    SportConfig,
)
from playbook.matcher import (
    compile_patterns,
    match_file_to_episode,
    _build_team_alias_lookup,
    _score_structured_match,
)
from playbook.models import Episode, Season, Show
from playbook.parsers.structured_filename import StructuredName
from playbook.team_aliases import get_team_alias_map


def build_show() -> Tuple[Show, Season]:
    practice = Episode(
        title="Free Practice 1",
        summary=None,
        originally_available=None,
        index=1,
        aliases=["FP1"],
    )
    qualifying = Episode(
        title="Qualifying",
        summary=None,
        originally_available=None,
        index=2,
        aliases=["Quali"],
    )

    season = Season(
        key="2024",
        title="2024 Bahrain Grand Prix",
        summary=None,
        index=1,
        episodes=[practice, qualifying],
        display_number=1,
        round_number=1,
    )

    show = Show(key="f1", title="Formula 1", summary=None, seasons=[season])
    return show, season


def build_sport(patterns: List[PatternConfig]) -> SportConfig:
    return SportConfig(
        id="f1",
        name="Formula 1",
        metadata=MetadataConfig(url="https://example.com"),
        patterns=patterns,
        destination=DestinationTemplates(),
    )


def test_match_file_to_episode_resolves_aliases() -> None:
    pattern = PatternConfig(
        regex=r"(?i)^(?P<round>\d+)[._-]*(?P<session>[A-Z0-9]+)",
        priority=10,
    )

    sport = build_sport([pattern])
    show, season = build_show()

    patterns = compile_patterns(sport)

    diagnostics: List[Tuple[str, str]] = []
    result = match_file_to_episode("01.fp1.release.mkv", sport, show, patterns, diagnostics=diagnostics)

    assert result is not None
    assert result["season"] is season
    assert result["episode"].title == "Free Practice 1"
    assert result["pattern"] is pattern
    assert diagnostics == []


def test_match_file_to_episode_warns_when_season_missing() -> None:
    pattern = PatternConfig(
        regex=r"(?i)^(?P<round>\d+)[._-]*(?P<session>[A-Z0-9]+)",
        season_selector=SeasonSelector(mode="round", group="round"),
        priority=10,
    )

    sport = build_sport([pattern])
    show, _ = build_show()

    patterns = compile_patterns(sport)

    diagnostics: List[Tuple[str, str]] = []
    result = match_file_to_episode("99.fp1.release.mkv", sport, show, patterns, diagnostics=diagnostics)

    assert result is None
    assert diagnostics
    severity, message = diagnostics[0]
    assert severity == "warning"
    assert "season not resolved" in message


def test_match_file_to_episode_suppresses_warnings_when_requested(caplog) -> None:
    pattern = PatternConfig(
        regex=r"(?i)^(?P<round>\d+)[._-]*(?P<session>[A-Z0-9]+)",
        season_selector=SeasonSelector(mode="round", group="round"),
        priority=10,
    )

    sport = build_sport([pattern])
    show, _ = build_show()

    patterns = compile_patterns(sport)

    diagnostics: List[Tuple[str, str]] = []
    caplog.set_level(logging.WARNING, logger="playbook.matcher")
    result = match_file_to_episode(
        "99.fp1.release.mkv",
        sport,
        show,
        patterns,
        diagnostics=diagnostics,
        suppress_warnings=True,
    )

    assert result is None
    assert diagnostics
    severity, _ = diagnostics[0]
    assert severity == "ignored"
    assert not any(record.levelno >= logging.WARNING for record in caplog.records)


def test_match_file_to_episode_includes_trace_details() -> None:
    pattern = PatternConfig(
        regex=r"(?i)^(?P<round>\d+)[._-]*(?P<session>[A-Za-z]+)",
        season_selector=SeasonSelector(mode="round", group="round"),
        priority=10,
    )

    sport = build_sport([pattern])
    show, season = build_show()

    patterns = compile_patterns(sport)

    trace: Dict[str, object] = {}
    result = match_file_to_episode(
        "01.qualifying.mkv",
        sport,
        show,
        patterns,
        diagnostics=None,
        trace=trace,
    )

    assert result is not None
    assert trace["status"] == "matched"
    attempts = trace["attempts"]
    assert attempts
    matched_attempt = next(item for item in attempts if item["status"] == "matched")
    assert matched_attempt["season"]["title"] == season.title
    assert matched_attempt["episode"]["title"] == "Qualifying"
    assert trace["messages"] == []


def test_score_rejects_wrong_away_team() -> None:
    """Verify that partial team overlap (one team matches, one doesn't) returns 0.0.

    This tests the fix for the NBA matching bug where 'Pacers vs Celtics' could
    incorrectly match 'Celtics vs Heat' because 'Celtics' overlaps.
    """
    # Create an episode for Celtics vs Heat
    episode = Episode(
        title="Boston Celtics vs Miami Heat",
        summary=None,
        originally_available=dt.date(2024, 12, 22),
        index=1,
    )

    season = Season(
        key="week9",
        title="Week 9",
        summary=None,
        index=9,
        episodes=[episode],
    )

    show = Show(
        key="nba",
        title="NBA",
        summary=None,
        seasons=[season],
    )

    # Build alias lookup for the show
    alias_lookup = _build_team_alias_lookup(show, {})

    # Create structured filename for Pacers vs Celtics (wrong match - only one team overlaps)
    structured = StructuredName(
        raw="NBA RS 2024 Indiana Pacers vs Boston Celtics 22 12",
        date=dt.date(2024, 12, 22),
        teams=["Indiana Pacers", "Boston Celtics"],
    )

    # Score should be 0.0 because only one team matches
    score = _score_structured_match(structured, season, episode, alias_lookup)

    assert score == 0.0, (
        f"Expected 0.0 for partial team overlap, got {score}. "
        "Filename has 'Pacers vs Celtics' but episode is 'Celtics vs Heat' - "
        "only 'Celtics' overlaps, so it should not match."
    )


class TestNBATeamAliases:
    """Tests to verify NBA team alias mapping is complete and correct."""

    # All 30 NBA teams
    NBA_TEAMS = [
        "Atlanta Hawks",
        "Boston Celtics",
        "Brooklyn Nets",
        "Charlotte Hornets",
        "Chicago Bulls",
        "Cleveland Cavaliers",
        "Dallas Mavericks",
        "Denver Nuggets",
        "Detroit Pistons",
        "Golden State Warriors",
        "Houston Rockets",
        "Indiana Pacers",
        "Los Angeles Clippers",
        "Los Angeles Lakers",
        "Memphis Grizzlies",
        "Miami Heat",
        "Milwaukee Bucks",
        "Minnesota Timberwolves",
        "New Orleans Pelicans",
        "New York Knicks",
        "Oklahoma City Thunder",
        "Orlando Magic",
        "Philadelphia 76ers",
        "Phoenix Suns",
        "Portland Trail Blazers",
        "Sacramento Kings",
        "San Antonio Spurs",
        "Toronto Raptors",
        "Utah Jazz",
        "Washington Wizards",
    ]

    def test_all_30_teams_have_aliases(self) -> None:
        """Verify all 30 NBA teams are present in the alias map."""
        alias_map = get_team_alias_map("nba")

        # Get all unique canonical team names from the alias map
        canonical_teams = set(alias_map.values())

        assert len(canonical_teams) == 30, (
            f"Expected 30 NBA teams in alias map, got {len(canonical_teams)}"
        )

        # Verify each team is present
        for team in self.NBA_TEAMS:
            assert team in canonical_teams, f"Team '{team}' not found in NBA alias map"

    def test_common_abbreviations_resolve(self) -> None:
        """Verify common 3-letter abbreviations resolve to correct teams."""
        alias_map = get_team_alias_map("nba")

        abbreviation_mappings = {
            "bos": "Boston Celtics",
            "lal": "Los Angeles Lakers",
            "lac": "Los Angeles Clippers",
            "gsw": "Golden State Warriors",
            "nyk": "New York Knicks",
            "chi": "Chicago Bulls",
            "mia": "Miami Heat",
            "okc": "Oklahoma City Thunder",
        }

        for abbr, expected_team in abbreviation_mappings.items():
            assert alias_map.get(abbr) == expected_team, (
                f"Abbreviation '{abbr}' should resolve to '{expected_team}', "
                f"got '{alias_map.get(abbr)}'"
            )

    def test_nicknames_resolve(self) -> None:
        """Verify team nicknames resolve to correct full names."""
        alias_map = get_team_alias_map("nba")

        nickname_mappings = {
            "celtics": "Boston Celtics",
            "lakers": "Los Angeles Lakers",
            "heat": "Miami Heat",
            "warriors": "Golden State Warriors",
            "bulls": "Chicago Bulls",
            "cavaliers": "Cleveland Cavaliers",
            "cavs": "Cleveland Cavaliers",
            "sixers": "Philadelphia 76ers",
            "blazers": "Portland Trail Blazers",
        }

        for nickname, expected_team in nickname_mappings.items():
            assert alias_map.get(nickname) == expected_team, (
                f"Nickname '{nickname}' should resolve to '{expected_team}', "
                f"got '{alias_map.get(nickname)}'"
            )

    def test_city_names_resolve(self) -> None:
        """Verify city names resolve to correct teams."""
        alias_map = get_team_alias_map("nba")

        city_mappings = {
            "boston": "Boston Celtics",
            "miami": "Miami Heat",
            "chicago": "Chicago Bulls",
            "denver": "Denver Nuggets",
            "phoenix": "Phoenix Suns",
            "dallas": "Dallas Mavericks",
            "atlanta": "Atlanta Hawks",
            "orlando": "Orlando Magic",
        }

        for city, expected_team in city_mappings.items():
            assert alias_map.get(city) == expected_team, (
                f"City '{city}' should resolve to '{expected_team}', "
                f"got '{alias_map.get(city)}'"
            )
# ========================== Date Proximity Tests ==========================


class TestDateProximity:
    """Tests for date proximity matching to avoid false matches between
    repeated games (e.g., same teams playing multiple times per season)."""

    def test_dates_within_proximity_same_date(self) -> None:
        date = dt.date(2024, 11, 15)
        assert _dates_within_proximity(date, date) is True

    def test_dates_within_proximity_one_day_apart(self) -> None:
        date1 = dt.date(2024, 11, 15)
        date2 = dt.date(2024, 11, 16)
        assert _dates_within_proximity(date1, date2, tolerance_days=2) is True

    def test_dates_within_proximity_two_days_apart(self) -> None:
        date1 = dt.date(2024, 11, 15)
        date2 = dt.date(2024, 11, 17)
        assert _dates_within_proximity(date1, date2, tolerance_days=2) is True

    def test_dates_outside_proximity(self) -> None:
        date1 = dt.date(2024, 11, 15)
        date2 = dt.date(2024, 11, 20)
        assert _dates_within_proximity(date1, date2, tolerance_days=2) is False

    def test_dates_months_apart_same_teams(self) -> None:
        """Simulate the NHL issue: same teams play in October and December."""
        october_game = dt.date(2024, 10, 15)
        december_game = dt.date(2024, 12, 15)
        assert _dates_within_proximity(october_game, december_game, tolerance_days=2) is False

    def test_dates_both_none(self) -> None:
        assert _dates_within_proximity(None, None) is True

    def test_dates_one_none(self) -> None:
        date = dt.date(2024, 11, 15)
        assert _dates_within_proximity(date, None) is False
        assert _dates_within_proximity(None, date) is False


class TestParseDateFromGroups:
    """Tests for parsing dates from regex match groups."""

    def test_parse_date_with_date_year(self) -> None:
        groups = {"day": "15", "month": "11", "date_year": "2024"}
        result = _parse_date_from_groups(groups)
        assert result == dt.date(2024, 11, 15)

    def test_parse_date_with_year_fallback(self) -> None:
        groups = {"day": "15", "month": "11", "year": "2024"}
        result = _parse_date_from_groups(groups)
        assert result == dt.date(2024, 11, 15)

    def test_parse_date_prefers_date_year(self) -> None:
        groups = {"day": "15", "month": "11", "date_year": "2024", "year": "2023"}
        result = _parse_date_from_groups(groups)
        assert result == dt.date(2024, 11, 15)

    def test_parse_date_missing_day(self) -> None:
        groups = {"month": "11", "year": "2024"}
        result = _parse_date_from_groups(groups)
        assert result is None

    def test_parse_date_invalid_date(self) -> None:
        groups = {"day": "32", "month": "11", "year": "2024"}
        result = _parse_date_from_groups(groups)
        assert result is None


class TestScoreStructuredMatchWithDates:
    """Tests for _score_structured_match date proximity behavior."""

    def build_nhl_show_with_repeat_games(self) -> Tuple[Show, Season]:
        """Build a show where the same teams play multiple times."""
        # Jets vs Stars game on October 15
        october_game = Episode(
            title="Winnipeg Jets vs Dallas Stars",
            summary=None,
            originally_available=dt.date(2024, 10, 15),
            index=1,
        )
        # Jets vs Stars game on December 15 (same teams, different date)
        december_game = Episode(
            title="Winnipeg Jets vs Dallas Stars",
            summary=None,
            originally_available=dt.date(2024, 12, 15),
            index=50,
        )
        # Different matchup
        other_game = Episode(
            title="Edmonton Oilers vs Calgary Flames",
            summary=None,
            originally_available=dt.date(2024, 11, 1),
            index=20,
        )

        season = Season(
            key="10",
            title="2024-25 Season",
            summary=None,
            index=10,
            episodes=[october_game, december_game, other_game],
            display_number=10,
        )

        show = Show(key="nhl", title="NHL", summary=None, seasons=[season])
        return show, season

    def test_score_rejects_wrong_date_same_teams(self) -> None:
        """Teams match but date is way off - should return 0."""
        show, season = self.build_nhl_show_with_repeat_games()
        alias_lookup = _build_team_alias_lookup(show, {})

        # Structured name for December 15 game
        structured = StructuredName(
            raw="NHL.2024.12.15.Winnipeg.Jets.vs.Dallas.Stars.mkv",
            date=dt.date(2024, 12, 15),
            teams=["Winnipeg Jets", "Dallas Stars"],
        )

        # Score against the October 15 episode (wrong date)
        october_episode = season.episodes[0]
        score = _score_structured_match(structured, season, october_episode, alias_lookup)

        # Should be 0 because dates don't match within proximity
        assert score == 0.0

    def test_score_accepts_correct_date_same_teams(self) -> None:
        """Teams match and date matches - should return positive score."""
        show, season = self.build_nhl_show_with_repeat_games()
        alias_lookup = _build_team_alias_lookup(show, {})

        # Structured name for December 15 game
        structured = StructuredName(
            raw="NHL.2024.12.15.Winnipeg.Jets.vs.Dallas.Stars.mkv",
            date=dt.date(2024, 12, 15),
            teams=["Winnipeg Jets", "Dallas Stars"],
        )

        # Score against the December 15 episode (correct date)
        december_episode = season.episodes[1]
        score = _score_structured_match(structured, season, december_episode, alias_lookup)

        # Should be positive with date + team bonuses
        assert score >= 0.6

    def test_score_accepts_close_date(self) -> None:
        """Teams match and date is within tolerance - should match."""
        show, season = self.build_nhl_show_with_repeat_games()
        alias_lookup = _build_team_alias_lookup(show, {})

        # Structured name with date 1 day off (due to timezone or late game)
        structured = StructuredName(
            raw="NHL.2024.12.16.Winnipeg.Jets.vs.Dallas.Stars.mkv",
            date=dt.date(2024, 12, 16),
            teams=["Winnipeg Jets", "Dallas Stars"],
        )

        # Score against the December 15 episode
        december_episode = season.episodes[1]
        score = _score_structured_match(structured, season, december_episode, alias_lookup)

        # Should be positive - 1 day difference is within tolerance
        assert score >= 0.6

    def test_score_without_date_uses_team_only(self) -> None:
        """When no date is available, fall back to team-only matching."""
        show, season = self.build_nhl_show_with_repeat_games()
        alias_lookup = _build_team_alias_lookup(show, {})

        # Structured name without date
        structured = StructuredName(
            raw="NHL.Winnipeg.Jets.vs.Dallas.Stars.mkv",
            date=None,
            teams=["Winnipeg Jets", "Dallas Stars"],
        )

        # Score against the October episode (first one found)
        october_episode = season.episodes[0]
        score = _score_structured_match(structured, season, october_episode, alias_lookup)

        # Should get team match score
        assert score > 0


class TestMatchFileWithDateProximity:
    """Integration tests for file matching with date proximity."""

    def build_nhl_sport(self) -> SportConfig:
        """Build NHL sport config with date-based pattern."""
        pattern = PatternConfig(
            regex=r"(?i)^NHL[\s._-]+(?P<date_year>\d{4})[\s._-]+(?P<month>\d{2})[\s._-]+(?P<day>\d{2})[\s._-]+(?P<session>(?P<away>[A-Za-z ]+)[\s._-]+(?P<separator>vs)[\s._-]+(?P<home>[A-Za-z ]+))[\s._-]+.*\.(?P<extension>mkv)$",
            season_selector=SeasonSelector(mode="date", value_template="{date_year}-{month:0>2}-{day:0>2}"),
            episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
            priority=10,
        )
        return SportConfig(
            id="nhl",
            name="NHL",
            metadata=MetadataConfig(url="https://example.com"),
            patterns=[pattern],
            destination=DestinationTemplates(),
        )

    def build_nhl_show_repeat_games(self) -> Show:
        """Build show with same matchup on different dates."""
        season = Season(
            key="10",
            title="2024-25 Season",
            summary=None,
            index=10,
            episodes=[
                Episode(
                    title="Winnipeg Jets vs Dallas Stars",
                    summary=None,
                    originally_available=dt.date(2024, 10, 15),
                    index=5,
                ),
                Episode(
                    title="Winnipeg Jets vs Dallas Stars",
                    summary=None,
                    originally_available=dt.date(2024, 12, 15),
                    index=45,
                ),
            ],
            display_number=10,
        )
        return Show(key="nhl", title="NHL", summary=None, seasons=[season])

    def test_match_selects_correct_game_by_date(self) -> None:
        """File with December date should match December episode, not October."""
        sport = self.build_nhl_sport()
        show = self.build_nhl_show_repeat_games()
        patterns = compile_patterns(sport)

        # December 15 game file
        result = match_file_to_episode(
            "NHL.2024.12.15.Winnipeg Jets vs Dallas Stars.1080p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None
        episode = result["episode"]
        # Should match December episode (index 45), not October (index 5)
        assert episode.index == 45
        assert episode.originally_available == dt.date(2024, 12, 15)

    def test_match_selects_october_game_correctly(self) -> None:
        """File with October date should match October episode."""
        sport = self.build_nhl_sport()
        show = self.build_nhl_show_repeat_games()
        patterns = compile_patterns(sport)

        # October 15 game file
        result = match_file_to_episode(
            "NHL.2024.10.15.Winnipeg Jets vs Dallas Stars.1080p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None
        episode = result["episode"]
        # Should match October episode (index 5), not December (index 45)
        assert episode.index == 5
        assert episode.originally_available == dt.date(2024, 10, 15)

