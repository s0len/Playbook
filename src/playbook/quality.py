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
    """

    resolution: str | None = None
    source: str | None = None
    release_group: str | None = None
    is_proper: bool = False
    is_repack: bool = False
    codec: str | None = None
    hdr_format: str | None = None

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
        )


# Resolution patterns (order matters - check higher resolutions first)
_RESOLUTION_PATTERNS = [
    (re.compile(r"\b2160p\b", re.IGNORECASE), "2160p"),
    (re.compile(r"\b4k\b", re.IGNORECASE), "2160p"),
    (re.compile(r"\buhd\b", re.IGNORECASE), "2160p"),
    (re.compile(r"\b1080p\b", re.IGNORECASE), "1080p"),
    (re.compile(r"\b1080i\b", re.IGNORECASE), "1080p"),
    (re.compile(r"\b720p\b", re.IGNORECASE), "720p"),
    (re.compile(r"\b576p\b", re.IGNORECASE), "576p"),
    (re.compile(r"\b480p\b", re.IGNORECASE), "480p"),
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
    # F1/Motorsport groups
    "mwr",
    "verum",
    "nightninjas",
    "smcgill1969",
    "sh0ww",
    "ebi",
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
    # Quality indicators that look like groups but aren't
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
            "mkv",
            "mp4",
            "avi",
            "srt",
            "sub",
            "idx",
            "nfo",
            "sample",
            "proof",
            "720p",
            "1080p",
            "2160p",
            "480p",
            "576p",
            "x264",
            "x265",
            "h264",
            "h265",
            "hevc",
            "avc",
            "aac",
            "dts",
            "ac3",
            "flac",
            "proper",
            "repack",
            "rerip",
            "web",
            "webrip",
            "webdl",
            "hdtv",
            "bluray",
            "bdrip",
            "remux",
            "hdr",
            "hdr10",
            "dv",
            "atmos",
            "dl",  # From WEB-DL
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
    source type, codec, HDR format, release group, and PROPER/REPACK flags.

    Args:
        filename: The filename to parse (without directory path).
        captured_groups: Optional regex capture groups from pattern matching.
            Can contain pre-extracted values like 'resolution', 'source',
            'release_group' that take precedence over filename parsing.

    Returns:
        QualityInfo with extracted quality attributes.

    Examples:
        >>> extract_quality("Formula.1.2026.R05.Monaco.GP.Race.1080p.WEB-DL.MWR.mkv")
        QualityInfo(resolution='1080p', source='webdl', release_group='mwr', ...)

        >>> extract_quality("UFC.300.Main.Event.720p.HDTV.PROPER.x264.mkv")
        QualityInfo(resolution='720p', source='hdtv', is_proper=True, codec='x264', ...)
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
    )
