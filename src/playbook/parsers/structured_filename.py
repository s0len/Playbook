from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..utils import normalize_token, sanitize_component

_QUALITY_TOKENS = {
    "2160p",
    "1080p",
    "720p",
    "hdtv",
    "web",
    "webrip",
    "proper",
    "repack",
}

_PROVIDER_TOKENS = {
    "sky",
    "fubo",
    "espn",
    "espn+",
    "espnplus",
    "tsn",
    "nbcsn",
    "fox",
    "verum",
}


@dataclass(slots=True)
class StructuredName:
    raw: str
    competition: str | None = None
    season: str | None = None
    year: int | None = None
    date: dt.date | None = None
    round: int | None = None
    matchday: int | None = None
    teams: list[str] = field(default_factory=list)
    home_team: str | None = None
    away_team: str | None = None
    resolution: str | None = None
    fps: int | None = None
    provider: str | None = None
    language: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    def canonical_matchup(self) -> str | None:
        if len(self.teams) >= 2:
            return f"{self.teams[0]} vs {self.teams[1]}"
        if self.home_team and self.away_team:
            return f"{self.home_team} vs {self.away_team}"
        return None


def _clean_tokens(text: str) -> str:
    normalized = re.sub(r"[._]+", " ", text)
    normalized = normalized.replace("@", " at ")
    normalized = normalized.replace("+", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _coerce_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _coerce_date(year: int, month: int, day: int) -> dt.date | None:
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def _parse_date_candidates(text: str) -> tuple[dt.date | None, int | None]:
    """Return (date, standalone_year) parsed from the text."""
    cleaned = text.replace(".", " ").replace("-", " ").replace("_", " ")
    tokens = [token for token in re.split(r"\s+", cleaned) if token]

    year_tokens = [_coerce_int(token) for token in tokens if len(token) == 4 and token.isdigit()]
    year_tokens = [token for token in year_tokens if token is not None and token > 1900]
    standalone_year = year_tokens[0] if year_tokens else None

    # Patterns with explicit year
    joined = " ".join(tokens)
    for regex in (
        r"(?P<y>\d{4})[.\-/ ](?P<m>\d{1,2})[.\-/ ](?P<d>\d{1,2})",
        r"(?P<d>\d{1,2})[.\-/ ](?P<m>\d{1,2})[.\-/ ](?P<y>\d{4})",
    ):
        match = re.search(regex, joined)
        if match:
            y = _coerce_int(match.group("y"))
            m = _coerce_int(match.group("m"))
            d = _coerce_int(match.group("d"))
            if y and m and d:
                parsed = _coerce_date(y, m, d)
                if parsed:
                    return parsed, standalone_year

    # Day/Month fragments with year elsewhere (e.g., "EPL 2025 Fulham vs City 02 12")
    if standalone_year:
        fragment_match = re.search(r"(?P<d>\d{1,2})[.\-/ ](?P<m>\d{1,2})(?!\d)", joined)
        if fragment_match:
            d = _coerce_int(fragment_match.group("d"))
            m = _coerce_int(fragment_match.group("m"))
            if d and m:
                parsed = _coerce_date(standalone_year, m, d)
                if parsed:
                    return parsed, standalone_year

    return None, standalone_year


def _trim_noise(segment: str) -> str:
    words = [word for word in re.split(r"\s+", segment) if word]
    cleaned: list[str] = []
    for word in words:
        lowered = word.lower()
        if lowered.isdigit():
            break
        if lowered in _QUALITY_TOKENS:
            break
        if re.match(r"\d{3,4}p", lowered):
            break
        if re.match(r"\d{2}fps", lowered):
            break
        cleaned.append(word)
    return " ".join(cleaned).strip()


def _extract_matchup(text: str) -> tuple[list[str], str | None, str | None]:
    normalized = _clean_tokens(text)
    pattern = re.compile(r"(?P<a>[A-Za-z0-9 .&'/-]+?)\s+(?:vs|v|at|@)\s+(?P<b>[A-Za-z0-9 .&'/-]+)", re.IGNORECASE)
    match = pattern.search(normalized)
    if not match:
        return [], None, None

    home_raw = _trim_noise(match.group("a"))
    away_raw = _trim_noise(match.group("b"))
    teams = [team for team in [home_raw, away_raw] if team]
    return teams, home_raw or None, away_raw or None


def _extract_resolution(text: str) -> tuple[str | None, int | None]:
    res = None
    fps = None
    res_match = re.search(r"\b(2160p|1080p|720p)\b", text, re.IGNORECASE)
    if res_match:
        res = res_match.group(1).lower()
    fps_match = re.search(r"\b(\d{2})\s?fps\b", text, re.IGNORECASE)
    if fps_match:
        fps = _coerce_int(fps_match.group(1))
    return res, fps


def _extract_provider(text: str) -> str | None:
    lowered = text.lower()
    normalized = lowered.replace("+", "")
    for provider in _PROVIDER_TOKENS:
        provider_clean = provider.replace("+", "")
        if provider in lowered or provider_clean in normalized:
            return provider
    return None


def _canonicalize_team(team: str, alias_lookup: dict[str, str]) -> str:
    normalized = normalize_token(team)
    if alias_lookup:
        mapped = alias_lookup.get(normalized)
        if mapped:
            return mapped
    return team.strip()


def parse_structured_filename(filename: str, alias_lookup: dict[str, str] | None = None) -> StructuredName | None:
    alias_lookup = alias_lookup or {}
    name = Path(filename).stem
    cleaned = _clean_tokens(name)

    date, standalone_year = _parse_date_candidates(cleaned)
    resolution, fps = _extract_resolution(cleaned)
    provider = _extract_provider(cleaned)

    teams, home_raw, away_raw = _extract_matchup(cleaned)
    teams = [_canonicalize_team(team, alias_lookup) for team in teams]

    competition = None
    competition_match = re.match(r"^(?P<comp>[A-Za-z]+)", cleaned)
    if competition_match:
        competition = competition_match.group("comp")

    year_value = standalone_year
    if not year_value and date:
        year_value = date.year

    structured = StructuredName(
        raw=filename,
        competition=competition,
        season=None,
        year=year_value,
        date=date,
        teams=teams,
        home_team=teams[0] if teams else None,
        away_team=teams[1] if len(teams) > 1 else None,
        resolution=resolution,
        fps=fps,
        provider=provider,
        extra={"cleaned": cleaned},
    )

    # Try to pull round/matchday from patterns like "Round04" or "Week 7"
    round_match = re.search(r"(round|week|matchday)[\s_-]*(\d{1,3})", cleaned, re.IGNORECASE)
    if round_match:
        structured.round = _coerce_int(round_match.group(2))
        structured.matchday = structured.round

    return structured


def build_canonical_filename(structured: StructuredName, *, language: str = "EN", extension: str = "mkv") -> str:
    """Assemble a normalized filename from structured components."""
    parts: list[str] = []
    if structured.competition:
        parts.append(structured.competition.upper())
    if structured.date:
        parts.append(structured.date.isoformat())
    elif structured.year:
        parts.append(str(structured.year))

    matchup = structured.canonical_matchup() or structured.extra.get("cleaned") or "match"
    parts.append(matchup.replace(" ", "_"))

    if structured.resolution:
        parts.append(structured.resolution)
    if structured.fps:
        parts.append(f"{structured.fps}fps")
    if language:
        parts.append(language)
    if structured.provider:
        parts.append(structured.provider)

    filename = "_".join(parts)
    safe = sanitize_component(filename, replacement="_")
    return f"{safe}.{extension.lstrip('.')}"
