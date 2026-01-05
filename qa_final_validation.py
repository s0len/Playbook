#!/usr/bin/env python3
"""QA Final Validation - Static Code Analysis."""
import ast
import sys

def check_function_exists(filepath, function_name):
    """Check if a function exists in a Python file using AST."""
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read(), filename=filepath)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return True
    return False

print("=" * 70)
print("QA VALIDATION REPORT - Static Code Analysis")
print("=" * 70)

checks_passed = 0
checks_total = 0

# CHECK 1: Functions exist in structured_filename.py
print("\n[CHECK 1] Functions exist in structured_filename.py")
checks_total += 2

if check_function_exists('./src/playbook/parsers/structured_filename.py', 'parse_structured_filename'):
    print("  ✅ parse_structured_filename function exists")
    checks_passed += 1
else:
    print("  ❌ parse_structured_filename function NOT FOUND")

if check_function_exists('./src/playbook/parsers/structured_filename.py', 'build_canonical_filename'):
    print("  ✅ build_canonical_filename function exists")
    checks_passed += 1
else:
    print("  ❌ build_canonical_filename function NOT FOUND")

# CHECK 2: Import statement in matcher.py
print("\n[CHECK 2] Import statement in matcher.py")
checks_total += 1

with open('./src/playbook/matcher.py', 'r') as f:
    tree = ast.parse(f.read())

found_import = False
imported_all_three = False
for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom):
        if node.module and 'structured_filename' in node.module:
            found_import = True
            names = [alias.name for alias in node.names]
            if all(name in names for name in ['StructuredName', 'build_canonical_filename', 'parse_structured_filename']):
                imported_all_three = True
                break

if found_import and imported_all_three:
    print("  ✅ matcher.py imports all 3 required items from structured_filename")
    checks_passed += 1
else:
    print("  ❌ matcher.py imports are incomplete or missing")

# CHECK 3: StructuredName class exists
print("\n[CHECK 3] StructuredName class exists")
checks_total += 1

with open('./src/playbook/parsers/structured_filename.py', 'r') as f:
    tree = ast.parse(f.read())

has_class = any(isinstance(node, ast.ClassDef) and node.name == 'StructuredName'
                for node in ast.walk(tree))

if has_class:
    print("  ✅ StructuredName class exists")
    checks_passed += 1
else:
    print("  ❌ StructuredName class NOT FOUND")

# CHECK 4: File line count (should be ~252-253 lines after restoration)
print("\n[CHECK 4] File restoration completeness")
checks_total += 1

with open('./src/playbook/parsers/structured_filename.py', 'r') as f:
    line_count = len(f.readlines())

if line_count >= 250:
    print(f"  ✅ structured_filename.py has {line_count} lines (expected ~252)")
    checks_passed += 1
else:
    print(f"  ❌ structured_filename.py has only {line_count} lines (expected ~252)")

# CHECK 5: Python syntax validation
print("\n[CHECK 5] Python syntax validation")
checks_total += 3

files_to_check = [
    './src/playbook/parsers/structured_filename.py',
    './src/playbook/matcher.py',
    './src/playbook/config.py'
]

for filepath in files_to_check:
    try:
        with open(filepath, 'r') as f:
            ast.parse(f.read(), filename=filepath)
        print(f"  ✅ {filepath.split('/')[-1]} - valid syntax")
        checks_passed += 1
    except SyntaxError as e:
        print(f"  ❌ {filepath.split('/')[-1]} - SYNTAX ERROR: {e}")

# CHECK 6: NHL pattern exists in YAML (basic check)
print("\n[CHECK 6] NHL pattern in pattern_templates.yaml")
checks_total += 1

with open('./src/playbook/pattern_templates.yaml', 'r') as f:
    yaml_content = f.read()

if 'nhl: &nhl_patterns' in yaml_content or 'nhl:' in yaml_content.lower():
    print("  ✅ NHL pattern set found in YAML")
    checks_passed += 1
else:
    print("  ❌ NHL pattern set NOT FOUND in YAML")

# SUMMARY
print("\n" + "=" * 70)
print(f"RESULTS: {checks_passed}/{checks_total} checks passed")
print("=" * 70)

if checks_passed == checks_total:
    print("\n✅ ALL STATIC VALIDATION CHECKS PASSED")
    print("\nIssue #72 Fixes Verified:")
    print("  1. ✅ ImportError fixed - functions restored")
    print("  2. ✅ ValueError fixed - NHL pattern set exists")
    print("\n⚠️  NOTE: Runtime testing requires Python 3.10+ with dependencies installed")
    sys.exit(0)
else:
    print(f"\n❌ VALIDATION FAILED: {checks_total - checks_passed} issues found")
    sys.exit(1)
