"""Tests for quality scoring engine."""

from __future__ import annotations

import pytest

from playbook.config import QualityProfile, QualityScoring
from playbook.quality import QualityInfo
from playbook.quality_scorer import (
    QualityComparison,
    QualityScore,
    compare_quality,
    compute_quality_score,
    get_effective_quality_profile,
)


class TestQualityScore:
    """Tests for the QualityScore dataclass."""

    def test_score_creation(self):
        """Test creating a QualityScore."""
        score = QualityScore(
            total=440,
            resolution_score=300,
            source_score=90,
            release_group_score=50,
            proper_bonus=0,
            repack_bonus=0,
            hdr_bonus=0,
        )
        assert score.total == 440
        assert score.resolution_score == 300
        assert score.source_score == 90
        assert score.release_group_score == 50

    def test_to_dict(self):
        """Test serialization to dictionary."""
        score = QualityScore(total=440, resolution_score=300, source_score=90)
        result = score.to_dict()
        assert result["total"] == 440
        assert result["resolution_score"] == 300
        assert result["source_score"] == 90

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {"total": 390, "resolution_score": 300, "source_score": 90}
        score = QualityScore.from_dict(data)
        assert score.total == 390
        assert score.resolution_score == 300


class TestComputeQualityScore:
    """Tests for the compute_quality_score function."""

    @pytest.fixture
    def default_profile(self) -> QualityProfile:
        """Create a default quality profile for testing."""
        return QualityProfile(enabled=True)

    @pytest.fixture
    def custom_profile(self) -> QualityProfile:
        """Create a custom quality profile with specific scoring."""
        return QualityProfile(
            enabled=True,
            scoring=QualityScoring(
                resolution={"2160p": 400, "1080p": 300, "720p": 200},
                source={"webdl": 90, "hdtv": 50},
                release_group={"mwr": 50, "verum": 40},
                proper_bonus=50,
                repack_bonus=50,
                hdr_bonus=25,
            ),
        )

    def test_resolution_only(self, default_profile: QualityProfile):
        """Test scoring with only resolution."""
        info = QualityInfo(resolution="1080p")
        score = compute_quality_score(info, default_profile)
        assert score.resolution_score == 300
        assert score.total == 300

    def test_resolution_and_source(self, default_profile: QualityProfile):
        """Test scoring with resolution and source."""
        info = QualityInfo(resolution="1080p", source="webdl")
        score = compute_quality_score(info, default_profile)
        assert score.resolution_score == 300
        assert score.source_score == 90
        assert score.total == 390

    def test_full_quality_info(self, custom_profile: QualityProfile):
        """Test scoring with all quality attributes."""
        info = QualityInfo(
            resolution="1080p",
            source="webdl",
            release_group="mwr",
        )
        score = compute_quality_score(info, custom_profile)
        # 300 (1080p) + 90 (webdl) + 50 (mwr) = 440
        assert score.resolution_score == 300
        assert score.source_score == 90
        assert score.release_group_score == 50
        assert score.total == 440

    def test_proper_bonus(self, custom_profile: QualityProfile):
        """Test that PROPER releases get bonus points."""
        info = QualityInfo(resolution="1080p", source="webdl", is_proper=True)
        score = compute_quality_score(info, custom_profile)
        # 300 + 90 + 50 (proper bonus) = 440
        assert score.proper_bonus == 50
        assert score.total == 440

    def test_repack_bonus(self, custom_profile: QualityProfile):
        """Test that REPACK releases get bonus points."""
        info = QualityInfo(resolution="1080p", source="webdl", is_repack=True)
        score = compute_quality_score(info, custom_profile)
        assert score.repack_bonus == 50
        assert score.total == 440

    def test_hdr_bonus(self, custom_profile: QualityProfile):
        """Test that HDR content gets bonus points."""
        info = QualityInfo(resolution="2160p", source="webdl", hdr_format="hdr10")
        score = compute_quality_score(info, custom_profile)
        # 400 (2160p) + 90 (webdl) + 25 (hdr) = 515
        assert score.hdr_bonus == 25
        assert score.total == 515

    def test_unknown_release_group(self, custom_profile: QualityProfile):
        """Test that unknown release groups get 0 points."""
        info = QualityInfo(resolution="1080p", source="webdl", release_group="unknown")
        score = compute_quality_score(info, custom_profile)
        assert score.release_group_score == 0
        assert score.total == 390

    def test_4k_with_preferred_group(self, custom_profile: QualityProfile):
        """Test scoring for 4K release with preferred group."""
        info = QualityInfo(
            resolution="2160p",
            source="webdl",
            release_group="mwr",
            hdr_format="hdr10",
        )
        score = compute_quality_score(info, custom_profile)
        # 400 + 90 + 50 + 25 = 565
        assert score.total == 565


class TestCompareQuality:
    """Tests for the compare_quality function."""

    @pytest.fixture
    def profile(self) -> QualityProfile:
        """Create a quality profile for comparison tests."""
        return QualityProfile(
            enabled=True,
            scoring=QualityScoring(
                resolution={"2160p": 400, "1080p": 300, "720p": 200},
                source={"webdl": 90, "hdtv": 50},
                release_group={"mwr": 50, "verum": 40},
            ),
            cutoff=400,
            min_score=100,
        )

    def test_no_existing_file(self, profile: QualityProfile):
        """Test comparison when no existing file exists."""
        info = QualityInfo(resolution="1080p", source="webdl")
        result = compare_quality(info, None, profile)
        assert result.should_upgrade is True
        assert "No existing file" in result.reason
        assert result.existing_score is None

    def test_below_min_score(self, profile: QualityProfile):
        """Test that files below min_score are rejected."""
        # 480p (not in our custom profile) defaults to 0
        info = QualityInfo(resolution="480p")
        result = compare_quality(info, None, profile)
        assert result.should_upgrade is False
        assert "minimum score" in result.reason.lower()

    def test_resolution_upgrade(self, profile: QualityProfile):
        """Test upgrade from 720p to 1080p."""
        info = QualityInfo(resolution="1080p", source="webdl")  # Score: 390
        existing_score = 250  # 720p + hdtv
        result = compare_quality(info, existing_score, profile)
        assert result.should_upgrade is True
        assert "Higher quality" in result.reason
        assert result.new_score.total == 390

    def test_no_upgrade_when_score_lower(self, profile: QualityProfile):
        """Test that lower score doesn't upgrade."""
        info = QualityInfo(resolution="720p", source="hdtv")  # Score: 250
        existing_score = 390  # 1080p + webdl
        result = compare_quality(info, existing_score, profile)
        assert result.should_upgrade is False
        assert "Not a quality upgrade" in result.reason

    def test_cutoff_prevents_upgrade(self, profile: QualityProfile):
        """Test that cutoff prevents further upgrades."""
        info = QualityInfo(resolution="2160p", source="webdl")  # Score: 490
        existing_score = 440  # Above cutoff of 400
        result = compare_quality(info, existing_score, profile)
        assert result.should_upgrade is False
        assert result.cutoff_reached is True
        assert "Cutoff reached" in result.reason

    def test_proper_overrides_cutoff(self, profile: QualityProfile):
        """Test that PROPER release upgrades even when cutoff reached."""
        info = QualityInfo(resolution="1080p", source="webdl", is_proper=True)
        existing_score = 440  # Above cutoff
        result = compare_quality(info, existing_score, profile)
        assert result.should_upgrade is True
        assert "PROPER" in result.reason
        assert result.cutoff_reached is True  # Cutoff was reached but overridden

    def test_repack_overrides_cutoff(self, profile: QualityProfile):
        """Test that REPACK release upgrades even when cutoff reached."""
        info = QualityInfo(resolution="1080p", source="webdl", is_repack=True)
        existing_score = 440  # Above cutoff
        result = compare_quality(info, existing_score, profile)
        assert result.should_upgrade is True
        assert "REPACK" in result.reason

    def test_release_group_preference_upgrade(self, profile: QualityProfile):
        """Test upgrade based on preferred release group (below cutoff)."""
        # Create profile without cutoff for this test
        profile_no_cutoff = QualityProfile(
            enabled=True,
            scoring=profile.scoring,
            cutoff=None,  # No cutoff
            min_score=100,
        )
        # New file: 1080p + webdl + mwr = 300 + 90 + 50 = 440
        info = QualityInfo(resolution="1080p", source="webdl", release_group="mwr")
        # Existing: 1080p + webdl + verum = 300 + 90 + 40 = 430
        existing_score = 430
        result = compare_quality(info, existing_score, profile_no_cutoff)
        assert result.should_upgrade is True


class TestGetEffectiveQualityProfile:
    """Tests for merging sport and global quality profiles."""

    def test_no_sport_profile(self):
        """Test that global profile is used when no sport profile exists."""
        global_profile = QualityProfile(enabled=True, cutoff=350)
        result = get_effective_quality_profile(None, global_profile)
        assert result.enabled is True
        assert result.cutoff == 350

    def test_sport_profile_overrides_enabled(self):
        """Test that sport profile can enable quality when global is disabled."""
        global_profile = QualityProfile(enabled=False)
        sport_profile = QualityProfile(enabled=True)
        result = get_effective_quality_profile(sport_profile, global_profile)
        assert result.enabled is True

    def test_sport_profile_overrides_cutoff(self):
        """Test that sport cutoff overrides global cutoff."""
        global_profile = QualityProfile(enabled=True, cutoff=350)
        sport_profile = QualityProfile(enabled=True, cutoff=600)
        result = get_effective_quality_profile(sport_profile, global_profile)
        assert result.cutoff == 600

    def test_sport_profile_inherits_global_cutoff(self):
        """Test that sport inherits global cutoff if not specified."""
        global_profile = QualityProfile(enabled=True, cutoff=350)
        sport_profile = QualityProfile(enabled=True)  # No cutoff specified
        result = get_effective_quality_profile(sport_profile, global_profile)
        assert result.cutoff == 350

    def test_release_group_scores_merge(self):
        """Test that release group scores are merged."""
        global_profile = QualityProfile(
            enabled=True,
            scoring=QualityScoring(release_group={"mwr": 30, "verum": 20}),
        )
        sport_profile = QualityProfile(
            enabled=True,
            scoring=QualityScoring(release_group={"mwr": 100}),  # Override mwr
        )
        result = get_effective_quality_profile(sport_profile, global_profile)
        # mwr should be overridden, verum should be inherited
        assert result.scoring.release_group["mwr"] == 100
        assert result.scoring.release_group["verum"] == 20


class TestQualityComparisonScenarios:
    """Integration tests for realistic quality comparison scenarios."""

    @pytest.fixture
    def profile(self) -> QualityProfile:
        """Create a realistic quality profile."""
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
        )

    def test_scenario_resolution_upgrade(self, profile: QualityProfile):
        """Scenario 1: Resolution Upgrade (720p -> 1080p)."""
        # Existing: 720p HDTV = 200 + 50 = 250
        existing_score = 250
        # New: 1080p WEB-DL MWR = 300 + 90 + 50 = 440
        info = QualityInfo(resolution="1080p", source="webdl", release_group="mwr")
        result = compare_quality(info, existing_score, profile)
        assert result.should_upgrade is True
        assert result.new_score.total == 440

    def test_scenario_cutoff_reached(self, profile: QualityProfile):
        """Scenario 2: Cutoff Reached - no upgrade."""
        # Existing: 1080p WEB-DL MWR = 440 (above cutoff of 400)
        existing_score = 440
        # New: 2160p WEB-DL = 400 + 90 = 490 (higher, but cutoff reached)
        info = QualityInfo(resolution="2160p", source="webdl")
        result = compare_quality(info, existing_score, profile)
        assert result.should_upgrade is False
        assert result.cutoff_reached is True

    def test_scenario_proper_override(self, profile: QualityProfile):
        """Scenario 3: PROPER Override - upgrade despite cutoff."""
        # Existing: 1080p WEB-DL MWR = 440 (cutoff reached)
        existing_score = 440
        # New: 1080p WEB-DL PROPER MWR = 300 + 90 + 50 + 50 = 490
        info = QualityInfo(
            resolution="1080p",
            source="webdl",
            release_group="mwr",
            is_proper=True,
        )
        result = compare_quality(info, existing_score, profile)
        assert result.should_upgrade is True
        assert result.new_score.proper_bonus == 50

    def test_scenario_release_group_preference(self, profile: QualityProfile):
        """Scenario 4: Release Group Preference (below cutoff)."""
        # Use a profile without cutoff for this test
        profile_no_cutoff = QualityProfile(
            enabled=True,
            scoring=profile.scoring,
            cutoff=None,  # No cutoff
        )
        # Existing: 1080p WEB-DL NightNinjas = 300 + 90 + 30 = 420
        existing_score = 420
        # New: 1080p WEB-DL MWR = 300 + 90 + 50 = 440
        info = QualityInfo(resolution="1080p", source="webdl", release_group="mwr")
        result = compare_quality(info, existing_score, profile_no_cutoff)
        assert result.should_upgrade is True
        assert result.new_score.release_group_score == 50
