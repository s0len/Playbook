# Investigation Notes: AttributeError in destination_builder.py

## Issue Description
The system crashes with an `AttributeError` when `build_destination()` tries to access `pattern.config.destination_root_template` at line 112 of `destination_builder.py`.

## Root Cause Analysis

### Expected vs Actual Types

**Expected**: `build_destination()` expects a `PatternRuntime` object as the `pattern` parameter:
```python
# destination_builder.py:89-94
def build_destination(
    runtime: SportRuntime,
    pattern: PatternRuntime,  # ← Expects PatternRuntime
    context: dict[str, Any],
    settings: Settings,
) -> Path:
```

**Actual**: `match_file_to_episode()` returns a `PatternConfig` object instead of `PatternRuntime`:

### Object Structure

**PatternRuntime** (matcher.py:174):
```python
@dataclass
class PatternRuntime:
    config: PatternConfig          # ← Has .config attribute
    regex: re.Pattern[str]
    session_lookup: SessionLookupIndex
```

**PatternConfig** (config.py:49):
```python
@dataclass
class PatternConfig:
    regex: str
    destination_root_template: str | None = None  # ← Direct attribute, no .config
    season_dir_template: str | None = None
    filename_template: str | None = None
    # ... other fields
```

### Exact Locations of Bug

#### Location 1: Regex Matching Path (matcher.py:1078)
```python
result = {
    "season": season,
    "episode": episode,
    "pattern": pattern_runtime.config,  # ← BUG: Returns PatternConfig
    "groups": groups,
}
```

**Should be**:
```python
"pattern": pattern_runtime,  # Returns PatternRuntime
```

#### Location 2: Structured Filename Matching Path (matcher.py:845 + 873)
```python
# Line 845 - Creates PatternConfig
pattern = PatternConfig(regex="structured", description="Structured filename matcher")

# Line 873 - Returns PatternConfig
return {
    "season": season,
    "episode": episode,
    "pattern": pattern,  # ← BUG: Returns PatternConfig
    "groups": groups,
}
```

**Should be**:
```python
# Line 845 - Create PatternRuntime
pattern = PatternRuntime(
    config=PatternConfig(regex="structured", description="Structured filename matcher"),
    regex=re.compile(".*"),  # Dummy regex since structured matching doesn't use regex
    session_lookup=SessionLookupIndex(),  # Empty lookup
)

# Line 873 - Returns PatternRuntime
return {
    "season": season,
    "episode": episode,
    "pattern": pattern,  # Now returns PatternRuntime
    "groups": groups,
}
```

### Call Chain

1. `processor.py:310` → `match_file_to_episode()` called
2. `processor.py:326` → `pattern = detection["pattern"]` (receives PatternConfig)
3. `processor.py:331` → `self._build_destination(runtime, pattern, context)` (passes PatternConfig)
4. `processor.py:472` → `build_destination(runtime=runtime, pattern=pattern, ...)` (passes PatternConfig)
5. `destination_builder.py:112` → `pattern.config.destination_root_template` **CRASHES** because PatternConfig has no `.config` attribute

### Why This Causes AttributeError

When `build_destination()` tries to access:
```python
pattern.config.destination_root_template  # Line 112
```

It fails because:
- `pattern` is a `PatternConfig` object (not `PatternRuntime`)
- `PatternConfig` does NOT have a `.config` attribute
- `PatternConfig` has `destination_root_template` as a direct attribute
- Python raises: `AttributeError: 'PatternConfig' object has no attribute 'config'`

## Fix Summary

**Change 1** (matcher.py:1078): Return `pattern_runtime` instead of `pattern_runtime.config`
**Change 2** (matcher.py:845): Create a `PatternRuntime` wrapper instead of bare `PatternConfig`

Both changes ensure that `match_file_to_episode()` always returns a `PatternRuntime` object in the "pattern" field, which is what `build_destination()` expects.

## Verification

Manual verification completed by reviewing:
- ✅ Object type definitions (PatternRuntime vs PatternConfig)
- ✅ Type annotations in build_destination() signature
- ✅ Return statements in match_file_to_episode() (both code paths)
- ✅ Call chain from processor through to destination_builder

The exact location where `PatternConfig` is incorrectly passed to `build_destination()` has been identified in two places in `matcher.py`.
