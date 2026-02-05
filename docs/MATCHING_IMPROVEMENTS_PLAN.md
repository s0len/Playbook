# Playbook Matching Improvements Plan

This document outlines the changes needed to achieve 100% match rate for the ~600 currently unmatched files.

## Implementation Status

| Category | Files | Status | Notes |
|----------|-------|--------|-------|
| NHL ISO date format | ~30+ | **DONE** | Added `NHL-*` and `nhl-*` source globs |
| UFC On ESPN | ~20+ | **DONE** | Added patterns and source globs |
| F1 Pre/Post Show | ~15+ | **DONE** | Fixed regex for hyphen + `.Show` suffix |
| F1 Weekend Warm-Up | ~5+ | **DONE** | Fixed regex for hyphen variant |
| IndyCar Round format | ~10+ | **DONE** | Changed `\d{2}` to `\d{1,2}` |
| Figure Skating location | ~5+ | **DONE** | Added location-to-event-name aliases |
| MotoGP 2026 | Future | **DONE** | Added 2026 variant |
| UFC season matching | 17 | **DONE** | Changed from `mode: title` to `mode: round` |
| WTA/Tennis files | ~400+ | Low Priority | Complex - many formats excluded by globs |
| NFL variant format | ~50+ | Pending | May need additional patterns |

---

## Completed Fixes

### 1. NHL - ISO date format source globs

Added `NHL-*` and `nhl-*` to default_source_globs to match files like `NHL-2025-11-22_NJD@PHI.mkv`.

### 2. UFC On ESPN - New patterns and source globs

Added 4 new patterns for UFC On ESPN events:
- Dot separated with session tag
- Space separated with session tag
- Dot separated without session tag
- Space separated without session tag

Added source globs: `UFC.On.ESPN.*`, `UFC On ESPN *`, `ufc.on.espn.*`, `ufc on espn *`

### 3. UFC Season Matching - Changed to round-based

Changed all UFC patterns from `mode: title` to `mode: round` with `group: season`. This matches UFC events by their event number (321, 263, 73, etc.) against the metadata's `round_number` or `display_number`, which is more reliable than title string matching.

**Why this is better:**
- Title matching fails when filenames have spelling variations (e.g., `makhacheve` vs `makhachev`)
- Event numbers are consistent between filenames and metadata
- No need for complex title normalization logic

### 4. Formula 1 - Pre/Post Show hyphen and .Show suffix

Updated regex to handle:
- Hyphen separator: `Pre-Race` instead of `Pre.Race`
- `.Show` suffix: `Post-Sprint.Show`
- Weekend Warm-Up hyphen variant

Added session aliases for all hyphen variants.

### 5. IndyCar - Round number without leading zero

Changed `Round(?P<round>\d{2})` to `Round(?P<round>\d{1,2})` to match both `Round06` and `Round6`.

### 6. Figure Skating - Location to event name aliases

Added aliases to map captured location names to actual ISU Grand Prix event names:
- `United State` / `United States` / `USA` / `US` → `Skate America`
- `France` → `Internationaux de France`
- `Canada` → `Skate Canada International`
- `Japan` → `NHK Trophy`
- `China` → `Cup of China`
- `Finland` → `Grand Prix of Espoo`
- `Final` → `Grand Prix Final`

### 7. MotoGP 2026 variant

Added 2026 variant with `show_slug: "motogp-2026"`.

### 8. WTA United Cup source globs

Added `*United Cup*` and `*United.Cup*` to WTA source globs.

---

## Test Commands

```bash
# Run pattern sample tests
pytest tests/test_pattern_samples.py -v

# Run matcher tests
pytest tests/test_matcher.py -v

# Run with trace output to debug specific files
python -m playbook.cli --config config/playbook.yaml --dry-run --verbose --trace-matches
```

---

## Files Modified

1. `src/playbook/pattern_templates.yaml` - All pattern changes
2. `tests/data/pattern_samples.yaml` - Updated UFC test data to use event numbers as round_numbers

---

## Remaining Work

### NFL variant format (if needed)
Files like `NFL 07-12-2025 Week14 Houston Texans vs...` may need additional pattern work if current patterns don't match.

### WTA/Tennis files
Complex and highly variable naming. The `allow_unmatched: true` flag is set to suppress warnings for exotic formats.
