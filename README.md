# Playbook

[![License: GPLv3](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776ab.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Fs0len%2Fplaybook-0db7ed.svg?logo=docker&logoColor=white)](https://github.com/users/s0len/packages/container/package/playbook)

> Metadata-driven automation that turns chaotic sports releases into Plex-perfect TV libraries—no brittle scripts, just declarative YAML.

## Overview

Playbook ingests authoritative YAML feeds, matches releases to canonical episodes, and renders deterministic folder/file structures for Plex, Jellyfin, or Kodi. Everything is configuration-driven—swap leagues, release groups, or folder formats by editing YAML, not Python.

## Quickstart

| Environment | Command | Docs |
|-------------|---------|------|
| Docker (recommended) | `docker run --rm -it -e DRY_RUN=true -e SOURCE_DIR=/downloads -e DESTINATION_DIR=/library -e CACHE_DIR=/cache -v /config:/config -v /downloads:/data/source -v /library:/data/destination -v /cache:/var/cache/playbook ghcr.io/s0len/playbook:latest --dry-run --verbose` | [Getting Started → Docker](docs/getting-started.md#option-a-docker-recommended) |
| Python | `python -m playbook.cli --config /path/to/playbook.yaml --dry-run --verbose` | [Getting Started → Python](docs/getting-started.md#option-b-python-environment) |
| Kubernetes | Flux HelmRelease sample under `docs/getting-started.md#option-c-kubernetes-flux-helmrelease` | [Getting Started → Kubernetes](docs/getting-started.md#option-c-kubernetes-flux-helmrelease) |

1. Copy `config/playbook.sample.yaml`, set `SOURCE_DIR`, `DESTINATION_DIR`, `CACHE_DIR`, and enable the sports you care about.  
2. Run the Docker dry-run (above) to warm caches and validate permissions.  
3. Point Plex/Kometa at the destination directory once the layout looks right.

## Documentation

Full docs live at **https://s0len.github.io/Playbook/** (Material for MkDocs). Highlights:

- [Getting Started](docs/getting-started.md) – install paths, environment prep, first-run checklist.
- [Configuration Guide](docs/configuration.md) – YAML schema, notifications, pattern packs, variants.
- [Operations & Run Modes](docs/operations.md) – CLI flags, watcher vs batch, logging, upgrades.
- [Integrations](docs/integrations.md) – Kometa triggers, Autobrr filters, Autoscan hooks, Plex setup.
- [Recipes & How-tos](docs/recipes.md) – sport-specific walkthroughs, regex samples, customization.
- [Troubleshooting & FAQ](docs/troubleshooting.md) – diagnostics, cache resets, common pitfalls.
- [Developer Guide](docs/developer-guide.md) – repo setup, testing, branching, release workflow.
- [Changelog](docs/changelog.md) – surfaced in the docs nav, sourced from `CHANGELOG.md`.

Run `make docs-serve` for a live preview while editing docs locally.

## Why Playbook?

- **Metadata-first** – Pull official titles, rounds, and air dates straight from curated YAML feeds.  
- **Pattern intelligence** – Regex packs + alias tables map messy release names onto canonical episodes.  
- **Deterministic templating** – Consistent folder/file naming keeps Plex/Jellyfin scans predictable.  
- **Observability built-in** – Structured console output, rotating log files, Kometa/autoscan summaries.  
- **Automation ready** – Run once, keep a watcher alive, or deploy to Kubernetes with Kometa triggers.  
- **Declarative workflows** – Extend to new sports by editing YAML instead of rewriting scripts.

## Support & Links

- [Issue tracker](https://github.com/s0len/playbook/issues) – bugs, feature requests, doc gaps.  
- [Discussions](https://github.com/s0len/playbook/discussions) – design chats, metadata feed requests.  
- Need bespoke integrations? Open an issue with logs + anonymized config snippets (redact secrets).

## Development

```bash
git clone https://github.com/s0len/playbook.git
cd playbook
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # pytest + mkdocs-material
```

- Run tests: `pytest`.  
- Sample validation: edit `tests/data/pattern_samples.yaml` then `pytest tests/test_pattern_samples.py`.  
- Docs preview: `make docs-serve`. Build: `make docs-build`. Deploy (maintainers): `make docs-deploy`.  
- Container build: `docker build -t playbook:dev .`.

Branching & release workflow lives in [docs/developer-guide.md](docs/developer-guide.md). TL;DR: feature branches → `develop`, release tags from `main`, and a docs-build GitHub Action keeps Pages in sync.

## License & Changelog

- License: [GNU GPLv3](LICENSE).  
- Changelog: [CHANGELOG.md](CHANGELOG.md) (also surfaced in the docs sidebar).  
- Releases: tagged from `main` (e.g., `v1.4.0`) once docs + code land together.

Enjoy the automation—PRs and doc fixes welcome!


