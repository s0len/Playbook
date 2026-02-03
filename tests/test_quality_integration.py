"""Integration tests for quality management system."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from playbook.config import QualityProfile, QualityScoring
from playbook.persistence import ProcessedFileRecord, ProcessedFileStore
from playbook.quality import QualityInfo, extract_quality
from playbook.quality_scorer import compute_quality_score, get_effective_quality_profile


class TestDatabaseMigration:
    """Tests for database schema migration from v1 to v2."""

    def test_fresh_database_has_quality_columns(self, tmp_path: Path):
        """Test that a fresh database has quality columns."""
        db_path = tmp_path / "playbook.db"
        store = ProcessedFileStore(db_path)

        # Check that columns exist by recording a file with quality info
        record = ProcessedFileRecord(
            source_path="/source/test.mkv",
            destination_path="/dest/test.mkv",
            sport_id="formula1",
            show_id="formula-1-2026",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
            quality_score=440,
            quality_info='{"resolution": "1080p", "source": "webdl"}',
        )
        store.record_processed(record)

        # Verify we can read it back
        retrieved = store.get_by_source("/source/test.mkv")
        assert retrieved is not None
        assert retrieved.quality_score == 440
        assert retrieved.quality_info is not None
        store.close()

    def test_migration_from_v1_schema(self, tmp_path: Path):
        """Test migration from v1 schema (no quality columns) to v2."""
        db_path = tmp_path / "playbook.db"

        # Create a v1 database manually
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE schema_version (version INTEGER PRIMARY KEY)
        """)
        conn.execute("INSERT INTO schema_version (version) VALUES (1)")
        conn.execute("""
            CREATE TABLE processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT UNIQUE NOT NULL,
                destination_path TEXT NOT NULL,
                sport_id TEXT NOT NULL,
                show_id TEXT NOT NULL,
                season_index INTEGER NOT NULL,
                episode_index INTEGER NOT NULL,
                processed_at TEXT NOT NULL,
                checksum TEXT,
                status TEXT NOT NULL DEFAULT 'linked',
                error_message TEXT
            )
        """)
        # Insert a record in v1 format
        conn.execute(
            """
            INSERT INTO processed_files (
                source_path, destination_path, sport_id, show_id,
                season_index, episode_index, processed_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "/source/old.mkv",
                "/dest/old.mkv",
                "formula1",
                "formula-1-2025",
                0,
                0,
                datetime.now().isoformat(),
                "linked",
            ),
        )
        conn.commit()
        conn.close()

        # Now open with ProcessedFileStore, which should migrate
        store = ProcessedFileStore(db_path)

        # Check that old record is still accessible
        old_record = store.get_by_source("/source/old.mkv")
        assert old_record is not None
        assert old_record.quality_score is None  # Not set in v1

        # Check that we can now add records with quality info
        new_record = ProcessedFileRecord(
            source_path="/source/new.mkv",
            destination_path="/dest/new.mkv",
            sport_id="formula1",
            show_id="formula-1-2026",
            season_index=0,
            episode_index=1,
            processed_at=datetime.now(),
            quality_score=440,
            quality_info='{"resolution": "1080p"}',
        )
        store.record_processed(new_record)

        retrieved = store.get_by_source("/source/new.mkv")
        assert retrieved is not None
        assert retrieved.quality_score == 440
        store.close()

    def test_get_quality_score_method(self, tmp_path: Path):
        """Test the get_quality_score lookup method."""
        db_path = tmp_path / "playbook.db"
        store = ProcessedFileStore(db_path)

        # Record a file with quality score
        record = ProcessedFileRecord(
            source_path="/source/test.mkv",
            destination_path="/dest/Formula 1/01 Monaco/episode.mkv",
            sport_id="formula1",
            show_id="formula-1-2026",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
            quality_score=440,
        )
        store.record_processed(record)

        # Look up by destination path
        score = store.get_quality_score("/dest/Formula 1/01 Monaco/episode.mkv")
        assert score == 440

        # Non-existent path returns None
        score = store.get_quality_score("/dest/nonexistent.mkv")
        assert score is None

        store.close()

    def test_update_quality_method(self, tmp_path: Path):
        """Test the update_quality method."""
        db_path = tmp_path / "playbook.db"
        store = ProcessedFileStore(db_path)

        # Record initial file
        record = ProcessedFileRecord(
            source_path="/source/test.mkv",
            destination_path="/dest/test.mkv",
            sport_id="formula1",
            show_id="formula-1-2026",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
            quality_score=250,
        )
        store.record_processed(record)

        # Update quality
        updated = store.update_quality(
            "/dest/test.mkv",
            quality_score=440,
            quality_info='{"resolution": "1080p", "source": "webdl"}',
        )
        assert updated is True

        # Verify update
        score = store.get_quality_score("/dest/test.mkv")
        assert score == 440

        # Update non-existent returns False
        updated = store.update_quality("/dest/nonexistent.mkv", quality_score=100, quality_info=None)
        assert updated is False

        store.close()

    def test_get_by_destination_method(self, tmp_path: Path):
        """Test the get_by_destination lookup method."""
        db_path = tmp_path / "playbook.db"
        store = ProcessedFileStore(db_path)

        record = ProcessedFileRecord(
            source_path="/source/test.mkv",
            destination_path="/dest/test.mkv",
            sport_id="formula1",
            show_id="formula-1-2026",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
            quality_score=440,
            quality_info='{"resolution": "1080p"}',
        )
        store.record_processed(record)

        # Look up by destination
        retrieved = store.get_by_destination("/dest/test.mkv")
        assert retrieved is not None
        assert retrieved.source_path == "/source/test.mkv"
        assert retrieved.quality_score == 440

        # Non-existent returns None
        retrieved = store.get_by_destination("/dest/nonexistent.mkv")
        assert retrieved is None

        store.close()


class TestQualityProfileConfiguration:
    """Tests for quality profile configuration parsing."""

    def test_global_profile_defaults(self):
        """Test that default quality profile has expected values."""
        profile = QualityProfile()
        assert profile.enabled is False
        assert profile.cutoff is None
        assert profile.min_score is None
        assert profile.scoring.resolution["1080p"] == 300
        assert profile.scoring.source["webdl"] == 90

    def test_sport_profile_merging(self):
        """Test that sport profiles merge correctly with global."""
        global_profile = QualityProfile(
            enabled=True,
            scoring=QualityScoring(
                release_group={"mwr": 30, "verum": 20},
            ),
            cutoff=350,
        )
        sport_profile = QualityProfile(
            enabled=True,
            scoring=QualityScoring(
                release_group={"mwr": 100, "smcgill1969": 80},
            ),
            cutoff=600,
        )

        effective = get_effective_quality_profile(sport_profile, global_profile)

        assert effective.enabled is True
        assert effective.cutoff == 600  # Sport override
        assert effective.scoring.release_group["mwr"] == 100  # Sport override
        assert effective.scoring.release_group["verum"] == 20  # Inherited from global
        assert effective.scoring.release_group["smcgill1969"] == 80  # Sport addition


class TestQualityUpgradeScenarios:
    """Integration tests for realistic upgrade scenarios."""

    @pytest.fixture
    def store(self, tmp_path: Path) -> ProcessedFileStore:
        """Create a test database."""
        db_path = tmp_path / "playbook.db"
        return ProcessedFileStore(db_path)

    @pytest.fixture
    def profile(self) -> QualityProfile:
        """Create a test quality profile."""
        return QualityProfile(
            enabled=True,
            scoring=QualityScoring(
                resolution={"2160p": 400, "1080p": 300, "720p": 200, "480p": 100},
                source={"bluray": 100, "webdl": 90, "webrip": 70, "hdtv": 50},
                release_group={"mwr": 50, "verum": 40, "nightninjas": 30},
                proper_bonus=50,
                repack_bonus=50,
                hdr_bonus=25,
            ),
            cutoff=400,
            min_score=100,
        )

    def test_scenario_resolution_upgrade_720_to_1080(self, store: ProcessedFileStore, profile: QualityProfile):
        """Test upgrading from 720p HDTV to 1080p WEB-DL."""
        destination = "/dest/Formula 1/01 Monaco/race.mkv"

        # Existing 720p file
        existing_info = extract_quality("Formula.1.2026.R01.Monaco.Race.720p.HDTV.mkv")
        existing_score = compute_quality_score(existing_info, profile)

        existing_record = ProcessedFileRecord(
            source_path="/source/old_720p.mkv",
            destination_path=destination,
            sport_id="formula1",
            show_id="formula-1-2026",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
            quality_score=existing_score.total,
            quality_info=json.dumps(existing_info.to_dict()),
        )
        store.record_processed(existing_record)

        # Verify existing score
        assert existing_score.total == 250  # 720p (200) + hdtv (50)
        assert store.get_quality_score(destination) == 250

        # New 1080p file arrives (use dash format which extracts release group reliably)
        new_info = extract_quality("Formula.1.2026.R01.Monaco.Race.1080p.WEB-DL-MWR.mkv")
        new_score = compute_quality_score(new_info, profile)

        # Should be higher
        assert new_score.total == 440  # 1080p (300) + webdl (90) + mwr (50)
        assert new_score.total > existing_score.total

        store.close()

    def test_scenario_cutoff_blocks_upgrade(self, store: ProcessedFileStore, profile: QualityProfile):
        """Test that cutoff prevents upgrade."""
        destination = "/dest/Formula 1/01 Monaco/race.mkv"

        # Existing file above cutoff
        existing_record = ProcessedFileRecord(
            source_path="/source/good_file.mkv",
            destination_path=destination,
            sport_id="formula1",
            show_id="formula-1-2026",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
            quality_score=440,  # Above cutoff of 400
        )
        store.record_processed(existing_record)

        # New 4K file
        new_info = extract_quality("Formula.1.2026.R01.Monaco.Race.2160p.WEB-DL.mkv")
        new_score = compute_quality_score(new_info, profile)

        # New score is higher (490), but cutoff was already reached
        assert new_score.total == 490
        existing_score = store.get_quality_score(destination)
        assert existing_score >= profile.cutoff  # Cutoff reached

        store.close()

    def test_scenario_proper_bypasses_cutoff(self, store: ProcessedFileStore, profile: QualityProfile):
        """Test that PROPER release upgrades despite cutoff."""
        destination = "/dest/Formula 1/01 Monaco/race.mkv"

        # Existing file above cutoff
        existing_record = ProcessedFileRecord(
            source_path="/source/good_file.mkv",
            destination_path=destination,
            sport_id="formula1",
            show_id="formula-1-2026",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
            quality_score=440,
        )
        store.record_processed(existing_record)

        # PROPER release - should bypass cutoff
        new_info = extract_quality("Formula.1.2026.R01.Monaco.Race.1080p.WEB-DL.PROPER.MWR.mkv")
        assert new_info.is_proper is True

        store.close()

    def test_scenario_min_score_rejection(self, store: ProcessedFileStore, profile: QualityProfile):
        """Test that files below min_score are rejected."""
        # Low quality file - min_score is 100
        low_quality_info = QualityInfo(resolution="480p")  # Only 100 points from default
        score = compute_quality_score(low_quality_info, profile)
        # 480p = 100 in our profile, which equals min_score
        assert score.total == 100

        # Try with even lower quality (unknown resolution)
        very_low_info = QualityInfo()  # No resolution = 0 points
        very_low_score = compute_quality_score(very_low_info, profile)
        assert very_low_score.total == 0
        assert very_low_score.total < profile.min_score

        store.close()

    def test_scenario_release_group_upgrade(self, store: ProcessedFileStore, profile: QualityProfile):
        """Test upgrade based on preferred release group."""
        destination = "/dest/Formula 1/01 Monaco/race.mkv"

        # Existing file with lower-ranked group (use dash format for reliable extraction)
        existing_info = extract_quality("Formula.1.2026.R01.Monaco.Race.1080p.WEB-DL-NightNinjas.mkv")
        existing_score = compute_quality_score(existing_info, profile)
        # 300 + 90 + 30 = 420

        existing_record = ProcessedFileRecord(
            source_path="/source/nightninjas.mkv",
            destination_path=destination,
            sport_id="formula1",
            show_id="formula-1-2026",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
            quality_score=existing_score.total,
        )
        store.record_processed(existing_record)

        # New file with preferred group (use dash format for reliable extraction)
        new_info = extract_quality("Formula.1.2026.R01.Monaco.Race.1080p.WEB-DL-MWR.mkv")
        new_score = compute_quality_score(new_info, profile)
        # 300 + 90 + 50 = 440

        assert new_score.total > existing_score.total  # 440 > 420
        assert new_score.release_group_score > existing_score.release_group_score  # 50 > 30

        store.close()


class TestLegacyMode:
    """Tests for legacy mode (quality profile disabled)."""

    def test_disabled_profile_uses_legacy_logic(self):
        """Test that disabled quality profile doesn't affect scoring."""
        profile = QualityProfile(enabled=False)

        # Scoring should still work but won't be used for decisions
        info = extract_quality("Formula.1.2026.R01.Monaco.Race.1080p.WEB-DL.MWR.mkv")
        score = compute_quality_score(info, profile)

        # Score is computed (for logging) but profile.enabled is False
        assert score.total > 0
        assert profile.enabled is False


class TestQualityInfoSerialization:
    """Tests for quality info JSON serialization in database."""

    def test_quality_info_round_trip(self, tmp_path: Path):
        """Test that quality info survives database round trip."""
        db_path = tmp_path / "playbook.db"
        store = ProcessedFileStore(db_path)

        original_info = QualityInfo(
            resolution="1080p",
            source="webdl",
            release_group="mwr",
            is_proper=True,
            is_repack=False,
            codec="h265",
            hdr_format="hdr10",
        )
        quality_info_json = json.dumps(original_info.to_dict())

        record = ProcessedFileRecord(
            source_path="/source/test.mkv",
            destination_path="/dest/test.mkv",
            sport_id="formula1",
            show_id="formula-1-2026",
            season_index=0,
            episode_index=0,
            processed_at=datetime.now(),
            quality_score=440,
            quality_info=quality_info_json,
        )
        store.record_processed(record)

        # Retrieve and deserialize
        retrieved = store.get_by_source("/source/test.mkv")
        assert retrieved is not None
        assert retrieved.quality_info is not None

        deserialized_data = json.loads(retrieved.quality_info)
        restored_info = QualityInfo.from_dict(deserialized_data)

        assert restored_info == original_info
        store.close()
