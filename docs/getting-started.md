# Getting Started

This guide walks you through installing Playbook, configuring your first sport, and verifying everything works before letting it run automatically. You can deploy via Docker (recommended), Python virtual environment, or Kubernetes.

## Quick Overview

**All sports are enabled by default!** Every deployment needs just three things:

1. **A config file** (`playbook.yaml`) with your directory paths
2. **Three directories**: source (downloads), destination (Plex library), and cache (metadata storage)
3. **Network access** to TheTVSportsDB API (metadata source for show/season/episode information)

Playbook automatically processes Formula 1, MotoGP, UFC, NFL, NBA, NHL, Premier League, Champions League, Figure Skating, and more. No need to configure individual sports unless you want to customize or disable them.

All deployment methods use the same config schema and produce identical folder layouts in your Plex library.

## Before You Start

Before installing, gather this information:

- **Source directory** – where your torrent client/downloader saves files (e.g., `/downloads/sport`)
- **Destination directory** – your Plex library path (e.g., `/library/sport`)
- **Cache directory** – persistent storage for metadata and state (e.g., `/cache/playbook`)

Then:

1. Copy `config/playbook.sample.yaml` to your preferred location (Docker defaults to `/config/playbook.yaml`)
2. Edit the config to set `SOURCE_DIR`, `DESTINATION_DIR`, and `CACHE_DIR` (or provide them as environment variables)
3. _(Optional)_ Disable sports you don't want using `disabled_sports: [sport_id, ...]`
4. Validate your config: `playbook validate-config --config playbook.yaml --diff-sample`

!!! tip "Minimal Configuration"
    With default sports enabled, your config can be as simple as:
    ```yaml
    settings:
      source_dir: /downloads/sport
      destination_dir: /library/sport
      cache_dir: /cache/playbook
    ```
    All 16 sports (26 variants) will be processed automatically!

## Installation Methods

Choose the deployment method that fits your setup. All methods use the same config file and produce identical results.

### Option A: Docker (Recommended)

#### Step 1: Test with a dry-run

Before running continuously, validate your setup with a one-shot dry-run:

```bash
docker run --rm -it \
  -e DRY_RUN=true \
  -e VERBOSE=true \
  -e SOURCE_DIR="/downloads" \
  -e DESTINATION_DIR="/library" \
  -e CACHE_DIR="/cache" \
  -v /path/to/your/config:/config \
  -v /path/to/downloads:/downloads \
  -v /path/to/library:/library \
  -v /path/to/cache:/cache \
  ghcr.io/s0len/playbook:latest
```

Replace `/path/to/...` with your actual host directories. This command:

- Runs once and exits (`--rm`)
- Shows what would happen without moving files (`DRY_RUN=true`)
- Prints detailed matching logic (`VERBOSE=true`)
- Validates config and metadata access

#### Step 2: Run continuously

Once the dry-run looks good, run detached:

```bash
docker run -d \
  --name playbook \
  -e TZ="UTC" \
  -e SOURCE_DIR="/downloads" \
  -e DESTINATION_DIR="/library" \
  -e CACHE_DIR="/cache" \
  -e WATCH_MODE=true \
  -v /path/to/your/config:/config \
  -v /path/to/downloads:/downloads \
  -v /path/to/library:/library \
  -v /path/to/cache:/cache \
  ghcr.io/s0len/playbook:latest
```

#### Environment Variables Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `SOURCE_DIR` | Where downloads land (required) | `/downloads` |
| `DESTINATION_DIR` | Plex library path (required) | `/library` |
| `CACHE_DIR` | Metadata/state storage (required) | `/cache` |
| `WATCH_MODE` | Keep running and watch for new files | `true` |
| `DRY_RUN` | Simulate without moving files | `true` |
| `VERBOSE` | Detailed matching logs | `true` |
| `LOG_LEVEL` | Logging verbosity | `DEBUG`, `INFO`, `WARNING` |

#### Monitoring

```bash
# Tail live logs
docker logs -f playbook

# Check container status
docker ps -a | grep playbook
```

### Option B: Python Environment

Use this method for local development, testing, or if you prefer managing Python dependencies directly:

#### Step 1: Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### Step 2: Validate your config

```bash
python -m playbook.cli validate-config --config /path/to/playbook.yaml --diff-sample
```

#### Step 3: Test with a dry-run

```bash
export SOURCE_DIR="/path/to/downloads"
export DESTINATION_DIR="/path/to/library"
export CACHE_DIR="/path/to/cache"

python -m playbook.cli process --config /path/to/playbook.yaml --dry-run --verbose
```

#### Step 4: Run continuously (watcher mode)

```bash
export WATCH_MODE=true
python -m playbook.cli watch --config /path/to/playbook.yaml
```

#### Useful Environment Variables

Same as Docker – set `SOURCE_DIR`, `DESTINATION_DIR`, `CACHE_DIR`, `LOG_LEVEL`, `VERBOSE`, etc. before running commands.

### Option C: Kubernetes (Flux HelmRelease)

Use this method if you're running a Flux-based Kubernetes cluster. This example uses the [bjw-s/app-template](https://github.com/bjw-s/helm-charts/tree/main/charts/other/app-template) chart to deploy Playbook as a single-pod deployment with persistent storage:

#### Prerequisites

- A running Kubernetes cluster with Flux installed
- Persistent storage provisioner (or NFS access)
- bjw-s app-template OCIRepository configured in Flux

```yaml
---
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
      main:
        serviceAccount:
          identifier: playbook
        type: deployment
        containers:
          app:
            image:
              repository: ghcr.io/s0len/playbook
              tag: develop@sha256:6248cac4f5aeb9403a88f919e522e96291e3c93eb018c289aff4dbfef92ec5fa
              pullPolicy: Always
            env:
              CACHE_DIR: /settings/cache
              CLEAR_PROCESSED_CACHE: false
              CONFIG_PATH: /config/config.yaml
              DRY_RUN: false
              DESTINATION_DIR: /data/media/sport
              LOG_DIR: /tmp
              LOG_LEVEL: INFO
              SOURCE_DIR: /data/torrents/sport
            envFrom:
              - secretRef:
                  name: playbook-secret
            securityContext:
              privileged: false
        annotations:
          reloader.stakater.com/auto: "true"

    defaultPodOptions:
      automountServiceAccountToken: true
      enableServiceLinks: false
      securityContext:
        runAsUser: 568
        runAsGroup: 568
        runAsNonRoot: true
        fsGroup: 568

    persistence:
      settings:
        existingClaim: playbook-settings
        globalMounts:
          - path: /settings
            readOnly: false

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
            readOnly: false

      config:
        type: configMap
        name: playbook-configmap
        globalMounts:
          - path: /config/config.yaml
            subPath: config.yaml
            readOnly: true

```

#### Key Configuration Notes

- **Image tag**: Use `latest` for stable releases or `develop` for bleeding edge (pin to digest for reproducibility)
- **Environment variables**: Set `SOURCE_DIR`, `DESTINATION_DIR`, `CACHE_DIR` to match your persistent volume mount paths
- **Config file**: Mount via ConfigMap or Secret (this example uses a ConfigMap at `/config/config.yaml`)
- **Secrets**: Store sensitive values (API keys, webhook URLs) in a `playbook-secret`, reference it with `envFrom`, and point `notifications.targets[].webhook_env` at the relevant variable (e.g., `DISCORD_WEBHOOK_URL`)
- **Persistent storage**: Cache directory should survive pod restarts (use PVC or NFS)
- **Watcher mode**: Enable `WATCH_MODE=true` or `file_watcher.enabled: true` in config for continuous processing
- **Automatic reloads**: Add `reloader.stakater.com/auto: "true"` annotation to restart when ConfigMap changes

#### Deployment Checklist

1. Create the secret: `kubectl create secret generic playbook-secret --from-literal=DISCORD_WEBHOOK=https://...`
2. Create the ConfigMap with your `playbook.yaml` content: `kubectl create configmap playbook-configmap --from-file=config.yaml=playbook.yaml`
3. Apply the HelmRelease manifest
4. Check logs: `kubectl logs -f deployment/playbook`
5. Verify processing: watch destination directory for new files

## First Run Checklist

Follow these steps in order to ensure everything works before running automatically:

### 1. Validate Your Config

```bash
# Docker
docker run --rm -it \
  -v /path/to/your/config:/config \
  ghcr.io/s0len/playbook:latest validate-config --config /config/playbook.yaml --diff-sample

# Python
python -m playbook.cli validate-config --config playbook.yaml --diff-sample
```

This command:

- Checks YAML syntax and required fields
- Validates pattern templates and matching logic
- Shows differences from the sample config
- Confirms metadata URLs are accessible

### 2. Run a Dry-Run

```bash
# Docker
docker run --rm -it \
  -e DRY_RUN=true \
  -e VERBOSE=true \
  -e SOURCE_DIR="/downloads" \
  -e DESTINATION_DIR="/library" \
  -e CACHE_DIR="/cache" \
  -v /path/to/your/config:/config \
  -v /path/to/downloads:/downloads \
  -v /path/to/library:/library \
  -v /path/to/cache:/cache \
  ghcr.io/s0len/playbook:latest

# Python
export SOURCE_DIR="/path/to/downloads"
export DESTINATION_DIR="/path/to/library"
export CACHE_DIR="/path/to/cache"
python -m playbook.cli process --config playbook.yaml --dry-run --verbose
```

Look for:

- **Matched files**: Confirm the pattern matched expected downloads
- **Destination paths**: Verify the Plex folder structure looks correct
- **Skipped files**: Understand why some files weren't processed
- **API responses**: Check that TheTVSportsDB metadata loaded successfully

### 3. Review Logs

Check `playbook.log` (or `docker logs`) for:

- Files successfully matched and their destination paths
- Any pattern matching failures or unmatched files
- Kometa/Autoscan trigger notifications (if enabled)
- Cache warming progress (first run downloads all metadata)

### 4. Test the Real Thing

Remove `DRY_RUN=true` and run a single batch:

```bash
# Docker (one-shot)
docker run --rm -it \
  -e SOURCE_DIR="/downloads" \
  -e DESTINATION_DIR="/library" \
  -e CACHE_DIR="/cache" \
  -v /path/to/your/config:/config \
  -v /path/to/downloads:/downloads \
  -v /path/to/library:/library \
  -v /path/to/cache:/cache \
  ghcr.io/s0len/playbook:latest
```

Verify:

- Files moved to correct destination folders
- Filenames follow Plex conventions (e.g., `S2024E05 - Round 5 - Monaco Grand Prix.mkv`)
- Original source files cleaned up (or preserved if `preserve_source: true`)

### 5. Point Plex at the Destination

Add your destination directory as a TV library in Plex:

- Library type: **TV Shows**
- Scanner: **Plex Series Scanner**
- Agent: **Plex TV Series** (metadata will be enriched by Kometa)

Scan the library and confirm shows/seasons/episodes appear.

### 6. Enable Continuous Processing

Once everything looks good, enable watcher mode or schedule regular runs:

#### Docker (detached with watcher)

```bash
docker run -d \
  --name playbook \
  -e WATCH_MODE=true \
  -e SOURCE_DIR="/downloads" \
  -e DESTINATION_DIR="/library" \
  -e CACHE_DIR="/cache" \
  -v /path/to/your/config:/config \
  -v /path/to/downloads:/downloads \
  -v /path/to/library:/library \
  -v /path/to/cache:/cache \
  ghcr.io/s0len/playbook:latest
```

#### Python (watcher mode)

```bash
export WATCH_MODE=true
python -m playbook.cli watch --config playbook.yaml
```

#### Kubernetes

Already running continuously with the HelmRelease

## What's Next?

- **[Configuration Guide](configuration.md)** – deep dive into all YAML options, pattern syntax, and templating
- **[Integrations](integrations.md)** – connect Kometa for metadata, Autoscan for instant Plex updates, Autobrr for automatic downloads
- **[Recipes](recipes.md)** – sport-specific examples (F1, MotoGP, UFC, etc.) and custom pattern tutorials
- **[Troubleshooting](troubleshooting.md)** – common issues, cache resets, debugging tips
