from __future__ import annotations

import pytest

from playbook.team_aliases import (
    _build_alias_map,
    get_team_alias_map,
)


# Tests for private helper function


class TestBuildAliasMap:
    """Tests for _build_alias_map helper function."""

    def test_canonical_name_normalization(self):
        """Test that canonical names are stripped and normalized."""
        entries = {
            "Boston Bruins": ["Bruins"],
            "  Toronto Maple Leafs  ": ["Leafs"],
        }
        result = _build_alias_map(entries)

        # Canonical names should be normalized (lowercase, no spaces/special chars)
        # "Boston Bruins" -> "bostonbruins"
        # "Toronto Maple Leafs" -> "torontomapleleafs"
        assert "bostonbruins" in result
        assert "torontomapleleafs" in result

        # Values should be the stripped canonical name
        assert result["bostonbruins"] == "Boston Bruins"
        assert result["torontomapleleafs"] == "Toronto Maple Leafs"

    def test_alias_normalization_and_mapping(self):
        """Test that aliases are normalized and map to canonical names."""
        entries = {
            "Boston Bruins": ["Bruins", "Boston", "BOS"],
            "Toronto Maple Leafs": ["Leafs", "Toronto", "TOR"],
        }
        result = _build_alias_map(entries)

        # All aliases should normalize and map to their canonical names
        # "Bruins" -> "bruins" -> "Boston Bruins"
        assert result["bruins"] == "Boston Bruins"
        assert result["boston"] == "Boston Bruins"
        assert result["bos"] == "Boston Bruins"

        assert result["leafs"] == "Toronto Maple Leafs"
        assert result["toronto"] == "Toronto Maple Leafs"
        assert result["tor"] == "Toronto Maple Leafs"

    def test_empty_whitespace_handling(self):
        """Test that empty or whitespace-only aliases are skipped."""
        entries = {
            "Boston Bruins": ["Bruins", "", "  ", "BOS"],
            "Toronto Maple Leafs": ["", "Leafs"],
        }
        result = _build_alias_map(entries)

        # Empty/whitespace aliases should be skipped
        # Only valid aliases should be present
        assert "bruins" in result
        assert "bos" in result
        assert "leafs" in result

        # Empty normalized key should not be in result
        assert "" not in result

    def test_first_defined_canonical_wins_for_duplicates(self):
        """Test that when multiple canonicals normalize to same value, first wins."""
        entries = {
            "St. Louis Blues": ["Blues"],
            "Saint Louis Blues": ["Blues2"],  # Normalizes to same as "St. Louis Blues"
        }
        result = _build_alias_map(entries)

        # Both canonical names normalize to "stlouisblues"
        # The first one defined should win due to setdefault
        normalized_key = "stlouisblues"
        assert normalized_key in result
        assert result[normalized_key] == "St. Louis Blues"

        # The second canonical's alias should still map correctly
        # "Blues2" -> "blues2" -> "Saint Louis Blues"
        assert result["blues2"] == "Saint Louis Blues"

    def test_duplicate_alias_maps_to_first_canonical(self):
        """Test that when same alias appears for multiple teams, first wins."""
        entries = {
            "Boston Bruins": ["Bruins", "BOS"],
            "Buffalo Sabres": ["BOS"],  # Same alias as Boston's BOS
        }
        result = _build_alias_map(entries)

        # "BOS" appears for both teams, first definition should win
        assert result["bos"] == "Boston Bruins"

    def test_complex_normalization_with_special_characters(self):
        """Test normalization handles special characters correctly."""
        entries = {
            "St. Louis Blues": ["Blues", "St Louis", "St. Louis"],
            "Manchester United": ["Man United", "Man Utd", "Man U"],
        }
        result = _build_alias_map(entries)

        # All variations should normalize to same value
        # "St. Louis" -> "stlouis"
        # "St Louis" -> "stlouis"
        assert result["stlouis"] == "St. Louis Blues"

        # "Man United" -> "manunited"
        # "Man Utd" -> "manutd"
        # "Man U" -> "manu"
        assert result["manunited"] == "Manchester United"
        assert result["manutd"] == "Manchester United"
        assert result["manu"] == "Manchester United"

    def test_empty_entries_dict(self):
        """Test that empty entries dict returns empty mapping."""
        result = _build_alias_map({})
        assert result == {}

    def test_canonical_with_empty_aliases_list(self):
        """Test canonical with no aliases still maps to itself."""
        entries = {
            "Boston Bruins": [],
        }
        result = _build_alias_map(entries)

        # Canonical should still map to itself
        assert result["bostonbruins"] == "Boston Bruins"

    def test_case_insensitive_normalization(self):
        """Test that normalization is case-insensitive."""
        entries = {
            "Boston Bruins": ["BRUINS", "Bruins", "bruins"],
        }
        result = _build_alias_map(entries)

        # All case variations should normalize to same key "bruins"
        # Due to setdefault, first one wins but they all point to canonical
        assert result["bruins"] == "Boston Bruins"

        # Should only have one entry for the normalized "bruins" key
        bruins_keys = [k for k in result.keys() if k == "bruins"]
        assert len(bruins_keys) == 1


# Tests for public API


class TestGetTeamAliasMap:
    """Tests for get_team_alias_map function."""

    def test_get_nhl_team_aliases(self):
        """Test that 'nhl' returns NHL team alias map."""
        result = get_team_alias_map("nhl")

        # Should return a non-empty dict
        assert isinstance(result, dict)
        assert len(result) > 0

        # Verify some known NHL teams and aliases
        assert result["bostonbruins"] == "Boston Bruins"
        assert result["bruins"] == "Boston Bruins"
        assert result["bos"] == "Boston Bruins"

        assert result["torontomapleleafs"] == "Toronto Maple Leafs"
        assert result["leafs"] == "Toronto Maple Leafs"
        assert result["tor"] == "Toronto Maple Leafs"

    def test_get_nba_team_aliases(self):
        """Test that 'nba' returns NBA team alias map."""
        result = get_team_alias_map("nba")

        # Should return a non-empty dict
        assert isinstance(result, dict)
        assert len(result) > 0

        # Verify some known NBA teams and aliases
        assert result["losangeleslakers"] == "Los Angeles Lakers"
        assert result["lakers"] == "Los Angeles Lakers"
        assert result["lal"] == "Los Angeles Lakers"

        assert result["goldenstatewarriors"] == "Golden State Warriors"
        assert result["warriors"] == "Golden State Warriors"
        assert result["gsw"] == "Golden State Warriors"

    def test_get_premier_league_team_aliases(self):
        """Test that 'premier_league' returns EPL team alias map."""
        result = get_team_alias_map("premier_league")

        # Should return a non-empty dict
        assert isinstance(result, dict)
        assert len(result) > 0

        # Verify some known EPL teams and aliases
        assert result["manchesterunited"] == "Manchester United"
        assert result["manunited"] == "Manchester United"
        assert result["mun"] == "Manchester United"

        assert result["arsenal"] == "Arsenal"
        assert result["gunners"] == "Arsenal"
        assert result["ars"] == "Arsenal"

    def test_get_uefa_champions_league_team_aliases(self):
        """Test that 'uefa_champions_league' returns UEFA CL team alias map."""
        result = get_team_alias_map("uefa_champions_league")

        # Should return a non-empty dict
        assert isinstance(result, dict)
        assert len(result) > 0

        # Verify some known UEFA CL teams and aliases
        # MC abbreviation should resolve to Manchester City
        assert result["mc"] == "Manchester City"
        assert result["manchestercity"] == "Manchester City"
        assert result["mancity"] == "Manchester City"

        # Borussia should resolve to Borussia Dortmund (first defined wins)
        assert result["borussia"] == "Borussia Dortmund"
        assert result["dortmund"] == "Borussia Dortmund"
        assert result["bvb"] == "Borussia Dortmund"

        # PSG aliases
        assert result["psg"] == "Paris Saint-Germain"
        assert result["paris"] == "Paris Saint-Germain"

        # Monaco aliases
        assert result["monaco"] == "Monaco"
        assert result["asmonaco"] == "Monaco"
        assert result["asm"] == "Monaco"

    def test_get_team_alias_map_with_none(self):
        """Test that None returns empty dict."""
        result = get_team_alias_map(None)
        assert result == {}

    def test_get_team_alias_map_with_unknown_name(self):
        """Test that unknown league name returns empty dict."""
        result = get_team_alias_map("unknown_league")
        assert result == {}

        result = get_team_alias_map("mlb")
        assert result == {}

        result = get_team_alias_map("")
        assert result == {}

    def test_get_team_alias_map_returns_same_instance(self):
        """Test that multiple calls return the same pre-built map instance."""
        result1 = get_team_alias_map("nhl")
        result2 = get_team_alias_map("nhl")

        # Should be the exact same dict instance (not just equal)
        assert result1 is result2

    def test_get_team_alias_map_different_leagues_are_distinct(self):
        """Test that different league maps are distinct from each other."""
        nhl_map = get_team_alias_map("nhl")
        nba_map = get_team_alias_map("nba")
        epl_map = get_team_alias_map("premier_league")

        # They should be different instances
        assert nhl_map is not nba_map
        assert nhl_map is not epl_map
        assert nba_map is not epl_map

        # They should have different content
        # NHL has Bruins, NBA doesn't
        assert "bruins" in nhl_map
        assert "bruins" not in nba_map

        # NBA has Lakers, NHL doesn't
        assert "lakers" in nba_map
        assert "lakers" not in nhl_map


# Integration tests for team alias resolution correctness


class TestTeamAliasResolution:
    """Integration tests verifying specific team name aliases resolve correctly."""

    # NHL Team Alias Resolution Tests

    def test_nhl_bruins_alias_resolution(self):
        """Test that various Boston Bruins aliases resolve correctly."""
        nhl_map = get_team_alias_map("nhl")

        # Test nickname alias
        assert nhl_map["bruins"] == "Boston Bruins"

        # Test city name alias
        assert nhl_map["boston"] == "Boston Bruins"

        # Test abbreviated code
        assert nhl_map["bos"] == "Boston Bruins"

        # Test full canonical name
        assert nhl_map["bostonbruins"] == "Boston Bruins"

    def test_nhl_maple_leafs_alias_resolution(self):
        """Test that various Toronto Maple Leafs aliases resolve correctly."""
        nhl_map = get_team_alias_map("nhl")

        # Test nickname alias
        assert nhl_map["leafs"] == "Toronto Maple Leafs"
        assert nhl_map["mapleleafs"] == "Toronto Maple Leafs"

        # Test city name alias
        assert nhl_map["toronto"] == "Toronto Maple Leafs"

        # Test abbreviated code
        assert nhl_map["tor"] == "Toronto Maple Leafs"

        # Test full canonical name
        assert nhl_map["torontomapleleafs"] == "Toronto Maple Leafs"

    def test_nhl_golden_knights_alias_resolution(self):
        """Test that various Vegas Golden Knights aliases resolve correctly."""
        nhl_map = get_team_alias_map("nhl")

        # Test nickname alias
        assert nhl_map["goldenknights"] == "Vegas Golden Knights"

        # Test city name alias
        assert nhl_map["vegas"] == "Vegas Golden Knights"

        # Test abbreviated code
        assert nhl_map["vgk"] == "Vegas Golden Knights"

        # Test full canonical name
        assert nhl_map["vegasgoldenknights"] == "Vegas Golden Knights"

    def test_nhl_st_louis_blues_alias_resolution(self):
        """Test that St. Louis Blues aliases with special characters resolve correctly."""
        nhl_map = get_team_alias_map("nhl")

        # Test nickname alias
        assert nhl_map["blues"] == "St. Louis Blues"

        # Test city name variations with special characters
        assert nhl_map["stlouis"] == "St. Louis Blues"
        assert nhl_map["saintlouisblues"] == "St. Louis Blues"
        assert nhl_map["stlouisblues"] == "St. Louis Blues"

        # Test abbreviated code
        assert nhl_map["stl"] == "St. Louis Blues"

    def test_nhl_abbreviated_codes(self):
        """Test that NHL abbreviated codes resolve correctly."""
        nhl_map = get_team_alias_map("nhl")

        # Test various NHL team codes
        assert nhl_map["ana"] == "Anaheim Ducks"
        assert nhl_map["chi"] == "Chicago Blackhawks"
        assert nhl_map["det"] == "Detroit Red Wings"
        assert nhl_map["mtl"] == "Montreal Canadiens"
        assert nhl_map["nyr"] == "New York Rangers"
        assert nhl_map["pit"] == "Pittsburgh Penguins"
        assert nhl_map["sea"] == "Seattle Kraken"
        assert nhl_map["wpg"] == "Winnipeg Jets"

    # NBA Team Alias Resolution Tests

    def test_nba_lakers_alias_resolution(self):
        """Test that various Los Angeles Lakers aliases resolve correctly."""
        nba_map = get_team_alias_map("nba")

        # Test nickname alias
        assert nba_map["lakers"] == "Los Angeles Lakers"

        # Test city name variations
        assert nba_map["lalakers"] == "Los Angeles Lakers"

        # Test abbreviated code
        assert nba_map["lal"] == "Los Angeles Lakers"

        # Test full canonical name
        assert nba_map["losangeleslakers"] == "Los Angeles Lakers"

    def test_nba_warriors_alias_resolution(self):
        """Test that various Golden State Warriors aliases resolve correctly."""
        nba_map = get_team_alias_map("nba")

        # Test nickname alias
        assert nba_map["warriors"] == "Golden State Warriors"
        assert nba_map["dubs"] == "Golden State Warriors"

        # Test city name alias
        assert nba_map["goldenstate"] == "Golden State Warriors"

        # Test abbreviated code
        assert nba_map["gsw"] == "Golden State Warriors"

        # Test full canonical name
        assert nba_map["goldenstatewarriors"] == "Golden State Warriors"

    def test_nba_76ers_alias_resolution(self):
        """Test that Philadelphia 76ers aliases with numbers resolve correctly."""
        nba_map = get_team_alias_map("nba")

        # Test nickname aliases
        assert nba_map["76ers"] == "Philadelphia 76ers"
        assert nba_map["sixers"] == "Philadelphia 76ers"

        # Test city name aliases
        assert nba_map["philadelphia"] == "Philadelphia 76ers"
        assert nba_map["philly"] == "Philadelphia 76ers"

        # Test abbreviated code
        assert nba_map["phi"] == "Philadelphia 76ers"

    def test_nba_abbreviated_codes(self):
        """Test that NBA abbreviated codes resolve correctly."""
        nba_map = get_team_alias_map("nba")

        # Test various NBA team codes
        assert nba_map["atl"] == "Atlanta Hawks"
        assert nba_map["bkn"] == "Brooklyn Nets"
        assert nba_map["chi"] == "Chicago Bulls"
        assert nba_map["dal"] == "Dallas Mavericks"
        assert nba_map["mia"] == "Miami Heat"
        assert nba_map["nyk"] == "New York Knicks"
        assert nba_map["okc"] == "Oklahoma City Thunder"
        assert nba_map["por"] == "Portland Trail Blazers"

    # Premier League Team Alias Resolution Tests

    def test_epl_man_united_alias_resolution(self):
        """Test that various Manchester United aliases resolve correctly."""
        epl_map = get_team_alias_map("premier_league")

        # Test nickname aliases
        assert epl_map["manunited"] == "Manchester United"
        assert epl_map["manutd"] == "Manchester United"
        assert epl_map["manu"] == "Manchester United"

        # Test abbreviated code
        assert epl_map["mun"] == "Manchester United"
        assert epl_map["mufc"] == "Manchester United"

        # Test full canonical name
        assert epl_map["manchesterunited"] == "Manchester United"

    def test_epl_arsenal_alias_resolution(self):
        """Test that various Arsenal aliases resolve correctly."""
        epl_map = get_team_alias_map("premier_league")

        # Test nickname alias
        assert epl_map["gunners"] == "Arsenal"

        # Test club variations
        assert epl_map["arsenalfc"] == "Arsenal"

        # Test abbreviated code
        assert epl_map["ars"] == "Arsenal"

        # Test full canonical name
        assert epl_map["arsenal"] == "Arsenal"

    def test_epl_brighton_alias_resolution(self):
        """Test that Brighton & Hove Albion aliases with special characters resolve correctly."""
        epl_map = get_team_alias_map("premier_league")

        # Test nickname alias
        assert epl_map["albion"] == "Brighton & Hove Albion"

        # Test variations with and without special characters
        assert epl_map["brighton"] == "Brighton & Hove Albion"
        assert epl_map["brightonhovealbion"] == "Brighton & Hove Albion"
        assert epl_map["brightonandhovealbion"] == "Brighton & Hove Albion"

        # Test abbreviated codes
        assert epl_map["bha"] == "Brighton & Hove Albion"
        assert epl_map["bhafc"] == "Brighton & Hove Albion"

    def test_epl_tottenham_alias_resolution(self):
        """Test that Tottenham Hotspur aliases resolve correctly."""
        epl_map = get_team_alias_map("premier_league")

        # Test nickname alias
        assert epl_map["spurs"] == "Tottenham Hotspur"

        # Test city name alias
        assert epl_map["tottenham"] == "Tottenham Hotspur"

        # Test abbreviated codes
        assert epl_map["tot"] == "Tottenham Hotspur"
        assert epl_map["thfc"] == "Tottenham Hotspur"

        # Test full canonical name
        assert epl_map["tottenhamhotspur"] == "Tottenham Hotspur"

    def test_epl_abbreviated_codes(self):
        """Test that EPL abbreviated codes resolve correctly."""
        epl_map = get_team_alias_map("premier_league")

        # Test various EPL team codes
        assert epl_map["ars"] == "Arsenal"
        assert epl_map["che"] == "Chelsea"
        assert epl_map["liv"] == "Liverpool"
        assert epl_map["mci"] == "Manchester City"
        assert epl_map["mun"] == "Manchester United"
        assert epl_map["tot"] == "Tottenham Hotspur"
        assert epl_map["whu"] == "West Ham United"
        assert epl_map["wol"] == "Wolverhampton Wanderers"

    # Cross-league tests to ensure proper isolation

    def test_league_isolation_for_common_codes(self):
        """Test that teams with same codes in different leagues are isolated correctly."""
        nhl_map = get_team_alias_map("nhl")
        nba_map = get_team_alias_map("nba")

        # BOS exists in both NHL (Boston Bruins) and NBA (Boston Celtics)
        assert nhl_map["bos"] == "Boston Bruins"
        assert nba_map["bos"] == "Boston Celtics"

        # CHI exists in both NHL (Chicago Blackhawks) and NBA (Chicago Bulls)
        assert nhl_map["chi"] == "Chicago Blackhawks"
        assert nba_map["chi"] == "Chicago Bulls"

        # TOR exists in both NHL (Toronto Maple Leafs) and NBA (Toronto Raptors)
        assert nhl_map["tor"] == "Toronto Maple Leafs"
        assert nba_map["tor"] == "Toronto Raptors"

        # DET exists in both NHL (Detroit Red Wings) and NBA (Detroit Pistons)
        assert nhl_map["det"] == "Detroit Red Wings"
        assert nba_map["det"] == "Detroit Pistons"

    def test_nickname_aliases_resolve_to_correct_teams(self):
        """Test that common nickname aliases resolve to their correct teams."""
        nhl_map = get_team_alias_map("nhl")
        nba_map = get_team_alias_map("nba")
        epl_map = get_team_alias_map("premier_league")

        # Test NHL nicknames
        assert nhl_map["bruins"] == "Boston Bruins"
        assert nhl_map["leafs"] == "Toronto Maple Leafs"
        assert nhl_map["penguins"] == "Pittsburgh Penguins"
        assert nhl_map["avalanche"] == "Colorado Avalanche"

        # Test NBA nicknames
        assert nba_map["lakers"] == "Los Angeles Lakers"
        assert nba_map["warriors"] == "Golden State Warriors"
        assert nba_map["celtics"] == "Boston Celtics"
        assert nba_map["bulls"] == "Chicago Bulls"

        # Test EPL nicknames
        assert epl_map["gunners"] == "Arsenal"
        assert epl_map["spurs"] == "Tottenham Hotspur"
        assert epl_map["blues"] == "Chelsea"
        assert epl_map["reds"] == "Liverpool"

    # UEFA Champions League Team Alias Resolution Tests

    def test_uefa_manchester_city_alias_resolution(self):
        """Test that various Manchester City aliases resolve correctly for UEFA CL."""
        uefa_map = get_team_alias_map("uefa_champions_league")

        # Test short abbreviation (key use case from spec)
        assert uefa_map["mc"] == "Manchester City"

        # Test nickname aliases
        assert uefa_map["mancity"] == "Manchester City"
        assert uefa_map["city"] == "Manchester City"

        # Test abbreviated codes
        assert uefa_map["mcfc"] == "Manchester City"
        assert uefa_map["mci"] == "Manchester City"

        # Test full canonical name
        assert uefa_map["manchestercity"] == "Manchester City"

    def test_uefa_borussia_dortmund_alias_resolution(self):
        """Test that various Borussia Dortmund aliases resolve correctly."""
        uefa_map = get_team_alias_map("uefa_champions_league")

        # Test common short names (key use case from spec - "Borussia")
        assert uefa_map["borussia"] == "Borussia Dortmund"
        assert uefa_map["dortmund"] == "Borussia Dortmund"

        # Test abbreviated code (BVB)
        assert uefa_map["bvb"] == "Borussia Dortmund"
        assert uefa_map["bor"] == "Borussia Dortmund"
        assert uefa_map["dor"] == "Borussia Dortmund"

        # Test full canonical name
        assert uefa_map["borussiadortmund"] == "Borussia Dortmund"

    def test_uefa_monaco_alias_resolution(self):
        """Test that Monaco aliases resolve correctly for UEFA CL."""
        uefa_map = get_team_alias_map("uefa_champions_league")

        # Test canonical and short names
        assert uefa_map["monaco"] == "Monaco"
        assert uefa_map["asmonaco"] == "Monaco"

        # Test abbreviated code
        assert uefa_map["asm"] == "Monaco"
        assert uefa_map["mon"] == "Monaco"

    def test_uefa_psg_alias_resolution(self):
        """Test that Paris Saint-Germain aliases resolve correctly."""
        uefa_map = get_team_alias_map("uefa_champions_league")

        # Test common abbreviation
        assert uefa_map["psg"] == "Paris Saint-Germain"

        # Test city name
        assert uefa_map["paris"] == "Paris Saint-Germain"

        # Test variations
        assert uefa_map["parissg"] == "Paris Saint-Germain"

        # Test full canonical name
        assert uefa_map["parissaintgermain"] == "Paris Saint-Germain"

    def test_uefa_spanish_clubs_alias_resolution(self):
        """Test that Spanish club aliases resolve correctly."""
        uefa_map = get_team_alias_map("uefa_champions_league")

        # Real Madrid
        assert uefa_map["realmadrid"] == "Real Madrid"
        assert uefa_map["real"] == "Real Madrid"
        assert uefa_map["rm"] == "Real Madrid"
        assert uefa_map["rma"] == "Real Madrid"
        assert uefa_map["madrid"] == "Real Madrid"

        # Barcelona
        assert uefa_map["barcelona"] == "Barcelona"
        assert uefa_map["barca"] == "Barcelona"
        assert uefa_map["fcb"] == "Barcelona"  # First FCB defined (Bayern also has FCB)

        # Atlético Madrid
        assert uefa_map["atleticomadrid"] == "Atlético Madrid"
        assert uefa_map["atletico"] == "Atlético Madrid"
        assert uefa_map["atleti"] == "Atlético Madrid"
        assert uefa_map["atm"] == "Atlético Madrid"

    def test_uefa_italian_clubs_alias_resolution(self):
        """Test that Italian club aliases resolve correctly."""
        uefa_map = get_team_alias_map("uefa_champions_league")

        # Inter Milan
        assert uefa_map["intermilan"] == "Inter Milan"
        assert uefa_map["inter"] == "Inter Milan"
        assert uefa_map["internazionale"] == "Inter Milan"
        assert uefa_map["int"] == "Inter Milan"

        # Juventus
        assert uefa_map["juventus"] == "Juventus"
        assert uefa_map["juve"] == "Juventus"
        assert uefa_map["juv"] == "Juventus"

        # AC Milan
        assert uefa_map["acmilan"] == "AC Milan"
        assert uefa_map["milan"] == "AC Milan"
        assert uefa_map["acm"] == "AC Milan"

    def test_uefa_german_clubs_alias_resolution(self):
        """Test that German club aliases resolve correctly."""
        uefa_map = get_team_alias_map("uefa_champions_league")

        # Bayern Munich
        assert uefa_map["bayernmunich"] == "Bayern Munich"
        assert uefa_map["bayern"] == "Bayern Munich"
        # Note: "Bayern München" normalizes to "bayernmnchen" (umlaut stripped)
        # but the ASCII alias "Bayern Munchen" normalizes to "bayernmunchen"
        assert uefa_map["bayernmunchen"] == "Bayern Munich"
        assert uefa_map["bay"] == "Bayern Munich"

        # RB Leipzig
        assert uefa_map["rbleipzig"] == "RB Leipzig"
        assert uefa_map["leipzig"] == "RB Leipzig"
        assert uefa_map["rbl"] == "RB Leipzig"

        # Bayer Leverkusen
        assert uefa_map["bayerleverkusen"] == "Bayer Leverkusen"
        assert uefa_map["leverkusen"] == "Bayer Leverkusen"
        assert uefa_map["lev"] == "Bayer Leverkusen"

    def test_uefa_abbreviated_codes(self):
        """Test that UEFA abbreviated codes resolve correctly."""
        uefa_map = get_team_alias_map("uefa_champions_league")

        # Test various common UEFA team codes
        assert uefa_map["psg"] == "Paris Saint-Germain"
        assert uefa_map["bvb"] == "Borussia Dortmund"
        assert uefa_map["asm"] == "Monaco"
        assert uefa_map["juv"] == "Juventus"
        assert uefa_map["int"] == "Inter Milan"
        assert uefa_map["ben"] == "Benfica"
        assert uefa_map["aja"] == "Ajax"
        assert uefa_map["cel"] == "Celtic"

    def test_uefa_mcfc_vs_mc_disambiguation(self):
        """Test that MC and MCFC both resolve to Manchester City in UEFA context."""
        uefa_map = get_team_alias_map("uefa_champions_league")

        # Both should resolve to Manchester City
        assert uefa_map["mc"] == "Manchester City"
        assert uefa_map["mcfc"] == "Manchester City"
        assert uefa_map["mci"] == "Manchester City"

        # Verify MC is specifically for Man City, not Monaco
        # (Monaco uses ASM, MON)
        assert uefa_map["mc"] != "Monaco"
