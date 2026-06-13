#!/usr/bin/env python3
"""Centralized path resolution for fplaunchwrapper.

This module provides consistent path resolution across all components,
eliminating duplicated path logic and ensuring XDG Base Directory
specification compliance.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_default_config_dir(app_name: str = "fplaunchwrapper") -> Path:
    """Get the default fplaunchwrapper configuration directory.

    Resolves in order:
    1. XDG_CONFIG_HOME/{app_name} if XDG_CONFIG_HOME is set
    2. ~/.config/{app_name} as fallback

    Args:
        app_name: Application name for namespacing (default: "fplaunchwrapper")

    Returns:
        Path to the configuration directory
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / app_name
    return Path.home() / ".config" / app_name


def get_default_bin_dir() -> Path:
    """Get the default wrapper bin directory.

    Returns:
        Path to ~/bin directory
    """
    return Path.home() / "bin"


def get_default_data_dir(app_name: str = "fplaunchwrapper") -> Path:
    """Get the default fplaunchwrapper data directory.

    Resolves in order:
    1. XDG_DATA_HOME/{app_name} if XDG_DATA_HOME is set
    2. ~/.local/share/{app_name} as fallback

    Args:
        app_name: Application name for namespacing (default: "fplaunchwrapper")

    Returns:
        Path to the data directory
    """
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / app_name
    return Path.home() / ".local" / "share" / app_name


def get_default_cache_dir(app_name: str = "fplaunchwrapper") -> Path:
    """Get the default fplaunchwrapper cache directory.

    Resolves in order:
    1. XDG_CACHE_HOME/{app_name} if XDG_CACHE_HOME is set
    2. ~/.cache/{app_name} as fallback

    Args:
        app_name: Application name for namespacing (default: "fplaunchwrapper")

    Returns:
        Path to the cache directory
    """
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache) / app_name
    return Path.home() / ".cache" / app_name


def get_systemd_unit_dir() -> Path:
    """Get the systemd user unit directory.

    Returns:
        Path to the systemd user unit directory
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "systemd" / "user"
    return Path.home() / ".config" / "systemd" / "user"


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory to ensure exists

    Returns:
        The same path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_lock_dir() -> Path:
    """Get the lock directory for fplaunchwrapper.

    Returns:
        Path to the locks directory within the config directory
    """
    return get_default_config_dir() / "locks"


def get_scripts_dir() -> Path:
    """Get the scripts directory for fplaunchwrapper.

    Returns:
        Path to the scripts directory within the config directory
    """
    return get_default_config_dir() / "scripts"


def resolve_bin_dir(explicit_dir: Optional[str] = None, config_dir: Optional[Path] = None) -> Path:
    """Resolve the bin directory with fallback chain.

    Resolution order:
    1. Explicit directory if provided
    2. Read from config_dir/bin_dir file if it exists
    3. Default ~/bin

    Args:
        explicit_dir: Explicitly provided bin directory
        config_dir: Configuration directory to read bin_dir from

    Returns:
        Resolved bin directory path

    Note:
        This function is total by design: it never raises on a bad
        ``explicit_dir`` or unreadable ``bin_dir`` file. Malformed
        input is silently dropped to the next fallback so callers
        (and the fuzz tests that pin this contract) cannot crash.
        Use :func:`lib.validation.validate_app_id` upstream if you
        need to reject bad input explicitly.
    """
    if explicit_dir:
        try:
            return Path(explicit_dir).expanduser()
        except (RuntimeError, ValueError):
            # RuntimeError: HOME not set; ValueError: embedded null byte.
            # Silent fallback to default keeps the function total.
            return get_default_bin_dir()

    if config_dir:
        bin_dir_file = config_dir / "bin_dir"
        try:
            if bin_dir_file.exists():
                bin_path = bin_dir_file.read_text().strip()
                if bin_path:
                    try:
                        return Path(bin_path).expanduser()
                    except (RuntimeError, ValueError):
                        return get_default_bin_dir()
        except (OSError, UnicodeDecodeError):
            pass

    return get_default_bin_dir()
