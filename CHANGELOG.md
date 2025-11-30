# Changelog

All notable changes to this project will be documented in this file.

The format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), with dates in `YYYY-MM-DD`.

## [2025-11-30] - 2025-11-30

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


