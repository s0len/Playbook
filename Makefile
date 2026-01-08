.PHONY: help docs-serve docs-build docs-deploy lint format lint-fix check lock verify-deps

help:
	@echo "Available targets:"
	@echo "  docs-serve   - Serve the MkDocs site with live reload"
	@echo "  docs-build   - Build the MkDocs site into the ./site directory"
	@echo "  docs-deploy  - Deploy the MkDocs site to GitHub Pages (uses mkdocs gh-deploy)"
	@echo "  lint         - Run ruff linter to check code quality"
	@echo "  format       - Run ruff formatter to auto-format code"
	@echo "  lint-fix     - Run ruff linter with auto-fix enabled"
	@echo "  check        - Run both lint and format checks"
	@echo "  lock         - Generate lock files with hash verification (requirements.lock, requirements-dev.lock)"
	@echo "  verify-deps  - Verify that lock files exist and can be used for dependency installation"

docs-serve:
	mkdocs serve

docs-build:
	mkdocs build --strict

docs-deploy:
	mkdocs gh-deploy --force --strict

lint:
	ruff check .

format:
	ruff format .

lint-fix:
	ruff check --fix .

check:
	ruff check .
	ruff format --check .

lock:
	@echo "Generating lock files with hash verification..."
	@bash scripts/generate_lockfiles.sh

verify-deps:
	@echo "Verifying lock files exist and are valid..."
	@if [ ! -f requirements.lock ]; then echo "ERROR: requirements.lock not found. Run 'make lock' first."; exit 1; fi
	@if [ ! -f requirements-dev.lock ]; then echo "ERROR: requirements-dev.lock not found. Run 'make lock' first."; exit 1; fi
	@echo "Checking requirements.lock can be parsed..."
	@pip install --require-hashes --dry-run -r requirements.lock > /dev/null 2>&1 || (echo "ERROR: requirements.lock verification failed"; exit 1)
	@echo "Checking requirements-dev.lock can be parsed..."
	@pip install --require-hashes --dry-run -r requirements-dev.lock > /dev/null 2>&1 || (echo "ERROR: requirements-dev.lock verification failed"; exit 1)
	@echo "✓ Lock files are valid and ready to use"
