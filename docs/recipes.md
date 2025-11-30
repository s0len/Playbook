# Recipes & How-tos

These walkthroughs illustrate how to adapt Playbook to new sports, tweak regexes, and validate results quickly.

## Extending to New Sports

1. Copy `config/playbook.sample.yaml` and enable the sport by listing the relevant `pattern_sets` (e.g., `formula1`, `motogp`).
2. Update `metadata.url` / `show_key`, `source_globs`, and `source_extensions` for your release group.
3. If no template exists yet, copy the closest set from `src/playbook/pattern_templates.yaml` into your config and adjust the regex/aliases.
4. Run `python -m playbook.cli --config playbook.yaml --dry-run --verbose` and review both console output and `playbook.log` for skipped/ignored diagnostics.
5. Iterate on patterns, aliases, and destination templates until every file links where you expect. Consider upstreaming new templates via a PR once battle-tested.

## Sample Figure Skating Grand Prix Workflow

Pair the `figure_skating_grand_prix` pattern set with the [Figure Skating Grand Prix 2025 metadata feed](https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/figure-skating-grand-prix-2025.yaml) to normalize releases such as:

- `Figure Skating Grand Prix France 2025 Pairs Short Program 17 10 720pEN50fps ES`
- `Figure Skating Grand Prix France 2025 Ice Dancing Rhythm Dance 18 10 720pEN50fps ES`
- `Figure Skating Grand Prix China 2025 Exhibition Gala 26 10 720pEN50fps ES`
- `Figure Skating Grand Prix Final 2025 Women Free Program 06 12 1080pEN50fps.mkv`

Tips:

- When releases omit round numbers, use `season_selector.mode: title` plus `session_aliases` to map `Rhythm Dance`/`Free Program` onto canonical metadata.
- Add `destination.filename_template` overrides if you need federation-specific folder structures (`{season_round:02} {season_title}` works well for multi-stop tours).

## Customizing Notifications per Sport

Use `notifications.mentions` to ping only the subscribers who care about a specific league:

```yaml
notifications:
  mentions:
    formula1: "<@&222333444555666777>"
    premier_league: "<@&123456789012345678>"
    default: "@here"
```

You can override mentions per target, mix `autoscan` triggers with Discord webhooks, and gate daily batch posts through `notifications.batch_daily` + `notifications.flush_time`.

## Testing Pattern Changes Quickly

- Edit `tests/data/pattern_samples.yaml` with real release names and run `pytest tests/test_pattern_samples.py`.
- Combine `--dry-run` with `VERBOSE=true` to see every capture group and template rendered in the console.
- Use `--clear-processed-cache` when you need to reprocess the same files repeatedly during regex tuning.

Have a favorite workflow that should live here? Open an issue or PR and drop it under `docs/recipes.md`.
# Recipes & How-tos

These walkthroughs illustrate how to adapt Playbook to new sports, tweak regexes, and validate results quickly.

## Extending to New Sports

1. Copy `config/playbook.sample.yaml` and enable the sport by listing the relevant `pattern_sets` (e.g., `formula1`, `motogp`).
2. Update `metadata.url` / `show_key`, `source_globs`, and `source_extensions` for your release group.
3. If no template exists yet, copy the closest set from `src/playbook/pattern_templates.yaml` into your config and adjust the regex/aliases.
4. Run `python -m playbook.cli --config playbook.yaml --dry-run --verbose` and review both console output and `playbook.log` for skipped/ignored diagnostics.
5. Iterate on patterns, aliases, and destination templates until every file links where you expect. Consider upstreaming new templates via a PR once battle-tested.

## Sample Figure Skating Grand Prix Workflow

Pair the `figure_skating_grand_prix` pattern set with the [Figure Skating Grand Prix 2025 metadata feed](https://raw.githubusercontent.com/s0len/meta-manager-config/refs/heads/main/metadata/figure-skating-grand-prix-2025.yaml) to normalize releases such as:

- `Figure Skating Grand Prix France 2025 Pairs Short Program 17 10 720pEN50fps ES`
- `Figure Skating Grand Prix France 2025 Ice Dancing Rhythm Dance 18 10 720pEN50fps ES`
- `Figure Skating Grand Prix China 2025 Exhibition Gala 26 10 720pEN50fps ES`
- `Figure Skating Grand Prix Final 2025 Women Free Program 06 12 1080pEN50fps.mkv`

Tips:

- When releases omit round numbers, use `season_selector.mode: title` plus `session_aliases` to map `Rhythm Dance`/`Free Program` onto canonical metadata.
- Add `destination.filename_template` overrides if you need federation-specific folder structures (`{season_round:02} {season_title}` works well for multi-stop tours).

## Customizing Notifications per Sport

Use `notifications.mentions` to ping only the subscribers who care about a specific league:

```yaml
notifications:
  mentions:
    formula1: "<@&222333444555666777>"
    premier_league: "<@&123456789012345678>"
    default: "@here"
```

You can override mentions per target, mix `autoscan` triggers with Discord webhooks, and gate daily batch posts through `notifications.batch_daily` + `notifications.flush_time`.

## Testing Pattern Changes Quickly

- Edit `tests/data/pattern_samples.yaml` with real release names and run `pytest tests/test_pattern_samples.py`.
- Combine `--dry-run` with `VERBOSE=true` to see every capture group and template rendered in the console.
- Use `--clear-processed-cache` when you need to reprocess the same files repeatedly during regex tuning.

Have a favorite workflow that should live here? Open an issue or PR and drop it under `docs/recipes.md`.
