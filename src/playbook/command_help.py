from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
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
            "Clear the processed file cache before running to reprocess all files",
            "playbook run --clear-processed-cache",
        ),
        (
            "Enable detailed match tracing for debugging pattern matches",
            "playbook run --trace-matches --trace-output /cache/traces",
        ),
        (
            "Custom log levels: DEBUG to file, INFO to console (reduces noise)",
            "playbook run --log-level DEBUG --console-level INFO",
        ),
        (
            "Use environment variables instead of CLI flags",
            "DRY_RUN=true VERBOSE=true playbook run",
        ),
        (
            "Docker: quick verification with dry-run and verbose logging",
            "docker run --rm -it -e DRY_RUN=true -e VERBOSE=true -e SOURCE_DIR=/downloads -e DESTINATION_DIR=/library -e CACHE_DIR=/cache -v /config:/config -v /downloads:/data/source -v /library:/data/destination -v /cache:/var/cache/playbook ghcr.io/s0len/playbook:latest --dry-run --verbose",
        ),
        (
            "Docker: production run with proper volume mounts",
            "docker run -d --name playbook -e TZ=UTC -e SOURCE_DIR=/downloads -e DESTINATION_DIR=/library -e CACHE_DIR=/cache -v /config:/config -v /downloads:/data/source -v /library:/data/destination -v /cache:/var/cache/playbook -v /logs:/var/log/playbook ghcr.io/s0len/playbook:latest",
        ),
        (
            "Docker: continuous watch mode for automated processing with downloaders",
            "docker run -d -e WATCH_MODE=true -e SOURCE_DIR=/downloads -e DESTINATION_DIR=/library -e CACHE_DIR=/cache -v /config:/config -v /downloads:/data/source -v /library:/data/destination -v /cache:/var/cache/playbook ghcr.io/s0len/playbook:latest --watch",
        ),
        (
            "Docker: one-time run with cache clearing",
            "docker run --rm -e CLEAR_PROCESSED_CACHE=true -e SOURCE_DIR=/downloads -e DESTINATION_DIR=/library -e CACHE_DIR=/cache -v /config:/config -v /downloads:/data/source -v /library:/data/destination -v /cache:/var/cache/playbook ghcr.io/s0len/playbook:latest --clear-processed-cache",
        ),
        (
            "Docker: dry-run with custom log directory",
            "docker run --rm -e DRY_RUN=true -e LOG_DIR=/var/log/playbook -v /config:/config -v /logs:/var/log/playbook ghcr.io/s0len/playbook:latest --dry-run",
        ),
        (
            "Python module: run from source with custom config",
            "python -m playbook.cli run --config ./playbook.yaml --dry-run",
        ),
        (
            "Python module: watch mode from local development environment",
            "python -m playbook.cli run --config ./playbook.yaml --watch --verbose",
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
            "Basic validation: check configuration file for syntax and schema errors",
            "playbook validate-config --config /config/playbook.yaml",
        ),
        (
            "Show diff against sample configuration to see what you've customized",
            "playbook validate-config --diff-sample",
        ),
        (
            "Show detailed Python tracebacks when validation fails for debugging",
            "playbook validate-config --show-trace",
        ),
        (
            "Combine diff and trace for comprehensive debugging session",
            "playbook validate-config --diff-sample --show-trace",
        ),
        (
            "Validate custom config file path (useful in multi-environment setups)",
            "playbook validate-config --config ./config/playbook.prod.yaml",
        ),
        (
            "Docker: validate configuration before starting main container",
            "docker run --rm -v /config:/config ghcr.io/s0len/playbook:latest validate-config --show-trace",
        ),
        (
            "Docker Compose: validate config as a pre-check service",
            "docker-compose run --rm playbook validate-config --config /config/playbook.yaml",
        ),
        (
            "CI/CD: GitHub Actions validation step with error reporting",
            "playbook validate-config --config ./config/playbook.yaml --show-trace || exit 1",
        ),
        (
            "CI/CD: GitLab CI validation job that fails the pipeline on errors",
            "docker run --rm -v $PWD/config:/config ghcr.io/s0len/playbook:latest validate-config --show-trace",
        ),
        (
            "CI/CD: Pre-commit hook to validate before allowing commits",
            "#!/bin/bash\nplaybook validate-config --config ./config/playbook.yaml || { echo 'Config validation failed'; exit 1; }",
        ),
        (
            "Kubernetes: validate ConfigMap before applying to cluster",
            "kubectl create configmap playbook-config --from-file=playbook.yaml --dry-run=client -o yaml | playbook validate-config --config -",
        ),
        (
            "Pre-deployment: validate config changes before rolling out to production",
            "playbook validate-config --config ./playbook.prod.yaml --diff-sample && echo 'Safe to deploy'",
        ),
        (
            "Python module: validate during development with full traceback",
            "python -m playbook.cli validate-config --config ./playbook.yaml --show-trace",
        ),
        (
            "Automated testing: validate sample config in unit tests",
            "python -m playbook.cli validate-config --config ./config/playbook.sample.yaml",
        ),
        (
            "Multi-environment: validate all configs in a loop (dev, staging, prod)",
            "for env in dev staging prod; do playbook validate-config --config ./config/playbook.$env.yaml || exit 1; done",
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
            "Basic manual trigger using configuration settings from playbook.yaml",
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
            "Trigger with verbose logging to debug connection issues and command execution",
            "playbook kometa-trigger --verbose --mode docker",
        ),
        (
            "Docker mode: trigger via 'docker run' to start a new Kometa container",
            "playbook kometa-trigger --mode docker --config /config/playbook.yaml",
        ),
        (
            "Docker mode: trigger via 'docker exec' in existing Kometa container",
            "docker exec playbook python -m playbook.cli kometa-trigger --mode docker",
        ),
        (
            "Docker mode: trigger specific libraries only (e.g., 'Sports' library)",
            "playbook kometa-trigger --mode docker --config /config/playbook.yaml",
        ),
        (
            "Docker mode: troubleshoot missing Docker socket or binary",
            "ls -la /var/run/docker.sock && which docker && playbook kometa-trigger --mode docker --verbose",
        ),
        (
            "Kubernetes mode: trigger metadata refresh after bulk imports",
            "playbook kometa-trigger --mode kubernetes --config /config/playbook.yaml",
        ),
        (
            "Kubernetes mode: trigger from within cluster with custom namespace",
            "kubectl exec -n media playbook -- python -m playbook.cli kometa-trigger --mode kubernetes",
        ),
        (
            "Kubernetes mode: monitor triggered Job completion status",
            "playbook kometa-trigger --mode kubernetes && kubectl get jobs -n media -l trigger=playbook --sort-by=.metadata.creationTimestamp",
        ),
        (
            "Kubernetes mode: cleanup old triggered Jobs after successful runs",
            "kubectl delete jobs -n media -l trigger=playbook --field-selector status.successful=1",
        ),
        (
            "Integration: automatic trigger after Playbook processes new files (configured in playbook.yaml)",
            "# Set kometa_trigger.enabled: true in config, then run:\nplaybook run --watch",
        ),
        (
            "Integration: manual metadata refresh after importing large batch of files",
            "playbook run --dry-run --verbose && playbook kometa-trigger --mode kubernetes",
        ),
        (
            "Integration: scheduled trigger via cron for daily metadata updates",
            "0 3 * * * /usr/local/bin/playbook kometa-trigger --config /config/playbook.yaml --mode docker >> /var/log/kometa-trigger.log 2>&1",
        ),
        (
            "CI/CD: test Kometa trigger in staging before production rollout",
            "playbook kometa-trigger --mode docker --config /config/playbook.staging.yaml --verbose",
        ),
        (
            "Debugging: verify Docker configuration and test trigger without side effects",
            "playbook validate-config && playbook kometa-trigger --mode docker --verbose 2>&1 | tee /tmp/trigger-debug.log",
        ),
        (
            "Debugging: check Kubernetes CronJob exists before triggering",
            "kubectl get cronjob kometa-sport -n media && playbook kometa-trigger --mode kubernetes",
        ),
        (
            "Debugging: verify RBAC permissions for Kubernetes Job creation",
            "kubectl auth can-i create jobs --namespace=media && playbook kometa-trigger --mode kubernetes --verbose",
        ),
        (
            "Production: Docker Compose integration with sidecar Kometa container",
            "docker-compose exec playbook python -m playbook.cli kometa-trigger --mode docker",
        ),
        (
            "Production: Kubernetes with custom Job name prefix for organization",
            "# Configure job_name_prefix in playbook.yaml, then:\nplaybook kometa-trigger --mode kubernetes",
        ),
        (
            "Python module: trigger from source with custom config path",
            "python -m playbook.cli kometa-trigger --config ./playbook.yaml --mode docker",
        ),
        (
            "Python module: development testing with local Kometa installation",
            "python -m playbook.cli kometa-trigger --config ./config/playbook.dev.yaml --mode docker --verbose",
        ),
        (
            "Multi-library: trigger all configured libraries after sports events complete",
            "# Configure docker_libraries or just trigger all:\nplaybook kometa-trigger --mode docker",
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
