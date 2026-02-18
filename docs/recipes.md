# Recipes & How-tos

These walkthroughs illustrate how to adapt Playbook to new sports, tune regexes, and validate results quickly. Use them as repeatable playbooks for common tasks.

## Quick Reference

| Scenario | Recipe |
|----------|--------|
| Onboard a new sport | [Extending to New Sports](#extending-to-new-sports) |
| Tweak per-league notifications | [Customizing Notifications per Sport](#customizing-notifications-per-sport) |
| Build downloader filters | [Autobrr Filter Walkthrough](#autobrr-filter-walkthrough) |
| Vet pattern changes safely | [Testing Pattern Changes Quickly](#testing-pattern-changes-quickly) |
| Validate metadata-driven workflows | [ISU Figure Skating Example](#sample-isu-figure-skating-workflow) |

## Extending to New Sports

1. Copy `config/playbook.sample.yaml` and enable the sport by listing the relevant `pattern_sets` (e.g., `formula1`, `motogp`).
2. Set `show_slug` to reference the show in TVSportsDB, and configure `source_globs` and `source_extensions` for your release group.
3. If no template exists yet, copy the closest set from `src/playbook/pattern_templates.yaml` into your config and adjust the regex/aliases.
4. Run `python -m playbook.cli --config playbook.yaml --dry-run --verbose` and review both console output and `playbook.log` for skipped/ignored diagnostics.
5. Iterate on patterns, aliases, and destination templates until every file links where you expect. Consider upstreaming new templates via a PR once battle-tested.

### Checklist

- [ ] Show exists in TVSportsDB with the specified `show_slug`.
- [ ] TVSportsDB API reachable from the container/host.
- [ ] `pattern_sets` entries spelled exactly as defined in `src/playbook/pattern_templates.yaml`.
- [ ] Regex capture groups line up with `season_selector` and `episode_selector`.
- [ ] Notifications configured for the new `sport_id`.
- [ ] `tests/data/pattern_samples.yaml` updated with at least one real release name.

## Sample ISU Figure Skating Workflow

The `isu_figure_skating` pattern set handles all ISU competitions (Grand Prix, Europeans, Four Continents, Worlds) with `show_slug: "isu-figure-skating-2025-2026"`. Example releases:

- `Figure Skating Grand Prix France 2025 Pairs Short Program 17 10 720pEN50fps ES`
- `ISU Figure Skating Grand Prix China 2025 Ice Dancing Rhythm Dance 18 10`
- `European Figure Skating Championships Sheffield 2026 Men Free Program 17 01`
- `ISU World Figure Skating Championships 2026 Women Free Program 26 03`

Tips:

- The pattern set includes 7 patterns covering all major ISU competitions.
- When releases omit round numbers, use `season_selector.mode: title` plus `session_aliases` to map `Rhythm Dance`/`Free Program` onto canonical metadata.
- Add `destination.filename_template` overrides if you need federation-specific folder structures (`{season_round:02} {season_title}` works well for multi-stop tours).
- Keep `allow_unmatched: true` during onboarding to reduce noise while you iterate on regexes.

## Customizing Notifications per Sport

Use `notifications.mentions` to ping only the subscribers who care about a specific league:

```yaml
notifications:
  mentions:
    formula1: "<@&222333444555666777>"
    premier_league: "<@&123456789012345678>"
    default: "@here"
```

Recipes:

- Override mentions per target to opt certain Discord webhooks into extra pings.
- Mix `autoscan` targets with Discord webhooks so watchers get immediate scans plus human-friendly summaries.
- Gate daily batch posts through `notifications.batch_daily` + `notifications.flush_time` (e.g., set `flush_time: "06:00"` so overnight events roll into the previous “day”).

## Autobrr Filter Walkthrough

Autobrr filters keep Playbook’s `SOURCE_DIR` populated with trusted releases. Start from this template:

```--8<-- "snippets/autobrr-filter.md"```

How to adapt it:

1. Update `match_releases` with sport/year/resolution-specific regexes.
2. Use `required_words` / `excluded_words` for release-group whitelisting.
3. Set `actions` to push directly into qBittorrent/Deluge with the correct category, or trigger custom scripts/webhooks.
4. Run Autobrr’s regex tester before enabling the filter, then monitor the “History” tab to confirm matches.

Pair each Autobrr category with a dedicated Playbook sport (or variant) so `source_globs` stay simple.

## Testing Pattern Changes Quickly

- Edit `tests/data/pattern_samples.yaml` with real release names and run `pytest tests/test_pattern_samples.py`.
- Combine `--dry-run` with `VERBOSE=true` to see every capture group and template rendered in the console.
- Use `--clear-processed-cache` when you need to reprocess the same files repeatedly during regex tuning.
- Add `--trace-matches` to dump match JSON artifacts into `cache_dir/traces`, then inspect them with your favorite JSON viewer.

## Validation Runbook

1. `python -m playbook.cli validate-config --config playbook.yaml --diff-sample --show-trace`.
2. `python -m playbook.cli --config playbook.yaml --dry-run --verbose --trace-matches`.
3. Inspect `playbook.log` for warnings, unmatched files, or Kometa/Autoscan issues.
4. Tail notifications (Discord/Slack) to ensure new sports trigger the right channels.
5. Promote changes to a staging environment (or run the Docker image with bind mounts) before rolling to production.

Have a favorite workflow that should live here? Open an issue or PR and drop it under `docs/recipes.md`.
