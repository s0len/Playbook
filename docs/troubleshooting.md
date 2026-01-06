# Troubleshooting & FAQ

Run into snags? Start with the quick triage grid below, then follow the deeper diagnostics checklist to narrow things down.

## Quick Triage

| Symptom | Likely cause | Immediate next step |
|---------|--------------|---------------------|
| CLI finishes instantly, nothing processed | `source_dir` not mounted/readable or `source_globs` too strict | Run `python -m playbook.cli --config ... --dry-run --verbose` and inspect `playbook.log` for “skipped” entries |
| Metadata looks stale / missing events | Cached YAML past TTL or wrong `metadata.url` | Delete `CACHE_DIR/metadata/*` or lower `metadata.ttl_hours`, then rerun with `--dry-run` |
| Hardlinks fail / files missing | Cross-filesystem moves or SMB/NFS target | Set `link_mode: copy` (global or per sport) and ensure destination mount permissions |
| Kometa/Autoscan never triggers | `settings.kometa_trigger.enabled` false or Autoscan rewrites wrong | Run `python -m playbook.cli kometa-trigger ...` to test; review notification targets for correct rewrites |
| Watcher never fires | `watchdog` missing or paths misconfigured | Check container logs for “watchdog unavailable”, confirm `file_watcher.paths` exist, or fall back to batch mode |

## Diagnostics Workflow

1. **Validate config:** `python -m playbook.cli validate-config --config playbook.yaml --diff-sample --show-trace`. Catch schema errors before wasting time elsewhere.
2. **Instrumented dry-run:** `python -m playbook.cli --config playbook.yaml --dry-run --verbose --trace-matches`. This produces console DEBUG output, persistent logs, and per-file trace JSON (under `cache_dir/traces`).
3. **Review logs:** Inspect `playbook.log` for warnings (missing metadata, Kometa trigger failures, Autoscan errors). The file rotates to `playbook.log.previous` every run—keep both when filing issues.
4. **Reset processed cache (optional):** `--clear-processed-cache` (or `CLEAR_PROCESSED_CACHE=true`) forces Playbook to treat every file as new—useful when you want to re-run test datasets.
5. **Isolate integrations:** 
   - Kometa: `python -m playbook.cli kometa-trigger --config ... --mode docker`
   - Autoscan: temporarily disable other targets so logs only contain Autoscan responses.
   - Notifications: point Discord/Slack webhooks at a test channel until you confirm formatting.

## Command Cheat Sheet

```bash
# Validate config with diff
python -m playbook.cli validate-config --config /config/playbook.yaml --diff-sample --show-trace

# Verbose dry-run with match traces
python -m playbook.cli --config /config/playbook.yaml --dry-run --verbose --trace-matches

# Force watcher mode off (single pass)
python -m playbook.cli --config /config/playbook.yaml --no-watch

# Manual Kometa trigger diagnostics
python -m playbook.cli kometa-trigger --config /config/playbook.yaml --mode docker --verbose
```

## Cache & Filesystem Hygiene

- **Safe to delete:**  
  `CACHE_DIR/metadata/*` (forces metadata refetch), `CACHE_DIR/processed_cache.json`, `LOG_DIR/*.previous`
- **Keep persistent:**  
  `playbook.yaml`, notification secrets, destination directory (Plex expects consistent paths), Kometa configs
- **Hardlink tips:**  
  Use `link_mode: copy` or `symlink` when crossing filesystems. On SMB/NFS mounts, confirm the server allows hardlinks or skip straight to copy mode.

## Integration Troubleshooting

### Kometa

- `Kometa trigger is disabled` → enable `settings.kometa_trigger.enabled` or pass `--mode docker/kubernetes` to the CLI.
- `Kometa docker trigger requires access to the Docker socket` → mount `/var/run/docker.sock` plus the Docker client binaries into the Playbook container.
- Kubernetes jobs stuck in `Active` → `kubectl delete job -l trigger=playbook` to clear them, then rerun.
- Use `kometa_trigger.docker.exec_command` to match whatever entrypoint your Compose stack uses; Playbook appends `--run-libraries`/`--config` automatically.

### Autoscan / Plex refreshes

- **404 errors** → Confirm Autoscan URL is reachable from Playbook's network namespace; check Docker network configuration and port mappings.
- **SSL/TLS certificate errors** → See [Certificate Configuration](#certificate-configuration) below for proper solutions. **Do not disable SSL verification** unless you understand the security risks.
- **Nothing happens after linking files** → Verify `rewrite` entries translate Playbook's destination into what Autoscan/Plex can see (inside Docker, paths often differ).
- **Plex scans stale metadata** → Pair Autoscan with Kometa triggers; Plex rescans directories immediately while Kometa updates titles/artwork.

#### Certificate Configuration

If you encounter SSL/TLS certificate verification errors when connecting to Autoscan, **do not immediately disable verification**. Instead, use one of these proper solutions:

1. **Use a CA-signed certificate** (recommended for production):
   - Obtain a certificate from Let's Encrypt or another trusted Certificate Authority
   - Configure your Autoscan server to use the CA-signed certificate
   - No Playbook configuration changes needed—verification will work automatically

2. **Add self-signed certificate to trust store** (for development/internal networks):
   ```bash
   # Copy your self-signed certificate into the container
   docker cp autoscan-cert.crt playbook:/usr/local/share/ca-certificates/

   # Update the certificate trust store
   docker exec playbook update-ca-certificates

   # Restart Playbook to pick up the new certificate
   docker restart playbook
   ```

3. **Disable verification (⚠️ NOT RECOMMENDED):**
   - **Only use this as a last resort in isolated development/testing environments**
   - Setting `verify_ssl: false` exposes your system to **man-in-the-middle (MITM) attacks**
   - **NEVER use this in production or on networks you don't fully control**
   - See the [Autoscan integration docs](integrations.md#autoscan-hooks) for detailed security warnings

The proper certificate configuration approach protects your system from MITM attacks while eliminating SSL errors. If you're still having issues after trying the above, review your certificate's Common Name (CN) or Subject Alternative Names (SAN) to ensure they match the hostname in your Autoscan URL.

### Autobrr / Downloader feeds

- Filters never match → use Autobrr’s regex tester and ensure `match_releases` are case-insensitive (`(?i)`), include the season/year, and restrict to trusted encoders.
- Wrong category/path → align Autobrr’s action category (e.g., `sports/f1`) with Playbook’s `source_globs` so new files land where pattern sets expect them.
- Duplicate grabs → leverage Autobrr `priority` and `excluded_words` to prefer one release group per sport.

## FAQ

**Can I run multiple configs?**  
Yes—launch separate containers/CLI processes with distinct `CONFIG_PATH`, `SOURCE_DIR`, and `DESTINATION_DIR`. Avoid pointing two configs at the same destination unless you coordinate notifications carefully.

**Does Playbook delete or move downloads?**  
No. Default is hardlinking. Switch to copy/symlink when cross-filesystem moves or NAS targets require it.

**How do I add a brand-new sport?**  
Follow the steps in [Recipes & How-tos](recipes.md#extending-to-new-sports), add real sample filenames to `tests/data/pattern_samples.yaml`, and consider upstreaming new pattern sets.

**Watcher vs batch—what should I use?**  
Use batch (cron/systemd) for infrequent reorganizations, watcher mode for continuous ingest. Even with watcher mode, schedule a nightly batch run as a safety net if your platform occasionally drops filesystem events.

**Where should I ask for help?**  
Open an issue with:
- Playbook version (container tag or commit SHA)
- Relevant excerpts from `playbook.log`
- Redacted `playbook.yaml` (remove secrets)
- Example filenames that failed to match

Still blocked? [Start a discussion or open an issue](https://github.com/s0len/playbook/issues) and we’ll dig in. The more context (logs, configs, sample names) you provide, the faster we can help.

