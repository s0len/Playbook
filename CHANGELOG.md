# Changelog

All notable changes to this project will be documented in this file.

The format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), with dates in `YYYY-MM-DD`.

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


