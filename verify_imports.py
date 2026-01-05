#!/usr/bin/env python3
"""
Verify that all imports in matcher.py resolve correctly.

This script performs static analysis to verify imports without executing code.
"""
import ast
import sys
from pathlib import Path

def check_import_exists(module_file: Path, names: list) -> bool:
    """Check if names exist in the given module file."""
    try:
        with open(module_file, 'r') as f:
            tree = ast.parse(f.read(), filename=str(module_file))

        # Extract all top-level function and class definitions
        definitions = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                definitions.add(node.name)

        # Check if all requested names exist
        for name in names:
            if name not in definitions:
                print(f"  ✗ {name} NOT FOUND in {module_file}")
                return False
            print(f"  ✓ {name} found in {module_file}")
        return True
    except Exception as e:
        print(f"  ✗ Error parsing {module_file}: {e}")
        return False

def verify_matcher_imports():
    """Verify all imports in matcher.py are correct."""
    src_dir = Path(__file__).parent / 'src' / 'playbook'

    print("Verifying matcher.py imports...\n")

    all_good = True

    # Check config.py imports
    print("1. Checking imports from config.py:")
    config_file = src_dir / 'config.py'
    if not check_import_exists(config_file, ['PatternConfig', 'SeasonSelector', 'SportConfig']):
        all_good = False
    print()

    # Check structured_filename.py imports
    print("2. Checking imports from parsers/structured_filename.py:")
    structured_file = src_dir / 'parsers' / 'structured_filename.py'
    if not check_import_exists(structured_file, ['StructuredName', 'build_canonical_filename', 'parse_structured_filename']):
        all_good = False
    print()

    # Check models.py imports
    print("3. Checking imports from models.py:")
    models_file = src_dir / 'models.py'
    if not check_import_exists(models_file, ['Episode', 'Season', 'Show']):
        all_good = False
    print()

    # Check team_aliases.py imports
    print("4. Checking imports from team_aliases.py:")
    team_aliases_file = src_dir / 'team_aliases.py'
    if not check_import_exists(team_aliases_file, ['get_team_alias_map']):
        all_good = False
    print()

    # Check utils.py imports
    print("5. Checking imports from utils.py:")
    utils_file = src_dir / 'utils.py'
    if not check_import_exists(utils_file, ['normalize_token']):
        all_good = False
    print()

    # Check matcher.py exports match_file_to_episode
    print("6. Checking matcher.py exports match_file_to_episode:")
    matcher_file = src_dir / 'matcher.py'
    if not check_import_exists(matcher_file, ['match_file_to_episode']):
        all_good = False
    print()

    # Check syntax of matcher.py
    print("7. Checking matcher.py syntax:")
    try:
        with open(matcher_file, 'r') as f:
            ast.parse(f.read(), filename=str(matcher_file))
        print("  ✓ matcher.py syntax is valid")
    except SyntaxError as e:
        print(f"  ✗ Syntax error in matcher.py: {e}")
        all_good = False
    print()

    if all_good:
        print("=" * 60)
        print("✓ ALL IMPORTS VERIFIED SUCCESSFULLY")
        print("=" * 60)
        print("\nNote: This verification confirms that all imports are")
        print("structurally correct. Runtime verification requires")
        print("Python 3.10+ due to dataclass slots=True feature.")
        print("The project is designed to run on Python 3.12 (see Dockerfile).")
        return 0
    else:
        print("=" * 60)
        print("✗ IMPORT VERIFICATION FAILED")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(verify_matcher_imports())
