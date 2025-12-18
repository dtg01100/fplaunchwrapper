#!/usr/bin/env python3
"""
Application launcher for fplaunchwrapper
Replaces fplaunch-launch bash script with Python implementation
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

# Import our utilities
try:
    from python_utils import find_executable

    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False


class AppLauncher:
    """Launch Flatpak applications with preference handling"""

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(
            config_dir or (Path.home() / ".config" / "fplaunchwrapper")
        )
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Get bin directory from config
        bin_dir_file = self.config_dir / "bin_dir"
        if bin_dir_file.exists():
            self.bin_dir = Path(bin_dir_file.read_text().strip())
        else:
            self.bin_dir = Path.home() / "bin"

    def launch_app(self, app_name: str, args: List[str] = None) -> int:
        """Launch an application by name"""
        if args is None:
            args = []

        wrapper_path = self.bin_dir / app_name

        if not wrapper_path.exists():
            print(
                f"Wrapper '{app_name}' not found. Run 'fplaunch generate' to create wrappers.",
                file=sys.stderr,
            )
            return 1

        if not os.access(wrapper_path, os.X_OK):
            print(f"Wrapper '{app_name}' is not executable.", file=sys.stderr)
            return 1

        try:
            # Execute the wrapper script
            cmd = [str(wrapper_path)] + args
            os.execv(str(wrapper_path), cmd)
            # This should not return
            return 0
        except Exception as e:
            print(f"Failed to launch '{app_name}': {e}", file=sys.stderr)
            return 1


def main():
    """Command-line interface for launching applications"""
    if len(sys.argv) < 2:
        print("Usage: python -m launch <app_name> [args...]", file=sys.stderr)
        print("Launch a Flatpak application using its wrapper", file=sys.stderr)
        return 1

    app_name = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    launcher = AppLauncher()
    return launcher.launch_app(app_name, args)


if __name__ == "__main__":
    sys.exit(main())
