from __future__ import annotations

import pytest

from playbook.validation import (
    CONFIG_SCHEMA,
    ValidationIssue,
    ValidationReport,
    _format_jsonschema_path,
    _parse_time,
    validate_config_data,
)


# Fixtures


@pytest.fixture
def minimal_valid_config():
    """Minimal valid configuration with only required fields."""
    return {
        "sports": []
    }


@pytest.fixture
def valid_config_with_sport():
    """Valid configuration with a single sport entry."""
    return {
        "sports": [
            {
                "id": "test-sport",
                "metadata": {
                    "url": "https://example.com/test.yaml",
                }
            }
        ]
    }


@pytest.fixture
def valid_config_with_settings():
    """Valid configuration with settings block."""
    return {
        "settings": {
            "source_dir": "/path/to/source",
            "destination_dir": "/path/to/destination",
            "link_mode": "hardlink",
            "notifications": {
                "batch_daily": True,
                "flush_time": "14:30",
            },
            "file_watcher": {
                "enabled": True,
                "paths": ["/watch/path"],
                "debounce_seconds": 5,
            },
            "kometa_trigger": {
                "enabled": False,
                "mode": "docker",
            }
        },
        "sports": [
            {
                "id": "test-sport",
                "metadata": {
                    "url": "https://example.com/test.yaml",
                }
            }
        ]
    }


# Tests for dataclass structures


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_validation_issue_creation(self):
        """Test creating a ValidationIssue with all fields."""
        issue = ValidationIssue(
            severity="error",
            path="sports[0].id",
            message="Invalid sport ID",
            code="invalid-id"
        )
        assert issue.severity == "error"
        assert issue.path == "sports[0].id"
        assert issue.message == "Invalid sport ID"
        assert issue.code == "invalid-id"

    def test_validation_issue_with_different_severity(self):
        """Test ValidationIssue with warning severity."""
        issue = ValidationIssue(
            severity="warning",
            path="settings.link_mode",
            message="Consider using hardlink",
            code="link-mode-suggestion"
        )
        assert issue.severity == "warning"
        assert issue.path == "settings.link_mode"
        assert issue.message == "Consider using hardlink"
        assert issue.code == "link-mode-suggestion"

    def test_validation_issue_with_root_path(self):
        """Test ValidationIssue with root-level path."""
        issue = ValidationIssue(
            severity="error",
            path="<root>",
            message="Missing required field",
            code="required"
        )
        assert issue.path == "<root>"

    def test_validation_issue_with_nested_path(self):
        """Test ValidationIssue with deeply nested path."""
        issue = ValidationIssue(
            severity="error",
            path="sports[0].variants[1].metadata.url",
            message="URL is blank",
            code="metadata-url"
        )
        assert issue.path == "sports[0].variants[1].metadata.url"


class TestValidationReport:
    """Tests for ValidationReport dataclass."""

    def test_validation_report_creation_empty(self):
        """Test creating an empty ValidationReport."""
        report = ValidationReport()
        assert report.errors == []
        assert report.warnings == []
        assert report.is_valid is True

    def test_validation_report_is_valid_with_no_errors(self):
        """Test is_valid returns True when there are no errors."""
        report = ValidationReport()
        assert report.is_valid is True

    def test_validation_report_is_valid_with_only_warnings(self):
        """Test is_valid returns True when there are only warnings."""
        report = ValidationReport()
        report.warnings.append(
            ValidationIssue(
                severity="warning",
                path="settings",
                message="Consider adding notifications",
                code="suggestion"
            )
        )
        assert len(report.warnings) == 1
        assert len(report.errors) == 0
        assert report.is_valid is True

    def test_validation_report_is_valid_with_errors(self):
        """Test is_valid returns False when there are errors."""
        report = ValidationReport()
        report.errors.append(
            ValidationIssue(
                severity="error",
                path="sports",
                message="Sports field is required",
                code="required"
            )
        )
        assert len(report.errors) == 1
        assert report.is_valid is False

    def test_validation_report_is_valid_with_errors_and_warnings(self):
        """Test is_valid returns False when there are both errors and warnings."""
        report = ValidationReport()
        report.errors.append(
            ValidationIssue(
                severity="error",
                path="sports",
                message="Sports field is required",
                code="required"
            )
        )
        report.warnings.append(
            ValidationIssue(
                severity="warning",
                path="settings",
                message="Consider adding notifications",
                code="suggestion"
            )
        )
        assert len(report.errors) == 1
        assert len(report.warnings) == 1
        assert report.is_valid is False

    def test_validation_report_multiple_errors(self):
        """Test ValidationReport with multiple errors."""
        report = ValidationReport()
        report.errors.append(
            ValidationIssue(
                severity="error",
                path="sports",
                message="Sports field is required",
                code="required"
            )
        )
        report.errors.append(
            ValidationIssue(
                severity="error",
                path="settings.link_mode",
                message="Invalid link mode",
                code="enum"
            )
        )
        assert len(report.errors) == 2
        assert report.is_valid is False

    def test_validation_report_multiple_warnings(self):
        """Test ValidationReport with multiple warnings."""
        report = ValidationReport()
        report.warnings.append(
            ValidationIssue(
                severity="warning",
                path="settings",
                message="Consider adding notifications",
                code="suggestion"
            )
        )
        report.warnings.append(
            ValidationIssue(
                severity="warning",
                path="sports[0]",
                message="Consider adding team_alias_map",
                code="suggestion"
            )
        )
        assert len(report.warnings) == 2
        assert len(report.errors) == 0
        assert report.is_valid is True

    def test_validation_report_errors_list_is_separate(self):
        """Test that errors and warnings are stored in separate lists."""
        report = ValidationReport()
        error = ValidationIssue(
            severity="error",
            path="sports",
            message="Sports field is required",
            code="required"
        )
        warning = ValidationIssue(
            severity="warning",
            path="settings",
            message="Consider adding notifications",
            code="suggestion"
        )
        report.errors.append(error)
        report.warnings.append(warning)

        assert error in report.errors
        assert error not in report.warnings
        assert warning in report.warnings
        assert warning not in report.errors

    def test_validation_report_with_default_factory(self):
        """Test that ValidationReport uses default_factory for lists."""
        report1 = ValidationReport()
        report2 = ValidationReport()

        report1.errors.append(
            ValidationIssue(
                severity="error",
                path="test",
                message="test",
                code="test"
            )
        )

        # Verify that report2's errors list is independent
        assert len(report1.errors) == 1
        assert len(report2.errors) == 0


# Tests for helper functions


class TestFormatJsonschemaPath:
    """Tests for _format_jsonschema_path helper function."""

    def test_empty_path_returns_root(self):
        """Test that an empty path returns '<root>'."""
        result = _format_jsonschema_path([])
        assert result == "<root>"

    def test_single_string_element(self):
        """Test path with a single string element."""
        result = _format_jsonschema_path(["sports"])
        assert result == "sports"

    def test_multiple_string_elements(self):
        """Test path with multiple string elements."""
        result = _format_jsonschema_path(["settings", "notifications", "flush_time"])
        assert result == "settings.notifications.flush_time"

    def test_single_integer_element(self):
        """Test path with a single integer element (array index)."""
        result = _format_jsonschema_path([0])
        assert result == "[0]"

    def test_string_then_integer(self):
        """Test path with string followed by integer (array access)."""
        result = _format_jsonschema_path(["sports", 0])
        assert result == "sports[0]"

    def test_multiple_array_indices(self):
        """Test path with multiple consecutive array indices."""
        result = _format_jsonschema_path(["sports", 0, 1])
        assert result == "sports[0][1]"

    def test_mixed_path_elements(self):
        """Test path with mixed string and integer elements."""
        result = _format_jsonschema_path(["sports", 0, "variants", 1, "metadata"])
        assert result == "sports[0].variants[1].metadata"

    def test_deeply_nested_path(self):
        """Test path with deeply nested elements."""
        result = _format_jsonschema_path(
            ["settings", "destination", "root_template", "params", 0, "name"]
        )
        assert result == "settings.destination.root_template.params[0].name"

    def test_string_with_special_characters(self):
        """Test path with string elements containing underscores and dashes."""
        result = _format_jsonschema_path(["file_watcher", "debounce_seconds"])
        assert result == "file_watcher.debounce_seconds"

    def test_array_notation_formatting(self):
        """Test that array indices are formatted with brackets."""
        result = _format_jsonschema_path(["sports", 5, "id"])
        assert result == "sports[5].id"

    def test_consecutive_strings_and_integers(self):
        """Test path alternating between strings and integers."""
        result = _format_jsonschema_path(["a", 0, "b", 1, "c", 2])
        assert result == "a[0].b[1].c[2]"

    def test_three_consecutive_array_indices(self):
        """Test path with three consecutive array indices."""
        result = _format_jsonschema_path(["matrix", 0, 1, 2])
        assert result == "matrix[0][1][2]"

    def test_empty_tuple_path(self):
        """Test that an empty tuple returns '<root>'."""
        result = _format_jsonschema_path(())
        assert result == "<root>"


# Tests for time parsing function


class TestParseTime:
    """Tests for _parse_time helper function."""

    def test_valid_hh_mm_format(self):
        """Test valid time in HH:MM format."""
        result = _parse_time("14:30")
        assert result is None

    def test_valid_hh_mm_with_leading_zeros(self):
        """Test valid time with leading zeros."""
        result = _parse_time("08:05")
        assert result is None

    def test_valid_hh_mm_midnight(self):
        """Test midnight time."""
        result = _parse_time("00:00")
        assert result is None

    def test_valid_hh_mm_end_of_day(self):
        """Test end of day time."""
        result = _parse_time("23:59")
        assert result is None

    def test_valid_hh_mm_ss_format(self):
        """Test valid time in HH:MM:SS format."""
        result = _parse_time("14:30:45")
        assert result is None

    def test_valid_hh_mm_ss_with_zeros(self):
        """Test valid time with seconds as zero."""
        result = _parse_time("12:30:00")
        assert result is None

    def test_valid_hh_mm_ss_end_of_minute(self):
        """Test valid time with 59 seconds."""
        result = _parse_time("23:59:59")
        assert result is None

    def test_invalid_hour_too_high(self):
        """Test invalid hour value greater than 23."""
        result = _parse_time("24:00")
        assert result is not None
        assert "hour must be in 0..23" in result

    def test_invalid_hour_negative(self):
        """Test invalid negative hour value."""
        result = _parse_time("-1:00")
        assert result is not None
        assert "hour must be in 0..23" in result

    def test_invalid_hour_too_high_with_seconds(self):
        """Test invalid hour with HH:MM:SS format."""
        result = _parse_time("25:30:45")
        assert result is not None
        assert "hour must be in 0..23" in result

    def test_invalid_minute_too_high(self):
        """Test invalid minute value greater than 59."""
        result = _parse_time("12:60")
        assert result is not None
        assert "minute must be in 0..59" in result

    def test_invalid_minute_negative(self):
        """Test invalid negative minute value."""
        result = _parse_time("12:-1")
        assert result is not None
        assert "minute must be in 0..59" in result

    def test_invalid_second_too_high(self):
        """Test invalid second value greater than 59."""
        result = _parse_time("12:30:60")
        assert result is not None
        assert "second must be in 0..59" in result

    def test_invalid_second_negative(self):
        """Test invalid negative second value."""
        result = _parse_time("12:30:-1")
        assert result is not None
        assert "second must be in 0..59" in result

    def test_non_integer_hour(self):
        """Test time with non-integer hour component."""
        result = _parse_time("12.5:30")
        assert result == "components must be integers"

    def test_non_integer_minute(self):
        """Test time with non-integer minute component."""
        result = _parse_time("12:30.5")
        assert result == "components must be integers"

    def test_non_integer_second(self):
        """Test time with non-integer second component."""
        result = _parse_time("12:30:45.5")
        assert result == "components must be integers"

    def test_non_integer_all_components(self):
        """Test time with all non-integer components."""
        result = _parse_time("abc:def")
        assert result == "components must be integers"

    def test_invalid_format_single_part(self):
        """Test time with only one component."""
        result = _parse_time("14")
        assert result == "expected HH:MM or HH:MM:SS"

    def test_invalid_format_four_parts(self):
        """Test time with four components."""
        result = _parse_time("14:30:45:00")
        assert result == "expected HH:MM or HH:MM:SS"

    def test_invalid_format_empty_string(self):
        """Test empty string."""
        result = _parse_time("")
        assert result == "expected HH:MM or HH:MM:SS"

    def test_invalid_format_no_colons(self):
        """Test time string without colons."""
        result = _parse_time("1430")
        assert result == "expected HH:MM or HH:MM:SS"

    def test_invalid_format_too_many_parts(self):
        """Test time with more than three parts."""
        result = _parse_time("12:30:45:12:00")
        assert result == "expected HH:MM or HH:MM:SS"

    def test_edge_case_single_digit_components(self):
        """Test that single-digit components are not automatically padded."""
        result = _parse_time("9:5")
        assert result is None

    def test_edge_case_all_zeros_with_seconds(self):
        """Test all zeros with seconds."""
        result = _parse_time("00:00:00")
        assert result is None


# Tests for CONFIG_SCHEMA validation


class TestConfigSchemaSettings:
    """Tests for CONFIG_SCHEMA validation of settings block."""

    def test_valid_settings_structure_passes(self, valid_config_with_settings):
        """Test that a valid settings structure passes validation."""
        report = validate_config_data(valid_config_with_settings)
        assert report.is_valid is True
        assert len(report.errors) == 0

    def test_settings_with_all_optional_fields(self):
        """Test settings with all optional fields populated."""
        config = {
            "sports": [],
            "settings": {
                "source_dir": "/source",
                "destination_dir": "/destination",
                "cache_dir": "/cache",
                "dry_run": True,
                "skip_existing": False,
                "link_mode": "hardlink",
                "destination": {
                    "root_template": "{sport_id}",
                    "season_dir_template": "Season {season}",
                    "episode_template": "{title}.{ext}",
                },
                "notifications": {
                    "batch_daily": True,
                    "flush_time": "14:30",
                },
                "file_watcher": {
                    "enabled": True,
                    "paths": ["/watch/path1", "/watch/path2"],
                    "include": ["*.mkv", "*.mp4"],
                    "ignore": ["*.tmp"],
                    "debounce_seconds": 5,
                    "reconcile_interval": 300,
                },
                "kometa_trigger": {
                    "enabled": False,
                    "mode": "docker",
                    "namespace": "default",
                    "cronjob_name": "kometa",
                    "job_name_prefix": "kometa-job",
                    "docker": {
                        "binary": "docker",
                        "image": "kometateam/kometa:latest",
                        "config_path": "/config/config.yml",
                        "container_path": "/config",
                        "volume_mode": "rw",
                        "libraries": "Movies,TV Shows",
                        "container_name": "kometa",
                        "exec_python": "python3",
                        "exec_script": "kometa.py",
                        "exec_command": ["--run"],
                        "extra_args": ["--trace"],
                        "env": {"TZ": "UTC"},
                        "remove_container": True,
                        "interactive": False,
                    },
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_invalid_link_mode_value(self):
        """Test that invalid link_mode value fails validation."""
        config = {
            "sports": [],
            "settings": {
                "link_mode": "invalid_mode",
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        assert len(report.errors) >= 1
        # Find the error related to link_mode
        link_mode_errors = [e for e in report.errors if "link_mode" in e.path]
        assert len(link_mode_errors) >= 1

    def test_valid_link_mode_hardlink(self):
        """Test that 'hardlink' is a valid link_mode."""
        config = {
            "sports": [],
            "settings": {"link_mode": "hardlink"},
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_valid_link_mode_copy(self):
        """Test that 'copy' is a valid link_mode."""
        config = {
            "sports": [],
            "settings": {"link_mode": "copy"},
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_valid_link_mode_symlink(self):
        """Test that 'symlink' is a valid link_mode."""
        config = {
            "sports": [],
            "settings": {"link_mode": "symlink"},
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_file_watcher_wrong_type(self):
        """Test that file_watcher must be an object."""
        config = {
            "sports": [],
            "settings": {
                "file_watcher": "not an object",
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        assert len(report.errors) >= 1
        # Find the error related to file_watcher
        watcher_errors = [e for e in report.errors if "file_watcher" in e.path]
        assert len(watcher_errors) >= 1

    def test_file_watcher_enabled_boolean(self):
        """Test that file_watcher.enabled accepts boolean."""
        config = {
            "sports": [],
            "settings": {
                "file_watcher": {
                    "enabled": True,
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_file_watcher_paths_as_array(self):
        """Test that file_watcher.paths accepts array of strings."""
        config = {
            "sports": [],
            "settings": {
                "file_watcher": {
                    "paths": ["/path1", "/path2", "/path3"],
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_file_watcher_paths_as_string(self):
        """Test that file_watcher.paths accepts a single string."""
        config = {
            "sports": [],
            "settings": {
                "file_watcher": {
                    "paths": "/single/path",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_file_watcher_include_as_array(self):
        """Test that file_watcher.include accepts array of strings."""
        config = {
            "sports": [],
            "settings": {
                "file_watcher": {
                    "include": ["*.mkv", "*.mp4"],
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_file_watcher_include_as_string(self):
        """Test that file_watcher.include accepts a single string."""
        config = {
            "sports": [],
            "settings": {
                "file_watcher": {
                    "include": "*.mkv",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_file_watcher_ignore_as_array(self):
        """Test that file_watcher.ignore accepts array of strings."""
        config = {
            "sports": [],
            "settings": {
                "file_watcher": {
                    "ignore": ["*.tmp", "*.bak"],
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_file_watcher_debounce_seconds_integer(self):
        """Test that file_watcher.debounce_seconds accepts integer."""
        config = {
            "sports": [],
            "settings": {
                "file_watcher": {
                    "debounce_seconds": 10,
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_file_watcher_debounce_seconds_float(self):
        """Test that file_watcher.debounce_seconds accepts float."""
        config = {
            "sports": [],
            "settings": {
                "file_watcher": {
                    "debounce_seconds": 2.5,
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_file_watcher_debounce_seconds_negative_invalid(self):
        """Test that negative debounce_seconds is invalid."""
        config = {
            "sports": [],
            "settings": {
                "file_watcher": {
                    "debounce_seconds": -1,
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is False

    def test_notifications_flush_time_valid_format(self):
        """Test that notifications.flush_time accepts valid HH:MM format."""
        config = {
            "sports": [],
            "settings": {
                "notifications": {
                    "flush_time": "14:30",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_notifications_flush_time_with_seconds(self):
        """Test that notifications.flush_time accepts HH:MM:SS format."""
        config = {
            "sports": [],
            "settings": {
                "notifications": {
                    "flush_time": "14:30:45",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_notifications_flush_time_invalid_format(self):
        """Test that invalid flush_time format fails validation."""
        config = {
            "sports": [],
            "settings": {
                "notifications": {
                    "flush_time": "invalid",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find the error related to flush_time
        flush_errors = [e for e in report.errors if "flush_time" in e.path]
        assert len(flush_errors) >= 1

    def test_notifications_flush_time_invalid_hour(self):
        """Test that flush_time with invalid hour fails validation."""
        config = {
            "sports": [],
            "settings": {
                "notifications": {
                    "flush_time": "25:00",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        flush_errors = [e for e in report.errors if "flush_time" in e.path]
        assert len(flush_errors) >= 1

    def test_notifications_batch_daily_boolean(self):
        """Test that notifications.batch_daily accepts boolean."""
        config = {
            "sports": [],
            "settings": {
                "notifications": {
                    "batch_daily": True,
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_kometa_trigger_structure_valid(self):
        """Test that valid kometa_trigger structure passes."""
        config = {
            "sports": [],
            "settings": {
                "kometa_trigger": {
                    "enabled": True,
                    "mode": "docker",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_kometa_trigger_mode_docker_valid(self):
        """Test that 'docker' is a valid kometa_trigger mode."""
        config = {
            "sports": [],
            "settings": {
                "kometa_trigger": {
                    "mode": "docker",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_kometa_trigger_mode_kubernetes_valid(self):
        """Test that 'kubernetes' is a valid kometa_trigger mode."""
        config = {
            "sports": [],
            "settings": {
                "kometa_trigger": {
                    "mode": "kubernetes",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_kometa_trigger_mode_invalid(self):
        """Test that invalid kometa_trigger mode fails validation."""
        config = {
            "sports": [],
            "settings": {
                "kometa_trigger": {
                    "mode": "invalid_mode",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find the error related to kometa_trigger
        kometa_errors = [e for e in report.errors if "kometa_trigger" in e.path]
        assert len(kometa_errors) >= 1

    def test_kometa_trigger_docker_config(self):
        """Test that kometa_trigger.docker config structure is valid."""
        config = {
            "sports": [],
            "settings": {
                "kometa_trigger": {
                    "enabled": True,
                    "mode": "docker",
                    "docker": {
                        "binary": "docker",
                        "image": "kometateam/kometa:latest",
                        "config_path": "/config/config.yml",
                        "exec_command": ["--run"],
                        "env": {"TZ": "UTC", "PUID": "1000"},
                    },
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_kometa_trigger_docker_exec_command_as_string(self):
        """Test that exec_command accepts a single string."""
        config = {
            "sports": [],
            "settings": {
                "kometa_trigger": {
                    "docker": {
                        "exec_command": "--run",
                    },
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_kometa_trigger_docker_exec_command_as_array(self):
        """Test that exec_command accepts an array of strings."""
        config = {
            "sports": [],
            "settings": {
                "kometa_trigger": {
                    "docker": {
                        "exec_command": ["--run", "--trace"],
                    },
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_source_dir_string_type(self):
        """Test that source_dir accepts string type."""
        config = {
            "sports": [],
            "settings": {
                "source_dir": "/path/to/source",
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_destination_dir_string_type(self):
        """Test that destination_dir accepts string type."""
        config = {
            "sports": [],
            "settings": {
                "destination_dir": "/path/to/destination",
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_cache_dir_string_type(self):
        """Test that cache_dir accepts string type."""
        config = {
            "sports": [],
            "settings": {
                "cache_dir": "/path/to/cache",
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_dry_run_boolean_type(self):
        """Test that dry_run accepts boolean type."""
        config = {
            "sports": [],
            "settings": {
                "dry_run": True,
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_skip_existing_boolean_type(self):
        """Test that skip_existing accepts boolean type."""
        config = {
            "sports": [],
            "settings": {
                "skip_existing": False,
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_destination_templates(self):
        """Test that destination templates are valid."""
        config = {
            "sports": [],
            "settings": {
                "destination": {
                    "root_template": "{sport_id}",
                    "season_dir_template": "Season {season}",
                    "episode_template": "{title}.{ext}",
                },
            },
        }
        report = validate_config_data(config)
        assert report.is_valid is True
