from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

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


# Fix Suggestion System
# Type alias for fix suggestion functions that take a ValidationIssue and return a suggestion string
FixSuggestionGenerator = Callable[[str, str, str], Optional[str]]


def _suggest_schema_fix(path: str, message: str, code: str) -> Optional[str]:
    """Generate fix suggestion for schema validation errors."""
    # Try to extract useful information from the error message
    if "is a required property" in message:
        # Extract the missing property name from the message
        return "Add the required field to your configuration"
    if "is not of type" in message:
        expected_type = None
        if "'string'" in message:
            expected_type = "string"
        elif "'object'" in message:
            expected_type = "object/mapping"
        elif "'array'" in message:
            expected_type = "array/list"
        elif "'boolean'" in message:
            expected_type = "boolean"
        elif "'integer'" in message or "'number'" in message:
            expected_type = "number"
        if expected_type:
            return f"Change this field to a {expected_type} value"
    if "is not one of" in message or "is not valid under any of the given schemas" in message:
        return "Check the allowed values/formats for this field in the documentation"
    return "Review the configuration schema requirements for this field"


def _suggest_flush_time_fix(path: str, message: str, code: str) -> Optional[str]:
    """Generate fix suggestion for flush_time validation errors."""
    return "Use format HH:MM or HH:MM:SS with valid hour (00-23) and minute (00-59) values (e.g., '09:00' or '15:30:00')"


def _suggest_metadata_url_fix(path: str, message: str, code: str) -> Optional[str]:
    """Generate fix suggestion for blank metadata URL errors."""
    return "Provide a valid non-empty URL for the metadata source (e.g., 'https://example.com/api/schedule')"


def _suggest_metadata_missing_fix(path: str, message: str, code: str) -> Optional[str]:
    """Generate fix suggestion for missing metadata errors."""
    if "variants" in path:
        return "Add a 'metadata' block with a 'url' field to this variant entry"
    return "Either add a 'metadata' block with a 'url' field, or define 'variants' with metadata for this sport"


def _suggest_duplicate_id_fix(path: str, message: str, code: str) -> Optional[str]:
    """Generate fix suggestion for duplicate sport ID errors."""
    return "Change the sport 'id' to a unique value not used by other sports in your configuration"


def _suggest_pattern_set_fix(path: str, message: str, code: str) -> Optional[str]:
    """Generate fix suggestion for unknown pattern set errors."""
    # Try to extract the unknown pattern set name from the message
    match = re.search(r"Unknown pattern set '([^']+)'", message)
    if match:
        unknown_name = match.group(1)
        return f"Either define '{unknown_name}' in the pattern_sets section or remove it from this sport's pattern_sets list. Check for typos in the pattern set name."
    return "Either define the pattern set in the pattern_sets section or remove it from this sport's pattern_sets list"


def _suggest_load_config_fix(path: str, message: str, code: str) -> Optional[str]:
    """Generate fix suggestion for configuration file loading errors."""
    if "No such file" in message or "not found" in message.lower():
        return "Ensure the configuration file path is correct and the file exists"
    if "Permission denied" in message:
        return "Check file permissions and ensure the application has read access to the configuration file"
    if "YAML" in message or "parse" in message.lower():
        return "Fix YAML syntax errors. Common issues: incorrect indentation, missing colons, unquoted special characters"
    return "Check the configuration file for syntax errors or file access issues"


def _suggest_metadata_structure_fix(path: str, message: str, code: str) -> Optional[str]:
    """Generate fix suggestion for metadata structure errors."""
    return "The metadata field must be an object/mapping with fields like 'url', 'show_key', etc. Remove or restructure this field."


def _suggest_variant_structure_fix(path: str, message: str, code: str) -> Optional[str]:
    """Generate fix suggestion for variant structure errors."""
    return "Each variant entry must be an object/mapping with fields like 'id', 'name', 'metadata', etc."


# Registry mapping error codes to fix suggestion generators
FIX_SUGGESTION_REGISTRY: Dict[str, FixSuggestionGenerator] = {
    "schema": _suggest_schema_fix,
    "flush-time": _suggest_flush_time_fix,
    "metadata-url": _suggest_metadata_url_fix,
    "metadata-missing": _suggest_metadata_missing_fix,
    "duplicate-id": _suggest_duplicate_id_fix,
    "pattern-set": _suggest_pattern_set_fix,
    "load-config": _suggest_load_config_fix,
    "metadata-structure": _suggest_metadata_structure_fix,
    "variant-structure": _suggest_variant_structure_fix,
}


def get_fix_suggestion(issue: ValidationIssue) -> Optional[str]:
    """Get a fix suggestion for a validation issue.

    Args:
        issue: The ValidationIssue to generate a suggestion for

    Returns:
        A fix suggestion string, or None if no suggestion is available
    """
    generator = FIX_SUGGESTION_REGISTRY.get(issue.code)
    if generator:
        return generator(issue.path, issue.message, issue.code)
    return None


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
        error_code = "metadata-url"
        error_message = "Metadata URL must not be blank"
        fix_suggestion = None
        if error_code in FIX_SUGGESTION_REGISTRY:
            fix_suggestion = FIX_SUGGESTION_REGISTRY[error_code](issue_path, error_message, error_code)
        report.errors.append(
            ValidationIssue(
                severity="error",
                path=issue_path,
                message=error_message,
                code=error_code,
                line_number=line_map.get(issue_path) if line_map else None,
                fix_suggestion=fix_suggestion,
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
        error_code = "schema"
        error_message = error.message
        fix_suggestion = None
        if error_code in FIX_SUGGESTION_REGISTRY:
            fix_suggestion = FIX_SUGGESTION_REGISTRY[error_code](error_path, error_message, error_code)
        report.errors.append(
            ValidationIssue(
                severity="error",
                path=error_path,
                message=error_message,
                code=error_code,
                line_number=line_map.get(error_path) if line_map else None,
                fix_suggestion=fix_suggestion,
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
            error_code = "flush-time"
            error_message = f"Invalid time '{flush_time}': {problem}"
            fix_suggestion = None
            if error_code in FIX_SUGGESTION_REGISTRY:
                fix_suggestion = FIX_SUGGESTION_REGISTRY[error_code](issue_path, error_message, error_code)
            report.errors.append(
                ValidationIssue(
                    severity="error",
                    path=issue_path,
                    message=error_message,
                    code=error_code,
                    line_number=line_map.get(issue_path) if line_map else None,
                    fix_suggestion=fix_suggestion,
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
                error_code = "duplicate-id"
                error_message = f"Duplicate sport id '{sport_id}' also defined at index {seen_ids[sport_id]}"
                fix_suggestion = None
                if error_code in FIX_SUGGESTION_REGISTRY:
                    fix_suggestion = FIX_SUGGESTION_REGISTRY[error_code](issue_path, error_message, error_code)
                report.errors.append(
                    ValidationIssue(
                        severity="error",
                        path=issue_path,
                        message=error_message,
                        code=error_code,
                        line_number=line_map.get(issue_path) if line_map else None,
                        fix_suggestion=fix_suggestion,
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
            error_code = "metadata-missing"
            error_message = "Sport must define metadata or variants with metadata"
            fix_suggestion = None
            if error_code in FIX_SUGGESTION_REGISTRY:
                fix_suggestion = FIX_SUGGESTION_REGISTRY[error_code](issue_path, error_message, error_code)
            report.errors.append(
                ValidationIssue(
                    severity="error",
                    path=issue_path,
                    message=error_message,
                    code=error_code,
                    line_number=line_map.get(issue_path) if line_map else None,
                    fix_suggestion=fix_suggestion,
                )
            )
        elif metadata is not None and not isinstance(metadata, dict):
            issue_path = f"sports[{index}].metadata"
            error_code = "metadata-structure"
            error_message = "Metadata must be a mapping when provided"
            fix_suggestion = None
            if error_code in FIX_SUGGESTION_REGISTRY:
                fix_suggestion = FIX_SUGGESTION_REGISTRY[error_code](issue_path, error_message, error_code)
            report.errors.append(
                ValidationIssue(
                    severity="error",
                    path=issue_path,
                    message=error_message,
                    code=error_code,
                    line_number=line_map.get(issue_path) if line_map else None,
                    fix_suggestion=fix_suggestion,
                )
            )

        if variants:
            for variant_index, variant in enumerate(variants):
                if not isinstance(variant, dict):
                    issue_path = f"sports[{index}].variants[{variant_index}]"
                    error_code = "variant-structure"
                    error_message = "Variant entries must be mappings"
                    fix_suggestion = None
                    if error_code in FIX_SUGGESTION_REGISTRY:
                        fix_suggestion = FIX_SUGGESTION_REGISTRY[error_code](issue_path, error_message, error_code)
                    report.errors.append(
                        ValidationIssue(
                            severity="error",
                            path=issue_path,
                            message=error_message,
                            code=error_code,
                            line_number=line_map.get(issue_path) if line_map else None,
                            fix_suggestion=fix_suggestion,
                        )
                    )
                    continue
                variant_metadata = variant.get("metadata")
                if not isinstance(variant_metadata, dict):
                    issue_path = f"sports[{index}].variants[{variant_index}].metadata"
                    error_code = "metadata-missing"
                    error_message = "Variant must provide a metadata block"
                    fix_suggestion = None
                    if error_code in FIX_SUGGESTION_REGISTRY:
                        fix_suggestion = FIX_SUGGESTION_REGISTRY[error_code](issue_path, error_message, error_code)
                    report.errors.append(
                        ValidationIssue(
                            severity="error",
                            path=issue_path,
                            message=error_message,
                            code=error_code,
                            line_number=line_map.get(issue_path) if line_map else None,
                            fix_suggestion=fix_suggestion,
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
                error_code = "pattern-set"
                error_message = f"Unknown pattern set '{name}'"
                fix_suggestion = None
                if error_code in FIX_SUGGESTION_REGISTRY:
                    fix_suggestion = FIX_SUGGESTION_REGISTRY[error_code](issue_path, error_message, error_code)
                report.errors.append(
                    ValidationIssue(
                        severity="error",
                        path=issue_path,
                        message=error_message,
                        code=error_code,
                        line_number=line_map.get(issue_path) if line_map else None,
                        fix_suggestion=fix_suggestion,
                    )
                )


def group_validation_issues(
    issues: List[ValidationIssue],
) -> Dict[str, Dict[str, List[ValidationIssue]]]:
    """Group validation issues by their root section and sub-section.

    This function organizes validation issues hierarchically:
    - First level: Root section (settings, sports, pattern_sets, etc.)
    - Second level: Sub-section for arrays (e.g., sports[0], sports[1]) or subsection names

    Args:
        issues: List of ValidationIssue objects to group

    Returns:
        Nested dictionary structure:
        {
            "settings": {
                "notifications": [issue1, issue2],
                "file_watcher": [issue3]
            },
            "sports": {
                "sports[0]": [issue4, issue5],
                "sports[1]": [issue6]
            },
            "pattern_sets": {
                "pattern_sets": [issue7]
            }
        }

    Example:
        >>> issues = [
        ...     ValidationIssue("error", "settings.notifications.flush_time", "Invalid time", "flush-time"),
        ...     ValidationIssue("error", "sports[0].id", "Required field", "schema"),
        ...     ValidationIssue("error", "sports[1].metadata.url", "Blank URL", "metadata-url"),
        ... ]
        >>> grouped = group_validation_issues(issues)
        >>> "settings" in grouped
        True
        >>> "sports[0]" in grouped["sports"]
        True
    """
    grouped: Dict[str, Dict[str, List[ValidationIssue]]] = {}

    for issue in issues:
        path = issue.path

        # Extract root section (first part before . or [)
        root_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)', path)
        if not root_match:
            # Fallback for unusual paths
            root_section = "<root>"
        else:
            root_section = root_match.group(1)

        # Determine the sub-section key for grouping
        # For array paths like "sports[0].id", extract "sports[0]"
        # For nested arrays like "sports[0].variants[1]", extract "sports[0].variants[1]"
        # For non-array paths like "settings.notifications.flush_time", use the second level "notifications"

        if '[' in path:
            # Array path - extract up to the last array index before any property access
            # Examples:
            #   "sports[0].id" -> "sports[0]"
            #   "sports[0].metadata.url" -> "sports[0]"
            #   "sports[0].variants[1].metadata" -> "sports[0].variants[1]"

            # Extract the path up to and including the last array index
            # This regex matches the path from start up to the last closing bracket
            match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_.\[\]-]*\[[0-9]+\])', path)
            if match:
                sub_section = match.group(1)
            else:
                # Fallback if regex fails
                sub_section = root_section
        else:
            # Non-array path - use second-level key if available, otherwise root
            parts = path.split('.')
            if len(parts) >= 2:
                sub_section = parts[1]
            else:
                sub_section = root_section

        # Initialize nested structure if needed
        if root_section not in grouped:
            grouped[root_section] = {}

        if sub_section not in grouped[root_section]:
            grouped[root_section][sub_section] = []

        grouped[root_section][sub_section].append(issue)

    return grouped


__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "validate_config_data",
    "CONFIG_SCHEMA",
    "extract_yaml_line_numbers",
    "extract_yaml_line_numbers_from_file",
    "get_fix_suggestion",
    "FIX_SUGGESTION_REGISTRY",
    "group_validation_issues",
]

