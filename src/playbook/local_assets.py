"""Local fallback artwork for Plex metadata sync.

Resolves user-provided poster/background files from a configured assets
directory. These are used as a *fallback* when TVSportsDB has no artwork
for an item (``url_poster: null``) - real artwork from the API always wins.

Directory layout (relative to the configured ``fallback_assets_dir``):

    <show_slug>/poster.jpg          Show poster
    <show_slug>/background.jpg      Show background
    <show_slug>/season-03.jpg       Poster for season 3 (unpadded also works)
    <show_slug>/s03e02.jpg          Poster for season 3, episode 2

``<show_slug>`` is the TVSportsDB show slug (e.g. ``ufc-2026``), the same
value as ``show_slug`` in the sport config. Supported image extensions:
jpg, jpeg, png, webp.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING

from .utils import sanitize_component

if TYPE_CHECKING:
    from .models import Episode, Season, Show

LOGGER = logging.getLogger(__name__)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def asset_content_type(path: Path) -> str:
    """Return the MIME type for an image file, defaulting to JPEG."""
    content_type, _ = mimetypes.guess_type(path.name)
    return content_type or "image/jpeg"


def _season_number(season: Season) -> int | None:
    if season.display_number is not None:
        return season.display_number
    return season.index


def _episode_number(episode: Episode) -> int | None:
    if episode.display_number is not None:
        return episode.display_number
    return episode.index


class LocalAssetResolver:
    """Looks up local fallback artwork files for shows, seasons, and episodes."""

    def __init__(self, assets_dir: str | Path | None) -> None:
        self.assets_dir = Path(assets_dir) if assets_dir else None
        if self.assets_dir and not self.assets_dir.is_dir():
            LOGGER.warning("Fallback assets directory does not exist: %s", self.assets_dir)

    @property
    def enabled(self) -> bool:
        return self.assets_dir is not None

    def _find(self, show: Show, stems: list[str]) -> Path | None:
        """Return the first existing image file matching any stem for the show."""
        if not self.assets_dir or not show.key:
            return None
        # show.key is the API-supplied slug (untrusted); sanitize it into a single
        # path component so it can never escape the assets directory via "../" or
        # an absolute path.
        show_dir = self.assets_dir / sanitize_component(show.key)
        for stem in stems:
            for ext in IMAGE_EXTENSIONS:
                candidate = show_dir / f"{stem}{ext}"
                if candidate.is_file() and self._within_assets_dir(candidate):
                    return candidate
        return None

    def _within_assets_dir(self, candidate: Path) -> bool:
        """Defense in depth: reject paths that resolve outside the assets dir."""
        assert self.assets_dir is not None
        try:
            return candidate.resolve().is_relative_to(self.assets_dir.resolve())
        except OSError:
            return False

    def show_poster(self, show: Show) -> Path | None:
        return self._find(show, ["poster"])

    def show_background(self, show: Show) -> Path | None:
        return self._find(show, ["background"])

    def season_poster(self, show: Show, season: Season) -> Path | None:
        number = _season_number(season)
        if number is None:
            return None
        return self._find(show, [f"season-{number:02d}", f"season-{number}"])

    def episode_poster(self, show: Show, season: Season, episode: Episode) -> Path | None:
        season_number = _season_number(season)
        episode_number = _episode_number(episode)
        if season_number is None or episode_number is None:
            return None
        return self._find(show, [f"s{season_number:02d}e{episode_number:02d}"])
