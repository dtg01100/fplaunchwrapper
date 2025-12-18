#!/usr/bin/env python3
"""
Batch fix script to update all test file imports from direct module imports
to proper fplaunch package imports.
"""

import os
import re
from pathlib import Path


def fix_test_imports():
    """Fix imports in all test files"""
    test_dir = Path("tests/python")
    fixed_files = []

    # Pattern to match direct module imports
    patterns = [
        (r"from (\w+)\s+import", r"from fplaunch.\1 import"),
        (r"import (\w+)", r"from fplaunch import \1"),
    ]

    # Files to process
    test_files = [
        "test_cleanup.py",
        "test_comprehensive.py",
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
        "test_launch.py",
        "test_management_functions_pytest.py",
        "test_migrated_shell_tests.py",
        "test_wrapper_generation_pytest.py",
        "test_wrapper_options_pytest.py",
    ]

    for filename in test_files:
        filepath = test_dir / filename
        if not filepath.exists():
            continue

        print(f"Processing {filename}...")

        with open(filepath, "r") as f:
            content = f.read()

        original_content = content

        # Remove sys.path.insert lines
        content = re.sub(
            r"# Add lib directory to path for imports\s*\n\s*sys\.path\.insert\(.*?\)\s*\n",
            "",
            content,
        )
        content = re.sub(r"sys\.path\.insert\(.*?\)\s*\n", "", content)

        # Fix imports - but be careful not to change standard library imports
        lines = content.split("\n")
        for i, line in enumerate(lines):
            # Skip if it's already a fplaunch import
            if "from fplaunch." in line or "import fplaunch" in line:
                continue

            # Skip standard library and third-party imports
            if any(
                line.startswith(f"from {lib}") or line.startswith(f"import {lib}")
                for lib in [
                    "os",
                    "sys",
                    "tempfile",
                    "subprocess",
                    "pytest",
                    "pathlib",
                    "unittest",
                    "json",
                    "shutil",
                    "time",
                ]
            ):
                continue

            # Fix direct module imports
            for pattern, replacement in patterns:
                if re.search(pattern, line) and not line.strip().startswith("#"):
                    # Only replace if it's importing from our modules
                    if any(
                        module in line
                        for module in [
                            "python_utils",
                            "cleanup",
                            "cli",
                            "config_manager",
                            "flatpak_monitor",
                            "fplaunch",
                            "generate",
                            "launch",
                            "manage",
                            "systemd_setup",
                        ]
                    ):
                        lines[i] = re.sub(pattern, replacement, line)
                        print(f"  Fixed: {line.strip()} -> {lines[i].strip()}")
                        break

        content = "\n".join(lines)

        if content != original_content:
            with open(filepath, "w") as f:
                f.write(content)
            fixed_files.append(filename)
            print(f"  ✅ Updated {filename}")
        else:
            print(f"  No changes needed for {filename}")

    print(f"\nFixed {len(fixed_files)} files:")
    for f in fixed_files:
        print(f"  - {f}")


if __name__ == "__main__":
    fix_test_imports()
