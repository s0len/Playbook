"""
Settings form state management for the Playbook GUI.

This module provides state management for the Settings GUI, tracking
form data, modifications, validation errors, and active tab state.
"""

from __future__ import annotations

import copy
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

LOGGER = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """A single validation error for a form field."""

    path: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class SettingsFormState:
    """State management for the Settings form.

    This class tracks the current form data, original data for reset/comparison,
    which fields have been modified, validation errors, and navigation state.

    Attributes:
        original_data: The configuration as loaded from file (for reset/comparison)
        form_data: Current form values (mutable copy)
        modified_paths: Set of dotted paths that have been modified
        validation_errors: Map of field path to validation error
        active_tab: Currently selected sidebar tab
        is_saving: Whether a save operation is in progress
        config_path: Path to the configuration file
        _update_callbacks: Callbacks to notify when state changes
    """

    original_data: dict[str, Any] = field(default_factory=dict)
    form_data: dict[str, Any] = field(default_factory=dict)
    modified_paths: set[str] = field(default_factory=set)
    validation_errors: dict[str, ValidationError] = field(default_factory=dict)
    active_tab: str = "general"
    is_saving: bool = False
    config_path: Path | None = None
    _update_callbacks: list[Callable[[str, Any], None]] = field(default_factory=list)

    @property
    def is_modified(self) -> bool:
        """Check if any fields have been modified."""
        return len(self.modified_paths) > 0

    @property
    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return any(e.severity == "error" for e in self.validation_errors.values())

    @property
    def has_warnings(self) -> bool:
        """Check if there are any validation warnings."""
        return any(e.severity == "warning" for e in self.validation_errors.values())

    def load_from_yaml(self, yaml_path: Path) -> bool:
        """Load configuration from a YAML file.

        Args:
            yaml_path: Path to the YAML configuration file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            yaml_text = yaml_path.read_text(encoding="utf-8")
            data = yaml.safe_load(yaml_text) or {}
            self.original_data = data
            self.form_data = copy.deepcopy(data)
            self.modified_paths = set()
            self.validation_errors = {}
            self.config_path = yaml_path
            self._notify_update("loaded", {"path": str(yaml_path)})
            return True
        except Exception as e:
            LOGGER.error("Failed to load configuration: %s", e)
            return False

    def load_from_dict(self, data: dict[str, Any], config_path: Path | None = None) -> None:
        """Load configuration from a dictionary.

        Args:
            data: Configuration dictionary
            config_path: Optional path to associate with this config
        """
        self.original_data = copy.deepcopy(data)
        self.form_data = copy.deepcopy(data)
        self.modified_paths = set()
        self.validation_errors = {}
        self.config_path = config_path
        self._notify_update("loaded", {"path": str(config_path) if config_path else None})

    def get_value(self, path: str, default: Any = None) -> Any:
        """Get a value from form data by dotted path.

        Args:
            path: Dotted path like "settings.dry_run" or "settings.notifications.targets"
            default: Default value if path not found

        Returns:
            The value at the path, or default if not found
        """
        return self._get_nested(self.form_data, path, default)

    def set_value(self, path: str, value: Any) -> None:
        """Set a value in form data and track modification.

        Args:
            path: Dotted path like "settings.dry_run"
            value: New value to set
        """
        original_value = self._get_nested(self.original_data, path)
        self._set_nested(self.form_data, path, value)

        # Track modification state
        if self._values_equal(value, original_value):
            self.modified_paths.discard(path)
        else:
            self.modified_paths.add(path)

        # Clear validation error for this path when value changes
        self.validation_errors.pop(path, None)

        self._notify_update("value_changed", {"path": path, "value": value})

    def reset_to_original(self) -> None:
        """Reset all form data to original values."""
        self.form_data = copy.deepcopy(self.original_data)
        self.modified_paths = set()
        self.validation_errors = {}
        self._notify_update("reset", {})

    def reset_field(self, path: str) -> None:
        """Reset a single field to its original value.

        Args:
            path: Dotted path of the field to reset
        """
        original_value = self._get_nested(self.original_data, path)
        self._set_nested(self.form_data, path, copy.deepcopy(original_value))
        self.modified_paths.discard(path)
        self.validation_errors.pop(path, None)
        self._notify_update("field_reset", {"path": path})

    def set_validation_error(self, path: str, message: str, severity: str = "error") -> None:
        """Set a validation error for a field.

        Args:
            path: Dotted path of the field
            message: Error message to display
            severity: "error" or "warning"
        """
        self.validation_errors[path] = ValidationError(path=path, message=message, severity=severity)
        self._notify_update("validation_error", {"path": path, "message": message})

    def clear_validation_error(self, path: str) -> None:
        """Clear a validation error for a field.

        Args:
            path: Dotted path of the field
        """
        if path in self.validation_errors:
            del self.validation_errors[path]
            self._notify_update("validation_cleared", {"path": path})

    def clear_all_errors(self) -> None:
        """Clear all validation errors."""
        self.validation_errors = {}
        self._notify_update("validation_cleared_all", {})

    def is_field_modified(self, path: str) -> bool:
        """Check if a specific field has been modified.

        Args:
            path: Dotted path of the field

        Returns:
            True if the field has been modified
        """
        return path in self.modified_paths

    def get_validation_error(self, path: str) -> ValidationError | None:
        """Get validation error for a field.

        Args:
            path: Dotted path of the field

        Returns:
            ValidationError if present, None otherwise
        """
        return self.validation_errors.get(path)

    def to_yaml(self) -> str:
        """Convert current form data to YAML string.

        Returns:
            YAML representation of the form data
        """
        return yaml.dump(self.form_data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def save(self) -> bool:
        """Save current form data to the configuration file.

        Returns:
            True if saved successfully, False otherwise
        """
        if not self.config_path:
            LOGGER.error("No configuration path set")
            return False

        self.is_saving = True
        self._notify_update("saving", {"path": str(self.config_path)})

        try:
            yaml_content = self.to_yaml()
            self.config_path.write_text(yaml_content, encoding="utf-8")

            # Update original data to match saved data
            self.original_data = copy.deepcopy(self.form_data)
            self.modified_paths = set()

            self._notify_update("saved", {"path": str(self.config_path)})
            return True
        except Exception as e:
            LOGGER.error("Failed to save configuration: %s", e)
            self._notify_update("save_error", {"error": str(e)})
            return False
        finally:
            self.is_saving = False

    def set_active_tab(self, tab: str) -> None:
        """Set the active tab.

        Args:
            tab: Tab identifier (general, quality, notifications, watcher, integrations, advanced)
        """
        self.active_tab = tab
        self._notify_update("tab_changed", {"tab": tab})

    def register_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Register a callback for state updates.

        Args:
            callback: Function to call with (event_type, data)
        """
        if callback not in self._update_callbacks:
            self._update_callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Unregister a state update callback.

        Args:
            callback: The callback to remove
        """
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)

    def _notify_update(self, event_type: str, data: Any) -> None:
        """Notify all registered callbacks of a state change.

        Args:
            event_type: Type of update (loaded, value_changed, reset, etc.)
            data: Event-specific data
        """
        import contextlib

        for callback in self._update_callbacks:
            with contextlib.suppress(Exception):
                callback(event_type, data)

    @staticmethod
    def _get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
        """Get a nested value from a dictionary using dotted path.

        Args:
            data: Dictionary to search
            path: Dotted path like "settings.dry_run"
            default: Default value if not found

        Returns:
            Value at path or default
        """
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    @staticmethod
    def _set_nested(data: dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value in a dictionary using dotted path.

        Creates intermediate dictionaries as needed.

        Args:
            data: Dictionary to modify
            path: Dotted path like "settings.dry_run"
            value: Value to set
        """
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    @staticmethod
    def _values_equal(a: Any, b: Any) -> bool:
        """Compare two values for equality, handling special cases.

        Args:
            a: First value
            b: Second value

        Returns:
            True if values are considered equal
        """
        # Handle None comparisons
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False

        # Handle list comparisons
        if isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                return False
            return all(SettingsFormState._values_equal(x, y) for x, y in zip(a, b, strict=True))

        # Handle dict comparisons
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a.keys()) != set(b.keys()):
                return False
            return all(SettingsFormState._values_equal(a[k], b[k]) for k in a)

        # Direct comparison
        return a == b


# Default tabs for the settings page
SETTINGS_TABS = [
    ("general", "General", "settings"),
    ("quality", "Quality", "tune"),
    ("notifications", "Notifications", "notifications"),
    ("watcher", "File Watcher", "visibility"),
    ("integrations", "Integrations", "extension"),
    ("advanced", "Advanced", "code"),
]
