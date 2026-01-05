#!/usr/bin/env python3
"""QA validation script to test imports and basic functionality."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("QA VALIDATION: Testing Critical Imports")
print("=" * 60)

# Test 1: Import structured_filename functions
print("\n[Test 1] Importing from structured_filename...")
try:
    from playbook.parsers.structured_filename import (
        parse_structured_filename,
        build_canonical_filename,
        StructuredName
    )
    print("✓ PASS: All functions imported successfully")
    print(f"  - parse_structured_filename: {parse_structured_filename}")
    print(f"  - build_canonical_filename: {build_canonical_filename}")
    print(f"  - StructuredName: {StructuredName}")
except ImportError as e:
    print(f"✗ FAIL: Import error - {e}")
    sys.exit(1)

# Test 2: Import matcher
print("\n[Test 2] Importing matcher module...")
try:
    from playbook import matcher
    print("✓ PASS: matcher module imported successfully")
    print(f"  - matcher.match_file_to_episode exists: {hasattr(matcher, 'match_file_to_episode')}")
except ImportError as e:
    print(f"✗ FAIL: Import error - {e}")
    sys.exit(1)

# Test 3: Check pattern templates loading
print("\n[Test 3] Loading pattern templates...")
try:
    from playbook.pattern_templates import load_builtin_pattern_sets
    pattern_sets = load_builtin_pattern_sets()
    print(f"✓ PASS: Loaded {len(pattern_sets)} pattern sets")
    print(f"  - NHL pattern set exists: {'nhl' in pattern_sets}")
    if 'nhl' in pattern_sets:
        print(f"  - NHL has {len(pattern_sets['nhl'])} patterns")
except Exception as e:
    print(f"✗ FAIL: Pattern loading error - {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
