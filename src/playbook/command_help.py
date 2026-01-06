from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(slots=True)
class CommandHelp:
    """
    Structured help content for a CLI command.

    Provides examples, environment variable documentation, and helpful tips
    for use with the RichHelpFormatter.
    """

    examples: List[Tuple[str, str]] = field(default_factory=list)
    """List of (description, command) tuples showing usage examples."""

    brief_examples: List[Tuple[str, str]] = field(default_factory=list)
    """Brief examples shown in --help (2-3 most common use cases)."""

    extended_examples: List[Tuple[str, str]] = field(default_factory=list)
    """Extended examples shown in --examples (comprehensive cookbook-style)."""

    env_vars: List[Tuple[str, str]] = field(default_factory=list)
    """List of (variable_name, description) tuples documenting environment variables."""

    tips: List[str] = field(default_factory=list)
    """List of helpful tips and best practices."""


# Help content for the 'run' command
RUN_COMMAND_HELP = CommandHelp(
    # Legacy examples field (kept for backward compatibility)
    examples=[
        (
            "Basic dry-run to preview what would happen without modifying files",
            "playbook run --dry-run --verbose",
        ),
        (
            "Run once and process all files in source directory",
            "playbook run --config /config/playbook.yaml",
        ),
        (
            "Watch mode: continuously monitor source directory for new files",
            "playbook run --watch",
        ),
    ],
    # Brief examples shown in --help
    brief_examples=[
        (
            "Basic dry-run to preview what would happen without modifying files",
            "playbook run --dry-run --verbose",
        ),
        (
            "Run once and process all files in source directory",
            "playbook run --config /config/playbook.yaml",
        ),
        (
            "Watch mode: continuously monitor source directory for new files",
            "playbook run --watch",
        ),
    ],
    # Extended examples shown in --examples
    extended_examples=[
        (
            "Basic dry-run to preview what would happen without modifying files",
            "playbook run --dry-run --verbose",
        ),
        (
            "Run once and process all files in source directory",
            "playbook run --config /config/playbook.yaml",
        ),
        (
            "Watch mode: continuously monitor source directory for new files",
            "playbook run --watch",
        ),
        (
            "Disable watch mode even if enabled in config",
            "playbook run --no-watch",
        ),
        (
            "Clear the processed file cache before running",
            "playbook run --clear-processed-cache",
        ),
        (
            "Enable detailed match tracing for debugging pattern matches",
            "playbook run --trace-matches --trace-output /cache/traces",
        ),
        (
            "Custom log levels: DEBUG to file, INFO to console",
            "playbook run --log-level DEBUG --console-level INFO",
        ),
        (
            "Docker: dry-run with verbose logging",
            "docker run --rm -e DRY_RUN=true -e VERBOSE=true -v /config:/config ghcr.io/s0len/playbook:latest",
        ),
        (
            "Docker: continuous watch mode for automated processing",
            "docker run -d -e WATCH_MODE=true -v /config:/config -v /downloads:/data/source ghcr.io/s0len/playbook:latest",
        ),
        (
            "Docker: process with custom config and clear cache",
            "docker run --rm -e CLEAR_PROCESSED_CACHE=true -v /my-config:/config -v /downloads:/data/source ghcr.io/s0len/playbook:latest",
        ),
        (
            "Python module: run from source with custom config",
            "python -m playbook.cli run --config ./playbook.yaml --dry-run",
        ),
    ],
    env_vars=[
        ("CONFIG_PATH", "Path to the YAML configuration file (default: /config/playbook.yaml)"),
        ("SOURCE_DIR", "Root directory containing downloads to process"),
        ("DESTINATION_DIR", "Library root where organized files are created"),
        ("CACHE_DIR", "Metadata cache directory (default: /data/cache)"),
        ("DRY_RUN", "When true, logs actions without writing files (true/false/1/0)"),
        ("VERBOSE", "Enable debug-level console logging (true/false/1/0)"),
        ("DEBUG", "Alias for VERBOSE (true/false/1/0)"),
        ("LOG_LEVEL", "File log level: CRITICAL, ERROR, WARNING, INFO, DEBUG (default: INFO)"),
        ("CONSOLE_LEVEL", "Console log level (defaults to LOG_LEVEL)"),
        ("LOG_FILE", "Path to the persistent log file (default: ./playbook.log)"),
        ("LOG_DIR", "Directory for log files (alternative to LOG_FILE)"),
        ("WATCH_MODE", "Enable filesystem watcher mode to continuously process new files (true/false/1/0)"),
        ("CLEAR_PROCESSED_CACHE", "Clear processed file cache before running (true/false/1/0)"),
        ("PLAIN_CONSOLE_LOGS", "Force plain text console output without Rich formatting (true/false/1/0)"),
        ("RICH_CONSOLE_LOGS", "Force Rich console output even in non-TTY environments (true/false/1/0)"),
    ],
    tips=[
        "Always test with --dry-run first to preview changes before modifying files",
        "Use --verbose to see detailed per-file processing information",
        "Enable --watch for automated processing when combined with downloaders like qBittorrent",
        "Set WATCH_MODE=true in Docker/Kubernetes for continuous operation",
        "Use --trace-matches to debug pattern matching and understand why files match or don't match",
        "The processed file cache prevents duplicate processing; use --clear-processed-cache to reprocess everything",
        "Environment variables override config file settings and CLI flags take precedence over both",
    ],
)


# Help content for the 'validate-config' command
VALIDATE_CONFIG_COMMAND_HELP = CommandHelp(
    # Legacy examples field (kept for backward compatibility)
    examples=[
        (
            "Validate configuration file for errors",
            "playbook validate-config --config /config/playbook.yaml",
        ),
        (
            "Show diff against sample configuration to see customizations",
            "playbook validate-config --diff-sample",
        ),
    ],
    # Brief examples shown in --help
    brief_examples=[
        (
            "Validate configuration file for errors",
            "playbook validate-config --config /config/playbook.yaml",
        ),
        (
            "Show diff against sample configuration to see customizations",
            "playbook validate-config --diff-sample",
        ),
    ],
    # Extended examples shown in --examples
    extended_examples=[
        (
            "Validate configuration file for errors",
            "playbook validate-config --config /config/playbook.yaml",
        ),
        (
            "Show diff against sample configuration to see customizations",
            "playbook validate-config --diff-sample",
        ),
        (
            "Show detailed tracebacks when validation fails",
            "playbook validate-config --show-trace",
        ),
        (
            "Combine diff and trace for comprehensive debugging",
            "playbook validate-config --diff-sample --show-trace",
        ),
        (
            "Docker: validate configuration in CI/CD pipeline",
            "docker run --rm -v /config:/config ghcr.io/s0len/playbook:latest validate-config --show-trace",
        ),
        (
            "CI/CD: exit with non-zero code on validation failure",
            "playbook validate-config || exit 1",
        ),
        (
            "Python module: validate from source",
            "python -m playbook.cli validate-config --config ./playbook.yaml",
        ),
    ],
    env_vars=[
        ("CONFIG_PATH", "Path to the YAML configuration file to validate (default: /config/playbook.yaml)"),
    ],
    tips=[
        "Run validate-config before deploying configuration changes to catch errors early",
        "Use --diff-sample to compare your config against the sample and identify customizations",
        "Add --show-trace to see full Python tracebacks for debugging complex validation errors",
        "Integrate into CI/CD pipelines to automatically validate config changes in pull requests",
        "The validator checks both YAML syntax and Playbook-specific configuration requirements",
    ],
)


# Help content for the 'kometa-trigger' command
KOMETA_TRIGGER_COMMAND_HELP = CommandHelp(
    # Legacy examples field (kept for backward compatibility)
    examples=[
        (
            "Manually trigger Kometa using configuration settings",
            "playbook kometa-trigger --config /config/playbook.yaml",
        ),
        (
            "Override trigger mode to use Docker instead of Kubernetes",
            "playbook kometa-trigger --mode docker",
        ),
    ],
    # Brief examples shown in --help
    brief_examples=[
        (
            "Manually trigger Kometa using configuration settings",
            "playbook kometa-trigger --config /config/playbook.yaml",
        ),
        (
            "Override trigger mode to use Docker instead of Kubernetes",
            "playbook kometa-trigger --mode docker",
        ),
    ],
    # Extended examples shown in --examples
    extended_examples=[
        (
            "Manually trigger Kometa using configuration settings",
            "playbook kometa-trigger --config /config/playbook.yaml",
        ),
        (
            "Override trigger mode to use Docker instead of Kubernetes",
            "playbook kometa-trigger --mode docker",
        ),
        (
            "Override trigger mode to use Kubernetes",
            "playbook kometa-trigger --mode kubernetes",
        ),
        (
            "Trigger with verbose logging to debug issues",
            "playbook kometa-trigger --verbose",
        ),
        (
            "Docker: trigger Kometa from within Playbook container",
            "docker exec playbook python -m playbook.cli kometa-trigger --mode docker",
        ),
        (
            "Kubernetes: manually trigger metadata refresh after bulk imports",
            "kubectl exec -n media playbook -- python -m playbook.cli kometa-trigger --mode kubernetes",
        ),
        (
            "Python module: trigger from source with custom config",
            "python -m playbook.cli kometa-trigger --config ./playbook.yaml --mode docker",
        ),
    ],
    env_vars=[
        ("CONFIG_PATH", "Path to the YAML configuration file (default: /config/playbook.yaml)"),
        ("LOG_LEVEL", "File log level: CRITICAL, ERROR, WARNING, INFO, DEBUG (default: INFO)"),
        ("CONSOLE_LEVEL", "Console log level (defaults to LOG_LEVEL)"),
        ("LOG_FILE", "Path to the persistent log file (default: ./playbook.log)"),
        ("LOG_DIR", "Directory for log files (alternative to LOG_FILE)"),
    ],
    tips=[
        "Use --mode to override the trigger mode configured in playbook.yaml",
        "In Docker mode, ensure the Docker socket is mounted and accessible",
        "In Kubernetes mode, ensure the service account has permissions to create Jobs",
        "Kometa trigger runs automatically after processing when enabled in config",
        "Manual triggering is useful for testing integration or refreshing metadata on demand",
        "Check logs for detailed output from the Kometa execution",
    ],
)


# Command help registry mapping command names to their help content
COMMAND_HELP: Dict[str, CommandHelp] = {
    "run": RUN_COMMAND_HELP,
    "validate-config": VALIDATE_CONFIG_COMMAND_HELP,
    "kometa-trigger": KOMETA_TRIGGER_COMMAND_HELP,
}


def get_command_help(command: str) -> CommandHelp:
    """
    Retrieve help content for a specific command.

    Args:
        command: Command name (run, validate-config, kometa-trigger)

    Returns:
        CommandHelp instance with examples, environment variables, and tips

    Raises:
        KeyError: If command is not recognized
    """
    return COMMAND_HELP[command]
