"""Session lookup index with optimized candidate filtering for fuzzy matching.

This module provides SessionLookupIndex, a specialized data structure that dramatically
reduces the performance cost of fuzzy session matching. By indexing session lookup keys
by their first character and length, it exploits the early-exit conditions in the
_tokens_close() matching function to filter candidates in O(1) time instead of scanning
all entries in O(n) time.

Performance Impact:
    For shows with 200+ episodes, this reduces candidate iteration from O(n) to approximately
    O(n/78) on average - a ~98% reduction in candidates to check before computing expensive
    edit distance calculations.

Optimization Strategy:
    The _tokens_close() function has three early-exit conditions that we can leverage:
    1. Both tokens must be >= 4 characters
    2. Length difference must be <= 1
    3. First character must match

    By bucketing keys using a two-level index (first_char -> length -> [keys]), we can
    retrieve only the keys that satisfy conditions #2 and #3 in O(1) time, eliminating
    ~98% of unnecessary distance calculations.
"""
from __future__ import annotations

from collections import defaultdict


class SessionLookupIndex:
    """Optimized index for session lookup with O(1) candidate filtering.

    This class provides fast candidate filtering for fuzzy matching by indexing
    session keys by their first character and length. This reduces the candidate
    set from O(n) to approximately O(n/78) on average, exploiting the early-exit
    conditions in _tokens_close():
    - Tokens must be >= 4 chars
    - Length difference must be <= 1
    - First character must match

    Data Structure:
        Uses a two-level nested dictionary for indexing:
        {
            first_char: {
                length: [key1, key2, ...],
                ...
            },
            ...
        }

        This structure enables O(1) access to candidates matching specific
        first character and length constraints.

    Complexity Guarantees:
        - add(key, value): O(1) - simple dict insert and list append
        - get_direct(token): O(1) - direct dictionary lookup
        - get_candidates(token): O(1) bucket access + O(k) to return k candidates
          where k is the number of candidates in matching buckets
        - Space: O(n) where n is the number of unique keys (same as original dict)

    Performance Characteristics:
        - With uniform distribution across 26 first characters and 3 length buckets,
          expected reduction factor k = n / (26 × 3) ≈ n/78
        - For 200 entries, get_candidates returns ~2-3 candidates instead of 200
        - Actual reduction depends on key distribution (worst case: all keys same
          first char and length → no filtering benefit)

    Usage Example:
        >>> index = SessionLookupIndex()
        >>> index.add("practice", "s01e01")
        >>> index.add("qualifying", "s01e02")
        >>> index.add("race", "s01e03")
        >>>
        >>> # Direct lookup
        >>> index.get_direct("race")  # Returns: "s01e03"
        >>>
        >>> # Fuzzy matching candidates
        >>> index.get_candidates("rce")  # Returns: ["race"] (first char 'r', length 3±1)
        >>> index.get_candidates("practce")  # Returns: ["practice"] (first char 'p', length 7±1)

    Thread Safety:
        Not thread-safe. External synchronization required for concurrent access.

    Backwards Compatibility:
        Maintains the same key->value mapping semantics as Dict[str, str].
        Can be used as a drop-in replacement with added candidate filtering.
    """

    def __init__(self) -> None:
        """Initialize an empty SessionLookupIndex.

        Creates two internal data structures:
        1. _mapping: Direct key->value dict for O(1) exact lookups
        2. _index: Two-level bucketed index for O(1) candidate filtering
        """
        # Direct mapping for exact lookups (e.g., {"race": "s01e03", "qualifying": "s01e02"})
        # Used by get_direct() to return values for exact key matches in O(1) time
        self._mapping: dict[str, str] = {}

        # Two-level bucketed index: first_char -> length -> [keys]
        # Structure: {'r': {4: ['race'], 5: ['races']}, 'p': {8: ['practice', 'practise']}}
        # This allows O(1) filtering by first character and length constraints:
        # - First level: 26 buckets (a-z) for first character matching
        # - Second level: ~50 buckets (typical key lengths) for length ±1 matching
        # - Result: ~98% reduction in candidates (n/78 on average)
        self._index: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))

    def add(self, key: str, value: str) -> None:
        """Add a key-value pair to the index.

        Stores the key-value pair in both the direct mapping (for exact lookups)
        and the bucketed index (for candidate filtering).

        Args:
            key: The lookup key (e.g., normalized episode title or alias)
            value: The value to return when this key matches (e.g., episode ID)

        Complexity: O(1)

        Example:
            >>> index = SessionLookupIndex()
            >>> index.add("practice", "s01e01")
            >>> # Stored in: _mapping["practice"] = "s01e01"
            >>> #            _index["p"][8] = ["practice"]
        """
        # Store in direct mapping for O(1) exact lookups
        # Example: _mapping["race"] = "s01e03"
        self._mapping[key] = value

        # Index by first character and length for O(1) candidate filtering
        if key:  # Only index non-empty keys
            first_char = key[0]  # Extract first character (e.g., "race" -> "r")
            length = len(key)     # Calculate length (e.g., "race" -> 4)

            # Append to the appropriate bucket: _index[first_char][length]
            # Example: "race" goes to _index["r"][4].append("race")
            # This enables get_candidates("rce") to quickly find ["race"]
            # by checking _index["r"][2], _index["r"][3], _index["r"][4]
            self._index[first_char][length].append(key)

    def get_direct(self, token: str) -> str | None:
        """Get exact match for a token.

        Performs an O(1) dictionary lookup for exact key matches.
        This should always be tried before fuzzy matching with get_candidates().

        Args:
            token: The token to look up (e.g., "race", "qualifying")

        Returns:
            The value if an exact match exists, None otherwise

        Complexity: O(1)

        Example:
            >>> index = SessionLookupIndex()
            >>> index.add("race", "s01e03")
            >>> index.get_direct("race")
            's01e03'
            >>> index.get_direct("rac")  # Not an exact match
            None
        """
        return self._mapping.get(token)

    def get_candidates(self, token: str) -> list[str]:
        """Get candidate keys for fuzzy matching.

        Returns only keys that match the first character and are within ±1
        in length, exploiting the early-exit conditions in _tokens_close().

        This method provides the core optimization: instead of checking all n keys
        in the index, it returns only the subset that could possibly match based
        on the constraints enforced by _tokens_close():
        - First character must match (reduces candidates by ~26x)
        - Length must be within ±1 (reduces candidates by ~3x)
        - Combined: ~98% reduction (n/78 candidates on average)

        Args:
            token: The token to find candidates for (e.g., "practce" with typo)

        Returns:
            List of candidate keys that could potentially match via fuzzy matching.
            Empty list if token is empty or no candidates match the constraints.

        Complexity: O(1) to access buckets + O(k) to return k candidates
                    where k << n (typically k ≈ n/78)

        Example:
            >>> index = SessionLookupIndex()
            >>> index.add("practice", "s01e01")    # Length 8, first char 'p'
            >>> index.add("qualifying", "s01e02")  # Length 10, first char 'q'
            >>> index.add("race", "s01e03")        # Length 4, first char 'r'
            >>>
            >>> # Token "practce" (length 7, first char 'p')
            >>> # Returns keys with first char 'p' and length in {6, 7, 8}
            >>> index.get_candidates("practce")
            ['practice']  # Only 1 candidate instead of 3 (67% reduction)
            >>>
            >>> # Token "rce" (length 3, first char 'r')
            >>> # Returns keys with first char 'r' and length in {2, 3, 4}
            >>> index.get_candidates("rce")
            ['race']  # Only 1 candidate instead of 3 (67% reduction)
        """
        if not token:
            return []

        # Extract filtering criteria from the token
        first_char = token[0]  # e.g., "practce" -> 'p'
        length = len(token)     # e.g., "practce" -> 7

        # Retrieve candidates matching the bucketing constraints
        # This is where the optimization happens: O(1) bucket access instead of O(n) scan
        candidates: list[str] = []

        if first_char in self._index:
            # Access the first-level bucket (first character match)
            # Example: _index['p'] contains all keys starting with 'p'
            length_buckets = self._index[first_char]

            # Check all three length buckets: length-1, length, length+1
            # This matches the _tokens_close() constraint: abs(len(a) - len(b)) <= 1
            # Example: token length 7 checks buckets {6, 7, 8}
            for target_length in [length - 1, length, length + 1]:
                if target_length in length_buckets:
                    # Extend candidates with all keys in this length bucket
                    # Example: length_buckets[8] = ["practice", "practise"]
                    candidates.extend(length_buckets[target_length])

        # Return the filtered candidate list
        # For 200 entries uniformly distributed, this typically returns ~2-3 candidates
        # instead of all 200, enabling _tokens_close() to run 98% fewer times
        return candidates

    def keys(self) -> list[str]:
        """Get all keys in the index.

        Returns all keys that have been added to the index, in arbitrary order.
        Useful for iteration or inspection of index contents.

        Returns:
            List of all keys in the index

        Complexity: O(n) where n is the number of keys

        Example:
            >>> index = SessionLookupIndex()
            >>> index.add("race", "s01e03")
            >>> index.add("qualifying", "s01e02")
            >>> sorted(index.keys())
            ['qualifying', 'race']
        """
        return list(self._mapping.keys())

    @classmethod
    def from_dict(cls, mapping: dict[str, str]) -> SessionLookupIndex:
        """Create a SessionLookupIndex from an existing dictionary.

        Convenience constructor for migrating from Dict[str, str] to SessionLookupIndex.
        Builds both the direct mapping and the bucketed index from all entries.

        Args:
            mapping: Dictionary mapping keys to values (e.g., session lookup dict)

        Returns:
            A new SessionLookupIndex containing all entries from the mapping

        Complexity: O(n) where n is the number of entries in mapping

        Example:
            >>> session_dict = {
            ...     "practice": "s01e01",
            ...     "qualifying": "s01e02",
            ...     "race": "s01e03"
            ... }
            >>> index = SessionLookupIndex.from_dict(session_dict)
            >>> index.get_direct("race")
            's01e03'
            >>> index.get_candidates("rac")  # Fuzzy matching
            ['race']
        """
        index = cls()
        for key, value in mapping.items():
            index.add(key, value)
        return index
