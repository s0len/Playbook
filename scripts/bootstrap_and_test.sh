#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${DIR}/.." && pwd)"
VENV_PATH="${PROJECT_ROOT}/.venv"

echo "[bootstrap] Project root: ${PROJECT_ROOT}"
echo "[bootstrap] Using virtual environment at: ${VENV_PATH}"

if [[ ! -d "${VENV_PATH}" ]]; then
  echo "[bootstrap] Creating virtual environment..."
  python3 -m venv "${VENV_PATH}"
else
  echo "[bootstrap] Virtual environment already exists, reusing."
fi

source "${VENV_PATH}/bin/activate"

echo "[bootstrap] Upgrading pip..."
pip install --upgrade pip

# Install production dependencies with hash verification if lock file exists
if [[ -f "${PROJECT_ROOT}/requirements.lock" ]]; then
  echo "[bootstrap] Installing requirements.lock with hash verification..."
  pip install --require-hashes -r "${PROJECT_ROOT}/requirements.lock"
elif [[ -f "${PROJECT_ROOT}/requirements.txt" ]]; then
  echo "[bootstrap] Installing requirements.txt (lock file not found)..."
  pip install -r "${PROJECT_ROOT}/requirements.txt"
else
  echo "[bootstrap] Skipping production requirements (not found)."
fi

# Install development dependencies with hash verification if lock file exists
if [[ -f "${PROJECT_ROOT}/requirements-dev.lock" ]]; then
  echo "[bootstrap] Installing requirements-dev.lock with hash verification..."
  pip install --require-hashes -r "${PROJECT_ROOT}/requirements-dev.lock"
elif [[ -f "${PROJECT_ROOT}/requirements-dev.txt" ]]; then
  echo "[bootstrap] Installing requirements-dev.txt (lock file not found)..."
  pip install -r "${PROJECT_ROOT}/requirements-dev.txt"
else
  echo "[bootstrap] Skipping development requirements (not found)."
fi

echo "[bootstrap] Running tests with pytest..."
python3 -m pytest "$@"

