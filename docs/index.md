# Playbook Documentation

**Sonarr for Sports** – Automated file matching, renaming, and metadata for sports content in Plex.

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

## Quickstart

**All sports are enabled by default!** Just configure your directories:

1. Copy `config/playbook.sample.yaml` to `playbook.yaml`
2. Set `SOURCE_DIR` (where downloads land) and `DESTINATION_DIR` (Plex library)
3. Run a dry-run to test: `playbook process --dry-run`
4. Let it run automatically with `playbook watch` or Docker

That's it! Playbook automatically processes Formula 1, MotoGP, UFC, NFL, NBA, NHL, Premier League, Champions League, and more. Use `disabled_sports` to exclude any sports you don't want.

See [Getting Started](getting-started.md) for detailed installation (Docker, Python, Kubernetes) or run `make docs-serve` for local docs at `http://127.0.0.1:8000`.

## Documentation Map

- [Getting Started](getting-started.md) – installation, environment setup, first-run checklist
- [Configuration Guide](configuration.md) – YAML schema, patterns, notifications, templating
- [Operations & Run Modes](operations.md) – CLI commands, watcher mode, logging, upgrades
- [Integrations](integrations.md) – Kometa triggers, Autobrr filters, Autoscan, Plex setup
- [Recipes & How-tos](recipes.md) – sport-specific walkthroughs, custom patterns, real examples
- [Troubleshooting & FAQ](troubleshooting.md) – diagnostics, cache resets, common issues
- [Developer Guide](developer-guide.md) – contributing, testing, release workflow
- [Changelog](changelog.md) – release notes and version history

---

*Missing something? Use the search box or [open an issue](https://github.com/yourusername/Playbook/issues) with your question.*