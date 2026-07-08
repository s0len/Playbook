"""Tests for local fallback artwork resolution and upload."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from playbook.local_assets import LocalAssetResolver, asset_content_type
from playbook.models import Episode, Season, Show
from playbook.plex_client import PLEX_TYPE_SEASON, PlexSyncStats
from playbook.plex_metadata_sync import MappedMetadata, _apply_metadata


def _make_show(key: str = "ufc-2026") -> Show:
    return Show(key=key, title="UFC 2026", summary=None, seasons=[])


def _make_season(index: int = 3, display_number: int | None = 3) -> Season:
    return Season(
        key=str(index),
        title=f"Season {index}",
        summary=None,
        index=index,
        episodes=[],
        display_number=display_number,
    )


def _make_episode(index: int = 2, display_number: int | None = 2) -> Episode:
    return Episode(
        title=f"Episode {index}",
        summary=None,
        originally_available=None,
        index=index,
        display_number=display_number,
    )


class TestAssetContentType:
    def test_jpg(self) -> None:
        assert asset_content_type(Path("poster.jpg")) == "image/jpeg"

    def test_png(self) -> None:
        assert asset_content_type(Path("poster.png")) == "image/png"

    def test_webp(self) -> None:
        assert asset_content_type(Path("poster.webp")) == "image/webp"

    def test_unknown_defaults_to_jpeg(self) -> None:
        assert asset_content_type(Path("poster.unknown")) == "image/jpeg"


class TestLocalAssetResolver:
    def test_disabled_without_dir(self) -> None:
        resolver = LocalAssetResolver(None)
        assert resolver.enabled is False
        assert resolver.show_poster(_make_show()) is None

    def test_enabled_with_dir(self, tmp_path: Path) -> None:
        assert LocalAssetResolver(tmp_path).enabled is True

    def test_show_poster_and_background(self, tmp_path: Path) -> None:
        show_dir = tmp_path / "ufc-2026"
        show_dir.mkdir()
        (show_dir / "poster.jpg").write_bytes(b"poster")
        (show_dir / "background.png").write_bytes(b"background")

        resolver = LocalAssetResolver(tmp_path)
        assert resolver.show_poster(_make_show()) == show_dir / "poster.jpg"
        assert resolver.show_background(_make_show()) == show_dir / "background.png"

    def test_season_poster_zero_padded(self, tmp_path: Path) -> None:
        show_dir = tmp_path / "ufc-2026"
        show_dir.mkdir()
        (show_dir / "season-03.jpg").write_bytes(b"season")

        resolver = LocalAssetResolver(tmp_path)
        assert resolver.season_poster(_make_show(), _make_season(3)) == show_dir / "season-03.jpg"

    def test_season_poster_unpadded(self, tmp_path: Path) -> None:
        show_dir = tmp_path / "ufc-2026"
        show_dir.mkdir()
        (show_dir / "season-3.webp").write_bytes(b"season")

        resolver = LocalAssetResolver(tmp_path)
        assert resolver.season_poster(_make_show(), _make_season(3)) == show_dir / "season-3.webp"

    def test_season_poster_uses_display_number(self, tmp_path: Path) -> None:
        show_dir = tmp_path / "ufc-2026"
        show_dir.mkdir()
        (show_dir / "season-07.jpg").write_bytes(b"season")

        resolver = LocalAssetResolver(tmp_path)
        season = _make_season(index=1, display_number=7)
        assert resolver.season_poster(_make_show(), season) == show_dir / "season-07.jpg"

    def test_episode_poster(self, tmp_path: Path) -> None:
        show_dir = tmp_path / "ufc-2026"
        show_dir.mkdir()
        (show_dir / "s03e02.jpg").write_bytes(b"episode")

        resolver = LocalAssetResolver(tmp_path)
        found = resolver.episode_poster(_make_show(), _make_season(3), _make_episode(2))
        assert found == show_dir / "s03e02.jpg"

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        resolver = LocalAssetResolver(tmp_path)
        assert resolver.show_poster(_make_show()) is None
        assert resolver.season_poster(_make_show(), _make_season(3)) is None
        assert resolver.episode_poster(_make_show(), _make_season(3), _make_episode(2)) is None

    def test_other_show_dir_not_matched(self, tmp_path: Path) -> None:
        other_dir = tmp_path / "nhl-2026"
        other_dir.mkdir()
        (other_dir / "season-03.jpg").write_bytes(b"season")

        resolver = LocalAssetResolver(tmp_path)
        assert resolver.season_poster(_make_show("ufc-2026"), _make_season(3)) is None


class TestPathTraversal:
    """show.key is API-supplied and must not escape the assets directory (fix #3)."""

    def test_parent_traversal_key_neutralized(self, tmp_path: Path) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "poster.jpg").write_bytes(b"secret")

        resolver = LocalAssetResolver(assets)
        # A naive `assets / "../outside"` would reach outside/poster.jpg.
        assert resolver.show_poster(_make_show("../outside")) is None

    def test_absolute_key_stays_within_assets(self, tmp_path: Path) -> None:
        assets = tmp_path / "assets"
        (assets / "etc").mkdir(parents=True)
        (assets / "etc" / "poster.jpg").write_bytes(b"contained")

        resolver = LocalAssetResolver(assets)
        # "/etc" is sanitized to the relative component "etc" *inside* assets,
        # so it resolves to the contained file, never the real /etc.
        found = resolver.show_poster(_make_show("/etc"))
        assert found == assets / "etc" / "poster.jpg"

    def test_symlink_escape_blocked(self, tmp_path: Path) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "poster.jpg").write_bytes(b"secret")
        # A symlink inside assets pointing out would pass is_file() but must be
        # rejected by the resolved-path containment check.
        (assets / "evil").symlink_to(outside, target_is_directory=True)

        resolver = LocalAssetResolver(assets)
        assert resolver.show_poster(_make_show("evil")) is None


class TestApplyMetadataWithLocalAssets:
    def _mapped(self, **overrides: object) -> MappedMetadata:
        defaults: dict[str, object] = {
            "title": None,
            "sort_title": None,
            "original_title": None,
            "originally_available_at": None,
            "summary": None,
            "poster_url": None,
            "background_url": None,
        }
        defaults.update(overrides)
        return MappedMetadata(**defaults)  # type: ignore[arg-type]

    def test_local_poster_uploaded_when_no_url(self, tmp_path: Path) -> None:
        poster = tmp_path / "season-03.jpg"
        poster.write_bytes(b"image-bytes")

        client = MagicMock()
        stats = PlexSyncStats()
        mapped = self._mapped(poster_file=poster)

        updated = _apply_metadata(
            client,
            "12345",
            mapped,
            type_code=PLEX_TYPE_SEASON,
            label="season 'Season 3'",
            dry_run=False,
            stats=stats,
        )

        assert updated is True
        expected_calls = [
            call.unlock_field("12345", "thumb"),
            call.upload_asset("12345", "thumb", b"image-bytes", content_type="image/jpeg"),
            call.lock_field("12345", "thumb"),
        ]
        assert client.mock_calls[-3:] == expected_calls
        client.set_asset.assert_not_called()
        assert stats.assets_updated == 1
        assert stats.assets_failed == 0

    def test_api_url_takes_precedence_over_local_file(self, tmp_path: Path) -> None:
        poster = tmp_path / "poster.jpg"
        poster.write_bytes(b"image-bytes")

        client = MagicMock()
        stats = PlexSyncStats()
        mapped = self._mapped(poster_url="https://example.com/poster.jpg", poster_file=poster)

        _apply_metadata(
            client,
            "12345",
            mapped,
            type_code=PLEX_TYPE_SEASON,
            label="season 'Season 3'",
            dry_run=False,
            stats=stats,
        )

        client.set_asset.assert_called_once_with("12345", "thumb", "https://example.com/poster.jpg")
        client.upload_asset.assert_not_called()

    def test_no_artwork_leaves_item_untouched(self) -> None:
        client = MagicMock()
        stats = PlexSyncStats()

        updated = _apply_metadata(
            client,
            "12345",
            self._mapped(),
            type_code=PLEX_TYPE_SEASON,
            label="season 'Season 3'",
            dry_run=False,
            stats=stats,
        )

        assert updated is False
        client.unlock_field.assert_not_called()
        client.set_asset.assert_not_called()
        client.upload_asset.assert_not_called()
        assert stats.assets_updated == 0

    def test_dry_run_does_not_upload(self, tmp_path: Path) -> None:
        poster = tmp_path / "poster.jpg"
        poster.write_bytes(b"image-bytes")

        client = MagicMock()
        stats = PlexSyncStats()

        _apply_metadata(
            client,
            "12345",
            self._mapped(poster_file=poster),
            type_code=PLEX_TYPE_SEASON,
            label="season 'Season 3'",
            dry_run=True,
            stats=stats,
        )

        client.upload_asset.assert_not_called()
        client.unlock_field.assert_not_called()

    def test_unreadable_file_counts_as_failure(self, tmp_path: Path) -> None:
        client = MagicMock()
        stats = PlexSyncStats()
        mapped = self._mapped(poster_file=tmp_path / "missing.jpg")

        _apply_metadata(
            client,
            "12345",
            mapped,
            type_code=PLEX_TYPE_SEASON,
            label="season 'Season 3'",
            dry_run=False,
            stats=stats,
        )

        client.upload_asset.assert_not_called()
        assert stats.assets_failed == 1
        assert stats.errors


class TestSyncShowFallbackWiring:
    def test_sync_show_uploads_local_fallback_poster(self, tmp_path: Path) -> None:
        """A show with no API artwork gets the local fallback uploaded during sync."""
        from playbook.metadata import MetadataChangeResult
        from playbook.plex_metadata_sync import PlexMetadataSync

        show_dir = tmp_path / "ufc-2026"
        show_dir.mkdir()
        (show_dir / "poster.jpg").write_bytes(b"local-poster")

        sync = object.__new__(PlexMetadataSync)
        sync.force = True
        sync.dry_run = False
        sync.asset_resolver = LocalAssetResolver(tmp_path)
        sync._library_id_resolved = None
        sync._client = MagicMock()
        sync._client.update_metadata.return_value = True

        show = _make_show("ufc-2026")
        show.metadata = {"url_poster": None}
        stats = PlexSyncStats()

        sync._sync_show(
            show=show,
            show_rating="12345",
            base_url="https://api.tvsportsdb.com",
            change=MetadataChangeResult(updated=True, changed_seasons=set(), changed_episodes={}),
            is_first_sync=True,
            stats=stats,
        )

        sync._client.upload_asset.assert_called_once_with("12345", "thumb", b"local-poster", content_type="image/jpeg")
        assert stats.assets_updated == 1


class TestFallbackAssetsConfig:
    def test_default_is_none(self) -> None:
        from playbook.config import PlexMetadataSyncSettings

        assert PlexMetadataSyncSettings().fallback_assets_dir is None

    def test_parsed_from_config(self) -> None:
        from playbook.config import _build_plex_metadata_sync_settings

        settings = _build_plex_metadata_sync_settings({"enabled": True, "fallback_assets_dir": "/config/assets"})
        assert settings.fallback_assets_dir == "/config/assets"

    def test_rejects_non_string(self) -> None:
        from playbook.config import _build_plex_metadata_sync_settings

        with pytest.raises(ValueError, match="fallback_assets_dir"):
            _build_plex_metadata_sync_settings({"fallback_assets_dir": 123})
