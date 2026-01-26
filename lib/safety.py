#!/usr/bin/env python3
"""Safety mechanisms to prevent accidental browser launches during tests.

This module lives in the real package directory (lib/) so that
`from fplaunch.safety import ...` resolves correctly under the configured
package-dir mapping in pyproject.toml.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import os
import sys


# Capture initial pytest modules so we can restore them if tests remove entries
_PYTEST_MODULE_SNAPSHOT = {
    name: module for name, module in sys.modules.items() if "pytest" in name
}


def _restore_pytest_if_missing() -> None:
    """Ensure pytest remains in sys.modules when running under pytest."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        # Restore any previously-loaded pytest modules that were removed
        for name, module in _PYTEST_MODULE_SNAPSHOT.items():
            if name not in sys.modules:
                sys.modules[name] = module

        if "pytest" not in sys.modules:
            try:
                sys.modules["pytest"] = importlib.import_module("pytest")
            except Exception:
                # Graceful fallback if pytest cannot be imported
                pass


def is_test_environment() -> bool:
    """Check if we're running in a test environment.

    Precedence:
    1. FPWRAPPER_TEST_ENV explicitly set to "true" -> True
       FPWRAPPER_TEST_ENV explicitly set to "false" -> False
    2. Command line args containing "test" -> True
    3. Presence of pytest/unittest or pytest env vars -> True

    When pytest env vars are present but FPWRAPPER_TEST_ENV is explicitly
    set to "false", we honor the explicit override to satisfy tests that
    simulate non-test contexts while running under pytest.
    """

    _restore_pytest_if_missing()

    env_override = os.environ.get("FPWRAPPER_TEST_ENV")
    value = env_override.lower().strip() if env_override is not None else None

    explicit_test_arg = any((arg or "").lower() == "test" for arg in sys.argv)

    # Explicit env override takes precedence, but allow a deliberate "test" arg
    if value == "true":
        _restore_pytest_if_missing()
        return True
    if value == "false":
        return True if explicit_test_arg else False

    # Command-line intent
    if explicit_test_arg:
        _restore_pytest_if_missing()
        return True

    # Check if we're being imported by pytest or unittest
    if "pytest" in sys.modules or "unittest" in sys.modules:
        return True

    # Check for pytest-specific environment variables
    if os.environ.get("PYTEST_CURRENT_TEST") or any(
        key.startswith("PYTEST_") for key in os.environ
    ):
        # If we reach here, no explicit opt-out was set; treat as test env
        _restore_pytest_if_missing()
        return True

    _restore_pytest_if_missing()
    return False


def is_dangerous_wrapper(wrapper_path: Path) -> bool:
    """Check if a wrapper script contains dangerous commands."""
    try:
        if wrapper_path.exists():
            content = wrapper_path.read_text()
            dangerous_patterns = [
                "flatpak run org.mozilla.firefox",
                "flatpak run com.google.Chrome",
                "firefox ",  # Direct firefox command
                "google-chrome",
                "chromium",
            ]
            return any(pattern in content for pattern in dangerous_patterns)
    except (IOError, OSError, UnicodeDecodeError):
        # If unreadable, err on the safe side by treating as non-dangerous
        # and letting higher-level checks decide next steps.
        pass
    return False


def _is_direct_browser_launch(app_name: str) -> bool:
    """Check if this is a direct browser launch that should be allowed in tests."""
    browser_names = ["firefox", "chrome", "chromium", "google-chrome"]
    return app_name.lower() in browser_names


def safe_launch_check(app_name: str, wrapper_path: str | Path | None = None) -> bool:
    """Perform safety checks before launching an application."""
    # Check wrapper content if provided (always perform this check)
    if wrapper_path:
        wrapper_path_obj = (
            Path(wrapper_path) if isinstance(wrapper_path, str) else wrapper_path
        )
        if is_dangerous_wrapper(wrapper_path_obj):
            print(
                f"🛡️  Safety: Blocked dangerous wrapper {wrapper_path}",
                file=sys.stderr,
            )
            return False

    # In test environment, block direct browser launches for safety
    if is_test_environment():
        if _is_direct_browser_launch(app_name):
            print(
                f"🛡️  Safety: Blocked direct browser launch in test environment: {app_name}",
                file=sys.stderr,
            )
            return False
        return True

    return True
