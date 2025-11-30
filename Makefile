.PHONY: help docs-serve docs-build docs-deploy

help:
	@echo "Available targets:"
	@echo "  docs-serve   - Serve the MkDocs site with live reload"
	@echo "  docs-build   - Build the MkDocs site into the ./site directory"
	@echo "  docs-deploy  - Deploy the MkDocs site to GitHub Pages (uses mkdocs gh-deploy)"

docs-serve:
	mkdocs serve

docs-build:
	mkdocs build --strict

docs-deploy:
	mkdocs gh-deploy --force --strict

