from __future__ import annotations

import pytest

from playbook.session_index import SessionLookupIndex


class TestSessionLookupIndexDirectLookup:
    """Tests for exact match functionality."""

    def test_get_direct_returns_value_for_exact_match(self) -> None:
        index = SessionLookupIndex()
        index.add("quali", "episode-1")
        assert index.get_direct("quali") == "episode-1"

    def test_get_direct_returns_none_for_missing_key(self) -> None:
        index = SessionLookupIndex()
        index.add("quali", "episode-1")
        assert index.get_direct("race") is None

    def test_get_direct_returns_none_for_empty_index(self) -> None:
        index = SessionLookupIndex()
        assert index.get_direct("anything") is None

    def test_get_direct_handles_multiple_entries(self) -> None:
        index = SessionLookupIndex()
        index.add("freepractice1", "episode-1")
        index.add("qualifying", "episode-2")
        index.add("race", "episode-3")

        assert index.get_direct("freepractice1") == "episode-1"
        assert index.get_direct("qualifying") == "episode-2"
        assert index.get_direct("race") == "episode-3"


class TestSessionLookupIndexFirstCharacterFiltering:
    """Tests for first-character filtering in candidate retrieval."""

    def test_get_candidates_filters_by_first_character(self) -> None:
        index = SessionLookupIndex()
        index.add("quali", "episode-1")
        index.add("race", "episode-2")
        index.add("practice", "episode-3")

        candidates = index.get_candidates("quick")

        # Should only include "quali", not "race" or "practice"
        assert "quali" in candidates
        assert "race" not in candidates
        assert "practice" not in candidates

    def test_get_candidates_returns_empty_for_no_first_char_match(self) -> None:
        index = SessionLookupIndex()
        index.add("quali", "episode-1")
        index.add("race", "episode-2")

        candidates = index.get_candidates("sprint")
        assert candidates == []

    def test_get_candidates_handles_case_sensitive_first_char(self) -> None:
        index = SessionLookupIndex()
        index.add("quali", "episode-1")
        index.add("Quali", "episode-2")

        # Lowercase 'q' should only match lowercase 'q' entries
        candidates = index.get_candidates("quick")
        assert "quali" in candidates
        assert "Quali" not in candidates

        # Uppercase 'Q' should only match uppercase 'Q' entries
        candidates = index.get_candidates("Quick")
        assert "Quali" in candidates
        assert "quali" not in candidates


class TestSessionLookupIndexLengthFiltering:
    """Tests for length-based filtering (±1 constraint)."""

    def test_get_candidates_includes_exact_length(self) -> None:
        index = SessionLookupIndex()
        index.add("quali", "episode-1")  # length 5

        candidates = index.get_candidates("quick")  # length 5
        assert "quali" in candidates

    def test_get_candidates_includes_length_minus_one(self) -> None:
        index = SessionLookupIndex()
        index.add("race", "episode-1")  # length 4

        candidates = index.get_candidates("races")  # length 5
        assert "race" in candidates

    def test_get_candidates_includes_length_plus_one(self) -> None:
        index = SessionLookupIndex()
        index.add("races", "episode-1")  # length 5

        candidates = index.get_candidates("race")  # length 4
        assert "races" in candidates

    def test_get_candidates_excludes_length_difference_greater_than_one(self) -> None:
        index = SessionLookupIndex()
        index.add("qualification", "episode-1")  # length 13

        candidates = index.get_candidates("quali")  # length 5
        # Length difference is 8, should not be included
        assert "qualification" not in candidates

    def test_get_candidates_filters_by_both_first_char_and_length(self) -> None:
        index = SessionLookupIndex()
        index.add("quali", "episode-1")      # q, length 5
        index.add("qualifying", "episode-2")  # q, length 10
        index.add("quick", "episode-3")       # q, length 5
        index.add("race", "episode-4")        # r, length 4

        candidates = index.get_candidates("qualif")  # q, length 6

        # Should include: exact length or ±1 with first char 'q'
        # "quali" - length 5 (within ±1) ✓
        # "qualifying" - length 10 (difference > 1) ✗
        # "quick" - length 5 (within ±1) ✓
        # "race" - wrong first char ✗
        assert "quali" in candidates
        assert "quick" in candidates
        assert "qualifying" not in candidates
        assert "race" not in candidates


class TestSessionLookupIndexEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_get_candidates_handles_empty_token(self) -> None:
        index = SessionLookupIndex()
        index.add("quali", "episode-1")

        candidates = index.get_candidates("")
        assert candidates == []

    def test_add_handles_empty_key(self) -> None:
        index = SessionLookupIndex()
        index.add("", "episode-1")

        # Empty key should be stored in mapping but not indexed
        assert index.get_direct("") == "episode-1"
        # Empty token should return empty candidates
        assert index.get_candidates("") == []

    def test_get_candidates_handles_very_short_tokens(self) -> None:
        index = SessionLookupIndex()
        index.add("q", "episode-1")
        index.add("qu", "episode-2")
        index.add("qui", "episode-3")

        # Single character token
        candidates = index.get_candidates("q")
        # Should match: "q" (length 1), "qu" (length 2)
        # Should not match: "qui" (length 3, difference > 1)
        assert "q" in candidates
        assert "qu" in candidates
        assert "qui" not in candidates

    def test_get_candidates_handles_single_character_token(self) -> None:
        index = SessionLookupIndex()
        index.add("a", "episode-1")   # length 1
        index.add("ab", "episode-2")  # length 2
        index.add("abc", "episode-3") # length 3

        candidates = index.get_candidates("a")
        # Should include length 1 and 2 only
        assert "a" in candidates
        assert "ab" in candidates
        assert "abc" not in candidates

    def test_empty_index_get_candidates_returns_empty(self) -> None:
        index = SessionLookupIndex()
        candidates = index.get_candidates("anything")
        assert candidates == []

    def test_add_allows_duplicate_keys_with_different_values(self) -> None:
        index = SessionLookupIndex()
        index.add("quali", "episode-1")
        index.add("quali", "episode-2")  # Overwrites

        # Should use the latest value
        assert index.get_direct("quali") == "episode-2"


class TestSessionLookupIndexFromDict:
    """Tests for the from_dict class method."""

    def test_from_dict_creates_index_from_mapping(self) -> None:
        mapping = {
            "quali": "episode-1",
            "race": "episode-2",
            "sprint": "episode-3",
        }

        index = SessionLookupIndex.from_dict(mapping)

        assert index.get_direct("quali") == "episode-1"
        assert index.get_direct("race") == "episode-2"
        assert index.get_direct("sprint") == "episode-3"

    def test_from_dict_builds_candidate_index(self) -> None:
        mapping = {
            "quali": "episode-1",
            "qualifying": "episode-2",
            "race": "episode-3",
        }

        index = SessionLookupIndex.from_dict(mapping)

        # Test that candidate filtering works correctly
        candidates = index.get_candidates("qualif")  # q, length 6
        # "quali" - length 5 (within ±1) ✓
        # "qualifying" - length 10 (difference > 1) ✗
        assert "quali" in candidates
        assert "qualifying" not in candidates

    def test_from_dict_handles_empty_mapping(self) -> None:
        index = SessionLookupIndex.from_dict({})

        assert index.get_direct("anything") is None
        assert index.get_candidates("anything") == []


class TestSessionLookupIndexMultipleEntries:
    """Tests with realistic multi-entry scenarios."""

    def test_index_handles_many_entries_with_same_first_char(self) -> None:
        index = SessionLookupIndex()
        # Add multiple entries starting with 'r'
        index.add("race", "episode-1")
        index.add("races", "episode-2")
        index.add("racing", "episode-3")
        index.add("rally", "episode-4")

        candidates = index.get_candidates("race")  # r, length 4
        # Should include entries with length 3, 4, 5
        # "race" - length 4 ✓
        # "races" - length 5 ✓
        # "racing" - length 6 ✗
        # "rally" - length 5 ✓
        assert "race" in candidates
        assert "races" in candidates
        assert "rally" in candidates
        assert "racing" not in candidates

    def test_index_reduces_candidate_set_significantly(self) -> None:
        """Test that demonstrates the optimization benefit."""
        index = SessionLookupIndex()

        # Add 26 entries, one for each letter, varying lengths
        for i, char in enumerate("abcdefghijklmnopqrstuvwxyz"):
            index.add(char * 5, f"episode-{i}")

        # Search for a token starting with 'q', length 5
        candidates = index.get_candidates("quick")

        # Should only return entries starting with 'q' and length 4-6
        # In this case, only "qqqqq" (length 5)
        assert len(candidates) == 1
        assert "qqqqq" in candidates
        # Should not include entries starting with other letters
        assert "aaaaa" not in candidates
        assert "zzzzz" not in candidates

    def test_index_handles_sports_show_scenario(self) -> None:
        """Test realistic scenario with sports show episodes."""
        index = SessionLookupIndex()

        # Simulating F1 session types
        index.add("freepractice1", "fp1")
        index.add("freepractice2", "fp2")
        index.add("freepractice3", "fp3")
        index.add("qualifying", "quali")
        index.add("sprintqualifying", "sprint-quali")
        index.add("sprint", "sprint")
        index.add("race", "race")

        # Test various lookups
        # Direct match
        assert index.get_direct("race") == "race"

        # Fuzzy candidate retrieval for "practise" (common misspelling)
        # Should match entries starting with 'p' and similar length
        candidates = index.get_candidates("practise")  # p, length 8
        # None of the entries start with 'p', so empty
        assert candidates == []

        # Fuzzy candidate retrieval for "quali"
        candidates = index.get_candidates("quali")  # q, length 5
        # "qualifying" - length 10 (difference > 1) ✗
        assert "qualifying" not in candidates

        # Fuzzy candidate retrieval for "qualifying"
        candidates = index.get_candidates("qualifying")  # q, length 10
        # "qualifying" - length 10 ✓
        assert "qualifying" in candidates

        # Fuzzy candidate retrieval for "sprintrace"
        candidates = index.get_candidates("sprintrace")  # s, length 10
        # "sprintqualifying" - length 16 (difference > 1) ✗
        # "sprint" - length 6 (difference > 1) ✗
        assert candidates == []
