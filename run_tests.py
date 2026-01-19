#!/usr/bin/env python3
"""
Simple test runner to execute multiple test files and report results
"""

import sys
import os
from pathlib import Path
import importlib.util
import traceback


def run_test_file(test_file_path):
    """Run all test methods in a test file"""
    print(f"\n🔍 Testing {test_file_path}...")

    try:
        spec = importlib.util.spec_from_file_location("test_module", test_file_path)
        if spec is None or spec.loader is None:
            print(f"❌ Could not load spec for {test_file_path}")
            return 0, 0
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)

        test_classes = []
        for name in dir(test_module):
            obj = getattr(test_module, name)
            if isinstance(obj, type) and name.startswith("Test"):
                test_classes.append((name, obj))

        if not test_classes:
            print(f"⚠️  No test classes found in {test_file_path}")
            return 0, 0

        total_tests = 0
        passed_tests = 0

        for class_name, test_class in test_classes:
            print(f"  📋 Running {class_name}...")

            test_methods = []
            for method_name in dir(test_class):
                if method_name.startswith("test_"):
                    method = getattr(test_class, method_name)
                    if callable(method):
                        test_methods.append((method_name, method))

            if not test_methods:
                print(f"    ⚠️  No test methods found in {class_name}")
                continue

            for method_name, method in test_methods:
                try:
                    # Create instance and run method
                    instance = test_class()
                    method(
                        instance
                    )  # Some tests might need parameters, but we'll handle exceptions
                    print(f"    ✅ {method_name}")
                    passed_tests += 1
                except TypeError as e:
                    if "positional arguments" in str(e):
                        # Method needs fixtures or parameters, skip for now
                        print(f"    ⚠️  {method_name} (needs parameters, skipped)")
                        continue
                    else:
                        raise
                except Exception as e:
                    print(f"    ❌ {method_name}: {e}")
                finally:
                    total_tests += 1

        return passed_tests, total_tests

    except Exception as e:
        print(f"❌ Failed to load {test_file_path}: {e}")
        traceback.print_exc()
        return 0, 0


def main():
    """Run tests on key test files"""
    test_files = [
        "tests/python/test_python_utils.py",
        "tests/python/test_edge_cases_focused.py",
        "tests/python/test_cleanup.py",
        "tests/python/test_config_manager.py",
    ]

    total_passed = 0
    total_tests = 0

    for test_file in test_files:
        if os.path.exists(test_file):
            passed, tests = run_test_file(test_file)
            total_passed += passed
            total_tests += tests
        else:
            print(f"⚠️  Test file not found: {test_file}")

    print("\n📊 Test Results Summary:")
    print(f"   ✅ Passed: {total_passed}")
    print(f"   ❌ Failed: {total_tests - total_passed}")
    print(
        f"   📈 Success Rate: {(total_passed / total_tests * 100):.1f}%"
        if total_tests > 0
        else "No tests run"
    )


if __name__ == "__main__":
    main()
