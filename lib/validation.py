#!/usr/bin/env python3
"""Shared validation utilities for fplaunchwrapper.

Provides validation functions for app IDs, path traversal checks,
and event processing logic.
"""

from __future__ import annotations

import os
import re
from pathlib import Path


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

    # Validate: only allow letters, digits, dot, underscore, hyphen
    # Must start with a letter (not digit, dot, hyphen, underscore)
    if not re.match(r"^[A-Za-z][A-Za-z0-9._-]*$", app_id):
        return False, f"Invalid app_id: {app_id}"

    return True, ""


def check_path_traversal(path: Path, base_dir: Path) -> tuple[bool, str]:
    """Check if a path attempts to traverse outside its base directory.

    Args:
        path: The path to check
        base_dir: The base directory that path should be contained within

    Returns:
        Tuple of (is_safe, error_message)
        If safe, error_message is empty string
    """
    try:
        path.resolve().relative_to(base_dir.resolve())
        return True, ""
    except ValueError as e:
        return False, f"Path traversal detected: {e}"


def _normalize_flatpak_path(path: str) -> str:
    """Normalize a path for comparison by expanding ~ and resolving to absolute path.

    This handles cases where the actual home directory path differs from ~ in
    the path string (e.g., symlinks like /home/user -> /var/home/user).
    """
    if path.startswith("~"):
        path = os.path.expanduser(path)
    return os.path.abspath(path)


# Flatpak paths that should trigger event processing (normalized lazily at runtime)
def _get_flatpak_paths() -> tuple[str, ...]:
    """Get normalized Flatpak paths for event filtering."""
    return (
        "/var/lib/flatpak",
        _normalize_flatpak_path("~/.local/share/flatpak"),
        _normalize_flatpak_path("~/.var/app"),
    )


def should_process_event(path: str | object) -> bool:
    """Determine if we should process a file system event for this path.

    Args:
        path: The file system path to check

    Returns:
        True if the path is under a Flatpak directory and should be processed
    """
    path_str = str(path)
    path_norm = os.path.abspath(path_str)

    for flatpak_path in _get_flatpak_paths():
        if path_norm == flatpak_path or path_norm.startswith(flatpak_path + "/"):
            return True

    return False
