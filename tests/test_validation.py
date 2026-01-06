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
