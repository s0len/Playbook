from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from playbook.config import AppConfig, KometaTriggerSettings, MetadataConfig, PatternConfig, Settings, SportConfig
from playbook.metadata import (
    MetadataChangeResult,
    MetadataFingerprintStore,
    MetadataNormalizer,
    ShowFingerprint,
    compute_show_fingerprint,
    compute_show_fingerprint_cached,
)
from playbook.models import Episode, ProcessingStats, Season, Show
from playbook.processor import Processor
from playbook.utils import sanitize_component


def _build_raw_metadata(episode_number: int) -> dict:
    return {
        "metadata": {
            "demo": {
                "title": "Demo Series",
                "seasons": {
                    "01": {
                        "title": "Season 1",
                        "episodes": [
                            {
                                "title": "Race",
                                "episode_number": episode_number,
                            }
                        ],
                    }
                },
            }
        }
    }


def _make_processor(tmp_path, *, dry_run: bool = True) -> Processor:
    settings = Settings(
        source_dir=tmp_path / "source",
        destination_dir=tmp_path / "dest",
        cache_dir=tmp_path / "cache",
        dry_run=dry_run,
    )
    settings.source_dir.mkdir(parents=True, exist_ok=True)
    settings.destination_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    config = AppConfig(settings=settings, sports=[])
    return Processor(config, enable_notifications=False)


def test_metadata_fingerprint_tracks_episode_changes(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    settings = Settings(
        source_dir=tmp_path / "src",
        destination_dir=tmp_path / "dest",
        cache_dir=cache_dir,
    )

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="demo")
    normalizer = MetadataNormalizer(metadata_cfg)

    raw_v1 = {
        "metadata": {
            "demo": {
                "title": "Demo Series",
                "seasons": {
                    "01": {
                        "title": "Season 1",
                        "episodes": [
                            {
                                "title": "Qualifying",
                                "summary": "Initial",
                                "episode_number": 1,
                            }
                        ],
                    }
                },
            }
        }
    }
    raw_v2 = {
        "metadata": {
            "demo": {
                "title": "Demo Series",
                "seasons": {
                    "01": {
                        "title": "Season 1",
                        "episodes": [
                            {
                                "title": "Qualifying",
                                "summary": "Updated",
                                "episode_number": 1,
                            }
                        ],
                    }
                },
            }
        }
    }

    fingerprint_v1 = compute_show_fingerprint(normalizer.load_show(raw_v1), metadata_cfg)
    fingerprint_v2 = compute_show_fingerprint(normalizer.load_show(raw_v2), metadata_cfg)

    store = MetadataFingerprintStore(settings.cache_dir)

    initial = store.update("demo", fingerprint_v1)
    assert initial.updated is True
    assert initial.changed_seasons == set()
    assert initial.changed_episodes == {}
    assert initial.invalidate_all is False

    change = store.update("demo", fingerprint_v2)
    assert change.updated is True
    assert change.changed_seasons == set()
    assert change.invalidate_all is False
    assert set(change.changed_episodes.keys()) == {"01"}
    episode_key = next(iter(fingerprint_v1.episode_hashes["01"].keys()))
    assert change.changed_episodes["01"] == {episode_key}


def test_processor_removes_changed_entries_when_metadata_changes(tmp_path, monkeypatch) -> None:
    settings = Settings(
        source_dir=tmp_path / "source",
        destination_dir=tmp_path / "dest",
        cache_dir=tmp_path / "cache",
    )
    settings.source_dir.mkdir(parents=True)
    settings.destination_dir.mkdir(parents=True)
    settings.cache_dir.mkdir(parents=True)

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="demo")
    sport = SportConfig(id="demo", name="Demo", metadata=metadata_cfg)
    config = AppConfig(settings=settings, sports=[sport])

    normalizer = MetadataNormalizer(metadata_cfg)
    raw_v1 = _build_raw_metadata(1)
    raw_v2 = _build_raw_metadata(2)
    fingerprint_v1 = compute_show_fingerprint(normalizer.load_show(raw_v1), metadata_cfg)
    fingerprint_v2 = compute_show_fingerprint(normalizer.load_show(raw_v2), metadata_cfg)

    state_dir = settings.cache_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "metadata-digests.json").write_text(json.dumps({"demo": fingerprint_v1.to_dict()}))

    call_counter = {"value": 0}

    def fake_load_show(settings_arg, metadata_cfg_arg, **kwargs):
        index = 0 if call_counter["value"] == 0 else 1
        call_counter["value"] += 1
        raw = raw_v1 if index == 0 else raw_v2
        return normalizer.load_show(raw)

    monkeypatch.setattr("playbook.processor.load_show", fake_load_show)

    processor = Processor(config, enable_notifications=False)
    remove_calls: list[dict[str, MetadataChangeResult]] = []
    original_remove = processor.processed_cache.remove_by_metadata_changes

    def tracking_remove(self, changes):
        remove_calls.append(dict(changes))
        return original_remove(changes)

    monkeypatch.setattr(
        type(processor.processed_cache),
        "remove_by_metadata_changes",
        tracking_remove,
    )

    processor.process_all()
    assert remove_calls == []
    assert call_counter["value"] == 1

    processor.process_all()
    assert len(remove_calls) == 1
    demo_change = remove_calls[0]["demo"]
    assert demo_change.changed_seasons == set()
    assert set(demo_change.changed_episodes.keys()) == {"01"}
    episode_key = next(iter(fingerprint_v1.episode_hashes["01"].keys()))
    assert demo_change.changed_episodes["01"] == {episode_key}
    assert demo_change.invalidate_all is False
    assert call_counter["value"] == 2
    assert processor.metadata_fingerprints.get("demo") == fingerprint_v2


def test_detailed_summary_groups_counts_with_info(tmp_path, caplog) -> None:
    processor = _make_processor(tmp_path)
    stats = ProcessingStats()
    detail_token = "IGNORED_DETAIL_ENTRY"
    stats.register_ignored(detail_token, sport_id="sport-a")
    stats.register_warning("demo: sport-a: warn", sport_id="sport-a")
    stats.register_error("demo: sport-a: error", sport_id="sport-a")
    stats.register_skipped("skip reason", is_error=False)

    from playbook import processor as processor_module

    original_level = processor_module.LOGGER.level
    processor_module.LOGGER.setLevel(logging.INFO)
    try:
        with caplog.at_level(logging.INFO, logger="playbook.processor"):
            processor._log_detailed_summary(stats)
    finally:
        processor_module.LOGGER.setLevel(original_level)

    text = caplog.text
    assert "Detailed Summary" in text
    assert "sport-a: 1 entry" in text
    assert detail_token not in text
    assert "Run with --verbose for per-warning details." in text


def test_detailed_summary_shows_details_with_debug(tmp_path, caplog) -> None:
    processor = _make_processor(tmp_path)
    stats = ProcessingStats()
    detail_token = "IGNORED_DETAIL_ENTRY"
    stats.register_ignored(detail_token, sport_id="sport-a")
    stats.register_warning("demo: sport-a: warn", sport_id="sport-a")

    from playbook import processor as processor_module

    original_level = processor_module.LOGGER.level
    processor_module.LOGGER.setLevel(logging.DEBUG)
    try:
        with caplog.at_level(logging.DEBUG, logger="playbook.processor"):
            processor._log_detailed_summary(stats, level=logging.DEBUG)
    finally:
        processor_module.LOGGER.setLevel(original_level)

    text = caplog.text
    assert detail_token in text
    assert "demo: sport-a: warn" in text


def test_run_recap_lists_destinations(tmp_path, caplog) -> None:
    processor = _make_processor(tmp_path)
    stats = ProcessingStats()
    stats.register_processed()
    processor._touched_destinations = {"Demo/Season 01/Race.mkv"}

    with caplog.at_level(logging.INFO, logger="playbook.processor"):
        processor._log_run_recap(stats, duration=1.25)

    text = caplog.text
    assert "Run Recap" in text
    # Plex sync status is always shown (disabled when not configured)
    assert "Plex Sync" in text
    assert "Demo/Season 01/Race.mkv" in text


def test_metadata_change_relinks_and_removes_old_destination(tmp_path, monkeypatch) -> None:
    settings = Settings(
        source_dir=tmp_path / "source",
        destination_dir=tmp_path / "dest",
        cache_dir=tmp_path / "cache",
    )
    settings.source_dir.mkdir(parents=True)
    settings.destination_dir.mkdir(parents=True)
    settings.cache_dir.mkdir(parents=True)

    source_file = settings.source_dir / "demo.r01.qualifying.mkv"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"demo")

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="demo")
    pattern = PatternConfig(
        regex=r"(?i)^demo\.r(?P<round>\d{2})\.(?P<session>qualifying)\.mkv$",
    )
    sport = SportConfig(id="demo", name="Demo", metadata=metadata_cfg, patterns=[pattern])
    config = AppConfig(settings=settings, sports=[sport])

    normalizer = MetadataNormalizer(metadata_cfg)

    def build_metadata(episode_number: int) -> dict:
        return {
            "metadata": {
                "demo": {
                    "title": "Demo Series",
                    "seasons": {
                        "01": {
                            "title": "Season 1",
                            "episodes": [
                                {
                                    "title": "Qualifying",
                                    "episode_number": episode_number,
                                }
                            ],
                        }
                    },
                }
            }
        }

    raw_v1 = build_metadata(1)
    raw_v2 = build_metadata(2)

    call_counter = {"value": 0}

    def fake_load_show(settings_arg, metadata_cfg_arg, **kwargs):
        index = 0 if call_counter["value"] == 0 else 1
        call_counter["value"] += 1
        raw = raw_v1 if index == 0 else raw_v2
        return normalizer.load_show(raw)

    monkeypatch.setattr("playbook.processor.load_show", fake_load_show)

    processor = Processor(config, enable_notifications=False)
    processor.process_all()

    old_destination = settings.destination_dir / "Demo Series" / "01 Season 1" / "Demo Series - S01E01 - Qualifying.mkv"
    assert old_destination.exists()

    processor.process_all()

    new_destination = settings.destination_dir / "Demo Series" / "01 Season 1" / "Demo Series - S01E02 - Qualifying.mkv"

    assert new_destination.exists()
    assert not old_destination.exists()


def test_skips_mac_resource_fork_files(tmp_path, monkeypatch) -> None:
    settings = Settings(
        source_dir=tmp_path / "source",
        destination_dir=tmp_path / "dest",
        cache_dir=tmp_path / "cache",
        dry_run=True,
    )
    settings.source_dir.mkdir(parents=True)
    settings.destination_dir.mkdir(parents=True)
    settings.cache_dir.mkdir(parents=True)

    noise_file = settings.source_dir / "._demo.r01.qualifying.mkv"
    noise_file.write_bytes(b"meta")
    valid_file = settings.source_dir / "demo.r01.qualifying.mkv"
    valid_file.write_bytes(b"video")

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="demo")
    pattern = PatternConfig(
        regex=r"(?i)^demo\.r(?P<round>\d{2})\.(?P<session>qualifying)\.mkv$",
    )
    sport = SportConfig(id="demo", name="Demo", metadata=metadata_cfg, patterns=[pattern])
    config = AppConfig(settings=settings, sports=[sport])

    episode = Episode(
        title="Qualifying",
        summary=None,
        originally_available=None,
        index=1,
        display_number=1,
    )
    season = Season(
        key="01",
        title="Season 1",
        summary=None,
        index=1,
        episodes=[episode],
        display_number=1,
        round_number=1,
    )
    show = Show(key="demo", title="Demo Series", summary=None, seasons=[season])

    monkeypatch.setattr("playbook.processor.load_show", lambda settings_arg, metadata_cfg_arg, **kwargs: show)
    monkeypatch.setattr(
        "playbook.processor.compute_show_fingerprint",
        lambda show_arg, metadata_cfg_arg: ShowFingerprint(digest="fingerprint", season_hashes={}, episode_hashes={}),
    )

    processor = Processor(config, enable_notifications=False)
    stats = processor.process_all()

    assert stats.processed == 1
    assert stats.skipped == 0
    assert stats.ignored == 0
    assert stats.errors == []
    assert stats.warnings == []


def test_destination_stays_within_root_for_hostile_metadata(tmp_path, monkeypatch) -> None:
    settings = Settings(
        source_dir=tmp_path / "source",
        destination_dir=tmp_path / "dest",
        cache_dir=tmp_path / "cache",
    )
    settings.source_dir.mkdir(parents=True)
    settings.destination_dir.mkdir(parents=True)
    settings.cache_dir.mkdir(parents=True)

    source_file = settings.source_dir / "demo.r01.qualifying.mkv"
    source_file.write_bytes(b"payload")

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="demo")
    pattern = PatternConfig(
        regex=r"(?i)^demo\.r(?P<round>\d{2})\.(?P<session>qualifying)\.mkv$",
    )
    sport = SportConfig(id="demo", name="Demo", metadata=metadata_cfg, patterns=[pattern])
    config = AppConfig(settings=settings, sports=[sport])

    episode = Episode(
        title="../Episode",
        summary=None,
        originally_available=None,
        index=1,
        display_number=1,
        aliases=["qualifying"],
    )
    season = Season(
        key="01",
        title="..",
        summary=None,
        index=1,
        episodes=[episode],
        display_number=1,
        round_number=1,
    )
    show = Show(key="demo", title="../Evil Series", summary=None, seasons=[season])

    monkeypatch.setattr("playbook.processor.load_show", lambda *args, **kwargs: show)
    monkeypatch.setattr(
        "playbook.processor.compute_show_fingerprint",
        lambda *args, **kwargs: ShowFingerprint(digest="fingerprint", season_hashes={}, episode_hashes={}),
    )

    processor = Processor(config, enable_notifications=False)
    stats = processor.process_all()

    assert stats.processed == 1
    files = [path for path in settings.destination_dir.rglob("*") if path.is_file()]
    assert len(files) == 1
    destination = files[0]

    base_resolved = settings.destination_dir.resolve()
    assert destination.resolve().is_relative_to(base_resolved)

    relative_parts = destination.relative_to(settings.destination_dir).parts
    assert all(part not in {".", ".."} for part in relative_parts)
    expected_root = sanitize_component(show.title)
    expected_season_template = f"{season.display_number:02d} {season.title}"
    expected_season = sanitize_component(expected_season_template)
    expected_episode_template = (
        f"{show.title} - S{season.display_number:02d}E{episode.display_number:02d} - {episode.title}.mkv"
    )
    expected_episode = sanitize_component(expected_episode_template)

    assert relative_parts[0] == expected_root
    assert relative_parts[1] == expected_season
    assert relative_parts[2] == expected_episode


def test_symlink_sources_are_skipped(tmp_path, monkeypatch) -> None:
    settings = Settings(
        source_dir=tmp_path / "source",
        destination_dir=tmp_path / "dest",
        cache_dir=tmp_path / "cache",
        dry_run=True,
    )
    settings.source_dir.mkdir(parents=True)
    settings.destination_dir.mkdir(parents=True)
    settings.cache_dir.mkdir(parents=True)

    real_file = settings.source_dir / "demo.r01.qualifying.mkv"
    real_file.write_bytes(b"video")

    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    symlink_path = settings.source_dir / "symlink.mkv"
    try:
        symlink_path.symlink_to(outside)
    except OSError as exc:  # pragma: no cover - platform specific guard
        pytest.skip(f"symlinks not supported: {exc}")

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="demo")
    pattern = PatternConfig(
        regex=r"(?i)^demo\.r(?P<round>\d{2})\.(?P<session>qualifying)\.mkv$",
    )
    sport = SportConfig(id="demo", name="Demo", metadata=metadata_cfg, patterns=[pattern])
    config = AppConfig(settings=settings, sports=[sport])

    episode = Episode(
        title="Qualifying",
        summary=None,
        originally_available=None,
        index=1,
        display_number=1,
    )
    season = Season(
        key="01",
        title="Season 1",
        summary=None,
        index=1,
        episodes=[episode],
        display_number=1,
        round_number=1,
    )
    show = Show(key="demo", title="Demo Series", summary=None, seasons=[season])

    monkeypatch.setattr("playbook.processor.load_show", lambda *args, **kwargs: show)
    monkeypatch.setattr(
        "playbook.processor.compute_show_fingerprint",
        lambda *args, **kwargs: ShowFingerprint(digest="fingerprint", season_hashes={}, episode_hashes={}),
    )

    processor = Processor(config, enable_notifications=False)
    stats = processor.process_all()

    assert stats.processed == 1
    assert stats.skipped == 0
    assert stats.ignored == 0
    assert stats.errors == []
    assert stats.warnings == []


def test_should_suppress_sample_variants() -> None:
    assert Processor._should_suppress_sample_ignored(Path("sample.mkv"))
    assert Processor._should_suppress_sample_ignored(
        Path("nba.2025.11.08.chicago.bulls.vs.cleveland.cavaliers.1080p.web.h264-gametime-sample.mkv")
    )
    assert Processor._should_suppress_sample_ignored(Path("nba.sample.1080p.web.h264-gametime.mkv"))
    assert not Processor._should_suppress_sample_ignored(Path("nba.sampleshow.1080p.mkv"))
    assert not Processor._should_suppress_sample_ignored(Path("nba.example.1080p.mkv"))


def test_processor_triggers_post_run_when_needed(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    cache_dir.mkdir()
    source_dir.mkdir()
    dest_dir.mkdir()

    kometa_settings = KometaTriggerSettings(enabled=True)
    settings = Settings(
        source_dir=source_dir,
        destination_dir=dest_dir,
        cache_dir=cache_dir,
        kometa_trigger=kometa_settings,
    )
    config = AppConfig(settings=settings, sports=[])

    class DummyTrigger:
        def __init__(self) -> None:
            self.enabled = True
            self.calls = 0

        def trigger(self, *_, **__) -> bool:
            self.calls += 1
            return True

    dummy_trigger = DummyTrigger()
    monkeypatch.setattr("playbook.processor.build_kometa_trigger", lambda _settings: dummy_trigger)

    processor = Processor(config, enable_notifications=False)
    stats = ProcessingStats(processed=2)

    processor._kometa_trigger = dummy_trigger
    processor._kometa_trigger_fired = False
    processor._kometa_trigger_needed = True
    processor._trigger_post_run_trigger_if_needed(stats)

    assert dummy_trigger.calls == 1


def test_processor_post_run_skips_when_not_needed(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    cache_dir.mkdir()
    source_dir.mkdir()
    dest_dir.mkdir()

    kometa_settings = KometaTriggerSettings(enabled=True)
    settings = Settings(
        source_dir=source_dir,
        destination_dir=dest_dir,
        cache_dir=cache_dir,
        kometa_trigger=kometa_settings,
    )
    config = AppConfig(settings=settings, sports=[])

    class DummyTrigger:
        def __init__(self) -> None:
            self.enabled = True
            self.calls = 0

        def trigger(self, *_, **__) -> bool:
            self.calls += 1
            return True

    dummy_trigger = DummyTrigger()
    monkeypatch.setattr("playbook.processor.build_kometa_trigger", lambda _settings: dummy_trigger)

    processor = Processor(config, enable_notifications=False)
    stats = ProcessingStats(processed=0)

    processor._kometa_trigger = dummy_trigger
    processor._kometa_trigger_fired = False
    processor._kometa_trigger_needed = False
    processor._trigger_post_run_trigger_if_needed(stats)

    assert dummy_trigger.calls == 0


def test_ts_extension_is_processed_correctly(tmp_path, monkeypatch) -> None:
    """Verify .ts (MPEG Transport Stream) files are processed with default extensions."""
    settings = Settings(
        source_dir=tmp_path / "source",
        destination_dir=tmp_path / "dest",
        cache_dir=tmp_path / "cache",
        dry_run=True,
    )
    settings.source_dir.mkdir(parents=True)
    settings.destination_dir.mkdir(parents=True)
    settings.cache_dir.mkdir(parents=True)

    # Create a .ts file (MPEG Transport Stream format)
    ts_file = settings.source_dir / "demo.r01.qualifying.ts"
    ts_file.write_bytes(b"video")

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="demo")
    pattern = PatternConfig(
        regex=r"(?i)^demo\.r(?P<round>\d{2})\.(?P<session>qualifying)\.ts$",
    )
    # Note: source_extensions defaults to [".mkv", ".mp4", ".ts", ".m4v", ".avi"]
    sport = SportConfig(id="demo", name="Demo", metadata=metadata_cfg, patterns=[pattern])
    config = AppConfig(settings=settings, sports=[sport])

    episode = Episode(
        title="Qualifying",
        summary=None,
        originally_available=None,
        index=1,
        display_number=1,
    )
    season = Season(
        key="01",
        title="Season 1",
        summary=None,
        index=1,
        episodes=[episode],
        display_number=1,
        round_number=1,
    )
    show = Show(key="demo", title="Demo Series", summary=None, seasons=[season])

    monkeypatch.setattr("playbook.processor.load_show", lambda *args, **kwargs: show)
    monkeypatch.setattr(
        "playbook.processor.compute_show_fingerprint",
        lambda *args, **kwargs: ShowFingerprint(digest="fingerprint", season_hashes={}, episode_hashes={}),
    )

    processor = Processor(config, enable_notifications=False)
    stats = processor.process_all()

    # Verify .ts file was processed successfully
    assert stats.processed == 1
    assert stats.skipped == 0
    assert stats.ignored == 0
    assert stats.errors == []
    assert stats.warnings == []


class TestSummarizePlexErrors:
    """Tests for Processor._summarize_plex_errors."""

    def test_summarize_plex_errors_empty_list(self) -> None:
        result = Processor._summarize_plex_errors([])
        assert result == []

    def test_summarize_plex_errors_groups_by_category(self) -> None:
        errors = [
            "Show not found: 'F1' in library 1 (metadata: http://example.com/f1.yaml). Similar: Formula 1",
            "Show not found: 'NBA' in library 2 (metadata: http://example.com/nba.yaml). Similar: NBA Games",
            "Season not found: S01 in show 'Demo' | library=1 | source=http://example.com. Available: S02, S03",
        ]
        result = Processor._summarize_plex_errors(errors)

        # Should have 2 groups: "Show not found" (2 items) and "Season not found" (1 item)
        assert len(result) == 4  # 2 lines for show group + 2 lines for season
        assert any("2×" in line and "Show not found" in line for line in result)
        assert any("Season not found" in line for line in result)

    def test_summarize_plex_errors_single_error_no_grouping(self) -> None:
        errors = [
            "Show not found: 'F1' in library 1 (metadata: http://example.com/f1.yaml). Similar: Formula 1",
        ]
        result = Processor._summarize_plex_errors(errors)

        # Single error should not have count prefix
        assert len(result) == 1
        assert "×" not in result[0]
        assert "Show not found" in result[0]

    def test_summarize_plex_errors_respects_limit(self) -> None:
        errors = [
            "Type A: error 1",
            "Type B: error 2",
            "Type C: error 3",
            "Type D: error 4",
        ]
        result = Processor._summarize_plex_errors(errors, limit=2)

        # Should show only 2 error types and a "more" message
        assert any("2 more error types" in line for line in result)

    def test_summarize_plex_errors_extracts_show_context(self) -> None:
        errors = [
            "Show not found: 'Formula 1' in library 5 (metadata: http://example.com/metadata.yaml). Similar: F1, Formula One",
        ]
        result = Processor._summarize_plex_errors(errors)

        assert len(result) == 1
        # Should contain extracted context
        assert "'Formula 1'" in result[0]
        assert "library=5" in result[0]
        assert "similar=" in result[0]

    def test_summarize_plex_errors_extracts_season_context(self) -> None:
        errors = [
            "Season not found: S01 in show 'Demo Series' | library=3 | source=http://example.com/demo.yaml. Available: S02, S03",
        ]
        result = Processor._summarize_plex_errors(errors)

        assert len(result) == 1
        assert "S01" in result[0]
        assert "show='Demo Series'" in result[0]
        assert "library=3" in result[0]
        assert "plex has=" in result[0]

    def test_summarize_plex_errors_extracts_episode_context(self) -> None:
        errors = [
            "Episode not found: E05 in season S01 of 'Demo Series' | library=2 | source=http://example.com/demo.yaml. Available: E01, E02, E03",
        ]
        result = Processor._summarize_plex_errors(errors)

        assert len(result) == 1
        assert "E05" in result[0]
        assert "season=S01" in result[0]
        assert "show='Demo Series'" in result[0]
        assert "plex has=" in result[0]

    def test_summarize_plex_errors_fallback_for_unrecognized(self) -> None:
        errors = [
            "Unknown error format that does not match patterns",
        ]
        result = Processor._summarize_plex_errors(errors)

        assert len(result) == 1
        assert "Unknown error format" in result[0]

    def test_summarize_plex_errors_truncates_long_errors(self) -> None:
        long_error = "Category: " + "x" * 100
        errors = [long_error]
        result = Processor._summarize_plex_errors(errors)

        assert len(result) == 1
        # Should be truncated to ~80 chars with "..."
        assert len(result[0]) < len(long_error)
        assert "..." in result[0]


class TestExtractErrorContext:
    """Tests for Processor._extract_error_context."""

    def test_extract_show_not_found_context(self) -> None:
        error = (
            "Show not found: 'Formula 1' in library 5 (metadata: http://example.com/f1.yaml). Similar: F1, Formula One"
        )
        result = Processor._extract_error_context(error)

        assert result is not None
        assert "'Formula 1'" in result
        assert "library=5" in result
        assert "similar=[F1, Formula One]" in result
        assert "source=" in result

    def test_extract_show_not_found_without_similar(self) -> None:
        error = "Show not found: 'Demo' in library 1 (metadata: http://example.com/demo.yaml)."
        result = Processor._extract_error_context(error)

        assert result is not None
        assert "'Demo'" in result
        assert "library=1" in result
        assert "similar" not in result

    def test_extract_show_not_found_truncates_long_url(self) -> None:
        long_url = "http://example.com/" + "a" * 50 + "/metadata.yaml"
        error = f"Show not found: 'Demo' in library 1 (metadata: {long_url})."
        result = Processor._extract_error_context(error)

        assert result is not None
        assert "..." in result  # URL should be truncated
        assert len(result) < len(error)

    def test_extract_season_not_found_context(self) -> None:
        error = "Season not found: S01 in show 'Demo Series' | library=3 | source=http://example.com/demo.yaml. Available: S02, S03"
        result = Processor._extract_error_context(error)

        assert result is not None
        assert "S01" in result
        assert "show='Demo Series'" in result
        assert "library=3" in result
        assert "plex has=[S02, S03]" in result

    def test_extract_season_not_found_without_available(self) -> None:
        error = "Season not found: S01 in show 'Demo Series' | library=3 | source=http://example.com/demo.yaml."
        result = Processor._extract_error_context(error)

        assert result is not None
        assert "S01" in result
        assert "show='Demo Series'" in result
        assert "plex has" not in result

    def test_extract_episode_not_found_context(self) -> None:
        error = "Episode not found: E05 in season S01 of 'Demo Series' | library=2 | source=http://example.com/demo.yaml. Available: E01, E02, E03"
        result = Processor._extract_error_context(error)

        assert result is not None
        assert "E05" in result
        assert "season=S01" in result
        assert "show='Demo Series'" in result
        assert "plex has=[E01, E02, E03]" in result

    def test_extract_episode_not_found_without_available(self) -> None:
        error = (
            "Episode not found: E05 in season S01 of 'Demo Series' | library=2 | source=http://example.com/demo.yaml."
        )
        result = Processor._extract_error_context(error)

        assert result is not None
        assert "E05" in result
        assert "season=S01" in result
        assert "plex has" not in result

    def test_extract_returns_none_for_unrecognized_pattern(self) -> None:
        error = "Some random error message that doesn't match any pattern"
        result = Processor._extract_error_context(error)

        assert result is None

    def test_extract_returns_none_for_partial_match(self) -> None:
        # Error starts like show not found but doesn't have full format
        error = "Show not found: some incomplete format"
        result = Processor._extract_error_context(error)

        assert result is None


def test_show_fingerprint_content_hash_serialization_roundtrip() -> None:
    """Test that ShowFingerprint.to_dict() and from_dict() correctly handle content_hash."""
    # Test with content_hash present
    fingerprint_with_hash = ShowFingerprint(
        digest="abc123",
        season_hashes={"01": "hash1", "02": "hash2"},
        episode_hashes={
            "01": {"ep1": "ep_hash1", "ep2": "ep_hash2"},
            "02": {"ep3": "ep_hash3"},
        },
        content_hash="content_abc123",
    )

    # Serialize to dict
    serialized = fingerprint_with_hash.to_dict()

    # Verify content_hash is in serialized output
    assert "content_hash" in serialized
    assert serialized["content_hash"] == "content_abc123"
    assert serialized["digest"] == "abc123"
    assert serialized["seasons"] == {"01": "hash1", "02": "hash2"}

    # Deserialize back
    deserialized = ShowFingerprint.from_dict(serialized)

    # Verify content_hash survives roundtrip
    assert deserialized.content_hash == "content_abc123"
    assert deserialized.digest == "abc123"
    assert deserialized.season_hashes == {"01": "hash1", "02": "hash2"}
    assert deserialized.episode_hashes == {
        "01": {"ep1": "ep_hash1", "ep2": "ep_hash2"},
        "02": {"ep3": "ep_hash3"},
    }


def test_show_fingerprint_backward_compatibility_without_content_hash() -> None:
    """Test backward compatibility with old format (no content_hash)."""
    # Simulate old format without content_hash
    old_format_dict = {
        "digest": "xyz789",
        "seasons": {"01": "season_hash"},
        "episodes": {"01": {"ep1": "episode_hash"}},
    }

    # Should deserialize without error
    fingerprint = ShowFingerprint.from_dict(old_format_dict)

    # content_hash should be None for backward compatibility
    assert fingerprint.content_hash is None
    assert fingerprint.digest == "xyz789"
    assert fingerprint.season_hashes == {"01": "season_hash"}
    assert fingerprint.episode_hashes == {"01": {"ep1": "episode_hash"}}

    # When serializing back, content_hash should not be included if None
    serialized = fingerprint.to_dict()
    assert "content_hash" not in serialized
    assert serialized["digest"] == "xyz789"


def test_compute_show_fingerprint_cached_returns_cached_when_content_matches() -> None:
    """Test that compute_show_fingerprint_cached() returns cached fingerprint when content matches."""
    # Setup metadata configuration
    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="demo")
    normalizer = MetadataNormalizer(metadata_cfg)

    # Create raw metadata
    raw_metadata = {
        "metadata": {
            "demo": {
                "title": "Demo Series",
                "seasons": {
                    "01": {
                        "title": "Season 1",
                        "episodes": [
                            {
                                "title": "Episode 1",
                                "summary": "First episode",
                                "episode_number": 1,
                            }
                        ],
                    }
                },
            }
        }
    }

    show = normalizer.load_show(raw_metadata)

    # Test 1: No cache exists - should compute new fingerprint with content_hash
    result_no_cache = compute_show_fingerprint_cached(show, metadata_cfg, cached_fingerprint=None)

    assert result_no_cache is not None
    assert result_no_cache.content_hash is not None
    assert result_no_cache.digest is not None
    assert result_no_cache.season_hashes is not None
    assert result_no_cache.episode_hashes is not None

    # Test 2: Cache exists with matching content_hash - should return cached fingerprint
    cached_fingerprint = result_no_cache
    result_cache_hit = compute_show_fingerprint_cached(show, metadata_cfg, cached_fingerprint=cached_fingerprint)

    # Should return the exact same cached fingerprint object (cache hit)
    assert result_cache_hit is cached_fingerprint
    assert result_cache_hit.content_hash == cached_fingerprint.content_hash
    assert result_cache_hit.digest == cached_fingerprint.digest

    # Test 3: Content changes - should compute new fingerprint
    modified_metadata = {
        "metadata": {
            "demo": {
                "title": "Demo Series",
                "seasons": {
                    "01": {
                        "title": "Season 1",
                        "episodes": [
                            {
                                "title": "Episode 1",
                                "summary": "Updated summary",  # Changed content
                                "episode_number": 1,
                            }
                        ],
                    }
                },
            }
        }
    }

    modified_show = normalizer.load_show(modified_metadata)
    result_cache_miss = compute_show_fingerprint_cached(
        modified_show, metadata_cfg, cached_fingerprint=cached_fingerprint
    )

    # Should compute new fingerprint (cache miss)
    assert result_cache_miss is not cached_fingerprint
    assert result_cache_miss.content_hash != cached_fingerprint.content_hash
    assert result_cache_miss.digest != cached_fingerprint.digest
    assert result_cache_miss.content_hash is not None


def test_content_hash_determinism() -> None:
    """Test that content_hash is deterministic for same input and different for different input."""
    # Setup metadata configuration
    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="demo")
    normalizer = MetadataNormalizer(metadata_cfg)

    # Create raw metadata
    raw_metadata = {
        "metadata": {
            "demo": {
                "title": "Demo Series",
                "seasons": {
                    "01": {
                        "title": "Season 1",
                        "episodes": [
                            {
                                "title": "Episode 1",
                                "summary": "First episode",
                                "episode_number": 1,
                            }
                        ],
                    }
                },
            }
        }
    }

    # Test 1: Same metadata produces same content_hash (determinism)
    show1 = normalizer.load_show(raw_metadata)
    fingerprint1 = compute_show_fingerprint(show1, metadata_cfg)

    show2 = normalizer.load_show(raw_metadata)
    fingerprint2 = compute_show_fingerprint(show2, metadata_cfg)

    assert fingerprint1.content_hash is not None
    assert fingerprint2.content_hash is not None
    assert fingerprint1.content_hash == fingerprint2.content_hash, "Same metadata should produce same content_hash"

    # Test 2: Different metadata produces different content_hash
    different_metadata = {
        "metadata": {
            "demo": {
                "title": "Different Series",  # Changed title
                "seasons": {
                    "01": {
                        "title": "Season 1",
                        "episodes": [
                            {
                                "title": "Episode 1",
                                "summary": "First episode",
                                "episode_number": 1,
                            }
                        ],
                    }
                },
            }
        }
    }

    show3 = normalizer.load_show(different_metadata)
    fingerprint3 = compute_show_fingerprint(show3, metadata_cfg)

    assert fingerprint3.content_hash is not None
    assert fingerprint3.content_hash != fingerprint1.content_hash, (
        "Different metadata should produce different content_hash"
    )

    # Test 3: Different season_overrides produces different content_hash
    metadata_cfg_with_overrides = MetadataConfig(
        url="https://example.com/demo.yaml", show_key="demo", season_overrides={"01": "Custom Season"}
    )
    show4 = normalizer.load_show(raw_metadata)
    fingerprint4 = compute_show_fingerprint(show4, metadata_cfg_with_overrides)

    assert fingerprint4.content_hash is not None
    assert fingerprint4.content_hash != fingerprint1.content_hash, (
        "Different season_overrides should produce different content_hash"
    )
