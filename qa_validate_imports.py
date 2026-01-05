#!/usr/bin/env python3
"""QA validation script for import chain."""
import sys
import ast

def check_function_exists(filepath, function_name):
    """Check if a function exists in a Python file using AST."""
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read(), filename=filepath)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return True
    return False

def check_import_statement(filepath, module_path, names):
    """Check if specific names are imported from a module."""
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read(), filename=filepath)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == module_path:
                imported_names = [alias.name for alias in node.names]
                return all(name in imported_names for name in names)
    return False

print("QA VALIDATION: Import Chain Verification")
print("=" * 60)

# Check functions exist in structured_filename.py
checks = []

print("\n1. Checking structured_filename.py functions...")
if check_function_exists('./src/playbook/parsers/structured_filename.py', 'parse_structured_filename'):
    print("   ✅ parse_structured_filename function exists")
    checks.append(True)
else:
    print("   ❌ parse_structured_filename function NOT FOUND")
    checks.append(False)

if check_function_exists('./src/playbook/parsers/structured_filename.py', 'build_canonical_filename'):
    print("   ✅ build_canonical_filename function exists")
    checks.append(True)
else:
    print("   ❌ build_canonical_filename function NOT FOUND")
    checks.append(False)

# Check imports in matcher.py
print("\n2. Checking matcher.py imports...")
if check_import_statement('./src/playbook/matcher.py', '.parsers.structured_filename',
                         ['StructuredName', 'build_canonical_filename', 'parse_structured_filename']):
    print("   ✅ matcher.py imports all required functions from structured_filename")
    checks.append(True)
else:
    print("   ❌ matcher.py imports are INCORRECT")
    checks.append(False)

# Check StructuredName class exists
print("\n3. Checking StructuredName class...")
with open('./src/playbook/parsers/structured_filename.py', 'r') as f:
    tree = ast.parse(f.read())

has_structured_name = False
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == 'StructuredName':
        has_structured_name = True
        break

if has_structured_name:
    print("   ✅ StructuredName class exists")
    checks.append(True)
else:
    print("   ❌ StructuredName class NOT FOUND")
    checks.append(False)

# Summary
print("\n" + "=" * 60)
if all(checks):
    print("✅ ALL IMPORT CHAIN CHECKS PASSED")
    sys.exit(0)
else:
    print(f"❌ FAILED: {checks.count(False)}/{len(checks)} checks failed")
    sys.exit(1)
