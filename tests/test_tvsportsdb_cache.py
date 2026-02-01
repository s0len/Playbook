"""Tests for TheTVSportsDB cache module."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from playbook.tvsportsdb.cache import TVSportsDBCache
from playbook.tvsportsdb.models import (
    EpisodeResponse,
    SeasonResponse,
    ShowResponse,
    TeamAliasResponse,
)


class TestTVSportsDBCache:
    """Tests for TTL-based API response caching."""

    def test_cache_miss_returns_none(self, tmp_path) -> None:
        """Test that cache miss returns None."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)
        assert cache.get_show("nonexistent") is None
        assert cache.get_season("nonexistent", 1) is None
        assert cache.get_team_aliases("nonexistent") is None

    def test_save_and_get_show(self, tmp_path) -> None:
        """Test saving and retrieving a show."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)
        show = ShowResponse(
            id=1,
            slug="formula-1-2026",
            title="Formula 1 2026",
            sort_title="Formula 1 2026",
            season_count=24,
            episode_count=144,
        )
        cache.save_show("formula-1-2026", show)

        retrieved = cache.get_show("formula-1-2026")
        assert retrieved is not None
        assert retrieved.id == 1
        assert retrieved.slug == "formula-1-2026"
        assert retrieved.title == "Formula 1 2026"
        assert retrieved.season_count == 24

    def test_save_and_get_season(self, tmp_path) -> None:
        """Test saving and retrieving a season."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)
        season = SeasonResponse(
            id=10,
            show_id=1,
            number=1,
            title="Australian Grand Prix",
            sort_title="01 - Australian Grand Prix",
            episodes=[
                EpisodeResponse(id=1, season_id=10, number=1, title="FP1"),
                EpisodeResponse(id=2, season_id=10, number=2, title="FP2"),
            ],
        )
        cache.save_season("formula-1-2026", 1, season)

        retrieved = cache.get_season("formula-1-2026", 1)
        assert retrieved is not None
        assert retrieved.id == 10
        assert retrieved.title == "Australian Grand Prix"
        assert len(retrieved.episodes) == 2
        assert retrieved.episodes[0].title == "FP1"

    def test_save_and_get_team_aliases(self, tmp_path) -> None:
        """Test saving and retrieving team aliases."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)
        aliases = [
            TeamAliasResponse(canonical_name="Lakers", alias="LAL", sport_slug="nba"),
            TeamAliasResponse(canonical_name="Celtics", alias="BOS", sport_slug="nba"),
        ]
        cache.save_team_aliases("nba-2025-2026", aliases)

        retrieved = cache.get_team_aliases("nba-2025-2026")
        assert retrieved is not None
        assert len(retrieved) == 2
        assert retrieved[0].alias == "LAL"
        assert retrieved[1].alias == "BOS"

    def test_expired_cache_returns_none(self, tmp_path) -> None:
        """Test that expired cache entries return None."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=1)
        show = ShowResponse(
            id=1,
            slug="test-show",
            title="Test Show",
            sort_title="Test Show",
        )
        cache.save_show("test-show", show)

        # Manually modify the cache file to have an old timestamp
        cache_file = tmp_path / "cache" / "shows" / "test-show.json"
        with cache_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Set cached_at to 2 hours ago
        old_time = datetime.now(UTC) - timedelta(hours=2)
        data["cached_at"] = old_time.isoformat(timespec="seconds")

        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(data, f)

        # Should return None due to expiry
        assert cache.get_show("test-show") is None

    def test_valid_cache_within_ttl(self, tmp_path) -> None:
        """Test that cache within TTL is still valid."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)
        show = ShowResponse(
            id=1,
            slug="test-show",
            title="Test Show",
            sort_title="Test Show",
        )
        cache.save_show("test-show", show)

        # Manually set cached_at to 6 hours ago (within 12 hour TTL)
        cache_file = tmp_path / "cache" / "shows" / "test-show.json"
        with cache_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        recent_time = datetime.now(UTC) - timedelta(hours=6)
        data["cached_at"] = recent_time.isoformat(timespec="seconds")

        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(data, f)

        # Should still return the show
        retrieved = cache.get_show("test-show")
        assert retrieved is not None
        assert retrieved.slug == "test-show"

    def test_invalidate_show(self, tmp_path) -> None:
        """Test invalidating a specific show."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)
        show = ShowResponse(
            id=1,
            slug="test-show",
            title="Test Show",
            sort_title="Test Show",
        )
        cache.save_show("test-show", show)
        assert cache.get_show("test-show") is not None

        cache.invalidate_show("test-show")
        assert cache.get_show("test-show") is None

    def test_invalidate_all(self, tmp_path) -> None:
        """Test invalidating all cached data."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)

        # Save multiple items
        show = ShowResponse(
            id=1,
            slug="test-show",
            title="Test Show",
            sort_title="Test Show",
        )
        season = SeasonResponse(
            id=10,
            show_id=1,
            number=1,
            title="Season 1",
            sort_title="Season 1",
        )
        cache.save_show("test-show", show)
        cache.save_season("test-show", 1, season)

        assert cache.get_show("test-show") is not None
        assert cache.get_season("test-show", 1) is not None

        cache.invalidate_all()

        assert cache.get_show("test-show") is None
        assert cache.get_season("test-show", 1) is None

    def test_corrupted_cache_file_returns_none(self, tmp_path) -> None:
        """Test that corrupted cache files are handled gracefully."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)

        # Create a corrupted cache file
        cache_file = tmp_path / "cache" / "shows" / "broken.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("not valid json{{{")

        assert cache.get_show("broken") is None

    def test_cache_without_cached_at_returns_none(self, tmp_path) -> None:
        """Test that cache file without cached_at timestamp is invalid."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)

        # Create cache file without cached_at
        cache_file = tmp_path / "cache" / "shows" / "no-timestamp.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump({"content": {"id": 1, "slug": "test", "title": "Test", "sort_title": "Test"}}, f)

        assert cache.get_show("no-timestamp") is None

    def test_cache_path_sanitizes_key(self, tmp_path) -> None:
        """Test that cache paths handle special characters."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)
        show = ShowResponse(
            id=1,
            slug="show/with/slashes",
            title="Show With Slashes",
            sort_title="Show With Slashes",
        )
        cache.save_show("show/with/slashes", show)

        # The path should have slashes replaced
        expected_path = tmp_path / "cache" / "shows" / "show_with_slashes.json"
        assert expected_path.exists()

        # And retrieval should still work
        retrieved = cache.get_show("show/with/slashes")
        assert retrieved is not None
        assert retrieved.slug == "show/with/slashes"

    def test_show_with_nested_seasons_and_episodes(self, tmp_path) -> None:
        """Test caching show with full nested structure."""
        cache = TVSportsDBCache(tmp_path / "cache", ttl_hours=12)
        show = ShowResponse(
            id=1,
            slug="full-show",
            title="Full Show",
            sort_title="Full Show",
            season_count=2,
            episode_count=4,
            seasons=[
                SeasonResponse(
                    id=10,
                    show_id=1,
                    number=1,
                    title="Season 1",
                    sort_title="Season 1",
                    episodes=[
                        EpisodeResponse(id=100, season_id=10, number=1, title="Ep1", aliases=["E1"]),
                        EpisodeResponse(id=101, season_id=10, number=2, title="Ep2"),
                    ],
                ),
                SeasonResponse(
                    id=20,
                    show_id=1,
                    number=2,
                    title="Season 2",
                    sort_title="Season 2",
                    episodes=[
                        EpisodeResponse(id=200, season_id=20, number=1, title="Ep1"),
                        EpisodeResponse(id=201, season_id=20, number=2, title="Ep2"),
                    ],
                ),
            ],
        )
        cache.save_show("full-show", show)

        retrieved = cache.get_show("full-show")
        assert retrieved is not None
        assert len(retrieved.seasons) == 2
        assert len(retrieved.seasons[0].episodes) == 2
        assert len(retrieved.seasons[1].episodes) == 2
        assert retrieved.seasons[0].episodes[0].aliases == ["E1"]
