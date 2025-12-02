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
| `--trace-matches` / `--explain` | — | `false` | Capture per-file trace JSON under `cache_dir/traces`. |
| `--trace-output PATH` | — | `cache_dir/traces` | Custom directory for trace JSONs (implies `--trace-matches`). |
| `--clear-processed-cache` | `CLEAR_PROCESSED_CACHE` | `false` | Resets processed file cache before processing. |
| `--watch` | `WATCH_MODE=true` | `settings.file_watcher.enabled` | Force watcher mode on. |
| `--no-watch` | `WATCH_MODE=false` | `false` | Disable watcher mode even if config enables it. |

Environment variables override config defaults; CLI flags override both. `SOURCE_DIR`, `DESTINATION_DIR`, and `CACHE_DIR` also override the `settings` block at runtime, which is handy for per-environment deployments.

### Mode playbooks

#### Batch runs via cron/systemd timer

Use cron (or a systemd timer) to kick off a fresh container/CLI run on a schedule. The example below dry-runs every hour and exits cleanly when finished:

```--8<-- "snippets/cron-batch-job.md"```

Keep `LOG_DIR` and `CACHE_DIR` on persistent volumes so subsequent runs stay warm.

#### Always-on watcher via systemd

When running natively on a host, wrap the CLI in a systemd service so it restarts after crashes and logs to `journalctl` while still writing `playbook.log`:

```--8<-- "snippets/systemd-watcher-service.md"```

Store secrets in `/etc/playbook.env` (referenced by `EnvironmentFile`) and keep the virtualenv pinned to a known path.

#### Kubernetes patterns

- **CronJob** – mirrors the batch run model; the container runs once and exits. Ideal for nightly/weekly cleanups.
- **Deployment / Flux HelmRelease** – keeps the watcher alive. Use `WATCH_MODE=true`, persistent cache/log PVCs, and `reloader.stakater.com/auto: "true"` so config changes hot-reload.

Examples for both live in [Getting Started](getting-started.md#option-c-kubernetes-flux-helmrelease).

### Subcommands

- `python -m playbook.cli validate-config --config … --diff-sample --show-trace`  
  CI-friendly validation that enforces schema checks and surfaces diffs against `config/playbook.sample.yaml`.
- `python -m playbook.cli kometa-trigger --config … --mode docker`  
  Triggers Kometa once without running the processor. Useful when debugging trigger failures or forcing a metadata refresh after a manual ingest.

## Logging & Observability

- Logs use a multi-line block layout (timestamp, header, aligned key/value pairs) for rapid scanning.
- INFO-level runs summarize totals per sport/source; add `--verbose`/`LOG_LEVEL=DEBUG` for per-file diagnostics.
- Each pass ends with a `Run Recap` block (duration, totals, Kometa trigger state, destination samples).
- On every start, the previous log rotates to `playbook.log.previous`. Persist `/var/log/playbook` (Docker) or whatever `LOG_DIR` you choose.
- Set `LOG_LEVEL=WARNING` (or higher) to cut down on noise for steady-state watcher deployments.
- `PLAIN_CONSOLE_LOGS=true` forces plain text output (handy for syslog collectors); `RICH_CONSOLE_LOGS=true` forces Rich formatting even when the console isn’t a TTY.
- Use separate `LOG_DIR` mounts per environment and ship the log files to your preferred log stack (Vector, Fluent Bit, Loki, etc.).

### Tracing & diagnostics

- `--trace-matches` (or `--explain`) writes JSON artifacts per processed file so you can audit regex captures, selectors, and template output.
- `--trace-output /path/to/dir` stores those JSONs somewhere other than `cache_dir/traces`.
- `--clear-processed-cache` forces Playbook to treat every file as new; pair it with `--dry-run` when validating a new config so you see complete notifications and Kometa trigger previews without touching the filesystem.
- Combine `--dry-run --verbose --trace-matches` to capture a full story: console logs, persistent logs, and JSON traces for each match.
- For watcher deployments, schedule periodic `validate-config` runs in CI so schema regressions surface before you roll containers.

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
- Before promoting a new version, run the container with `--dry-run --clear-processed-cache` against a staging copy of your downloads to confirm new pattern packs behave as expected.
- Pin tags (e.g., `ghcr.io/s0len/playbook:v1.3.1`) in production deployments, then test `:latest` or `develop` in a sandbox before rolling forward.
- Keep a copy of `playbook.sample.yaml` from the release you are running; diffs against the current sample file quickly highlight breaking config changes.

When you need to troubleshoot, jump to [Troubleshooting & FAQ](troubleshooting.md) for per-scenario guidance.
