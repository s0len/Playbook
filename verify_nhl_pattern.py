#!/usr/bin/env python3
"""
Static verification that NHL pattern set exists in pattern_templates.yaml
This doesn't require any dependencies - just reads the file directly.
"""

import re
from pathlib import Path

# Read the YAML file
yaml_path = Path("src/playbook/pattern_templates.yaml")
content = yaml_path.read_text()

# Check if NHL pattern set is defined
nhl_pattern_match = re.search(r'^\s+nhl:\s*&nhl_patterns', content, re.MULTILINE)

if nhl_pattern_match:
    print("✓ NHL pattern set found in YAML at line", content[:nhl_pattern_match.start()].count('\n') + 1)

    # Count total pattern sets
    pattern_sets_match = re.search(r'^pattern_sets:', content, re.MULTILINE)
    if pattern_sets_match:
        # Find all top-level pattern set keys (2-space indent after pattern_sets:)
        pattern_set_keys = re.findall(r'^\s{2}(\w+):\s*(?:&\w+)?', content[pattern_sets_match.end():], re.MULTILINE)
        print(f"✓ Total pattern sets found: {len(pattern_set_keys)}")
        print(f"✓ Pattern sets: {', '.join(pattern_set_keys[:10])}")

        if 'nhl' in pattern_set_keys:
            print("\n✓ VERIFICATION PASSED: 'nhl' is in pattern_sets")
            print(f"True {len(pattern_set_keys)}")
        else:
            print("\n✗ VERIFICATION FAILED: 'nhl' not found in pattern set keys")
            print(f"False {len(pattern_set_keys)}")
    else:
        print("✗ pattern_sets section not found")
else:
    print("✗ NHL pattern set not found in YAML")
