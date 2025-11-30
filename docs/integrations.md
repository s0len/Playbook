# Integrations

Playbook focuses on filesystem organization and leaves downloading, metadata enrichment, and library refreshes to the tools that already excel at those jobs. This guide summarizes the supported integrations.

## Kometa Metadata

Point Kometa at the same metadata YAML feeds that Playbook uses so Plex shows canonical titles, posters, and collections:

```yaml
libraries:
  Sport:
    metadata_files:
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/formula1/2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/formula-e/2025-2026.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/indycar-2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/isle-of-man-tt.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/moto2-2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/moto3-2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/motogp-2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/nba/2025-2026.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/nfl/2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/premier-league/2025-2026.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/uefa-champions-league/2025-2026.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/ufc/2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/womens-uefa-euro.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/wsbk-2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/wssp-2025.yaml
      - url: https://raw.githubusercontent.com/s0len/meta-manager-config/main/metadata/wssp300-2025.yaml
```

### Kometa Triggering from Playbook {#kometa-triggering}

Configure `settings.kometa_trigger` so Playbook nudges Kometa only when new files were linked.

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

Already running Kometa via Docker Compose? Set `docker.container_name` (plus optional `exec_python` / `exec_script`) and Playbook will call `docker exec` instead of spinning up a new container.

##### Docker prerequisites inside the Playbook container

- Mount `/var/run/docker.sock` so the daemon is reachable.
- Mount the client binaries (paths differ per host; use `command -v docker`). Example:

  ```bash
  -v $(command -v docker):/usr/local/bin/docker \
  -v $(command -v com.docker.cli):/usr/local/bin/com.docker.cli
  ```

##### Manual Trigger CLI

Use `python -m playbook.cli kometa-trigger --config /config/playbook.yaml --mode docker` when you want to test the integration without a full ingest run. Logs are captured inside `playbook.log`.

## Autobrr Download Automation

Playbook expects files to appear in `SOURCE_DIR`. When you want to automate torrent grabs, Autobrr pairs well with the built-in pattern packs.

### Basic Setup

1. Create a filter per sport (e.g., `F1 1080p MWR`, `EPL 1080p NiGHTNiNJAS`).
2. Select trackers that carry those releases.
3. Under **Advanced → Release names → Match releases**, paste regexes that encode sport/year/resolution/release-group.

### Sample Regexes

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

# NFL by NiGHTNiNJAS
nfl.*nightninjas

# UFC by VERUM
ufc[ ._-].*?\d{3}.*verum

# WorldSBK / WorldSSP / WorldSSP300 by MWR
(wsbk|wssp|wssp300).*\d{4}.round\d+.[^.]+.(fp\d?|season.preview|superpole|race.one|race.two|war.up(one|two)?|weekend.highlights).*h264.*mwr
```

UFC releases now include the matchup slug (e.g., `UFC 322 Della Maddalena vs Makhachev`) so Playbook can align each file with the correct metadata season.

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

## Autoscan Hooks

Add an `autoscan` notification target to retrigger Plex/Emby/Jellyfin scans immediately after new files are linked:

```yaml
notifications:
  targets:
    - type: autoscan
      url: http://autoscan:3030
      trigger: manual
      rewrite:
        - from: /data/destination
          to: /mnt/unionfs/Media
```

Define additional rewrite mappings when Autoscan lives in another container or when Plex sees different mount points.

Need end-to-end walkthroughs? Jump to [Recipes & How-tos](recipes.md).
