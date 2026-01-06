# Playbook

[![License: GPLv3](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776ab.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Fs0len%2Fplaybook-0db7ed.svg?logo=docker&logoColor=white)](https://github.com/users/s0len/packages/container/package/playbook)
[![Docs](https://img.shields.io/badge/docs-View%20Documentation-0f172a.svg?logo=book&logoColor=white)](https://s0len.github.io/Playbook/)

**Sonarr for Sports** – Automated file matching, renaming, and metadata for sports content in Plex.

> Metadata-driven automation that turns chaotic sports releases into Plex-perfect TV libraries—no brittle scripts, just declarative YAML.

## The Problem

Love watching sports replays in Plex but hate manually renaming files and setting metadata? Traditional tools like Sonarr don't work for sports because there's no centralized database like TheTVDB. Every sport structures their seasons differently (F1 has races, UFC has events, NFL has weeks), and release groups use wildly inconsistent naming schemes.

## How Playbook Solves It

Playbook is a complete pipeline that bridges the gap between messy downloads and perfectly organized Plex libraries:

### 1. **The Database Layer**

Custom scrapers pull sports schedules from various sources (SportsDB, official APIs, manual curation) and structure them as YAML files that mirror how Plex expects TV shows: Show → Season → Episode. This is the foundation – every sport gets its own "TVDb" equivalent.

### 2. **Smart File Matching** (like Sonarr)

Playbook scans your downloads, parses filenames using regex patterns (built-in packs for F1, MotoGP, UFC, NFL, NBA, NHL, etc.), matches them against the YAML database, and automatically renames/moves them to your Plex library with perfect naming.

### 3. **Rich Metadata** (via Kometa)

The same YAML files that power matching also feed Kometa to set posters, summaries, air dates, and episode titles. One source of truth for everything.

## Why It's a Game-Changer

- **One YAML file** does it all: episode matching + metadata + Kometa integration
- **Declarative**: Swap leagues, change folder structures, or add new release groups without touching Python
- **Complete automation**: From download to Plex-ready with proper artwork and descriptions
- **Built for sports**: Handles special cases like sprint races, prelims, qualifying sessions, and multi-part events

## Quick Verification

Before running for real, test with a dry-run to confirm metadata downloads and filesystem access:

```bash
docker run --rm -it \
  -e DRY_RUN=true \
  -e VERBOSE=true \
  -e SOURCE_DIR="/downloads" \
  -e DESTINATION_DIR="/library" \
  -e CACHE_DIR="/cache" \
  -v /config:/config \
  -v /downloads:/data/source \
  -v /library:/data/destination \
  -v /cache:/var/cache/playbook \
  ghcr.io/s0len/playbook:latest --dry-run --verbose
```

## Table of Contents

- [Playbook](#playbook)
  - [The Problem](#the-problem)
  - [How Playbook Solves It](#how-playbook-solves-it)
    - [1. **The Database Layer**](#1-the-database-layer)
    - [2. **Smart File Matching** (like Sonarr)](#2-smart-file-matching-like-sonarr)
    - [3. **Rich Metadata** (via Kometa)](#3-rich-metadata-via-kometa)
  - [Why It's a Game-Changer](#why-its-a-game-changer)
  - [Quick Verification](#quick-verification)
  - [Table of Contents](#table-of-contents)
  - [Quickstart](#quickstart)
    - [Option A: Docker (Recommended)](#option-a-docker-recommended)
    - [Option B: Python Environment](#option-b-python-environment)
    - [Option C: Kubernetes (Flux HelmRelease)](#option-c-kubernetes-flux-helmrelease)
  - [Architecture at a Glance](#architecture-at-a-glance)
  - [Configuration Deep Dive](#configuration-deep-dive)
    - [1. Global Settings](#1-global-settings)
      - [Notification targets \& Autoscan](#notification-targets--autoscan)
    - [2. Sport Entries](#2-sport-entries)
    - [3. Pattern Matching](#3-pattern-matching)
    - [4. Destination Templating](#4-destination-templating)
    - [5. Variants \& Reuse](#5-variants--reuse)
  - [Run Modes \& CLI](#run-modes--cli)
    - [Config Validation](#config-validation)
  - [Logging \& Observability](#logging--observability)
  - [Directory Conventions](#directory-conventions)
  - [Plex Metadata via Kometa](#plex-metadata-via-kometa)
    - [Example Kometa config](#example-kometa-config)
    - [Triggering Kometa After Ingests](#triggering-kometa-after-ingests)
      - [Kubernetes CronJob trigger](#kubernetes-cronjob-trigger)
      - [Docker Run trigger](#docker-run-trigger)
        - [Docker prerequisites inside the Playbook container](#docker-prerequisites-inside-the-playbook-container)
      - [Manual trigger CLI](#manual-trigger-cli)
  - [Downloading Sports with Autobrr](#downloading-sports-with-autobrr)
    - [Basic Autobrr setup](#basic-autobrr-setup)
    - [Example regexes](#example-regexes)
  - [Plex Library Setup](#plex-library-setup)
  - [Extending to New Sports](#extending-to-new-sports)
  - [Troubleshooting \& FAQ](#troubleshooting--faq)
  - [Development](#development)
  - [Roadmap](#roadmap)
  - [License](#license)
  - [Support](#support)
  - [Sample NHL Regular Season Filenames](#sample-nhl-regular-season-filenames)
  - [Sample Figure Skating Grand Prix Filenames](#sample-figure-skating-grand-prix-filenames)

## Quickstart

Before running the organizer for real, confirm:

- `playbook.yaml` exists (copy `config/playbook.sample.yaml` and tailor it).
- `SOURCE_DIR`, `DESTINATION_DIR`, and `CACHE_DIR` point at mounted paths with the right permissions.
- You can reach the remote metadata URLs from the host/container (validate with the dry-run above).

### Option A: Docker (Recommended)

> **Important:** The container validates that `SOURCE_DIR`, `DESTINATION_DIR`, and `CACHE_DIR` are defined through environment variables or the `settings` block in your config. It exits with an error instead of silently creating `/data/...` defaults, so wire these paths explicitly.

```bash
docker run -d \
  --name playbook \
  -e TZ="UTC" \
  -e SOURCE_DIR="/downloads" \
  -e DESTINATION_DIR="/library" \
  -e CACHE_DIR="/cache" \
  -v /config:/config \
  -v /downloads:/data/source \
  -v /library:/data/destination \
  -v /cache:/var/cache/playbook \
  -v /logs:/var/log/playbook \
  ghcr.io/s0len/playbook:latest
```

1. Copy the sample configuration: `cp config/playbook.sample.yaml /config/playbook.yaml`.
2. Update `playbook.yaml` with your directories, enabled sports, and any overrides.
3. Tail the logs (`docker logs -f playbook`) to watch the first pass.

> Tip: Dry-run everything first.
>
> ```bash
> docker run --rm -it \
>   -e DRY_RUN=true \
>   -e VERBOSE=true \
>   -e SOURCE_DIR="/downloads" \
>   -e DESTINATION_DIR="/library" \
>   -e CACHE_DIR="/cache" \
>   -v /config:/config \
>   -v /downloads:/data/source \
>   -v /library:/data/destination \
>   -v /cache:/var/cache/playbook \
>   -v /logs:/var/log/playbook \
>   ghcr.io/s0len/playbook:latest --dry-run --verbose
> ```

### Option B: Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playbook.cli --config /path/to/playbook.yaml --dry-run --verbose
```

Tips:

- Set `SOURCE_DIR`, `DESTINATION_DIR`, and `CACHE_DIR` env vars (or the equivalent entries in `settings`)—the container will refuse to start if these are missing.
- Use `LOG_LEVEL=DEBUG` or `VERBOSE=true` to mirror the Docker verbosity locally.
- When running from source, the entrypoint script `entrypoint.sh` mirrors the Docker environment variable contract.

### Option C: Kubernetes (Flux HelmRelease)

Use the [bjw-s/app-template](https://github.com/bjw-s/helm-charts/tree/main/charts/other/app-template) chart with Flux to keep a cluster deployment reconciled. The example below mirrors the Docker settings and mounts persistent cache/log directories alongside the config file:

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
  values:
    controllers:
      main:
        type: deployment
        containers:
          app:
            image:
              repository: ghcr.io/s0len/playbook
              tag: develop@sha256:586d8e06fae7d156d47130ed18b1a619a47d2c5378345e3f074ee6c282f09f02
              pullPolicy: Always
            env:
              WATCH_MODE: true
              LOG_LEVEL: INFO
              CONFIG_PATH: /config/playbook.yaml
              CACHE_DIR: /settings/cache
              LOG_DIR: /settings/logs
              SOURCE_DIR: /data/torrents/sport
              DESTINATION_DIR: /data/media/sport
            envFrom:
              - secretRef:
                  name: playbook-secret
    persistence:
      settings:
        existingClaim: playbook-settings
        globalMounts:
          - path: /settings
      data:
        type: nfs
        server: "${TRUENAS_IP}"
        path: /mnt/rust/data
        globalMounts:
          - path: /data
      config:
        type: configMap
        name: playbook-configmap
        globalMounts:
          - path: /config/playbook.yaml
            subPath: playbook.yaml
            readOnly: true
```

Quick checklist:

- Create a `playbook-secret` with any sensitive values (`kubectl create secret generic ... --from-literal=API_TOKEN=...`).
- Mount a `playbook-configmap` containing your `playbook.yaml` (or use an `externalSecret`).
- Backing storage: either bind an existing PVC (`settings`) for cache/logs or swap in another persistence strategy. The NFS block mounts downloads and media libraries.
- Enable `file_watcher.enabled` (or set `WATCH_MODE=true`) to keep Playbook running continuously; leave it disabled for ad-hoc batch runs.
- Add `reloader.stakater.com/auto: "true"` (already in the example) to hot-reload when the config map changes.

## Architecture at a Glance

Under the hood, Playbook follows this flow:

```text
┌────────────────┐    fetch + cache     ┌─────────────────────┐
│ Remote YAML    │ ───────────────────▶ │ Metadata Normalizer │
└────────────────┘                      └────────┬────────────┘
                                               │ normalized Show/Season/Episode
                                       ┌───────▼────────┐
   source files + globs + aliases       │ Matching Engine │
──────────────────────────────────────▶ │  (regex + TTL)  │
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

1. **Metadata fetch & cache**: remote YAML is downloaded with `requests`, cached on disk, and refreshed when TTLs expire.
2. **Normalization**: structured dataclasses infer round numbers, preserve summaries, and attach aliases.
3. **Matching**: regex capture groups, alias tables, and fuzzy matching link filenames to metadata episodes.
4. **Templating**: rich context feeds customizable templates for root folders, season directories, and filenames.
5. **Action**: files are hardlinked (default), copied, or symlinked into the library, respecting `skip_existing` and priority rules.

## Configuration Deep Dive

Start with `config/playbook.sample.yaml`. The schema mirrors `playbook.config` dataclasses.

### 1. Global Settings

| Field | Description | Default |
|-------|-------------|---------|
| `source_dir` | Root directory containing downloads to normalize. | `/data/source` |
| `destination_dir` | Library root where organized folders/files are created. | `/data/destination` |
| `cache_dir` | Metadata cache directory (`metadata/<sha1>.json`). Safe to delete to force refetch. | `/data/cache` |
| `dry_run` | When `true`, logs intent but skips filesystem writes. | `false` |
| `skip_existing` | Leave destination files untouched unless a higher-priority release arrives. | `true` |
| `link_mode` | Default link behavior: `hardlink`, `copy`, or `symlink`. | `hardlink` |
| `notifications.batch_daily` | When `true`, queue per-sport notifications for the day and edit a single Discord message instead of posting every file. | `false` |
| `notifications.flush_time` | Local time boundary (`HH:MM`) used to roll daily batches forward. Entries before this time count toward the previous day. | `"00:00"` |
| `notifications.mentions` | Map `sport_id` (supports glob patterns, plus `default`) to a Discord mention string (role ID, `@here`, etc.) to prepend to matching notifications. | `{}` |
| `file_watcher.enabled` | When `true`, Playbook keeps running and reacts to filesystem events; when `false`, the CLI performs a single pass and exits. | `false` |
| `file_watcher.paths` | Directories to observe; defaults to `source_dir` when empty. Relative entries resolve under `source_dir`. | `[]` |
| `file_watcher.include` / `ignore` | Glob filters to allow/skip events (e.g. ignore `*.part`). | `[]` / `["*.part","*.tmp"]` |
| `file_watcher.debounce_seconds` | Minimum seconds between watcher-triggered runs. Batches bursts of events into a single processor pass. | `5` |
| `file_watcher.reconcile_interval` | Forces a full scan every _N_ seconds even if no events arrive, ensuring missed events are caught. | `900` |
| `destination.*` | Default templates for root folder, season folder, and filename. | See sample |

Define Discord notifications under `notifications.targets`: each entry describes a destination (single-event or batched) and can have its own mention overrides. Enable `notifications.batch_daily` if you prefer a rolling per-day embed instead of individual posts. Use `notifications.flush_time` to control when the “day” ends (useful for overnight events).

Use `notifications.mentions` to opt specific Discord roles or users into certain sports. Entries are keyed by the sport’s ID (plus an optional `default` fallback) and the value is any mentionable string (`<@&ROLE_ID>`, `@here`, etc.). Keys can include shell-style wildcards (e.g. `formula1_*`), and Playbook automatically falls back to the base ID before any variant suffix (`premier_league` also covers `premier_league_2025_26`). Mentions are prepended to both single-event and batched messages, so subscribers only get pinged for the sports they care about:

```yaml
notifications:
  mentions:
    premier_league: "<@&123456789012345678>"
    formula1: "<@&222333444555666777>"   # Automatically applies to formula1_2025, formula1_2026, etc.
    default: "@everyone"           # optional fallback when no explicit entry exists

notifications:
  targets:
    - type: discord
      webhook_env: DISCORD_WEBHOOK_URL      # Keep secrets in env vars/Secrets, not the config file.
      # webhook_url: ${DISCORD_WEBHOOK_URL} # Optional inline expansion if you already template configs elsewhere.
      mentions:
        formula1: "<@&999>"        # Overrides/extends the global mentions for this webhook only.
    - type: discord
      webhook_url: https://discord.com/api/webhooks/alt
      mentions:
        premier_league: "<@&1234>"
```

`webhook_env` tells Playbook to read the runtime environment for the URL, so you can mount a Kubernetes/Docker secret as env vars without ever writing the secret into the ConfigMap. If you already have your own templating flow you can continue to use `webhook_url` with `${VAR}` substitution; both options are supported.

Older releases supported `settings.discord_webhook_url`; that field has been removed. If it still exists in your config you'll get a startup error — move the value into `notifications.targets` as shown above.

#### Notification targets & Autoscan

`notifications.targets` lets you fan out the same event to multiple destinations. Supported `type` values today are:

- `discord` (single event or rolling daily embed, as above)
- `slack` (simple text payload, optional template)
- `webhook` (generic JSON payload, fully templatable)
- `email` (SMTP with configurable subject/body templates)
- `autoscan` (new) — ping the Autoscan manual trigger so Plex/Emby/Jellyfin rescans a directory as soon as Playbook links a file

Autoscan support mirrors the [manual trigger endpoint](https://github.com/Cloudbox/autoscan?tab=readme-ov-file#manual): Playbook issues a `POST /triggers/<name>?dir=...` call with the directory that just received a processed file. Add a block like this under `notifications.targets`:

```yaml
notifications:
  targets:
    - type: autoscan
      url: http://autoscan:3030          # Base Autoscan URL (http/s)
      trigger: manual                    # Optional when using the default manual endpoint
      username: ${AUTOSCAN_USERNAME:-}   # Optional basic-auth credentials
      password: ${AUTOSCAN_PASSWORD:-}
      rewrite:
        - from: ${DESTINATION_DIR:-/data/destination}
          to: /mnt/unionfs/Media         # Rewrite Playbook’s path to what Autoscan/Plex can see
      timeout: 10                        # Seconds before the request is considered failed (default 10)
      verify_ssl: true                   # ⚠️ SECURITY WARNING: Setting false disables SSL/TLS verification and exposes you to MITM attacks - only for development with self-signed certs
```

Every successful `new`/`changed` event sends the parent directory of the destination file as a `dir` query parameter. Add more rewrite entries if Autoscan lives inside a container with different mount points.

Enable `file_watcher.enabled` to react to filesystem events instead of relying on periodic scans. The watcher listens for `create`, `modify`, and `move` events under `source_dir` (or the directories listed in `file_watcher.paths`). Globs in `include`/`ignore` cull noisy files, `debounce_seconds` batches rapid-fire events into a single processor run, and `reconcile_interval` guarantees a periodic full scan just in case the platform drops events.

### 2. Sport Entries

Each sport defines metadata, source detection, and matching behavior. Example below uses the Formula 1 2025 feed [^f1].

```yaml
- id: formula1_2025
  name: Formula 1 2025
  enabled: true
  metadata:
    url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/formula1/2025.yaml
    show_key: Formula1 2025
    ttl_hours: 12
    season_overrides:
      Pre-Season Testing:
        season_number: 0
        round: 0
  source_globs:
    - "Formula.1.*"
  source_extensions:
    - .mkv
    - .mp4
  allow_unmatched: false
  file_patterns:
    - regex: "(?i)^Formula\\.1\\.(?P<year>\\d{4})\\.Round(?P<round>\\d{2})\\.(?P<location>[^.]+)\\.(?P<session>[^.]+)"
      description: Canonical multi-session weekend releases
      season_selector:
        mode: round
        group: round
      episode_selector:
        group: session
      session_aliases:
        Race: ["Race"]
        Sprint: ["Sprint.Race", "Sprint"]
        Qualifying: ["Qualifying", "Quali"]
        Free Practice 1: ["FP1", "Free.Practice.1"]
```

Key fields:

- `enabled`: toggle sports on/off without deleting them.
- `source_globs` / `source_extensions`: coarse filters before pattern matching.
- `allow_unmatched`: downgrade pattern failures to informational logs (no warnings).
- `link_mode`: override global link behavior for a specific sport.

### 3. Pattern Matching

- **`regex`** – Must supply the capture groups consumed by selectors and templates (e.g., `round`, `session`, `location`).
- **`season_selector`** – Maps captures to a season. Supported modes: `round`, `key`, `title`, `sequential`. Add `offset` or `mapping` for fine-grained control.
- **`episode_selector`** – Chooses which capture identifies an episode. `allow_fallback_to_title` lets the matcher fall back to fuzzy title comparisons, and `default_value` forces a canonical session when the regex doesn’t capture one (useful for release groups that omit `Prelims`/`Main Card` tags).
- **`session_aliases`** – Augment metadata aliases with release-specific tokens (case-insensitive, normalized).
- **`priority`** – Lower numbers win when multiple patterns match the same file (defaults to `100`).
- **`destination_*` overrides** – Apply sport- or pattern-specific templates without touching global settings.

Built-in templates: the project now ships curated pattern sets for Formula 1, MotoGP, Moto2, Moto3, Isle of Man TT, NFL, and UFC. Reference them from a sport entry via:

```yaml
pattern_sets:
  - formula1
```

You can still inline `file_patterns` (alone or in addition to templates) for overrides or experiments. Review `src/playbook/pattern_templates.yaml` for the complete list and structure.

### 4. Destination Templating

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

### 5. Variants & Reuse

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
| `--config PATH` | `CONFIG_PATH` | `/config/playbook.yaml` | Path to the YAML config. |
| `--dry-run` | `DRY_RUN` | Inherits `settings.dry_run` | Force no-write mode. |
| `--verbose` | `VERBOSE` / `DEBUG` | `false` | Enables console DEBUG output. |
| `--log-level LEVEL` | `LOG_LEVEL` | `INFO` (or `DEBUG` with `--verbose`) | File log level. |
| `--console-level LEVEL` | `CONSOLE_LEVEL` | matches file level | Console log level. |
| `--log-file PATH` | `LOG_FILE` / `LOG_DIR` | `./playbook.log` | Rotates to `*.previous` on start. |
| `--clear-processed-cache` | `CLEAR_PROCESSED_CACHE` | `false` | Truthy to reset processed file cache before processing. |
| `--watch` | `WATCH_MODE=true` | `settings.file_watcher.enabled` | Force filesystem watcher mode (keep Playbook running). |
| `--no-watch` | `WATCH_MODE=false` | `false` | Disable watcher mode even if the config enables it. |

Environment variables always win over config defaults, and CLI flags win over environment variables.

### Config Validation

Preflight your YAML before running the processor:

```bash
python -m playbook.cli validate-config --config /config/playbook.yaml --diff-sample
```

The validator enforces the JSON schema, confirms referenced pattern sets exist, and then calls the same loader used by the runtime. Add `--show-trace` to surface Python tracebacks for deeper debugging. `--diff-sample` compares your file to `config/playbook.sample.yaml` to highlight customizations.

Continuous mode example:

```bash
docker run -d \
  -e WATCH_MODE=true \
  ghcr.io/s0len/playbook:latest --watch
```

Playbook stays alive and reruns automatically whenever the watcher observes filesystem changes (or when the reconcile timer forces a full scan). Use `--no-watch` (or `WATCH_MODE=false`) for single-pass batch runs.

## Logging & Observability

- Log entries now use a multi-line block layout (timestamp + header + aligned key/value pairs) so dense sections breathe.
- INFO-level runs show grouped counts per sport/source; add `--verbose`/`LOG_LEVEL=DEBUG` to expand into per-file diagnostics.
- Each pass ends with a `Run Recap` block (duration, totals, Kometa trigger state, destination samples) for quick scanning.
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

## Plex Metadata via Kometa

Playbook only handles **file and folder layout**. To get rich titles, posters and collections in Plex, you can pair it with [Kometa](https://github.com/Kometa-Team/Kometa) and the same YAML metadata feeds.

### Example Kometa config

Add something like this to your Kometa `config.yml` (library name can be whatever you use for sports, e.g. `Sport`):

```yaml
libraries:
  Sport:
    metadata_files:
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/formula1/2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/formula-e/2025-2026.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/indycar-series/2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/isle-of-man-tt.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/moto2/2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/moto3/2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/motogp/2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/nba/2025-2026.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/nfl/2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/premier-league/2025-2026.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/uefa-champions-league/2025-2026.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/ufc/2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/womens-uefa-euro.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/wsbk-2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/wssp-2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/wssp300-2025.yaml
```

### Triggering Kometa After Ingests

Playbook can nudge Kometa automatically after each ingest cycle. Configure it once under `settings.kometa_trigger` and it will fire once at the end of every processor run whenever at least one brand-new file was linked, so duplicate runs are avoided automatically.

#### Kubernetes CronJob trigger

Use this when Playbook and Kometa live in the same cluster:

```yaml
settings:
  kometa_trigger:
    enabled: true
    mode: kubernetes
    namespace: media
    cronjob_name: kometa-sport
    job_name_prefix: kometa-sport-triggered-by-playbook
```

Playbook clones the CronJob's `jobTemplate` so Kometa uses the exact same Pod spec you already trust. Jobs are labeled `trigger=playbook`, which makes it easy to monitor and tail logs:

```bash
kubectl -n media get jobs -l trigger=playbook
kubectl -n media logs job/kometa-sport-triggered-by-playbook-20241121-123456-abcd
```

If a Job already exists (e.g., Kometa is still running from a previous batch), Playbook logs the conflict and waits for the next ingest cycle.

#### Docker Run trigger

No Kubernetes? Set `mode: docker` and Playbook will shell out to `docker run` (or `podman`, etc.) with whatever libraries and config path you provide:

```yaml
settings:
  kometa_trigger:
    enabled: true
    mode: docker
    docker:
      binary: docker
      image: kometateam/kometa
      config_path: /srv/media/Kometa/config   # host path
      libraries: "Sports|TV Shows - 4K"
      extra_args:
        - --config
        - /config/config.yml
```

Under the hood Playbook runs a command similar to:

```bash
docker run --rm \
  -v "/srv/media/Kometa/config:/config:rw" \
  kometateam/kometa \
  --run-libraries "Sports|TV Shows - 4K" \
  --config /config/config.yml
```

Add any additional Kometa CLI flags to `docker.extra_args`, and mount a different config path/container path if needed. Logs from the container are captured and surfaced in `playbook.log`, so failures stand out quickly.

##### Docker prerequisites inside the Playbook container

- Mount the Docker socket so the daemon is reachable: `-v /var/run/docker.sock:/var/run/docker.sock`.
- Mount the client binaries into the container (paths vary, discover them with `command -v docker` and `command -v com.docker.cli` on macOS):

  ```bash
  -v $(command -v docker):/usr/local/bin/docker \
  -v $(command -v com.docker.cli):/usr/local/bin/com.docker.cli
  ```

Without these mounts the trigger will log clear errors (look for `Kometa docker trigger requires...`).

Already running Kometa in Docker Compose? Set `docker.container_name` (plus optional `exec_python` / `exec_script`) and Playbook will switch to `docker exec` instead of launching a new container:

```bash
docker exec kometa \
  python3 /app/kometa/kometa.py \
  --config /config/config.yml \
  --library "Sports" \
  --run
```

All other fields (`libraries`, `extra_args`, environment overrides) still apply, so you can reuse the same knobs regardless of whether you spin up a fresh container or exec into an existing one.
For absolute control you can provide `docker.exec_command` (a list such as `["python3", "/app/kometa/kometa.py"]`), in which case Playbook appends your `libraries`/`extra_args` without any shell gymnastics.

#### Manual trigger CLI

Need to test the integration without running the full ingest loop? Use the dedicated CLI helper:

```bash
python -m playbook.cli kometa-trigger --config /config/playbook.yaml --mode docker
```

It loads your config, instantiates the trigger, and logs the full docker command/output to `playbook.log` (or whatever `--log-file` you specify), making it easy to diagnose missing mounts or permissions.

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

To let Plex correctly index everything that Playbook creates, set up a dedicated **TV library** that points at your Playbook destination directory.

1. In the Plex web UI, go to **Libraries → Add Library**.
2. Choose:
   - **Library type:** `TV Shows`
   - **Name:** e.g. `Sport`, `Sports`, or whatever fits your setup.
3. Click **Next** and under **Add folders**, select the **same folder** you configured as `DESTINATION_DIR` for Playbook (or the sports subfolder inside it).
4. Click **Advanced** and set:

   - **Scanner:** `Plex Series Scanner`  
   - **Agent:** `Personal Media Shows`  
   - **Episode sorting:** `Newest first`

5. Save the library, then run a **Scan Library Files** once Playbook has populated the destination folder.

Using `TV Shows` + `Plex Series Scanner` + `Personal Media Shows` ensures Plex treats each sport/season/session as proper TV episodes, while Kometa applies all the rich metadata on top.

## Extending to New Sports

1. Start from `playbook.sample.yaml` and enable the sport by listing the appropriate `pattern_sets` (e.g., `formula1`, `motogp`).
2. Update the `metadata.url` / `show_key`, along with `source_globs` and `source_extensions` for your release group.
3. If no template exists yet (or you need tweaks), copy the closest set from `pattern_templates.yaml` into the `pattern_sets:` section of your config and adjust the regex/aliases.
4. Run `--dry-run --verbose` and review both console output and `playbook.log` for skipped/ignored diagnostics.
5. Iterate on patterns, aliases, and templates until every file links where you expect—then consider opening a PR to upstream the new template.

## Troubleshooting & FAQ

- **Nothing gets processed:** Confirm the `source_dir` is mounted, readable, and matches your `source_globs`. Enable `DEBUG` to see ignored reasons.
- **Metadata looks stale:** Delete the cache directory (`rm -rf /var/cache/playbook/metadata`) or lower `ttl_hours`.
- **Hardlinks fail:** Set `link_mode: copy` (globally or per sport) when crossing filesystems or writing to SMB/NFS shares.
- **Pattern matches but wrong season:** Adjust `season_selector` mappings or use `season_overrides` to force numbers for exhibitions/pre-season events.
- **Need to re-run immediately:** Run `python -m playbook.cli --no-watch ...` (or set `WATCH_MODE=false`) to perform an on-demand single pass even if your watcher deployment is already running.

## Development

```bash
git clone https://github.com/s0len/playbook.git
cd playbook
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- Run the CLI locally: `python -m playbook.cli --config config/playbook.sample.yaml --dry-run --verbose`.
- Build the container image: `docker build -t playbook:dev .`.
- Follow standard Python formatting (e.g., `ruff`, `black`) to keep diffs tidy.
- Install test tooling: `pip install -r requirements-dev.txt`.
- Run the automated tests: `pytest`.
- Bootstrap a brand-new sandbox (e.g., Cursor/MCP agents) and run the full test suite in one step: `bash scripts/bootstrap_and_test.sh`.
- Validate filename samples: edit `tests/data/pattern_samples.yaml` and run `pytest tests/test_pattern_samples.py` to confirm new or modified patterns resolve correctly.
- Open a draft pull request early—sample configs and matching logic benefit from collaborative review.

## Roadmap

- Additional pattern packs (MotoGP, IndyCar, NBA, NFL, NHL) with ready-to-use regex + alias tables.
- Optional webhook/websocket triggers to react to new downloads instantly.
- Strategy plugins for bespoke numbering or archive workflows.
- Web UI to inspect matches, stats, and activity history.
- Telemetry toggles for Prometheus/Grafana dashboards.

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

---

[^f1]: Formula 1 2025 metadata feed – [raw YAML](https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/formula1/2025.yaml)
