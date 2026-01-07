#!/usr/bin/env python3
"""Verify syntax of modified source files."""

import py_compile
from pathlib import Path

def main():
    # Modified files from this task
    modified_files = [
        "./src/playbook/match_handler.py",
        "./src/playbook/matcher.py",
        "./src/playbook/metadata.py",
        "./src/playbook/notifications/types.py",
        "./src/playbook/plex_client.py",
        "./src/playbook/plex_metadata_sync.py",
        "./src/playbook/trace_writer.py",
    ]

    print("Verifying syntax of modified source files...\n")

    passed = 0
    failed = 0

    for file_path in modified_files:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠ {path.name} - FILE NOT FOUND")
            continue

        try:
            py_compile.compile(str(path), doraise=True)
            print(f"✓ {path.name}")
            passed += 1
        except py_compile.PyCompileError as e:
            print(f"✗ {path.name} - SYNTAX ERROR")
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
