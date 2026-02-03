"""Quality scoring engine for file upgrade decisions.

This module provides functionality for computing quality scores from extracted
quality attributes and comparing scores to make upgrade decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import QualityProfile
    from .quality import QualityInfo


@dataclass
class QualityScore:
    """Computed quality score with breakdown.

    Attributes:
        total: Total quality score (sum of all components)
        resolution_score: Points from resolution (e.g., 1080p = 300)
        source_score: Points from source (e.g., webdl = 90)
        release_group_score: Points from release group (e.g., mwr = 50)
        proper_bonus: Bonus points for PROPER release
        repack_bonus: Bonus points for REPACK release
        hdr_bonus: Bonus points for HDR content
    """

    total: int
    resolution_score: int = 0
    source_score: int = 0
    release_group_score: int = 0
    proper_bonus: int = 0
    repack_bonus: int = 0
    hdr_bonus: int = 0

    def to_dict(self) -> dict[str, int]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "total": self.total,
            "resolution_score": self.resolution_score,
            "source_score": self.source_score,
            "release_group_score": self.release_group_score,
            "proper_bonus": self.proper_bonus,
            "repack_bonus": self.repack_bonus,
            "hdr_bonus": self.hdr_bonus,
        }

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> QualityScore:
        """Create from a dictionary."""
        return cls(
            total=data.get("total", 0),
            resolution_score=data.get("resolution_score", 0),
            source_score=data.get("source_score", 0),
            release_group_score=data.get("release_group_score", 0),
            proper_bonus=data.get("proper_bonus", 0),
            repack_bonus=data.get("repack_bonus", 0),
            hdr_bonus=data.get("hdr_bonus", 0),
        )


@dataclass
class QualityComparison:
    """Result of comparing two quality scores.

    Attributes:
        should_upgrade: Whether the new file should replace the existing one
        reason: Human-readable explanation for the decision
        new_score: Quality score of the new file
        existing_score: Quality score of the existing file (None if no existing)
        cutoff_reached: Whether the existing file has reached the cutoff score
    """

    should_upgrade: bool
    reason: str
    new_score: QualityScore
    existing_score: QualityScore | None = None
    cutoff_reached: bool = False


def compute_quality_score(
    quality_info: QualityInfo,
    profile: QualityProfile,
) -> QualityScore:
    """Compute a quality score from extracted quality attributes.

    Args:
        quality_info: Extracted quality attributes from a filename.
        profile: Quality profile with scoring configuration.

    Returns:
        QualityScore with computed values and breakdown.

    Examples:
        >>> from playbook.quality import QualityInfo
        >>> from playbook.config import QualityProfile
        >>> info = QualityInfo(resolution="1080p", source="webdl", release_group="mwr")
        >>> profile = QualityProfile(enabled=True)
        >>> score = compute_quality_score(info, profile)
        >>> score.total
        440  # 300 (1080p) + 90 (webdl) + 50 (mwr)
    """
    scoring = profile.scoring

    # Resolution score
    resolution_score = 0
    if quality_info.resolution:
        resolution_score = scoring.resolution.get(quality_info.resolution.lower(), 0)

    # Source score
    source_score = 0
    if quality_info.source:
        source_score = scoring.source.get(quality_info.source.lower(), 0)

    # Release group score
    release_group_score = 0
    if quality_info.release_group:
        release_group_score = scoring.release_group.get(quality_info.release_group.lower(), 0)

    # Bonus scores
    proper_bonus = scoring.proper_bonus if quality_info.is_proper else 0
    repack_bonus = scoring.repack_bonus if quality_info.is_repack else 0
    hdr_bonus = scoring.hdr_bonus if quality_info.hdr_format else 0

    total = resolution_score + source_score + release_group_score + proper_bonus + repack_bonus + hdr_bonus

    return QualityScore(
        total=total,
        resolution_score=resolution_score,
        source_score=source_score,
        release_group_score=release_group_score,
        proper_bonus=proper_bonus,
        repack_bonus=repack_bonus,
        hdr_bonus=hdr_bonus,
    )


def compare_quality(
    new_info: QualityInfo,
    existing_score: int | None,
    profile: QualityProfile,
) -> QualityComparison:
    """Compare a new file's quality against an existing file's score.

    This function implements the quality upgrade decision logic:
    1. If min_score is set and new file is below it, reject
    2. If no existing file, accept the new file
    3. If existing file hasn't reached cutoff, upgrade if new score is higher
    4. If existing file has reached cutoff, only upgrade for PROPER/REPACK
    5. PROPER/REPACK always upgrades regardless of cutoff

    Args:
        new_info: Quality info extracted from the new file.
        existing_score: Quality score of the existing file (None if no existing).
        profile: Quality profile with scoring and cutoff configuration.

    Returns:
        QualityComparison with the upgrade decision and reasoning.

    Examples:
        # Resolution upgrade (720p -> 1080p)
        >>> new_info = QualityInfo(resolution="1080p", source="webdl")
        >>> compare = compare_quality(new_info, existing_score=290, profile=profile)
        >>> compare.should_upgrade
        True
        >>> compare.reason
        'Higher quality score: 390 > 290'

        # Cutoff reached, no upgrade
        >>> new_info = QualityInfo(resolution="2160p", source="webdl")
        >>> compare = compare_quality(new_info, existing_score=440, profile=profile_with_cutoff_400)
        >>> compare.should_upgrade
        False
        >>> compare.cutoff_reached
        True

        # PROPER overrides cutoff
        >>> new_info = QualityInfo(resolution="1080p", source="webdl", is_proper=True)
        >>> compare = compare_quality(new_info, existing_score=440, profile=profile_with_cutoff_400)
        >>> compare.should_upgrade
        True
    """
    new_score = compute_quality_score(new_info, profile)

    # Check minimum score threshold
    if profile.min_score is not None and new_score.total < profile.min_score:
        return QualityComparison(
            should_upgrade=False,
            reason=f"Below minimum score threshold: {new_score.total} < {profile.min_score}",
            new_score=new_score,
            existing_score=None,
            cutoff_reached=False,
        )

    # No existing file - accept the new file
    if existing_score is None:
        return QualityComparison(
            should_upgrade=True,
            reason="No existing file",
            new_score=new_score,
            existing_score=None,
            cutoff_reached=False,
        )

    # Create existing score object for comparison result
    existing_score_obj = QualityScore(total=existing_score)

    # Check if existing file has reached cutoff
    cutoff_reached = False
    if profile.cutoff is not None and existing_score >= profile.cutoff:
        cutoff_reached = True

    # PROPER/REPACK always allows upgrade, even when cutoff is reached
    if new_info.is_proper:
        return QualityComparison(
            should_upgrade=True,
            reason=f"PROPER release replaces existing (score: {new_score.total} vs {existing_score})",
            new_score=new_score,
            existing_score=existing_score_obj,
            cutoff_reached=cutoff_reached,
        )

    if new_info.is_repack:
        return QualityComparison(
            should_upgrade=True,
            reason=f"REPACK release replaces existing (score: {new_score.total} vs {existing_score})",
            new_score=new_score,
            existing_score=existing_score_obj,
            cutoff_reached=cutoff_reached,
        )

    # If cutoff is reached, no upgrade (unless PROPER/REPACK, handled above)
    if cutoff_reached:
        return QualityComparison(
            should_upgrade=False,
            reason=f"Cutoff reached ({profile.cutoff}), existing score {existing_score} is sufficient",
            new_score=new_score,
            existing_score=existing_score_obj,
            cutoff_reached=True,
        )

    # Compare scores - upgrade if new is higher
    if new_score.total > existing_score:
        return QualityComparison(
            should_upgrade=True,
            reason=f"Higher quality score: {new_score.total} > {existing_score}",
            new_score=new_score,
            existing_score=existing_score_obj,
            cutoff_reached=False,
        )

    # New score is not higher - no upgrade
    return QualityComparison(
        should_upgrade=False,
        reason=f"Not a quality upgrade: {new_score.total} <= {existing_score}",
        new_score=new_score,
        existing_score=existing_score_obj,
        cutoff_reached=False,
    )


def get_effective_quality_profile(
    sport_profile: QualityProfile | None,
    global_profile: QualityProfile,
) -> QualityProfile:
    """Get the effective quality profile for a sport.

    Merges the sport-specific profile with the global profile. Sport-specific
    settings override global settings where specified.

    Args:
        sport_profile: Sport-specific quality profile (may be None).
        global_profile: Global quality profile from settings.

    Returns:
        The effective quality profile to use for the sport.
    """
    if sport_profile is None:
        return global_profile

    # Import here to avoid circular import
    from .config import QualityProfile, QualityScoring

    # Merge scoring dictionaries - sport overrides take precedence
    merged_resolution = {**global_profile.scoring.resolution, **sport_profile.scoring.resolution}
    merged_source = {**global_profile.scoring.source, **sport_profile.scoring.source}
    merged_release_group = {**global_profile.scoring.release_group, **sport_profile.scoring.release_group}

    # For bonus values, use sport's value if it differs from default
    default_scoring = QualityScoring()
    proper_bonus = (
        sport_profile.scoring.proper_bonus
        if sport_profile.scoring.proper_bonus != default_scoring.proper_bonus
        else global_profile.scoring.proper_bonus
    )
    repack_bonus = (
        sport_profile.scoring.repack_bonus
        if sport_profile.scoring.repack_bonus != default_scoring.repack_bonus
        else global_profile.scoring.repack_bonus
    )
    hdr_bonus = (
        sport_profile.scoring.hdr_bonus
        if sport_profile.scoring.hdr_bonus != default_scoring.hdr_bonus
        else global_profile.scoring.hdr_bonus
    )

    merged_scoring = QualityScoring(
        resolution=merged_resolution,
        source=merged_source,
        release_group=merged_release_group,
        proper_bonus=proper_bonus,
        repack_bonus=repack_bonus,
        hdr_bonus=hdr_bonus,
    )

    # Determine enabled state - sport can override global
    enabled = sport_profile.enabled if sport_profile.enabled else global_profile.enabled

    # Use sport's cutoff/min_score if set, otherwise global
    cutoff = sport_profile.cutoff if sport_profile.cutoff is not None else global_profile.cutoff
    min_score = sport_profile.min_score if sport_profile.min_score is not None else global_profile.min_score

    return QualityProfile(
        enabled=enabled,
        scoring=merged_scoring,
        cutoff=cutoff,
        min_score=min_score,
    )
