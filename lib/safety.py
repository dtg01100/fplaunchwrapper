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

import contextlib
import hashlib
import importlib
import os
import re
import sys
import unicodedata
from pathlib import Path


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


def sanitize_string(input_str: str) -> str:
    """Safely sanitize a string for use in shell/Python code."""
    if not input_str:
        return ""

    sanitized = input_str.replace("\\", "\\\\")
    sanitized = sanitized.replace('"', '\\"')
    sanitized = sanitized.replace("'", "\\'")
    sanitized = sanitized.replace("$", "\\$")
    sanitized = sanitized.replace("`", "\\`")
    sanitized = sanitized.replace("(", "\\(")
    sanitized = sanitized.replace(")", "\\)")
    sanitized = sanitized.replace(";", "\\;")
    sanitized = sanitized.replace("&", "\\&")
    sanitized = sanitized.replace("|", "\\|")
    sanitized = sanitized.replace("<", "\\<")
    sanitized = sanitized.replace(">", "\\>")
    sanitized = sanitized.replace("\n", "\\n")
    sanitized = sanitized.replace("\r", "\\r")
    return sanitized.replace("\t", "\\t")


def sanitize_id_to_name(id_str: str) -> str:
    """Sanitize a Flatpak ID to a safe wrapper name."""
    try:
        name = id_str.split(".")[-1].lower()

        try:
            name = unicodedata.normalize("NFKD", name)
            name = "".join(c for c in name if not unicodedata.combining(c))
        except ImportError:
            pass

        with contextlib.suppress(UnicodeError):
            name = name.encode("ascii", "ignore").decode("ascii")

        name = re.sub(r"[^a-z0-9_\-]", "-", name)

        name = re.sub(r"^\-+|\-+$", "", name)
        name = re.sub(r"\-+", "-", name)

        if not name:
            hash_obj = hashlib.sha256(id_str.encode("utf-8"))
            name = f"app-{hash_obj.hexdigest()[:8]}"

        return name[:100]

    except (TypeError, AttributeError, UnicodeDecodeError, re.error):
        try:
            return f"app-{hashlib.sha256(id_str.encode('utf-8')).hexdigest()[:8]}"
        except Exception:
            return "app-fallback"


def canonicalize_path_no_resolve(path: str | Path) -> Path | None:
    """Normalize a path without resolving symlinks."""
    try:
        path_str = str(path)

        if path_str.startswith("~"):
            path_str = os.path.expanduser(path_str)

        if not os.path.isabs(path_str):
            path_str = os.path.abspath(path_str)

        return Path(os.path.normpath(path_str))

    except (TypeError, ValueError, OSError):
        return None


def validate_home_dir(dir_path: str | Path) -> str | None:
    """Validate that a directory is within HOME.

    Returns the normalized absolute path string if within HOME, otherwise None.
    """
    try:
        dir_str = str(dir_path)

        if dir_str.startswith("~"):
            dir_str = os.path.expanduser(dir_str)

        abs_dir = os.path.abspath(dir_str)

        if os.path.islink(abs_dir):
            abs_dir = os.path.realpath(abs_dir)

        home = os.path.expanduser("~")
        if abs_dir == home or abs_dir.startswith(home + os.sep):
            return abs_dir

        return None
    except (TypeError, ValueError, OSError):
        return None


def validate_flatpak_id(flatpak_id: str) -> bool:
    """Validate a Flatpak ID format.

    Valid IDs: org.mozilla.Firefox, com.example.App123
    Must contain at least one dot, only alphanumeric, hyphens, underscores.
    """
    if not flatpak_id or not isinstance(flatpak_id, str):
        return False

    if "." not in flatpak_id:
        return False

    return bool(re.match(r"^[A-Za-z0-9._-]+$", flatpak_id))


def is_wrapper_file(file_path: str | Path) -> bool | None:
    """Check if a file is a valid wrapper script."""
    try:
        if not os.path.isfile(file_path):
            return False
        if not os.access(file_path, os.R_OK):
            return False
        if os.path.islink(file_path):
            return False

        size = os.path.getsize(file_path)
        if size > 100000:
            return False

        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read(min(8192, size))

        if any(ord(c) < 32 and c not in "\t\n\r" for c in content):
            return False

        if not re.match(r"^#!.*(bash|sh)", content, re.MULTILINE):
            return False

        if "Generated by fplaunchwrapper" not in content:
            return False

        name_match = re.search(r"^NAME=[^\n]*", content, re.MULTILINE)
        id_match = re.search(r"^ID=[^\n]*", content, re.MULTILINE)

        if not name_match or not id_match:
            return False

        id_value = re.search(r'ID="([^"]*)"', id_match.group())
        return not (
            not id_value or not re.match(r"^[A-Za-z0-9._-]+$", id_value.group(1))
        )
    except (IOError, OSError, UnicodeDecodeError, re.error):
        return False


def get_wrapper_id(file_path: str | Path) -> str | None:
    """Extract the wrapper ID from a wrapper script."""
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read(8192)

        id_match = re.search(r'^ID="([^"]*)"', content, re.MULTILINE)
        if id_match:
            return id_match.group(1)

        comment_match = re.search(r"Flatpak ID:\s*([^\s\n]+)", content)
        if comment_match:
            return comment_match.group(1)

        return None
    except (IOError, OSError, UnicodeDecodeError, re.error):
        return None


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
