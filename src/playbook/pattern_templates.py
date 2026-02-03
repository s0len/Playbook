from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from typing import Any

from .utils import load_yaml_file

PLACEHOLDER_RE = re.compile(r"(?<!\?P)<([A-Za-z0-9_]+)>")
_REGEX_TOKENS: dict[str, str] = {}
_DEFAULT_SPORTS: list[dict[str, Any]] = []


@dataclass
class PatternSetData:
    """Parsed pattern set containing patterns and optional default source globs."""

    patterns: list[dict[str, Any]] = field(default_factory=list)
    default_source_globs: list[str] = field(default_factory=list)


def _resolve_regex_tokens(raw_tokens: dict[str, str]) -> dict[str, str]:
    resolved: dict[str, str] = {}

    def resolve(name: str, stack: list[str]) -> str:
        if name in resolved:
            return resolved[name]
        if name not in raw_tokens:
            raise ValueError(f"Unknown regex token <{name}> referenced")
        if name in stack:
            cycle = " -> ".join(stack + [name])
            raise ValueError(f"Circular regex token reference detected: {cycle}")
        pattern = raw_tokens[name]

        def replace(match: re.Match[str]) -> str:
            token_name = match.group(1)
            return resolve(token_name, stack + [name])

        expanded = PLACEHOLDER_RE.sub(replace, pattern)
        resolved[name] = expanded
        return expanded

    for token_name in raw_tokens:
        resolve(token_name, [])

    return resolved


def _expand_placeholders(text: str, tokens: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        token_name = match.group(1)
        if token_name not in tokens:
            raise ValueError(f"Unknown regex token <{token_name}> referenced in pattern: {text}")
        return tokens[token_name]

    return PLACEHOLDER_RE.sub(replace, text)


@lru_cache
def _load_raw_pattern_data() -> dict[str, PatternSetData]:
    """Load and parse the pattern templates file."""
    with resources.as_file(resources.files(__package__) / "pattern_templates.yaml") as path:
        data = load_yaml_file(path)

    raw_tokens = data.get("regex_tokens") or {}
    if not isinstance(raw_tokens, dict):
        raise ValueError("'regex_tokens' must be a mapping of token -> regex fragment when provided")
    normalized_tokens = {str(key): str(value) for key, value in raw_tokens.items()}
    resolved_tokens = _resolve_regex_tokens(normalized_tokens)
    global _REGEX_TOKENS
    _REGEX_TOKENS = resolved_tokens

    # Load default sports definitions
    global _DEFAULT_SPORTS
    raw_default_sports = data.get("default_sports", [])
    _DEFAULT_SPORTS = deepcopy(raw_default_sports) if isinstance(raw_default_sports, list) else []

    raw_pattern_sets = data.get("pattern_sets", {})
    if not isinstance(raw_pattern_sets, dict):
        raise ValueError("Builtin pattern templates must define a mapping of pattern sets")

    result: dict[str, PatternSetData] = {}

    for name, value in raw_pattern_sets.items():
        # Support both old format (list of patterns) and new format (dict with patterns and default_source_globs)
        if isinstance(value, list):
            # Legacy format: just a list of patterns
            patterns = value
            default_source_globs: list[str] = []
        elif isinstance(value, dict):
            # New format: dict with 'patterns' and optional 'default_source_globs'
            patterns = value.get("patterns", [])
            default_source_globs = value.get("default_source_globs", [])
            if not isinstance(patterns, list):
                patterns = []
            if not isinstance(default_source_globs, list):
                default_source_globs = []
        else:
            continue

        # Expand regex tokens in patterns
        for pattern in patterns:
            if not isinstance(pattern, dict):
                continue
            regex_value = pattern.get("regex")
            if isinstance(regex_value, str):
                pattern["regex"] = _expand_placeholders(regex_value, resolved_tokens)

        result[name] = PatternSetData(
            patterns=patterns,
            default_source_globs=[str(g) for g in default_source_globs],
        )

    return result


def load_builtin_pattern_sets() -> dict[str, list[dict[str, Any]]]:
    """Load the curated pattern sets shipped with Playbook.

    Returns just the patterns for backwards compatibility.
    Use load_pattern_set_data() to also get default_source_globs.
    """
    data = _load_raw_pattern_data()
    return {name: ps.patterns for name, ps in data.items()}


def load_pattern_set_data() -> dict[str, PatternSetData]:
    """Load pattern sets with both patterns and default_source_globs."""
    return _load_raw_pattern_data()


def get_default_source_globs(pattern_set_names: list[str]) -> list[str]:
    """Get merged default source globs from multiple pattern sets.

    Args:
        pattern_set_names: List of pattern set names to get defaults from

    Returns:
        Merged list of default source globs (duplicates removed, order preserved)
    """
    data = _load_raw_pattern_data()
    seen: set[str] = set()
    result: list[str] = []

    for name in pattern_set_names:
        if name not in data:
            continue
        for glob in data[name].default_source_globs:
            if glob not in seen:
                seen.add(glob)
                result.append(glob)

    return result


def expand_regex_with_tokens(regex: str) -> str:
    if PLACEHOLDER_RE.search(regex) is None:
        return regex
    if not _REGEX_TOKENS:
        # Ensure tokens are loaded by forcing the builtin template load.
        load_builtin_pattern_sets()
    return _expand_placeholders(regex, _REGEX_TOKENS)


def load_default_sports() -> list[dict[str, Any]]:
    """Load the default sports definitions from pattern_templates.yaml.

    Returns a list of sport configuration dictionaries that should be enabled
    by default. Each sport includes:
    - id: Sport identifier
    - name: Display name
    - pattern_sets: List of pattern set names to use
    - variants: Year-based variants with show_slugs
    - team_alias_map: Optional team alias mapping
    - destination: Optional destination template overrides
    - season_overrides: Optional per-season configuration

    Note: source_globs are NOT included here; they are computed from
    the pattern_sets' default_source_globs at config load time.
    """
    if not _DEFAULT_SPORTS:
        # Ensure data is loaded
        _load_raw_pattern_data()
    return deepcopy(_DEFAULT_SPORTS)
