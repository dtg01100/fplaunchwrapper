#!/usr/bin/env python3
"""fplaunchwrapper - Modern Flatpak wrapper management system
Main entry point for all operations.
"""

import sys
from typing import Any

from .safety import is_wrapper_file as safe_launch_check
from . import safety as safety_mod

safety = safety_mod


def main():
    """Main entry point."""
    try:
        from .cli import main as cli_main

        if cli_main is not None:
            return cli_main()
        return 1
    except (ImportError, AttributeError):
        return 1


if __name__ == "__main__":
    sys.exit(main())
