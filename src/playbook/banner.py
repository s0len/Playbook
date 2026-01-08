from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .config import AppConfig


@dataclass
class BannerInfo:
    version: str
    dry_run: bool
    watch_mode: bool
    verbose: bool
    trace_matches: bool
    source_dir: str
    destination_dir: str
    cache_dir: str
    enabled_sports_count: int
    notifications_enabled: bool
    plex_sync_enabled: bool
    kometa_trigger_enabled: bool


def build_banner_info(
    config: AppConfig,
    verbose: bool = False,
    trace_matches: bool = False,
) -> BannerInfo:
    """Build a BannerInfo instance from AppConfig and runtime settings."""
    enabled_sports_count = sum(1 for sport in config.sports if sport.enabled)
    notifications_enabled = bool(config.settings.notifications.targets)

    return BannerInfo(
        version=__version__,
        dry_run=config.settings.dry_run,
        watch_mode=config.settings.file_watcher.enabled,
        verbose=verbose,
        trace_matches=trace_matches,
        source_dir=str(config.settings.source_dir),
        destination_dir=str(config.settings.destination_dir),
        cache_dir=str(config.settings.cache_dir),
        enabled_sports_count=enabled_sports_count,
        notifications_enabled=notifications_enabled,
        plex_sync_enabled=config.settings.plex_sync.enabled,
        kometa_trigger_enabled=config.settings.kometa_trigger.enabled,
    )


def print_startup_banner(info: BannerInfo, console: Console) -> None:
    """Print a styled startup banner showing version and configuration."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="cyan bold", no_wrap=True)
    table.add_column("Value", style="white")

    # Version
    table.add_row("Version", f"[bold]{info.version}[/bold]")

    # Mode indicators
    mode_parts = []
    if info.dry_run:
        mode_parts.append("[yellow]DRY-RUN[/yellow]")
    if info.watch_mode:
        mode_parts.append("[cyan]WATCH[/cyan]")
    if info.verbose:
        mode_parts.append("[cyan]VERBOSE[/cyan]")
    if info.trace_matches:
        mode_parts.append("[cyan]TRACE[/cyan]")

    if mode_parts:
        table.add_row("Mode", " ".join(mode_parts))

    # Directories
    table.add_row("Source", info.source_dir)
    table.add_row("Destination", info.destination_dir)
    table.add_row("Cache", info.cache_dir)

    # Configuration summary
    table.add_row("Enabled Sports", f"[bold]{info.enabled_sports_count}[/bold]")

    # Optional features
    features = []
    if info.notifications_enabled:
        features.append("[green]Notifications[/green]")
    if info.plex_sync_enabled:
        features.append("[green]Plex Sync[/green]")
    if info.kometa_trigger_enabled:
        features.append("[green]Kometa Trigger[/green]")

    if features:
        table.add_row("Features", " · ".join(features))

    panel = Panel(
        table,
        title="[bold white]PLAYBOOK[/bold white]",
        border_style="blue",
        padding=(1, 2),
    )

    console.print()
    console.print(panel)
    console.print()
