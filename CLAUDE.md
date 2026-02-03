# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Playbook is a Python automation tool for organizing sports media files in Plex libraries ("Sonarr for Sports"). It matches files against YAML metadata feeds, renames them, and links them to a Plex-ready library structure.

**Pipeline flow**: Remote YAML → Metadata Normalizer → Matching Engine (regex + aliases + fuzzy) → Templating → File Operations (hardlink/copy/symlink)

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

# Run CLI locally
python -m playbook.cli --config config/playbook.sample.yaml --dry-run --verbose

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

## Architecture

**Core modules** (`src/playbook/`):
- `processor.py` - Main orchestration, runs the full pipeline
- `config.py` - Configuration parsing, dataclasses for AppConfig/Settings/SportConfig/PatternConfig
- `matcher.py` - Pattern matching: regex capture groups, alias lookup, fuzzy matching (rapidfuzz)
- `metadata.py` / `metadata_loader.py` - Fetch, cache, normalize YAML metadata feeds
- `file_discovery.py` - Source file scanning with glob filtering
- `destination_builder.py` - Template-driven path construction with context variables
- `match_handler.py` - File linking, overwrite decisions, conflict resolution
- `watcher.py` - Filesystem monitoring with debouncing (watchdog)
- `cli.py` - Entry point with subcommands (run, validate-config, kometa-trigger)

**Data models** (`models.py`): `Show`, `Season`, `Episode`, `SportFileMatch`, `ProcessingStats`

**Integrations**:
- `notifications/` - Discord, Slack, Webhook, Email, Autoscan
- `kometa_trigger.py` - Integration with Kometa for Plex metadata
- `plex_metadata_sync.py` - Direct Plex library synchronization

**Pattern templates**: Built-in regex packs in `src/playbook/pattern_templates.yaml` for F1, MotoGP, UFC, NFL, NBA, NHL, etc.

## Testing

- **Framework**: pytest 8+
- **Location**: `tests/` directory (~18,350 lines across 30+ test files)
- **Key test files**: `test_matcher.py` (pattern matching), `test_validation.py` (config), `test_processor.py` (orchestration)
- **Pattern samples**: Add filenames to `tests/data/pattern_samples.yaml`, run `pytest tests/test_pattern_samples.py`
- **Path setup**: `tests/conftest.py` adds `src/` to sys.path

## Code Style

- **Tool**: Ruff (linter + formatter)
- **Line length**: 120 characters
- **Python**: 3.12+
- **Quotes**: Double quotes
- **Pre-commit hooks**: `.pre-commit-config.yaml` (install via `pre-commit install`)

## Key Configuration

- Sample config: `config/playbook.sample.yaml`
- Environment variables: `CONFIG_PATH`, `SOURCE_DIR`, `DESTINATION_DIR`, `CACHE_DIR`, `DRY_RUN`, `VERBOSE`, `LOG_LEVEL`, `WATCH_MODE`
- Pattern sets referenced via `pattern_sets:` in sport configs

## Branching

- `develop` - Day-to-day feature work
- `main` - Latest tagged release
- Feature branches: `feature/<area>-<description>`
