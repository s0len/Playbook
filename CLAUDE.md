# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Playbook is a Python automation tool for organizing sports media files in Plex libraries ("Sonarr for Sports"). It matches files against YAML metadata feeds, renames them, and links them to a Plex-ready library structure.

**Pipeline flow**: Remote YAML / TVSportsDB API → Metadata Normalizer → Matching Engine (regex + aliases + fuzzy) → Templating → File Operations (hardlink/copy/symlink)

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev,gui]        # Editable install with dev + GUI deps
pre-commit install               # Ruff lint+format on commit
```

## Common Commands

```bash
# Run tests
pytest                                    # Full suite
pytest tests/test_matcher.py              # Single file
pytest tests/test_matcher.py::TestClass::test_method  # Single test
pytest -k "keyword"                       # Filter by name
pytest --lf                               # Re-run last failed

# Lint and format (Ruff)
ruff check .                              # Lint
ruff check . --fix                        # Auto-fix
ruff format .                             # Format
make check                                # Both lint + format check

# Run CLI locally
python -m playbook.cli --config config/config.sample.yaml --dry-run --verbose

# Validate config
python -m playbook.cli validate-config --config /path/to/config.yaml --diff-sample

# Debug pattern matching
python -m playbook.cli --dry-run --verbose --trace-matches  # Writes JSON to cache_dir/traces

# Documentation
make docs-serve                           # Live preview at http://127.0.0.1:8000
make docs-build                           # Build static site

# Bootstrap clean environment and run tests
bash scripts/bootstrap_and_test.sh
```

**Minimum loop after small changes**: `ruff check . && pytest -k "relevant_keyword"`

## Architecture

### Core Pipeline (`src/playbook/`)

- `processor.py` — Main `Processor` class orchestrating the full pipeline per run
- `config.py` — Configuration dataclasses (`AppConfig`, `Settings`, `SportConfig`, `PatternConfig`). Keep in sync with `validation.py`
- `metadata.py` / `metadata_loader.py` — Fetch, cache, normalize YAML metadata feeds; `DynamicMetadataLoader` supports on-demand loading per sport/year
- `file_discovery.py` — Source file scanning with glob filtering
- `destination_builder.py` — Template-driven path construction with context variables
- `match_handler.py` — File linking (hardlink/copy/symlink), overwrite decisions, conflict resolution
- `watcher.py` — Filesystem monitoring with debouncing (watchdog)
- `cli.py` — Entry point with subcommands (run, validate-config, kometa-trigger)

### Matcher Package (`src/playbook/matcher/`)

The matcher is a multi-module package, not a single file:
- `orchestrator.py` — Entry points: `compile_patterns()`, `match_file_to_episode()`
- `core.py` — `PatternRuntime` (compiled regex + session lookup)
- `season_selector.py` / `episode_selector.py` — Season/episode resolution from regex capture groups
- `session_resolver.py` — Build session lookup indices for alias-based matching
- `similarity.py` — Fuzzy matching via rapidfuzz
- `structured.py` — Structured filename matching (parsed tokens vs regex)
- `team_resolver.py` — Team name/alias resolution
- `date_utils.py` — Date parsing helpers for date-based season selection

### Persistence (`src/playbook/persistence/`)

SQLite-backed storage layer:
- `processed_store.py` — Tracks successfully processed files
- `unmatched_store.py` — Tracks failed matches with `MatchAttempt` details
- `manual_override_store.py` — User overrides for match corrections
- `metadata_cache.py` — TTL-based API response cache

### Storage Model

Two separate directories — keep this distinction when modifying file paths:
- `state_dir` (default `/config/state`): SQLite databases, durable app state. Must persist across restarts.
- `cache_dir` (default `/data/cache`): Metadata cache, trace artifacts. Disposable/temporary.

### GUI (`src/playbook/gui/`)

NiceGUI-based web interface (optional dependency `nicegui`):
- `app.py` — Entry point (`run_with_gui()`), env var overrides must be applied before creating `Processor`
- `state.py` — Shared `gui_state` singleton
- `pages/` — Dashboard, sports browser, settings, logs, unmatched files
- `components/` — Reusable UI components (settings editors, activity feed, stats cards)

### TVSportsDB Integration (`src/playbook/tvsportsdb/`)

API client for the TVSportsDB backend (alternative metadata source):
- `client.py` — HTTP client
- `adapter.py` — Converts API responses to Playbook `Show`/`Season`/`Episode` models
- `cache.py` — Response caching

### Other Key Modules

- `models.py` — Domain models: `Show`, `Season`, `Episode`, `SportFileMatch`, `ProcessingStats`
- `pattern_templates.py` / `pattern_templates.yaml` — Built-in regex packs for F1, MotoGP, UFC, NFL, NBA, NHL, etc.
- `quality_scorer.py` / `quality.py` — File quality scoring and comparison
- `notifications/` — Discord, Slack, Webhook, Email, Autoscan, Plex scan
- `kometa_trigger.py` — Integration with Kometa for Plex metadata
- `plex_metadata_sync.py` — Direct Plex library synchronization
- `reconciliation.py` — File reconciliation between source and destination

## Testing

- **Framework**: pytest 8+
- **Location**: `tests/` directory, path setup in `tests/conftest.py` adds `src/` to sys.path
- **Key test files**: `test_matcher.py` (pattern matching), `test_validation.py` (config), `test_processor.py` (orchestration)
- **Pattern samples**: After editing patterns or matcher logic, add filenames to `tests/data/pattern_samples.yaml` and run `pytest tests/test_pattern_samples.py`

## Code Conventions

- **Ruff** is the source of truth for lint + format. Line length 120, double quotes, Python 3.12+.
- Use `from __future__ import annotations` at top of modules (repo convention).
- Use `TYPE_CHECKING` for type-only imports. Prefer `list[str]`, `dict[str, Any]`, `X | None` over `Optional`/`List`/`Dict`.
- Module logger pattern: `LOGGER = logging.getLogger(__name__)`.
- Config dataclasses (`config.py`) and validation schema (`validation.py`) must stay in sync.
- Preserve dry-run semantics: no filesystem side effects when `dry_run=True`.

## Branching

- `develop` — Day-to-day feature work
- `main` — Latest tagged release
- Feature branches: `feature/<area>-<description>`
