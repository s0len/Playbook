"""Tests for metadata fingerprinting and change tracking."""

from __future__ import annotations

from datetime import date

from playbook.metadata import (
    MetadataChangeResult,
    MetadataFetchStatistics,
    MetadataFingerprintStore,
    ShowFingerprint,
    compute_show_fingerprint,
)
from playbook.models import Episode, Season, Show


class TestMetadataFetchStatistics:
    """Tests for thread-safe statistics accumulator."""

    def test_initial_state(self) -> None:
        """Test statistics start at zero."""
        stats = MetadataFetchStatistics()
        snapshot = stats.snapshot()
        assert snapshot["cache_hits"] == 0
        assert snapshot["cache_misses"] == 0
        assert snapshot["network_requests"] == 0
        assert snapshot["not_modified"] == 0
        assert snapshot["stale_used"] == 0
        assert snapshot["failures"] == 0

    def test_record_methods(self) -> None:
        """Test all recording methods increment correctly."""
        stats = MetadataFetchStatistics()
        stats.record_cache_hit()
        stats.record_cache_hit()
        stats.record_cache_miss()
        stats.record_network_request()
        stats.record_not_modified()
        stats.record_stale_used()
        stats.record_failure()
        stats.record_failure()

        snapshot = stats.snapshot()
        assert snapshot["cache_hits"] == 2
        assert snapshot["cache_misses"] == 1
        assert snapshot["network_requests"] == 1
        assert snapshot["not_modified"] == 1
        assert snapshot["stale_used"] == 1
        assert snapshot["failures"] == 2

    def test_has_activity(self) -> None:
        """Test has_activity detection."""
        stats = MetadataFetchStatistics()
        assert not stats.has_activity()

        stats.record_cache_hit()
        assert stats.has_activity()


class TestShowFingerprint:
    """Tests for ShowFingerprint dataclass."""

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        fp = ShowFingerprint(
            digest="abc123",
            season_hashes={"s1": "hash1", "s2": "hash2"},
            episode_hashes={"s1": {"e1": "ehash1"}, "s2": {"e1": "ehash2"}},
            content_hash="content123",
        )
        result = fp.to_dict()
        assert result["digest"] == "abc123"
        assert result["seasons"] == {"s1": "hash1", "s2": "hash2"}
        assert result["episodes"] == {"s1": {"e1": "ehash1"}, "s2": {"e1": "ehash2"}}
        assert result["content_hash"] == "content123"

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "digest": "abc123",
            "seasons": {"s1": "hash1"},
            "episodes": {"s1": {"e1": "ehash1"}},
            "content_hash": "content123",
        }
        fp = ShowFingerprint.from_dict(data)
        assert fp.digest == "abc123"
        assert fp.season_hashes == {"s1": "hash1"}
        assert fp.episode_hashes == {"s1": {"e1": "ehash1"}}
        assert fp.content_hash == "content123"

    def test_from_dict_with_missing_fields(self) -> None:
        """Test deserialization handles missing optional fields."""
        data = {"digest": "abc123"}
        fp = ShowFingerprint.from_dict(data)
        assert fp.digest == "abc123"
        assert fp.season_hashes == {}
        assert fp.episode_hashes == {}
        assert fp.content_hash is None

    def test_to_dict_without_content_hash(self) -> None:
        """Test serialization without content_hash."""
        fp = ShowFingerprint(
            digest="abc123",
            season_hashes={},
            episode_hashes={},
        )
        result = fp.to_dict()
        assert "content_hash" not in result


class TestMetadataFingerprintStore:
    """Tests for persistent fingerprint storage."""

    def test_get_nonexistent(self, tmp_path) -> None:
        """Test getting a non-existent fingerprint returns None."""
        store = MetadataFingerprintStore(tmp_path)
        assert store.get("nonexistent") is None

    def test_update_new_fingerprint(self, tmp_path) -> None:
        """Test adding a new fingerprint."""
        store = MetadataFingerprintStore(tmp_path)
        fp = ShowFingerprint(digest="abc", season_hashes={}, episode_hashes={})
        result = store.update("sport1", fp)

        assert result.updated is True
        assert result.invalidate_all is False
        assert store.get("sport1") is not None

    def test_update_unchanged_fingerprint(self, tmp_path) -> None:
        """Test updating with identical fingerprint."""
        store = MetadataFingerprintStore(tmp_path)
        fp = ShowFingerprint(digest="abc", season_hashes={}, episode_hashes={})
        store.update("sport1", fp)

        result = store.update("sport1", fp)
        assert result.updated is False

    def test_update_changed_fingerprint(self, tmp_path) -> None:
        """Test updating with changed fingerprint."""
        store = MetadataFingerprintStore(tmp_path)
        fp1 = ShowFingerprint(
            digest="abc",
            season_hashes={"s1": "h1"},
            episode_hashes={"s1": {"e1": "eh1"}},
        )
        store.update("sport1", fp1)

        fp2 = ShowFingerprint(
            digest="def",
            season_hashes={"s1": "h2"},
            episode_hashes={"s1": {"e1": "eh2"}},
        )
        result = store.update("sport1", fp2)

        assert result.updated is True
        assert "s1" in result.changed_seasons

    def test_save_and_load(self, tmp_path) -> None:
        """Test persistence across store instances."""
        store1 = MetadataFingerprintStore(tmp_path)
        fp = ShowFingerprint(digest="abc", season_hashes={"s1": "h1"}, episode_hashes={})
        store1.update("sport1", fp)
        store1.save()

        store2 = MetadataFingerprintStore(tmp_path)
        loaded = store2.get("sport1")
        assert loaded is not None
        assert loaded.digest == "abc"
        assert loaded.season_hashes == {"s1": "h1"}

    def test_remove(self, tmp_path) -> None:
        """Test removing a fingerprint."""
        store = MetadataFingerprintStore(tmp_path)
        fp = ShowFingerprint(digest="abc", season_hashes={}, episode_hashes={})
        store.update("sport1", fp)
        assert store.get("sport1") is not None

        store.remove("sport1")
        assert store.get("sport1") is None


class TestComputeShowFingerprint:
    """Tests for compute_show_fingerprint function."""

    def _make_show(self) -> Show:
        """Create a test show with seasons and episodes."""
        return Show(
            key="test-show",
            title="Test Show",
            summary="A test show",
            seasons=[
                Season(
                    key="s1",
                    title="Season 1",
                    summary=None,
                    index=1,
                    display_number=1,
                    round_number=1,
                    episodes=[
                        Episode(
                            title="Episode 1",
                            summary=None,
                            originally_available=date(2026, 1, 1),
                            index=1,
                            display_number=1,
                            aliases=["E1", "Ep1"],
                        ),
                        Episode(
                            title="Episode 2",
                            summary=None,
                            originally_available=None,
                            index=2,
                            display_number=2,
                        ),
                    ],
                ),
            ],
            metadata={"id": 1, "slug": "test-show"},
        )

    def test_compute_fingerprint(self) -> None:
        """Test computing a fingerprint for a show."""
        show = self._make_show()
        fp = compute_show_fingerprint(show, "test-show")

        assert fp.digest  # Non-empty hash
        assert len(fp.season_hashes) == 1
        assert "s1" in fp.season_hashes
        assert len(fp.episode_hashes["s1"]) == 2
        assert fp.content_hash  # Non-empty content hash

    def test_fingerprint_changes_with_metadata(self) -> None:
        """Test that fingerprint changes when metadata changes."""
        show1 = self._make_show()
        show2 = self._make_show()
        show2.metadata["id"] = 999  # Change metadata

        fp1 = compute_show_fingerprint(show1, "test-show")
        fp2 = compute_show_fingerprint(show2, "test-show")

        assert fp1.digest != fp2.digest

    def test_cached_fingerprint_reused(self) -> None:
        """Test that cached fingerprint is returned when content unchanged."""
        show = self._make_show()
        fp1 = compute_show_fingerprint(show, "test-show")
        fp2 = compute_show_fingerprint(show, "test-show", cached_fingerprint=fp1)

        # Should return the same object when content hash matches
        assert fp2 is fp1

    def test_cached_fingerprint_not_reused_when_changed(self) -> None:
        """Test that new fingerprint is computed when content changes."""
        show1 = self._make_show()
        fp1 = compute_show_fingerprint(show1, "test-show")

        show2 = self._make_show()
        show2.title = "Changed Title"
        show2.metadata["title"] = "Changed Title"

        fp2 = compute_show_fingerprint(show2, "test-show", cached_fingerprint=fp1)

        # Should compute new fingerprint
        assert fp2 is not fp1

    def test_episode_fingerprint_includes_aliases(self) -> None:
        """Test that episode fingerprint includes aliases."""
        show1 = self._make_show()
        show2 = self._make_show()
        show2.seasons[0].episodes[0].aliases = ["NewAlias"]

        fp1 = compute_show_fingerprint(show1, "test-show")
        fp2 = compute_show_fingerprint(show2, "test-show")

        # Episode hashes should differ
        s1_episodes_1 = fp1.episode_hashes.get("s1", {})
        s1_episodes_2 = fp2.episode_hashes.get("s1", {})

        # Find the episode keys
        ep1_keys = list(s1_episodes_1.keys())
        ep2_keys = list(s1_episodes_2.keys())

        # At least one episode hash should differ
        assert any(s1_episodes_1.get(k) != s1_episodes_2.get(k) for k in ep1_keys)


class TestMetadataChangeResult:
    """Tests for MetadataChangeResult dataclass."""

    def test_no_changes(self) -> None:
        """Test result with no changes."""
        result = MetadataChangeResult(
            updated=False,
            changed_seasons=set(),
            changed_episodes={},
        )
        assert not result.updated
        assert not result.changed_seasons
        assert not result.changed_episodes
        assert not result.invalidate_all

    def test_with_changed_seasons(self) -> None:
        """Test result with changed seasons."""
        result = MetadataChangeResult(
            updated=True,
            changed_seasons={"s1", "s2"},
            changed_episodes={},
        )
        assert result.updated
        assert "s1" in result.changed_seasons
        assert "s2" in result.changed_seasons

    def test_with_changed_episodes(self) -> None:
        """Test result with changed episodes."""
        result = MetadataChangeResult(
            updated=True,
            changed_seasons=set(),
            changed_episodes={"s1": {"e1", "e2"}, "s2": {"e3"}},
        )
        assert result.updated
        assert "e1" in result.changed_episodes["s1"]
        assert "e2" in result.changed_episodes["s1"]
        assert "e3" in result.changed_episodes["s2"]

    def test_invalidate_all(self) -> None:
        """Test result with invalidate_all flag."""
        result = MetadataChangeResult(
            updated=True,
            changed_seasons=set(),
            changed_episodes={},
            invalidate_all=True,
        )
        assert result.invalidate_all
