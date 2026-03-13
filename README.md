# Playbook

[![License: GPLv3](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776ab.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Fs0len%2Fplaybook-0db7ed.svg?logo=docker&logoColor=white)](https://github.com/users/s0len/packages/container/package/playbook)
[![Docs](https://img.shields.io/badge/docs-View%20Documentation-0f172a.svg?logo=book&logoColor=white)](https://s0len.github.io/Playbook/)

**Sonarr for Sports** – automated sports file matching, naming, and organization for Plex.

Playbook watches your downloads, identifies what each file actually is (race, match, event), then creates clean TV-style files and folders in your media library.

## What Playbook Solves

Sports releases are messy:
- Inconsistent naming (`F1`, `Formula.1`, `R05`, `Round 5`, etc.)
- Different season models by sport (events, rounds, weeks)
- Manual renaming and moving every day

Playbook fixes that by combining:
- Metadata-driven matching via TVSportsDB API (show/season/episode model)
- Built-in sport pattern packs (F1, Formula E, MotoGP, UFC, NFL, NBA, NHL, Premier League, Champions League, IndyCar, WSBK, WTA, Figure Skating, and more)
- Smart linking (`hardlink`, `copy`, `symlink`) into your Plex structure
- Quality-based upgrade scoring (resolution, framerate, codec, source, release group)
- Optional notifications (Discord, Slack, Webhook, Email) and Plex/Autoscan integrations

## TL;DR Quick Start (Docker Compose)

This is the easiest first run. Copy, edit two paths, and start.

```yaml
services:
  playbook:
    image: ghcr.io/s0len/playbook:latest
    container_name: playbook
    restart: unless-stopped
    environment:
      TZ: UTC
      GUI_PORT: 8765
      CONFIG_PATH: /config/config.yaml
    ports:
      - "8765:8765"
    volumes:
      - ./config:/config              # config + persistent state db
      - /path/to/downloads:/data/source
      - /path/to/library:/data/destination
      - ./cache:/data/cache           # metadata cache (can be tmpfs if desired)
```

Start it:

```bash
docker compose up -d
```

Open GUI:

```text
http://<host-ip>:8765
```

On first run, Playbook auto-creates `/config/config.yaml` if missing. You can then configure everything in the GUI and click Save.

## Minimal `docker run` Alternative

```bash
docker run -d \
  --name playbook \
  -p 8765:8765 \
  -e TZ=UTC \
  -e GUI_PORT=8765 \
  -e CONFIG_PATH=/config/config.yaml \
  -v ./config:/config \
  -v /path/to/downloads:/data/source \
  -v /path/to/library:/data/destination \
  -v ./cache:/data/cache \
  ghcr.io/s0len/playbook:latest
```

## First-Run Checklist

1. Open `Settings` in the GUI.
2. Verify `Source Directory` and `Destination Directory`.
3. Keep default `State Directory` persistent (`/config/state`).
4. Enable the sports you want.
5. Click `Save`.
6. Trigger processing from dashboard or wait for watcher mode.

## Storage Model (Important)

Playbook separates persistent state from cache:

- `state_dir` (default: `/config/state`): SQLite databases and durable app state. **Must persist** across restarts.
- `cache_dir` (default: `/data/cache`): Metadata cache and trace artifacts. Disposable/temporary.

This means you can keep `cache_dir` disposable/temporary while preserving match history and manual overrides in `state_dir`.

## Table of Contents

- [Playbook](#playbook)
- [What Playbook Solves](#what-playbook-solves)
- [TL;DR Quick Start (Docker Compose)](#tldr-quick-start-docker-compose)
- [Minimal `docker run` Alternative](#minimal-docker-run-alternative)
- [First-Run Checklist](#first-run-checklist)
- [Storage Model (Important)](#storage-model-important)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Configuration Deep Dive](#configuration-deep-dive)
- [Run Modes & CLI](#run-modes--cli)
- [Plex Library Setup](#plex-library-setup)
- [Adding New Sports](#adding-new-sports)
- [Troubleshooting & FAQ](#troubleshooting--faq)

## Kubernetes (Flux HelmRelease)

Use the [bjw-s/app-template](https://github.com/bjw-s/helm-charts/tree/main/charts/other/app-template) chart with Flux to keep a cluster deployment reconciled. The example below mirrors the Docker settings and keeps persistent state under `/settings`:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/bjw-s-labs/helm-charts/main/charts/other/app-template/schemas/helmrelease-helm-v2.schema.json
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: &app playbook
spec:
  interval: 30m
  chartRef:
    kind: OCIRepository
    name: app-template
  install:
    remediation:
      retries: 3
  upgrade:
    cleanupOnFail: true
    remediation:
      strategy: rollback
      retries: 3

  values:
    serviceAccount:
      playbook: {}

    controllers:
      playbook:
        serviceAccount:
          identifier: playbook
        type: deployment
        annotations:
          reloader.stakater.com/auto: "true"
        containers:
          app:
            image:
              repository: ghcr.io/s0len/playbook
              tag: develop  # Pin to a digest for production: tag: develop@sha256:...
              pullPolicy: Always
            env:
              CONFIG_PATH: /settings/config.yaml
              SOURCE_DIR: /data/torrents/sport
              DESTINATION_DIR: /data/media/sport
              CACHE_DIR: /settings/cache
              STATE_DIR: /settings/state
              LOG_DIR: /tmp
              LOG_LEVEL: INFO
              GUI_PORT: &port 8765
              PLEX_URL: http://plex:32400
              PLEX_LIBRARY_NAME: Sport
            envFrom:
              - secretRef:
                  name: playbook-secret  # DISCORD_WEBHOOK_URL, PLEX_TOKEN, etc.
            probes:
              startup:
                enabled: true
                custom: true
                spec:
                  httpGet:
                    path: /healthz
                    port: *port
                  initialDelaySeconds: 10
                  periodSeconds: 5
                  failureThreshold: 30
              liveness:
                enabled: true
                custom: true
                spec:
                  httpGet:
                    path: /healthz
                    port: *port
                  periodSeconds: 15
                  failureThreshold: 5
              readiness:
                enabled: true
                custom: true
                spec:
                  httpGet:
                    path: /healthz
                    port: *port
                  periodSeconds: 10
                  failureThreshold: 3

    service:
      app:
        controller: *app
        ports:
          http:
            port: *port

    route:
      app:
        hostnames:
          - "{{ .Release.Name }}.${SECRET_DOMAIN}"
        parentRefs:
          - name: envoy-internal
            namespace: network
            sectionName: https

    defaultPodOptions:
      automountServiceAccountToken: true
      enableServiceLinks: false
      securityContext:
        runAsUser: 568
        runAsGroup: 568
        runAsNonRoot: true
        fsGroup: 568
        fsGroupChangePolicy: OnRootMismatch

    persistence:
      settings:
        existingClaim: playbook-settings   # 1Gi ceph-block PVC
        globalMounts:
          - path: /settings
      tmp:
        type: emptyDir
        medium: Memory
        globalMounts:
          - path: /tmp
      data:
        type: nfs
        server: "${TRUENAS_IP}"
        path: /mnt/rust/data
        globalMounts:
          - path: /data
```

Quick checklist:

- Create a `playbook-secret` with sensitive values (`kubectl create secret generic playbook-secret --from-literal=DISCORD_WEBHOOK_URL=... --from-literal=PLEX_TOKEN=...`), or use an ExternalSecret backed by 1Password/Vault/etc.
- Persist `/settings` (PVC) for the SQLite state databases. Cache lives under the same PVC in this example.
- Enable `file_watcher.enabled` (or set `WATCH_MODE=true`) to keep Playbook running continuously; leave it disabled for ad-hoc batch runs.
- Add `reloader.stakater.com/auto: "true"` to hot-reload when the config map or secrets change.
- Set `fsGroupChangePolicy: OnRootMismatch` for Ceph RBD PVCs to avoid slow recursive permission changes.

## Architecture at a Glance

Under the hood, Playbook follows this flow:

```text
┌─────────────────┐   fetch + cache    ┌─────────────────────┐
│ TVSportsDB API  │ ──────────────────▶ │ Metadata Normalizer │
└─────────────────┘                     └────────┬────────────┘
                                                 │ normalized Show/Season/Episode
                                         ┌───────▼────────┐
   source files + globs + aliases        │ Matching Engine │
────────────────────────────────────────▶│  (regex + fuzzy)│
                                         └───────┬────────┘
                                                 │ context (season, episode, templates)
                                         ┌───────▼────────┐
                                         │ Templating     │
                                         │ & Sanitization │
                                         └───────┬────────┘
                                                 │ destination path
                                         ┌───────▼────────┐
                                         │ Link/Copy/Sym  │
                                         └────────────────┘
```

1. **Metadata fetch & cache**: Playbook fetches show/season/episode data from the [TVSportsDB](https://tvsportsdb.com) REST API via `httpx`, caches responses in a SQLite store with TTL and ETag support. Legacy YAML URL metadata is still supported for backwards compatibility.
2. **Normalization**: structured dataclasses infer round numbers, preserve summaries, and attach aliases (including team aliases for sports like NHL and Premier League).
3. **Matching**: regex capture groups, alias tables, and fuzzy matching (rapidfuzz) link filenames to metadata episodes.
4. **Templating**: rich context feeds customizable templates for root folders, season directories, and filenames.
5. **Action**: files are hardlinked (default), copied, or symlinked into the library, with quality-based upgrade rules.

## Configuration Deep Dive

Start with `config/config.sample.yaml`. The schema mirrors `playbook.config` dataclasses.

### 1. Global Settings

| Field | Description | Default |
|-------|-------------|---------|
| `source_dir` | Root directory containing downloads to normalize. | `/data/source` |
| `destination_dir` | Library root where organized folders/files are created. | `/data/destination` |
| `cache_dir` | Metadata cache directory. Safe to delete to force refetch. | `/var/cache/playbook` |
| `state_dir` | Persistent state directory for SQLite DBs and durable runtime state. | `/config/state` |
| `theme` | GUI color theme. | `swizzin` |
| `dry_run` | When `true`, logs intent but skips filesystem writes. | `false` |
| `link_mode` | Default link behavior: `hardlink`, `copy`, or `symlink`. | `hardlink` |
| `use_default_sports` | Auto-load all built-in sports from pattern templates. | `true` |
| `disabled_sports` | List of sport IDs to exclude from defaults (e.g. `["formula_e", "moto2"]`). | `[]` |
| `force_reprocess` | Bypass processed-file database and reprocess all files. | `false` |
| `include_patterns` | Only process files matching these globs (empty = all). E.g. `["**/*.mkv", "**/*.mp4"]`. | `[]` |
| `ignore_patterns` | Skip files matching these globs. E.g. `["*sample*", "*.part"]`. | `[]` |
| `file_watcher.enabled` | When `true`, Playbook keeps running and reacts to filesystem events; when `false`, a single pass and exit. | `false` |
| `file_watcher.paths` | Directories to observe; defaults to `source_dir` when empty. | `[]` |
| `file_watcher.debounce_seconds` | Minimum seconds between watcher-triggered runs. | `5` |
| `file_watcher.reconcile_interval` | Forces a full scan every _N_ seconds even if no events arrive. | `900` |
| `destination.*` | Default templates for root folder, season folder, and filename. | See sample |

### 2. Integrations

The `integrations` section configures direct connections to media servers. These are separate from notifications — integrations interact with APIs, while notifications alert users.

#### Plex Integration

```yaml
settings:
  integrations:
    plex:
      url: ${PLEX_URL:-http://plex:32400}
      token: ${PLEX_TOKEN:-}
      library_name: ${PLEX_LIBRARY_NAME:-Sports}

      # Sync metadata (titles, summaries, posters) from TVSportsDB to Plex
      metadata_sync:
        enabled: false
        timeout: 15
        scan_wait: 5        # Seconds to wait after triggering library scan
        lock_poster_fields: false  # Prevent Plex from overwriting custom posters

      # Trigger Plex partial library scan when files are linked
      scan_on_activity:
        enabled: false
        rewrite: []          # Path mapping if Plex sees different mount paths
          # - from: /data/destination
          #   to: /mnt/plex/media
```

**Metadata Sync** pushes titles, sort titles, summaries, posters, and backgrounds from TVSportsDB to Plex. It uses fingerprint-based change detection to only update what has changed, and preserves Plex title casing.

**Scan on Activity** triggers partial Plex library scans via the Plex API whenever files are linked, so Plex picks up new files immediately without waiting for scheduled scans.

#### Autoscan Integration

```yaml
settings:
  integrations:
    autoscan:
      enabled: false
      url: ${AUTOSCAN_URL:-http://autoscan:3030}
      trigger: manual
      username: ${AUTOSCAN_USERNAME:-}
      password: ${AUTOSCAN_PASSWORD:-}
      rewrite: []
```

Autoscan support mirrors the [manual trigger endpoint](https://github.com/Cloudbox/autoscan?tab=readme-ov-file#manual): Playbook issues a `POST /triggers/<name>?dir=...` call with the directory that just received a processed file.

### 3. Notifications

```yaml
settings:
  notifications:
    scan_summary: true     # Send a summary after each scan with activity
    targets:
      - type: discord
        webhook_env: DISCORD_WEBHOOK_URL
        # mentions:
        #   formula1: "<@&123456789>"
      # - type: slack
      #   webhook_url: https://hooks.slack.com/...
      # - type: webhook
      #   url: https://example.com/webhook
      # - type: email
      #   smtp_host: smtp.gmail.com
      # - type: plex_scan      # Alternative way to configure Plex scans
      # - type: autoscan       # Alternative way to configure Autoscan
```

Supported `type` values:

- `discord` — Rich embeds with optional per-sport mentions
- `slack` — Simple text payload, optional template
- `webhook` — Generic JSON payload, fully templatable
- `email` — SMTP with configurable subject/body templates
- `autoscan` — Ping Autoscan to rescan a directory (alternative to `integrations.autoscan`)
- `plex_scan` (or `plex`) — Trigger Plex partial library scans (alternative to `integrations.plex.scan_on_activity`)

> **Note:** If you configure Plex or Autoscan under `integrations`, Playbook auto-creates the corresponding notification targets. You only need entries under `notifications.targets` if you want to override settings or use multiple targets.

#### Discord mentions

Use `notifications.mentions` to opt specific Discord roles or users into certain sports. Entries are keyed by the sport's ID (plus an optional `default` fallback) and the value is any mentionable string (`<@&ROLE_ID>`, `@here`, etc.). Keys can include shell-style wildcards (e.g. `formula1_*`), and Playbook automatically falls back to the base ID before any variant suffix (`premier_league` also covers `premier_league_2025_26`). Mentions are prepended to notification messages, so subscribers only get pinged for the sports they care about:

```yaml
notifications:
  mentions:
    premier_league: "<@&123456789012345678>"
    formula1: "<@&222333444555666777>"   # Automatically applies to formula1_2025, formula1_2026, etc.
    default: "@everyone"                 # optional fallback when no explicit entry exists
```

`webhook_env` tells Playbook to read the runtime environment for the URL, so you can mount a Kubernetes/Docker secret as env vars without ever writing the secret into the ConfigMap. If you already have your own templating flow you can continue to use `webhook_url` with `${VAR}` substitution; both options are supported.

### 4. Quality Profile

Playbook can score files and automatically upgrade to higher-quality releases when better versions appear.

```yaml
settings:
  quality_profile:
    enabled: false
    scoring:
      resolution:
        2160p: 400
        1080p: 300
        720p: 200
      source:
        webdl: 90
        webrip: 70
        hdtv: 50
      frame_rate:
        "60": 100
        "50": 75
      codec:
        x265: 25
        x264: 0
      bit_depth:
        "10": 25
      audio:
        atmos: 40
        ddp51: 25
        aac: 0
      broadcaster:
        f1tv: 50
        sky: 30
      release_group: {}
        # mwr: 50
        # verum: 40
      proper_bonus: 50
      repack_bonus: 50
      hdr_bonus: 50
    # cutoff: 350     # Stop upgrading at this score
    # min_score: 100  # Reject files below this score
```

Scoring dimensions: `resolution`, `source`, `frame_rate`, `codec`, `bit_depth`, `audio`, `broadcaster`, `release_group`, plus bonuses for `proper`, `repack`, and `hdr`. Quality profiles can be set globally or overridden per-sport.

### 5. TVSportsDB

Playbook fetches metadata from the [TVSportsDB](https://tvsportsdb.com) REST API. Configuration is optional — defaults work for most users:

```yaml
settings:
  tvsportsdb:
    base_url: http://localhost:8000   # Default API endpoint
    ttl_hours: 2                      # Cache TTL
    timeout: 30                       # Request timeout in seconds
```

Sports reference metadata via `show_slug` or `show_slug_template` instead of raw YAML URLs:

```yaml
sports:
  - id: formula1
    show_slug_template: "formula-1-{year}"   # Dynamic: year captured from filename
  - id: nba
    show_slug: "nba-2025-2026"               # Static: single season
```

> **Legacy:** The `metadata.url` / `metadata.show_key` format still works for backwards compatibility but is deprecated.

### 6. Sport Entries

All built-in sports are **enabled by default** — most users only need to configure directories and integrations. To customize, add entries to the `sports` list:

```yaml
sports:
  - id: formula1
    quality_profile:
      enabled: true
      scoring:
        release_group:
          mwr: 100
          smcgill1969: 80

  - id: my_custom_sport
    name: My Sport
    show_slug: "my-sport-2025"
    source_globs: ["MySport.*"]
    pattern_sets: [my_sport]
```

Key fields:

- `enabled`: toggle sports on/off without deleting them.
- `show_slug` / `show_slug_template`: TVSportsDB metadata reference.
- `source_globs` / `extra_source_globs` / `disabled_source_globs`: control which files are considered for this sport.
- `source_extensions`: file extensions to match (default: `.mkv`, `.mp4`, `.ts`, `.m4v`, `.avi`).
- `allow_unmatched`: downgrade pattern failures to informational logs (no warnings).
- `link_mode`: override global link behavior for a specific sport.
- `quality_profile`: per-sport quality scoring override.
- `team_alias_map`: TVSportsDB team alias map for team-based sports (e.g. NHL, Premier League).
- `season_overrides`: force season numbers for exhibitions/pre-season events.

### 7. Pattern Matching

- **`regex`** – Must supply the capture groups consumed by selectors and templates (e.g., `round`, `session`, `location`).
- **`season_selector`** – Maps captures to a season. Supported modes: `round`, `key`, `title`, `sequential`, `date`. Add `offset` or `mapping` for fine-grained control.
- **`episode_selector`** – Chooses which capture identifies an episode. `allow_fallback_to_title` lets the matcher fall back to fuzzy title comparisons, and `default_value` forces a canonical session when the regex doesn't capture one (useful for release groups that omit `Prelims`/`Main Card` tags).
- **`session_aliases`** – Augment metadata aliases with release-specific tokens (case-insensitive, normalized).
- **`priority`** – Lower numbers win when multiple patterns match the same file (defaults to `100`).
- **`destination_*` overrides** – Apply sport- or pattern-specific templates without touching global settings.

Built-in pattern sets: the project ships curated pattern packs for Formula 1, Formula E, IndyCar, MotoGP, Moto2, Moto3, World Superbike, World Supersport, World Supersport 300, Isle of Man TT, UFC, NFL, NBA, NHL, Premier League, UEFA Champions League, ISU Figure Skating, Figure Skating Grand Prix, and WTA. Reference them from a sport entry via:

```yaml
pattern_sets:
  - formula1
```

You can still inline `file_patterns` (alone or in addition to templates) for overrides or experiments. Review `src/playbook/pattern_templates.yaml` for the complete list and structure.

### 8. Destination Templating

Templates accept rich context built from the match:

| Key | Meaning |
|-----|---------|
| `sport_id`, `sport_name` | Sport metadata from the config. |
| `show_title`, `show_key` | Raw and display titles from the metadata feed. |
| `season_title`, `season_number`, `season_round`, `season_year` | Season fields with overrides applied. |
| `episode_title`, `episode_number`, `episode_summary`, `episode_originally_available` | Episode details and optional air date (`YYYY-MM-DD`). |
| `location`, `session`, `round`, … | Any capture group from the regex. |
| `source_filename`, `source_stem`, `extension`, `suffix`, `relative_source` | Safe access to the original file name and path components. |

Filename components are sanitized automatically (lowercasing dangerous characters, trimming whitespace, removing forbidden characters).

### 9. Variants & Reuse

Reuse a base sport definition across seasons or release groups using `variants`:

```yaml
- id: indycar
  name: IndyCar
  metadata:
    url: https://example.com/indycar/base.yaml
  variants:
    - year: 2024
      metadata:
        url: https://example.com/indycar-2024.yaml
    - year: 2025
      metadata:
        url: https://example.com/indycar-2025.yaml
```

Each variant inherits the base config, tweaks fields from the variant block, and receives an auto-generated `id`/`name` when not explicitly set.

## Run Modes & CLI

`python -m playbook.cli` powers both the Docker entrypoint and local runs.

| CLI Flag | Environment | Default | Notes |
|----------|-------------|---------|-------|
| `--config PATH` | `CONFIG_PATH` | `/config/config.yaml` | Path to the YAML config. |
| `--dry-run` | `DRY_RUN` | Inherits `settings.dry_run` | Force no-write mode. |
| `--verbose` | `VERBOSE` / `DEBUG` | `false` | Enables console DEBUG output. |
| `--log-level LEVEL` | `LOG_LEVEL` | `INFO` (or `DEBUG` with `--verbose`) | File log level. |
| `--console-level LEVEL` | `CONSOLE_LEVEL` | matches file level | Console log level. |
| `--log-file PATH` | `LOG_FILE` / `LOG_DIR` | `./playbook.log` | Rotates to `*.previous` on start. |
| `--clear-processed-cache` | `CLEAR_PROCESSED_CACHE` | `false` | Reset processed file cache before processing. |
| `--force-reprocess` | `FORCE_REPROCESS` | `false` | Bypass processed-file database and reprocess all files. |
| `--trace-matches` / `--explain` | — | `false` | Capture detailed match traces as JSON artifacts. |
| `--trace-output PATH` | — | `cache_dir/traces` | Directory for trace JSON files (implies `--trace-matches`). |
| `--watch` | `WATCH_MODE=true` | `settings.file_watcher.enabled` | Force filesystem watcher mode. |
| `--no-watch` | `WATCH_MODE=false` | `false` | Disable watcher mode even if the config enables it. |
| `--gui` | `GUI_ENABLED=true` | `true` | Enable web GUI mode (enabled by default). |
| `--no-gui` | `GUI_ENABLED=false` | `false` | Disable GUI and run CLI-only processing. |
| `--gui-port PORT` | `GUI_PORT` | `8765` | GUI web port. |
| `--gui-host HOST` | `GUI_HOST` | `0.0.0.0` | Host to bind GUI to. |
| `--examples` | — | — | Show cookbook-style examples for any subcommand and exit. |

Environment variables always win over config defaults, and CLI flags win over environment variables.

Additional environment variables:

| Variable | Description |
|----------|-------------|
| `SOURCE_DIR` | Override `settings.source_dir` |
| `DESTINATION_DIR` | Override `settings.destination_dir` |
| `CACHE_DIR` | Override `settings.cache_dir` |
| `STATE_DIR` | Override `settings.state_dir` |
| `GUI_THEME` / `PLAYBOOK_THEME` | Override `settings.theme` |
| `PLEX_URL` | Plex server URL (fallback for integrations config) |
| `PLEX_TOKEN` | Plex authentication token |
| `PLEX_LIBRARY_NAME` | Plex library name |
| `PLEX_LIBRARY_ID` | Plex library section ID |
| `DISCORD_WEBHOOK_URL` | Discord webhook (used by `webhook_env` default) |
| `PLAIN_CONSOLE_LOGS` | Force plain-text console output (no Rich formatting) |
| `RICH_CONSOLE_LOGS` | Force Rich console output even in non-interactive terminals |

#### Getting Help

Playbook features **rich, color-formatted help** with practical examples for every command. Use `--help` for quick reference or `--examples` for a comprehensive cookbook-style guide:

```bash
# Main help with all available commands
playbook --help

# Command-specific help with brief examples
playbook run --help
playbook validate-config --help

# Extended examples and usage patterns
playbook run --examples
playbook validate-config --examples
```

The help output includes:
- **Usage examples** – Real-world commands you can copy-paste
- **Environment variables** – Alternative ways to configure options
- **Tips & best practices** – Common workflows and gotchas
- **Docker variants** – How to run the same command in containers

All help content is formatted with colors and icons for easy scanning. On non-interactive terminals (CI/CD, redirected output), Playbook automatically falls back to plain text.

### Config Validation

Preflight your YAML before running the processor:

```bash
python -m playbook.cli validate-config --config /config/config.yaml --diff-sample
```

The validator enforces the JSON schema, confirms referenced pattern sets exist, and then calls the same loader used by the runtime. Add `--show-trace` to surface Python tracebacks for deeper debugging. `--diff-sample` compares your file to `config/config.sample.yaml` to highlight customizations. Use `--no-suggestions` for cleaner output without fix suggestions.

Continuous mode example:

```bash
docker run -d \
  -e WATCH_MODE=true \
  -p 8765:8765 \
  ghcr.io/s0len/playbook:latest
```

Playbook stays alive and reruns automatically whenever the watcher observes filesystem changes (or when the reconcile timer forces a full scan). Use `--no-watch` (or `WATCH_MODE=false`) for single-pass batch runs.

## Logging & Observability

- Log entries use a multi-line block layout (timestamp + header + aligned key/value pairs) so dense sections breathe.
- INFO-level runs show grouped counts per sport/source; add `--verbose`/`LOG_LEVEL=DEBUG` to expand into per-file diagnostics.
- Each pass ends with a `Run Recap` block (duration, totals, destination samples) for quick scanning.
- On each run, the previous log rotates to `playbook.log.previous`, and `LOG_DIR=/var/log/playbook` keeps files persistent.

## Directory Conventions

A typical library after one Formula 1 weekend might look like:

```text
Formula 1 2025/
└── 01 Bahrain Grand Prix/
    ├── Formula 1 - S01E01 - Free Practice 1.mkv
    ├── Formula 1 - S01E02 - Qualifying.mkv
    ├── Formula 1 - S01E03 - Sprint.mkv
    └── Formula 1 - S01E04 - Race.mkv
```

Hardlinks preserve disk space; switch to `copy` or `symlink` when cross-filesystem moves are required.

## Downloading Sports with Autobrr

Playbook does **not** download anything itself – it expects files to appear in `SOURCE_DIR` from a downloader (qBittorrent, Deluge, etc.). One way to automate this is with [Autobrr](https://github.com/autobrr/autobrr).

Below is one approach using **Autobrr filters** and regexes targeted at specific sports and release groups.

### Basic Autobrr setup

For each sport you care about:

1. **Create a filter** in Autobrr (e.g. `F1 1080p MWR`, `EPL 1080p NiGHTNiNJAS`, etc.).
2. Select the trackers where your sports are available.
3. Under **Advanced → Release names → Match releases**, paste a regex that:
   - matches the sport name and year
   - restricts to the resolution you want (e.g. `1080p`)
   - optionally restricts to specific release groups (e.g. `MWR`, `NiGHTNiNJAS`, `DNU`, `GAMETiME`, `VERUM`).

### Example regexes

These are examples that pair well with the built-in pattern packs and metadata feeds:

```text
# Premier League (EPL) 1080p releases by NiGHTNiNJAS
epl.*1080p.*nightninjas

# Formula 1 multi-session weekends by MWR
(F1|Formula.*1).*\d{4}.Round\d+.*[^.]+\.*?(Drivers.*Press.*Conference|Weekend.*Warm.*Up|FP\d?|Practice|Sprint.Qualifying|Sprint|Qualifying|Pre.Qualifying|Post.Qualifying|Race|Pre.Race|Post.Race|Sprint.Race|Feature.*Race).*1080p.*MWR

# Formula E by MWR
formulae\.\d{4}\.round\d+\.(?:[A-Za-z]+(?:\.[A-Za-z]+)?)\.(?:preview.show|qualifying|race)\..*h264.*-mwr

# IndyCar by MWR
indycar.*\d{4}\.round\d+\.(?:[A-Za-z]+(?:\.[A-Za-z]+)?)\.(?:qualifying|race)\..*h264.*-MWR

# Isle of Man TT by DNU
isle.of.man.tt.*DNU

# MotoGP by DNU
motogp.*\d{4}.*round\d.*((fp\d?|practice|sprint|qualifying|q1|q2|race)).*DNU

# NBA 1080p by GAMETiME
nba.*1080p.*gametime

# NHL RS 60fps feeds
nhl.*rs.*(720p|1080p).*en60fps

# NFL by NiGHTNiNJAS
nfl.*nightninjas

# UFC by VERUM
ufc[ ._-].*?\d{3}.*verum

# WorldSBK / WorldSSP / WorldSSP300 by MWR
(wsbk|wssp|wssp300).*\d{4}.round\d+.[^.]+.(fp\d?|season.preview|superpole|race.one|race.two|war.up(one|two)?|weekend.highlights).*h264.*mwr
```

UFC releases must now include the matchup slug (e.g., `UFC 322 Della Maddalena vs Makhachev`) so Playbook can align each file with the correct metadata season. Event numbers alone are ignored by the new title-based matching.

## Plex Library Setup

Playbook handles **file and folder layout**. To get rich metadata (titles, summaries, posters, artwork) in Plex, use the **TVSportsDB metadata agent**. This is a custom Plex metadata provider that pulls everything directly from [TVSportsDB](https://tvsportsdb.com) — no extra tools needed.

### 1. Add the TVSportsDB metadata provider

Requires Plex Media Server **1.43.0+** (2024 or newer). No plugin installation required.

1. In Plex, go to **Settings → Metadata Agents**.
2. Click the **add provider** button and enter: `https://api.tvsportsdb.com/plex`
3. Click the **add agent** button to confirm.
4. **Restart Plex** for the changes to take effect.

For the full setup guide with screenshots, see [tvsportsdb.com/setup/plex](https://tvsportsdb.com/setup/plex).

### 2. Create your sports library

1. In the Plex web UI, go to **Libraries → Add Library**.
2. Choose:
   - **Library type:** `TV Shows`
   - **Name:** e.g. `Sport`
3. Click **Next** and under **Add folders**, select your `DESTINATION_DIR`.
4. Click **Advanced** and set:
   - **Scanner:** `Plex Series Scanner`
   - **Agent:** `TVSportsDB`
   - **Episode sorting:** `Newest first`
5. Save the library.

Once Playbook populates the destination folder, Plex will automatically pick up shows with titles, summaries, posters, and backgrounds from TVSportsDB.

### Troubleshooting metadata

- **Missing metadata:** Verify your filenames match the expected format (`Show - S01E01 - Title.ext`). Use Plex's **Fix Match** feature to manually search for the correct show.
- **Incorrect matches:** Right-click the item → **Fix Match** → search for the correct show name, then refresh metadata.
- **Show not found:** Confirm the show exists in the [TVSportsDB database](https://tvsportsdb.com). If it's missing, request it via the site.

Playbook also supports pushing metadata directly via the Plex API using `integrations.plex.metadata_sync` — see the [Configuration Deep Dive](#2-integrations) for details.

## Adding New Sports

Adding a new sport is a two-step process: first add the metadata to TVSportsDB, then configure Playbook to match files against it.

### 1. Add metadata to TVSportsDB

All show/season/episode metadata lives in [TVSportsDB](https://tvsportsdb.com). If the sport you want isn't there yet:

1. Go to [tvsportsdb.com](https://tvsportsdb.com) and request the sport or add it yourself.
2. Make sure the show has seasons and episodes populated with titles and aliases that match how release groups name their files.

### 2. Configure Playbook

Once the sport exists in TVSportsDB:

1. Add a sport entry to your `config.yaml` with a `show_slug` or `show_slug_template` pointing to the TVSportsDB show.
2. Either reference an existing `pattern_sets` pack or write custom `file_patterns` with regex that captures the groups your release files use.
3. Run `--dry-run --verbose` to test matching without writing files.
4. Iterate on patterns and aliases until every file links where you expect.

If you build a pattern pack that works well, consider opening a PR to add it to `pattern_templates.yaml` so others can use it too.

## Troubleshooting & FAQ

- **Nothing gets processed:** Confirm `source_dir` is mounted and readable. Check that `source_globs` and `include_patterns` match your files. Run with `LOG_LEVEL=DEBUG` to see why files are being skipped.
- **Files processed but not appearing in Plex:** Verify `destination_dir` is the same path Plex is scanning. If using Docker/NFS, check mount paths match. Enable `integrations.plex.scan_on_activity` or trigger a manual library scan.
- **Metadata looks stale:** Lower `ttl_hours` in `settings.tvsportsdb` or delete `cache_dir` contents to force a refetch from the TVSportsDB API.
- **Hardlinks fail:** Set `link_mode: copy` (globally or per sport) when source and destination are on different filesystems, or when writing to SMB/NFS shares.
- **Pattern matches but wrong season:** Adjust `season_selector` mappings or use `season_overrides` to force season numbers for exhibitions/pre-season events.
- **File was already processed and won't re-run:** Playbook tracks processed files in a SQLite database under `state_dir`. Use `--force-reprocess` (or `FORCE_REPROCESS=true`) to bypass the database check, or `--clear-processed-cache` to wipe the database entirely.
- **Quality upgrade not happening:** Ensure `quality_profile.enabled: true` is set globally or on the sport. Check that the new file actually scores higher — run with `--trace-matches` to see scoring details.
- **Need to re-run immediately:** Use `--no-watch` (or `WATCH_MODE=false`) to force a single processing pass even if your watcher deployment is already running.

## Development

```bash
git clone https://github.com/s0len/playbook.git
cd playbook
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev,gui]
pre-commit install
```

- Run the CLI locally: `python -m playbook.cli --config config/config.sample.yaml --dry-run --verbose`.
- Build the container image: `docker build -t playbook:dev .`.
- Lint and format: `ruff check .` / `ruff format .`.
- Run the automated tests: `pytest`.
- Bootstrap a brand-new sandbox and run the full test suite: `bash scripts/bootstrap_and_test.sh`.
- Validate filename samples: edit `tests/data/pattern_samples.yaml` and run `pytest tests/test_pattern_samples.py` to confirm new or modified patterns resolve correctly.
- Open a draft pull request early—sample configs and matching logic benefit from collaborative review.

## License

Distributed under the [GNU GPLv3](LICENSE).

## Support

Questions, feature ideas, or metadata feed requests? [Open an issue](https://github.com/s0len/playbook/issues) or start a discussion. For bespoke integrations, reach out via the issue tracker and we can coordinate.

## Sample NHL Regular Season Filenames

Bundle the `nhl` pattern set with the [NHL 2025-2026 metadata feed](https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/nhl/2025-2026.yaml) to normalize releases such as:

- `NHL RS 2025 New Jersey Devils vs Buffalo Sabres 28 11 720pEN60fps MSG.mkv`
- `NHL 18-10-2025 RS Edmonton Oilers vs New Jersey Devils 1080p60_EN_MSGSN.mkv`
- `NHL RS 2025 New Jersey Devils vs Washington Capitals 15 11 720pEN60fps MonumentalS.mkv`
- `NHL.2025.RS.Blue.Jackets.vs.Devils.1080pEN60fps.mkv`

## Sample Figure Skating Grand Prix Filenames

Bundle the `figure_skating_grand_prix` pattern set with the [Figure Skating Grand Prix 2025 metadata feed](https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/figure-skating-grand-prix-2025.yaml) to normalize releases such as:

- `Figure Skating Grand Prix France 2025 Pairs Short Program 17 10 720pEN50fps ES`
- `Figure Skating Grand Prix France 2025 Ice Dancing Rhythm Dance 18 10 720pEN50fps ES`
- `Figure Skating Grand Prix China 2025 Mixed Pairs Short Program 24 10 720pEN50fps ES`
- `Figure Skating Grand Prix China 2025 Exhibition Gala 26 10 720pEN50fps ES`
- `Figure Skating Grand Prix Canada 2025 Ice Dancing Free Program 02 11 720pEN50fps ES`
- `Figure Skating Grand Prix Canada 2025 Men Free Program 02 11 720pEN50fps ES`
- `Figure Skating Grand Prix Japan 2025 Ice Dancing Free Program 08 11 720pEN50fps ES`
- `Figure Skating USA Grand Prix 2025 Pairs Short Program 15 11 720pEN50fps ES`
- `Figure Skating Grand Prix Espoo 2025 Exhibition Gala 23 11 720pEN50fps ES`
- `Figure Skating Grand Prix Final 2025 Women Free Program 06 12 1080pEN50fps.mkv`

