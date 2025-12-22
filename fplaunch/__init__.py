"""Proxy package for local development and CI.

This package exposes modules from the local ``lib`` directory under the
``fplaunch`` namespace so tests and scripts can import ``fplaunch.*``
without requiring the project to be installed into the environment.
"""

# Re-export key submodules via lightweight shim modules placed alongside
# this __init__.py (see files in this package). No additional logic needed here.

__all__ = [
    "cleanup",
    "cli",
    "config_manager",
    "flatpak_monitor",
    "fplaunch",
    "generate",
    "launch",
    "manage",
    "python_utils",
    "systemd_setup",
]
