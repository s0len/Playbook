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

    pass
