"""
NiceGUI application setup and entry point for the Playbook GUI.

This module provides the main entry point for running Playbook with
the web GUI enabled, handling the integration between the Processor
and the NiceGUI web interface.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from nicegui import app, ui

from .components.header import header
from .log_handler import install_gui_log_handler
from .pages import dashboard, logs, settings, sports, unmatched
from .state import gui_state
from .styles import apply_color_theme, setup_page_styles
from .utils import suppress_nicegui_disconnect_errors

if TYPE_CHECKING:
    from playbook.config import AppConfig
    from playbook.processor import Processor

LOGGER = logging.getLogger(__name__)


def _persist_env_overrides(config_path: Path, overrides: dict) -> None:
    """Write env var overrides into the YAML config file.

    Uses safe YAML round-trip: load, update settings dict, write back.
    Only updates keys whose env var is set.
    """
    import yaml

    try:
        raw = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
        settings = data.setdefault("settings", {})
        changed = False
        for _env_var, (attr, value) in overrides.items():
            if value and str(settings.get(attr, "")) != value:
                settings[attr] = value
                changed = True
        if changed:
            config_path.write_text(
                yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            LOGGER.info("Persisted env var overrides to %s", config_path)
    except Exception:
        LOGGER.debug("Could not persist env overrides to config file", exc_info=True)


def create_app() -> None:
    """Create and configure the NiceGUI application with all routes."""

    # Serve icon.png as a static file
    _icon_path = Path(__file__).parent.parent.parent.parent / "icon.png"
    if _icon_path.exists():
        app.add_static_file(local_file=str(_icon_path), url_path="/icon.png")

    @ui.page("/")
    def index_page() -> None:
        """Dashboard page."""
        _page_wrapper(dashboard.dashboard_page, "/")

    @ui.page("/logs")
    def logs_page_route() -> None:
        """Logs page."""
        _page_wrapper(logs.logs_page, "/logs")

    @ui.page("/config")
    def config_page_route() -> None:
        """Settings page with form-based configuration."""
        _page_wrapper(settings.settings_page, "/config")

    @ui.page("/sports")
    def sports_page_route() -> None:
        """Sports management page."""
        _page_wrapper(sports.sports_page, "/sports")

    @ui.page("/sports/{sport_id}")
    def sport_detail_route(sport_id: str) -> None:
        """Sport detail page with season/episode tracking."""
        _page_wrapper(lambda: sports.sport_detail_page(sport_id), "/sports")

    @ui.page("/unmatched")
    def unmatched_page_route() -> None:
        """Unmatched files management page."""
        _page_wrapper(unmatched.unmatched_page, "/unmatched")

    # Health check endpoint — must respond instantly even under heavy load
    @app.get("/healthz")
    async def healthz() -> dict:
        """Lightweight liveness probe endpoint."""
        return {"status": "ok"}

    # API endpoints for programmatic access
    @app.get("/api/stats")
    def api_stats() -> dict:
        """Get current processing statistics."""
        return gui_state.get_stats()

    @app.get("/api/sports")
    def api_sports() -> list:
        """Get configured sports."""
        return gui_state.get_sports()

    @app.get("/api/status")
    def api_status() -> dict:
        """Get current status."""
        return {
            "is_processing": gui_state.is_processing,
            "last_run_at": gui_state.last_run_at.isoformat() if gui_state.last_run_at else None,
            "run_count": gui_state.run_count,
            "events_count": len(gui_state.recent_events),
            "log_entries_count": len(gui_state.log_buffer),
        }


def _page_wrapper(page_fn: callable, current_path: str = "/") -> None:
    """Wrap a page function with common layout elements."""
    # Inject styles and set up theme (includes FOUC prevention script)
    setup_page_styles()

    # Force dark mode (light mode removed)
    ui.dark_mode(True)

    # Override badge default: remove color="primary" which adds bg-primary class
    # and fights our semantic badge variant classes (app-badge-success etc.)
    ui.badge.default_props(remove="color")

    # Apply selected GUI color theme
    selected_theme = "swizzin"
    if gui_state.config and gui_state.config.settings:
        selected_theme = getattr(gui_state.config.settings, "theme", "swizzin") or "swizzin"
    apply_color_theme(str(selected_theme))

    # Add sidebar
    header(current_path=current_path)

    # Add page content
    page_fn()


def run_with_gui(
    config_path: Path,
    port: int = 8765,
    host: str = "0.0.0.0",
    *,
    dry_run: bool = False,
    enable_notifications: bool = True,
    watch_mode: bool = True,
    verbose: bool = False,
    **kwargs,
) -> None:
    """Run Playbook with the GUI enabled.

    This function initializes the Processor, sets up the GUI state,
    and starts both the NiceGUI web server and the file watcher
    (if enabled) in the same process.

    Args:
        config_path: Path to the Playbook configuration file
        port: Port to run the web server on (default: 8765)
        host: Host to bind the web server to (default: 0.0.0.0)
        dry_run: Enable dry-run mode
        enable_notifications: Enable notification delivery
        watch_mode: Enable file watcher mode
        verbose: Enable verbose logging
        **kwargs: Additional arguments passed to Processor
    """
    from playbook.config import load_config
    from playbook.processor import Processor

    # Suppress harmless NiceGUI disconnect errors
    suppress_nicegui_disconnect_errors()

    # Load configuration
    LOGGER.info("Loading configuration from %s", config_path)
    app_config = load_config(config_path)

    # Apply overrides
    if dry_run:
        app_config.settings.dry_run = True

    # Apply environment variable overrides and persist them to the config file
    # so the YAML always reflects the actual running values.
    import os

    _env_overrides = {
        "SOURCE_DIR": ("source_dir", os.getenv("SOURCE_DIR")),
        "DESTINATION_DIR": ("destination_dir", os.getenv("DESTINATION_DIR")),
        "CACHE_DIR": ("cache_dir", os.getenv("CACHE_DIR")),
        "STATE_DIR": ("state_dir", os.getenv("STATE_DIR")),
    }
    _config_changed = False
    for _env_var, (attr, value) in _env_overrides.items():
        if value:
            setattr(app_config.settings, attr, Path(value))
            _config_changed = True

    if _config_changed:
        _persist_env_overrides(config_path, _env_overrides)

    # Create processor
    LOGGER.info("Initializing Processor")
    processor = Processor(
        app_config,
        enable_notifications=enable_notifications,
        **kwargs,
    )

    # Initialize GUI state
    gui_state.processor = processor
    gui_state.config = app_config
    gui_state.config_path = config_path
    gui_state.processed_store = processor.processed_store
    gui_state.unmatched_store = processor.unmatched_store
    gui_state.manual_override_store = processor.manual_override_store

    # Forward notification events to GUI activity feed
    _original_notify = processor.notification_service.notify

    def _gui_notify(event):
        gui_state.add_event(event)
        _original_notify(event)

    processor.notification_service.notify = _gui_notify

    # Set NiceGUI storage path to persistent state directory
    state_dir = app_config.settings.state_dir or app_config.settings.cache_dir
    storage_path = state_dir / ".nicegui"
    storage_path.mkdir(parents=True, exist_ok=True)
    app.storage.path = storage_path
    LOGGER.debug("NiceGUI storage path: %s", storage_path)

    # Install log handler to forward logs to GUI
    log_handler = install_gui_log_handler(gui_state, level=logging.DEBUG if verbose else logging.INFO)

    # Create NiceGUI app
    create_app()

    # Set up shutdown handler
    @app.on_shutdown
    async def on_shutdown() -> None:
        LOGGER.info("Shutting down GUI...")
        # Remove log handler
        from .log_handler import remove_gui_log_handler

        remove_gui_log_handler(log_handler)

    # Start file watcher in background if enabled
    if watch_mode and app_config.settings.file_watcher.enabled:
        _start_watcher_thread(processor, app_config)

    # Run NiceGUI
    LOGGER.info("Starting Playbook GUI on http://%s:%d", host, port)
    ui.run(
        host=host,
        port=port,
        title="Playbook",
        favicon="https://raw.githubusercontent.com/s0len/Playbook/main/docs/assets/logo.png",
        dark=False,
        reload=False,
        show=False,  # Don't auto-open browser
        storage_secret="playbook-gui-storage",  # Enable persistent user storage
    )


def _start_watcher_thread(processor: Processor, app_config: AppConfig) -> threading.Thread:
    """Start the file watcher in a background thread.

    Args:
        processor: The Processor instance
        app_config: The application configuration

    Returns:
        The started thread
    """
    from playbook.watcher import FileWatcherLoop

    def run_watcher() -> None:
        LOGGER.info("Starting file watcher in background thread")
        try:
            watcher = FileWatcherLoop(
                processor,
                app_config.settings.file_watcher,
                include_patterns=app_config.settings.include_patterns,
                ignore_patterns=app_config.settings.ignore_patterns,
            )
            gui_state.watcher = watcher

            # Wrap process_all to update GUI state
            original_process_all = processor.process_all

            def wrapped_process_all():
                gui_state.set_processing(True)
                try:
                    result = original_process_all()
                    return result
                finally:
                    gui_state.set_processing(False)

            processor.process_all = wrapped_process_all

            # Run watcher (blocks until stopped)
            watcher.run_forever()
        except Exception as e:
            LOGGER.exception("File watcher error: %s", e)

    thread = threading.Thread(target=run_watcher, daemon=True, name="FileWatcher")
    thread.start()
    return thread


def run_gui_standalone(port: int = 8765, host: str = "0.0.0.0") -> None:
    """Run the GUI in standalone mode without a processor.

    This is useful for development and testing the GUI
    without a full Playbook setup.

    Args:
        port: Port to run the web server on
        host: Host to bind the web server to
    """
    suppress_nicegui_disconnect_errors()
    LOGGER.info("Running GUI in standalone mode (no processor)")
    create_app()
    ui.run(
        host=host,
        port=port,
        title="Playbook (Standalone)",
        dark=False,
        reload=True,
        show=True,
        storage_secret="playbook-gui-storage",  # Enable persistent user storage
    )


# Development entry point
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
        run_with_gui(config_path)
    else:
        run_gui_standalone()
