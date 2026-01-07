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
        index.add("quali", "episode-1")  # q, length 5
        index.add("qualifying", "episode-2")  # q, length 10
        index.add("quick", "episode-3")  # q, length 5
        index.add("race", "episode-4")  # r, length 4

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
        index.add("a", "episode-1")  # length 1
        index.add("ab", "episode-2")  # length 2
        index.add("abc", "episode-3")  # length 3

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


@pytest.mark.benchmark
class TestSessionLookupIndexBenchmark:
    """Benchmark tests to measure performance with large session_lookup.

    These tests are skipped in normal test runs. Run explicitly with:
        pytest -m benchmark tests/test_session_index.py
    """

    def test_candidate_reduction_with_200_entries(self) -> None:
        """Benchmark test demonstrating candidate reduction with 200+ entries.

        This test simulates a sports show with many episodes (e.g., F1 season with
        multiple sessions per race weekend). It demonstrates the optimization benefit
        by comparing the total candidate set size vs. filtered candidate set.
        """
        index = SessionLookupIndex()

        # Simulate a sports show with 200+ episodes
        # Pattern: 24 race weekends × 9 sessions = 216 entries
        # Sessions: FP1, FP2, FP3, Qualifying, Sprint Quali, Sprint, Race, etc.
        session_types = [
            "freepractice1",
            "freepractice2",
            "freepractice3",
            "qualifying",
            "sprintqualifying",
            "sprintshootout",
            "sprint",
            "race",
            "warmup",
        ]

        # Create 24 race weekends
        for race_num in range(1, 25):
            for session in session_types:
                # Create keys like "race1freepractice1", "race2qualifying", etc.
                key = f"race{race_num}{session}"
                value = f"episode-{race_num}-{session}"
                index.add(key, value)

        # Verify we have 200+ entries
        total_entries = len(index.keys())
        assert total_entries >= 200, f"Expected 200+ entries, got {total_entries}"

        # Test 1: Measure candidate reduction for a typical lookup
        search_token = "race15qualifying"  # Looking for race 15 qualifying

        # Without optimization, we'd iterate over ALL entries
        candidates = index.get_candidates(search_token)

        # Calculate reduction ratio
        reduction_ratio = len(candidates) / total_entries
        candidate_count = len(candidates)

        # Log the results (will show in pytest output with -v or -s)
        print(f"\n{'=' * 60}")
        print("BENCHMARK RESULTS:")
        print(f"{'=' * 60}")
        print(f"Total entries in index: {total_entries}")
        print(f"Search token: '{search_token}' (length {len(search_token)})")
        print(f"First character: '{search_token[0]}'")
        print(f"Candidates after filtering: {candidate_count}")
        print(f"Reduction ratio: {reduction_ratio:.2%}")
        print(f"Candidates checked: {candidate_count}/{total_entries}")
        print("Expected theoretical reduction: ~1.28% (1/78)")
        print(f"{'=' * 60}\n")

        # Verify the optimization is working
        # With 216 entries and 26 possible first chars × 3 length buckets,
        # we expect roughly 216/78 ≈ 2.77 candidates on average
        # In practice, with our specific data, we should see significant reduction
        assert candidate_count < total_entries * 0.5, (
            f"Candidate filtering not effective: {candidate_count}/{total_entries}"
        )

        # Verify the correct answer is in the filtered candidates
        assert "race15qualifying" in candidates, "Expected exact match should be in filtered candidates"

    def test_worst_case_candidate_reduction(self) -> None:
        """Test worst-case scenario where many entries share first char and length.

        Even in the worst case (all entries start with same char and similar length),
        the optimization should still provide some benefit by avoiding iteration
        over entries with different first chars or lengths outside ±1 range.
        """
        index = SessionLookupIndex()

        # Worst case: 250 entries all starting with 'r' and similar lengths
        # This simulates a pathological case for the optimization
        base_words = [
            "race",
            "races",
            "racing",
            "racer",
            "racers",
            "round",
            "rounds",
            "result",
            "results",
            "replay",
            "ranking",
            "rankings",
            "record",
            "records",
            "review",
        ]

        # Create 250 entries by combining base words with numbers
        entry_count = 0
        for i in range(1, 51):  # 50 iterations
            for word in base_words[:5]:  # Use 5 base words = 250 entries
                key = f"{word}{i}"
                value = f"episode-{entry_count}"
                index.add(key, value)
                entry_count += 1

        total_entries = len(index.keys())
        assert total_entries >= 200, f"Expected 200+ entries, got {total_entries}"

        # Search for a token that will match many entries
        search_token = "race15"  # length 6
        candidates = index.get_candidates(search_token)

        # Calculate metrics
        reduction_ratio = len(candidates) / total_entries

        print(f"\n{'=' * 60}")
        print("WORST-CASE BENCHMARK RESULTS:")
        print(f"{'=' * 60}")
        print(f"Total entries in index: {total_entries}")
        print("All entries start with: 'r'")
        print(f"Search token: '{search_token}' (length {len(search_token)})")
        print(f"Candidates after filtering: {len(candidates)}")
        print(f"Reduction ratio: {reduction_ratio:.2%}")
        print(f"{'=' * 60}\n")

        # Even in worst case, length filtering should eliminate some candidates
        # With length 6, we only check lengths 5, 6, 7
        # All other lengths are filtered out
        assert len(candidates) < total_entries, "Even in worst case, some filtering should occur"

        # Verify that candidates only include appropriate lengths
        for candidate in candidates:
            candidate_length = len(candidate)
            assert abs(candidate_length - len(search_token)) <= 1, (
                f"Candidate '{candidate}' has invalid length {candidate_length}"
            )

    def test_iteration_count_comparison(self) -> None:
        """Compare iteration counts: naive O(n) vs optimized O(n/k) approach.

        This test explicitly demonstrates the iteration count reduction that would
        occur in the original _resolve_session_lookup() implementation.
        """
        index = SessionLookupIndex()

        # Create 200 diverse entries across different first chars and lengths
        entries_added = 0

        # Add entries for each letter of alphabet
        for char in "abcdefghijklmnopqrstuvwxyz":
            for length in range(5, 15):  # Lengths 5-14
                key = char * length  # "aaaaa", "aaaaaa", etc.
                value = f"episode-{entries_added}"
                index.add(key, value)
                entries_added += 1
                if entries_added >= 200:
                    break
            if entries_added >= 200:
                break

        total_entries = len(index.keys())

        # Test multiple search scenarios
        test_cases = [
            ("qualifying", "Common F1 session name"),
            ("practice1", "Another common session"),
            ("sprint", "Sprint race session"),
            ("race", "Main race session"),
        ]

        print(f"\n{'=' * 60}")
        print("ITERATION COUNT COMPARISON:")
        print(f"{'=' * 60}")
        print(f"Total entries in index: {total_entries}\n")

        total_naive_iterations = 0
        total_optimized_iterations = 0

        for token, description in test_cases:
            # Naive approach: iterate ALL entries
            naive_iterations = total_entries

            # Optimized approach: only filtered candidates
            candidates = index.get_candidates(token)
            optimized_iterations = len(candidates)

            total_naive_iterations += naive_iterations
            total_optimized_iterations += optimized_iterations

            speedup = naive_iterations / max(optimized_iterations, 1)

            print(f"Token: '{token}' ({description})")
            print(f"  Naive iterations: {naive_iterations}")
            print(f"  Optimized iterations: {optimized_iterations}")
            print(f"  Speedup: {speedup:.1f}x")
            print()

        # Calculate overall metrics
        avg_reduction = (total_naive_iterations - total_optimized_iterations) / total_naive_iterations
        overall_speedup = total_naive_iterations / max(total_optimized_iterations, 1)

        print("OVERALL RESULTS:")
        print(f"  Total naive iterations: {total_naive_iterations}")
        print(f"  Total optimized iterations: {total_optimized_iterations}")
        print(f"  Average reduction: {avg_reduction:.1%}")
        print(f"  Overall speedup: {overall_speedup:.1f}x")
        print(f"{'=' * 60}\n")

        # Verify significant reduction in iterations
        assert total_optimized_iterations < total_naive_iterations * 0.2, (
            "Expected at least 80% reduction in iterations"
        )
