#!/usr/bin/env python3
"""Validate imports for all refactored modules."""
import sys
sys.path.insert(0, 'src')

modules_to_check = [
    'playbook.processor',
    'playbook.trace_writer',
    'playbook.file_discovery',
    'playbook.run_summary',
    'playbook.destination_builder',
    'playbook.metadata_loader',
    'playbook.match_handler',
    'playbook.post_run_triggers',
]

print("Validating module imports...")
print("=" * 60)

all_ok = True
for module_name in modules_to_check:
    try:
        __import__(module_name)
        print(f"✓ {module_name}: OK")
    except Exception as e:
        print(f"✗ {module_name}: FAILED - {e}")
        all_ok = False

print("=" * 60)
if all_ok:
    print("✓ All modules imported successfully!")
    sys.exit(0)
else:
    print("✗ Some modules failed to import")
    sys.exit(1)
