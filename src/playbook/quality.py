"""Quality attribute extraction from media filenames.

This module provides functionality for extracting quality attributes from media
filenames, such as resolution, source, release group, and quality flags like
PROPER/REPACK.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QualityInfo:
    """Extracted quality attributes from a filename.

    Attributes:
        resolution: Video resolution (e.g., "2160p", "1080p", "720p", "480p")
        source: Media source (e.g., "bluray", "webdl", "webrip", "hdtv")
        release_group: Release group name (e.g., "mwr", "verum", "nightninjas")
        is_proper: Whether this is a PROPER release (corrected version)
        is_repack: Whether this is a REPACK release (re-encoded/fixed version)
        codec: Video codec (e.g., "h265", "h264", "x265", "x264")
        hdr_format: HDR format if present (e.g., "hdr", "hdr10", "dolby_vision")
        frame_rate: Frame rate in fps (e.g., 60, 50, 25) - critical for sports
        bit_depth: Bit depth (e.g., 10 for 10-bit encoding)
        audio: Audio codec/format (e.g., "ddp51", "aac", "ac3")
        broadcaster: Original broadcaster (e.g., "f1tv", "sky", "espn")
    """

    resolution: str | None = None
    source: str | None = None
    release_group: str | None = None
    is_proper: bool = False
    is_repack: bool = False
    codec: str | None = None
    hdr_format: str | None = None
    frame_rate: int | None = None
    bit_depth: int | None = None
    audio: str | None = None
    broadcaster: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "resolution": self.resolution,
            "source": self.source,
            "release_group": self.release_group,
            "is_proper": self.is_proper,
            "is_repack": self.is_repack,
            "codec": self.codec,
            "hdr_format": self.hdr_format,
            "frame_rate": self.frame_rate,
            "bit_depth": self.bit_depth,
            "audio": self.audio,
            "broadcaster": self.broadcaster,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityInfo:
        """Create from a dictionary."""
        return cls(
            resolution=data.get("resolution"),
            source=data.get("source"),
            release_group=data.get("release_group"),
            is_proper=bool(data.get("is_proper", False)),
            is_repack=bool(data.get("is_repack", False)),
            codec=data.get("codec"),
            hdr_format=data.get("hdr_format"),
            frame_rate=data.get("frame_rate"),
            bit_depth=data.get("bit_depth"),
            audio=data.get("audio"),
            broadcaster=data.get("broadcaster"),
        )


# Resolution patterns (order matters - check higher resolutions first)
# These match both standalone (1080p) and with embedded frame rate (1080p50, 1080p60fps)
_RESOLUTION_PATTERNS = [
    (re.compile(r"\b2160p", re.IGNORECASE), "2160p"),
    (re.compile(r"\b4k\b", re.IGNORECASE), "2160p"),
    (re.compile(r"\buhd\b", re.IGNORECASE), "2160p"),
    (re.compile(r"\b1080p", re.IGNORECASE), "1080p"),
    (re.compile(r"\b1080i", re.IGNORECASE), "1080p"),
    (re.compile(r"\b720p", re.IGNORECASE), "720p"),
    (re.compile(r"\b576p", re.IGNORECASE), "576p"),
    (re.compile(r"\b480p", re.IGNORECASE), "480p"),
    (re.compile(r"\bsd\b", re.IGNORECASE), "480p"),
]

# Source patterns (normalized to lowercase keys for scoring lookup)
_SOURCE_PATTERNS = [
    # Blu-ray variants
    (re.compile(r"\bblu[\s._-]?ray\b", re.IGNORECASE), "bluray"),
    (re.compile(r"\bbd[\s._-]?rip\b", re.IGNORECASE), "bluray"),
    (re.compile(r"\bbdrip\b", re.IGNORECASE), "bluray"),
    (re.compile(r"\bremux\b", re.IGNORECASE), "bluray"),
    # WEB-DL variants (higher quality web source)
    (re.compile(r"\bweb[\s._-]?dl\b", re.IGNORECASE), "webdl"),
    (re.compile(r"\bwebdl\b", re.IGNORECASE), "webdl"),
    (re.compile(r"\bamazon\b", re.IGNORECASE), "webdl"),
    (re.compile(r"\bamzn\b", re.IGNORECASE), "webdl"),
    (re.compile(r"\bnetflix\b", re.IGNORECASE), "webdl"),
    (re.compile(r"\bnf\b", re.IGNORECASE), "webdl"),
    (re.compile(r"\bdsnp\b", re.IGNORECASE), "webdl"),
    (re.compile(r"\bf1tv\b", re.IGNORECASE), "webdl"),
    # WEBRip (re-encoded from web source)
    (re.compile(r"\bweb[\s._-]?rip\b", re.IGNORECASE), "webrip"),
    (re.compile(r"\bwebrip\b", re.IGNORECASE), "webrip"),
    # Generic WEB (could be either, default to webdl)
    (re.compile(r"\bweb\b", re.IGNORECASE), "webdl"),
    # HDTV variants
    (re.compile(r"\bhdtv\b", re.IGNORECASE), "hdtv"),
    (re.compile(r"\bpdtv\b", re.IGNORECASE), "hdtv"),
    (re.compile(r"\bdsr\b", re.IGNORECASE), "hdtv"),
    (re.compile(r"\bdtv\b", re.IGNORECASE), "hdtv"),
    (re.compile(r"\btvrip\b", re.IGNORECASE), "hdtv"),
    (re.compile(r"\bhdtvrip\b", re.IGNORECASE), "hdtv"),
    # SDTV (lower quality)
    (re.compile(r"\bsdtv\b", re.IGNORECASE), "sdtv"),
    (re.compile(r"\bdvdrip\b", re.IGNORECASE), "dvdrip"),
    (re.compile(r"\bdvd\b", re.IGNORECASE), "dvdrip"),
]

# Codec patterns
_CODEC_PATTERNS = [
    (re.compile(r"\bx265\b", re.IGNORECASE), "x265"),
    (re.compile(r"\bh\.?265\b", re.IGNORECASE), "h265"),
    (re.compile(r"\bhevc\b", re.IGNORECASE), "h265"),
    (re.compile(r"\bx264\b", re.IGNORECASE), "x264"),
    (re.compile(r"\bh\.?264\b", re.IGNORECASE), "h264"),
    (re.compile(r"\bavc\b", re.IGNORECASE), "h264"),
    (re.compile(r"\bxvid\b", re.IGNORECASE), "xvid"),
    (re.compile(r"\bdivx\b", re.IGNORECASE), "divx"),
]

# HDR patterns
_HDR_PATTERNS = [
    (re.compile(r"\bdolby[\s._-]?vision\b", re.IGNORECASE), "dolby_vision"),
    (re.compile(r"\bdv\b", re.IGNORECASE), "dolby_vision"),
    (re.compile(r"\bhdr10\+", re.IGNORECASE), "hdr10plus"),
    (re.compile(r"\bhdr10\b", re.IGNORECASE), "hdr10"),
    (re.compile(r"\bhdr\b", re.IGNORECASE), "hdr"),
    (re.compile(r"\bhlg\b", re.IGNORECASE), "hlg"),
]

# Frame rate patterns - critical for sports content
# Supports: 60fps, 50fps, 1080p60, 1080p50, 720p50fps, etc.
_FRAME_RATE_PATTERNS = [
    # Explicit fps markers (check first)
    (re.compile(r"\b60fps\b", re.IGNORECASE), 60),
    (re.compile(r"\b50fps\b", re.IGNORECASE), 50),
    (re.compile(r"\b30fps\b", re.IGNORECASE), 30),
    (re.compile(r"\b25fps\b", re.IGNORECASE), 25),
    (re.compile(r"\b24fps\b", re.IGNORECASE), 24),
    # Embedded in resolution with fps suffix (e.g., 720p50fps)
    (re.compile(r"\b\d{3,4}p60fps\b", re.IGNORECASE), 60),
    (re.compile(r"\b\d{3,4}p50fps\b", re.IGNORECASE), 50),
    (re.compile(r"\b\d{3,4}p30fps\b", re.IGNORECASE), 30),
    (re.compile(r"\b\d{3,4}p25fps\b", re.IGNORECASE), 25),
    (re.compile(r"\b\d{3,4}p24fps\b", re.IGNORECASE), 24),
    # Embedded in resolution (e.g., 1080p60, 720p50)
    (re.compile(r"\b\d{3,4}p60\b", re.IGNORECASE), 60),
    (re.compile(r"\b\d{3,4}p50\b", re.IGNORECASE), 50),
    (re.compile(r"\b\d{3,4}p30\b", re.IGNORECASE), 30),
    (re.compile(r"\b\d{3,4}p25\b", re.IGNORECASE), 25),
    (re.compile(r"\b\d{3,4}p24\b", re.IGNORECASE), 24),
    # With i (interlaced, treat as equivalent fps)
    (re.compile(r"\b\d{3,4}i60\b", re.IGNORECASE), 60),
    (re.compile(r"\b\d{3,4}i50\b", re.IGNORECASE), 50),
]

# Bit depth patterns (10-bit encoding has better color/gradients)
_BIT_DEPTH_PATTERNS = [
    (re.compile(r"\b10[\s._-]?bit\b", re.IGNORECASE), 10),
    (re.compile(r"\.10bit\b", re.IGNORECASE), 10),
    (re.compile(r"\bx265\.10bit\b", re.IGNORECASE), 10),
    (re.compile(r"\bhevc\.10bit\b", re.IGNORECASE), 10),
    (re.compile(r"\b8[\s._-]?bit\b", re.IGNORECASE), 8),
]

# Audio patterns
_AUDIO_PATTERNS = [
    # Dolby Digital Plus / E-AC-3 (best quality streaming audio)
    (re.compile(r"\bddp[\s._-]?5\.?1\b", re.IGNORECASE), "ddp51"),
    (re.compile(r"\bdd[\s._-]?5\.?1\b", re.IGNORECASE), "dd51"),
    (re.compile(r"\be[\s._-]?ac[\s._-]?3\b", re.IGNORECASE), "eac3"),
    (re.compile(r"\beac3\b", re.IGNORECASE), "eac3"),
    (re.compile(r"\bac[\s._-]?3\b", re.IGNORECASE), "ac3"),
    (re.compile(r"\bdolby[\s._-]?digital\b", re.IGNORECASE), "dd51"),
    # DTS variants
    (re.compile(r"\bdts[\s._-]?hd[\s._-]?ma\b", re.IGNORECASE), "dtshd"),
    (re.compile(r"\bdts[\s._-]?hd\b", re.IGNORECASE), "dtshd"),
    (re.compile(r"\bdts\b", re.IGNORECASE), "dts"),
    # TrueHD / Atmos
    (re.compile(r"\btruehd\b", re.IGNORECASE), "truehd"),
    (re.compile(r"\batmos\b", re.IGNORECASE), "atmos"),
    # AAC variants
    (re.compile(r"\baac[\s._-]?5\.?1\b", re.IGNORECASE), "aac51"),
    (re.compile(r"\baac[\s._-]?2\.?0\b", re.IGNORECASE), "aac"),
    (re.compile(r"\baac\b", re.IGNORECASE), "aac"),
    # FLAC
    (re.compile(r"\bflac\b", re.IGNORECASE), "flac"),
    # MP3
    (re.compile(r"\bmp3\b", re.IGNORECASE), "mp3"),
]

# Broadcaster patterns - official sources are preferred
_BROADCASTER_PATTERNS = [
    # F1 specific
    (re.compile(r"\bf1tv\b", re.IGNORECASE), "f1tv"),
    (re.compile(r"\bf1[\s._-]?live\b", re.IGNORECASE), "f1tv"),
    (re.compile(r"\bskyf1[\s._-]?uhd\b", re.IGNORECASE), "skyf1uhd"),
    (re.compile(r"\bskyf1[\s._-]?hd\b", re.IGNORECASE), "skyf1"),
    (re.compile(r"\bskyf1\b", re.IGNORECASE), "skyf1"),
    # Sky variants
    (re.compile(r"\bsky[\s._-]?sports?\b", re.IGNORECASE), "sky"),
    (re.compile(r"\bskynz\b", re.IGNORECASE), "sky"),
    (re.compile(r"[\.\s_-]sky[\.\s_-]", re.IGNORECASE), "sky"),
    # US networks (match both "NBC Sports" and bare "NBC")
    (re.compile(r"\bespn\+?\b", re.IGNORECASE), "espn"),
    (re.compile(r"\btnt\b", re.IGNORECASE), "tnt"),
    (re.compile(r"\bnbc[\s._-]?sports?\b", re.IGNORECASE), "nbc"),
    (re.compile(r"[\.\s_-]nbc[\.\s_-]", re.IGNORECASE), "nbc"),
    (re.compile(r"\bcbs[\s._-]?sports?\b", re.IGNORECASE), "cbs"),
    (re.compile(r"[\.\s_-]cbs[\.\s_-]", re.IGNORECASE), "cbs"),
    (re.compile(r"\bfox[\s._-]?sports?\b", re.IGNORECASE), "fox"),
    (re.compile(r"[\.\s_-]fox[\.\s_-]", re.IGNORECASE), "fox"),
    (re.compile(r"\bmsg\b", re.IGNORECASE), "msg"),
    (re.compile(r"\bfubo\b", re.IGNORECASE), "fubo"),
    # Streaming services
    (re.compile(r"\bstan\b", re.IGNORECASE), "stan"),
    (re.compile(r"\bnowtv\b", re.IGNORECASE), "nowtv"),
    (re.compile(r"\bdazn\b", re.IGNORECASE), "dazn"),
    # Other regional
    (re.compile(r"\bbt[\s._-]?sport\b", re.IGNORECASE), "bt"),
    (re.compile(r"\btsn\b", re.IGNORECASE), "tsn"),
    (re.compile(r"\bsportsnet\b", re.IGNORECASE), "sportsnet"),
]

# PROPER/REPACK patterns
_PROPER_PATTERN = re.compile(r"\bproper\b", re.IGNORECASE)
_REPACK_PATTERN = re.compile(r"\brepack\b", re.IGNORECASE)
_RERIP_PATTERN = re.compile(r"\brerip\b", re.IGNORECASE)

# Release group pattern - typically at the end of filename before extension
# Common formats: -GROUP, .GROUP, [GROUP]
# Requires at least 2 characters for the group name to avoid matching "DL" from "WEB-DL"
_RELEASE_GROUP_PATTERN = re.compile(r"(?:^|[.\s_\-\[])([a-zA-Z][a-zA-Z0-9]{2,14})(?:\])?(?:\.[a-zA-Z0-9]{2,4})?$")

# Known release groups (case-insensitive matching)
_KNOWN_RELEASE_GROUPS = {
    # F1/Motorsport specialists
    "mwr",
    "verum",
    "nightninjas",
    "smcgill1969",
    "sh0ww",
    "ebi",
    "darksport",
    "f1carreras",
    "tabularippa",
    "m4c",
    # Sports generalists
    "dnu",
    "gametime",
    "sportsfire",
    "varyg",
    "cakes",
    "deejonker",
    # General scene groups
    "ntb",
    "ntg",
    "yts",
    "rarbg",
    "sparks",
    "fleet",
    "ettv",
    "eztv",
    "yify",
    "hulu",
    "dsnp",
    "amzn",
    "nf",
    "atvp",
    "pcok",
    "hmax",
    "stan",
    # P2P groups
    "ion10",
    "sigma",
    "flux",
    "nogrp",
    "nogroup",
}

# Common file extensions to strip
_EXTENSIONS = {".mkv", ".mp4", ".avi", ".m4v", ".ts", ".wmv", ".mov"}


def _extract_release_group(filename: str) -> str | None:
    """Extract release group from filename.

    Release groups are typically found at the end of the filename,
    before the extension, prefixed with a dash or dot.

    Args:
        filename: The filename to extract from.

    Returns:
        The release group name in lowercase, or None if not found.
    """
    # Remove extension if present
    name = filename
    for ext in _EXTENSIONS:
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
            break

    # Try to match release group at the end
    match = _RELEASE_GROUP_PATTERN.search(name)
    if match:
        group = match.group(1).lower()
        # Filter out common false positives
        false_positives = {
            # File extensions
            "mkv",
            "mp4",
            "avi",
            "srt",
            "sub",
            "idx",
            "nfo",
            "sample",
            "proof",
            # Resolutions
            "720p",
            "1080p",
            "2160p",
            "480p",
            "576p",
            # Codecs
            "x264",
            "x265",
            "h264",
            "h265",
            "hevc",
            "avc",
            # Audio
            "aac",
            "dts",
            "ac3",
            "flac",
            # Quality flags
            "proper",
            "repack",
            "rerip",
            # Sources
            "web",
            "webrip",
            "webdl",
            "hdtv",
            "bluray",
            "bdrip",
            "remux",
            # HDR
            "hdr",
            "hdr10",
            "dv",
            "atmos",
            "dl",  # From WEB-DL
            # Broadcasters (should not be treated as release groups)
            "f1tv",
            "sky",
            "skyf1",
            "espn",
            "tnt",
            "cbs",
            "fox",
            "nbc",
            "msg",
            "dazn",
            "stan",
            "fubo",
            "nowtv",
            "tsn",
            "sportsnet",
            "bt",
        }
        if group not in false_positives:
            return group

    # Also check for known groups anywhere in the filename (less common position)
    name_lower = filename.lower()
    for known_group in _KNOWN_RELEASE_GROUPS:
        # Match as word boundary
        pattern = re.compile(rf"[.\s_\-\[]({re.escape(known_group)})[.\s_\-\]\)]?", re.IGNORECASE)
        if pattern.search(name_lower):
            return known_group

    return None


def extract_quality(
    filename: str,
    captured_groups: dict[str, Any] | None = None,
) -> QualityInfo:
    """Extract quality attributes from a media filename.

    Parses the filename to extract quality indicators such as resolution,
    source type, codec, HDR format, release group, frame rate, bit depth,
    audio format, broadcaster, and PROPER/REPACK flags.

    Args:
        filename: The filename to parse (without directory path).
        captured_groups: Optional regex capture groups from pattern matching.
            Can contain pre-extracted values like 'resolution', 'source',
            'release_group' that take precedence over filename parsing.

    Returns:
        QualityInfo with extracted quality attributes.

    Examples:
        >>> extract_quality("Formula.1.2026.R05.Monaco.GP.Race.1080p50.WEB-DL.MWR.mkv")
        QualityInfo(resolution='1080p', source='webdl', release_group='mwr', frame_rate=50, ...)

        >>> extract_quality("UFC.300.Main.Event.720p.HDTV.PROPER.x264.mkv")
        QualityInfo(resolution='720p', source='hdtv', is_proper=True, codec='x264', ...)

        >>> extract_quality("F1.2026.Monaco.GP.2160p.F1TV.WEB-DL.x265.10bit.DDP5.1.mkv")
        QualityInfo(resolution='2160p', source='webdl', broadcaster='f1tv', bit_depth=10, audio='ddp51', ...)
    """
    groups = captured_groups or {}

    # Extract resolution
    resolution: str | None = groups.get("resolution")
    if not resolution:
        for pattern, value in _RESOLUTION_PATTERNS:
            if pattern.search(filename):
                resolution = value
                break

    # Extract source
    source: str | None = groups.get("source")
    if not source:
        for pattern, value in _SOURCE_PATTERNS:
            if pattern.search(filename):
                source = value
                break

    # Extract codec
    codec: str | None = groups.get("codec")
    if not codec:
        for pattern, value in _CODEC_PATTERNS:
            if pattern.search(filename):
                codec = value
                break

    # Extract HDR format
    hdr_format: str | None = groups.get("hdr_format") or groups.get("hdr")
    if not hdr_format:
        for pattern, value in _HDR_PATTERNS:
            if pattern.search(filename):
                hdr_format = value
                break

    # Extract frame rate (critical for sports!)
    frame_rate: int | None = groups.get("frame_rate")
    if not frame_rate:
        for pattern, value in _FRAME_RATE_PATTERNS:
            if pattern.search(filename):
                frame_rate = value
                break

    # Extract bit depth (10-bit = better colors)
    bit_depth: int | None = groups.get("bit_depth")
    if not bit_depth:
        for pattern, value in _BIT_DEPTH_PATTERNS:
            if pattern.search(filename):
                bit_depth = value
                break

    # Extract audio format
    audio: str | None = groups.get("audio")
    if not audio:
        for pattern, value in _AUDIO_PATTERNS:
            if pattern.search(filename):
                audio = value
                break

    # Extract broadcaster (official sources are preferred)
    broadcaster: str | None = groups.get("broadcaster")
    if not broadcaster:
        for pattern, value in _BROADCASTER_PATTERNS:
            if pattern.search(filename):
                broadcaster = value
                break

    # Extract release group
    release_group: str | None = groups.get("release_group") or groups.get("group")
    if not release_group:
        release_group = _extract_release_group(filename)

    # Check for PROPER/REPACK
    is_proper = bool(_PROPER_PATTERN.search(filename))
    is_repack = bool(_REPACK_PATTERN.search(filename)) or bool(_RERIP_PATTERN.search(filename))

    return QualityInfo(
        resolution=resolution,
        source=source,
        release_group=release_group,
        is_proper=is_proper,
        is_repack=is_repack,
        codec=codec,
        hdr_format=hdr_format,
        frame_rate=frame_rate,
        bit_depth=bit_depth,
        audio=audio,
        broadcaster=broadcaster,
    )
