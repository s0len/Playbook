from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional


class SessionLookupIndex:
    """Optimized index for session lookup with O(1) candidate filtering.

    This class provides fast candidate filtering for fuzzy matching by indexing
    session keys by their first character and length. This reduces the candidate
    set from O(n) to approximately O(n/78) on average, exploiting the early-exit
    conditions in _tokens_close():
    - Tokens must be >= 4 chars
    - Length difference must be <= 1
    - First character must match

    Complexity:
    - Direct lookup: O(1)
    - Candidate retrieval: O(1) to get bucket, O(k) to return k candidates
      where k << n (typically k ~ n/78 due to 26 first-char buckets × 3 length buckets)
    """

    def __init__(self) -> None:
        """Initialize an empty SessionLookupIndex."""
        # Direct mapping for exact lookups
        self._mapping: Dict[str, str] = {}

        # Two-level index: first_char -> length -> [keys]
        # This allows O(1) filtering by first character and length
        self._index: Dict[str, Dict[int, List[str]]] = defaultdict(lambda: defaultdict(list))

    def add(self, key: str, value: str) -> None:
        """Add a key-value pair to the index.

        Args:
            key: The lookup key (e.g., normalized episode title or alias)
            value: The value to return when this key matches (e.g., episode ID)
        """
        # Store in direct mapping
        self._mapping[key] = value

        # Index by first character and length
        if key:  # Only index non-empty keys
            first_char = key[0]
            length = len(key)
            self._index[first_char][length].append(key)

    def get_direct(self, token: str) -> Optional[str]:
        """Get exact match for a token.

        Args:
            token: The token to look up

        Returns:
            The value if an exact match exists, None otherwise
        """
        return self._mapping.get(token)

    def get_candidates(self, token: str) -> List[str]:
        """Get candidate keys for fuzzy matching.

        Returns only keys that match the first character and are within ±1
        in length, exploiting the early-exit conditions in _tokens_close().

        Args:
            token: The token to find candidates for

        Returns:
            List of candidate keys that could potentially match via fuzzy matching
        """
        if not token:
            return []

        first_char = token[0]
        length = len(token)

        # Get candidates from first-char bucket with length ±1
        candidates: List[str] = []
        if first_char in self._index:
            length_buckets = self._index[first_char]
            # Check length-1, length, length+1 buckets
            for target_length in [length - 1, length, length + 1]:
                if target_length in length_buckets:
                    candidates.extend(length_buckets[target_length])

        return candidates

    @classmethod
    def from_dict(cls, mapping: Dict[str, str]) -> SessionLookupIndex:
        """Create a SessionLookupIndex from an existing dictionary.

        Args:
            mapping: Dictionary mapping keys to values

        Returns:
            A new SessionLookupIndex containing all entries from the mapping
        """
        index = cls()
        for key, value in mapping.items():
            index.add(key, value)
        return index
