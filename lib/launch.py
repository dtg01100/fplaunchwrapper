#!/usr/bin/env python3
"""Application launcher for fplaunchwrapper
Replaces fplaunch-launch bash script with Python implementation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Import our utilities
try:
    from python_utils import find_executable

    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False


class AppLauncher:
    """Launch Flatpak applications with preference handling."""

    def __init__(self, config_dir: str | None = None) -> None:
        self.config_dir = Path(
            config_dir or (Path.home() / ".config" / "fplaunchwrapper"),
        )
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Get bin directory from config
        bin_dir_file = self.config_dir / "bin_dir"
        if bin_dir_file.exists():
            self.bin_dir = Path(bin_dir_file.read_text().strip())
        else:
            self.bin_dir = Path.home() / "bin"

    def launch_app(self, app_name: str, args: list[str] | None = None) -> int:
        """Launch an application by name."""
        if args is None:
            args = []

        wrapper_path = self.bin_dir / app_name

        if not wrapper_path.exists():
            return 1

        if not os.access(wrapper_path, os.X_OK):
            return 1

        try:
            # Execute the wrapper script
            cmd = [str(wrapper_path), *args]
            os.execv(str(wrapper_path), cmd)
            # This should not return
            return 0
        except Exception:
            return 1


def main():
    """Command-line interface for launching applications."""
    if len(sys.argv) < 2:
        return 1

    app_name = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    launcher = AppLauncher()
    return launcher.launch_app(app_name, args)


if __name__ == "__main__":
    sys.exit(main())
