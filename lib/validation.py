#!/usr/bin/env python3
"""Shared validation utilities for fplaunchwrapper.

Provides validation functions for app IDs, path traversal checks,
and event processing logic.
"""

from __future__ import annotations

# os removed - pathlib.Path used instead
import re
from pathlib import Path

__all__ = [
    "validate_app_id",
    "validate_wrapper_name",
    "check_path_traversal",
    "should_process_event",
]


MAX_WRAPPER_NAME_LENGTH = 255
# Linux path length limit is typically 4096, reserve space for bin_dir prefix
MAX_PATH_OVERHEAD = 512  # Reserve for bin_dir + wrapper prefix + extension
# Stricter limit for CLI commands to prevent path length issues
MAX_CLI_WRAPPER_NAME = 128

def validate_wrapper_name(name: str, max_total_length: int = MAX_WRAPPER_NAME_LENGTH) -> tuple[bool, str]:
    """Validate a wrapper name (script filename).

    Args:
        name: The wrapper name to validate
        max_total_length: Maximum allowed length for the wrapper name (default: 255)

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is empty string
    """
    if not name or not name.strip():
        return False, "Empty wrapper name provided"

    # Check length (filesystem limits)
    if len(name) > max_total_length:
        return False, f"Wrapper name too long: {len(name)} chars (max {max_total_length})"

    # Wrapper names must be valid POSIX filename
    # Invalid characters: / \0 and path separators
    invalid_chars = ['/', '\\', '\0']
    for char in invalid_chars:
        if char in name:
            return False, f"Invalid character in wrapper name: '{char}'"

    # Names shouldn't start with - (often interpreted as options)
    if name.startswith('-'):
        return False, "Wrapper name cannot start with hyphen"

    # Hidden files (starting with .) should be handled carefully
    if name.startswith('.') and len(name) > 1:
        # Allow . to work as wrapper name, but warn about hidden files
        # This is a security consideration - hidden wrappers can be unexpected
        pass

    return True, ""


def validate_app_id(app_id: str) -> tuple[bool, str]:
    """Validate a Flatpak application ID.

    Args:
        app_id: The application ID to validate

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is empty string
    """
    if not app_id or not app_id.strip():
        return False, "Empty app_id provided"

    # Flatpak IDs must not start or end with a dot (check BEFORE regex for specific errors)
    if app_id.startswith("."):
        return False, f"Invalid app_id: {app_id} (cannot start with a dot)"
    if app_id.endswith("."):
        return False, f"Invalid app_id: {app_id} (cannot end with a dot)"

    # Flatpak IDs must not have trailing slash
    if app_id.endswith("/"):
        return False, f"Invalid app_id: {app_id} (cannot end with a slash)"

    # Platform/runtime IDs may use // for version format (e.g., org.freedesktop.Platform//21.08)
    # Check this BEFORE the main regex since it contains /
    has_platform_version = "//" in app_id

    # Validate: only allow letters, digits, dot, underscore, hyphen, and optionally /
    # for platform/runtime version format (e.g., org.freedesktop.Platform//21.08)
    # Must start with a letter (not digit, dot, hyphen, underscore)
    if has_platform_version:
        if not re.match(r"^[A-Za-z][A-Za-z0-9._/-]*$", app_id):
            return False, f"Invalid app_id: {app_id}"
    else:
        if not re.match(r"^[A-Za-z][A-Za-z0-9._-]*$", app_id):
            return False, f"Invalid app_id: {app_id}"

    # Flatpak IDs must contain at least one dot (reverse-DNS format)
    if "." not in app_id:
        return False, f"Invalid app_id: {app_id} (must contain a dot for reverse-DNS format)"

    # Standalone / is not allowed (only // for platform versions)
    if "/" in app_id and "//" not in app_id:
        return False, (
            f"Invalid app_id: {app_id} (forward slash only allowed in // for platform versions)"
        )

    return True, ""


def check_path_traversal(path: str | Path, base_dir: Path) -> tuple[bool, str]:
    """Check if a path attempts to traverse outside its base directory.

    Args:
        path: The path to check
        base_dir: The base directory that path should be contained within

    Returns:
        Tuple of (is_safe, error_message)
        If safe, error_message is empty string

    Security Note:
        This function resolves symlinks, so symlinks within the base_dir
        pointing to outside locations will be flagged as unsafe.
    """
    try:
        path = Path(path) if not isinstance(path, Path) else path
        # Check for symlinks in the path that might escape base_dir
        resolved_path = path.resolve()
        resolved_base = base_dir.resolve()

        # Verify the path is within base_dir
        resolved_path.relative_to(resolved_base)
        return True, ""
    except (ValueError, OSError) as e:
        return False, f"Path traversal detected: {e}"


def _normalize_flatpak_path(path: str) -> str:
    """Normalize a path for comparison by expanding ~ and resolving to absolute path.

    This handles cases where the actual home directory path differs from ~ in
    the path string (e.g., symlinks like /home/user -> /var/home/user).
    """
    if path.startswith("~"):
        path = str(Path(path).expanduser())
    return str(Path(path).resolve())


# Flatpak paths that should trigger event processing (normalized lazily at runtime)
def _get_flatpak_paths() -> tuple[str, ...]:
    """Get normalized Flatpak paths for event filtering."""
    return (
        "/var/lib/flatpak",
        _normalize_flatpak_path("~/.local/share/flatpak"),
        _normalize_flatpak_path("~/.var/app"),
    )


def should_process_event(path: str | Path) -> bool:
    """Determine if we should process a file system event for this path.

    Args:
        path: The file system path to check

    Returns:
        True if the path is under a Flatpak directory and should be processed
    """
    path_str = str(path)
    path_norm = str(Path(path_str).resolve())

    for flatpak_path in _get_flatpak_paths():
        if path_norm == flatpak_path or path_norm.startswith(flatpak_path + "/"):
            return True

    return False
