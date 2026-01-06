.PHONY: help docs-serve docs-build docs-deploy lock verify-deps

help:
	@echo "Available targets:"
	@echo "  docs-serve   - Serve the MkDocs site with live reload"
	@echo "  docs-build   - Build the MkDocs site into the ./site directory"
	@echo "  docs-deploy  - Deploy the MkDocs site to GitHub Pages (uses mkdocs gh-deploy)"
	@echo "  lock         - Generate lock files with hash verification (requirements.lock, requirements-dev.lock)"
	@echo "  verify-deps  - Verify that lock files exist and can be used for dependency installation"

docs-serve:
	mkdocs serve

docs-build:
	mkdocs build --strict

docs-deploy:
	mkdocs gh-deploy --force --strict

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

