# Integrations

Playbook focuses on filesystem organization and leaves downloading, metadata enrichment, and library refreshes to the tools that already excel at those jobs. This guide summarizes the supported integrations.

## Integration Overview

| Integration | Purpose | Quick link |
|-------------|---------|------------|
| Plex Metadata Sync | Pushes show/season/episode metadata from TheTVSportsDB directly to Plex. | [Plex Metadata Sync](#plex-metadata-sync) |
| Kometa | Applies metadata feeds so Plex gets canonical titles/artwork. | [Kometa Metadata](#kometa-metadata) |
| Kometa trigger | Automatically re-runs Kometa whenever Playbook links new files. | [Kometa Triggering](#kometa-triggering) |
| Autobrr | Automates torrent intake so Playbook always has fresh downloads to normalize. | [Autobrr Automation](#autobrr-download-automation) |
| Plex + Autoscan | Keeps your TV library and metadata agents refreshed the moment Playbook writes new files. | [Plex Library Setup](#plex-library-setup) / [Autoscan Hooks](#autoscan-hooks) |

## Plex Metadata Sync

Playbook can push show, season, and episode metadata directly from TheTVSportsDB to Plex. This includes:

- **Titles and sort titles** - Preserves original casing (e.g., "NTT IndyCar Series" instead of Plex's normalized "Ntt Indycar Series")
- **Summaries** - Episode and season descriptions
- **Dates** - Originally available dates for proper episode ordering
- **Artwork** - Posters and backgrounds from TheTVSportsDB

### Configuration

Enable Plex metadata sync in your config:

```yaml
settings:
  plex_metadata_sync:
    enabled: true
    url: ${PLEX_URL:-http://plex:32400}
    token: ${PLEX_TOKEN:-}
    library_id: ${PLEX_LIBRARY_ID:-}      # Optional: faster lookup by ID
    library_name: ${PLEX_LIBRARY_NAME:-TV Shows}
    timeout: 15
    force: false       # Force all updates even if unchanged
    dry_run: false     # Log only, no Plex writes
    sports: []         # Limit to specific sport IDs; empty = all sports
    scan_wait: 5       # Seconds to wait after triggering library scan
```

### How It Works

1. **Automatic sync** - When Playbook processes new files, it automatically syncs metadata for affected sports
2. **Fingerprint-based detection** - Only syncs when metadata actually changes (based on content fingerprints)
3. **First-time sync** - Sports that have never been synced will auto-sync on first run
4. **Field locking** - Locks Plex fields after updating to prevent metadata refresh from overwriting

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `PLEX_URL` | Plex server URL |
| `PLEX_TOKEN` | Plex authentication token |
| `PLEX_LIBRARY_ID` | Target library ID |
| `PLEX_LIBRARY_NAME` | Target library name (fallback) |
| `PLEX_SYNC_ENABLED` | Enable/disable sync |
| `PLEX_FORCE` | Force all updates |
| `PLEX_SYNC_DRY_RUN` | Dry-run mode |
| `PLEX_SPORTS` | Comma-separated sport IDs to sync |

### Relationship with Kometa

Plex Metadata Sync and Kometa serve complementary purposes:

- **Plex Metadata Sync** - Pushes TheTVSportsDB metadata (titles, summaries, artwork) to Plex
- **Kometa** - Creates collections, applies overlays, and handles advanced library management

You can use both together: Plex Metadata Sync keeps episode data fresh, while Kometa handles collections and visual customizations.

## Kometa Metadata

Point Kometa at metadata YAML feeds so Plex shows canonical titles, posters, and collections. Start by wiring a `libraries` block:

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
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/wsbk-2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/wssp-2025.yaml
```

1. List the metadata YAML feeds for your sports (feeds live under `s0len/meta-manager-config`).
2. Use a single Kometa library (e.g., `Sport`) to collect all sports series; Kometa handles per-show organization via the YAML metadata.
3. Schedule Kometa normally (cron, k8s CronJob) so it still refreshes on its own, then layer Playbook triggers for instant updates.

> **Note:** Playbook now fetches metadata from TheTVSportsDB API, not YAML files. Kometa can still use YAML feeds for its own metadata operations—they're maintained in parallel.

### Kometa Triggering from Playbook {#kometa-triggering}

Configure `settings.kometa_trigger` so Playbook nudges Kometa only when new files were linked. Trigger modes:

| Mode | When to use | Requirements |
|------|-------------|--------------|
| `kubernetes` | Playbook and Kometa live in the same cluster. Clone an existing CronJob spec. | Service account with permission to read/clone the CronJob. |
| `docker` | Kometa runs as a standalone container or via Docker Compose. | Mount Docker socket & binaries into the Playbook container, or run Playbook on the host. |
| `docker exec` | Kometa is already running (`docker-compose up`). | Set `docker.container_name` (plus optional `exec_python`/`exec_script`). |

#### Kubernetes CronJob Trigger

```yaml
settings:
  kometa_trigger:
    enabled: true
    mode: kubernetes
    namespace: media
    cronjob_name: kometa-sport
    job_name_prefix: kometa-sport-triggered-by-playbook
```

Playbook clones the CronJob's `jobTemplate`, labels jobs with `trigger=playbook`, and logs the job name so you can `kubectl logs job/<name>` later.

#### Docker Run / Exec Trigger

```yaml
settings:
  kometa_trigger:
    enabled: true
    mode: docker
    docker:
      binary: docker
      image: kometateam/kometa
      config_path: /srv/media/Kometa/config
      libraries: "Sports|TV Shows - 4K"
      extra_args:
        - --config
        - /config/config.yml
```

Under the hood Playbook runs:

```bash
docker run --rm \
  -v "/srv/media/Kometa/config:/config:rw" \
  kometateam/kometa \
  --run-libraries "Sports|TV Shows - 4K" \
  --config /config/config.yml
```

Already running Kometa via Docker Compose? Set `docker.container_name` (plus optional `exec_python` / `exec_script`) and Playbook will call `docker exec` instead of spinning up a new container. For absolute control, provide `docker.exec_command` (e.g., `["python3", "/app/kometa/kometa.py"]`) and Playbook will append `libraries`/`extra_args`.

##### Docker prerequisites inside the Playbook container

- Mount `/var/run/docker.sock` so the daemon is reachable.
- Mount the client binaries (paths differ per host; use `command -v docker`). Example:

  ```bash
  -v $(command -v docker):/usr/local/bin/docker \
  -v $(command -v com.docker.cli):/usr/local/bin/com.docker.cli
  ```

##### Manual Trigger CLI

Use `python -m playbook.cli kometa-trigger --config /config/playbook.yaml --mode docker` when you want to test the integration without a full ingest run. Logs are captured inside `playbook.log`, so failed triggers show up alongside the main processor output. Combine it with `--verbose --log-level DEBUG` to watch the exact docker command invoked.

##### Kometa troubleshooting

- `Kometa trigger is disabled` – enable `settings.kometa_trigger.enabled` or pass `--mode docker` / `--mode kubernetes` to the CLI.
- `Kometa docker trigger requires access to the Docker socket` – mount `/var/run/docker.sock` plus the Docker client binary.
- Stuck jobs in Kubernetes? `kubectl delete job -l trigger=playbook` to clear out previous runs before trying again.
- Need a dry run? Set `kometa_trigger.enabled: false`, run Playbook once to ensure filenames look good, then re-enable and re-run.

## Autobrr Download Automation

Playbook expects files to appear in `SOURCE_DIR`. When you want to automate torrent grabs, Autobrr pairs well with the built-in pattern packs.

### Basic Setup

1. Create a filter per sport (e.g., `F1 1080p MWR`, `EPL 1080p NiGHTNiNJAS`).
2. Select trackers that carry those releases.
3. Under **Advanced → Release names → Match releases**, paste regexes that encode sport/year/resolution/release-group.
4. Assign a dedicated category/tag so your downloader routes sports torrents into the Playbook `SOURCE_DIR`.
5. Use Autobrr’s `Actions` to push directly into qBittorrent/Deluge, or fire off a webhook/exec script for bespoke flows.

Sample filter (partial TOML):

```--8<-- "snippets/autobrr-filter.md"```

### Sample Regexes

```text
# Premier League (EPL) 1080p releases by NiGHTNiNJAS
epl.*1080p.*nightninjas

Playbook also swallows the non-dotted drops (`EPL 2025 Fulham vs Manchester City 02 12 …`) and normalizes common nicknames (`Leeds`, `Man City`, etc.) so you can keep a single filter for every encoder variant.

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

Tips:

- UFC releases now **must** include the matchup slug (e.g., `UFC 322 Della Maddalena vs Makhachev`) so Playbook can align each file with the correct metadata season.
- Test regexes via Autobrr’s built-in tester or an interactive `ripgrep --pcre2` session before enabling filters.
- When multiple release groups upload the same events, use Autobrr’s `required_words`/`excluded_words` to prefer trusted encoders.
- Keep filters narrow—use separate rules for 1080p vs 2160p, English vs multi-audio, etc.—so Playbook can rely on deterministic naming.

## Plex Library Setup

1. In the Plex UI, **Libraries → Add Library → TV Shows**.
2. Name it something like `Sports`.
3. Point the folder at the same `DESTINATION_DIR` (or the sports subdirectory) that Playbook writes to.
4. Under **Advanced**:
   - Scanner: `Plex Series Scanner`
   - Agent: `Personal Media Shows`
   - Episode sorting: `Newest first`
5. Run **Scan Library Files** after Playbook populates the destination folder.

This pairing ensures Plex treats every season/session as canonical TV episodes while Kometa layers metadata on top.

When using Kometa:

- Create the library first, run a manual **Scan Library Files**, then let Kometa populate posters/collections.
- Keep the Playbook destination mounted read-only inside Plex if you want extra protection against accidental edits.
- Pair Plex with [Autoscan](#autoscan-hooks) to avoid delayed library scans.

## Autoscan Hooks

Add an `autoscan` notification target to retrigger Plex/Emby/Jellyfin scans immediately after new files are linked:

```--8<-- "snippets/notifications-autoscan.md"```

### ⚠️ Security Warning: SSL/TLS Verification

**IMPORTANT:** The `verify_ssl` setting controls SSL/TLS certificate verification for HTTPS connections to Autoscan. Disabling this verification (`verify_ssl: false`) exposes your system to **man-in-the-middle (MITM) attacks** where an attacker can intercept and modify the communication between Playbook and Autoscan.

- **Production environments:** ALWAYS keep `verify_ssl: true` (the default)
- **Development/testing only:** `verify_ssl: false` may be used temporarily with self-signed certificates, but you should properly configure certificate trust stores instead
- **Better alternatives:** Add self-signed certificates to your system's trust store or use a proper CA-signed certificate rather than disabling verification

Guidelines:

- `rewrite` entries translate Playbook's container paths into whatever Autoscan/Plex can see (add as many mappings as needed).
- Combine Autoscan pings with watcher mode for near-instant Plex updates—new files drop, Playbook links them, Autoscan triggers a scan.
- Want extra resiliency? Keep one Autoscan target per Plex server/library pair so failures are isolated.

Need end-to-end walkthroughs? Jump to [Recipes & How-tos](recipes.md).
