#!/usr/bin/env python3
"""fplaunchwrapper - Modern Flatpak wrapper management system
Main entry point for all operations.
"""

import sys

# Expose important submodules (like `safety`) as attributes on the package
# so tests that patch `fplaunch.safety` can find them regardless of import
# ordering or package installation details.
try:
    from .safety import is_wrapper_file as safe_launch_check
except (ImportError, AttributeError):

    class _SafetyStub:
        @staticmethod
        def safe_launch_check(_app_name, _wrapper_path=None):
            return True

    safety = _SafetyStub()  # type: ignore[assignment]


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
