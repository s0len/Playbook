"""
Advanced settings tab for the Settings page.

Provides YAML editor, backups management, and import/export.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from nicegui import ui

from ...components.settings import settings_card

if TYPE_CHECKING:
    from ...settings_state.settings_state import SettingsFormState

LOGGER = logging.getLogger(__name__)


def advanced_tab(state: SettingsFormState) -> None:
    """Render the Advanced settings tab.

    Args:
        state: Settings form state
    """
    with ui.column().classes("w-full gap-6"):
        # YAML Editor Section
        _render_yaml_editor(state)

        # Backups Section
        _render_backups_section(state)

        # Import/Export Section
        _render_import_export_section(state)


def _render_yaml_editor(state: SettingsFormState) -> None:
    """Render the raw YAML editor."""
    with settings_card(
        "YAML Editor",
        icon="code",
        description="Edit configuration directly as YAML",
    ):
        yaml_text = state.to_yaml()

        editor = (
            ui.textarea(value=yaml_text)
            .classes("w-full font-mono text-sm")
            .style("height: 600px !important; min-height: 600px !important;")
            .props("outlined")
        )

        with ui.row().classes("w-full items-center justify-between mt-4"):
            with ui.row().classes("gap-2"):
                ui.button(
                    "Format",
                    icon="format_align_left",
                    on_click=lambda: _format_yaml(editor),
                ).props("outline")
                ui.button(
                    "Validate",
                    icon="check_circle",
                    on_click=lambda: _validate_yaml(editor.value),
                ).props("outline")

            ui.button(
                "Apply Changes",
                icon="save",
                on_click=lambda: _apply_yaml_changes(state, editor.value),
            ).props("color=primary")

        # Help text
        with ui.expansion(text="YAML Syntax Help", icon="help").props("dense").classes("mt-2"):
            with ui.column().classes("gap-1 text-xs text-slate-600 dark:text-slate-400"):
                ui.label("• Use 2-space indentation")
                ui.label("• Strings with special characters should be quoted")
                ui.label("• Lists use '- ' prefix")
                ui.label("• Use null for empty values")


def _render_backups_section(state: SettingsFormState) -> None:
    """Render the backups management section."""
    with settings_card(
        "Configuration Backups",
        icon="backup",
        description="Manage configuration backups",
        collapsible=True,
        default_expanded=False,
    ):
        backups = _list_backups(state.config_path)

        if backups:
            with ui.column().classes("w-full gap-2"):
                for backup in backups[:10]:  # Show last 10 backups
                    _render_backup_row(state, backup)

                if len(backups) > 10:
                    ui.label(f"...and {len(backups) - 10} more").classes(
                        "text-xs text-slate-500 dark:text-slate-400 italic"
                    )
        else:
            ui.label("No backups found").classes("text-sm text-slate-500 dark:text-slate-400 italic")

        with ui.row().classes("w-full gap-2 mt-4"):
            ui.button(
                "Create Backup",
                icon="add",
                on_click=lambda: _create_backup(state),
            ).props("outline")
            ui.button(
                "Clean Old Backups",
                icon="delete_sweep",
                on_click=lambda: _clean_old_backups(state),
            ).props("outline color=warning")


def _render_backup_row(state: SettingsFormState, backup_path: Path) -> None:
    """Render a single backup row."""
    # Extract timestamp from filename
    try:
        timestamp_str = backup_path.stem.split("_")[-2] + "_" + backup_path.stem.split("_")[-1]
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
        display_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        display_time = backup_path.name

    size_kb = backup_path.stat().st_size / 1024

    with ui.row().classes("w-full items-center gap-2 py-1 px-2 bg-slate-50 dark:bg-slate-800 rounded"):
        ui.icon("description").classes("text-slate-400")
        ui.label(display_time).classes("flex-1 text-sm text-slate-700 dark:text-slate-200")
        ui.label(f"{size_kb:.1f} KB").classes("text-xs text-slate-500 dark:text-slate-400")
        ui.button(
            icon="restore",
            on_click=lambda p=backup_path: _restore_backup(state, p),
        ).props("flat dense").classes("text-blue-600")
        ui.button(
            icon="delete",
            on_click=lambda p=backup_path: _delete_backup(p),
        ).props("flat dense color=negative")


def _render_import_export_section(state: SettingsFormState) -> None:
    """Render import/export section."""
    with settings_card(
        "Import / Export",
        icon="import_export",
        description="Import or export configuration",
        collapsible=True,
        default_expanded=False,
    ):
        with ui.row().classes("w-full gap-4"):
            # Export
            with ui.column().classes("flex-1 gap-2"):
                ui.label("Export Configuration").classes("text-sm font-medium text-slate-700 dark:text-slate-200")
                ui.label("Download current configuration as YAML file").classes(
                    "text-xs text-slate-500 dark:text-slate-400"
                )
                ui.button(
                    "Export",
                    icon="download",
                    on_click=lambda: _export_config(state),
                ).props("outline")

            # Import
            with ui.column().classes("flex-1 gap-2"):
                ui.label("Import Configuration").classes("text-sm font-medium text-slate-700 dark:text-slate-200")
                ui.label("Load configuration from YAML file").classes("text-xs text-slate-500 dark:text-slate-400")
                ui.upload(
                    label="Choose File",
                    on_upload=lambda e: _import_config(state, e),
                ).props('accept=".yaml,.yml" max-file-size="1048576"').classes("max-w-xs")

            # Reset to sample
            with ui.column().classes("flex-1 gap-2"):
                ui.label("Reset to Sample").classes("text-sm font-medium text-slate-700 dark:text-slate-200")
                ui.label("Reset configuration to sample defaults").classes("text-xs text-slate-500 dark:text-slate-400")
                ui.button(
                    "Reset",
                    icon="restart_alt",
                    on_click=lambda: _reset_to_sample(state),
                ).props("outline color=warning")


# Helper functions


def _format_yaml(editor: ui.textarea) -> None:
    """Format YAML in editor."""
    try:
        data = yaml.safe_load(editor.value)
        formatted = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        editor.value = formatted
        ui.notify("YAML formatted", type="positive")
    except yaml.YAMLError as e:
        ui.notify(f"Invalid YAML: {e}", type="negative")


def _validate_yaml(yaml_text: str) -> None:
    """Validate YAML syntax and schema."""
    try:
        data = yaml.safe_load(yaml_text)
        if data is None:
            ui.notify("Empty configuration", type="warning")
            return

        from playbook.validation import validate_config_data

        report = validate_config_data(data)
        if report.is_valid:
            ui.notify("Configuration is valid", type="positive")
        else:
            errors = [f"{e.path}: {e.message}" for e in report.errors[:5]]
            ui.notify("Validation errors:\n" + "\n".join(errors), type="negative")

    except yaml.YAMLError as e:
        ui.notify(f"YAML syntax error: {e}", type="negative")


def _apply_yaml_changes(state: SettingsFormState, yaml_text: str) -> None:
    """Apply YAML changes to form state."""
    try:
        data = yaml.safe_load(yaml_text)
        if data is None:
            ui.notify("Cannot apply empty configuration", type="warning")
            return

        state.load_from_dict(data, state.config_path)
        ui.notify("Changes applied to form", type="positive")
        ui.navigate.to("/config")  # Refresh page
    except yaml.YAMLError as e:
        ui.notify(f"Invalid YAML: {e}", type="negative")


def _list_backups(config_path: Path | None) -> list[Path]:
    """List configuration backups."""
    if not config_path:
        return []

    backup_dir = config_path.parent / "backups"
    if not backup_dir.exists():
        return []

    backups = sorted(
        backup_dir.glob(f"{config_path.stem}_*.yaml"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return backups


def _create_backup(state: SettingsFormState) -> None:
    """Create a manual backup."""
    if not state.config_path:
        ui.notify("No configuration file to backup", type="warning")
        return

    backup_dir = state.config_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{state.config_path.stem}_{timestamp}{state.config_path.suffix}"
    backup_path = backup_dir / backup_name

    shutil.copy2(state.config_path, backup_path)
    ui.notify(f"Backup created: {backup_name}", type="positive")
    ui.navigate.to("/config")


def _restore_backup(state: SettingsFormState, backup_path: Path) -> None:
    """Restore a backup."""
    try:
        yaml_text = backup_path.read_text(encoding="utf-8")
        data = yaml.safe_load(yaml_text)
        state.load_from_dict(data, state.config_path)
        ui.notify(f"Restored from backup: {backup_path.name}", type="positive")
        ui.navigate.to("/config")
    except Exception as e:
        ui.notify(f"Failed to restore: {e}", type="negative")


def _delete_backup(backup_path: Path) -> None:
    """Delete a backup file."""
    try:
        backup_path.unlink()
        ui.notify(f"Deleted: {backup_path.name}", type="info")
        ui.navigate.to("/config")
    except Exception as e:
        ui.notify(f"Failed to delete: {e}", type="negative")


def _clean_old_backups(state: SettingsFormState, keep: int = 10) -> None:
    """Remove old backups, keeping the most recent ones."""
    backups = _list_backups(state.config_path)
    to_delete = backups[keep:]

    if not to_delete:
        ui.notify(f"No backups to clean (keeping last {keep})", type="info")
        return

    for backup in to_delete:
        backup.unlink(missing_ok=True)

    ui.notify(f"Removed {len(to_delete)} old backups", type="positive")
    ui.navigate.to("/config")


def _export_config(state: SettingsFormState) -> None:
    """Export configuration as downloadable file."""
    yaml_content = state.to_yaml()
    filename = f"playbook_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"

    ui.download(yaml_content.encode("utf-8"), filename)
    ui.notify(f"Downloading: {filename}", type="positive")


def _import_config(state: SettingsFormState, event) -> None:
    """Import configuration from uploaded file."""
    try:
        content = event.content.read().decode("utf-8")
        data = yaml.safe_load(content)
        if data is None:
            ui.notify("Empty configuration file", type="warning")
            return

        state.load_from_dict(data, state.config_path)
        ui.notify("Configuration imported", type="positive")
        ui.navigate.to("/config")
    except Exception as e:
        ui.notify(f"Import failed: {e}", type="negative")


def _reset_to_sample(state: SettingsFormState) -> None:
    """Reset to sample configuration."""
    try:
        # Look for sample config
        sample_paths = [
            Path(__file__).parent.parent.parent.parent.parent.parent.parent / "config" / "playbook.sample.yaml",
            Path("/app/config/playbook.sample.yaml"),
            Path("config/playbook.sample.yaml"),
        ]

        sample_content = None
        for sample_path in sample_paths:
            if sample_path.exists():
                sample_content = sample_path.read_text(encoding="utf-8")
                break

        if not sample_content:
            ui.notify("Sample configuration not found", type="warning")
            return

        data = yaml.safe_load(sample_content)
        state.load_from_dict(data, state.config_path)
        ui.notify("Reset to sample configuration", type="positive")
        ui.navigate.to("/config")

    except Exception as e:
        ui.notify(f"Reset failed: {e}", type="negative")
