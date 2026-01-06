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


class TestConfigSchemaSports:
    """Tests for CONFIG_SCHEMA validation of sports array and nested structures."""

    def test_sports_field_is_required(self):
        """Test that sports field is required in config."""
        config = {
            "settings": {
                "source_dir": "/source",
            }
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to sports field
        sports_errors = [e for e in report.errors if "sports" in e.path or "<root>" in e.path]
        assert len(sports_errors) >= 1

    def test_sports_must_be_array(self):
        """Test that sports field must be an array."""
        config = {
            "sports": "not an array"
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to sports type
        sports_errors = [e for e in report.errors if "sports" in e.path]
        assert len(sports_errors) >= 1

    def test_empty_sports_array_is_valid(self):
        """Test that an empty sports array is valid."""
        config = {
            "sports": []
        }
        report = validate_config_data(config)
        assert report.is_valid is True
        assert len(report.errors) == 0

    def test_sport_id_is_required(self):
        """Test that sport.id field is required."""
        config = {
            "sports": [
                {
                    "name": "Test Sport",
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to sport id
        id_errors = [e for e in report.errors if "id" in e.path or "sports[0]" in e.path]
        assert len(id_errors) >= 1

    def test_sport_id_must_be_string(self):
        """Test that sport.id must be a string."""
        config = {
            "sports": [
                {
                    "id": 123,
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to sport id type
        id_errors = [e for e in report.errors if "id" in e.path]
        assert len(id_errors) >= 1

    def test_sport_id_must_not_be_empty(self):
        """Test that sport.id must have minimum length of 1."""
        config = {
            "sports": [
                {
                    "id": "",
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to sport id length
        id_errors = [e for e in report.errors if "id" in e.path]
        assert len(id_errors) >= 1

    def test_sport_with_valid_id_and_metadata(self):
        """Test that a sport with valid id and metadata passes."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "metadata": {
                        "url": "https://example.com/test.yaml"
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_name_is_optional_string(self):
        """Test that sport.name is optional and accepts string."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "name": "Test Sport Name",
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_enabled_boolean(self):
        """Test that sport.enabled accepts boolean."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "enabled": True,
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_team_alias_map_string(self):
        """Test that sport.team_alias_map accepts string."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "team_alias_map": "nhl",
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_team_alias_map_null(self):
        """Test that sport.team_alias_map accepts null."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "team_alias_map": None,
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_metadata_url_is_required(self):
        """Test that metadata.url is required when metadata is present."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "metadata": {
                        "show_key": "test-show"
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to metadata.url
        url_errors = [e for e in report.errors if "url" in e.path]
        assert len(url_errors) >= 1

    def test_metadata_url_must_be_string(self):
        """Test that metadata.url must be a string."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "metadata": {
                        "url": 123
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to metadata.url type
        url_errors = [e for e in report.errors if "url" in e.path]
        assert len(url_errors) >= 1

    def test_metadata_url_must_not_be_empty(self):
        """Test that metadata.url must have minimum length of 1."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "metadata": {
                        "url": ""
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to metadata.url length
        url_errors = [e for e in report.errors if "url" in e.path]
        assert len(url_errors) >= 1

    def test_metadata_show_key_string(self):
        """Test that metadata.show_key accepts string."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "metadata": {
                        "url": "https://example.com/test.yaml",
                        "show_key": "test-show"
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_metadata_show_key_null(self):
        """Test that metadata.show_key accepts null."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "metadata": {
                        "url": "https://example.com/test.yaml",
                        "show_key": None
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_metadata_ttl_hours_integer(self):
        """Test that metadata.ttl_hours accepts integer."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "metadata": {
                        "url": "https://example.com/test.yaml",
                        "ttl_hours": 24
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_metadata_ttl_hours_minimum_value(self):
        """Test that metadata.ttl_hours must be at least 1."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "metadata": {
                        "url": "https://example.com/test.yaml",
                        "ttl_hours": 0
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to ttl_hours
        ttl_errors = [e for e in report.errors if "ttl_hours" in e.path]
        assert len(ttl_errors) >= 1

    def test_metadata_headers_object(self):
        """Test that metadata.headers accepts object with string values."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "metadata": {
                        "url": "https://example.com/test.yaml",
                        "headers": {
                            "Authorization": "Bearer token",
                            "User-Agent": "Playbook/1.0"
                        }
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_metadata_season_overrides_object(self):
        """Test that metadata.season_overrides accepts object."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "metadata": {
                        "url": "https://example.com/test.yaml",
                        "season_overrides": {
                            "2023": {"key": "value"}
                        }
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_pattern_sets_as_array(self):
        """Test that sport.pattern_sets accepts array of strings."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "pattern_sets": ["nhl_default", "custom_set"],
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        # May have errors about unknown pattern sets, but schema validation passes
        # The semantic validation (unknown pattern sets) is tested separately

    def test_sport_file_patterns_as_array(self):
        """Test that sport.file_patterns accepts array of pattern definitions."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "file_patterns": [
                        {
                            "regex": r".*\.mkv"
                        }
                    ],
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_pattern_definition_regex_required(self):
        """Test that pattern_definition.regex is required."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "file_patterns": [
                        {
                            "description": "Test pattern"
                        }
                    ],
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to regex
        regex_errors = [e for e in report.errors if "regex" in e.message.lower() or "file_patterns" in e.path]
        assert len(regex_errors) >= 1

    def test_pattern_definition_regex_must_not_be_empty(self):
        """Test that pattern_definition.regex must have minimum length."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "file_patterns": [
                        {
                            "regex": ""
                        }
                    ],
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to regex length
        regex_errors = [e for e in report.errors if "file_patterns" in e.path]
        assert len(regex_errors) >= 1

    def test_pattern_definition_with_season_selector(self):
        """Test that pattern_definition can include season_selector."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "file_patterns": [
                        {
                            "regex": r".*\.mkv",
                            "season_selector": {
                                "mode": "round",
                                "offset": 1
                            }
                        }
                    ],
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_season_selector_mode_enum(self):
        """Test that season_selector.mode must be valid enum value."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "file_patterns": [
                        {
                            "regex": r".*\.mkv",
                            "season_selector": {
                                "mode": "invalid_mode"
                            }
                        }
                    ],
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to mode
        mode_errors = [e for e in report.errors if "mode" in e.path or "season_selector" in e.path]
        assert len(mode_errors) >= 1

    def test_season_selector_valid_modes(self):
        """Test that season_selector.mode accepts valid enum values."""
        valid_modes = ["round", "key", "title", "sequential", "date"]
        for mode in valid_modes:
            config = {
                "sports": [
                    {
                        "id": "test-sport",
                        "file_patterns": [
                            {
                                "regex": r".*\.mkv",
                                "season_selector": {
                                    "mode": mode
                                }
                            }
                        ],
                        "metadata": {"url": "https://example.com/test.yaml"}
                    }
                ]
            }
            report = validate_config_data(config)
            assert report.is_valid is True, f"Mode '{mode}' should be valid"

    def test_pattern_definition_with_episode_selector(self):
        """Test that pattern_definition can include episode_selector."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "file_patterns": [
                        {
                            "regex": r".*\.mkv",
                            "episode_selector": {
                                "group": "episode"
                            }
                        }
                    ],
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_source_globs_array(self):
        """Test that sport.source_globs accepts array of strings."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "source_globs": ["**/*.mkv", "**/*.mp4"],
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_source_extensions_array(self):
        """Test that sport.source_extensions accepts array of strings."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "source_extensions": [".mkv", ".mp4", ".avi"],
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_link_mode_valid_values(self):
        """Test that sport.link_mode accepts valid enum values."""
        for link_mode in ["hardlink", "copy", "symlink"]:
            config = {
                "sports": [
                    {
                        "id": "test-sport",
                        "link_mode": link_mode,
                        "metadata": {"url": "https://example.com/test.yaml"}
                    }
                ]
            }
            report = validate_config_data(config)
            assert report.is_valid is True, f"Link mode '{link_mode}' should be valid"

    def test_sport_link_mode_invalid_value(self):
        """Test that sport.link_mode rejects invalid values."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "link_mode": "invalid_mode",
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is False
        # Find error related to link_mode
        link_errors = [e for e in report.errors if "link_mode" in e.path]
        assert len(link_errors) >= 1

    def test_sport_allow_unmatched_boolean(self):
        """Test that sport.allow_unmatched accepts boolean."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "allow_unmatched": True,
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_destination_templates(self):
        """Test that sport.destination accepts template strings."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "destination": {
                        "root_template": "{sport_id}",
                        "season_dir_template": "Season {season}",
                        "episode_template": "{title}.{ext}"
                    },
                    "metadata": {"url": "https://example.com/test.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_variants_array(self):
        """Test that sport.variants accepts array of variant objects."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "variants": [
                        {
                            "id": "variant-1",
                            "metadata": {"url": "https://example.com/variant1.yaml"}
                        }
                    ]
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_variant_with_id_string(self):
        """Test that variant.id accepts string."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "variants": [
                        {
                            "id": "custom-variant-id",
                            "metadata": {"url": "https://example.com/variant.yaml"}
                        }
                    ]
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_variant_with_id_suffix(self):
        """Test that variant.id_suffix accepts string."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "variants": [
                        {
                            "id_suffix": "-2023",
                            "metadata": {"url": "https://example.com/variant.yaml"}
                        }
                    ]
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_variant_with_year_integer(self):
        """Test that variant.year accepts integer."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "variants": [
                        {
                            "year": 2023,
                            "metadata": {"url": "https://example.com/variant.yaml"}
                        }
                    ]
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_variant_with_year_string(self):
        """Test that variant.year accepts string."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "variants": [
                        {
                            "year": "2023",
                            "metadata": {"url": "https://example.com/variant.yaml"}
                        }
                    ]
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_variant_with_name(self):
        """Test that variant.name accepts string."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "variants": [
                        {
                            "name": "Test Variant",
                            "metadata": {"url": "https://example.com/variant.yaml"}
                        }
                    ]
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_variant_metadata_structure(self):
        """Test that variant.metadata follows metadata schema."""
        config = {
            "sports": [
                {
                    "id": "test-sport",
                    "variants": [
                        {
                            "metadata": {
                                "url": "https://example.com/variant.yaml",
                                "show_key": "variant-show",
                                "ttl_hours": 48
                            }
                        }
                    ]
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_multiple_sports_in_array(self):
        """Test that multiple sports can be defined in array."""
        config = {
            "sports": [
                {
                    "id": "sport-1",
                    "metadata": {"url": "https://example.com/sport1.yaml"}
                },
                {
                    "id": "sport-2",
                    "metadata": {"url": "https://example.com/sport2.yaml"}
                },
                {
                    "id": "sport-3",
                    "metadata": {"url": "https://example.com/sport3.yaml"}
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_with_all_optional_fields(self):
        """Test sport with all optional fields populated."""
        config = {
            "sports": [
                {
                    "id": "comprehensive-sport",
                    "name": "Comprehensive Sport",
                    "enabled": True,
                    "team_alias_map": "nhl",
                    "metadata": {
                        "url": "https://example.com/test.yaml",
                        "show_key": "test-show",
                        "ttl_hours": 24,
                        "headers": {"Authorization": "Bearer token"},
                        "season_overrides": {"2023": {}}
                    },
                    "pattern_sets": [],
                    "file_patterns": [
                        {
                            "regex": r".*\.mkv",
                            "description": "MKV files",
                            "season_selector": {"mode": "round"},
                            "episode_selector": {"group": "ep"},
                            "priority": 100
                        }
                    ],
                    "source_globs": ["**/*.mkv"],
                    "source_extensions": [".mkv", ".mp4"],
                    "link_mode": "hardlink",
                    "allow_unmatched": False,
                    "destination": {
                        "root_template": "{sport_id}",
                        "season_dir_template": "Season {season}",
                        "episode_template": "{title}.{ext}"
                    }
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True

    def test_sport_with_multiple_variants(self):
        """Test sport with multiple variants."""
        config = {
            "sports": [
                {
                    "id": "multi-variant-sport",
                    "variants": [
                        {
                            "id": "variant-1",
                            "year": 2022,
                            "metadata": {"url": "https://example.com/v1.yaml"}
                        },
                        {
                            "id": "variant-2",
                            "year": 2023,
                            "metadata": {"url": "https://example.com/v2.yaml"}
                        },
                        {
                            "id_suffix": "-2024",
                            "year": "2024",
                            "name": "2024 Season",
                            "metadata": {"url": "https://example.com/v3.yaml"}
                        }
                    ]
                }
            ]
        }
        report = validate_config_data(config)
        assert report.is_valid is True
