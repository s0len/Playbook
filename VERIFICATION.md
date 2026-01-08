# NHL Poster Persistence Verification Guide

## Overview

This document provides step-by-step instructions for manually verifying that the NHL poster persistence fix works correctly in Plex. The fix implements a poster field unlock → upload → lock → refresh sequence to ensure posters remain visible after Kometa/Playbook updates them.

**What Was Fixed:**
- Added `unlock_field()` and `lock_field()` methods to PlexClient
- Modified `_apply_metadata()` in plex_metadata_sync to unlock poster fields before upload
- Poster fields are now locked after successful upload to prevent agent overwrites
- Metadata refresh is triggered to clear cache and display new posters immediately

**Root Cause:**
Plex automatically locks any field that is manually edited (via UI or API). Once locked, subsequent uploads are ignored or immediately reverted by metadata agents. The fix ensures fields are unlocked before upload and optionally locked afterward to preserve custom artwork.

---

## Prerequisites

Before starting verification, ensure you have:

1. **Playbook configured with plex_metadata_sync enabled**
   - Configuration file: `config/playbook.yaml`
   - Required settings in config:
     ```yaml
     plex_metadata_sync:
       enabled: true
       plex_url: http://your-plex-server:32400
       plex_token: your-plex-token-here
       lock_poster_fields: true  # Optional: defaults to false
     ```

2. **NHL content in Plex library**
   - At least one NHL show/season/episode with existing poster
   - Library should be accessible via Plex Web App

3. **Access to Plex Web App**
   - Browser with access to `http://your-plex-server:32400/web`
   - Ability to hard refresh (Ctrl+F5 / Cmd+Shift+R)

4. **Playbook environment ready**
   - Docker container running OR
   - Python virtual environment activated
   - Config file accessible at specified path

---

## Verification Steps

### Step 1: Document Current Poster State (Baseline)

Before running Playbook, capture the current state of NHL posters:

1. Open Plex Web App: `http://your-plex-server:32400/web`
2. Navigate to your NHL library (e.g., "Sports" or "NHL")
3. Take screenshots of 2-3 NHL items showing their current posters
4. Note the item titles for later reference

**Expected Result:** You have baseline screenshots of current poster artwork.

---

### Step 2: Run Playbook with Metadata Sync Enabled

Execute Playbook to update NHL metadata and posters:

**Docker Method:**
```bash
docker run --rm -it \
  -v /path/to/config:/config \
  -v /path/to/downloads:/data/source \
  -v /path/to/library:/data/destination \
  -v /path/to/cache:/var/cache/playbook \
  ghcr.io/s0len/playbook:latest \
  --config /config/playbook.yaml \
  --verbose
```

**Python Method:**
```bash
# Activate virtual environment
source .venv/bin/activate

# Run Playbook
python -m playbook.cli --config config/playbook.yaml --verbose
```

**What to Look For in Logs:**

The verbose output should include:
```
DEBUG: Unlocked field 'thumb' for rating_key=12345
DEBUG: Setting poster for rating_key=12345
DEBUG: Locked field 'thumb' for rating_key=12345
INFO: Updated poster for NHL item: "Team vs Team - 2024-12-15"
```

If you see these log messages, the unlock/lock sequence is working correctly.

**Expected Result:** Playbook completes successfully with "Unlocked field" and "Locked field" debug messages in logs.

---

### Step 3: Verify Posters Updated in Plex

Immediately after Playbook finishes:

1. Return to Plex Web App (keep the same browser window/tab open)
2. Navigate back to the NHL library
3. Look at the items you documented in Step 1
4. Observe whether posters have changed to new artwork

**What You Might See:**
- ✅ **Success:** New posters are visible immediately
- ⚠️ **Cached:** Old posters still showing (proceed to Step 4 for hard refresh)
- ❌ **Flash and Revert:** Posters briefly change then revert (indicates fix did not apply)

**Expected Result:** New posters are visible (or become visible after hard refresh in Step 4).

---

### Step 4: Hard Refresh Browser Cache

Browser caching can cause old posters to persist. Force a cache clear:

1. While viewing the NHL library in Plex Web App:
   - **Windows/Linux:** Press `Ctrl + F5` or `Ctrl + Shift + R`
   - **Mac:** Press `Cmd + Shift + R`
2. Wait 5-10 seconds for page to fully reload
3. Check if posters now show new artwork

**Alternative Method (if hard refresh doesn't work):**
1. Open browser DevTools (F12)
2. Right-click the refresh button → Select "Empty Cache and Hard Reload"
3. Close DevTools and check posters again

**Expected Result:** After hard refresh, new posters are visible.

---

### Step 5: Wait 10 Minutes (Persistence Test)

This is the critical test to verify the poster locking fix works:

1. Set a timer for 10 minutes
2. Leave Plex Web App open OR close and reopen after 10 minutes
3. During this time, Plex may perform background metadata refresh operations
4. After 10 minutes, return to the NHL library and check posters

**Why 10 Minutes?**
Plex periodically refreshes metadata in the background. The original bug caused posters to revert during these automatic refreshes. If posters remain after 10 minutes, the locking mechanism is working correctly.

**Expected Result:** Posters still show new artwork (no reversion to old thumbnails).

---

### Step 6: Perform Another Hard Refresh (Final Verification)

After the 10-minute wait:

1. Perform another hard refresh (Ctrl+F5 / Cmd+Shift+R)
2. Verify posters STILL show new artwork
3. Click into individual NHL items and verify poster details
4. Check that poster images load correctly (no broken images)

**Expected Result:** Posters persist after hard refresh. No reversion to old artwork.

---

## Success Criteria

✅ **Verification PASSES if:**
- Playbook logs show "Unlocked field" and "Locked field" messages
- New posters are visible in Plex Web App after Step 3 or 4
- Posters remain visible after 10-minute wait (Step 5)
- Posters persist after final hard refresh (Step 6)
- No console errors or broken images in browser DevTools

❌ **Verification FAILS if:**
- No unlock/lock messages in Playbook logs
- Posters revert to old artwork after 10-minute wait
- Posters flash/flicker and immediately revert to old thumbnails
- Browser console shows 404 errors for poster image URLs
- Plex shows "Poster unavailable" placeholder images

---

## Troubleshooting

### Issue: Posters Still Revert After Fix

**Possible Causes:**
1. **Config not loaded:** Verify `plex_metadata_sync.enabled: true` in config
2. **Wrong Plex token:** Check `plex_token` is valid and has write permissions
3. **Plex agents overwriting:** Try setting `lock_poster_fields: true` in config
4. **Cache not cleared:** Plex server cache may need manual clear

**Debug Steps:**
```bash
# Check Playbook config is valid
python -m playbook.cli --config config/playbook.yaml --validate

# Run with verbose logging to see API calls
python -m playbook.cli --config config/playbook.yaml --verbose

# Check Plex server logs for errors
# Location: <Plex Media Server>/Logs/Plex Media Server.log
```

---

### Issue: No "Unlocked field" Messages in Logs

**Possible Causes:**
1. **Verbose mode not enabled:** Add `--verbose` flag or set `VERBOSE=true`
2. **Old code running:** Ensure latest changes are deployed
3. **Metadata sync disabled:** Check `plex_metadata_sync.enabled: true`

**Debug Steps:**
```bash
# Verify unlock_field method exists in PlexClient
python -c "from src.playbook.plex_client import PlexClient; print('unlock_field' in dir(PlexClient))"
# Expected output: True

# Check implementation_plan.json shows subtasks 3-1 and 3-2 completed
cat .auto-claude/specs/029-posters-in-plex-for-nhl-no-longer-update-though-yo/implementation_plan.json | grep -A2 "subtask-3-1"
```

---

### Issue: Posters Show as Broken Images

**Possible Causes:**
1. **Invalid poster URL:** Metadata source returned broken URL
2. **Network issue:** Plex cannot reach poster image source
3. **Asset upload failed:** Check Playbook logs for "Failed to set asset" errors

**Debug Steps:**
```bash
# Check Playbook logs for asset errors
grep -i "failed.*asset" /path/to/playbook.log

# Test poster URL directly in browser
# (URL should be visible in Playbook debug logs)

# Verify Plex can reach external URLs
# Check Plex server network connectivity
```

---

### Issue: Changes Not Reflected in Plex

**Possible Causes:**
1. **Wrong Plex server URL:** Verify `plex_url` points to correct server
2. **Library not scanned:** Plex hasn't picked up new metadata
3. **Cache not refreshed:** Browser or Plex server cache is stale

**Debug Steps:**
```bash
# Test Plex API connectivity
curl -v http://your-plex-server:32400/identity?X-Plex-Token=your-token

# Check if rating_keys in logs match Plex items
# Navigate to item in Plex Web App, check URL for ratingKey parameter

# Manually trigger Plex library scan
# Plex Web App → Library → ... → Scan Library Files
```

---

## Expected Log Output (Reference)

Successful Playbook run with poster update should show:

```
INFO: Starting Playbook metadata sync
DEBUG: Fetching metadata for NHL 2024-25
DEBUG: Processing item: "Tampa Bay Lightning vs Florida Panthers - 2024-12-15"
DEBUG: Resolved poster URL: https://example.com/posters/nhl-2024-12-15.jpg
DEBUG: Unlocked field 'thumb' for rating_key=54321
DEBUG: Setting poster for rating_key=54321 with URL: https://example.com/...
DEBUG: Locked field 'thumb' for rating_key=54321
INFO: Updated poster for "Tampa Bay Lightning vs Florida Panthers - 2024-12-15"
INFO: Metadata sync complete - 3 items processed, 3 assets updated
```

---

## Verification Checklist

Use this checklist when performing verification:

- [ ] Baseline screenshots captured (Step 1)
- [ ] Playbook run completed successfully (Step 2)
- [ ] Logs show "Unlocked field" messages (Step 2)
- [ ] Logs show "Locked field" messages (Step 2)
- [ ] New posters visible after initial check (Step 3)
- [ ] Hard refresh performed (Step 4)
- [ ] Posters still visible after hard refresh (Step 4)
- [ ] 10-minute wait completed (Step 5)
- [ ] Posters persist after wait (Step 5)
- [ ] Final hard refresh performed (Step 6)
- [ ] Posters STILL persist after final refresh (Step 6)
- [ ] No browser console errors (Step 6)
- [ ] No broken images or placeholders (Step 6)

---

## Additional Testing (Optional)

### Test Multiple NHL Items

To thoroughly verify the fix:

1. Select 5-10 different NHL items across multiple shows/seasons
2. Document their current posters (screenshots)
3. Run Playbook metadata sync
4. Verify ALL items update correctly
5. Wait 10 minutes and confirm ALL persist

### Test Lock Configuration Option

Test both lock_poster_fields values:

**Test 1: With Locking (Recommended)**
```yaml
plex_metadata_sync:
  lock_poster_fields: true
```
- Posters should persist indefinitely
- Plex agents will NOT overwrite custom posters

**Test 2: Without Locking**
```yaml
plex_metadata_sync:
  lock_poster_fields: false
```
- Posters upload successfully but may be overwritten by agents
- Useful if you want Plex to update posters from metadata providers

### Test with Plex Metadata Refresh

Trigger a manual Plex metadata refresh to verify locking:

1. Update NHL item posters via Playbook
2. In Plex Web App: Right-click item → "Match..."
3. Select same match and click "Match"
4. Check if poster reverts

**Expected:** With `lock_poster_fields: true`, poster should NOT revert.

---

## Next Steps After Verification

If verification **PASSES:**
1. ✅ Mark subtask-4-3 as completed in implementation_plan.json
2. ✅ Commit VERIFICATION.md to repository
3. ✅ Proceed to QA sign-off phase

If verification **FAILS:**
1. ❌ Document failure details in build-progress.txt
2. ❌ Review troubleshooting steps above
3. ❌ Check if earlier subtasks (3-1, 3-2, 3-3) are properly implemented
4. ❌ Run unit and integration tests to identify regression
5. ❌ DO NOT mark subtask as completed until issue is resolved

---

## Related Documentation

- **INVESTIGATION.md** - Technical details of Plex API field locking
- **POSTER_FLOW_TRACE.md** - Code flow analysis of poster upload
- **spec.md** - Original problem specification and acceptance criteria
- **implementation_plan.json** - Complete implementation plan with all subtasks

---

## Verification Metadata

**Subtask:** subtask-4-3
**Phase:** Testing and Verification
**Type:** Manual Verification
**Date Created:** January 7, 2026
**Estimated Duration:** 15-20 minutes (including 10-minute wait)

---

**Document Status:** ✅ Ready for Use
**Last Updated:** January 7, 2026
