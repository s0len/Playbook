"""Tests for quality attribute extraction from filenames."""

from __future__ import annotations

import pytest

from playbook.quality import QualityInfo, extract_quality


class TestQualityInfo:
    """Tests for the QualityInfo dataclass."""

    def test_default_values(self):
        """Test that QualityInfo has sensible defaults."""
        info = QualityInfo()
        assert info.resolution is None
        assert info.source is None
        assert info.release_group is None
        assert info.is_proper is False
        assert info.is_repack is False
        assert info.codec is None
        assert info.hdr_format is None

    def test_to_dict(self):
        """Test serialization to dictionary."""
        info = QualityInfo(
            resolution="1080p",
            source="webdl",
            release_group="mwr",
            is_proper=True,
            is_repack=False,
            codec="h265",
            hdr_format="hdr10",
        )
        result = info.to_dict()
        assert result == {
            "resolution": "1080p",
            "source": "webdl",
            "release_group": "mwr",
            "is_proper": True,
            "is_repack": False,
            "codec": "h265",
            "hdr_format": "hdr10",
        }

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "resolution": "2160p",
            "source": "bluray",
            "release_group": "verum",
            "is_proper": False,
            "is_repack": True,
            "codec": "x264",
            "hdr_format": "dolby_vision",
        }
        info = QualityInfo.from_dict(data)
        assert info.resolution == "2160p"
        assert info.source == "bluray"
        assert info.release_group == "verum"
        assert info.is_proper is False
        assert info.is_repack is True
        assert info.codec == "x264"
        assert info.hdr_format == "dolby_vision"

    def test_from_dict_missing_keys(self):
        """Test that missing keys in dict use defaults."""
        data = {"resolution": "720p"}
        info = QualityInfo.from_dict(data)
        assert info.resolution == "720p"
        assert info.source is None
        assert info.is_proper is False

    def test_frozen(self):
        """Test that QualityInfo is immutable."""
        info = QualityInfo(resolution="1080p")
        with pytest.raises(AttributeError):
            info.resolution = "720p"


class TestExtractQualityResolution:
    """Tests for resolution extraction."""

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("Formula.1.2026.R05.Monaco.GP.Race.2160p.WEB-DL.mkv", "2160p"),
            ("Formula.1.2026.R05.Monaco.GP.Race.4K.WEB-DL.mkv", "2160p"),
            ("Formula.1.2026.R05.Monaco.GP.Race.UHD.WEB-DL.mkv", "2160p"),
            ("Formula.1.2026.R05.Monaco.GP.Race.1080p.WEB-DL.mkv", "1080p"),
            ("Formula.1.2026.R05.Monaco.GP.Race.1080i.HDTV.mkv", "1080p"),
            ("Formula.1.2026.R05.Monaco.GP.Race.720p.HDTV.mkv", "720p"),
            ("Formula.1.2026.R05.Monaco.GP.Race.576p.DVDRip.mkv", "576p"),
            ("Formula.1.2026.R05.Monaco.GP.Race.480p.SDTV.mkv", "480p"),
            ("Formula.1.2026.R05.Monaco.GP.Race.SD.SDTV.mkv", "480p"),
            ("Formula.1.2026.R05.Monaco.GP.Race.WEB-DL.mkv", None),  # No resolution
        ],
    )
    def test_resolution_extraction(self, filename: str, expected: str | None):
        """Test that resolution is correctly extracted from various filename formats."""
        info = extract_quality(filename)
        assert info.resolution == expected


class TestExtractQualitySource:
    """Tests for source type extraction."""

    @pytest.mark.parametrize(
        "filename,expected",
        [
            # Blu-ray variants
            ("Movie.2024.BluRay.1080p.mkv", "bluray"),
            ("Movie.2024.Blu-ray.1080p.mkv", "bluray"),
            ("Movie.2024.BDRip.1080p.mkv", "bluray"),
            ("Movie.2024.REMUX.1080p.mkv", "bluray"),
            # WEB-DL variants
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.MWR.mkv", "webdl"),
            ("Formula.1.2026.R05.Monaco.1080p.WEBDL.MWR.mkv", "webdl"),
            ("Formula.1.2026.R05.Monaco.1080p.AMZN.MWR.mkv", "webdl"),
            ("Formula.1.2026.R05.Monaco.1080p.AMAZON.MWR.mkv", "webdl"),
            ("Formula.1.2026.R05.Monaco.1080p.NF.MWR.mkv", "webdl"),
            ("Formula.1.2026.R05.Monaco.1080p.DSNP.MWR.mkv", "webdl"),
            ("Formula.1.2026.R05.Monaco.1080p.F1TV.MWR.mkv", "webdl"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB.MWR.mkv", "webdl"),
            # WEBRip variants
            ("Movie.2024.WEBRip.1080p.mkv", "webrip"),
            ("Movie.2024.WEB-Rip.1080p.mkv", "webrip"),
            # HDTV variants
            ("UFC.300.Main.Event.720p.HDTV.mkv", "hdtv"),
            ("UFC.300.Main.Event.720p.PDTV.mkv", "hdtv"),
            ("UFC.300.Main.Event.720p.DSR.mkv", "hdtv"),
            ("UFC.300.Main.Event.720p.TVRip.mkv", "hdtv"),
            # DVD variants
            ("Movie.2024.DVDRip.480p.mkv", "dvdrip"),
            ("Movie.2024.DVD.480p.mkv", "dvdrip"),
            # SDTV
            ("Movie.2024.SDTV.480p.mkv", "sdtv"),
            # No source
            ("Movie.2024.1080p.mkv", None),
        ],
    )
    def test_source_extraction(self, filename: str, expected: str | None):
        """Test that source type is correctly extracted."""
        info = extract_quality(filename)
        assert info.source == expected


class TestExtractQualityCodec:
    """Tests for codec extraction."""

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.x265.mkv", "x265"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.H.265.mkv", "h265"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.H265.mkv", "h265"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.HEVC.mkv", "h265"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.x264.mkv", "x264"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.H.264.mkv", "h264"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.H264.mkv", "h264"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.AVC.mkv", "h264"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.XviD.mkv", "xvid"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.DivX.mkv", "divx"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.mkv", None),
        ],
    )
    def test_codec_extraction(self, filename: str, expected: str | None):
        """Test that codec is correctly extracted."""
        info = extract_quality(filename)
        assert info.codec == expected


class TestExtractQualityHDR:
    """Tests for HDR format extraction."""

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("Movie.2024.2160p.WEB-DL.HDR.mkv", "hdr"),
            ("Movie.2024.2160p.WEB-DL.HDR10.mkv", "hdr10"),
            ("Movie.2024.2160p.WEB-DL.HDR10+.mkv", "hdr10plus"),
            ("Movie.2024.2160p.WEB-DL.Dolby.Vision.mkv", "dolby_vision"),
            ("Movie.2024.2160p.WEB-DL.DV.mkv", "dolby_vision"),
            ("Movie.2024.2160p.WEB-DL.HLG.mkv", "hlg"),
            ("Movie.2024.2160p.WEB-DL.mkv", None),
        ],
    )
    def test_hdr_extraction(self, filename: str, expected: str | None):
        """Test that HDR format is correctly extracted."""
        info = extract_quality(filename)
        assert info.hdr_format == expected


class TestExtractQualityReleaseGroup:
    """Tests for release group extraction."""

    @pytest.mark.parametrize(
        "filename,expected",
        [
            # Standard formats (dash-separated is most reliable)
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL-MWR.mkv", "mwr"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.[MWR].mkv", "mwr"),
            # Known groups (3+ chars detected anywhere)
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.Verum.mkv", "verum"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.SMCGILL1969.mkv", "smcgill1969"),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL-NTb.mkv", "ntb"),
            ("Movie.2024.1080p.WEB-DL-FLUX.mkv", "flux"),
            # Edge cases
            ("Movie.2024.1080p.WEB-DL.mkv", None),  # No group
            # Dot-separated groups need 3+ chars to avoid matching "DL"
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.MWR.mkv", "mwr"),  # MWR is 3 chars
        ],
    )
    def test_release_group_extraction(self, filename: str, expected: str | None):
        """Test that release group is correctly extracted."""
        info = extract_quality(filename)
        assert info.release_group == expected


class TestExtractQualityProperRepack:
    """Tests for PROPER/REPACK detection."""

    @pytest.mark.parametrize(
        "filename,is_proper,is_repack",
        [
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.PROPER.mkv", True, False),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.REPACK.mkv", False, True),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.RERIP.mkv", False, True),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.PROPER.REPACK.mkv", True, True),
            ("Formula.1.2026.R05.Monaco.1080p.WEB-DL.mkv", False, False),
        ],
    )
    def test_proper_repack_detection(self, filename: str, is_proper: bool, is_repack: bool):
        """Test that PROPER and REPACK flags are correctly detected."""
        info = extract_quality(filename)
        assert info.is_proper == is_proper
        assert info.is_repack == is_repack


class TestExtractQualityFullFilenames:
    """Integration tests with realistic filenames."""

    def test_f1_filename(self):
        """Test extraction from F1 filename."""
        # Use dash format for reliable release group extraction
        filename = "Formula.1.2026.R05.Monaco.Grand.Prix.Race.1080p.WEB-DL-MWR.mkv"
        info = extract_quality(filename)
        assert info.resolution == "1080p"
        assert info.source == "webdl"
        assert info.release_group == "mwr"
        assert info.is_proper is False
        assert info.is_repack is False

    def test_ufc_filename(self):
        """Test extraction from UFC filename."""
        filename = "UFC.300.Main.Event.720p.HDTV.PROPER.x264.mkv"
        info = extract_quality(filename)
        assert info.resolution == "720p"
        assert info.source == "hdtv"
        assert info.codec == "x264"
        assert info.is_proper is True

    def test_nba_filename(self):
        """Test extraction from NBA filename."""
        filename = "NBA.2025.12.25.Lakers.vs.Celtics.1080p.WEB-DL.AAC2.0.H.264-NTb.mkv"
        info = extract_quality(filename)
        assert info.resolution == "1080p"
        assert info.source == "webdl"
        assert info.codec == "h264"
        assert info.release_group == "ntb"

    def test_nhl_filename(self):
        """Test extraction from NHL filename."""
        filename = "NHL.2025.12.25.Rangers.vs.Bruins.720p.HDTV.x264.mkv"
        info = extract_quality(filename)
        assert info.resolution == "720p"
        assert info.source == "hdtv"
        assert info.codec == "x264"

    def test_4k_hdr_filename(self):
        """Test extraction from 4K HDR filename."""
        filename = "Formula.1.2026.R05.Monaco.Grand.Prix.Race.2160p.WEB-DL.HDR10.HEVC-MWR.mkv"
        info = extract_quality(filename)
        assert info.resolution == "2160p"
        assert info.source == "webdl"
        assert info.hdr_format == "hdr10"
        assert info.codec == "h265"
        assert info.release_group == "mwr"


class TestExtractQualityWithCapturedGroups:
    """Tests for using pre-captured regex groups."""

    def test_captured_resolution_takes_precedence(self):
        """Test that captured groups override filename parsing."""
        filename = "Formula.1.2026.R05.Monaco.1080p.WEB-DL.mkv"
        groups = {"resolution": "720p"}  # Pretend regex captured 720p
        info = extract_quality(filename, groups)
        assert info.resolution == "720p"  # Captured value takes precedence

    def test_captured_source_takes_precedence(self):
        """Test that captured source overrides filename parsing."""
        filename = "Formula.1.2026.R05.Monaco.1080p.WEB-DL.mkv"
        groups = {"source": "hdtv"}
        info = extract_quality(filename, groups)
        assert info.source == "hdtv"

    def test_captured_release_group(self):
        """Test that captured release group is used."""
        filename = "Formula.1.2026.R05.Monaco.1080p.WEB-DL.mkv"
        groups = {"release_group": "custom"}
        info = extract_quality(filename, groups)
        assert info.release_group == "custom"

    def test_captured_group_key_alias(self):
        """Test that 'group' key works as alias for release_group."""
        filename = "Formula.1.2026.R05.Monaco.1080p.WEB-DL.mkv"
        groups = {"group": "aliased"}
        info = extract_quality(filename, groups)
        assert info.release_group == "aliased"

    def test_partial_captured_groups(self):
        """Test that uncaptured values still come from filename."""
        # Use dash format for reliable release group extraction
        filename = "Formula.1.2026.R05.Monaco.1080p.WEB-DL-MWR.mkv"
        groups = {"resolution": "2160p"}  # Only resolution captured
        info = extract_quality(filename, groups)
        assert info.resolution == "2160p"  # From captured
        assert info.source == "webdl"  # From filename
        assert info.release_group == "mwr"  # From filename
