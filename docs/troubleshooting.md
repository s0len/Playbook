# Troubleshooting & FAQ

Run into snags? Start here before diving into the code.

## Common Failures

- **Nothing gets processed** – Confirm `source_dir` is mounted/readable and matches `source_globs`. Enable `--verbose` (or `LOG_LEVEL=DEBUG`) to see why releases were skipped.
- **Metadata looks stale** – Delete the cache directory (`rm -rf /var/cache/playbook/metadata`) or lower `metadata.ttl_hours` for the affected sport.
- **Hardlinks fail** – Switch `link_mode: copy` (globally or per sport) when crossing filesystems or writing to SMB/NFS shares.
- **Pattern matches the wrong season** – Adjust `season_selector` mappings or add `season_overrides` to force round numbers for exhibitions/pre-season events.
- **Need to re-run immediately** – Run `python -m playbook.cli --no-watch ...` (or set `WATCH_MODE=false`) to perform an on-demand pass even if watcher mode is enabled.

## Diagnostics Workflow

1. Run `python -m playbook.cli validate-config --config playbook.yaml --diff-sample` to rule out schema or typo errors.
2. Enable `VERBOSE=true` and `--dry-run` so you can iterate without touching the filesystem.
3. Inspect `playbook.log` for warnings about missing metadata, Kometa trigger failures, or notification issues.
4. Use `--clear-processed-cache` if the processor keeps skipping files you want to re-evaluate immediately.
5. When debugging Kometa triggers, run `python -m playbook.cli kometa-trigger --config ... --mode <docker|kubernetes>` to isolate that integration.

## Cache Hygiene

- Safe to delete: `CACHE_DIR/metadata/*`, `CACHE_DIR/processed_cache.json`, `LOG_DIR/*.previous`.
- Keep persistent: `playbook.yaml`, notification secrets, long-term cache directories if you need warm starts.

## FAQ

**Can I run multiple configs?**  
Yes—start multiple containers (or CLI processes) with different `CONFIG_PATH` values and distinct destination directories. Avoid pointing two configs at the same destination unless you coordinate notification targets carefully.

**Does Playbook move or delete original downloads?**  
No. The default action is hardlinking. Set `link_mode: copy` or `symlink` when required by your storage layout.

**How do I add a brand-new sport?**  
Follow the steps in [Recipes & How-tos](recipes.md#extending-to-new-sports) and consider contributing pattern sets back to the repo so others benefit.

Still blocked? [Open an issue](https://github.com/s0len/playbook/issues) with logs, config snippets (redact secrets), and the release names that fail to match.

