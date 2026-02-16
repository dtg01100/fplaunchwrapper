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


def get_default_config_dir() -> Path:
    """Get the default fplaunchwrapper configuration directory.
    
    Resolves in order:
    1. XDG_CONFIG_HOME/fplaunchwrapper if XDG_CONFIG_HOME is set
    2. ~/.config/fplaunchwrapper as fallback
    
    Returns:
        Path to the configuration directory
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "fplaunchwrapper"
    return Path.home() / ".config" / "fplaunchwrapper"


def get_default_bin_dir() -> Path:
    """Get the default wrapper bin directory.
    
    Returns:
        Path to ~/bin directory
    """
    return Path.home() / "bin"


def get_default_data_dir() -> Path:
    """Get the default fplaunchwrapper data directory.
    
    Resolves in order:
    1. XDG_DATA_HOME/fplaunchwrapper if XDG_DATA_HOME is set
    2. ~/.local/share/fplaunchwrapper as fallback
    
    Returns:
        Path to the data directory
    """
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / "fplaunchwrapper"
    return Path.home() / ".local" / "share" / "fplaunchwrapper"


def get_default_cache_dir() -> Path:
    """Get the default fplaunchwrapper cache directory.
    
    Resolves in order:
    1. XDG_CACHE_HOME/fplaunchwrapper if XDG_CACHE_HOME is set
    2. ~/.cache/fplaunchwrapper as fallback
    
    Returns:
        Path to the cache directory
    """
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache) / "fplaunchwrapper"
    return Path.home() / ".cache" / "fplaunchwrapper"


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
    """
    if explicit_dir:
        return Path(explicit_dir)
    
    if config_dir:
        bin_dir_file = config_dir / "bin_dir"
        try:
            if bin_dir_file.exists():
                bin_path = bin_dir_file.read_text().strip()
                if bin_path:
                    return Path(bin_path)
        except (OSError, UnicodeDecodeError):
            pass
    
    return get_default_bin_dir()
