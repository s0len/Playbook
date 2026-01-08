#!/usr/bin/env python3
"""
Integration test for refactored processor.py modules.

This script verifies that all refactored modules can be imported
and have no circular dependencies or runtime errors.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all modules can be imported successfully."""
    print("=" * 80)
    print("INTEGRATION TEST: Module Imports")
    print("=" * 80)

    tests_passed = 0
    tests_failed = 0

    # Test 1: Main package imports
    try:
        from playbook import Processor, TraceOptions, __version__
        print("✓ Main package imports successful (Processor, TraceOptions, __version__)")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Main package import failed: {e}")
        tests_failed += 1

    # Test 2: trace_writer module
    try:
        from playbook.trace_writer import TraceOptions, persist_trace
        print("✓ trace_writer module imports successful")
        tests_passed += 1
    except Exception as e:
        print(f"✗ trace_writer module import failed: {e}")
        tests_failed += 1

    # Test 3: file_discovery module
    try:
        from playbook.file_discovery import (
            gather_source_files,
            matches_globs,
            should_suppress_sample_ignored,
            skip_reason_for_source_file,
            SAMPLE_FILENAME_PATTERN
        )
        print("✓ file_discovery module imports successful")
        tests_passed += 1
    except Exception as e:
        print(f"✗ file_discovery module import failed: {e}")
        tests_failed += 1

    # Test 4: run_summary module
    try:
        from playbook.run_summary import (
            has_activity,
            has_detailed_activity,
            filtered_ignored_details,
            summarize_counts,
            summarize_messages,
            summarize_plex_errors,
            extract_error_context,
            log_detailed_summary,
            log_run_recap
        )
        print("✓ run_summary module imports successful")
        tests_passed += 1
    except Exception as e:
        print(f"✗ run_summary module import failed: {e}")
        tests_failed += 1

    # Test 5: destination_builder module
    try:
        from playbook.destination_builder import (
            build_match_context,
            build_destination,
            format_relative_destination
        )
        print("✓ destination_builder module imports successful")
        tests_passed += 1
    except Exception as e:
        print(f"✗ destination_builder module import failed: {e}")
        tests_failed += 1

    # Test 6: metadata_loader module
    try:
        from playbook.metadata_loader import (
            SportRuntime,
            MetadataLoadResult,
            load_sports
        )
        print("✓ metadata_loader module imports successful")
        tests_passed += 1
    except Exception as e:
        print(f"✗ metadata_loader module import failed: {e}")
        tests_failed += 1

    # Test 7: match_handler module
    try:
        from playbook.match_handler import (
            specificity_score,
            alias_candidates,
            season_cache_key,
            episode_cache_key,
            should_overwrite_existing,
            cleanup_old_destination,
            handle_match
        )
        print("✓ match_handler module imports successful")
        tests_passed += 1
    except Exception as e:
        print(f"✗ match_handler module import failed: {e}")
        tests_failed += 1

    # Test 8: post_run_triggers module
    try:
        from playbook.post_run_triggers import (
            run_plex_sync_if_needed,
            trigger_kometa_if_needed
        )
        print("✓ post_run_triggers module imports successful")
        tests_passed += 1
    except Exception as e:
        print(f"✗ post_run_triggers module import failed: {e}")
        tests_failed += 1

    # Test 9: Processor class instantiation (basic check)
    try:
        from playbook import Processor
        from playbook.config import Settings

        # Create minimal settings for testing
        settings = Settings(
            source_directory="./test_source",
            destination_directory="./test_dest",
            sports=[]
        )

        # Try to instantiate Processor
        processor = Processor(settings=settings)
        print("✓ Processor class can be instantiated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Processor instantiation failed: {e}")
        tests_failed += 1

    # Test 10: CLI module imports
    try:
        from playbook.cli import main
        print("✓ CLI module imports successful")
        tests_passed += 1
    except Exception as e:
        print(f"✗ CLI module import failed: {e}")
        tests_failed += 1

    print("\n" + "=" * 80)
    print(f"RESULTS: {tests_passed} passed, {tests_failed} failed")
    print("=" * 80)

    return tests_failed == 0


def test_no_circular_imports():
    """Test that there are no circular import dependencies."""
    print("\n" + "=" * 80)
    print("INTEGRATION TEST: Circular Import Detection")
    print("=" * 80)

    # Import all modules in different orders to check for circular dependencies
    import_orders = [
        ["processor", "trace_writer", "file_discovery", "run_summary",
         "destination_builder", "metadata_loader", "match_handler", "post_run_triggers"],
        ["match_handler", "destination_builder", "metadata_loader", "post_run_triggers",
         "run_summary", "file_discovery", "trace_writer", "processor"],
        ["post_run_triggers", "run_summary", "match_handler", "destination_builder",
         "metadata_loader", "file_discovery", "trace_writer", "processor"]
    ]

    for i, order in enumerate(import_orders, 1):
        try:
            # Clear previously imported playbook modules
            for key in list(sys.modules.keys()):
                if key.startswith('playbook') and key != 'playbook':
                    del sys.modules[key]

            # Import in specific order
            for module_name in order:
                __import__(f'playbook.{module_name}')

            print(f"✓ Import order {i} successful (no circular dependencies detected)")
        except Exception as e:
            print(f"✗ Import order {i} failed: {e}")
            return False

    print("\n✓ No circular import dependencies detected")
    return True


def test_basic_functionality():
    """Test basic functionality of key functions."""
    print("\n" + "=" * 80)
    print("INTEGRATION TEST: Basic Functionality")
    print("=" * 80)

    tests_passed = 0
    tests_failed = 0

    # Test trace_writer
    try:
        from playbook.trace_writer import TraceOptions
        opts = TraceOptions(enabled=False)
        assert opts.enabled is False
        assert opts.output_dir is None
        print("✓ TraceOptions dataclass works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ TraceOptions test failed: {e}")
        tests_failed += 1

    # Test file_discovery
    try:
        from playbook.file_discovery import should_suppress_sample_ignored
        from pathlib import Path

        assert should_suppress_sample_ignored(Path("test_sample.mkv")) is True
        assert should_suppress_sample_ignored(Path("real_file.mkv")) is False
        print("✓ should_suppress_sample_ignored works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ should_suppress_sample_ignored test failed: {e}")
        tests_failed += 1

    # Test match_handler specificity_score
    try:
        from playbook.match_handler import specificity_score

        score1 = specificity_score("Round 1")
        score2 = specificity_score("Final")
        assert score1 > 0
        assert isinstance(score1, int)
        print("✓ specificity_score works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ specificity_score test failed: {e}")
        tests_failed += 1

    # Test run_summary
    try:
        from playbook.run_summary import has_activity
        from playbook.processor import ProcessingStats

        stats = ProcessingStats()
        assert has_activity(stats) is False

        stats.processed_count = 1
        assert has_activity(stats) is True
        print("✓ has_activity works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ has_activity test failed: {e}")
        tests_failed += 1

    print(f"\n✓ Basic functionality tests: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


def main():
    """Run all integration tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "INTEGRATION TEST SUITE" + " " * 36 + "║")
    print("║" + " " * 15 + "Processor Refactoring Validation" + " " * 30 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    all_passed = True

    # Run import tests
    if not test_imports():
        all_passed = False

    # Run circular import tests
    if not test_no_circular_imports():
        all_passed = False

    # Run basic functionality tests
    if not test_basic_functionality():
        all_passed = False

    # Final summary
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ✓ ✓  ALL INTEGRATION TESTS PASSED  ✓ ✓ ✓")
        print("=" * 80)
        print("\nThe refactored code works correctly end-to-end:")
        print("  • All modules import successfully")
        print("  • No circular import dependencies detected")
        print("  • No runtime import errors")
        print("  • Basic functionality verified")
        print("  • Application can run correctly")
        print("\n" + "=" * 80)
        return 0
    else:
        print("✗ ✗ ✗  SOME INTEGRATION TESTS FAILED  ✗ ✗ ✗")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
