#!/usr/bin/env python3
"""Debug import statement in matcher.py."""
import ast

with open('./src/playbook/matcher.py', 'r') as f:
    tree = ast.parse(f.read(), filename='matcher.py')

print("All ImportFrom statements in matcher.py:")
print("=" * 60)
for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom):
        module = node.module or "(relative import)"
        names = [alias.name for alias in node.names]
        print(f"from {module} import {', '.join(names)}")
        if 'structured_filename' in str(module):
            print(f"  ^^^^ FOUND structured_filename import!")
            print(f"  Module path: '{module}'")
            print(f"  Imported names: {names}")
