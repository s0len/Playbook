#!/usr/bin/env python3
"""QA validation script for YAML syntax and NHL pattern set."""
import sys

import yaml

try:
    with open('./src/playbook/pattern_templates.yaml') as f:
        data = yaml.safe_load(f)

    print("✅ YAML syntax valid")

    pattern_sets = data.get('pattern_sets', {})
    nhl_exists = 'nhl' in pattern_sets

    print(f"✅ NHL in pattern_sets: {nhl_exists}")

    if nhl_exists:
        nhl_patterns = pattern_sets['nhl']
        print(f"✅ NHL has {len(nhl_patterns)} patterns defined")
    else:
        print("❌ NHL pattern set NOT FOUND")
        sys.exit(1)

    print("\n✅ All YAML validation checks passed")
    sys.exit(0)

except Exception as e:
    print(f"❌ YAML validation failed: {e}")
    sys.exit(1)
