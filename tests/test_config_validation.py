from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from playbook.utils import load_yaml_file
from playbook.validation import (
    FIX_SUGGESTION_REGISTRY,
    ValidationIssue,
    extract_yaml_line_numbers,
    extract_yaml_line_numbers_from_file,
    get_fix_suggestion,
    validate_config_data,
)


def test_sample_configuration_passes_validation() -> None:
    project_root = Path(__file__).resolve().parents[1]
    sample_path = project_root / "config" / "playbook.sample.yaml"
    if not sample_path.exists():
        pytest.skip("Sample configuration not present in repository checkout")
    data = load_yaml_file(sample_path)
    report = validate_config_data(data)
    assert report.errors == []


def test_validation_flags_invalid_flush_time_and_metadata_url() -> None:
    config = {
        "settings": {
            "notifications": {
                "flush_time": "25:61",
            }
        },
        "sports": [
            {
                "id": "test",
                "metadata": {
                    "url": "",
                },
            }
        ],
    }

    report = validate_config_data(config)
    codes = {issue.code for issue in report.errors}
    assert "flush-time" in codes
    assert "metadata-url" in codes


def test_validation_rejects_invalid_watcher_block() -> None:
    config = {
        "settings": {
            "file_watcher": {
                "debounce_seconds": -1,
                "reconcile_interval": -5,
                "paths": 123,
            }
        },
        "sports": [
            {"id": "demo", "metadata": {"url": "https://example.com/demo.yaml"}},
        ],
    }

    report = validate_config_data(config)
    assert any(issue.path == "settings.file_watcher.paths" for issue in report.errors)


# ============================================================================
# YAML Line Number Extraction Tests
# ============================================================================


def test_extract_yaml_line_numbers_simple_nested_objects() -> None:
    """Test line number extraction for simple nested object structures."""
    yaml_content = textwrap.dedent("""
        settings:
          source_dir: /path/to/source
          destination_dir: /path/to/dest
          cache_dir: /path/to/cache
          dry_run: true
    """).strip()

    line_map = extract_yaml_line_numbers(yaml_content)

    assert line_map.get("settings") == 1
    assert line_map.get("settings.source_dir") == 2
    assert line_map.get("settings.destination_dir") == 3
    assert line_map.get("settings.cache_dir") == 4
    assert line_map.get("settings.dry_run") == 5


def test_extract_yaml_line_numbers_deeply_nested_objects() -> None:
    """Test line number extraction for deeply nested structures."""
    yaml_content = textwrap.dedent("""
        settings:
          notifications:
            batch_daily: true
            flush_time: "23:00"
          file_watcher:
            enabled: true
            debounce_seconds: 5
    """).strip()

    line_map = extract_yaml_line_numbers(yaml_content)

    assert line_map.get("settings") == 1
    assert line_map.get("settings.notifications") == 2
    assert line_map.get("settings.notifications.batch_daily") == 3
    assert line_map.get("settings.notifications.flush_time") == 4
    assert line_map.get("settings.file_watcher") == 5
    assert line_map.get("settings.file_watcher.enabled") == 6
    assert line_map.get("settings.file_watcher.debounce_seconds") == 7


def test_extract_yaml_line_numbers_array_elements() -> None:
    """Test line number extraction for array elements."""
    yaml_content = textwrap.dedent("""
        sports:
          - id: formula1
            name: Formula 1
          - id: nba
            name: NBA
          - id: nfl
            name: NFL
    """).strip()

    line_map = extract_yaml_line_numbers(yaml_content)

    assert line_map.get("sports") == 1
    assert line_map.get("sports[0]") == 2
    assert line_map.get("sports[0].id") == 2
    assert line_map.get("sports[0].name") == 3
    assert line_map.get("sports[1]") == 4
    assert line_map.get("sports[1].id") == 4
    assert line_map.get("sports[1].name") == 5
    assert line_map.get("sports[2]") == 6
    assert line_map.get("sports[2].id") == 6
    assert line_map.get("sports[2].name") == 7


def test_extract_yaml_line_numbers_nested_arrays() -> None:
    """Test line number extraction for nested arrays (variants within sports)."""
    yaml_content = textwrap.dedent("""
        sports:
          - id: formula1
            name: Formula 1
            variants:
              - year: 2024
                name: F1 2024
              - year: 2023
                name: F1 2023
    """).strip()

    line_map = extract_yaml_line_numbers(yaml_content)

    assert line_map.get("sports") == 1
    assert line_map.get("sports[0]") == 2
    assert line_map.get("sports[0].id") == 2
    assert line_map.get("sports[0].name") == 3
    assert line_map.get("sports[0].variants") == 4
    assert line_map.get("sports[0].variants[0]") == 5
    assert line_map.get("sports[0].variants[0].year") == 5
    assert line_map.get("sports[0].variants[0].name") == 6
    assert line_map.get("sports[0].variants[1]") == 7
    assert line_map.get("sports[0].variants[1].year") == 7
    assert line_map.get("sports[0].variants[1].name") == 8


def test_extract_yaml_line_numbers_complex_config() -> None:
    """Test line number extraction for a complex config with multiple sections."""
    yaml_content = textwrap.dedent("""
        settings:
          source_dir: /path/to/source
          destination_dir: /path/to/dest
          notifications:
            batch_daily: false
            flush_time: "22:30"

        pattern_sets:
          common:
            - regex: "pattern1"
              priority: 10
            - regex: "pattern2"
              priority: 20

        sports:
          - id: formula1
            name: Formula 1
            metadata:
              url: https://example.com/f1.yaml
              ttl_hours: 24
    """).strip()

    line_map = extract_yaml_line_numbers(yaml_content)

    # Settings section
    assert line_map.get("settings") == 1
    assert line_map.get("settings.source_dir") == 2
    assert line_map.get("settings.destination_dir") == 3
    assert line_map.get("settings.notifications") == 4
    assert line_map.get("settings.notifications.batch_daily") == 5
    assert line_map.get("settings.notifications.flush_time") == 6

    # Pattern sets section
    assert line_map.get("pattern_sets") == 8
    assert line_map.get("pattern_sets.common") == 9
    assert line_map.get("pattern_sets.common[0]") == 10
    assert line_map.get("pattern_sets.common[1]") == 12

    # Sports section
    assert line_map.get("sports") == 15
    assert line_map.get("sports[0]") == 16
    assert line_map.get("sports[0].id") == 16
    assert line_map.get("sports[0].name") == 17
    assert line_map.get("sports[0].metadata") == 18
    assert line_map.get("sports[0].metadata.url") == 19
    assert line_map.get("sports[0].metadata.ttl_hours") == 20


def test_extract_yaml_line_numbers_with_comments() -> None:
    """Test that comments are properly skipped during line number extraction."""
    yaml_content = textwrap.dedent("""
        # This is a comment
        settings:
          # Another comment
          source_dir: /path
          # Inline comments should not affect line numbers
          destination_dir: /dest
    """).strip()

    line_map = extract_yaml_line_numbers(yaml_content)

    assert line_map.get("settings") == 2
    assert line_map.get("settings.source_dir") == 4
    assert line_map.get("settings.destination_dir") == 6


def test_extract_yaml_line_numbers_with_empty_lines() -> None:
    """Test that empty lines are properly handled."""
    yaml_content = textwrap.dedent("""
        settings:
          source_dir: /path

          destination_dir: /dest

        sports:
          - id: test
    """).strip()

    line_map = extract_yaml_line_numbers(yaml_content)

    assert line_map.get("settings") == 1
    assert line_map.get("settings.source_dir") == 2
    assert line_map.get("settings.destination_dir") == 4
    assert line_map.get("sports") == 6
    assert line_map.get("sports[0]") == 7


def test_extract_yaml_line_numbers_empty_content() -> None:
    """Test that empty YAML content returns an empty mapping."""
    line_map = extract_yaml_line_numbers("")
    assert line_map == {}

    line_map = extract_yaml_line_numbers("   \n\n   \n")
    assert line_map == {}


def test_extract_yaml_line_numbers_from_file(tmp_path) -> None:
    """Test extracting line numbers from a file."""
    yaml_file = tmp_path / "test.yaml"
    yaml_content = textwrap.dedent("""
        settings:
          source_dir: /path
        sports:
          - id: test
            name: Test Sport
    """).strip()
    yaml_file.write_text(yaml_content, encoding="utf-8")

    line_map = extract_yaml_line_numbers_from_file(yaml_file)

    assert line_map.get("settings") == 1
    assert line_map.get("settings.source_dir") == 2
    assert line_map.get("sports") == 3
    assert line_map.get("sports[0]") == 4
    assert line_map.get("sports[0].id") == 4
    assert line_map.get("sports[0].name") == 5


def test_extract_yaml_line_numbers_from_nonexistent_file(tmp_path) -> None:
    """Test that extracting from nonexistent file returns empty dict."""
    nonexistent_file = tmp_path / "does_not_exist.yaml"
    line_map = extract_yaml_line_numbers_from_file(nonexistent_file)
    assert line_map == {}


def test_extract_yaml_line_numbers_multiple_sports_with_variants() -> None:
    """Test line number extraction for multiple sports with multiple variants each."""
    yaml_content = textwrap.dedent("""
        sports:
          - id: formula1
            name: Formula 1
            variants:
              - year: 2024
              - year: 2023
          - id: nba
            name: NBA
            variants:
              - season: 2023-24
              - season: 2022-23
    """).strip()

    line_map = extract_yaml_line_numbers(yaml_content)

    # First sport
    assert line_map.get("sports[0]") == 2
    assert line_map.get("sports[0].variants[0]") == 5
    assert line_map.get("sports[0].variants[0].year") == 5
    assert line_map.get("sports[0].variants[1]") == 6
    assert line_map.get("sports[0].variants[1].year") == 6

    # Second sport
    assert line_map.get("sports[1]") == 7
    assert line_map.get("sports[1].variants[0]") == 10
    assert line_map.get("sports[1].variants[0].season") == 10
    assert line_map.get("sports[1].variants[1]") == 11
    assert line_map.get("sports[1].variants[1].season") == 11


def test_extract_yaml_line_numbers_inline_array_syntax() -> None:
    """Test line number extraction for arrays with inline values."""
    yaml_content = textwrap.dedent("""
        pattern_sets:
          common:
            - regex: "pattern1"
            - regex: "pattern2"
            - regex: "pattern3"
    """).strip()

    line_map = extract_yaml_line_numbers(yaml_content)

    assert line_map.get("pattern_sets") == 1
    assert line_map.get("pattern_sets.common") == 2
    assert line_map.get("pattern_sets.common[0]") == 3
    assert line_map.get("pattern_sets.common[0].regex") == 3
    assert line_map.get("pattern_sets.common[1]") == 4
    assert line_map.get("pattern_sets.common[1].regex") == 4
    assert line_map.get("pattern_sets.common[2]") == 5
    assert line_map.get("pattern_sets.common[2].regex") == 5


# ============================================================================
# Fix Suggestion Tests
# ============================================================================


def test_fix_suggestion_schema_required_property() -> None:
    """Test fix suggestion for schema validation error: missing required property."""
    issue = ValidationIssue(
        severity="error",
        path="sports[0]",
        message="'id' is a required property",
        code="schema",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "Add the required field" in suggestion


def test_fix_suggestion_schema_wrong_type_string() -> None:
    """Test fix suggestion for schema validation error: wrong type (string expected)."""
    issue = ValidationIssue(
        severity="error",
        path="settings.source_dir",
        message="123 is not of type 'string'",
        code="schema",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "string" in suggestion.lower()


def test_fix_suggestion_schema_wrong_type_object() -> None:
    """Test fix suggestion for schema validation error: wrong type (object expected)."""
    issue = ValidationIssue(
        severity="error",
        path="settings.notifications",
        message="'value' is not of type 'object'",
        code="schema",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "object" in suggestion.lower() or "mapping" in suggestion.lower()


def test_fix_suggestion_schema_wrong_type_array() -> None:
    """Test fix suggestion for schema validation error: wrong type (array expected)."""
    issue = ValidationIssue(
        severity="error",
        path="sports",
        message="'test' is not of type 'array'",
        code="schema",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "array" in suggestion.lower() or "list" in suggestion.lower()


def test_fix_suggestion_schema_wrong_type_boolean() -> None:
    """Test fix suggestion for schema validation error: wrong type (boolean expected)."""
    issue = ValidationIssue(
        severity="error",
        path="settings.dry_run",
        message="'yes' is not of type 'boolean'",
        code="schema",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "boolean" in suggestion.lower()


def test_fix_suggestion_schema_wrong_type_number() -> None:
    """Test fix suggestion for schema validation error: wrong type (number expected)."""
    issue = ValidationIssue(
        severity="error",
        path="settings.file_watcher.debounce_seconds",
        message="'five' is not of type 'integer'",
        code="schema",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "number" in suggestion.lower()


def test_fix_suggestion_schema_invalid_enum() -> None:
    """Test fix suggestion for schema validation error: invalid enum value."""
    issue = ValidationIssue(
        severity="error",
        path="settings.link_mode",
        message="'invalid' is not one of ['hardlink', 'copy', 'symlink']",
        code="schema",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "allowed values" in suggestion.lower() or "documentation" in suggestion.lower()


def test_fix_suggestion_schema_generic() -> None:
    """Test fix suggestion for generic schema validation error."""
    issue = ValidationIssue(
        severity="error",
        path="settings.unknown",
        message="Some other schema error",
        code="schema",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "schema" in suggestion.lower() or "requirements" in suggestion.lower()


def test_fix_suggestion_flush_time() -> None:
    """Test fix suggestion for flush_time validation error."""
    issue = ValidationIssue(
        severity="error",
        path="settings.notifications.flush_time",
        message="flush_time must be in HH:MM or HH:MM:SS format",
        code="flush-time",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "HH:MM" in suggestion
    assert "00-23" in suggestion or "hour" in suggestion.lower()
    assert "00-59" in suggestion or "minute" in suggestion.lower()


def test_fix_suggestion_metadata_url() -> None:
    """Test fix suggestion for blank metadata URL error."""
    issue = ValidationIssue(
        severity="error",
        path="sports[0].metadata.url",
        message="metadata.url must be a non-blank string",
        code="metadata-url",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "URL" in suggestion
    assert "non-empty" in suggestion.lower() or "valid" in suggestion.lower()


def test_fix_suggestion_metadata_missing_sport() -> None:
    """Test fix suggestion for missing metadata on sport (not variant)."""
    issue = ValidationIssue(
        severity="error",
        path="sports[0].metadata",
        message="Either metadata or variants must be provided",
        code="metadata-missing",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "metadata" in suggestion.lower()
    assert "variants" in suggestion.lower()


def test_fix_suggestion_metadata_missing_variant() -> None:
    """Test fix suggestion for missing metadata on variant."""
    issue = ValidationIssue(
        severity="error",
        path="sports[0].variants[0].metadata",
        message="Each variant must have metadata",
        code="metadata-missing",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "metadata" in suggestion.lower()
    assert "variant" in suggestion.lower()


def test_fix_suggestion_duplicate_id() -> None:
    """Test fix suggestion for duplicate sport ID error."""
    issue = ValidationIssue(
        severity="error",
        path="sports[2].id",
        message="Duplicate sport id 'formula1' at indices 0 and 2",
        code="duplicate-id",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "unique" in suggestion.lower()
    assert "id" in suggestion.lower()


def test_fix_suggestion_pattern_set_with_name() -> None:
    """Test fix suggestion for unknown pattern set error with specific name."""
    issue = ValidationIssue(
        severity="error",
        path="sports[0].pattern_sets[0]",
        message="Unknown pattern set 'my_custom_patterns' referenced",
        code="pattern-set",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "my_custom_patterns" in suggestion
    assert "define" in suggestion.lower() or "pattern_sets" in suggestion.lower()
    assert "typo" in suggestion.lower()


def test_fix_suggestion_pattern_set_generic() -> None:
    """Test fix suggestion for unknown pattern set error without specific name."""
    issue = ValidationIssue(
        severity="error",
        path="sports[0].pattern_sets[0]",
        message="Unknown pattern set referenced",
        code="pattern-set",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "pattern" in suggestion.lower()
    assert "define" in suggestion.lower() or "remove" in suggestion.lower()


def test_fix_suggestion_load_config_file_not_found() -> None:
    """Test fix suggestion for config file not found error."""
    issue = ValidationIssue(
        severity="error",
        path="",
        message="No such file or directory: config.yaml",
        code="load-config",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "file path" in suggestion.lower() or "file exists" in suggestion.lower()


def test_fix_suggestion_load_config_permission_denied() -> None:
    """Test fix suggestion for config file permission error."""
    issue = ValidationIssue(
        severity="error",
        path="",
        message="Permission denied: config.yaml",
        code="load-config",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "permission" in suggestion.lower()
    assert "access" in suggestion.lower() or "read" in suggestion.lower()


def test_fix_suggestion_load_config_yaml_syntax() -> None:
    """Test fix suggestion for config YAML syntax error."""
    issue = ValidationIssue(
        severity="error",
        path="",
        message="YAML syntax error: invalid indentation",
        code="load-config",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "YAML" in suggestion or "syntax" in suggestion.lower()
    assert "indentation" in suggestion.lower() or "colon" in suggestion.lower() or "quote" in suggestion.lower()


def test_fix_suggestion_load_config_generic() -> None:
    """Test fix suggestion for generic config load error."""
    issue = ValidationIssue(
        severity="error",
        path="",
        message="Unknown error loading configuration",
        code="load-config",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "syntax" in suggestion.lower() or "access" in suggestion.lower()


def test_fix_suggestion_metadata_structure() -> None:
    """Test fix suggestion for metadata structure error."""
    issue = ValidationIssue(
        severity="error",
        path="sports[0].metadata",
        message="Metadata must be a mapping when provided",
        code="metadata-structure",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "metadata" in suggestion.lower()
    assert "object" in suggestion.lower() or "mapping" in suggestion.lower()


def test_fix_suggestion_variant_structure() -> None:
    """Test fix suggestion for variant structure error."""
    issue = ValidationIssue(
        severity="error",
        path="sports[0].variants[0]",
        message="Each variant must be a dict/mapping",
        code="variant-structure",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is not None
    assert "variant" in suggestion.lower()
    assert "object" in suggestion.lower() or "mapping" in suggestion.lower()


def test_fix_suggestion_registry_completeness() -> None:
    """Test that all expected error codes have fix suggestion generators."""
    expected_codes = [
        "schema",
        "flush-time",
        "metadata-url",
        "metadata-missing",
        "duplicate-id",
        "pattern-set",
        "load-config",
        "metadata-structure",
        "variant-structure",
    ]

    for code in expected_codes:
        assert code in FIX_SUGGESTION_REGISTRY, f"Missing fix suggestion generator for error code: {code}"
        generator = FIX_SUGGESTION_REGISTRY[code]
        assert callable(generator), f"Fix suggestion generator for {code} is not callable"


def test_fix_suggestion_unknown_code() -> None:
    """Test that unknown error codes return None for fix suggestion."""
    issue = ValidationIssue(
        severity="error",
        path="some.path",
        message="Some error message",
        code="unknown-error-code",
    )

    suggestion = get_fix_suggestion(issue)

    assert suggestion is None


def test_fix_suggestions_integration_with_validation() -> None:
    """Test that fix suggestions are automatically generated during validation."""
    config = {
        "settings": {
            "notifications": {
                "flush_time": "25:99",  # Invalid flush_time
            }
        },
        "sports": [
            {
                "id": "test",
                "metadata": {
                    "url": "",  # Blank URL
                },
            }
        ],
    }

    report = validate_config_data(config)

    # Find the flush_time error
    flush_time_errors = [e for e in report.errors if e.code == "flush-time"]
    assert len(flush_time_errors) > 0
    assert flush_time_errors[0].fix_suggestion is not None
    assert "HH:MM" in flush_time_errors[0].fix_suggestion

    # Find the metadata-url error
    url_errors = [e for e in report.errors if e.code == "metadata-url"]
    assert len(url_errors) > 0
    assert url_errors[0].fix_suggestion is not None
    assert "URL" in url_errors[0].fix_suggestion

