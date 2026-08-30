## [Unreleased]

### Fixed
- **Premier League fixtures from a new season were silently filed into the previous one.** The `Premier League matchweek releases` pattern read `EPL.2026.08.28.Crystal.Palace.vs.Manchester.City` as year=2026 + matchweek=08 and hardlinked it into Matchweek 8 of the 2025-26 show, picking whichever fixture in that week shared a team. The pattern now carries a negative lookahead so it can no longer swallow a `YYYY.MM.DD` release.
- **Two-legged ties resolved to the wrong leg.** The session-lookup index maps both orderings of a matchup to the same entry, so a lookup hit cannot tell the home leg from the away leg, and `select_episode` returned it without checking the date. On the real library this mis-filed 12 Champions League fixtures - `2026.03.17.Chelsea.vs.PSG` landed on the 2026-03-10 Paris Saint-Germain home leg, and so on. A lookup hit whose date contradicts the filename now re-points to the occurrence the date supports.
- Team names containing letters outside ASCII were truncated before comparison: `TEAM_PATTERN` was `[A-Za-z0-9 .&'/-]`, so "Atlético Madrid" was extracted as "tico Madrid", "Bayern München" as "nchen", and "Beşiktaş vs Porto" not at all. The truncated name then tripped the partial-overlap rejection and scored zero.
- `normalize_token` now folds Latin letters that NFD cannot decompose (ø, đ, ð, ł, ħ, ı, æ, œ, ß, þ). These were deleted outright by the combining-mark strip, so metadata "Bodø/Glimt" normalized to `bodglimt` and never matched a release named "Bodo-Glimt".
- `find_episode_across_seasons` ignored the date and returned whichever season came first, even though league teams meet home and away and players meet again at another tournament. It now skips occurrences the filename's date contradicts.
- `parse_date_from_groups` now also reads `season_year`, which several competition patterns use to name the leading YYYY of a `YYYY.MM.DD` date. Because a date also requires day and month, a genuine season label can never be read as one.
- WTA: `WTA Finals | Riyadh | ...` parsed as level=Finals, tournament=Riyadh, resolved to no season, and then fell through to the first season holding that matchup - filing the Riyadh final under the Australian Open. `level` is now the tour tier only (1000/500/250/125); the dedicated Finals pattern handles the rest.
- Added a pattern for the bare `CL - Home vs Away DD.MM.YYYY` shape, which the structured parser cannot split (it glues the prefix onto the home team as "CL - Qarabag").

### Changed
- Premier League, Champions League and NFL now offer every season's show as a match candidate instead of mapping a calendar year to one show. A season spans two calendar years, so the captured year cannot pick the right show on its own - January 2026 is the 2025 season while September 2026 is the 2026 season. Variants use `id_suffix` (the season's starting year) rather than `year`, which leaves `variant_year` unset so the date in the filename decides. Existing sport ids are unchanged, so no persisted state is orphaned. Premier League and Champions League now reach their 2026-27 shows and NFL reaches `nfl-2026`.
- The structured matcher's date term is monotonic (0.40 exact, 0.30 at one day, 0.20 at two) instead of a flat 0.40 anywhere within the window, so two fixtures between the same teams a day or two apart can no longer tie on the date alone.
- The structured matcher now refuses when several episodes tie at the top score and name different fixtures, instead of silently taking the first. This surfaces duplicated metadata (a game listed in both a pre-season and a regular-season season) and dateless filenames whose teams meet several times a season as unmatched rather than mis-filed.
- An episode whose date is known and outside the tolerance is no longer accepted just because it was the only candidate. A lone candidate with an *unknown* date is still accepted.
- CI now runs the test suite, and a push to `develop` cannot build and publish an image unless it passes. Previously only ruff, docs and a security scan ran, while Renovate auto-bumped the deployed digest.

### Notes
- Measured against the live library (944 files, real TVSportsDB metadata): 14 files that resolved to the wrong fixture now resolve correctly, no file changed to a wrong answer, and one file stopped matching - `NHL.2025.RS.Blue.Jackets.vs.Devils` carries no date and those teams meet four times that season, so the previous match was a one-in-four guess.
- NHL is deliberately *not* pointed at `nhl-2026-2027` yet: in that show season 0 ("Pre-Season") duplicates the entire regular season, 1403 episodes spanning 2026-09-19..2027-04-10, so 414 of 2332 fixtures exist in more than one season. Repoint it once the duplicate season is removed upstream.
- `wta-2025` does not exist and has 404'd silently for months (the API publishes this family as `wta-tour-<year>`). It is left as-is on purpose: repointing it at `wta-tour-2026` made a 2020 file match an unrelated 2026 fixture, so WTA episode selection needs tightening first.
- `tests/data/pattern_samples.yaml` silently ignored 24 filename entries (they use the key `files:` rather than `filenames:`) and every `expect_season` assertion. Both are now honoured, and a sample declaring no filenames is an error rather than a vacuous pass.

## [2.23.0] - 2026-08-28

### Fixed
- **The published Docker image was installing badly outdated dependencies.** `requirements.lock` is what the image installs (`pip install --require-hashes -r /app/requirements.lock`), but Dependabot's pip ecosystem only parses `pyproject.toml` and `.txt`/`.in` files and cannot see a `.lock` — so every merged dependency PR left the shipped artifact untouched. Both locks are regenerated, and the image now ships `nicegui` 3.16.0 (was 3.6.1), `kubernetes` 36.0.3 (was 35.0.0), `requests` 2.34.2 (was 2.32.5), `pydantic` 2.13.4 (was 2.12.5), `rich` 15.0.0 (was 14.3.1), `tenacity` 9.1.4, and `rapidfuzz` 3.14.5, plus 36 refreshed transitive packages including `fastapi` 0.141.1 (was 0.128.0), `starlette` 1.6.0 (was 0.50.0), and `uvicorn` 0.52.4 (was 0.40.0) (#225).
- Both lock files are now compiled under Python 3.12, matching the `python:3.12-slim-bookworm` runtime. `requirements.lock` had been generated under Python 3.14 and `requirements-dev.lock` under Python 3.9 — the latter below the project's own `requires-python = ">=3.12"`. Environment markers and wheel selection are resolved at compile time, so under `--require-hashes` a mismatch fails the image build outright rather than warning (#225).
- Dependabot's `target-branch: "develop"` existed only on `main` and had never been merged back into `develop`, so the next release merge would have overwritten it and sent dependency PRs to `main` again. Both branches now agree (#226).
- Dependabot review requests were never actually sent: the `reviewers:` key was set to `"@solen"`, but the field expects a bare username and the `@` prefix silently never resolved to a user. Replaced with `.github/CODEOWNERS`, where the `@` is required (#226).

### Changed
- Dependency updates: `nicegui` 3.16.0 (#206, #222), `kubernetes` 36.0.3 (#213).
- Dev dependency updates: `pytest` >=9.1.1 (#207), `ruff` >=0.16.4 (#212, #218), `setuptools` >=84.0.0 (#204, #220), `mkdocs-material` >=9.7.7 (#219), `pre-commit` >=4.6.2 (#221).
- CI: `actions/setup-python` v7 (#214), `docker/login-action` 4.6.0 (#216, #224), `github/codeql-action` 4.37.8 (#217, #223).
- Dependabot now tracks the Docker base image (`python:3.12-slim-bookworm`), which had never been offered an update (#226).
- Security scanning now covers the lock files: `requirements.lock` and `requirements-dev.lock` are in the workflow's path filters, so a lock-only change no longer slips through unscanned, and `pip-audit` runs against `requirements.lock` — the file the image actually installs (#225).

### Notes
- No application code changed in this release; `src/` is untouched. The web GUI stack did move substantially inside the image (`starlette` crosses 0.x→1.x, `rich` 14→15, `nicegui` gains ten minor versions), so a quick smoke test of the GUI after upgrading is worthwhile.
- `pip-audit` reports no known vulnerabilities in either regenerated lock.
- Nothing regenerates the locks automatically yet, so they can drift again. Tracking a follow-up to either enforce `pip-compile` in CI or rename the locks so Dependabot maintains them directly.

## [2.22.0] - 2026-07-08

### Security
- Web GUI now supports **opt-in authentication**. Set `GUI_PASSWORD` (and optionally `GUI_USERNAME`, default `admin`) to require login; all pages redirect to a login screen and `/api/*` returns 401 until authenticated. When no password is set the GUI stays unauthenticated as before, but logs a warning at startup (#209).
- The GUI session-cookie signing key is now randomized per process (or set via `GUI_STORAGE_SECRET`) instead of a hardcoded value, so session cookies can no longer be forged (#209).
- GUI settings editors no longer send stored secrets (Plex token, SMTP/autoscan passwords) to the browser. Password fields render blank; leave one blank on save to keep the existing value (#209).
- Kometa Docker trigger: the container runtime (`kometa_trigger.docker.binary`) is now restricted to `docker`, `podman`, or `nerdctl`, so a config cannot invoke an arbitrary interpreter (#209).
- Local fallback artwork: the TVSportsDB show slug is sanitized and path-contained before use, so a malicious API response cannot read files outside the assets directory (#209).
- Email notifications now verify TLS certificates on SMTP STARTTLS (#209).
- Webhook, Discord, and Slack failure logs no longer include the full webhook URL (which can contain a secret token) (#209).
- Plex metadata sync only relays `http(s)` artwork URLs to the Plex server, rejecting other schemes from the metadata source (#209).
- The container image now runs as a non-root user (#209).

### Changed
- **The web GUI now binds to `127.0.0.1` by default** (was `0.0.0.0`). The Docker image keeps `GUI_HOST=0.0.0.0` so container/Kubernetes access is unchanged; bare-metal users who expose the GUI must set `GUI_HOST` explicitly (#209).
- Removed the unused `browser-use` dependency (declared in 2.21.0 but never imported) (#209).
- `NICEGUI_STORAGE_PATH` now defaults to `<STATE_DIR>/.nicegui` in the container entrypoint so GUI storage (and login sessions) work for the non-root user (#210).

### Notes
- SMTP TLS verification may now reject internal relays that use self-signed or hostname-mismatched certificates; use a valid certificate or a trusted CA if affected.

## [2.21.0] - 2026-07-08

### Added
- Plex metadata sync: new `fallback_assets_dir` option (`integrations.plex.metadata_sync`) for local fallback artwork. When TVSportsDB has no poster/background for a show, season, or episode, Playbook uploads a matching local image (`<dir>/<show_slug>/poster.jpg`, `season-NN.jpg`, `sNNeNN.jpg`) to Plex instead of leaving the generic show poster. API artwork always takes precedence (#203, fixes #181).

### Changed
- Dependency updates: `nicegui` 3.13.0 (#200), `kubernetes` 36.0.2 (#196), `browser-use` >=0.13.1 (#199).
- Dev dependency updates: `ruff` >=0.15.16 (#197), `pip-audit` >=2.10.1 (#201).
- CI: `actions/checkout` v7 (#202).

## [2.20.3] - 2026-05-16

### Fixed
- README Docker Compose example: replaced the split `/data/source` + `/data/destination` mounts with a single `/data` mount so hardlink suggestions work out of the box (source and destination must share a filesystem).

## [2.20.2] - 2026-05-16

### Changed
- Dependency updates: `requests` 2.34.2, `pydantic` 2.13.4, `nicegui` 3.12.0 (includes upstream security fixes for `ui.restructured_text` and dynamic resource routes).
- Dev dependency updates: `ruff` >=0.15.13, `pre-commit` >=4.6.0, `pip-audit` >=2.10.0.
- CI: `docker/setup-qemu-action` v4.

### Added
- GitHub Release notes are now auto-populated from the matching `CHANGELOG.md` section on tag push.

## [2.20.1] - 2026-04-25

### Fixed
- GUI logging: `playbook.*` log records were silently dropped from the file log shortly after startup. NiceGUI's `ui.run()` triggers uvicorn's `dictConfig`, which closes every existing handler; our `mode='w'` `FileHandler` then refused to reopen and silently swallowed every subsequent record. Pass `log_config=None` to `ui.run()` so uvicorn skips `dictConfig` and our root handlers survive.

## [2.20.0] - 2026-04-25

### Added
- Multi-arch Docker images: `ghcr.io/s0len/playbook` is now published for both `linux/amd64` and `linux/arm64` (fixes #151).

### Changed
- Dependency updates: `rapidfuzz` 3.14.5, `nicegui` 3.10.0, `rich` 15.0.0, `browser-use` >=0.12.6.
- Dev dependency updates: `pytest` >=9.0.3, `pre-commit` >=4.5.1, `setuptools` >=82.0.1, `mkdocs-material` >=9.7.6.
- CI: `aquasecurity/trivy-action` 0.36.0, `softprops/action-gh-release` v3.

## [2.7.0] - 2026-02-03

### Added
- **All TVSportsDB sports enabled by default** - No configuration required! Playbook now automatically enables all 16 supported sports (26 variants including yearly versions). Just set your directories and go.
- New `use_default_sports` setting (default: `true`) - Toggle all default sports on/off
- New `disabled_sports` setting - List of sport IDs to exclude from defaults (e.g., `disabled_sports: [formula_e, moto2]`)
- Default sports registry in `pattern_templates.yaml` with all sport configurations
- Source globs automatically inherited from pattern templates - updates benefit all users immediately

### Changed
- Simplified sample config to demonstrate minimal configuration approach
- User-defined sports now override defaults (define a sport in `sports:` to replace its default)
- Pattern templates now include `default_sports` section with complete sport definitions

### Default Sports
| Category | Sports |
|----------|--------|
| Motorsport | Formula 1, Formula E, IndyCar, MotoGP, Moto2, Moto3, World Superbike, World Supersport, Isle of Man TT |
| Combat Sports | UFC |
| North American | NFL, NBA, NHL |
| Football (Soccer) | Premier League, UEFA Champions League |
| Figure Skating | Figure Skating Grand Prix |

## [2.6.1] - 2026-01-29

### Fixed
- Added UCL abbreviated format patterns for UEFA Champions League (e.g., `UCL.2026.01.28.MD8.Liverpool.vs.Qarabag.1080p50.x264.EN.TNT.mp4`)

## [2.6.0] - 2026-01-29

### Added
- **Enhanced quality scoring system** with new attributes:
  - Frame rate scoring (critical for sports: 60fps=100, 50fps=75, 30fps=25)
  - Bit depth scoring (10-bit=25, 8-bit=0)
  - Audio format scoring (Atmos=40, TrueHD=35, DTS-HD=30, DDP5.1=25)
  - Broadcaster scoring (F1TV=50, Sky=30, ESPN=30, etc.)
  - Codec scoring (x265=25, x264=0, xvid=-25)
- Quality extraction patterns for frame rate (60fps, 50fps, 1080p50, etc.)
- Quality extraction patterns for bit depth (10bit, 8bit)
- Quality extraction patterns for audio formats (Atmos, TrueHD, DTS-HD, etc.)
- Quality extraction patterns for broadcasters (F1TV, Sky, ESPN, TNT, CBS, FOX, NBC)
- GUI settings page for quality scoring configuration

### Changed
- Resolution pattern matching improved to handle embedded frame rates (e.g., "1080p50")
- Broadcaster names (CBS, FOX, NBC) no longer detected as release groups

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
- **Metadata source migrated from YAML to TVSportsDB REST API.** Sport configurations now use `show_slug` instead of the previous `metadata.url` / `metadata.show_key` approach. Update your config files:
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
- The `metadata` block on sport entries is removed. Use `show_slug` to reference shows in TVSportsDB.
- Variants now require `show_slug` instead of `metadata.url`.

### Added
- **TVSportsDB API integration** - Metadata is now fetched from TVSportsDB REST API instead of static YAML files. Works out of the box with sensible defaults (12h cache TTL, 30s timeout). Optionally tune via `settings.tvsportsdb.ttl_hours` and `settings.tvsportsdb.timeout`.
- New `tvsportsdb` package (`src/playbook/tvsportsdb/`) with HTTP client, Pydantic response models, adapter layer, and TTL-based file caching.
- **Plex Metadata Sync** now fetches metadata directly from TVSportsDB API and pushes titles, summaries, posters, and backgrounds to Plex automatically.
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


