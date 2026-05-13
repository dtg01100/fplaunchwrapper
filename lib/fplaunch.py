#!/usr/bin/env python3
"""fplaunchwrapper - Modern Flatpak wrapper management system
Main entry point for all operations.
"""

import sys
from typing import Any

safety: Any
safe_launch_check: Any

try:
    from .safety import is_wrapper_file as safe_launch_check
    from . import safety as _safety_mod

    safety = _safety_mod
except (ImportError, AttributeError):

    class _SafetyStub:
        @staticmethod
        def is_wrapper_file(_app_name, _wrapper_path=None):
            return True

    safety = _SafetyStub()
    safe_launch_check = safety.is_wrapper_file


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
