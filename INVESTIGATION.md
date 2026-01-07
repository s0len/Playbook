# Plex API Field Locking Investigation

## Overview

This document details the Plex Media Server HTTP API endpoints for field locking/unlocking, specifically for poster (thumb) fields. The investigation reveals how to properly unlock poster fields before upload and re-lock them afterward to ensure poster persistence.

## Problem Summary

**Root Cause:** Plex automatically locks any field that is manually edited (via UI or API). Once locked, the field will NOT be updated by metadata agents during refresh operations. The current Playbook implementation calls `set_asset()` to upload posters but does NOT unlock the field first, causing Plex to either:
1. Ignore the upload (if field is locked), or
2. Accept the upload but then lock it, preventing future agent-based updates

**Solution:** Implement unlock → upload → lock → refresh sequence using the Plex HTTP API.

---

## Plex API Endpoints

### 1. Update Metadata (Generic Endpoint)

**HTTP Method:** `PUT`

**Endpoint:**
```
PUT /library/metadata/{rating_key}
```

**Purpose:** Update any metadata field including locking/unlocking fields.

**Query Parameters:**
- `{field_name}.value={value}` - Set field value
- `{field_name}.locked={0|1}` - Lock (1) or unlock (0) field
- `type={media_type}` - Media type (2=show, 3=season, 4=episode)
- `X-Plex-Token={token}` - Authentication token (header or query param)

**Examples:**

Unlock poster field:
```http
PUT /library/metadata/12345?thumb.locked=0&X-Plex-Token={token}
```

Lock poster field:
```http
PUT /library/metadata/12345?thumb.locked=1&X-Plex-Token={token}
```

Update title and lock it:
```http
PUT /library/metadata/12345?title.value=New%20Title&title.locked=1&X-Plex-Token={token}
```

---

### 2. Set Asset (Poster Upload)

**HTTP Method:** `PUT`

**Endpoint:**
```
PUT /library/metadata/{rating_key}/{element}
```

**Purpose:** Upload artwork asset from URL.

**Path Parameters:**
- `{rating_key}` - Plex item identifier
- `{element}` - Asset type: `thumb` (poster), `art` (background), `banner`, `clearLogo`, `theme`

**Query Parameters:**
- `url={image_url}` - URL to image file (local or remote)
- `X-Plex-Token={token}` - Authentication token

**Example:**
```http
PUT /library/metadata/12345/thumb?url=http://example.com/poster.jpg&X-Plex-Token={token}
```

**Current Implementation:**
See `PlexClient.set_asset()` in `src/playbook/plex_client.py` lines 449-466.

---

### 3. Refresh Metadata

**HTTP Method:** `PUT`

**Endpoint:**
```
PUT /library/metadata/{rating_key}/refresh
```

**Purpose:** Trigger metadata refresh to clear cache and reload asset.

**Query Parameters:**
- `X-Plex-Token={token}` - Authentication token

**Example:**
```http
PUT /library/metadata/12345/refresh?X-Plex-Token={token}
```

**Current Implementation:**
See `PlexClient.refresh_metadata()` in `src/playbook/plex_client.py` lines 468-470.

---

## Required Sequence for Poster Upload

The correct sequence to ensure poster persistence is:

```
1. Unlock field   → PUT /library/metadata/{key}?thumb.locked=0
2. Upload poster  → PUT /library/metadata/{key}/thumb?url={url}
3. Lock field     → PUT /library/metadata/{key}?thumb.locked=1
4. Refresh cache  → PUT /library/metadata/{key}/refresh
```

**Why this sequence matters:**

1. **Unlock first:** If field is locked from previous edits, upload may be silently ignored
2. **Upload:** Apply new poster from URL
3. **Lock after:** Prevent Plex metadata agents from overwriting custom poster during automatic refreshes
4. **Refresh:** Clear server/client cache to immediately display new poster

---

## PlexAPI Library Implementation Reference

The Python PlexAPI library (used in spec examples but NOT in Playbook) implements this via the `PosterLockMixin` class:

```python
class PosterLockMixin:
    """ Mixin for Plex objects that can have a locked poster. """

    def lockPoster(self):
        """ Lock the poster for a Plex object. """
        return self._edit(**{'thumb.locked': 1})

    def unlockPoster(self):
        """ Unlock the poster for a Plex object. """
        return self._edit(**{'thumb.locked': 0})
```

**HTTP Translation:**
- `lockPoster()` → `PUT /library/metadata/{key}?thumb.locked=1`
- `unlockPoster()` → `PUT /library/metadata/{key}?thumb.locked=0`

---

## Proposed PlexClient Implementation

### New Methods to Add

**File:** `src/playbook/plex_client.py`

**Method 1: `unlock_field()`**

```python
def unlock_field(self, rating_key: str, field: str) -> None:
    """Unlock a metadata field to allow updates.

    Args:
        rating_key: The Plex rating key of the item.
        field: Field name (e.g., 'thumb', 'art', 'title', 'summary').
    """
    params = {f"{field}.locked": 0}
    self._request("PUT", f"/library/metadata/{rating_key}", params=params)
    LOGGER.debug("Unlocked field '%s' for rating_key=%s", field, rating_key)
```

**Method 2: `lock_field()`**

```python
def lock_field(self, rating_key: str, field: str) -> None:
    """Lock a metadata field to prevent agent overwrites.

    Args:
        rating_key: The Plex rating key of the item.
        field: Field name (e.g., 'thumb', 'art', 'title', 'summary').
    """
    params = {f"{field}.locked": 1}
    self._request("PUT", f"/library/metadata/{rating_key}", params=params)
    LOGGER.debug("Locked field '%s' for rating_key=%s", field, rating_key)
```

**Usage Pattern:**

```python
# Before uploading poster
plex_client.unlock_field(rating_key, "thumb")
plex_client.set_asset(rating_key, "thumb", poster_url)
plex_client.lock_field(rating_key, "thumb")  # Optional
plex_client.refresh_metadata(rating_key)
```

---

## Integration Points

### Current Code Flow

**File:** `src/playbook/plex_metadata_sync.py`

**Function:** `_apply_metadata()` (lines 361-445)

**Current Implementation:**
```python
# Line 427: Direct asset upload without unlocking
if poster_url:
    self.plex_client.set_asset(rating_key, "thumb", poster_url)
    self.stats.assets_updated += 1
```

**Problem:** No unlock before upload, no lock after upload, no refresh call.

---

### Proposed Code Flow

**Updated Implementation:**
```python
# Updated _apply_metadata() function
if poster_url:
    try:
        # Step 1: Unlock poster field
        self.plex_client.unlock_field(rating_key, "thumb")

        # Step 2: Upload poster
        self.plex_client.set_asset(rating_key, "thumb", poster_url)

        # Step 3: Lock poster field (configurable)
        if self.config.get("plex_metadata_sync", {}).get("lock_poster_fields", True):
            self.plex_client.lock_field(rating_key, "thumb")

        # Step 4: Refresh metadata cache
        self.plex_client.refresh_metadata(rating_key)

        self.stats.assets_updated += 1
        LOGGER.debug("Poster updated with unlock/lock sequence for rating_key=%s", rating_key)

    except PlexApiError as exc:
        LOGGER.error("Failed to update poster for rating_key=%s: %s", rating_key, exc)
        self.stats.assets_failed += 1
```

**Configuration Option:**

Add to `src/playbook/config.py`:
```python
plex_metadata_sync:
  lock_poster_fields: true  # Default: true (lock after upload)
```

Setting to `false` allows Plex agents to update posters during automatic refreshes.

---

## API Response Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Continue to next step |
| 400 | Invalid field name | Check field parameter |
| 401 | Invalid auth token | Verify X-Plex-Token |
| 404 | Item not found | Verify rating_key exists |
| 429 | Rate limit | Retry with backoff |
| 500 | Invalid field data | Check value format |

**Note:** PlexClient already implements retry logic for 429/500 status codes (see lines 22-24).

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_plex_client.py`

**Test Cases:**
1. `test_unlock_field()` - Verify PUT request with `thumb.locked=0`
2. `test_lock_field()` - Verify PUT request with `thumb.locked=1`
3. `test_unlock_field_invalid_rating_key()` - Verify 404 handling
4. `test_unlock_field_rate_limit()` - Verify retry on 429

### Integration Tests

**File:** `tests/test_plex_metadata_sync.py`

**Test Cases:**
1. `test_poster_unlock_before_upload()` - Verify unlock called before set_asset
2. `test_poster_lock_after_upload()` - Verify lock called after set_asset
3. `test_poster_refresh_after_upload()` - Verify refresh_metadata called
4. `test_poster_lock_configurable()` - Verify lock_poster_fields config respected

### Manual Verification

**Steps:**
1. Run Playbook metadata sync with plex_metadata_sync enabled
2. Check Plex web UI - verify NHL posters update
3. Wait 10 minutes (ensure no reversion)
4. Hard refresh browser (Ctrl+F5)
5. Confirm posters still show new artwork

---

## References

**Plex API Documentation:**
- [Plexopedia: Update Movie API](https://www.plexopedia.com/plex-media-server/api/library/movie-update/) - HTTP endpoint details and field locking syntax
- [Python PlexAPI Mixins](https://python-plexapi.readthedocs.io/en/latest/modules/mixins.html) - PosterLockMixin reference implementation
- [Plex API Documentation](https://plexapi.dev/Intro) - General API overview

**Community Resources:**
- [How to Stop Plex from Changing Movie Posters](https://www.plexopedia.com/blog/keep-plex-posters/) - Field locking behavior explanation
- [Plex Forum: Unlock Metadata Fields](https://forums.plex.tv/t/how-to-unlock-locked-metadata-fields-en-masse/673826) - Bulk unlock scripting examples
- [JBOPS Poster Scripts](https://github.com/blacktwin/JBOPS/blob/master/utility/plex_api_poster_pull.py) - Community poster management scripts

**PlexAPI Source Code:**
- [PlexAPI GitHub](https://github.com/pkkid/python-plexapi) - Official Python library implementation
- [PlexAPI Library Module](https://python-plexapi.readthedocs.io/en/latest/modules/library.html) - Library object methods

---

## Key Insights

1. **Field Locking is Automatic:** Any edit (UI or API) automatically locks the field
2. **Locked Fields Ignore Updates:** Metadata agents skip locked fields during refresh
3. **HTTP API is Simple:** Just add `{field}.locked={0|1}` to PUT request
4. **Unlock is Idempotent:** Safe to unlock already-unlocked fields
5. **Lock is Optional:** Can leave unlocked if you want agents to update posters
6. **Refresh Clears Cache:** Required to see changes immediately in web/mobile apps
7. **Existing PlexClient Patterns:** Current code uses `update_metadata()` with `lock_fields=True` for text fields (line 418), but NOT for assets

---

## Next Steps

1. ✅ **COMPLETED:** Research Plex API field locking endpoints
2. **PENDING:** Identify integration points in PlexClient (subtask-2-2)
3. **PENDING:** Implement `unlock_field()` and `lock_field()` methods (subtask-3-1)
4. **PENDING:** Integrate into `_apply_metadata()` workflow (subtask-3-2)
5. **PENDING:** Add configuration option (subtask-3-3)
6. **PENDING:** Write unit tests (subtask-4-1)
7. **PENDING:** Write integration tests (subtask-4-2)
8. **PENDING:** Manual verification with NHL library (subtask-4-3)

---

## Decision

**Recommended Approach:**

Add two new methods to `PlexClient`:
- `unlock_field(rating_key, field)` - Generic field unlock
- `lock_field(rating_key, field)` - Generic field lock

These methods follow existing patterns in `PlexClient.update_metadata()` which already implements field locking for text fields (line 441: `clean_params[f"{key}.locked"] = 1`).

**Why Generic Methods:**
- Works for any lockable field (thumb, art, title, summary, etc.)
- Consistent with Plex API design
- Reusable for future enhancements (e.g., background art, banners)
- Follows single responsibility principle

**Integration Location:**
- Call in `plex_metadata_sync.py` → `_apply_metadata()` function
- Before `set_asset()` call (line 427)
- After successful upload
- Before `refresh_metadata()` (not currently called for assets)

---

**Investigation Status:** ✅ COMPLETE

**Date:** January 7, 2026

**Next Subtask:** subtask-2-2 - Identify where to add unlock logic in PlexClient
