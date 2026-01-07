#!/usr/bin/env python3
"""Verify syntax of all test files."""

import os
import py_compile
from pathlib import Path

def main():
    test_dir = Path("./tests")
    test_files = sorted(test_dir.glob("*.py"))

    print("Verifying syntax of test files...\n")

    passed = 0
    failed = 0

    for test_file in test_files:
        try:
            py_compile.compile(str(test_file), doraise=True)
            print(f"✓ {test_file.name}")
            passed += 1
        except py_compile.PyCompileError as e:
            print(f"✗ {test_file.name} - SYNTAX ERROR")
            print(f"  {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Total: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"{'='*50}")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit(main())
