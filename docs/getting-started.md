# Getting Started

This guide covers the supported deployment paths, environment prep, and the first-run checklist. Regardless of where Playbook runs, every deployment shares the same configuration file (`playbook.yaml`) and destination library layout.

## Prerequisites

- Copy `config/playbook.sample.yaml` to your preferred location (Docker defaults to `/config/playbook.yaml`).
- Define `SOURCE_DIR`, `DESTINATION_DIR`, and `CACHE_DIR` through environment variables or the `settings` block. The container refuses to start if these values are missing.
- Ensure the host/container can reach the remote metadata URLs (validate with the dry-run command below).
- Mount persistent storage for cache/log directories if you want warm starts across restarts.

## Installation Paths

### Option A: Docker (Recommended)

Run the container detached once you are ready for continuous processing:

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

Recommended first run:

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
  -v /logs:/var/log/playbook \
  ghcr.io/s0len/playbook:latest --dry-run --verbose
```

Tips:

- The entrypoint validates required directories before the processor starts. Missing values cause a clear error instead of silently creating `/data/...` defaults.
- Use `LOG_LEVEL=DEBUG` or `VERBOSE=true` when you want deeper diagnostics.
- `docker logs -f playbook` tails the structured log output.

### Option B: Python Environment

Use a virtual environment for local development or CI:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playbook.cli --config /path/to/playbook.yaml --dry-run --verbose
```

Helpful environment variables:

- `SOURCE_DIR`, `DESTINATION_DIR`, `CACHE_DIR` mirror the Docker contract.
- `LOG_LEVEL=DEBUG` or `VERBOSE=true` copies the container verbosity locally.
- `WATCH_MODE=true` keeps the CLI alive with the filesystem watcher.

### Option C: Kubernetes (Flux HelmRelease)

Use the [bjw-s/app-template](https://github.com/bjw-s/helm-charts/tree/main/charts/other/app-template) chart with Flux. The example below mirrors the Docker configuration and mounts persistent cache/log directories alongside the config file:

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

Checklist:

- Create a `playbook-secret` with sensitive values (`kubectl create secret generic ...`).
- Mount a `playbook-configmap` containing your `playbook.yaml` (or source it from ExternalSecrets).
- Provide persistent storage for cache/log directories (PVC, NFS, etc.).
- Enable `file_watcher.enabled` (or set `WATCH_MODE=true`) when you want Playbook to keep watching.
- Add `reloader.stakater.com/auto: "true"` if you want automatic restarts on config changes.

## First Run Checklist

1. Confirm the config validates: `python -m playbook.cli validate-config --config playbook.yaml --diff-sample`.
2. Run a dry-run to warm caches and verify metadata downloads.
3. Review `playbook.log` (or `docker logs`) for skipped files and Kometa/autoscan triggers.
4. Point Plex/Kometa at the destination directory once the folder layout looks right.
5. Enable watcher mode or CronJob scheduling only after the initial batch finishes cleanly.

Next step: dive into the [Configuration Guide](configuration.md) to understand every YAML knob.
