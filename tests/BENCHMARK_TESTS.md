# Benchmark Tests for SessionLookupIndex

## Overview

The benchmark tests measure the performance improvement from using `SessionLookupIndex` with large session_lookup dictionaries (200+ entries). These tests demonstrate the candidate reduction achieved by the optimization.

## Running Benchmark Tests

The benchmark tests are marked with `@pytest.mark.benchmark` and are **skipped in normal test runs** by default.

### Run ALL benchmark tests explicitly:

```bash
pytest -m benchmark tests/test_session_index.py -v -s
```

### Run a specific benchmark test:

```bash
pytest tests/test_session_index.py::TestSessionLookupIndexBenchmark::test_candidate_reduction_with_200_entries -v -s
```

### Run normal tests (excludes benchmarks):

```bash
pytest tests/test_session_index.py
```

Or with explicit exclusion:

```bash
pytest -m "not benchmark" tests/test_session_index.py
```

## Benchmark Test Suite

### 1. `test_candidate_reduction_with_200_entries`

**Purpose:** Demonstrates candidate reduction with realistic sports show data (216 entries simulating F1 season).

**What it measures:**
- Total entries in index: 216 (24 race weekends × 9 sessions)
- Candidate reduction ratio
- Comparison to theoretical O(n/78) reduction

**Expected results:**
- Candidates should be < 50% of total entries
- Demonstrates significant reduction in iteration count

### 2. `test_worst_case_candidate_reduction`

**Purpose:** Tests pathological case where many entries share first character and similar lengths.

**What it measures:**
- Worst-case scenario with 250 entries all starting with 'r'
- Length filtering effectiveness when first-char filtering is minimal

**Expected results:**
- Even in worst case, length filtering provides benefit
- All returned candidates respect ±1 length constraint

### 3. `test_iteration_count_comparison`

**Purpose:** Direct comparison of naive O(n) vs optimized O(n/k) iteration counts.

**What it measures:**
- Iteration count for multiple search scenarios
- Per-token speedup
- Overall reduction percentage

**Expected results:**
- At least 80% reduction in total iterations
- Significant speedup (typically 5-50x depending on data distribution)

## Output Format

When run with `-s` flag, the benchmark tests print detailed metrics:

```
============================================================
BENCHMARK RESULTS:
============================================================
Total entries in index: 216
Search token: 'race15qualifying' (length 16)
First character: 'r'
Candidates after filtering: 24
Reduction ratio: 11.11%
Candidates checked: 24/216
Expected theoretical reduction: ~1.28% (1/78)
============================================================
```

## Configuration

To configure pytest to always skip benchmark tests unless explicitly requested, add to `pytest.ini` or `pyproject.toml`:

```ini
[tool.pytest.ini_options]
markers = [
    "benchmark: marks tests as benchmark tests (deselect with '-m \"not benchmark\"')"
]
```

## Performance Expectations

Based on the optimization strategy:

- **Theoretical reduction:** ~1.28% (1/78) where 78 = 26 first-chars × 3 length buckets
- **Actual reduction:** Varies by data distribution, typically 5-20% in practice
- **Worst case:** Still provides length filtering benefit even when first-char distribution is poor
- **Best case:** 1-2% when entries are evenly distributed across first characters

## Notes

- These tests use `print()` statements for output visibility
- Use `-s` or `--capture=no` flag to see benchmark output
- Tests include assertions to verify optimization effectiveness
- All tests create realistic data patterns based on actual use cases (sports shows, F1 seasons)
