# Operations & Run Modes

The CLI powers every deployment path—Docker entrypoint, Kubernetes container, or ad-hoc batch run. This guide covers run modes, flags, logging, and day-2 operations.

## Run Modes

| Mode | How to enable | Best for |
|------|---------------|----------|
| Batch | Default CLI behavior (`python -m playbook.cli`) | One-off reorg runs and cron jobs |
| Watcher | `--watch` flag or `WATCH_MODE=true` (also controlled via `settings.file_watcher.enabled`) | Always-on ingestion, reacts to filesystem events |
| Validate | `python -m playbook.cli validate-config --config ...` | CI gates + local smoke tests |

Batch mode exits after a single pass. Watcher mode keeps the process alive, listening for `create`, `modify`, and `move` events underneath `source_dir` (or `file_watcher.paths`). Use `file_watcher.debounce_seconds` to batch bursts of events, and `file_watcher.reconcile_interval` to force periodic full scans in case the platform drops events.

## CLI Flags & Environment Variables

| CLI Flag | Environment | Default | Notes |
|----------|-------------|---------|-------|
| `--config PATH` | `CONFIG_PATH` | `/config/playbook.yaml` | Path to the YAML config. |
| `--dry-run` | `DRY_RUN` | Inherits `settings.dry_run` | Force no-write mode. |
| `--verbose` | `VERBOSE` / `DEBUG` | `false` | Enables console `DEBUG` output. |
| `--log-level LEVEL` | `LOG_LEVEL` | `INFO` (or `DEBUG` with `--verbose`) | File log level. |
| `--console-level LEVEL` | `CONSOLE_LEVEL` | Matches file level | Console log level. |
| `--log-file PATH` | `LOG_FILE` / `LOG_DIR` | `./playbook.log` | Rotates to `*.previous` on start. |
| `--clear-processed-cache` | `CLEAR_PROCESSED_CACHE` | `false` | Resets processed file cache before processing. |
| `--watch` | `WATCH_MODE=true` | `settings.file_watcher.enabled` | Force watcher mode on. |
| `--no-watch` | `WATCH_MODE=false` | `false` | Disable watcher mode even if config enables it. |

Environment variables override config defaults; CLI flags override both.

## Logging & Observability

- Logs use a multi-line block layout (timestamp, header, aligned key/value pairs) for rapid scanning.
- INFO-level runs summarize totals per sport/source; add `--verbose`/`LOG_LEVEL=DEBUG` for per-file diagnostics.
- Each pass ends with a `Run Recap` block (duration, totals, Kometa trigger state, destination samples).
- On every start, the previous log rotates to `playbook.log.previous`. Persist `/var/log/playbook` (Docker) or whatever `LOG_DIR` you choose.
- Set `LOG_LEVEL=WARNING` (or higher) to cut down on noise for steady-state watcher deployments.

## Monitoring Hooks

- `settings.kometa_trigger` nudges Kometa after each ingest cycle. Modes: `kubernetes` (clone a CronJob) or `docker` (run/exec a container). Detailed examples live in [Integrations](integrations.md#kometa-triggering).
- `notifications.targets` can ping Autoscan immediately after new files appear so Plex rescans folders without manual input.
- Add `notifications.targets` entries for Discord/Slack/webhooks to receive summaries per run or per day.

## Directory Conventions

Hardlinks are the default action, so you retain the original downloads while presenting a clean Plex library. A typical layout after a Formula 1 weekend:

```text
Formula 1 2025/
└── 01 Bahrain Grand Prix/
    ├── Formula 1 - S01E01 - Free Practice 1.mkv
    ├── Formula 1 - S01E02 - Qualifying.mkv
    ├── Formula 1 - S01E03 - Sprint.mkv
    └── Formula 1 - S01E04 - Race.mkv
```

Switch `link_mode` to `copy` or `symlink` globally or per sport when working across filesystems or SMB/NFS shares.

## Upgrades & Backups

- Docker: pull the latest tag (`docker pull ghcr.io/s0len/playbook:latest`) and recreate the container. Keep `/config`, `/var/log/playbook`, and cache directories mounted so runs resume instantly.
- Kubernetes: bump the HelmRelease image tag and let Flux reconcile. Cluster CronJobs/Deployments inherit the latest container automatically.
- Python: upgrade the virtualenv (`pip install -U -r requirements.txt`).
- Back up `playbook.yaml`, notification secrets, and metadata caches if you want to preserve warm-start performance. Everything else is auto-generated.

When you need to troubleshoot, jump to [Troubleshooting & FAQ](troubleshooting.md) for per-scenario guidance.
