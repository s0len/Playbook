# Docker Build Verification with Hash-Verified Dependencies

## Overview

This document describes how to verify that the Docker build works correctly with hash-verified dependencies using `requirements.lock`.

## Quick Verification

Run the automated verification script:

```bash
./scripts/verify_docker_build.sh
```

This script will:
1. Check that all required files exist
2. Verify that `requirements.lock` contains SHA256 hashes
3. Build the Docker image with hash verification
4. Run a basic smoke test of the container
5. Report success or failure

## Manual Verification Steps

If you prefer to verify manually:

### 1. Verify Prerequisites

Ensure Docker is installed:
```bash
docker --version
```

### 2. Verify Lock File Format

Check that `requirements.lock` contains SHA256 hashes:
```bash
grep --color "^[[:space:]]*--hash=sha256:" requirements.lock | head -5
```

You should see lines like:
```
    --hash=sha256:16d5969b87f0859ef33a48b35d55ac1be6e42ae49d5e853b597db70c35c57e11 \
```

### 3. Build Docker Image

Build the image with a test tag:
```bash
docker build -t playbook:hash-verification-test .
```

**Expected outcome:** Build succeeds with output showing:
- `COPY requirements.lock /app/requirements.lock`
- `RUN pip install --require-hashes -r /app/requirements.lock`
- All packages installing successfully with hash verification

**What this verifies:**
- The Dockerfile correctly references `requirements.lock`
- The `pip install --require-hashes` command works
- All hashes in `requirements.lock` are valid
- No packages are tampered with

### 4. Verify Image Created

```bash
docker images | grep playbook
```

### 5. Test Container (Optional)

Run the container to ensure it starts correctly:
```bash
docker run --rm playbook:hash-verification-test --help
```

### 6. Cleanup

Remove the test image:
```bash
docker rmi playbook:hash-verification-test
```

## What Hash Verification Prevents

When building with `--require-hashes`, pip will:
- **Reject packages without hashes** in the requirements file
- **Reject packages with mismatched hashes** (tampering detected)
- **Ensure reproducible builds** (same packages every time)
- **Protect against supply chain attacks** (compromised PyPI mirrors)

## Troubleshooting

### Build fails with "Hashes are required"

**Cause:** `requirements.lock` is missing hash entries for some packages.

**Solution:** Regenerate the lock file:
```bash
make lock
```

### Build fails with "Hash mismatch"

**Cause:** A package on PyPI has been updated or tampered with.

**Solution:**
1. Investigate which package failed
2. Regenerate lock file to get new hashes: `make lock`
3. Review changes to ensure they're legitimate

### Build fails with "File not found: requirements.lock"

**Cause:** The lock file doesn't exist or wasn't copied into the Docker context.

**Solution:** Ensure `requirements.lock` exists in the project root:
```bash
ls -l requirements.lock
```

## Verification Checklist

- [ ] `requirements.lock` exists and contains SHA256 hashes
- [ ] All required files exist (Dockerfile, entrypoint.sh, src/, etc.)
- [ ] Docker build completes successfully
- [ ] No hash verification errors during build
- [ ] Container starts and runs basic commands
- [ ] Build is reproducible (same image hash on repeated builds)

## Related Files

- `Dockerfile` - Uses `requirements.lock` with `--require-hashes`
- `requirements.lock` - Production dependencies with SHA256 hashes
- `scripts/generate_lockfiles.sh` - Regenerates lock files
- `Makefile` - Contains `make lock` target
