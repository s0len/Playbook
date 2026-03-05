"""
Application info tab for the Settings page.

Shows build, runtime, and storage information.
"""

from __future__ import annotations

import platform
import subprocess
from datetime import datetime
from typing import TYPE_CHECKING

from nicegui import ui

from ...components.settings import settings_card
from ...state import gui_state

if TYPE_CHECKING:
    from ...settings_state.settings_state import SettingsFormState


def _info_row(label: str, value: str) -> None:
    """Render a label-value row."""
    with ui.row().classes("w-full items-center justify-between py-1"):
        ui.label(label).classes("text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400")
        ui.label(value).classes("text-sm font-semibold text-slate-800 dark:text-slate-100 select-all")


def _get_git_sha() -> str:
    """Get the short git commit SHA."""
    import os

    sha = os.environ.get("GIT_SHA")
    if sha:
        return sha[:8]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "N/A"


def _get_build_date() -> str:
    """Get the build date from env or fallback."""
    import os

    return os.environ.get("GIT_BUILD_DATE", "N/A")


def _format_uptime(start: datetime) -> str:
    """Format uptime as human-readable string."""
    delta = datetime.now() - start
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def application_tab(state: SettingsFormState) -> None:
    """Render the Application info tab."""
    from playbook import __version__

    with ui.column().classes("w-full gap-6"):
        # Build info
        with settings_card("Build", icon="build", description="Version and build information"):
            _info_row("VERSION", __version__)
            _info_row("COMMIT", _get_git_sha())
            _info_row("BUILD DATE", _get_build_date())

        # Runtime info
        with settings_card("Runtime", icon="memory", description="Current runtime environment"):
            _info_row("UPTIME", _format_uptime(gui_state.start_time))
            _info_row("PYTHON", platform.python_version())
            _info_row("PLATFORM", platform.platform())

        # Storage info
        with settings_card("Storage", icon="storage", description="File and data paths"):
            config_path = str(gui_state.config_path) if gui_state.config_path else "N/A"
            _info_row("CONFIG FILE", config_path)

            cache_dir = "N/A"
            state_dir = "N/A"
            theme_name = "N/A"
            if gui_state.config and gui_state.config.settings:
                cache_dir = str(gui_state.config.settings.cache_dir)
                state_dir = str(gui_state.config.settings.state_dir or gui_state.config.settings.cache_dir)
                theme_name = str(gui_state.config.settings.theme)
            _info_row("CACHE DIR", cache_dir)
            _info_row("STATE DIR", state_dir)
            _info_row("THEME", theme_name)

            db_path = "N/A"
            if gui_state.processed_store and hasattr(gui_state.processed_store, "db_path"):
                db_path = str(gui_state.processed_store.db_path)
            _info_row("DATABASE", db_path)
