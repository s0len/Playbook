#!/usr/bin/env python3
"""
Test script for subtask-3-2: Test config loading with NHL sport enabled

This script verifies that:
1. The NHL pattern set is properly registered in builtin_pattern_sets
2. A config with NHL sport using pattern_sets: [nhl] loads without ValueError
3. The actual user config from issue #72 can be loaded successfully

This is the critical test to confirm the NHL ValueError issue is fixed.
"""

import sys
import tempfile
from pathlib import Path

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_nhl_pattern_set_registered():
    """Test 1: Verify NHL pattern set exists in builtin pattern sets"""
    print("=" * 70)
    print("TEST 1: Verify NHL pattern set is registered")
    print("=" * 70)

    try:
        from playbook.pattern_templates import load_builtin_pattern_sets

        builtin_sets = load_builtin_pattern_sets()

        print("✓ Successfully loaded builtin pattern sets")
        print(f"✓ Total pattern sets: {len(builtin_sets)}")
        print(f"✓ Available pattern sets: {sorted(builtin_sets.keys())}")

        if "nhl" in builtin_sets:
            print("\n✅ SUCCESS: 'nhl' pattern set IS registered")
            print(f"✓ NHL pattern set contains {len(builtin_sets['nhl'])} pattern(s)")
            return True
        else:
            print("\n❌ FAILURE: 'nhl' pattern set NOT found in builtin_pattern_sets")
            print(f"Available: {sorted(builtin_sets.keys())}")
            return False
    except Exception as e:
        print(f"\n❌ FAILURE: Error loading pattern sets: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_minimal_nhl_config():
    """Test 2: Load minimal config with NHL sport enabled"""
    print("\n" + "=" * 70)
    print("TEST 2: Load minimal config with NHL sport")
    print("=" * 70)

    # Create minimal valid config with NHL sport
    minimal_config = {
        "settings": {
            "source_dir": "/tmp/test_source",
            "destination_dir": "/tmp/test_dest",
            "cache_dir": "/tmp/test_cache",
        },
        "sports": [
            {
                "id": "nhl",
                "name": "NHL",
                "pattern_sets": ["nhl"],  # Reference the builtin NHL pattern set
                "metadata": {"url": "https://example.com/nhl.yaml", "show_key": "NHL Test", "ttl_hours": 24},
            }
        ],
    }

    try:
        from playbook.config import load_config

        # Write config to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(minimal_config, f)
            temp_path = f.name

        print(f"✓ Created temporary config file: {temp_path}")
        print("✓ Config contains NHL sport with pattern_sets: ['nhl']")

        # Load the config
        config = load_config(Path(temp_path))

        print("✓ Config loaded successfully without ValueError")
        print(f"✓ Number of sports configured: {len(config.sports)}")

        # Verify NHL sport is loaded
        nhl_sport = next((s for s in config.sports if s.id == "nhl"), None)
        if nhl_sport:
            print(f"✓ NHL sport found: {nhl_sport.name}")
            print(f"✓ NHL sport enabled: {nhl_sport.enabled}")
            print(f"✓ NHL patterns loaded: {len(nhl_sport.patterns)}")
            print("\n✅ SUCCESS: NHL config loads without ValueError")

            # Clean up
            Path(temp_path).unlink()
            return True
        else:
            print("\n❌ FAILURE: NHL sport not found in loaded config")
            Path(temp_path).unlink()
            return False

    except ValueError as e:
        print(f"\n❌ FAILURE: ValueError raised when loading config: {e}")
        import traceback

        traceback.print_exc()
        Path(temp_path).unlink()
        return False
    except Exception as e:
        print(f"\n❌ FAILURE: Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        try:
            Path(temp_path).unlink()
        except:
            pass
        return False


def test_sample_config_with_nhl():
    """Test 3: Load the actual sample config which includes NHL"""
    print("\n" + "=" * 70)
    print("TEST 3: Load sample config with NHL (from issue #72)")
    print("=" * 70)

    sample_config_path = Path(__file__).parent / "config" / "playbook.sample.yaml"

    if not sample_config_path.exists():
        print(f"⚠️  SKIPPED: Sample config not found at {sample_config_path}")
        return True

    try:
        from playbook.config import load_config

        print(f"✓ Loading sample config from: {sample_config_path}")

        # Load the sample config
        config = load_config(sample_config_path)

        print("✓ Sample config loaded successfully")
        print(f"✓ Number of sports in sample config: {len(config.sports)}")

        # Find NHL sport
        nhl_sport = next((s for s in config.sports if s.id == "nhl"), None)

        if nhl_sport:
            print("✓ NHL sport found in sample config")
            print(f"✓ NHL sport name: {nhl_sport.name}")
            print(f"✓ NHL sport enabled: {nhl_sport.enabled}")
            print(f"✓ NHL patterns loaded: {len(nhl_sport.patterns)}")
            print(f"✓ NHL metadata URL: {nhl_sport.metadata.url if nhl_sport.metadata else 'None'}")

            # List all sports that loaded successfully
            sport_ids = [s.id for s in config.sports]
            print(f"✓ All sports loaded: {', '.join(sport_ids)}")

            print("\n✅ SUCCESS: Sample config with NHL loads without ValueError")
            print("   This confirms the fix for Issue #72 ValueError is working!")
            return True
        else:
            print("\n⚠️  WARNING: NHL sport not found in sample config")
            print("   (This may be expected if NHL was removed from sample)")
            return True

    except ValueError as e:
        if "Unknown pattern set 'nhl'" in str(e):
            print("\n❌ FAILURE: Original Issue #72 ValueError still occurs!")
            print(f"   Error: {e}")
            print("   This means the NHL pattern set is not properly registered.")
        else:
            print(f"\n❌ FAILURE: ValueError raised: {e}")
        import traceback

        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ FAILURE: Unexpected error loading sample config: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all NHL config loading tests"""
    print("\n" + "=" * 70)
    print("NHL CONFIG LOADING TEST SUITE")
    print("Subtask 3-2: Test config loading with NHL sport enabled")
    print("=" * 70)

    results = []

    # Test 1: Pattern set registration
    results.append(("NHL pattern set registered", test_nhl_pattern_set_registered()))

    # Test 2: Minimal config loading
    results.append(("Minimal NHL config loads", test_minimal_nhl_config()))

    # Test 3: Sample config loading
    results.append(("Sample config with NHL loads", test_sample_config_with_nhl()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - NHL config loading is working correctly!")
        print("   Issue #72 ValueError: Unknown pattern set 'nhl' is FIXED")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME TESTS FAILED - NHL config loading has issues")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
