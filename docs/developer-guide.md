# Developer Guide

Welcome, contributor! This guide captures the repo setup, test workflow, branching policy, and release cadence.

## Local Environment

```bash
git clone https://github.com/s0len/playbook.git
cd playbook
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run the CLI locally:

```bash
python -m playbook.cli --config config/playbook.sample.yaml --dry-run --verbose
```

Build the container image:

```bash
docker build -t playbook:dev .
```

## Tests & Tooling

- Primary suite: `pytest` (run via `pytest` or `python -m pytest`).  
- Pattern samples: edit `tests/data/pattern_samples.yaml` and run `pytest tests/test_pattern_samples.py`.  
- Bootstrap helper: `bash scripts/bootstrap_and_test.sh` spins up a clean virtualenv and runs the full suite.
- Formatting/linting: follow `ruff`/`black` defaults (coming soon to CI). Use `ruff check .` and `black .` before committing when touching Python files.
- Match traces: `python -m playbook.cli --dry-run --verbose --trace-matches` writes JSON artifacts in `cache_dir/traces` and is invaluable when reviewing PRs that tweak regex logic.

## Documentation Workflow

- Install `mkdocs-material` via `pip install -r requirements-dev.txt`.
- `make docs-serve` starts the live preview at `http://127.0.0.1:8000`.
- `make docs-build` produces the static site under `site/`.
- `make docs-deploy` runs `mkdocs gh-deploy` (maintainers only).
- GitHub Actions (`.github/workflows/docs.yml`) build the docs on every PR and publish to GitHub Pages when `main` changes.
- Keep reusable snippets under `docs/snippets/` and include them via ` ```--8<-- "snippets/foo.md"``` ` so updates propagate automatically.

## Branching & Releases

- `develop` collects day-to-day feature work.  
- `main` always reflects the latest tagged release.  
- Feature branches follow `feature/<area>-<short-description>` (e.g., `feature/docs-foundation`, `feature/kometa-webhook`).  
- Open bite-sized PRs; large doc pushes can be split per section (config guide, integrations, recipes, etc.).  
- Release checklist:\n  1. Ensure docs for new features merged into `develop`.\n  2. Bump version + changelog.\n  3. Merge `develop` → `main` via PR.\n  4. Tag (e.g., `v1.4.0`).\n  5. Let the docs workflow deploy GitHub Pages; update badges/links if needed.
- Automated tests run in CI via GitHub Actions; keep PRs green by running `pytest` locally before pushing.
- For doc-heavy efforts, follow the A/B/C plan (foundation → README → chapter-focused branches) so reviewers aren’t overwhelmed.

## Contribution Etiquette

- Include sample configs or tests whenever you touch matching logic.\n- Redact secrets before sharing logs/configs in issues.\n- Use draft PRs early—pattern reviews benefit from real-world filenames.\n- Mention whether docs updates are included (there’s a “Docs updated?” checkbox in the PR template).\n- For architecture proposals or metadata feed requests, start a GitHub Discussion before coding.

Need more details? Ping `@s0len` in issues/discussions or hop into the project chat.

