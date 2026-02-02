"""
Configuration editor page for the Playbook GUI.

Provides a YAML editor with live validation and save functionality.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

import yaml
from nicegui import ui

from ..state import gui_state

LOGGER = logging.getLogger(__name__)


def config_page() -> None:
    """Render the configuration editor page."""
    # Load current config
    config_text = _load_config_yaml()
    original_text = config_text

    # State
    state = {
        "modified": False,
        "valid": True,
        "validation_messages": [],
    }

    with ui.column().classes("w-full max-w-7xl mx-auto p-4 gap-4"):
        # Page title with actions
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Configuration").classes("text-3xl font-bold text-gray-800")

            with ui.row().classes("gap-2"):
                # Save indicator
                save_indicator = ui.label("").classes("text-sm")

                # Validate button
                validate_btn = ui.button(
                    "Validate",
                    icon="check_circle",
                    on_click=lambda: _validate_config(editor.value, validation_panel, state, validate_btn),
                ).props("outline")

                # Save button
                save_btn = ui.button(
                    "Save",
                    icon="save",
                    on_click=lambda: _save_config(editor.value, state, save_btn, save_indicator),
                ).props("color=primary")

                # Reset button
                ui.button(
                    "Reset",
                    icon="undo",
                    on_click=lambda: _reset_config(editor, original_text, state),
                ).props("outline")

        # Main content: Editor + Validation panel
        with ui.row().classes("w-full gap-4"):
            # Editor panel (left, wider)
            with ui.card().classes("flex-1"):
                with ui.row().classes("items-center justify-between mb-2"):
                    ui.label("playbook.yaml").classes("text-lg font-semibold text-gray-700")
                    if gui_state.config_path:
                        ui.label(str(gui_state.config_path)).classes("text-sm text-gray-500")

                # YAML editor
                editor = (
                    ui.textarea(value=config_text)
                    .classes("w-full font-mono text-sm")
                    .style("height: 600px; max-height: 70vh;")
                    .props("outlined")
                )

                # Track modifications
                def on_change(e) -> None:
                    state["modified"] = e.value != original_text
                    if state["modified"]:
                        save_indicator.text = "Modified"
                        save_indicator.classes(replace="text-yellow-600 text-sm")
                    else:
                        save_indicator.text = ""

                editor.on("change", on_change)

            # Validation panel (right, narrower)
            with ui.column().classes("w-80 gap-4"):
                # Validation results
                with ui.card().classes("w-full"):
                    ui.label("Validation").classes("text-lg font-semibold text-gray-700 mb-2")
                    validation_panel = ui.column().classes("w-full gap-2")
                    with validation_panel:
                        ui.label("Click 'Validate' to check configuration").classes("text-sm text-gray-500 italic")

                # Help/Tips card
                with ui.card().classes("w-full"):
                    ui.label("Tips").classes("text-lg font-semibold text-gray-700 mb-2")
                    with ui.column().classes("gap-1 text-sm text-gray-600"):
                        ui.label("- Use 2-space indentation for YAML")
                        ui.label("- Required: settings, sports sections")
                        ui.label("- Each sport needs: id, show_slug")
                        ui.label("- Save creates automatic backup")

                # Quick links
                with ui.card().classes("w-full"):
                    ui.label("Reference").classes("text-lg font-semibold text-gray-700 mb-2")
                    with ui.column().classes("gap-1"):
                        ui.link(
                            "Documentation",
                            "https://s0len.github.io/Playbook/",
                            new_tab=True,
                        ).classes("text-sm text-blue-600")
                        ui.link(
                            "Sample Config",
                            "https://github.com/s0len/Playbook/blob/main/config/playbook.sample.yaml",
                            new_tab=True,
                        ).classes("text-sm text-blue-600")


def _load_config_yaml() -> str:
    """Load the current configuration YAML."""
    if not gui_state.config_path:
        return "# No configuration file loaded\n"

    try:
        return gui_state.config_path.read_text(encoding="utf-8")
    except Exception as e:
        LOGGER.error("Failed to load config: %s", e)
        return f"# Error loading configuration: {e}\n"


def _validate_config(yaml_text: str, panel: ui.column, state: dict, button: ui.button) -> None:
    """Validate the YAML configuration."""
    from playbook.validation import validate_config_data

    panel.clear()
    messages = []

    try:
        # Parse YAML
        data = yaml.safe_load(yaml_text)
        if data is None:
            messages.append(("error", "Empty configuration"))
            state["valid"] = False
        else:
            # Run validation
            report = validate_config_data(data)

            if report.is_valid:
                messages.append(("success", "Configuration is valid"))
                state["valid"] = True

                # Try actual load as final check
                try:
                    import tempfile

                    from playbook.config import load_config

                    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                        f.write(yaml_text)
                        temp_path = Path(f.name)
                    try:
                        load_config(temp_path)
                        messages.append(("success", "Configuration loads successfully"))
                    finally:
                        temp_path.unlink(missing_ok=True)
                except Exception as e:
                    messages.append(("warning", f"Load warning: {e}"))
            else:
                state["valid"] = False
                for error in report.errors:
                    messages.append(("error", f"{error.path}: {error.message}"))
                for warning in report.warnings:
                    messages.append(("warning", f"{warning.path}: {warning.message}"))

    except yaml.YAMLError as e:
        messages.append(("error", f"YAML syntax error: {e}"))
        state["valid"] = False
    except Exception as e:
        messages.append(("error", f"Validation error: {e}"))
        state["valid"] = False

    state["validation_messages"] = messages

    # Update panel
    with panel:
        for msg_type, message in messages:
            _validation_message(msg_type, message)

    # Update button
    if state["valid"]:
        button.props("color=positive")
        ui.notify("Configuration is valid", type="positive")
    else:
        button.props("color=negative")
        ui.notify("Configuration has errors", type="negative")


def _validation_message(msg_type: str, message: str) -> None:
    """Render a validation message."""
    colors = {
        "error": ("bg-red-100 text-red-800", "error"),
        "warning": ("bg-yellow-100 text-yellow-800", "warning"),
        "success": ("bg-green-100 text-green-800", "check_circle"),
    }
    color_class, icon = colors.get(msg_type, ("bg-gray-100 text-gray-800", "info"))

    with ui.row().classes(f"w-full items-start gap-2 p-2 rounded {color_class}"):
        ui.icon(icon).classes("text-lg shrink-0")
        ui.label(message).classes("text-sm break-all")


def _save_config(yaml_text: str, state: dict, button: ui.button, indicator: ui.label) -> None:
    """Save the configuration to file."""
    if not gui_state.config_path:
        ui.notify("No configuration file path set", type="warning")
        return

    # Validate first
    try:
        data = yaml.safe_load(yaml_text)
        if data is None:
            ui.notify("Cannot save empty configuration", type="negative")
            return
    except yaml.YAMLError as e:
        ui.notify(f"Cannot save invalid YAML: {e}", type="negative")
        return

    try:
        # Create backup
        backup_path = _create_backup(gui_state.config_path)
        if backup_path:
            LOGGER.info("Created backup: %s", backup_path)

        # Write new config
        gui_state.config_path.write_text(yaml_text, encoding="utf-8")

        state["modified"] = False
        indicator.text = "Saved"
        indicator.classes(replace="text-green-600 text-sm")

        ui.notify("Configuration saved successfully", type="positive")
        LOGGER.info("Configuration saved to %s", gui_state.config_path)

    except Exception as e:
        LOGGER.exception("Failed to save config: %s", e)
        ui.notify(f"Failed to save: {e}", type="negative")


def _create_backup(config_path: Path) -> Path | None:
    """Create a timestamped backup of the config file."""
    if not config_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = config_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    backup_name = f"{config_path.stem}_{timestamp}{config_path.suffix}"
    backup_path = backup_dir / backup_name

    shutil.copy2(config_path, backup_path)
    return backup_path


def _reset_config(editor: ui.textarea, original_text: str, state: dict) -> None:
    """Reset editor to original content."""
    editor.value = original_text
    state["modified"] = False
    ui.notify("Configuration reset to original", type="info")
