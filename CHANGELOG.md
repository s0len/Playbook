## [1.4.2] - 2026-01-07

### ✨ New Features
- Read version from CHANGELOG.md instead of hardcoding
- Add date proximity matching and parsing functionality
- Enhance Plex metadata sync functionality with pre-sync operations
- Add library scan functionality and fuzzy search improvements
- Improve Plex sync logging and error handling
- Enhance team noise filtering and provider handling in matcher
- Introduce team alias mapping for sports configurations
- Enhance NHL and EPL matching with new patterns and team aliases
- Enhance NHL support with new patterns and metadata integration
- Enhance season and episode matching with fuzzy and partial title support
- Enhance show search functionality in PlexClient
- Improve episode display number handling in MetadataNormalizer
- Add space-separated NBA and NFL pattern support with week-based season selection
- Add fuzzy location matching using rapidfuzz
- Add round-based episode resolution fallback in matcher
- Add unlock/lock functionality for Plex poster field locking
- Add configuration option for poster locking behavior
- Integrate unlock/lock calls into metadata application
- Add mode:week support to matcher for NFL patterns

### 🐛 Bug Fixes
- Use ternary operator in validation.py (SIM108)
- Remove non-existent extract_yaml_line_numbers_from_file import
- Set docker-image-scan to report-only mode for base image CVEs
- Add CVE-2025-68973 (gnupg2) to trivy ignore list
- Use text-based .trivyignore for better compatibility
- Revert to python:3.12-slim-bookworm for security
- Use specific python:3.12-alpine3.21 base image for security
- Fix Docker build by adding bash to Alpine image
- Resolve final lint errors in cli.py
- Resolve all remaining lint errors in cli.py
- Remove duplicate function definitions breaking NBA/NFL matching
- Update metadata extraction to prioritize new URL fields
- Update fingerprint usage in Plex metadata sync to use digest
- Update search_show method to return None for unmatched results
- Fix title normalization in metadata.py to preserve acronym casing
- Update plex_client.py to override Plex title normalization
- Update plex_metadata_sync.py to handle show lookup with case preservation
- Add Issue #74 exact filenames to pattern_samples.yaml

### 🔧 Improvements
- Apply ruff formatting to validation.py
- Add get_section_display_name and group_validation_issues
- Sync rapidfuzz version in requirements.txt to match pyproject.toml (3.14.3)
- Fix lint errors in tests/*.py and src/playbook/*.py files
- Regenerate requirements.lock with updated versions
- Switch Docker base image from Debian slim to Alpine
- Restore Python 3.9 compatibility and fix scoring logic
- Enhance asset URL resolution and logging in metadata mapping
- Update playbook sample and documentation for scan_wait parameter
- Downgrade verbose logging from INFO to DEBUG level across multiple modules to reduce noise while preserving debug capability
- Downgrade routine trigger and dispatch logs to DEBUG level
- Downgrade library scan logs to DEBUG level
- Downgrade per-item and per-file logs to DEBUG level
- Downgrade metadata fetch and stale cache logs to DEBUG level
- Enhance error summary with context extraction for better troubleshooting
- Add SearchResult dataclass to capture search diagnostics
- Update error handling with enhanced show not found, season not found, and episode not found messages
- Add comprehensive unit tests for new matching and validation features
- Add integration tests for poster unlock workflow
- Extensive code refactoring and modularization of monolithic processor.py into specialized modules (file_discovery, match_handler, destination_builder, metadata_loader, post_run_triggers, trace_writer, run_summary, notifications)
- Add session lookup index optimization with cached fingerprint computation
- Implement content hash tracking for improved cache validation
- Add optional cache statistics tracking for debugging and performance monitoring
- Migrate from SHA-1 to SHA-256 for enhanced security
- Add ruff formatter and linter configuration with pre-commit hooks
- Enable automated dependency updates with Dependabot
- Add pip-audit security scanning to development workflow
- Create comprehensive lock files with SHA256 hashes for reproducible builds
- Add Rich-based validation formatter with grouping and fix suggestions
- Create SummaryTableRenderer for structured output formatting
- Add command examples and help text throughout CLI
- Create comprehensive documentation including troubleshooting guides and Docker verification tools
- Add security scanning workflow with pip-audit and Trivy integration
- Implement notification system with multiple targets (Slack, Discord, Autoscan, Webhook, Email)
- Add verbose mode for enhanced debugging with debug logging when needed

### 📚 Documentation
- Add comprehensive refactoring summary
- Update README with Run Modes & CLI section mentioning new modes
- Update documentation to describe new validation output format
- Update README.md and docs/integrations.md to fix broken metadata URLs
- Update configuration documentation to use generic 'hash' instead of 'sha1'
- Update verify_ssl comment in README.md to include certificate troubleshooting
- Create examples covering Docker mode trigger, Kubernetes integration, basic validation, diff against sample, show-trace for debugging, and CI/CD integration patterns
- Add security scanning documentation
- Extend troubleshooting docs to suggest proper certificate handling
- Update bootstrap script to use lock files with hash verification
- Add test verification status documentation

# Changelog

All notable changes to this project will be documented in this file.

The format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), with dates in `YYYY-MM-DD`.

## [Unreleased]

### ⚠️ Breaking Changes
- **Metadata source migrated from YAML to TheTVSportsDB REST API.** Sport configurations now use `show_slug` instead of the previous `metadata.url` / `metadata.show_key` approach. Update your config files:
  ```yaml
  # OLD (no longer supported)
  - id: formula1_2025
    metadata:
      url: https://example.com/formula1/2025.yaml
      show_key: Formula1 2025

  # NEW
  - id: formula1_2025
    show_slug: "formula-1-2025"
  ```
- The `metadata` block on sport entries is removed. Use `show_slug` to reference shows in TheTVSportsDB.
- Variants now require `show_slug` instead of `metadata.url`.

### Added
- **TheTVSportsDB API integration** - Metadata is now fetched from a REST API instead of static YAML files. Configure the API endpoint under `settings.tvsportsdb`:
  ```yaml
  settings:
    tvsportsdb:
      base_url: "https://thetvsportsdb-api.uniflix.vip/api/v1"
      ttl_hours: 12
      timeout: 30
  ```
- New `tvsportsdb` package (`src/playbook/tvsportsdb/`) with HTTP client, Pydantic response models, adapter layer, and TTL-based file caching.
- **Plex Metadata Sync** now fetches metadata directly from TheTVSportsDB API and pushes titles, summaries, posters, and backgrounds to Plex automatically.
- NHL regular-season filename patterns, metadata wiring, and docs/sample config updates powered by the new `nhl` pattern set and metadata feed.
- `SeasonSelector` now supports a `date` mode plus `value_template`, enabling calendar-date lookups that select the season containing a matching `originally_available` entry.
- Team alias mapping utilities (with an NHL map) allow matchup strings such as "Blue Jackets vs Devils" to resolve to the canonical metadata titles.
- Requirements lock files (`requirements.lock` and `requirements-dev.lock`) with SHA256 hash verification to protect against supply chain attacks. All Python dependencies now install with `pip install --require-hashes` to ensure package integrity.

### Changed
- Pattern sample tests understand `originally_available` timestamps so date-driven selectors can be exercised in CI.
- Validation schema updated: `show_slug` is now validated instead of `metadata.url`.
## [1.4.0] - 2025-12-04

### Added
- MkDocs-powered documentation is live at https://s0len.github.io/Playbook/ with deployment wiring captured in the docs release (#44, #52).
- New integrations and recipe guides cover real-world automation patterns for Playbook operators (#45, #46).

### Changed
- The troubleshooting guide was rebuilt to fit the MkDocs structure and highlight the refreshed workflows (#47).
- Operations guidance was fleshed out with day-two scenarios and runbook tips (#48).
- The developer guide now includes deeper contributor instructions and local workflows (#49).
- Configuration guidance was expanded to better explain advanced settings and templates (#50).

### Fixed
- Notification settings now separate environment variables from user configuration so overrides no longer leak across deploy targets (#51).

## [1.3.1] - 2025-11-30

### Added
- `match_file_to_episode` now accepts a `suppress_warnings` flag so sample file discovery can mute noisy logs, with processor wiring and regression tests covering the workflow.
- `_process_single_file` gains an `is_sample_file` hint to keep sample and real file processing paths aligned without duplicating detection logic.

### Changed
- Kometa triggers now execute once per processing pass rather than per batch, and the associated configuration/docs/tests were updated to reflect the simplified behavior.
- Runtime switches were consolidated: the watcher is controlled via `WATCH_MODE`, `process_all()` replaces the old `run_once`, and Docker/CLI documentation explains the new flow.
- Sports metadata guidance in `README.md` and `config/playbook.sample.yaml` uses standardized regex casing, refreshed IndyCar paths, and clearer UFC slug requirements.
- `openapi.json` was added to `.gitignore` to keep generated artifacts out of commits.

### Removed
- The `per_batch` Kometa trigger toggle was removed; existing configs must drop this key.
- Deprecated environment variables `PROCESS_INTERVAL` and `RUN_ONCE` were eliminated in favor of the clearer `WATCH_MODE`.


