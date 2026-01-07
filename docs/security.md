# Security & Vulnerability Scanning

This project uses automated vulnerability scanning to detect security issues in Python dependencies and Docker images before they reach production. The security pipeline runs on every pull request, push to develop/main, and weekly on a schedule.

## Overview

The security scanning setup consists of three complementary tools:

| Tool | Purpose | Scan Target | Trigger |
|------|---------|-------------|---------|
| **pip-audit** | Python dependency CVE scanning | `requirements.txt`, `requirements-dev.txt` | PRs, pushes, weekly, manual |
| **Trivy** | Container vulnerability scanning | Docker images (OS + app dependencies) | PRs, pushes, weekly, manual |
| **Dependabot** | Automated dependency updates | Python packages, GitHub Actions | Weekly on Mondays |

All scans run in the `.github/workflows/security-scan.yml` workflow and are integrated into the build pipeline. If HIGH or CRITICAL vulnerabilities are detected, the build is blocked from proceeding.

## Python Dependency Scanning (pip-audit)

pip-audit checks Python packages against the [PyPI Advisory Database](https://github.com/pypa/advisory-database) for known CVEs.

### What it scans

- Production dependencies in `requirements.txt`:
  - PyYAML
  - jsonschema
  - requests
  - python-dateutil
  - rich
  - tenacity
  - rapidfuzz
  - watchdog
  - kubernetes
- Development dependencies in `requirements-dev.txt`:
  - pytest
  - mkdocs-material
  - pip-audit itself

### How it works

The workflow runs pip-audit on both dependency files:

```bash
pip-audit -r requirements.txt --desc
pip-audit -r requirements-dev.txt --desc
```

The `--desc` flag provides detailed descriptions of vulnerabilities, including:
- CVE identifier (e.g., CVE-2024-1234)
- Affected package and version
- Vulnerability description
- Fixed version (if available)
- Severity level

### Running locally

Install pip-audit from dev dependencies:

```bash
pip install -r requirements-dev.txt
```

Scan dependencies:

```bash
# Scan production dependencies
pip-audit -r requirements.txt --desc

# Scan development dependencies
pip-audit -r requirements-dev.txt --desc

# Scan currently installed packages
pip-audit
```

Additional useful flags:

```bash
# Output as JSON for automation
pip-audit -r requirements.txt --format json

# Only show vulnerabilities (skip informational messages)
pip-audit -r requirements.txt --desc --strict

# Generate a detailed report
pip-audit -r requirements.txt --desc --output audit-report.txt
```

## Docker Image Scanning (Trivy)

Trivy scans the built Docker image for vulnerabilities in:
- Base OS packages (from `python:3.12-slim`)
- Python packages installed in the container
- Known malware or misconfigurations

### Severity levels

Trivy reports vulnerabilities at multiple severity levels:

| Severity | Description | CI Action |
|----------|-------------|-----------|
| CRITICAL | Exploitable vulnerabilities requiring immediate action | **Blocks build** |
| HIGH | Serious vulnerabilities that should be addressed quickly | **Blocks build** |
| MEDIUM | Moderate vulnerabilities to address in normal workflow | Reported only |
| LOW | Minor issues or edge cases | Reported only |
| UNKNOWN | Severity not yet determined | Reported only |

The CI workflow is configured to **fail on HIGH or CRITICAL** vulnerabilities only, balancing security with practicality.

### How it works

1. The workflow builds the Docker image locally:
   ```bash
   docker build -t playbook:scan .
   ```

2. Trivy scans the image for HIGH and CRITICAL vulnerabilities:
   ```bash
   trivy image --severity HIGH,CRITICAL playbook:scan
   ```

3. Results are uploaded to GitHub Security tab (SARIF format) and displayed in the workflow logs (table format).

### Running locally

Scan the Docker image locally:

```bash
# Build the image
docker build -t playbook:dev .

# Scan for all vulnerabilities
trivy image playbook:dev

# Scan for HIGH and CRITICAL only (matches CI)
trivy image --severity HIGH,CRITICAL playbook:dev

# Generate detailed report
trivy image --format json --output image-scan.json playbook:dev

# Scan and ignore unfixed vulnerabilities
trivy image --ignore-unfixed playbook:dev
```

Additional Trivy scanning capabilities:

```bash
# Scan the Dockerfile for best practice violations
trivy config Dockerfile

# Scan local filesystem for secrets
trivy fs .

# Scan a specific Python package
trivy rootfs --pkg-types library /path/to/venv
```

## Dependabot Automated Updates

Dependabot automatically creates pull requests to update dependencies when:
- New versions are released
- Security advisories are published
- Dependencies become outdated

### Configuration

Dependabot is configured in `.github/dependabot.yml`:

- **Schedule**: Weekly on Mondays at 9:00 AM UTC (aligned with security scans)
- **Pull request limit**: 5 open PRs per ecosystem
- **Ecosystems monitored**:
  - `pip` – Python packages in `requirements.txt` and `requirements-dev.txt`
  - `github-actions` – GitHub Actions versions in `.github/workflows/`
- **Labels**: PRs are tagged with `dependencies`, `python`/`github-actions`, and `security`
- **Commit prefixes**: `deps` for Python, `ci` for GitHub Actions

### Reviewing Dependabot PRs

When Dependabot opens a PR:

1. **Check the changelog** – Review what changed in the new version
2. **Review security advisories** – If the PR addresses a CVE, prioritize it
3. **Run tests locally** – Ensure the update doesn't break functionality:
   ```bash
   git fetch origin
   git checkout dependabot/pip/package-name-1.2.3
   pip install -r requirements.txt
   pytest
   ```
4. **Check CI results** – Security scans and tests run automatically
5. **Merge if green** – Dependabot PRs that pass all checks are safe to merge

### Managing Dependabot

```bash
# Rebase a stale Dependabot PR
@dependabot rebase

# Recreate a PR
@dependabot recreate

# Merge a PR
@dependabot merge

# Ignore a specific version
@dependabot ignore this version

# Ignore a major version
@dependabot ignore this major version
```

## Interpreting Scan Results

### GitHub Security Tab

All Trivy scan results appear in the repository's **Security** → **Code scanning** tab. This provides:
- Centralized view of all vulnerabilities
- Filtering by severity, state, and branch
- Links to CVE details and remediation guidance
- Historical tracking of when issues were introduced/fixed

### Workflow Logs

Security scan results appear in the GitHub Actions workflow logs:

**pip-audit output example:**
```
Found 2 known vulnerabilities in 1 package
Name    Version ID             Fix Versions
------- ------- -------------- ------------
urllib3 1.26.5  GHSA-q2q7-5pp4 1.26.18,2.0.7
urllib3 1.26.5  PYSEC-2023-74  1.26.16
```

**Trivy output example:**
```
playbook:scan (debian 12.4)
Total: 5 (HIGH: 3, CRITICAL: 2)

┌──────────────┬────────────────┬──────────┬───────────────────┬───────────────┬─────────────────┐
│   Library    │ Vulnerability  │ Severity │ Installed Version │ Fixed Version │     Title       │
├──────────────┼────────────────┼──────────┼───────────────────┼───────────────┼─────────────────┤
│ openssl      │ CVE-2024-1234  │ CRITICAL │ 3.0.11-1          │ 3.0.13-1      │ Buffer overflow │
└──────────────┴────────────────┴──────────┴───────────────────┴───────────────┴─────────────────┘
```

## Handling Reported Vulnerabilities

When a vulnerability is detected:

### 1. Assess severity and impact

- **CRITICAL/HIGH in production dependencies**: Address immediately
- **CRITICAL/HIGH in dev dependencies**: Address in next sprint
- **MEDIUM/LOW**: Schedule for routine maintenance
- **Unfixed vulnerabilities**: Evaluate workarounds or risk acceptance

### 2. Check for available fixes

```bash
# For Python packages, check PyPI for newer versions
pip index versions <package-name>

# Check the CVE database for fix details
pip-audit -r requirements.txt --desc
```

### 3. Update the dependency

**Option A: Direct update (preferred)**

1. Update `requirements.txt`:
   ```diff
   -requests==2.31.0
   +requests==2.32.5
   ```

2. Test locally:
   ```bash
   pip install -r requirements.txt
   pytest
   python -m playbook.cli --dry-run --config config/playbook.sample.yaml
   ```

3. Commit and push:
   ```bash
   git add requirements.txt
   git commit -m "deps: Update requests to 2.32.5 to fix CVE-2024-XXXX"
   git push
   ```

**Option B: Wait for Dependabot**

If the fix was recently released, Dependabot will create a PR within a week. Monitor the Security tab for updates.

**Option C: Pin to a safe version**

If the latest version introduces breaking changes:

1. Pin to the newest **safe** version that fixes the CVE
2. Create a tracking issue for upgrading to the latest version
3. Document the decision in the commit message

### 4. Verify the fix

After updating:

```bash
# Verify Python dependencies are clean
pip-audit -r requirements.txt

# Rebuild and scan Docker image
docker build -t playbook:dev .
trivy image --severity HIGH,CRITICAL playbook:dev
```

The CI workflow will also re-scan on the next push.

### 5. Handle unfixed vulnerabilities

If no fix is available:

1. **Assess exploitability** – Is this vulnerability exploitable in Playbook's context?
2. **Check for workarounds** – Can you mitigate the risk through configuration?
3. **File an upstream issue** – Alert the package maintainers
4. **Consider alternatives** – Can you switch to a different package?
5. **Document the risk** – Add a comment in `requirements.txt` explaining why the vulnerable version is pinned
6. **Suppress false positives** (last resort):
   ```bash
   # Create .trivyignore file for Trivy
   echo "CVE-2024-XXXX" >> .trivyignore

   # Use pip-audit vulnerability ignore file
   echo "GHSA-XXXX-XXXX-XXXX" >> .pip-audit-ignore.json
   ```

## CI/CD Integration

### Security scan workflow triggers

The security scan workflow (`.github/workflows/security-scan.yml`) runs on:

1. **Pull requests** – Gates merges via required status checks
2. **Pushes to `develop`/`main`** – Catches issues before deployment
3. **Weekly schedule** – Monday at 9:00 AM UTC to catch newly disclosed CVEs
4. **Manual trigger** – Via Actions tab for ad-hoc audits
5. **File changes** – Only runs when `requirements*.txt`, `Dockerfile`, or the workflow itself changes

### Build pipeline integration

The build-and-push workflow (`.github/workflows/build-and-push.yml`) includes security scans as prerequisites:

```yaml
jobs:
  python-dependency-scan:
    # ... runs pip-audit ...

  docker-image-scan:
    # ... runs Trivy ...

  build-and-push:
    needs: [python-dependency-scan, docker-image-scan]
    # ... builds and pushes Docker image ...
```

**This ensures:**
- Security scans run **before** building Docker images
- Build is **blocked** if HIGH or CRITICAL vulnerabilities are found
- No vulnerable images are pushed to the registry
- Failed scans prevent deployment to production

### Setting up required status checks

To enforce security scans on pull requests:

1. Go to **Settings** → **Branches** → **Branch protection rules**
2. Edit the rule for `develop` and `main`
3. Enable **Require status checks to pass before merging**
4. Search for and add:
   - `python-dependency-scan`
   - `docker-image-scan`
5. Save changes

Now PRs cannot be merged if security scans fail.

## Best Practices

### For developers

- ✅ Run `pip-audit` locally before committing dependency updates
- ✅ Keep dependencies pinned to specific versions in `requirements.txt`
- ✅ Review Dependabot PRs promptly, especially security updates
- ✅ Test locally after updating dependencies
- ✅ Document any risk acceptance decisions in commit messages or issues

### For maintainers

- ✅ Monitor the GitHub Security tab weekly
- ✅ Set security scans as required status checks on protected branches
- ✅ Triage vulnerability reports within 1 business day
- ✅ Prioritize CRITICAL/HIGH fixes in current sprint
- ✅ Keep base Docker images updated (`python:3.12-slim`)
- ✅ Review `.trivyignore` and `.pip-audit-ignore.json` quarterly

### For CI/CD

- ✅ Run security scans before building artifacts
- ✅ Fail fast on CRITICAL/HIGH vulnerabilities
- ✅ Upload SARIF reports to GitHub Security tab for tracking
- ✅ Schedule regular scans to catch new CVEs
- ✅ Monitor workflow failures and fix them promptly

## Troubleshooting

### Scan failing due to network issues

```bash
# pip-audit can't reach PyPI Advisory Database
Error: Failed to download vulnerability database

# Solution: Retry the workflow or check network connectivity
```

### False positives in Trivy

Some vulnerabilities may not apply to Playbook's use case:

```bash
# Create .trivyignore file
cat > .trivyignore <<EOF
# Not exploitable: Playbook doesn't use affected code path
CVE-2024-XXXX
EOF
```

Document the reason for ignoring in comments.

### Dependabot PRs failing tests

If a Dependabot PR breaks tests:

1. Comment `@dependabot ignore this major version` to skip major updates
2. Investigate breaking changes in the package changelog
3. Update Playbook code to handle API changes
4. Manually create a PR with the fix

### Security scan taking too long

Large Docker images can slow down Trivy scans. To optimize:

```dockerfile
# Use multi-stage builds to reduce final image size
FROM python:3.12-slim AS builder
# ... build steps ...

FROM python:3.12-slim
COPY --from=builder /app /app
```

## Additional Resources

- [pip-audit documentation](https://github.com/pypa/pip-audit)
- [Trivy documentation](https://aquasecurity.github.io/trivy/)
- [Dependabot documentation](https://docs.github.com/en/code-security/dependabot)
- [GitHub Security tab](https://docs.github.com/en/code-security/code-scanning)
- [PyPI Advisory Database](https://github.com/pypa/advisory-database)
- [CVE database](https://cve.mitre.org/)

Need help? Check [Troubleshooting & FAQ](troubleshooting.md) or open a GitHub issue.
