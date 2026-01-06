from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from jsonschema import Draft7Validator

from .pattern_templates import load_builtin_pattern_sets


@dataclass(slots=True)
class ValidationIssue:
    """Represents a single validation problem."""

    severity: str
    path: str
    message: str
    code: str
    line_number: Optional[int] = None
    fix_suggestion: Optional[str] = None


@dataclass(slots=True)
class ValidationReport:
    """Aggregates validation warnings and errors."""

    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


_TIME_PATTERN = r"^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$"
_LINK_MODES = ["hardlink", "copy", "symlink"]

CONFIG_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "settings": {
            "type": "object",
            "properties": {
                "source_dir": {"type": "string"},
                "destination_dir": {"type": "string"},
                "cache_dir": {"type": "string"},
                "dry_run": {"type": "boolean"},
                "skip_existing": {"type": "boolean"},
                "link_mode": {"type": "string", "enum": _LINK_MODES},
                "destination": {
                    "type": "object",
                    "properties": {
                        "root_template": {"type": "string"},
                        "season_dir_template": {"type": "string"},
                        "episode_template": {"type": "string"},
                    },
                    "additionalProperties": True,
                },
                "notifications": {
                    "type": "object",
                    "properties": {
                        "batch_daily": {"type": "boolean"},
                        "flush_time": {"type": "string", "pattern": _TIME_PATTERN},
                    },
                    "additionalProperties": True,
                },
                "file_watcher": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "paths": {
                            "oneOf": [
                                {"type": "array", "items": {"type": "string"}},
                                {"type": "string"},
                            ]
                        },
                        "include": {
                            "oneOf": [
                                {"type": "array", "items": {"type": "string"}},
                                {"type": "string"},
                            ]
                        },
                        "ignore": {
                            "oneOf": [
                                {"type": "array", "items": {"type": "string"}},
                                {"type": "string"},
                            ]
                        },
                        "debounce_seconds": {"type": ["number", "integer"], "minimum": 0},
                        "reconcile_interval": {"type": "integer", "minimum": 0},
                    },
                    "additionalProperties": True,
                },
                "kometa_trigger": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "mode": {"type": "string", "enum": ["kubernetes", "docker"]},
                        "namespace": {"type": "string"},
                        "cronjob_name": {"type": "string"},
                        "job_name_prefix": {"type": "string"},
                        "docker": {
                            "type": "object",
                            "properties": {
                                "binary": {"type": "string"},
                                "image": {"type": "string"},
                                "config_path": {"type": "string"},
                                "container_path": {"type": "string"},
                                "volume_mode": {"type": "string"},
                                "libraries": {"type": "string"},
                                "container_name": {"type": "string"},
                                "exec_python": {"type": "string"},
                                "exec_script": {"type": "string"},
                                "exec_command": {
                                    "oneOf": [
                                        {"type": "array", "items": {"type": "string"}},
                                        {"type": "string"},
                                    ]
                                },
                                "extra_args": {
                                    "oneOf": [
                                        {"type": "array", "items": {"type": "string"}},
                                        {"type": "string"},
                                    ]
                                },
                                "env": {
                                    "type": "object",
                                    "additionalProperties": {"type": "string"},
                                },
                                "remove_container": {"type": "boolean"},
                                "interactive": {"type": "boolean"},
                            },
                            "additionalProperties": True,
                        },
                    },
                    "additionalProperties": True,
                },
            },
            "additionalProperties": True,
        },
        "pattern_sets": {
            "type": ["object", "null"],
            "patternProperties": {
                "^[A-Za-z0-9_.-]+$": {
                    "oneOf": [
                        {"type": "array", "items": {"$ref": "#/definitions/pattern_definition"}},
                        {"type": "null"},
                    ]
                }
            },
            "additionalProperties": True,
        },
        "sports": {
            "type": "array",
            "items": {"$ref": "#/definitions/sport"},
        },
    },
    "required": ["sports"],
    "additionalProperties": True,
    "definitions": {
        "metadata": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "minLength": 1},
                "show_key": {"type": ["string", "null"]},
                "ttl_hours": {"type": "integer", "minimum": 1},
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "season_overrides": {
                    "type": "object",
                    "additionalProperties": {"type": "object"},
                },
            },
            "required": ["url"],
            "additionalProperties": True,
        },
        "season_selector": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["round", "key", "title", "sequential", "date"],
                },
                "group": {"type": ["string", "null"]},
                "offset": {"type": "integer"},
                "mapping": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                },
                "value_template": {"type": ["string", "null"]},
            },
            "additionalProperties": True,
        },
        "episode_selector": {
            "type": "object",
            "properties": {
                "group": {"type": "string"},
                "allow_fallback_to_title": {"type": "boolean"},
                "default_value": {"type": ["string", "null"]},
            },
            "additionalProperties": True,
        },
        "pattern_definition": {
            "type": "object",
            "properties": {
                "regex": {"type": "string", "minLength": 1},
                "description": {"type": ["string", "null"]},
                "season_selector": {"$ref": "#/definitions/season_selector"},
                "episode_selector": {"$ref": "#/definitions/episode_selector"},
                "session_aliases": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "metadata_filters": {
                    "type": "object",
                    "additionalProperties": True,
                },
                "filename_template": {"type": ["string", "null"]},
                "season_dir_template": {"type": ["string", "null"]},
                "destination_root_template": {"type": ["string", "null"]},
                "priority": {"type": "integer"},
            },
            "required": ["regex"],
            "additionalProperties": True,
        },
        "sport": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "name": {"type": "string"},
                "enabled": {"type": "boolean"},
                "team_alias_map": {"type": ["string", "null"]},
                "metadata": {"$ref": "#/definitions/metadata"},
                "pattern_sets": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                },
                "file_patterns": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/pattern_definition"},
                },
                "source_globs": {"type": "array", "items": {"type": "string"}},
                "source_extensions": {"type": "array", "items": {"type": "string"}},
                "link_mode": {"type": "string", "enum": _LINK_MODES},
                "allow_unmatched": {"type": "boolean"},
                "destination": {
                    "type": "object",
                    "properties": {
                        "root_template": {"type": "string"},
                        "season_dir_template": {"type": "string"},
                        "episode_template": {"type": "string"},
                    },
                    "additionalProperties": True,
                },
                "variants": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "id_suffix": {"type": "string"},
                            "year": {"type": ["integer", "string"]},
                            "name": {"type": "string"},
                            "metadata": {"$ref": "#/definitions/metadata"},
                        },
                        "additionalProperties": True,
                    },
                },
            },
            "required": ["id"],
            "additionalProperties": True,
        },
    },
}


def extract_yaml_line_numbers(yaml_content: str) -> Dict[str, int]:
    """Extract line numbers for YAML keys from content.

    This function parses YAML content and creates a mapping from key paths
    to their line numbers in the original file. It attempts to use ruamel.yaml
    if available for accurate line tracking, otherwise falls back to a regex-based
    approach.

    Args:
        yaml_content: The YAML file content as a string

    Returns:
        Dictionary mapping key paths (e.g., "sports[0].id") to line numbers

    Example:
        >>> content = "settings:\\n  source_dir: /path\\n"
        >>> line_map = extract_yaml_line_numbers(content)
        >>> line_map.get("settings.source_dir")
        2
    """
    line_map: Dict[str, int] = {}

    # Try ruamel.yaml first for accurate line number tracking
    try:
        from ruamel.yaml import YAML

        yaml_parser = YAML()
        data = yaml_parser.load(yaml_content)

        def _traverse_ruamel(obj: Any, path: str = "") -> None:
            """Recursively traverse ruamel.yaml CommentedMap to extract line numbers."""
            try:
                from ruamel.yaml.comments import CommentedMap, CommentedSeq

                if isinstance(obj, CommentedMap):
                    for key, value in obj.items():
                        key_path = f"{path}.{key}" if path else str(key)
                        # Get line number for this key (lc = line/column info)
                        if hasattr(obj, 'lc') and obj.lc.data:
                            line_info = obj.lc.data.get(key)
                            if line_info is not None:
                                # line_info is typically (line, col, ...), 0-indexed
                                line_map[key_path] = line_info[0] + 1
                        _traverse_ruamel(value, key_path)

                elif isinstance(obj, CommentedSeq):
                    for index, item in enumerate(obj):
                        item_path = f"{path}[{index}]"
                        # Get line number for this array item
                        if hasattr(obj, 'lc') and obj.lc.data:
                            line_info = obj.lc.data.get(index)
                            if line_info is not None:
                                line_map[item_path] = line_info[0] + 1
                        _traverse_ruamel(item, item_path)

            except ImportError:
                pass

        _traverse_ruamel(data)

        if line_map:
            return line_map

    except ImportError:
        pass  # ruamel.yaml not available, fall back to regex approach
    except Exception:  # noqa: BLE001
        pass  # Any parsing errors, fall back to regex approach

    # Fallback: regex-based line number extraction
    # This approach is less accurate but works without ruamel.yaml
    lines = yaml_content.split('\n')
    current_path: List[str] = []
    array_indices: Dict[str, int] = {}

    for line_num, line in enumerate(lines, start=1):
        # Skip empty lines and comments
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue

        # Calculate indentation level
        indent = len(line) - len(stripped)

        # Match key-value pairs (key: value or key:)
        key_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$', stripped)
        if key_match:
            key = key_match.group(1)
            value = key_match.group(2).strip()

            # Determine the depth based on indentation (assuming 2 spaces per level)
            depth = indent // 2

            # Adjust current path to match depth
            current_path = current_path[:depth]
            current_path.append(key)

            # Build the full path
            path_str = '.'.join(current_path)
            line_map[path_str] = line_num

            # Reset array indices for this path
            array_indices[path_str] = 0

            continue

        # Match array items (- value or - )
        array_match = re.match(r'^-\s+(.*)$', stripped)
        if array_match and current_path:
            # Determine the parent array path
            depth = indent // 2
            parent_path = '.'.join(current_path[:depth])

            if parent_path not in array_indices:
                array_indices[parent_path] = 0
            else:
                array_indices[parent_path] += 1

            index = array_indices[parent_path]
            array_path = f"{parent_path}[{index}]"
            line_map[array_path] = line_num

            # Check if the array item has an inline key-value
            item_content = array_match.group(1).strip()
            inline_key_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$', item_content)
            if inline_key_match:
                inline_key = inline_key_match.group(1)
                inline_path = f"{array_path}.{inline_key}"
                line_map[inline_path] = line_num

    return line_map


def extract_yaml_line_numbers_from_file(file_path: Path) -> Dict[str, int]:
    """Extract line numbers for YAML keys from a file.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dictionary mapping key paths to line numbers
    """
    try:
        with file_path.open('r', encoding='utf-8') as f:
            content = f.read()
        return extract_yaml_line_numbers(content)
    except Exception:  # noqa: BLE001
        return {}


def _format_jsonschema_path(path: Sequence[Any]) -> str:
    if not path:
        return "<root>"
    tokens: List[str] = []
    for part in path:
        if isinstance(part, int):
            if tokens:
                tokens[-1] = f"{tokens[-1]}[{part}]"
            else:
                tokens.append(f"[{part}]")
        else:
            tokens.append(str(part))
    return ".".join(tokens) if tokens else "<root>"


def _parse_time(value: str) -> Optional[str]:
    try:
        parts = [int(part) for part in value.split(":")]
    except ValueError:
        return "components must be integers"
    if len(parts) not in {2, 3}:
        return "expected HH:MM or HH:MM:SS"
    hour, minute = parts[0], parts[1]
    second = parts[2] if len(parts) == 3 else 0
    try:
        dt.time(hour=hour, minute=minute, second=second)
    except ValueError as exc:
        return str(exc)
    return None


def _collect_pattern_set_names(data: Dict[str, Any]) -> Iterable[str]:
    builtin = set(load_builtin_pattern_sets().keys())
    user_sets = data.get("pattern_sets") or {}
    if isinstance(user_sets, dict):
        return builtin | set(user_sets.keys())
    return builtin


def _validate_metadata_block(
    metadata: Dict[str, Any],
    path: str,
    report: ValidationReport,
    line_map: Optional[Dict[str, int]] = None,
) -> None:
    url_value = metadata.get("url")
    if isinstance(url_value, str) and not url_value.strip():
        issue_path = path + ".url"
        report.errors.append(
            ValidationIssue(
                severity="error",
                path=issue_path,
                message="Metadata URL must not be blank",
                code="metadata-url",
                line_number=line_map.get(issue_path) if line_map else None,
            )
        )


def validate_config_data(
    data: Dict[str, Any],
    line_map: Optional[Dict[str, int]] = None,
) -> ValidationReport:
    """Validate configuration data against schema and semantic rules.

    Args:
        data: The configuration data to validate
        line_map: Optional mapping from config paths to line numbers in the source file

    Returns:
        ValidationReport containing any errors or warnings found
    """
    report = ValidationReport()
    validator = Draft7Validator(CONFIG_SCHEMA)

    for error in sorted(validator.iter_errors(data), key=lambda exc: exc.path):
        error_path = _format_jsonschema_path(error.absolute_path)
        report.errors.append(
            ValidationIssue(
                severity="error",
                path=error_path,
                message=error.message,
                code="schema",
                line_number=line_map.get(error_path) if line_map else None,
            )
        )

    _validate_semantics(data, report, line_map)
    return report


def _validate_semantics(
    data: Dict[str, Any],
    report: ValidationReport,
    line_map: Optional[Dict[str, int]] = None,
) -> None:
    settings = data.get("settings") or {}
    notifications = settings.get("notifications") or {}
    flush_time = notifications.get("flush_time")
    if isinstance(flush_time, str):
        problem = _parse_time(flush_time)
        if problem:
            issue_path = "settings.notifications.flush_time"
            report.errors.append(
                ValidationIssue(
                    severity="error",
                    path=issue_path,
                    message=f"Invalid time '{flush_time}': {problem}",
                    code="flush-time",
                    line_number=line_map.get(issue_path) if line_map else None,
                )
            )

    sports = data.get("sports") or []
    seen_ids: Dict[str, int] = {}
    for index, sport in enumerate(sports):
        if not isinstance(sport, dict):
            continue
        sport_id = sport.get("id")
        if isinstance(sport_id, str):
            if sport_id in seen_ids:
                issue_path = f"sports[{index}].id"
                report.errors.append(
                    ValidationIssue(
                        severity="error",
                        path=issue_path,
                        message=f"Duplicate sport id '{sport_id}' also defined at index {seen_ids[sport_id]}",
                        code="duplicate-id",
                        line_number=line_map.get(issue_path) if line_map else None,
                    )
                )
            else:
                seen_ids[sport_id] = index
        metadata = sport.get("metadata")
        variants = sport.get("variants") or []

        if isinstance(metadata, dict):
            _validate_metadata_block(metadata, f"sports[{index}].metadata", report, line_map)
        elif metadata is None and not variants:
            issue_path = f"sports[{index}].metadata"
            report.errors.append(
                ValidationIssue(
                    severity="error",
                    path=issue_path,
                    message="Sport must define metadata or variants with metadata",
                    code="metadata-missing",
                    line_number=line_map.get(issue_path) if line_map else None,
                )
            )
        elif metadata is not None and not isinstance(metadata, dict):
            issue_path = f"sports[{index}].metadata"
            report.errors.append(
                ValidationIssue(
                    severity="error",
                    path=issue_path,
                    message="Metadata must be a mapping when provided",
                    code="metadata-structure",
                    line_number=line_map.get(issue_path) if line_map else None,
                )
            )

        if variants:
            for variant_index, variant in enumerate(variants):
                if not isinstance(variant, dict):
                    issue_path = f"sports[{index}].variants[{variant_index}]"
                    report.errors.append(
                        ValidationIssue(
                            severity="error",
                            path=issue_path,
                            message="Variant entries must be mappings",
                            code="variant-structure",
                            line_number=line_map.get(issue_path) if line_map else None,
                        )
                    )
                    continue
                variant_metadata = variant.get("metadata")
                if not isinstance(variant_metadata, dict):
                    issue_path = f"sports[{index}].variants[{variant_index}].metadata"
                    report.errors.append(
                        ValidationIssue(
                            severity="error",
                            path=issue_path,
                            message="Variant must provide a metadata block",
                            code="metadata-missing",
                            line_number=line_map.get(issue_path) if line_map else None,
                        )
                    )
                    continue
                _validate_metadata_block(
                    variant_metadata,
                    f"sports[{index}].variants[{variant_index}].metadata",
                    report,
                    line_map,
                )

    known_sets = _collect_pattern_set_names(data)
    for index, sport in enumerate(sports):
        if not isinstance(sport, dict):
            continue
        requested_sets = sport.get("pattern_sets") or []
        for name in requested_sets:
            if name not in known_sets:
                issue_path = f"sports[{index}].pattern_sets"
                report.errors.append(
                    ValidationIssue(
                        severity="error",
                        path=issue_path,
                        message=f"Unknown pattern set '{name}'",
                        code="pattern-set",
                        line_number=line_map.get(issue_path) if line_map else None,
                    )
                )


__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "validate_config_data",
    "CONFIG_SCHEMA",
    "extract_yaml_line_numbers",
    "extract_yaml_line_numbers_from_file",
]

