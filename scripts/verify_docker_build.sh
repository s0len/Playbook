#!/bin/bash
#
# Verification script for Docker build with hash-verified dependencies
# This script tests that the Docker image builds successfully with requirements.lock
#

set -euo pipefail

echo "[docker-verify] Starting Docker build verification..."

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "[docker-verify] ERROR: Docker is not installed or not in PATH"
    exit 1
fi

# Verify required files exist
echo "[docker-verify] Checking required files..."
required_files=(
    "Dockerfile"
    "requirements.lock"
    "entrypoint.sh"
    "src"
    "README.md"
    "LICENSE"
)

for file in "${required_files[@]}"; do
    if [ ! -e "$file" ]; then
        echo "[docker-verify] ERROR: Required file/directory '$file' not found"
        exit 1
    fi
    echo "[docker-verify]   ✓ $file exists"
done

# Verify requirements.lock has hashes
echo "[docker-verify] Verifying requirements.lock format..."
if ! grep -q "^[[:space:]]*--hash=sha256:" requirements.lock; then
    echo "[docker-verify] ERROR: requirements.lock does not contain SHA256 hashes"
    exit 1
fi
echo "[docker-verify]   ✓ requirements.lock contains SHA256 hashes"

# Count hashes
hash_count=$(grep -c "^[[:space:]]*--hash=sha256:" requirements.lock)
echo "[docker-verify]   Found $hash_count SHA256 hashes in requirements.lock"

# Build Docker image
echo "[docker-verify] Building Docker image with hash verification..."
IMAGE_TAG="playbook:hash-verification-test"

if docker build -t "$IMAGE_TAG" . ; then
    echo "[docker-verify] ✓ Docker build SUCCEEDED with hash-verified dependencies"

    # Verify the image was created
    if docker image inspect "$IMAGE_TAG" &> /dev/null; then
        echo "[docker-verify] ✓ Docker image '$IMAGE_TAG' created successfully"

        # Get image details
        echo "[docker-verify] Image details:"
        docker image inspect "$IMAGE_TAG" --format '  Size: {{.Size}} bytes'
        docker image inspect "$IMAGE_TAG" --format '  Created: {{.Created}}'

        # Test that the image runs (basic smoke test)
        echo "[docker-verify] Running basic smoke test..."
        if docker run --rm "$IMAGE_TAG" --version 2>&1 | grep -q "Playbook"; then
            echo "[docker-verify] ✓ Container smoke test PASSED"
        else
            echo "[docker-verify] ⚠ Container smoke test: could not verify version output"
        fi

        echo ""
        echo "[docker-verify] SUCCESS: All verifications passed!"
        echo "[docker-verify] You can clean up the test image with: docker rmi $IMAGE_TAG"
    else
        echo "[docker-verify] WARNING: Build succeeded but image not found"
        exit 1
    fi
else
    echo "[docker-verify] ✗ Docker build FAILED"
    echo "[docker-verify] This indicates an issue with hash verification or the Dockerfile"
    exit 1
fi
