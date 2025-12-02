# Configuration Guide

Every Playbook deployment runs from a single YAML file. Start by copying `config/playbook.sample.yaml`, then enable sports, pattern sets, and integrations one section at a time. This guide mirrors the dataclasses under `src/playbook/config.py`.

## 1. Global Settings

| Field | Description | Default |
|-------|-------------|---------|
| `source_dir` | Root directory containing downloads to normalize. | `/data/source` |
| `destination_dir` | Library root where organized folders/files are created. | `/data/destination` |
| `cache_dir` | Metadata cache directory (`metadata/<sha1>.json`). Safe to delete to force refetch. | `/data/cache` |
| `dry_run` | When `true`, logs intent but skips filesystem writes. | `false` |
| `skip_existing` | Leave destination files untouched unless a higher-priority release arrives. | `true` |
| `link_mode` | Default link behavior: `hardlink`, `copy`, or `symlink`. | `hardlink` |
| `file_watcher.enabled` | Keeps Playbook running and reacts to filesystem events. | `false` |
| `file_watcher.paths` | Directories to observe; defaults to `source_dir` when empty. | `[]` |
| `file_watcher.include` / `ignore` | Glob filters to allow/skip events (e.g., ignore `*.part`). | `[]` / `["*.part","*.tmp"]` |
| `file_watcher.debounce_seconds` | Minimum seconds between watcher-triggered runs. | `5` |
| `file_watcher.reconcile_interval` | Forces a full scan every _N_ seconds even if no events arrive. | `900` |
| `destination.*` | Default templates for root folder, season folder, and filename. | See sample |

### Notifications & Autoscan

Define Discord/Slack/webhook/email/autoscan targets under `notifications.targets`. Entries can override mention mappings defined globally:

```yaml
notifications:
  mentions:
    premier_league: "<@&123456789012345678>"
    formula1: "<@&222333444555666777>"
    default: "@everyone"
  targets:
    - type: discord
      webhook_env: DISCORD_WEBHOOK_URL
      # webhook_url: ${DISCORD_WEBHOOK_URL}  # Optional inline expansion if your config templating supports it.
      mentions:
        formula1: "<@&999>"
    - type: autoscan
      url: http://autoscan:3030
      trigger: manual
      rewrite:
        - from: ${DESTINATION_DIR:-/data/destination}
          to: /mnt/unionfs/Media
```

Set `webhook_env` to the name of an environment variable (in your container/host manifest) to keep secrets out of the YAML file. Playbook resolves the value at runtime and skips the target if the variable is absent. If you already template the config file yourself you can keep using `webhook_url` with `${VAR}` syntax; both approaches continue to work.

Autoscan entries mirror the [manual trigger](https://github.com/Cloudbox/autoscan?tab=readme-ov-file#manual). Rewrites translate container paths to Plex-visible mount points. Every successful `new`/`changed` event sends the parent directory of the destination file.

**Supported target types**

- `discord` – rich embeds with optional mention overrides per webhook.
- `slack` – simple JSON payload; add your preferred text template.
- `webhook` – fully templatable JSON for custom receivers.
- `email` – SMTP transport with subject/body templates.
- `autoscan` – immediately ping Autoscan so Plex/Jellyfin rescans the destination directories.

Batching knobs (`notifications.batch_daily`, `notifications.flush_time`) apply to any target that supports rolling updates (Discord embeds today). Use `notifications.mentions` to fan out role/user mentions by sport ID (supports shell-style globs), and override them per target when one destination needs custom pings.

#### Autoscan example

```--8<-- "snippets/notifications-autoscan.md"```

Define multiple `rewrite` map entries when Autoscan lives in another container or when Plex views different mount points.

### File Watcher Settings

The watcher keeps Playbook alive and reacts to filesystem events instead of relying solely on periodic scans:

- `file_watcher.paths` defaults to `source_dir`. List additional absolute or relative paths to watch multiple download roots.
- `include` / `ignore` accept glob syntax. Common ignores: `["*.part", "*.tmp", "*.!qb"]`.
- `debounce_seconds` batches bursts of events into a single processor run. Increase it when downloaders generate rapid file-change storms.
- `reconcile_interval` performs a full scan every _N_ seconds even if the platform drops events.
- Override `WATCH_MODE=true|false` (or use `--watch` / `--no-watch`) to force the CLI into the desired mode regardless of the config.

## 2. Sport Entries

Each sport describes metadata, detection filters, and pattern packs:

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
  pattern_sets:
    - formula1
```

Key knobs:

- `enabled` toggles sports without deleting them.
- `source_globs` / `source_extensions` are coarse filters before any regex work happens.
- `link_mode`, `destination.*`, and notification overrides let you specialize behavior per sport.
- `pattern_sets` pulls from `src/playbook/pattern_templates.yaml`; you can still inline `file_patterns` for overrides.

**Metadata overrides**

- `season_overrides` lets you force numbers/titles for special events (exhibitions, pre-season testing, etc.).
- `metadata.ttl_hours` controls how aggressively Playbook refreshes remote YAML feeds; lower it for rapidly changing leagues.
- `allow_unmatched: true` is useful when onboarding a new sport—you’ll still see matches in the log but without warnings.

### Pattern Sets & Reuse

Pattern sets bundle curated regex/alias definitions under `src/playbook/pattern_templates.yaml`. To inspect them:

```bash
rg --context 3 "pattern_sets" src/playbook/pattern_templates.yaml
```

- Reference a bundle via `pattern_sets: ["formula1", "motoGP"]`.
- Layer sport-specific overrides by combining `pattern_sets` with inline `file_patterns`.
- Keep experimental tweaks local until they’re stable, then upstream them by editing `pattern_templates.yaml`.

## 3. Pattern Matching

Inline patterns support full regex/group control:

```yaml
file_patterns:
  - regex: "(?i)^Formula\\.1\\.(?P<year>\\d{4})\\.Round(?P<round>\\d{2})\\.(?P<location>[^.]+)\\.(?P<session>[^.]+)"
    description: Canonical multi-session weekend releases
    priority: 10
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

Reference table:

- `regex` must expose the capture groups consumed by selectors/templates.
- `season_selector` supports `round`, `key`, `title`, and `sequential` modes plus offsets/mappings.
- `episode_selector` chooses which capture identifies an episode; set `allow_fallback_to_title` when a regex omits the session.
- `session_aliases` augment metadata aliases with release-specific tokens (case-insensitive).
- `priority` resolves collisions when multiple patterns match the same file.

**Testing patterns quickly**

1. Drop real release names into `tests/data/pattern_samples.yaml`.
2. Run `pytest tests/test_pattern_samples.py` to confirm they map to the expected metadata.
3. Use `python -m playbook.cli --config playbook.yaml --dry-run --verbose` with `--clear-processed-cache` to reprocess the same files repeatedly during tuning.

## 4. Destination Templating

Templates receive a rich context assembled from metadata + regex captures:

| Key | Meaning |
|-----|---------|
| `sport_id`, `sport_name` | Sport metadata from the config. |
| `show_title`, `show_key` | Raw and display titles from the metadata feed. |
| `season_title`, `season_number`, `season_round`, `season_year` | Season context with overrides applied. |
| `episode_title`, `episode_number`, `episode_summary`, `episode_originally_available` | Episode metadata pulled from the feed. |
| `location`, `session`, `round`, … | Any capture group from the regex. |
| `source_filename`, `extension`, `relative_source` | Safe access to the original file path. |

Set per-sport or per-pattern overrides (`destination.root_template`, `destination.filename_template`) whenever a league needs special formatting.

Tips:

- Append `{suffix}` to preserve any release-group decorations that survived sanitization.
- Use conditionals in templates (Jinja syntax) for optional segments, e.g., `{% if episode_originally_available %}...{% endif %}`.
- The renderer automatically normalizes whitespace and strips forbidden path characters—keep templates readable and let Playbook worry about sanitization.
- Override `destination.season_folder_template` to group rounds (e.g., `{season_round:02} {season_title}` for touring series).

## 5. Variants & Reuse

Reuse a base sport definition across seasons or release groups:

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

Each variant inherits fields from the parent, tweaks whatever is listed inside the variant block, and gets an auto-generated `id`/`name` when not explicitly set. Use variants when only the metadata URL or alias table changes year-to-year.

## Validation Workflow

1. Run `python -m playbook.cli validate-config --config /config/playbook.yaml --diff-sample` to catch schema errors early.
2. Add `--show-trace` if you need full Python tracebacks.
3. Commit sample configs to version control and watch the diff returned by the validator to understand exactly what deviated from `playbook.sample.yaml`.

Ready to operate the organizer? Continue to [Operations & Run Modes](operations.md).
