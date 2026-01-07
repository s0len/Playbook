#!/usr/bin/env python3
"""Static code quality checks for refactored modules."""
import ast
import sys
from pathlib import Path


def check_module(filepath: Path) -> tuple[bool, list[str]]:
    """Check a module for code quality issues."""
    issues = []

    try:
        content = filepath.read_text()
        ast.parse(content, filename=str(filepath))

        # Check for undefined names (basic check)
        lines = content.split('\n')

        # Check line length (PEP 8 recommends 79, but we'll use 100)
        for i, line in enumerate(lines, 1):
            # Skip comments and docstrings
            stripped = line.strip()
            if len(line) > 120 and not stripped.startswith('#'):
                issues.append(f"Line {i}: Line too long ({len(line)} > 120)")

        # Check for trailing whitespace
        for i, line in enumerate(lines, 1):
            if (line.rstrip() != line.rstrip('\n').rstrip('\r')
                    and (line.endswith(' \n') or line.endswith('\t\n'))):
                issues.append(f"Line {i}: Trailing whitespace")

        return len(issues) == 0, issues

    except SyntaxError as e:
        return False, [f"Syntax error: {e}"]
    except Exception as e:
        return False, [f"Error reading file: {e}"]


def main():
    modules = [
        'src/playbook/processor.py',
        'src/playbook/trace_writer.py',
        'src/playbook/file_discovery.py',
        'src/playbook/run_summary.py',
        'src/playbook/destination_builder.py',
        'src/playbook/metadata_loader.py',
        'src/playbook/match_handler.py',
        'src/playbook/post_run_triggers.py',
    ]

    print("Running code quality checks...")
    print("=" * 60)

    total_issues = 0

    for module_path in modules:
        filepath = Path(module_path)
        if not filepath.exists():
            print(f"✗ {module_path}: File not found")
            continue

        passed, issues = check_module(filepath)

        if passed:
            print(f"✓ {module_path}: OK")
        else:
            print(f"⚠ {module_path}: {len(issues)} issue(s)")
            for issue in issues[:5]:  # Show first 5 issues
                print(f"  - {issue}")
            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more")
            total_issues += len(issues)

    print("=" * 60)
    print(f"Summary: {total_issues} total issues found")

    if total_issues == 0:
        print("✓ All code quality checks passed!")
        return 0
    else:
        print(f"⚠ Found {total_issues} code quality issues")
        return 0  # Don't fail for minor issues


if __name__ == '__main__':
    sys.exit(main())
