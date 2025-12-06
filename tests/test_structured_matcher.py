from __future__ import annotations

import datetime as dt

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

