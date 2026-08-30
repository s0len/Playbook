"""Pins the shipped sport definitions in pattern_templates.yaml.

These assertions exist because the season-resolution behaviour is carried entirely by
data, not code: a sport pointing at the wrong TVSportsDB show, or regaining a `year:`
key, silently breaks a whole competition while every other test stays green.
"""

from __future__ import annotations

from playbook.config import _expand_sport_variants
from playbook.pattern_templates import load_default_sports


def _variants() -> dict[str, dict]:
    expanded: dict[str, dict] = {}
    for sport in load_default_sports():
        for variant in _expand_sport_variants(sport):
            expanded[variant["id"]] = variant
    return expanded


# Competitions whose season straddles a calendar year cannot pick a show from the captured
# year alone, so they must NOT carry a variant_year - every season show stays a candidate
# and the fixture date decides. The suffix is the season's starting year.
DATE_RESOLVED_SHOWS = {
    "premier_league_2025": "english-premier-league-2025-2026",
    "premier_league_2026": "english-premier-league-2026-2027",
    "uefa_champions_league_2025": "uefa-champions-league-2025-2026",
    "uefa_champions_league_2026": "uefa-champions-league-2026-2027",
    "nfl_2025": "nfl-2025",
    "nfl_2026": "nfl-2026",
    "nba_2025": "nba-2025-2026",
    "nba_2026": "nba-2026-2027",
}


def test_date_resolved_sports_point_at_the_right_shows() -> None:
    variants = _variants()
    resolved = {sport_id: variants[sport_id]["show_slug"] for sport_id in DATE_RESOLVED_SHOWS if sport_id in variants}
    assert resolved == DATE_RESOLVED_SHOWS


def test_date_resolved_sports_do_not_pin_a_variant_year() -> None:
    variants = _variants()
    pinned = {
        sport_id: variants[sport_id]["variant_year"]
        for sport_id in DATE_RESOLVED_SHOWS
        if variants.get(sport_id, {}).get("variant_year") is not None
    }
    assert pinned == {}, (
        f"These sports regained a 'year:' key, which pins them to one show per calendar "
        f"year and breaks the season that straddles it: {pinned}"
    )


def test_nhl_is_still_held_back_from_the_2026_27_show() -> None:
    """nhl-2026-2027 season 0 duplicates the entire regular season upstream.

    Offering it as a candidate makes ~411 fixtures ambiguous. Flip this test together
    with pattern_templates.yaml once the duplicate season is gone.
    """
    variants = _variants()
    assert variants["nhl_2026"]["show_slug"] == "nhl-2025-2026"


def test_variant_ids_are_stable() -> None:
    """Sport ids key persisted rows in processed_files; renaming one orphans its history."""
    variants = _variants()
    for sport_id in DATE_RESOLVED_SHOWS:
        assert sport_id in variants, f"{sport_id} disappeared - persisted rows would be orphaned"


def test_no_default_sport_resolves_to_an_empty_slug() -> None:
    for sport_id, variant in _variants().items():
        assert variant.get("show_slug") or variant.get("show_slug_template"), (
            f"{sport_id} has neither show_slug nor show_slug_template"
        )
