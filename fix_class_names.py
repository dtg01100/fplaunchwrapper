#!/usr/bin/env python3
"""
Fix class name mismatches between test expectations and actual module definitions.
"""

import re
from pathlib import Path


def fix_class_names():
    """Fix class name mismatches in test files"""

    # Mapping of expected names to actual names
    name_mapping = {
        "CleanupManager": "WrapperCleanup",
        "ApplicationLauncher": "AppLauncher",
        "ConfigManager": "EnhancedConfigManager",
        "FlatpakMonitor": "FlatpakMonitor",  # This one is correct
        "WrapperGenerator": "WrapperGenerator",  # This one is correct
        "WrapperManager": "WrapperManager",  # This one is correct
        "SystemdSetup": "SystemdSetup",  # This one is correct
    }

    test_files = [
        "test_cleanup.py",
        "test_launch.py",
        "test_config_manager.py",
        "test_edge_cases_comprehensive.py",
        "test_edge_cases_focused.py",
        "test_emit_functionality.py",
        "test_emit_safety.py",
        "test_emit_simple.py",
        "test_emit_verbose.py",
        "test_final_validation.py",
        "test_flatpak_monitor.py",
        "test_focused.py",
        "test_fplaunch_main.py",
        "test_integration_pytest.py",
        "test_management_functions_pytest.py",
        "test_migrated_shell_tests.py",
        "test_wrapper_generation_pytest.py",
        "test_wrapper_options_pytest.py",
    ]

    for filename in test_files:
        filepath = Path("tests/python") / filename
        if not filepath.exists():
            continue

        print(f"Processing {filename}...")

        with open(filepath, "r") as f:
            content = f.read()

        original_content = content

        # Fix imports first
        for expected, actual in name_mapping.items():
            if expected != actual:
                # Fix import statements
                content = re.sub(
                    rf"(\s+)from fplaunch\.\w+ import (.*){expected}(.*)",
                    rf"\1from fplaunch.\2 import {actual}\3",
                    content,
                )
                # Fix variable assignments
                content = re.sub(
                    rf"(\s+){expected} = None", rf"\1{actual} = None", content
                )
                # Fix class references in code
                content = re.sub(rf"(\W){expected}(\W)", rf"\1{actual}\2", content)

        if content != original_content:
            with open(filepath, "w") as f:
                f.write(content)
            print(f"  ✅ Updated {filename}")
        else:
            print(f"  No changes needed for {filename}")


if __name__ == "__main__":
    fix_class_names()
