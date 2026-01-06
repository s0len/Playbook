.PHONY: help docs-serve docs-build docs-deploy lint format lint-fix check

help:
	@echo "Available targets:"
	@echo "  docs-serve   - Serve the MkDocs site with live reload"
	@echo "  docs-build   - Build the MkDocs site into the ./site directory"
	@echo "  docs-deploy  - Deploy the MkDocs site to GitHub Pages (uses mkdocs gh-deploy)"
	@echo "  lint         - Run ruff linter to check code quality"
	@echo "  format       - Run ruff formatter to auto-format code"
	@echo "  lint-fix     - Run ruff linter with auto-fix enabled"
	@echo "  check        - Run both lint and format checks"

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

