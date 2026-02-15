#!/usr/bin/env python3
"""Safety mechanisms for fplaunchwrapper.

This module handles all security boundaries including:
- Input validation and sanitization
- Path traversal prevention
- Wrapper file validation
- Test environment detection
- Safe launch checks
"""

from __future__ import annotations

import importlib
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Define fallback exception classes first
class _SafetyError(Exception):
    pass

class _ForbiddenNameError(Exception):
    pass

class _PathTraversalError(Exception):
    pass

class _InvalidFlatpakIdError(Exception):
    pass

# Default to fallback values
SafetyError = _SafetyError
ForbiddenNameError = _ForbiddenNameError
PathTraversalError = _PathTraversalError
InvalidFlatpakIdError = _InvalidFlatpakIdError

# Default utils to None
canonicalize_path_no_resolve: Any = None
get_wrapper_id: Any = None
is_wrapper_file: Any = None
sanitize_id_to_name: Any = None
sanitize_string: Any = None
validate_home_dir: Any = None
UTILS_IMPORTED = False

# Try to import and override with real implementations
try:
    from .exceptions import (
        ForbiddenNameError as _ForbiddenNameErrorReal,
        InvalidFlatpakIdError as _InvalidFlatpakIdErrorReal,
        PathTraversalError as _PathTraversalErrorReal,
        SafetyError as _SafetyErrorReal,
    )
    SafetyError = _SafetyErrorReal  # type: ignore[misc,assignment]
    ForbiddenNameError = _ForbiddenNameErrorReal  # type: ignore[misc,assignment]
    PathTraversalError = _PathTraversalErrorReal  # type: ignore[misc,assignment]
    InvalidFlatpakIdError = _InvalidFlatpakIdErrorReal  # type: ignore[misc,assignment]
except ImportError:
    pass

try:
    from .python_utils import (
        canonicalize_path_no_resolve as _canonicalize_path_no_resolve,
        get_wrapper_id as _get_wrapper_id,
        is_wrapper_file as _is_wrapper_file,
        sanitize_id_to_name as _sanitize_id_to_name,
        sanitize_string as _sanitize_string,
        validate_home_dir as _validate_home_dir,
    )
    canonicalize_path_no_resolve = _canonicalize_path_no_resolve
    get_wrapper_id = _get_wrapper_id
    is_wrapper_file = _is_wrapper_file
    sanitize_id_to_name = _sanitize_id_to_name
    sanitize_string = _sanitize_string
    validate_home_dir = _validate_home_dir
    UTILS_IMPORTED = True
except ImportError:
    pass

__all__ = [
    "canonicalize_path_no_resolve",
    "get_wrapper_id",
    "is_test_environment",
    "is_wrapper_file",
    "sanitize_id_to_name",
    "sanitize_string",
    "validate_flatpak_id",
    "validate_home_dir",
    "safe_launch_check",
    "SafetyError",
    "ForbiddenNameError",
    "PathTraversalError",
    "InvalidFlatpakIdError",
]


_PYTEST_MODULE_SNAPSHOT = {
    name: module for name, module in sys.modules.items() if "pytest" in name
}


def _restore_pytest_if_missing() -> None:
    """Ensure pytest remains in sys.modules when running under pytest."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        for name, module in _PYTEST_MODULE_SNAPSHOT.items():
            if name not in sys.modules:
                sys.modules[name] = module

        if "pytest" not in sys.modules:
            try:
                sys.modules["pytest"] = importlib.import_module("pytest")
            except Exception:
                pass


def is_test_environment() -> bool:
    """Check if we're running in a test environment.

    Precedence:
    1. FPWRAPPER_TEST_ENV explicitly set to "true" -> True
       FPWRAPPER_TEST_ENV explicitly set to "false" -> False
    2. Command line args containing "test" -> True
    3. Presence of pytest/unittest or pytest env vars -> True
    """
    _restore_pytest_if_missing()

    env_override = os.environ.get("FPWRAPPER_TEST_ENV")
    value = env_override.lower().strip() if env_override is not None else None

    explicit_test_arg = any((arg or "").lower() == "test" for arg in sys.argv)

    if value == "true":
        _restore_pytest_if_missing()
        return True
    if value == "false":
        return True if explicit_test_arg else False

    if explicit_test_arg:
        _restore_pytest_if_missing()
        return True

    if "pytest" in sys.modules or "unittest" in sys.modules:
        return True

    if os.environ.get("PYTEST_CURRENT_TEST") or any(
        key.startswith("PYTEST_") for key in os.environ
    ):
        _restore_pytest_if_missing()
        return True

    _restore_pytest_if_missing()
    return False


def validate_flatpak_id(flatpak_id: str) -> bool:
    """Validate a Flatpak ID format.

    Valid IDs: org.mozilla.Firefox, com.example.App123
    Must contain at least one dot, only alphanumeric, hyphens, underscores, dots.
    Must start with a letter.
    """
    if not flatpak_id or not isinstance(flatpak_id, str):
        return False

    if "." not in flatpak_id:
        return False

    if (
        flatpak_id.startswith(".")
        or flatpak_id.startswith("-")
        or flatpak_id.startswith("_")
    ):
        return False

    return bool(re.match(r"^[A-Za-z][A-Za-z0-9._-]*$", flatpak_id))


def is_dangerous_wrapper(wrapper_path: Path) -> bool:
    """Check if a wrapper script contains dangerous commands."""
    try:
        if wrapper_path.exists():
            content = wrapper_path.read_text()
            dangerous_patterns = [
                "flatpak run org.mozilla.firefox",
                "flatpak run com.google.Chrome",
                "firefox ",
                "google-chrome",
                "chromium",
            ]
            return any(pattern in content for pattern in dangerous_patterns)
    except (IOError, OSError, UnicodeDecodeError):
        pass
    return False


def _is_direct_browser_launch(app_name: str) -> bool:
    """Check if this is a direct browser launch."""
    browser_names = ["firefox", "chrome", "chromium", "google-chrome"]
    return app_name.lower() in browser_names


def safe_launch_check(app_name: str, wrapper_path: str | Path | None = None) -> bool:
    """Perform safety checks before launching an application."""
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

    if is_test_environment():
        if _is_direct_browser_launch(app_name):
            print(
                f"🛡️  Safety: Blocked direct browser launch in test environment: {app_name}",
                file=sys.stderr,
            )
            return False
        return True

    return True
