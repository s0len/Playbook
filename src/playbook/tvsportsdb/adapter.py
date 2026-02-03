"""Adapter to convert API responses to Playbook dataclass models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import Episode, Season, Show

if TYPE_CHECKING:
    from .models import EpisodeResponse, SeasonResponse, ShowResponse, TeamAliasResponse


class TVSportsDBAdapter:
    """Converts TheTVSportsDB API responses to Playbook dataclass models."""

    def to_show(self, response: ShowResponse) -> Show:
        """Convert ShowResponse to Show model.

        Args:
            response: API show response

        Returns:
            Playbook Show dataclass
        """
        seasons = [self.to_season(s, idx + 1) for idx, s in enumerate(sorted(response.seasons, key=lambda x: x.number))]
        return Show(
            key=response.slug,
            title=response.title,
            summary=response.summary,
            seasons=seasons,
            metadata={
                "id": response.id,
                "slug": response.slug,
                "sort_title": response.sort_title,
                "url_poster": response.url_poster,
                "url_background": response.url_background,
                "season_count": response.season_count,
                "episode_count": response.episode_count,
            },
        )

    def to_season(self, response: SeasonResponse, index: int) -> Season:
        """Convert SeasonResponse to Season model.

        Args:
            response: API season response
            index: Sequential index (1-based) of the season

        Returns:
            Playbook Season dataclass
        """
        episodes = [
            self.to_episode(e, idx + 1) for idx, e in enumerate(sorted(response.episodes, key=lambda x: x.number))
        ]
        return Season(
            key=str(response.number),
            title=response.title,
            summary=response.summary,
            index=index,
            episodes=episodes,
            sort_title=response.sort_title,
            display_number=response.number,
            round_number=response.number,
            metadata={
                "id": response.id,
                "show_id": response.show_id,
                "number": response.number,
                "url_poster": response.url_poster,
                "aliases": response.aliases,
            },
        )

    def to_episode(self, response: EpisodeResponse, index: int) -> Episode:
        """Convert EpisodeResponse to Episode model.

        Args:
            response: API episode response
            index: Sequential index (1-based) of the episode

        Returns:
            Playbook Episode dataclass
        """
        return Episode(
            title=response.title,
            summary=response.summary,
            originally_available=response.originally_available,
            index=index,
            metadata={
                "id": response.id,
                "season_id": response.season_id,
                "number": response.number,
                "url_poster": response.url_poster,
            },
            display_number=response.number,
            aliases=list(response.aliases),
        )

    def to_team_alias_map(self, aliases: list[TeamAliasResponse]) -> dict[str, str]:
        """Convert team aliases to lookup map.

        Creates a dictionary mapping normalized alias -> canonical_name
        for fast team name resolution.

        Args:
            aliases: List of team alias responses from API

        Returns:
            Dict mapping lowercase alias to canonical team name
        """
        return {a.alias.lower(): a.canonical_name for a in aliases}
