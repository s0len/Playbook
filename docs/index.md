# Playbook Documentation

Metadata-driven automation that turns chaotic sports releases into Plex-perfect TV libraries. Playbook ingests authoritative YAML feeds, matches releases to canonical episodes, and renders deterministic folder/file structures so Plex, Jellyfin, and Kometa stay perfectly in sync.

## Highlights

- Declarative YAML: switch leagues, release groups, or folder formats without touching Python.
- Built-in pattern packs and alias tables for F1, MotoGP, Isle of Man TT, UFC, NFL, NBA, and more.
- Multiple run modes (batch CLI, long-lived watcher, Docker, Kubernetes) with Kometa/autoscan hooks.
- First-class observability: rich console output, rotating log files, and structured summaries per run.

## Quickstart

1. Copy `config/playbook.sample.yaml` to `playbook.yaml`, tune `SOURCE_DIR`, `DESTINATION_DIR`, `CACHE_DIR`, and enable the sports you care about.
2. Dry-run the Docker image (or local CLI) to warm caches and validate permissions.
3. Wire Plex/Kometa to the destination directory once you're happy with the library layout.

Detailed installation paths (Docker, Python, Kubernetes) live in [Getting Started](getting-started.md). For local doc previews run `make docs-serve` and visit `http://127.0.0.1:8000`.

## Documentation Map

- [Getting Started](getting-started.md) – installation paths, environment prep, first-run checklist.
- [Configuration Guide](configuration.md) – YAML schema, notifications, pattern sets, templating, variants.
- [Operations & Run Modes](operations.md) – CLI flags, watcher vs batch, logging, upgrades, backups.
- [Integrations](integrations.md) – Kometa triggers, Autobrr filters, Autoscan hooks, Plex setup.
- [Recipes & How-tos](recipes.md) – sport-specific walkthroughs, regex samples, customization playbooks.
- [Troubleshooting & FAQ](troubleshooting.md) – diagnostics, cache resets, common pitfalls.
- [Developer Guide](developer-guide.md) – repo setup, testing, contributing, release workflow.
- [Changelog](changelog.md) – latest releases and doc references.

Looking for something else? Use the search box (Material for MkDocs) or open an issue with your documentation request.
