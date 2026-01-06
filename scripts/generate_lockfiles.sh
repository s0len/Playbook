#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${DIR}/.." && pwd)"

echo "[lockfile] Project root: ${PROJECT_ROOT}"
echo "[lockfile] Generating lock files with hash verification..."

# Check if pip-compile is available
if ! command -v pip-compile &> /dev/null; then
  echo "[lockfile] pip-compile not found. Installing pip-tools..."
  pip install pip-tools
fi

# Navigate to project root to ensure relative paths work correctly
cd "${PROJECT_ROOT}"

# Generate requirements.lock from requirements.txt
if [[ -f "${PROJECT_ROOT}/requirements.txt" ]]; then
  echo "[lockfile] Generating requirements.lock from requirements.txt..."
  pip-compile \
    --generate-hashes \
    --allow-unsafe \
    --output-file=requirements.lock \
    requirements.txt
  echo "[lockfile] ✓ requirements.lock generated successfully"
else
  echo "[lockfile] ERROR: requirements.txt not found!"
  exit 1
fi

# Generate requirements-dev.lock from requirements-dev.txt
if [[ -f "${PROJECT_ROOT}/requirements-dev.txt" ]]; then
  echo "[lockfile] Generating requirements-dev.lock from requirements-dev.txt..."
  pip-compile \
    --generate-hashes \
    --allow-unsafe \
    --output-file=requirements-dev.lock \
    requirements-dev.txt
  echo "[lockfile] ✓ requirements-dev.lock generated successfully"
else
  echo "[lockfile] ERROR: requirements-dev.txt not found!"
  exit 1
fi

echo "[lockfile] Lock file generation complete!"
echo "[lockfile] You can now install with: pip install --require-hashes -r requirements.lock"
