# Specification: Improve Sports Matcher to Prevent Incorrect NBA Game Matches

## Overview

The current sports file matcher is producing incorrect matches for NBA games. Files are being matched to completely wrong games - the correct home team is found but the away team and episode dates are wrong. For example, "Indiana Pacers vs Boston Celtics 22 12" gets matched to "Boston Celtics vs Miami Heat (episode 16)" instead of the correct game. This task will fix the matcher by adding NBA team aliases, requiring both teams to match, and improving date parsing for trailing date formats.

## Workflow Type

**Type**: feature

**Rationale**: This is a feature enhancement that requires adding new functionality (NBA team aliases), modifying existing matching logic (stricter team validation), and improving parsing (trailing date formats). While it's fixing bugs, the scope requires new code and architectural changes.

## Task Scope

### Services Involved
- **main** (primary) - Single Python application containing all matching logic

### This Task Will:
- [ ] Add NBA team aliases to `team_aliases.py`
- [ ] Require BOTH teams to match in episode scoring (not just one)
- [ ] Fix trailing date parsing for formats like "Team A vs Team B 22 12" (day month at end)
- [ ] Add sport detection from filename prefix (NBA, NHL, EPL, etc.)
- [ ] Improve team matching validation to prevent partial matches
- [ ] Add comprehensive tests for NBA matching scenarios

### Out of Scope:
- Changes to metadata fetching or database structure
- UI/frontend changes
- Configuration file format changes
- Other sports beyond NBA fixes (though the pattern will benefit all sports)

## Service Context

### Main Service

**Tech Stack:**
- Language: Python 3.14
- Framework: None (standalone application)
- Key Dependencies: rapidfuzz (fuzzy matching), python-dateutil

**Key Directories:**
- `src/playbook/` - Source code
- `src/playbook/parsers/` - Filename parsing logic
- `tests/` - Test files
- `config/` - Configuration

**Entry Point:** `src/playbook/cli.py`

**How to Run:**
```bash
# Run tests
pytest tests/

# Run specific matcher tests
pytest tests/test_matcher.py tests/test_structured_matcher.py -v
```

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `src/playbook/team_aliases.py` | main | Add `_NBA_TEAM_SYNONYMS` dictionary with all 30 NBA teams and their common aliases/abbreviations |
| `src/playbook/matcher.py` | main | Modify `_score_structured_match()` to require BOTH teams to match, not just overlap. Add sport detection logic |
| `src/playbook/parsers/structured_filename.py` | main | Improve `_parse_date_candidates()` to handle trailing day/month formats like "22 12" after team names |
| `tests/test_matcher.py` | main | Add tests for NBA matching scenarios including the reported failures |
| `tests/test_structured_matcher.py` | main | Add NBA-specific structured matching tests |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `src/playbook/team_aliases.py` | Follow the exact pattern of `_NHL_TEAM_SYNONYMS` and `_EPL_TEAM_SYNONYMS` for NBA teams |
| `tests/test_matcher.py` | Follow `TestScoreStructuredMatchWithDates` class structure for new tests |
| `tests/test_structured_matcher.py` | Follow `test_structured_match_nhl_abbreviations()` pattern for NBA tests |

## Patterns to Follow

### Team Alias Dictionary Pattern

From `src/playbook/team_aliases.py`:

```python
_NHL_TEAM_SYNONYMS: Dict[str, Iterable[str]] = {
    "Anaheim Ducks": ["Ducks", "Anaheim", "ANA"],
    "Boston Bruins": ["Bruins", "Boston", "BOS"],
    # ... more teams
}
```

**Key Points:**
- Canonical team name as dictionary key
- List of aliases including: short name, city, 3-letter abbreviation
- Register the map in `_TEAM_ALIAS_MAPS` with a key like `"nba"`

### Scoring Logic Pattern

From `src/playbook/matcher.py` lines 641-679:

```python
def _score_structured_match(
    structured: StructuredName, season: Season, episode: Episode, alias_lookup: Dict[str, str]
) -> float:
    score = 0.0
    episode_teams = _extract_teams_from_text(episode.title, alias_lookup)
    structured_tokens = {normalize_token(team) for team in structured.teams if team}
    episode_tokens = {normalize_token(team) for team in episode_teams if team}

    # Date proximity check
    if structured.date and episode.originally_available:
        if not _dates_within_proximity(structured.date, episode.originally_available, tolerance_days=2):
            return 0.0
        score += 0.4

    # Team matching - CURRENT ISSUE: allows partial overlap
    if structured_tokens and episode_tokens:
        if structured_tokens == episode_tokens:
            score += 0.55
        else:
            overlap = structured_tokens.intersection(episode_tokens)
            if overlap:
                score += 0.35 + 0.05 * len(overlap)  # <-- THIS ALLOWS PARTIAL MATCHES
```

**Key Points:**
- Current logic gives points for partial team overlap (one team matching)
- Should require BOTH teams to match for sports like NBA/NHL
- The `overlap` calculation allows matches where only one team is correct

### Date Parsing Pattern

From `src/playbook/parsers/structured_filename.py`:

```python
def _parse_date_candidates(text: str) -> Tuple[Optional[dt.date], Optional[int]]:
    # Day/Month fragments with year elsewhere (e.g., "EPL 2025 Fulham vs City 02 12")
    if standalone_year:
        fragment_match = re.search(r"(?P<d>\d{1,2})[.\-/ ](?P<m>\d{1,2})(?!\d)", joined)
```

**Key Points:**
- Currently parses "02 12" format after team names
- May need adjustment for NBA filenames like "22 12" at end
- Year is extracted separately from the 4-digit year token

## Requirements

### Functional Requirements

1. **Add NBA Team Aliases**
   - Description: Create comprehensive alias mapping for all 30 NBA teams
   - Acceptance: NBA team names, cities, and abbreviations resolve to canonical team names

2. **Require Both Teams to Match**
   - Description: Modify scoring to require both teams from filename to match episode teams
   - Acceptance: Files with one correct team but wrong other team return score 0.0

3. **Fix Trailing Date Parsing**
   - Description: Parse dates that appear after team names (e.g., "Team A vs Team B 22 12")
   - Acceptance: "22 12" correctly parses as December 22 when year is available from filename prefix

4. **Add Sport Detection**
   - Description: Detect sport from filename prefix (NBA, NHL, EPL) to select appropriate team alias map
   - Acceptance: NBA filenames automatically use NBA team aliases

5. **Improve Match Disambiguation**
   - Description: When multiple episodes match by teams, use date to select correct one
   - Acceptance: Same teams playing on different dates match to correct episodes

### Edge Cases

1. **Same Teams Multiple Games** - When teams play each other multiple times in a season, date must disambiguate
2. **Missing Date** - When no date is available, fall back to team-only matching (existing behavior)
3. **Team Name Variations** - Handle "Celtics" vs "Boston Celtics" vs "BOS" all mapping to same team
4. **Timezone Differences** - Allow ±2 day tolerance for date matching (existing behavior)

## Implementation Notes

### DO
- Follow the exact pattern in `team_aliases.py` for NBA teams - use same dictionary structure
- Reuse `_build_alias_map()` function for creating the lookup
- Keep the 2-day tolerance for date matching (handles timezones)
- Add tests for each reported failure case

### DON'T
- Don't remove partial matching entirely - it's needed as fallback when dates are unavailable
- Don't change the minimum score threshold (0.6) without careful consideration
- Don't break existing NHL/EPL matching while fixing NBA

## Development Environment

### Start Services

```bash
# Install dependencies
pip install -e .

# Run all tests
pytest tests/ -v

# Run matcher tests only
pytest tests/test_matcher.py tests/test_structured_matcher.py -v

# Run with coverage
pytest tests/ --cov=src/playbook --cov-report=term-missing
```

### Required Environment Variables
- None required for testing

## Success Criteria

The task is complete when:

1. [ ] NBA team aliases are defined in `team_aliases.py` with all 30 teams
2. [ ] The reported test cases now match correctly:
   - "NBA RS 2025 Indiana Pacers vs Boston Celtics 22 12" → matches "Indiana Pacers vs Boston Celtics" episode
   - "NBA RS 2025 Utah Jazz vs Denver Nuggets 22 12" → matches "Utah Jazz vs Denver Nuggets" episode
   - "NBA RS 2025 Orlando Magic vs Golden State Warriors 22 12" → matches "Orlando Magic vs Golden State Warriors" episode
3. [ ] Files with wrong away team no longer match (e.g., Pacers vs Celtics file doesn't match Celtics vs Heat episode)
4. [ ] Existing NHL and EPL tests still pass
5. [ ] No console errors
6. [ ] New unit tests cover the failure scenarios

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| test_nba_team_aliases_complete | `tests/test_matcher.py` | All 30 NBA teams have aliases defined |
| test_score_rejects_wrong_away_team | `tests/test_matcher.py` | Files with wrong away team return score 0.0 |
| test_nba_trailing_date_parsing | `tests/test_structured_matcher.py` | "22 12" parses as December 22 |
| test_nba_both_teams_required | `tests/test_matcher.py` | Score requires both teams to match |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| test_match_nba_file_to_episode | main | Full matching flow works for NBA files |
| test_nba_repeat_matchups_disambiguate | main | Same teams on different dates match correctly |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| NBA File Match | 1. Parse "NBA RS 2025 Indiana Pacers vs Boston Celtics 22 12" 2. Match to show with multiple episodes | Matches episode with title "Indiana Pacers vs Boston Celtics" |
| Wrong Team Rejection | 1. Parse file with "Pacers vs Celtics" 2. Try match to episode "Celtics vs Heat" | Match rejected (score 0.0) |

### Database Verification (if applicable)
| Check | Query/Command | Expected |
|-------|---------------|----------|
| N/A | N/A | N/A |

### QA Sign-off Requirements
- [ ] All unit tests pass (`pytest tests/test_matcher.py tests/test_structured_matcher.py -v`)
- [ ] All existing tests pass (`pytest tests/ -v`)
- [ ] Reported NBA failure cases now match correctly
- [ ] No regressions in existing NHL/EPL functionality
- [ ] Code follows established patterns (team_aliases structure)
- [ ] No security vulnerabilities introduced
