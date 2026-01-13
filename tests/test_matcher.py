from __future__ import annotations

import datetime as dt
import logging

from playbook.config import (
    DestinationTemplates,
    EpisodeSelector,
    MetadataConfig,
    PatternConfig,
    SeasonSelector,
    SportConfig,
)
from playbook.matcher import (
    _build_session_lookup,
    _build_team_alias_lookup,
    _dates_within_proximity,
    _DEFAULT_GENERIC_SESSION_ALIASES,
    _location_matches_title,
    _parse_date_from_groups,
    _parse_date_string,
    _resolve_session_lookup,
    _score_structured_match,
    compile_patterns,
    match_file_to_episode,
)
from playbook.models import Episode, Season, Show
from playbook.parsers.structured_filename import StructuredName
from playbook.team_aliases import get_team_alias_map


def build_show() -> tuple[Show, Season]:
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


def build_sport(patterns: list[PatternConfig]) -> SportConfig:
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

    diagnostics: list[tuple[str, str]] = []
    result = match_file_to_episode("01.fp1.release.mkv", sport, show, patterns, diagnostics=diagnostics)

    assert result is not None
    assert result["season"] is season
    assert result["episode"].title == "Free Practice 1"
    assert result["pattern"].config is pattern
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

    diagnostics: list[tuple[str, str]] = []
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

    diagnostics: list[tuple[str, str]] = []
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

    trace: dict[str, object] = {}
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

        assert len(canonical_teams) == 30, f"Expected 30 NBA teams in alias map, got {len(canonical_teams)}"

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
                f"Abbreviation '{abbr}' should resolve to '{expected_team}', got '{alias_map.get(abbr)}'"
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
                f"Nickname '{nickname}' should resolve to '{expected_team}', got '{alias_map.get(nickname)}'"
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
                f"City '{city}' should resolve to '{expected_team}', got '{alias_map.get(city)}'"
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

    def build_nhl_show_with_repeat_games(self) -> tuple[Show, Season]:
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


def test_session_to_episode_resolution() -> None:
    """Test that different session types (Race/Practice/Qualifying) from the same round map to the same episode.

    This validates the critical behavior for racing content where:
    - Metadata defines one episode per race weekend/round
    - Filenames include session types (Practice/Qualifying/Race)
    - All sessions from the same round must resolve to the same episode
    """
    # Create IndyCar pattern
    pattern = PatternConfig(
        regex=r"(?i)^IndyCar\.Series\.(?P<year>\d{4})\.Round(?P<round>\d{2})\.(?P<location>[^.]+)\.(?P<session>Race|Practice|Qualifying)\..*\.mkv$",
        season_selector=SeasonSelector(mode="round", group="round"),
        episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
        priority=10,
    )

    sport = SportConfig(
        id="indycar",
        name="IndyCar Series",
        metadata=MetadataConfig(url="https://example.com"),
        patterns=[pattern],
        destination=DestinationTemplates(),
    )

    # Create show with one episode per round (not per session)
    episode = Episode(
        title="The Thermal Club IndyCar Grand Prix",
        summary=None,
        originally_available=dt.date(2025, 3, 23),
        index=2,
    )

    season = Season(
        key="2025",
        title="2025 Season",
        summary=None,
        index=1,
        episodes=[episode],
        display_number=1,
        round_number=2,
    )

    show = Show(key="indycar", title="NTT IndyCar Series", summary=None, seasons=[season])

    patterns = compile_patterns(sport)

    # Test that Practice session maps to episode
    practice_result = match_file_to_episode(
        "IndyCar.Series.2025.Round02.Thermal.Practice.STAN.WEB-DL.1080p.h264.English-MWR.mkv",
        sport,
        show,
        patterns,
    )

    # Test that Qualifying session maps to same episode
    qualifying_result = match_file_to_episode(
        "IndyCar.Series.2025.Round02.Thermal.Qualifying.STAN.WEB-DL.1080p.h264.English-MWR.mkv",
        sport,
        show,
        patterns,
    )

    # Test that Race session maps to same episode
    race_result = match_file_to_episode(
        "IndyCar.Series.2025.Round02.Thermal.Race.STAN.WEB-DL.1080p.h264.English-MWR.mkv",
        sport,
        show,
        patterns,
    )

    # All three sessions should resolve to the same episode
    assert practice_result is not None, "Practice session should resolve to episode"
    assert qualifying_result is not None, "Qualifying session should resolve to episode"
    assert race_result is not None, "Race session should resolve to episode"

    # Verify all map to the same episode
    assert practice_result["episode"] is episode
    assert qualifying_result["episode"] is episode
    assert race_result["episode"] is episode

    # Verify all have correct season
    assert practice_result["season"] is season
    assert qualifying_result["season"] is season
    assert race_result["season"] is season

    # Verify episode details are correct
    assert practice_result["episode"].title == "The Thermal Club IndyCar Grand Prix"
    assert practice_result["episode"].index == 2


def test_indycar_pattern_matching() -> None:
    """Test IndyCar pattern matching with round-based fallback and fuzzy location matching.

    This validates the fix for IndyCar series where session names (Race/Practice/Qualifying)
    don't match episode titles, requiring fallback to round number + location fuzzy matching.
    """
    # Create IndyCar pattern (simplified version of actual pattern)
    pattern = PatternConfig(
        regex=r"(?i)^IndyCar\.Series\.(?P<year>\d{4})\.Round(?P<round>\d{2})\.(?P<location>[^.]+)\.(?P<session>Race|Practice|Qualifying)\..*\.mkv$",
        season_selector=SeasonSelector(mode="key", group="year"),
        episode_selector=EpisodeSelector(group="round", allow_fallback_to_title=True),
        priority=10,
    )

    sport = SportConfig(
        id="indycar",
        name="IndyCar Series",
        metadata=MetadataConfig(url="https://example.com"),
        patterns=[pattern],
        destination=DestinationTemplates(),
    )

    # Create IndyCar show with realistic episode structure
    # Note: Episode titles have full location names, not just session types
    episode1 = Episode(
        title="Streets of St. Petersburg Grand Prix",
        summary=None,
        originally_available=dt.date(2025, 3, 2),
        index=1,
    )
    episode2 = Episode(
        title="The Thermal Club IndyCar Grand Prix",
        summary=None,
        originally_available=dt.date(2025, 3, 23),
        index=2,
    )
    episode3 = Episode(
        title="Indianapolis 500",
        summary=None,
        originally_available=dt.date(2025, 5, 25),
        index=6,
    )

    season = Season(
        key="2025",
        title="2025 Season",
        summary=None,
        index=1,
        episodes=[episode1, episode2, episode3],
        display_number=1,
        round_number=1,
    )

    show = Show(key="indycar", title="NTT IndyCar Series", summary=None, seasons=[season])

    patterns = compile_patterns(sport)

    # Test case 1: Round 2 with location "Thermal" should fuzzy-match to "The Thermal Club IndyCar Grand Prix"
    trace: dict[str, object] = {}
    result = match_file_to_episode(
        "IndyCar.Series.2025.Round02.Thermal.Race.STAN.WEB-DL.1080p.h264.English-MWR.mkv",
        sport,
        show,
        patterns,
        trace=trace,
    )

    assert result is not None, "Should match IndyCar file with round-based fallback"
    assert result["season"] is season
    assert result["episode"].title == "The Thermal Club IndyCar Grand Prix"
    assert result["episode"].index == 2
    assert result["pattern"].config is pattern

    # Verify trace shows round-based fallback was used
    assert trace.get("status") == "matched"
    attempts = trace.get("attempts")
    assert attempts
    matched_attempt = next((item for item in attempts if item.get("status") == "matched"), None)
    assert matched_attempt is not None

    # Test case 2: Round 6 with location "Indianapolis" should match "Indianapolis 500"
    result2 = match_file_to_episode(
        "IndyCar.Series.2025.Round06.Indianapolis.Race.STAN.WEB-DL.1080p.h264.English-MWR.mkv",
        sport,
        show,
        patterns,
    )

    assert result2 is not None
    assert result2["episode"].title == "Indianapolis 500"
    assert result2["episode"].index == 6

    # Test case 3: Round 1 with location "StPetersburg" should match "Streets of St. Petersburg Grand Prix"
    result3 = match_file_to_episode(
        "IndyCar.Series.2025.Round01.StPetersburg.Qualifying.STAN.WEB-DL.1080p.h264.English-MWR.mkv",
        sport,
        show,
        patterns,
    )

    assert result3 is not None
    assert result3["episode"].title == "Streets of St. Petersburg Grand Prix"
    assert result3["episode"].index == 1


def test_fuzzy_location_matching() -> None:
    """Test fuzzy location matching for racing content where filenames have
    abbreviated location names (e.g., "Thermal") and episode titles have full
    location names (e.g., "The Thermal Club IndyCar Grand Prix").

    This validates the _location_matches_title function which uses rapidfuzz
    partial_ratio for fuzzy substring matching.
    """

    # Test exact substring match (case-sensitive)
    assert _location_matches_title("Thermal", "The Thermal Club IndyCar Grand Prix") is True

    # Test case-insensitive exact match
    assert _location_matches_title("thermal", "The Thermal Club IndyCar Grand Prix") is True

    # Test partial match with common racing locations
    assert _location_matches_title("Indianapolis", "Indianapolis 500") is True
    assert _location_matches_title("Indy", "Indianapolis 500") is True

    # Test St. Petersburg variations
    assert _location_matches_title("St.Petersburg", "Streets of St. Petersburg Grand Prix") is True
    assert _location_matches_title("St Petersburg", "Streets of St. Petersburg Grand Prix") is True
    assert _location_matches_title("Petersburg", "Streets of St. Petersburg Grand Prix") is True

    # Test location with punctuation variations
    assert _location_matches_title("St.Pete", "Streets of St. Petersburg Grand Prix") is True

    # Test non-matching locations (should return False)
    assert _location_matches_title("Miami", "Indianapolis 500") is False
    assert _location_matches_title("Texas", "The Thermal Club IndyCar Grand Prix") is False

    # Test empty/None inputs
    assert _location_matches_title("", "Indianapolis 500") is False
    assert _location_matches_title("Indianapolis", "") is False
    assert _location_matches_title("", "") is False

    # Test threshold behavior - very different strings should not match
    assert _location_matches_title("xyz", "Indianapolis 500") is False
    assert _location_matches_title("abc", "The Thermal Club IndyCar Grand Prix") is False

    # Test multi-word locations
    assert _location_matches_title("Long Beach", "Acura Grand Prix of Long Beach") is True
    assert _location_matches_title("Road America", "Road America 250") is True

    # Test abbreviated vs full location names
    assert _location_matches_title("Barber", "Honda Indy Grand Prix of Alabama at Barber Motorsports Park") is True
    assert _location_matches_title("Alabama", "Honda Indy Grand Prix of Alabama at Barber Motorsports Park") is True

    # Test with default threshold (80.0) - close matches should work
    assert _location_matches_title("Laguna Seca", "WeatherTech Raceway Laguna Seca") is True

    # Test custom threshold
    # Very strict threshold (99.0) - only exact substring should match
    assert _location_matches_title("Thermal", "The Thermal Club IndyCar Grand Prix", threshold=99.0) is True
    # Looser threshold should allow more fuzzy matches
    assert _location_matches_title("Therm", "The Thermal Club IndyCar Grand Prix", threshold=70.0) is True


def test_nhl_team_name_cleaning() -> None:
    """Test that team names are cleaned of quality metadata and source codes.

    This validates the fix for GitHub Issue #86 where quality metadata like
    "720p60_EN_Utah16" was being captured as part of team names. The
    _strip_team_noise() function should remove resolution tags, FPS indicators,
    and source codes from team names.
    """
    from playbook.matcher import _strip_team_noise

    # Test case 1: Team with 720p60 quality tag
    result1 = _strip_team_noise("Utah Mammoth 720p60")
    assert result1 == "Utah Mammoth", f"Expected 'Utah Mammoth', got '{result1}'"

    # Test case 2: Team with 1080p quality tag
    result2 = _strip_team_noise("Ottawa Senators 1080p")
    assert result2 == "Ottawa Senators", f"Expected 'Ottawa Senators', got '{result2}'"

    # Test case 3: Team with source code like _EN_Utah16
    result3 = _strip_team_noise("Dallas Stars EN")
    assert result3 == "Dallas Stars EN", f"Expected 'Dallas Stars EN', got '{result3}'"

    # Test case 4: Team with multiple quality indicators
    result4 = _strip_team_noise("Boston Bruins 720p 60fps")
    assert result4 == "Boston Bruins", f"Expected 'Boston Bruins', got '{result4}'"

    # Test case 5: Team with provider tag
    result5 = _strip_team_noise("Toronto Maple Leafs sky")
    assert result5 == "Toronto Maple Leafs", f"Expected 'Toronto Maple Leafs', got '{result5}'"

    # Test case 6: Team with web/hdtv tag
    result6 = _strip_team_noise("Montreal Canadiens web")
    assert result6 == "Montreal Canadiens", f"Expected 'Montreal Canadiens', got '{result6}'"

    # Test case 7: Team name that's clean (no noise)
    result7 = _strip_team_noise("Winnipeg Jets")
    assert result7 == "Winnipeg Jets", f"Expected 'Winnipeg Jets', got '{result7}'"

    # Test case 8: Complex case - the exact scenario from GitHub Issue #86
    result8 = _strip_team_noise("Utah Mammoth 720p60_EN_Utah16")
    assert result8 == "Utah Mammoth", f"Expected 'Utah Mammoth', got '{result8}'"


def test_nhl_date_season_resolution() -> None:
    """Test that NHL files with date patterns resolve to correct seasons.

    NHL seasons span calendar years (e.g., 2025-2026 season runs from October 2025
    through June 2026). This test verifies that dates from filenames correctly
    resolve to the appropriate season based on episode dates.
    """
    # Create NHL pattern with date-based season selector
    pattern = PatternConfig(
        regex=r"(?i)^NHL[\s._-]+(?P<day>\d{2})-(?P<month>\d{2})-(?P<date_year>\d{4})[\s._-]+RS[\s._-]+(?P<away>[A-Za-z ]+)[\s._-]+vs[\s._-]+(?P<home>[A-Za-z ]+).*\.mkv$",
        season_selector=SeasonSelector(mode="date", value_template="{date_year}-{month:0>2}-{day:0>2}"),
        episode_selector=EpisodeSelector(group="away", allow_fallback_to_title=True),
        priority=10,
    )

    sport = SportConfig(
        id="nhl",
        name="NHL",
        metadata=MetadataConfig(url="https://example.com"),
        patterns=[pattern],
        destination=DestinationTemplates(),
    )

    # Create 2024-2025 season with games from October 2024 through June 2025
    season_2024_2025 = Season(
        key="2024-2025",
        title="2024-2025 Season",
        summary=None,
        index=1,
        episodes=[
            Episode(
                title="Ottawa Senators vs Toronto Maple Leafs",
                summary=None,
                originally_available=dt.date(2024, 10, 15),
                index=1,
            ),
            Episode(
                title="Montreal Canadiens vs Boston Bruins",
                summary=None,
                originally_available=dt.date(2024, 12, 20),
                index=50,
            ),
        ],
        display_number=1,
    )

    # Create 2025-2026 season with games from October 2025 onwards
    season_2025_2026 = Season(
        key="2025-2026",
        title="2025-2026 Season",
        summary=None,
        index=2,
        episodes=[
            Episode(
                title="Ottawa Senators vs Utah Mammoth",
                summary=None,
                originally_available=dt.date(2025, 1, 7),
                index=30,
            ),
            Episode(
                title="Winnipeg Jets vs Dallas Stars",
                summary=None,
                originally_available=dt.date(2025, 10, 15),
                index=1,
            ),
        ],
        display_number=2,
    )

    show = Show(
        key="nhl",
        title="NHL",
        summary=None,
        seasons=[season_2024_2025, season_2025_2026],
    )

    patterns = compile_patterns(sport)

    # Test 1: January 2025 date should match 2025-2026 season
    result1 = match_file_to_episode(
        "NHL 07-01-2025 RS Ottawa Senators vs Utah Mammoth 720p60.mkv",
        sport,
        show,
        patterns,
    )

    assert result1 is not None, "Should match file with date 2025-01-07"
    assert result1["season"] is season_2025_2026, "January 2025 should resolve to 2025-2026 season"
    assert result1["episode"].title == "Ottawa Senators vs Utah Mammoth"
    assert result1["episode"].originally_available == dt.date(2025, 1, 7)

    # Test 2: October 2024 date should match 2024-2025 season
    result2 = match_file_to_episode(
        "NHL 15-10-2024 RS Ottawa Senators vs Toronto Maple Leafs.mkv",
        sport,
        show,
        patterns,
    )

    assert result2 is not None, "Should match file with date 2024-10-15"
    assert result2["season"] is season_2024_2025, "October 2024 should resolve to 2024-2025 season"
    assert result2["episode"].title == "Ottawa Senators vs Toronto Maple Leafs"
    assert result2["episode"].originally_available == dt.date(2024, 10, 15)

    # Test 3: December 2024 date should match 2024-2025 season
    result3 = match_file_to_episode(
        "NHL 20-12-2024 RS Montreal Canadiens vs Boston Bruins.mkv",
        sport,
        show,
        patterns,
    )

    assert result3 is not None, "Should match file with date 2024-12-20"
    assert result3["season"] is season_2024_2025, "December 2024 should resolve to 2024-2025 season"
    assert result3["episode"].title == "Montreal Canadiens vs Boston Bruins"
    assert result3["episode"].originally_available == dt.date(2024, 12, 20)

    # Test 4: October 2025 date should match 2025-2026 season (new season start)
    result4 = match_file_to_episode(
        "NHL 15-10-2025 RS Winnipeg Jets vs Dallas Stars.mkv",
        sport,
        show,
        patterns,
    )

    assert result4 is not None, "Should match file with date 2025-10-15"
    assert result4["season"] is season_2025_2026, "October 2025 should resolve to 2025-2026 season"
    assert result4["episode"].title == "Winnipeg Jets vs Dallas Stars"
    assert result4["episode"].originally_available == dt.date(2025, 10, 15)


def test_nhl_integration_github_issue_86() -> None:
    """Integration test for GitHub Issue #86: NHL file processing failures.

    This test verifies that all three fixes work together end-to-end:
    1. Season resolution from date components (DD-MM-YYYY format)
    2. Team name cleaning (removing quality metadata like 720p60_EN_Utah16)
    3. No AttributeError when passing PatternRuntime to destination builder

    Uses the exact filename from GitHub Issue #86 to validate the complete fix.
    """
    # Create NHL pattern with date-based season selector
    pattern = PatternConfig(
        regex=r"(?i)^NHL[\s._-]+(?P<day>\d{2})-(?P<month>\d{2})-(?P<date_year>\d{4})[\s._-]+RS[\s._-]+(?P<away>[A-Za-z ]+)[\s._-]+vs\.?[\s._-]+(?P<home>[A-Za-z ]+).*\.mkv$",
        season_selector=SeasonSelector(mode="date", value_template="{date_year}-{month:0>2}-{day:0>2}"),
        episode_selector=EpisodeSelector(group="away", allow_fallback_to_title=True),
        priority=10,
    )

    sport = SportConfig(
        id="nhl",
        name="NHL",
        metadata=MetadataConfig(url="https://example.com"),
        patterns=[pattern],
        destination=DestinationTemplates(),
    )

    # Create 2025-2026 season with the exact episode from the GitHub issue
    season_2025_2026 = Season(
        key="2025-2026",
        title="2025-2026 Season",
        summary=None,
        index=1,
        episodes=[
            Episode(
                title="Ottawa Senators vs Utah Mammoth",
                summary=None,
                originally_available=dt.date(2025, 1, 7),
                index=1,
            ),
        ],
        display_number=1,
    )

    show = Show(
        key="nhl",
        title="NHL",
        summary=None,
        seasons=[season_2025_2026],
    )

    patterns = compile_patterns(sport)

    # Test with the EXACT filename from GitHub Issue #86
    filename = "NHL 07-01-2025 RS Ottawa Senators vs. Utah Mammoth 720p60_EN_Utah16.mkv"
    result = match_file_to_episode(filename, sport, show, patterns)

    # Verify all aspects of the fix
    assert result is not None, f"Should match filename: {filename}"
    assert result["season"] is season_2025_2026, "Should resolve to 2025-2026 season"
    assert result["episode"].title == "Ottawa Senators vs Utah Mammoth", "Should match correct episode"
    assert result["episode"].originally_available == dt.date(2025, 1, 7), "Should match date from filename"

    # Verify no AttributeError by checking pattern is PatternRuntime
    # The match may come from either the structured matcher or the pattern-based matcher
    # Both are valid matching mechanisms
    assert result["pattern"] is not None, "Should return a matched pattern"


# ========================== Partial Date Parsing Tests ==========================


class TestParseDateStringPartialDates:
    """Tests for parsing partial dates (DD MM format without year)."""

    def test_parse_partial_date_space_separator(self) -> None:
        """Parse '16 11' with reference year 2025."""
        result = _parse_date_string("16 11", reference_year=2025)
        assert result == dt.date(2025, 11, 16)

    def test_parse_partial_date_dash_separator(self) -> None:
        """Parse '16-11' with reference year 2025."""
        result = _parse_date_string("16-11", reference_year=2025)
        assert result == dt.date(2025, 11, 16)

    def test_parse_partial_date_dot_separator(self) -> None:
        """Parse '16.11' with reference year 2025."""
        result = _parse_date_string("16.11", reference_year=2025)
        assert result == dt.date(2025, 11, 16)

    def test_parse_partial_date_slash_separator(self) -> None:
        """Parse '16/11' with reference year 2025."""
        result = _parse_date_string("16/11", reference_year=2025)
        assert result == dt.date(2025, 11, 16)

    def test_parse_partial_date_without_reference_year_returns_none(self) -> None:
        """Partial date without reference year should return None."""
        result = _parse_date_string("16 11")
        assert result is None

    def test_parse_partial_date_invalid_day(self) -> None:
        """Invalid day (32) should return None."""
        result = _parse_date_string("32 11", reference_year=2025)
        assert result is None

    def test_parse_partial_date_invalid_month(self) -> None:
        """Invalid month (13) should return None."""
        result = _parse_date_string("16 13", reference_year=2025)
        assert result is None

    def test_parse_full_date_ignores_reference_year(self) -> None:
        """Full date should use its own year, not reference year."""
        result = _parse_date_string("16 11 2024", reference_year=2025)
        assert result == dt.date(2024, 11, 16)


# ========================== Figure Skating Date Resolution Tests ==========================


class TestFigureSkatingDateResolution:
    """Tests for Figure Skating Grand Prix date-based episode resolution.

    Figure Skating Grand Prix files typically have patterns like:
    'Figure.Skating.GP.2025.16.11.Ice.Dancing.Rhythm.Dance.mkv'

    where '16 11' is the event date (November 16) that needs to resolve
    to the correct Grand Prix event by date proximity.
    """

    def build_figure_skating_show(self) -> tuple[Show, Season]:
        """Build a Figure Skating show with Grand Prix events on specific dates."""
        # ISU Grand Prix events for the 2025 season
        skate_america = Episode(
            title="Skate America",
            summary=None,
            originally_available=dt.date(2025, 10, 18),  # October 18-20
            index=1,
        )
        skate_canada = Episode(
            title="Skate Canada International",
            summary=None,
            originally_available=dt.date(2025, 10, 25),  # October 25-27
            index=2,
        )
        grand_prix_france = Episode(
            title="Grand Prix de France",
            summary=None,
            originally_available=dt.date(2025, 11, 1),  # November 1-3
            index=3,
        )
        nhk_trophy = Episode(
            title="NHK Trophy",
            summary=None,
            originally_available=dt.date(2025, 11, 8),  # November 8-10
            index=4,
        )
        rostelecom_cup = Episode(
            title="Rostelecom Cup",
            summary=None,
            originally_available=dt.date(2025, 11, 15),  # November 15-17
            index=5,
        )
        grand_prix_final = Episode(
            title="Grand Prix Final",
            summary=None,
            originally_available=dt.date(2025, 12, 5),  # December 5-8
            index=6,
        )

        season = Season(
            key="2025",
            title="2025 Grand Prix",
            summary=None,
            index=1,
            episodes=[
                skate_america,
                skate_canada,
                grand_prix_france,
                nhk_trophy,
                rostelecom_cup,
                grand_prix_final,
            ],
            display_number=1,
        )

        show = Show(
            key="figure_skating_gp",
            title="ISU Grand Prix of Figure Skating",
            summary=None,
            seasons=[season],
        )

        return show, season

    def build_figure_skating_sport(self) -> SportConfig:
        """Build Figure Skating sport config with event_date pattern."""
        # Pattern captures event_date as DD MM (partial date) and year separately
        pattern = PatternConfig(
            regex=(
                r"(?i)^Figure\.Skating\.GP\.(?P<year>\d{4})\.(?P<event_date>\d{1,2}[\s._-]\d{1,2})\."
                r"(?P<session>Ice[\s._-]+Dancing|Pairs|Ladies|Men|Exhibition).*\.mkv$"
            ),
            season_selector=SeasonSelector(mode="key", group="year"),
            episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
            priority=10,
        )
        return SportConfig(
            id="figure_skating_gp",
            name="ISU Grand Prix of Figure Skating",
            metadata=MetadataConfig(url="https://example.com"),
            patterns=[pattern],
            destination=DestinationTemplates(),
        )

    def test_date_resolution_november_16_matches_rostelecom_cup(self) -> None:
        """Event date '16 11' (Nov 16) should resolve to Rostelecom Cup (Nov 15-17)."""
        show, season = self.build_figure_skating_show()
        sport = self.build_figure_skating_sport()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "Figure.Skating.GP.2025.16.11.Ice.Dancing.Rhythm.Dance.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Should resolve Figure Skating file with date fallback"
        assert result["season"] is season
        assert result["episode"].title == "Rostelecom Cup"
        assert result["episode"].originally_available == dt.date(2025, 11, 15)

    def test_date_resolution_october_18_matches_skate_america(self) -> None:
        """Event date '18 10' (Oct 18) should resolve to Skate America (Oct 18-20)."""
        show, season = self.build_figure_skating_show()
        sport = self.build_figure_skating_sport()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "Figure.Skating.GP.2025.18.10.Ladies.Short.Program.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Should resolve Figure Skating file with date fallback"
        assert result["episode"].title == "Skate America"

    def test_date_resolution_november_9_matches_nhk_trophy(self) -> None:
        """Event date '09 11' (Nov 9) should resolve to NHK Trophy (Nov 8-10)."""
        show, season = self.build_figure_skating_show()
        sport = self.build_figure_skating_sport()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "Figure.Skating.GP.2025.09.11.Men.Free.Skate.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Should resolve Figure Skating file with date fallback"
        assert result["episode"].title == "NHK Trophy"

    def test_date_resolution_with_dash_separator(self) -> None:
        """Event date with dash separator should also work."""
        show, season = self.build_figure_skating_show()

        # Modify pattern to accept dash separator
        pattern = PatternConfig(
            regex=(
                r"(?i)^Figure\.Skating\.GP\.(?P<year>\d{4})\.(?P<event_date>\d{1,2}-\d{1,2})\."
                r"(?P<session>Ice[\s._-]+Dancing|Pairs|Ladies|Men|Exhibition).*\.mkv$"
            ),
            season_selector=SeasonSelector(mode="key", group="year"),
            episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
            priority=10,
        )
        sport = SportConfig(
            id="figure_skating_gp",
            name="ISU Grand Prix of Figure Skating",
            metadata=MetadataConfig(url="https://example.com"),
            patterns=[pattern],
            destination=DestinationTemplates(),
        )
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "Figure.Skating.GP.2025.15-11.Pairs.Short.Program.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Should resolve Figure Skating file with dash-separated date"
        assert result["episode"].title == "Rostelecom Cup"

    def test_date_resolution_no_match_outside_proximity(self) -> None:
        """Event date far from any episode should not match."""
        show, season = self.build_figure_skating_show()
        sport = self.build_figure_skating_sport()
        patterns = compile_patterns(sport)

        # March 15 is far from any GP event
        result = match_file_to_episode(
            "Figure.Skating.GP.2025.15.03.Ice.Dancing.Free.Dance.mkv",
            sport,
            show,
            patterns,
        )

        # Should not match because March 15 is far from any event
        assert result is None, "Should not resolve when date is far from any episode"


class TestDateBasedEpisodeResolutionFallback:
    """Tests for the date-based episode resolution fallback mechanism.

    This tests the scenario where session name lookup fails but we have
    a parsed date (from _parse_date_from_groups) that can be used to
    find episodes by date proximity.
    """

    def test_date_fallback_uses_parsed_date_from_groups(self) -> None:
        """When session lookup fails, fallback to date from parsed groups."""
        # Create a pattern that parses date components
        pattern = PatternConfig(
            regex=(
                r"(?i)^(?P<sport>Figure\.Skating)\.GP\.(?P<year>\d{4})\."
                r"(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<session>[A-Za-z]+).*\.mkv$"
            ),
            season_selector=SeasonSelector(mode="key", group="year"),
            episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
            priority=10,
        )
        sport = SportConfig(
            id="figure_skating_gp",
            name="ISU Grand Prix of Figure Skating",
            metadata=MetadataConfig(url="https://example.com"),
            patterns=[pattern],
            destination=DestinationTemplates(),
        )

        # Create episode on November 16
        episode = Episode(
            title="Rostelecom Cup",
            summary=None,
            originally_available=dt.date(2025, 11, 16),
            index=1,
        )
        season = Season(
            key="2025",
            title="2025 Grand Prix",
            summary=None,
            index=1,
            episodes=[episode],
            display_number=1,
        )
        show = Show(
            key="figure_skating_gp",
            title="ISU Grand Prix of Figure Skating",
            summary=None,
            seasons=[season],
        )

        patterns = compile_patterns(sport)

        # File has session=Exhibition which won't match "Rostelecom Cup"
        # But date (16 11) matches episode date
        result = match_file_to_episode(
            "Figure.Skating.GP.2025.16.11.Exhibition.720p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Should resolve via date fallback"
        assert result["episode"].title == "Rostelecom Cup"

    def test_date_fallback_selects_closest_episode(self) -> None:
        """Date fallback should select episode with closest date."""
        pattern = PatternConfig(
            regex=(
                r"(?i)^(?P<sport>GP)\.(?P<year>\d{4})\.(?P<day>\d{2})\.(?P<month>\d{2})\."
                r"(?P<session>[A-Za-z]+).*\.mkv$"
            ),
            season_selector=SeasonSelector(mode="key", group="year"),
            episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
            priority=10,
        )
        sport = SportConfig(
            id="gp",
            name="Grand Prix",
            metadata=MetadataConfig(url="https://example.com"),
            patterns=[pattern],
            destination=DestinationTemplates(),
        )

        # Two episodes close together
        episode1 = Episode(
            title="Event A",
            summary=None,
            originally_available=dt.date(2025, 11, 14),  # Nov 14
            index=1,
        )
        episode2 = Episode(
            title="Event B",
            summary=None,
            originally_available=dt.date(2025, 11, 17),  # Nov 17
            index=2,
        )
        season = Season(
            key="2025",
            title="2025",
            summary=None,
            index=1,
            episodes=[episode1, episode2],
            display_number=1,
        )
        show = Show(key="gp", title="Grand Prix", summary=None, seasons=[season])

        patterns = compile_patterns(sport)

        # File date Nov 15 - closer to Nov 14 (1 day) than Nov 17 (2 days)
        result = match_file_to_episode(
            "GP.2025.15.11.Warmup.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None
        assert result["episode"].title == "Event A", "Should select closest episode by date"

    def test_date_fallback_respects_2_day_tolerance(self) -> None:
        """Date fallback should only match episodes within 2-day tolerance."""
        pattern = PatternConfig(
            regex=(
                r"(?i)^(?P<sport>GP)\.(?P<year>\d{4})\.(?P<day>\d{2})\.(?P<month>\d{2})\."
                r"(?P<session>[A-Za-z]+).*\.mkv$"
            ),
            season_selector=SeasonSelector(mode="key", group="year"),
            episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
            priority=10,
        )
        sport = SportConfig(
            id="gp",
            name="Grand Prix",
            metadata=MetadataConfig(url="https://example.com"),
            patterns=[pattern],
            destination=DestinationTemplates(),
        )

        # Episode on Nov 10
        episode = Episode(
            title="Event",
            summary=None,
            originally_available=dt.date(2025, 11, 10),
            index=1,
        )
        season = Season(
            key="2025",
            title="2025",
            summary=None,
            index=1,
            episodes=[episode],
            display_number=1,
        )
        show = Show(key="gp", title="Grand Prix", summary=None, seasons=[season])

        patterns = compile_patterns(sport)

        # File date Nov 12 - 2 days away (within tolerance)
        result_within = match_file_to_episode(
            "GP.2025.12.11.Warmup.mkv",
            sport,
            show,
            patterns,
        )
        assert result_within is not None, "2 days difference should be within tolerance"

        # File date Nov 15 - 5 days away (outside tolerance)
        result_outside = match_file_to_episode(
            "GP.2025.15.11.Warmup.mkv",
            sport,
            show,
            patterns,
        )
        assert result_outside is None, "5 days difference should be outside tolerance"


# ========================== Generic Session Matching Tests ==========================


class TestDefaultGenericSessionAliases:
    """Tests for _DEFAULT_GENERIC_SESSION_ALIASES configuration."""

    def test_race_aliases_exist(self) -> None:
        """Verify Race has common alias variations."""
        assert "Race" in _DEFAULT_GENERIC_SESSION_ALIASES
        aliases = _DEFAULT_GENERIC_SESSION_ALIASES["Race"]
        # Should include Main Race, Feature Race variations
        assert "Race" in aliases
        assert "Main Race" in aliases
        assert "Feature Race" in aliases

    def test_practice_aliases_exist(self) -> None:
        """Verify Practice has common alias variations."""
        assert "Practice" in _DEFAULT_GENERIC_SESSION_ALIASES
        aliases = _DEFAULT_GENERIC_SESSION_ALIASES["Practice"]
        # Should include Free Practice variations
        assert "Practice" in aliases
        assert "Free Practice" in aliases

    def test_qualifying_aliases_exist(self) -> None:
        """Verify Qualifying has common alias variations."""
        assert "Qualifying" in _DEFAULT_GENERIC_SESSION_ALIASES
        aliases = _DEFAULT_GENERIC_SESSION_ALIASES["Qualifying"]
        # Should include Quali variations
        assert "Qualifying" in aliases
        assert "Quali" in aliases

    def test_sprint_aliases_exist(self) -> None:
        """Verify Sprint has common alias variations."""
        assert "Sprint" in _DEFAULT_GENERIC_SESSION_ALIASES
        aliases = _DEFAULT_GENERIC_SESSION_ALIASES["Sprint"]
        # Should include Sprint Race variations
        assert "Sprint" in aliases
        assert "Sprint Race" in aliases


class TestBuildSessionLookupGenericAliases:
    """Tests for _build_session_lookup with generic session aliases."""

    def build_empty_season(self) -> Season:
        """Build a season with minimal episodes (no session aliases in titles)."""
        episode = Episode(
            title="Grand Prix",
            summary=None,
            originally_available=dt.date(2025, 3, 23),
            index=1,
        )
        return Season(
            key="2025",
            title="2025 Season",
            summary=None,
            index=1,
            episodes=[episode],
            display_number=1,
        )

    def test_generic_race_alias_added_to_lookup(self) -> None:
        """Generic 'race' alias should be added to session lookup."""
        pattern = PatternConfig(
            regex=r"(?i)^.*\.(?P<session>Race|Practice).*\.mkv$",
            priority=10,
        )
        season = self.build_empty_season()

        lookup = _build_session_lookup(pattern, season)

        # Verify 'race' is in the lookup
        from playbook.utils import normalize_token

        assert lookup.get_direct(normalize_token("Race")) == "Race"
        assert lookup.get_direct(normalize_token("race")) == "Race"

    def test_generic_practice_alias_added_to_lookup(self) -> None:
        """Generic 'practice' alias should be added to session lookup."""
        pattern = PatternConfig(
            regex=r"(?i)^.*\.(?P<session>Race|Practice).*\.mkv$",
            priority=10,
        )
        season = self.build_empty_season()

        lookup = _build_session_lookup(pattern, season)

        from playbook.utils import normalize_token

        assert lookup.get_direct(normalize_token("Practice")) == "Practice"
        assert lookup.get_direct(normalize_token("Free Practice")) == "Practice"

    def test_generic_qualifying_alias_added_to_lookup(self) -> None:
        """Generic 'qualifying' alias should be added to session lookup."""
        pattern = PatternConfig(
            regex=r"(?i)^.*\.(?P<session>Qualifying|Quali).*\.mkv$",
            priority=10,
        )
        season = self.build_empty_season()

        lookup = _build_session_lookup(pattern, season)

        from playbook.utils import normalize_token

        assert lookup.get_direct(normalize_token("Qualifying")) == "Qualifying"
        assert lookup.get_direct(normalize_token("Quali")) == "Qualifying"

    def test_pattern_specific_aliases_take_precedence(self) -> None:
        """Pattern-specific session_aliases should override generic defaults."""
        pattern = PatternConfig(
            regex=r"(?i)^.*\.(?P<session>Race|Practice).*\.mkv$",
            priority=10,
            session_aliases={
                "Grand Prix Race": ["Race", "Main Race"],
            },
        )
        season = self.build_empty_season()

        lookup = _build_session_lookup(pattern, season)

        from playbook.utils import normalize_token

        # Pattern-specific alias should resolve to "Grand Prix Race"
        assert lookup.get_direct(normalize_token("Race")) == "Grand Prix Race"
        assert lookup.get_direct(normalize_token("Main Race")) == "Grand Prix Race"


class TestResolveSessionLookupFuzzy:
    """Tests for _resolve_session_lookup fuzzy matching behavior."""

    def test_exact_match_returns_immediately(self) -> None:
        """Exact match should return without fuzzy matching."""
        from playbook.session_index import SessionLookupIndex
        from playbook.utils import normalize_token

        lookup = SessionLookupIndex()
        lookup.add(normalize_token("Race"), "Race")
        lookup.add(normalize_token("Practice"), "Practice")

        result = _resolve_session_lookup(lookup, normalize_token("Race"))
        assert result == "Race"

    def test_fuzzy_match_with_typo(self) -> None:
        """Fuzzy matching should handle minor typos (Damerau-Levenshtein distance <= 1)."""
        from playbook.session_index import SessionLookupIndex
        from playbook.utils import normalize_token

        lookup = SessionLookupIndex()
        lookup.add(normalize_token("Qualifying"), "Qualifying")

        # "qualifyng" is "qualifying" with one character missing
        result = _resolve_session_lookup(lookup, normalize_token("qualifyng"))
        assert result == "Qualifying"

    def test_short_tokens_skip_fuzzy_matching(self) -> None:
        """Tokens shorter than 4 characters should not fuzzy match."""
        from playbook.session_index import SessionLookupIndex
        from playbook.utils import normalize_token

        lookup = SessionLookupIndex()
        lookup.add(normalize_token("Race"), "Race")

        # "rac" is too short for fuzzy matching
        result = _resolve_session_lookup(lookup, "rac")
        assert result is None

    def test_no_match_for_completely_different_token(self) -> None:
        """Completely different tokens should not match."""
        from playbook.session_index import SessionLookupIndex
        from playbook.utils import normalize_token

        lookup = SessionLookupIndex()
        lookup.add(normalize_token("Qualifying"), "Qualifying")

        # "freeswimming" is completely different from "qualifying"
        result = _resolve_session_lookup(lookup, normalize_token("freeswimming"))
        assert result is None


class TestGenericSessionFileMatching:
    """Integration tests for file matching with generic session terms.

    Tests end-to-end file matching where generic session names like "Race",
    "Practice", and "Qualifying" should resolve to episodes via the round-based
    fallback mechanism.
    """

    def build_indycar_sport(self) -> SportConfig:
        """Build IndyCar sport config with round-based fallback."""
        pattern = PatternConfig(
            regex=r"(?i)^IndyCar\.Series\.(?P<year>\d{4})\.Round(?P<round>\d{2})\.(?P<location>[^.]+)\.(?P<session>Race|Practice|Qualifying)\..*\.mkv$",
            season_selector=SeasonSelector(mode="round", group="round"),
            episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
            priority=10,
        )
        return SportConfig(
            id="indycar",
            name="IndyCar Series",
            metadata=MetadataConfig(url="https://example.com"),
            patterns=[pattern],
            destination=DestinationTemplates(),
        )

    def build_indycar_show(self) -> tuple[Show, Season]:
        """Build IndyCar show with realistic episodes."""
        episode = Episode(
            title="Snap-on Milwaukee Mile 250",
            summary=None,
            originally_available=dt.date(2025, 8, 17),
            index=16,
        )

        season = Season(
            key="2025",
            title="2025 Season",
            summary=None,
            index=1,
            episodes=[episode],
            display_number=1,
            round_number=16,
        )

        show = Show(key="indycar", title="NTT IndyCar Series", summary=None, seasons=[season])
        return show, season

    def test_generic_race_session_resolves_via_round_fallback(self) -> None:
        """Generic 'Race' session should resolve to episode via round-based fallback."""
        sport = self.build_indycar_sport()
        show, season = self.build_indycar_show()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "IndyCar.Series.2025.Round16.Milwaukee.Race.STAN.WEB-DL.1080p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Generic 'Race' session should resolve via round fallback"
        assert result["season"] is season
        assert result["episode"].title == "Snap-on Milwaukee Mile 250"

    def test_generic_practice_session_resolves_via_round_fallback(self) -> None:
        """Generic 'Practice' session should resolve to episode via round-based fallback."""
        sport = self.build_indycar_sport()
        show, season = self.build_indycar_show()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "IndyCar.Series.2025.Round16.Milwaukee.Practice.STAN.WEB-DL.1080p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Generic 'Practice' session should resolve via round fallback"
        assert result["episode"].title == "Snap-on Milwaukee Mile 250"

    def test_generic_qualifying_session_resolves_via_round_fallback(self) -> None:
        """Generic 'Qualifying' session should resolve to episode via round-based fallback."""
        sport = self.build_indycar_sport()
        show, season = self.build_indycar_show()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "IndyCar.Series.2025.Round16.Milwaukee.Qualifying.STAN.WEB-DL.1080p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Generic 'Qualifying' session should resolve via round fallback"
        assert result["episode"].title == "Snap-on Milwaukee Mile 250"

    def test_fuzzy_location_matching_with_generic_session(self) -> None:
        """Location fuzzy matching should work with generic session terms.

        This tests the complete flow:
        1. Pattern extracts location='Milwaukee' and session='Race'
        2. 'Race' doesn't match episode title 'Snap-on Milwaukee Mile 250'
        3. Round-based fallback finds episode with matching round number
        4. Location fuzzy matching confirms 'Milwaukee' is in episode title
        """
        sport = self.build_indycar_sport()
        show, season = self.build_indycar_show()
        patterns = compile_patterns(sport)

        trace: dict[str, object] = {}
        result = match_file_to_episode(
            "IndyCar.Series.2025.Round16.Milwaukee.Race.STAN.WEB-DL.1080p.mkv",
            sport,
            show,
            patterns,
            trace=trace,
        )

        assert result is not None
        assert result["episode"].title == "Snap-on Milwaukee Mile 250"
        # Verify the trace shows a successful match
        assert trace.get("status") == "matched"


def test_generic_session_aliases_are_configured() -> None:
    """Verify generic session aliases are configured in _DEFAULT_GENERIC_SESSION_ALIASES."""
    # This is a simple sanity test to verify the generic session configuration exists
    assert "Race" in _DEFAULT_GENERIC_SESSION_ALIASES
    assert "Practice" in _DEFAULT_GENERIC_SESSION_ALIASES
    assert "Qualifying" in _DEFAULT_GENERIC_SESSION_ALIASES
    assert "Sprint" in _DEFAULT_GENERIC_SESSION_ALIASES

    # Verify each has at least one alias
    for canonical, aliases in _DEFAULT_GENERIC_SESSION_ALIASES.items():
        assert len(aliases) >= 1, f"{canonical} should have at least one alias"


def test_generic_session_lookup_resolves_common_terms() -> None:
    """Test that generic session lookup correctly resolves common motorsport terms."""
    from playbook.session_index import SessionLookupIndex
    from playbook.utils import normalize_token

    # Build a lookup index with generic session aliases
    pattern = PatternConfig(
        regex=r"(?i)^.*\.(?P<session>.+)\.mkv$",
        priority=10,
    )

    episode = Episode(
        title="Grand Prix",
        summary=None,
        originally_available=dt.date(2025, 1, 1),
        index=1,
    )
    season = Season(
        key="2025",
        title="2025 Season",
        summary=None,
        index=1,
        episodes=[episode],
        display_number=1,
    )

    lookup = _build_session_lookup(pattern, season)

    # Test that common session terms resolve correctly
    assert lookup.get_direct(normalize_token("Race")) == "Race"
    assert lookup.get_direct(normalize_token("Practice")) == "Practice"
    assert lookup.get_direct(normalize_token("Qualifying")) == "Qualifying"
    assert lookup.get_direct(normalize_token("Sprint")) == "Sprint"


class TestGenericSessionAliasNormalization:
    """Tests for session alias normalization handling various input formats."""

    def test_mainrace_normalized_to_race(self) -> None:
        """'mainrace' (no space) should normalize to match 'Main Race' alias."""
        pattern = PatternConfig(
            regex=r"(?i)^.*\.(?P<session>.+)\.mkv$",
            priority=10,
        )

        episode = Episode(
            title="Grand Prix",
            summary=None,
            originally_available=dt.date(2025, 1, 1),
            index=1,
        )
        season = Season(
            key="2025",
            title="2025 Season",
            summary=None,
            index=1,
            episodes=[episode],
            display_number=1,
        )

        lookup = _build_session_lookup(pattern, season)

        from playbook.utils import normalize_token

        # Both "mainrace" and "Main Race" should normalize to the same key
        mainrace_normalized = normalize_token("mainrace")
        main_race_normalized = normalize_token("Main Race")

        # They should be equivalent after normalization
        assert mainrace_normalized == main_race_normalized

        # And should resolve to "Race" canonical name
        assert lookup.get_direct(mainrace_normalized) == "Race"

    def test_featurerace_normalized_to_race(self) -> None:
        """'featurerace' should normalize to match 'Feature Race' alias."""
        pattern = PatternConfig(
            regex=r"(?i)^.*\.(?P<session>.+)\.mkv$",
            priority=10,
        )

        episode = Episode(
            title="Grand Prix",
            summary=None,
            originally_available=dt.date(2025, 1, 1),
            index=1,
        )
        season = Season(
            key="2025",
            title="2025 Season",
            summary=None,
            index=1,
            episodes=[episode],
            display_number=1,
        )

        lookup = _build_session_lookup(pattern, season)

        from playbook.utils import normalize_token

        featurerace_normalized = normalize_token("featurerace")
        assert lookup.get_direct(featurerace_normalized) == "Race"

    def test_freepractice_normalized_to_practice(self) -> None:
        """'freepractice' should normalize to match 'Free Practice' alias."""
        pattern = PatternConfig(
            regex=r"(?i)^.*\.(?P<session>.+)\.mkv$",
            priority=10,
        )

        episode = Episode(
            title="Grand Prix",
            summary=None,
            originally_available=dt.date(2025, 1, 1),
            index=1,
        )
        season = Season(
            key="2025",
            title="2025 Season",
            summary=None,
            index=1,
            episodes=[episode],
            display_number=1,
        )

        lookup = _build_session_lookup(pattern, season)

        from playbook.utils import normalize_token

        freepractice_normalized = normalize_token("freepractice")
        assert lookup.get_direct(freepractice_normalized) == "Practice"

    def test_sprintrace_normalized_to_sprint(self) -> None:
        """'sprintrace' should normalize to match 'Sprint Race' alias."""
        pattern = PatternConfig(
            regex=r"(?i)^.*\.(?P<session>.+)\.mkv$",
            priority=10,
        )

        episode = Episode(
            title="Grand Prix",
            summary=None,
            originally_available=dt.date(2025, 1, 1),
            index=1,
        )
        season = Season(
            key="2025",
            title="2025 Season",
            summary=None,
            index=1,
            episodes=[episode],
            display_number=1,
        )

        lookup = _build_session_lookup(pattern, season)

        from playbook.utils import normalize_token

        sprintrace_normalized = normalize_token("sprintrace")
        assert lookup.get_direct(sprintrace_normalized) == "Sprint"


# ========================== NBA Dot-Separated Format Tests ==========================


class TestNBADotSeparatedFormat:
    """Tests for NBA team name resolution with dot-separated filename formats.

    NBA files often have patterns like:
    - NBA.RS.2024.Denver.Nuggets.vs.LA.Clippers.22.12.mkv
    - NBA.Regular.Season.2024.12.22.denver.nuggets.vs.la.clippers.mkv

    These tests verify that team names with dots/spaces are properly normalized
    and resolved through the alias system.
    """

    def test_laclippers_alias_resolves(self) -> None:
        """Verify 'laclippers' (dot-removed format) resolves to Los Angeles Clippers."""
        alias_map = get_team_alias_map("nba")

        # 'laclippers' should resolve to full team name
        assert alias_map.get("laclippers") == "Los Angeles Clippers", (
            "'laclippers' should resolve to 'Los Angeles Clippers'"
        )

    def test_la_alias_resolves(self) -> None:
        """Verify 'la' alias resolves to Los Angeles Clippers."""
        alias_map = get_team_alias_map("nba")

        # 'la' should resolve to Clippers (as added in subtask-5-1)
        assert alias_map.get("la") == "Los Angeles Clippers", (
            "'la' should resolve to 'Los Angeles Clippers'"
        )

    def test_denvernuggets_normalized_resolves(self) -> None:
        """Verify 'denvernuggets' (dot-removed format) resolves correctly."""
        alias_map = get_team_alias_map("nba")

        # 'denvernuggets' should resolve via city+nickname combination
        assert alias_map.get("denvernuggets") == "Denver Nuggets", (
            "'denvernuggets' should resolve to 'Denver Nuggets'"
        )

    def test_dot_separated_team_names_normalize_correctly(self) -> None:
        """Verify that dot-separated team names normalize to resolve correctly.

        When filenames have 'Denver.Nuggets', the normalize_token function
        strips dots, producing 'denvernuggets' which should then resolve.
        """
        from playbook.utils import normalize_token

        alias_map = get_team_alias_map("nba")

        # Simulate what happens with dot-separated input
        denver_nuggets_normalized = normalize_token("Denver.Nuggets")
        la_clippers_normalized = normalize_token("LA.Clippers")

        # Normalized tokens should be alphanumeric only
        assert denver_nuggets_normalized == "denvernuggets"
        assert la_clippers_normalized == "laclippers"

        # And should resolve to correct teams
        assert alias_map.get(denver_nuggets_normalized) == "Denver Nuggets"
        assert alias_map.get(la_clippers_normalized) == "Los Angeles Clippers"

    def test_nba_file_matching_with_dot_separated_teams(self) -> None:
        """Integration test for NBA file matching with dot-separated team names.

        This tests the full flow:
        1. Filename has 'Denver.Nuggets.vs.LA.Clippers' format
        2. Pattern extracts team names
        3. Team aliases resolve to canonical names
        4. Correct episode is matched by date + teams
        """
        # Create NBA pattern that extracts teams
        pattern = PatternConfig(
            regex=(
                r"(?i)^NBA[\s._-]+RS[\s._-]+(?P<date_year>\d{4})[\s._-]+"
                r"(?P<session>(?P<away>[A-Za-z.]+[\s._-]+[A-Za-z.]+)[\s._-]+vs[\s._-]+"
                r"(?P<home>[A-Za-z.]+[\s._-]+[A-Za-z.]+))[\s._-]+"
                r"(?P<day>\d{2})[\s._-]+(?P<month>\d{2}).*\.mkv$"
            ),
            season_selector=SeasonSelector(
                mode="date", value_template="{date_year}-{month:0>2}-{day:0>2}"
            ),
            episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
            priority=10,
        )

        sport = SportConfig(
            id="nba",
            name="NBA",
            metadata=MetadataConfig(url="https://example.com"),
            patterns=[pattern],
            destination=DestinationTemplates(),
        )

        # Create NBA show with the expected game
        episode = Episode(
            title="Denver Nuggets vs Los Angeles Clippers",
            summary=None,
            originally_available=dt.date(2024, 12, 22),
            index=1,
        )

        season = Season(
            key="week10",
            title="Week 10",
            summary=None,
            index=10,
            episodes=[episode],
            display_number=10,
        )

        show = Show(key="nba", title="NBA", summary=None, seasons=[season])

        patterns = compile_patterns(sport)

        # Test with dot-separated filename
        result = match_file_to_episode(
            "NBA.RS.2024.Denver.Nuggets.vs.LA.Clippers.22.12.720p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Should match NBA file with dot-separated team names"
        assert result["episode"].title == "Denver Nuggets vs Los Angeles Clippers"
        assert result["episode"].originally_available == dt.date(2024, 12, 22)

    def test_nba_structured_match_with_dot_separated_teams(self) -> None:
        """Test structured matching for NBA with dot-separated team names.

        This tests the _score_structured_match function specifically with
        team names that come from dot-separated filenames.
        """
        # Create episode for Denver Nuggets vs LA Clippers
        episode = Episode(
            title="Denver Nuggets vs Los Angeles Clippers",
            summary=None,
            originally_available=dt.date(2024, 12, 22),
            index=1,
        )

        season = Season(
            key="week10",
            title="Week 10",
            summary=None,
            index=10,
            episodes=[episode],
        )

        show = Show(key="nba", title="NBA", summary=None, seasons=[season])

        # Build alias lookup
        alias_lookup = _build_team_alias_lookup(show, {})

        # Create structured name as if parsed from "NBA.RS.2024.Denver.Nuggets.vs.LA.Clippers.22.12.mkv"
        structured = StructuredName(
            raw="NBA RS 2024 Denver Nuggets vs LA Clippers 22 12",
            date=dt.date(2024, 12, 22),
            teams=["Denver Nuggets", "LA Clippers"],  # As parsed (before full alias resolution)
        )

        # Score should be positive - teams should match via aliases
        score = _score_structured_match(structured, season, episode, alias_lookup)

        assert score > 0, (
            f"Expected positive score for Denver Nuggets vs LA Clippers match, got {score}. "
            "LA Clippers should resolve to Los Angeles Clippers via alias."
        )

    def test_all_la_team_aliases_present(self) -> None:
        """Verify LA team aliases are comprehensive for both Lakers and Clippers."""
        alias_map = get_team_alias_map("nba")

        # Lakers aliases
        assert alias_map.get("lakers") == "Los Angeles Lakers"
        assert alias_map.get("lal") == "Los Angeles Lakers"
        assert alias_map.get("losangeleslakers") == "Los Angeles Lakers"

        # Clippers aliases (including new ones from subtask-5-1)
        assert alias_map.get("clippers") == "Los Angeles Clippers"
        assert alias_map.get("lac") == "Los Angeles Clippers"
        assert alias_map.get("losangelesclippers") == "Los Angeles Clippers"
        assert alias_map.get("laclippers") == "Los Angeles Clippers"


class TestNBAIntegrationDateAndTeams:
    """Integration tests for NBA matching with both date and team resolution.

    These tests verify the complete flow for NBA Regular Season files where:
    1. Date is used for season selection
    2. Team names (potentially dot-separated) are used for episode matching
    3. Aliases resolve abbreviated/normalized team names to canonical forms
    """

    def build_nba_sport_config(self) -> SportConfig:
        """Build NBA sport config with realistic pattern."""
        pattern = PatternConfig(
            regex=(
                r"(?i)^NBA[\s._-]+(?:RS|Regular[\s._-]+Season)[\s._-]+"
                r"(?P<date_year>\d{4})[\s._-]+(?P<month>\d{2})[\s._-]+(?P<day>\d{2})[\s._-]+"
                r"(?P<session>(?P<away>[A-Za-z ]+)[\s._-]+vs[\s._-]+(?P<home>[A-Za-z ]+)).*\.mkv$"
            ),
            season_selector=SeasonSelector(
                mode="date", value_template="{date_year}-{month:0>2}-{day:0>2}"
            ),
            episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
            priority=10,
        )
        return SportConfig(
            id="nba",
            name="NBA",
            metadata=MetadataConfig(url="https://example.com"),
            patterns=[pattern],
            destination=DestinationTemplates(),
        )

    def build_nba_show_with_clippers_games(self) -> Show:
        """Build NBA show with LA Clippers games."""
        # Game 1: Nuggets vs Clippers (Dec 22)
        game1 = Episode(
            title="Denver Nuggets vs Los Angeles Clippers",
            summary=None,
            originally_available=dt.date(2024, 12, 22),
            index=1,
        )
        # Game 2: Clippers vs Lakers (Dec 25)
        game2 = Episode(
            title="Los Angeles Clippers vs Los Angeles Lakers",
            summary=None,
            originally_available=dt.date(2024, 12, 25),
            index=2,
        )

        season = Season(
            key="2024-2025",
            title="2024-2025 Season",
            summary=None,
            index=1,
            episodes=[game1, game2],
            display_number=1,
        )

        return Show(key="nba", title="NBA", summary=None, seasons=[season])

    def test_nba_nuggets_vs_clippers_matches_correctly(self) -> None:
        """Verify Denver Nuggets vs LA Clippers file matches correct episode."""
        sport = self.build_nba_sport_config()
        show = self.build_nba_show_with_clippers_games()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "NBA RS 2024 12 22 Denver Nuggets vs LA Clippers 720p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Should match Nuggets vs Clippers file"
        assert result["episode"].title == "Denver Nuggets vs Los Angeles Clippers"
        assert result["episode"].originally_available == dt.date(2024, 12, 22)

    def test_nba_clippers_vs_lakers_matches_correctly(self) -> None:
        """Verify LA Clippers vs LA Lakers file matches correct episode."""
        sport = self.build_nba_sport_config()
        show = self.build_nba_show_with_clippers_games()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "NBA RS 2024 12 25 LA Clippers vs LA Lakers 720p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Should match Clippers vs Lakers file"
        assert result["episode"].title == "Los Angeles Clippers vs Los Angeles Lakers"
        assert result["episode"].originally_available == dt.date(2024, 12, 25)

    def test_nba_team_disambiguation_by_date(self) -> None:
        """Verify that date helps disambiguate when team names could match multiple games.

        LA Clippers appear in both games, but date should select the correct one.
        """
        sport = self.build_nba_sport_config()
        show = self.build_nba_show_with_clippers_games()
        patterns = compile_patterns(sport)

        # Dec 22 file should match game 1 (Nuggets vs Clippers)
        result1 = match_file_to_episode(
            "NBA RS 2024 12 22 Denver Nuggets vs LA Clippers 720p.mkv",
            sport,
            show,
            patterns,
        )

        # Dec 25 file should match game 2 (Clippers vs Lakers)
        result2 = match_file_to_episode(
            "NBA RS 2024 12 25 LA Clippers vs LA Lakers 720p.mkv",
            sport,
            show,
            patterns,
        )

        assert result1 is not None
        assert result2 is not None

        # Should be different episodes despite both having Clippers
        assert result1["episode"].index != result2["episode"].index
        assert result1["episode"].index == 1  # Nuggets vs Clippers
        assert result2["episode"].index == 2  # Clippers vs Lakers


# ========================== UEFA Champions League Integration Tests ==========================


class TestUEFAChampionsLeagueIntegration:
    """Integration tests for UEFA Champions League file resolution.

    These tests verify that abbreviated team names (MC, Borussia, PSG, etc.)
    resolve correctly to their full canonical names using the UEFA team alias
    system. This addresses the issue where files like:
        UEFA.Champions.League.2025.MC.vs.Borussia.1080pEN50fps.mkv
    failed to resolve because 'MC' and 'Borussia' couldn't match episode titles.
    """

    def build_uefa_sport_config(self) -> SportConfig:
        """Build UEFA Champions League sport config with team matching pattern."""
        pattern = PatternConfig(
            regex=(
                r"(?i)^UEFA[\s._-]+Champions[\s._-]+League[\s._-]+"
                r"(?P<date_year>\d{4})[\s._-]+"
                r"(?P<session>(?P<home>[A-Za-z ]+)[\s._-]+vs[\s._-]+(?P<away>[A-Za-z ]+))"
                r"[\s._-]*.*\.mkv$"
            ),
            season_selector=SeasonSelector(mode="key", value_template="{date_year}"),
            episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
            priority=10,
        )
        return SportConfig(
            id="uefa_champions_league",
            name="UEFA Champions League",
            metadata=MetadataConfig(url="https://example.com"),
            patterns=[pattern],
            destination=DestinationTemplates(),
            team_alias_map="uefa_champions_league",
        )

    def build_uefa_show_with_matches(self) -> Show:
        """Build UEFA CL show with typical group stage matches."""
        # Match 1: Manchester City vs Borussia Dortmund (the file from the spec)
        match1 = Episode(
            title="Manchester City vs Borussia Dortmund",
            summary=None,
            originally_available=dt.date(2025, 10, 22),
            index=1,
        )
        # Match 2: Paris Saint-Germain vs Bayern Munich
        match2 = Episode(
            title="Paris Saint-Germain vs Bayern Munich",
            summary=None,
            originally_available=dt.date(2025, 10, 23),
            index=2,
        )
        # Match 3: Real Madrid vs Inter Milan
        match3 = Episode(
            title="Real Madrid vs Inter Milan",
            summary=None,
            originally_available=dt.date(2025, 10, 24),
            index=3,
        )
        # Match 4: Atlético Madrid vs Union Saint-Gilloise
        match4 = Episode(
            title="Atlético Madrid vs Union Saint-Gilloise",
            summary=None,
            originally_available=dt.date(2025, 10, 25),
            index=4,
        )

        season = Season(
            key="2025",
            title="2025 Group Stage",
            summary=None,
            index=1,
            episodes=[match1, match2, match3, match4],
            display_number=1,
        )

        return Show(
            key="uefa_champions_league",
            title="UEFA Champions League",
            summary=None,
            seasons=[season],
        )

    def test_uefa_integration_mc_vs_borussia_resolves(self) -> None:
        """Integration test: MC vs Borussia resolves to Manchester City vs Borussia Dortmund.

        This is the primary test case from the spec where abbreviated team names
        in the filename need to resolve to canonical episode titles.
        """
        sport = self.build_uefa_sport_config()
        show = self.build_uefa_show_with_matches()
        patterns = compile_patterns(sport)

        # Test with the exact filename pattern from the spec
        result = match_file_to_episode(
            "UEFA.Champions.League.2025.MC.vs.Borussia.1080pEN50fps.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, (
            "Should match UEFA Champions League file with abbreviated team names (MC, Borussia)"
        )
        assert result["episode"].title == "Manchester City vs Borussia Dortmund", (
            f"Expected 'Manchester City vs Borussia Dortmund', got '{result['episode'].title}'"
        )

    def test_uefa_integration_psg_vs_bayern_resolves(self) -> None:
        """Integration test: PSG vs Bayern resolves to Paris Saint-Germain vs Bayern Munich."""
        sport = self.build_uefa_sport_config()
        show = self.build_uefa_show_with_matches()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "UEFA.Champions.League.2025.PSG.vs.Bayern.1080p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, (
            "Should match UEFA Champions League file with PSG and Bayern abbreviations"
        )
        assert result["episode"].title == "Paris Saint-Germain vs Bayern Munich"

    def test_uefa_integration_real_vs_inter_resolves(self) -> None:
        """Integration test: Real vs Inter resolves to Real Madrid vs Inter Milan."""
        sport = self.build_uefa_sport_config()
        show = self.build_uefa_show_with_matches()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "UEFA.Champions.League.2025.Real.vs.Inter.720p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, (
            "Should match UEFA Champions League file with Real and Inter abbreviations"
        )
        assert result["episode"].title == "Real Madrid vs Inter Milan"

    def test_uefa_integration_german_club_abbreviation_resolves(self) -> None:
        """Integration test: BVB vs BAY resolves to Borussia Dortmund vs Bayern Munich.

        Uses standard German club abbreviations BVB and BAY which are registered aliases.
        """
        sport = self.build_uefa_sport_config()
        # Add a BVB vs Bayern match for testing
        match = Episode(
            title="Borussia Dortmund vs Bayern Munich",
            summary=None,
            originally_available=dt.date(2025, 11, 5),
            index=5,
        )
        show = self.build_uefa_show_with_matches()
        show.seasons[0].episodes.append(match)
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "UEFA.Champions.League.2025.BVB.vs.BAY.1080p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, (
            "Should match UEFA Champions League file with BVB and BAY abbreviations"
        )
        assert result["episode"].title == "Borussia Dortmund vs Bayern Munich"

    def test_uefa_integration_full_team_names_still_work(self) -> None:
        """Integration test: Full team names should still match correctly."""
        sport = self.build_uefa_sport_config()
        show = self.build_uefa_show_with_matches()
        patterns = compile_patterns(sport)

        result = match_file_to_episode(
            "UEFA.Champions.League.2025.Manchester City.vs.Borussia Dortmund.1080p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, "Should match with full team names"
        assert result["episode"].title == "Manchester City vs Borussia Dortmund"

    def test_uefa_integration_mixed_abbreviation_formats(self) -> None:
        """Integration test: Various abbreviation formats resolve correctly.

        Tests that different filename separators and case variations work.
        """
        sport = self.build_uefa_sport_config()
        show = self.build_uefa_show_with_matches()
        patterns = compile_patterns(sport)

        # Test with underscore separators and different case
        result = match_file_to_episode(
            "UEFA_Champions_League_2025_mc_vs_borussia_720p.mkv",
            sport,
            show,
            patterns,
        )

        assert result is not None, (
            "Should match with underscore separators and lowercase abbreviations"
        )
        assert result["episode"].title == "Manchester City vs Borussia Dortmund"


def test_uefa_integration_alias_resolution() -> None:
    """Standalone integration test for UEFA alias resolution.

    This is a comprehensive test verifying the full alias resolution chain:
    filename -> pattern match -> team alias lookup -> episode match.
    """
    # Create pattern matching UEFA CL filename format
    pattern = PatternConfig(
        regex=(
            r"(?i)^UEFA[\s._-]+Champions[\s._-]+League[\s._-]+"
            r"(?P<date_year>\d{4})[\s._-]+"
            r"(?P<session>(?P<home>[A-Za-z]+)[\s._-]+vs[\s._-]+(?P<away>[A-Za-z]+))"
            r".*\.mkv$"
        ),
        season_selector=SeasonSelector(mode="key", value_template="{date_year}"),
        episode_selector=EpisodeSelector(group="session", allow_fallback_to_title=True),
        priority=10,
    )

    sport = SportConfig(
        id="uefa_champions_league",
        name="UEFA Champions League",
        metadata=MetadataConfig(url="https://example.com"),
        patterns=[pattern],
        destination=DestinationTemplates(),
        team_alias_map="uefa_champions_league",
    )

    # Create season with the episode
    season = Season(
        key="2025",
        title="2025",
        summary=None,
        index=1,
        episodes=[
            Episode(
                title="Manchester City vs Borussia Dortmund",
                summary=None,
                originally_available=dt.date(2025, 10, 22),
                index=1,
            ),
        ],
        display_number=1,
    )

    show = Show(
        key="uefa_champions_league",
        title="UEFA Champions League",
        summary=None,
        seasons=[season],
    )

    patterns = compile_patterns(sport)

    # Test the EXACT problematic filename from the spec
    filename = "UEFA.Champions.League.2025.MC.vs.Borussia.1080pEN50fps.mkv"

    trace: dict[str, object] = {}
    result = match_file_to_episode(
        filename,
        sport,
        show,
        patterns,
        trace=trace,
    )

    # Verify the match succeeded
    assert result is not None, (
        f"Failed to match UEFA file: {filename}\n"
        f"Trace: {trace}"
    )

    # Verify correct episode matched
    assert result["season"].key == "2025"
    assert result["episode"].title == "Manchester City vs Borussia Dortmund"

    # Verify no warnings were generated
    diagnostics: list[tuple[str, str]] = []
    result_with_diag = match_file_to_episode(
        filename,
        sport,
        show,
        patterns,
        diagnostics=diagnostics,
    )
    assert result_with_diag is not None
    assert len([d for d in diagnostics if d[0] == "warning"]) == 0, (
        f"Unexpected warnings: {diagnostics}"
    )
