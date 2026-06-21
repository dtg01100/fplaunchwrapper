#!/usr/bin/env python3

"""fplaunchwrapper - Modern Flatpak wrapper management system
Main entry point for all operations.
"""

import sys

from . import safety as safety_mod
from .safety import safe_launch_check  # noqa: F401  (re-exported for back-compat)

__all__ = [
    "main",
    "safe_launch_check",
    "safety",
]

safety = safety_mod


def main() -> int:
    """Main entry point."""
    try:
        from .cli import main as cli_main

        if cli_main is not None:
            return cli_main()
        return 1
    except ImportError as e:
        import os

        sys.stderr.write(
            f"fplaunchwrapper: failed to import CLI module: {e}\n"
            f"  PYTHONPATH={os.environ.get('PYTHONPATH', '<unset>')}\n"
            f"  Check that fplaunchwrapper is installed correctly.\n"
        )
        return 1
    except AttributeError as e:
        sys.stderr.write(f"fplaunchwrapper: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
