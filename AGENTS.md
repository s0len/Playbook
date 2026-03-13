# AGENTS.md

Guidance for agentic coding assistants working in this repository.

## Repository Snapshot
- Project: `Playbook` (Python 3.12+), sports media organization for Plex.
- Main package: `src/playbook/`
- Test suite: `tests/`
- Sample config: `config/config.sample.yaml`
- Core flow: metadata -> normalization -> matching -> destination templating -> link/copy/symlink.

## Rule Files Check (Important)
- Cursor rules: not found (`.cursorrules` and `.cursor/rules/` absent).
- Copilot instructions: not found (`.github/copilot-instructions.md` absent).
- Additional local guidance exists in `CLAUDE.md`.
- If Cursor/Copilot files appear later, treat them as higher-priority and update this file.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Optional editable install:
```bash
pip install -e .[dev]
```

## Build, Lint, and Format
Primary commands:
```bash
ruff check .
ruff check . --fix
ruff format .
ruff format --check .
```

Makefile shortcuts:
```bash
make lint
make lint-fix
make format
make check
```

## Testing Commands (Use These Exactly)
Run all tests:
```bash
pytest
```

Run a single test file:
```bash
pytest tests/test_matcher.py
```

Run a single test function (preferred targeted loop):
```bash
pytest tests/test_matcher.py::test_match_file_to_episode_resolves_aliases
```

Run a test class method:
```bash
pytest tests/test_matcher.py::TestClass::test_method
```

Run tests by keyword expression:
```bash
pytest -k "matcher and not integration"
```

Re-run only last failures:
```bash
pytest --lf
```

Pattern sample validation (required after pattern edits):
```bash
pytest tests/test_pattern_samples.py
```

Bootstrap + full test run:
```bash
bash scripts/bootstrap_and_test.sh
```

## Useful CLI Validation Commands
- Dry-run processor: `python -m playbook.cli --config config/config.sample.yaml --dry-run --verbose`
- Validate config + sample diff: `python -m playbook.cli validate-config --config /path/to/config.yaml --diff-sample`
- Trace matching decisions: `python -m playbook.cli --dry-run --verbose --trace-matches`

## Code Style Guidelines

### Formatting and Imports
- Ruff is the source of truth; do not hand-format against Ruff output.
- Line length is 120.
- Use double quotes; use spaces for indentation.
- Keep imports ordered as stdlib / third-party / local (Ruff `I`).
- Prefer `from __future__ import annotations` (common in repo modules).
- Use `TYPE_CHECKING` for type-only imports where useful.

### Typing and Data Modeling
- Add type hints to public functions and non-trivial internal helpers.
- Prefer builtin generics (`list[str]`, `dict[str, Any]`) and `X | None` unions.
- Follow the repository's dataclass-heavy modeling style for config/domain objects.
- Use `field(default_factory=...)` for mutable dataclass defaults.
- Prefer `pathlib.Path` over raw path strings.

### Naming
- Modules/files: `snake_case`
- Functions/variables: `snake_case`
- Classes/dataclasses: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Tests: `tests/test_*.py`, function names like `test_<behavior>`

### Error Handling and Logging
- Raise explicit exceptions for invalid config/programmer errors.
- Keep exception chaining (`raise ... from exc`) when re-raising.
- For recoverable operations, prefer structured results where established (example: `LinkResult`).
- Do not silently swallow exceptions.
- Use module logger pattern: `LOGGER = logging.getLogger(__name__)`.
- Include actionable context in log fields/messages (path, sport_id, mode, reason).
- Preserve dry-run semantics: no filesystem side effects in dry-run mode.

### Config and Validation
- Keep config dataclasses and validation schema in sync (`config.py` and `validation.py`).
- Maintain explicit defaults in dataclasses for user-facing behavior.
- Validate external inputs defensively (URLs, env-expanded values, etc.).
- Preserve backward-compatibility behavior only where already established.

### Testing Expectations
- Update/add tests whenever behavior changes.
- Prefer deterministic tests; avoid external network dependencies in unit tests.
- Reuse shared fixtures/helpers in `tests/`.
- For matcher changes, update `tests/data/pattern_samples.yaml` and run its dedicated test.

## Agent Workflow Recommendations
- Make focused edits; avoid broad refactors unless requested.
- Read adjacent code and mirror existing patterns before changing structure.
- Run targeted tests first, then broader checks when the change stabilizes.
- Small Python changes minimum loop:
```bash
ruff check .
pytest -k "relevant_keyword"
```
- For bigger changes, run full `pytest` before finalizing.

## Safety and Secrets
- Never commit secrets (tokens, webhook URLs, credentials).
- Prefer env-var expansion for sensitive config values.
- Be careful with destructive filesystem operations; this app manages media libraries.
