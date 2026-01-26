#!/usr/bin/env python3
"""fplaunchwrapper - Modern Flatpak wrapper management system
Main entry point for all operations.
"""

import os
import sys

# Add lib directory to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

# Expose important submodules (like `safety`) as attributes on the package
# so tests that patch `fplaunch.safety` can find them regardless of import
# ordering or package installation details.
try:
    from . import safety  # type: ignore
except Exception:
    # Minimal stub to allow tests to patch attributes on fplaunch.safety
    class _SafetyStub:
        @staticmethod
        def safe_launch_check(*args, **kwargs):
            return True

    safety = _SafetyStub()


def main():
    """Main entry point."""
    try:
        from . import cli

        if hasattr(cli, "main"):
            return cli.main()
        else:
            # Fallback - shouldn't happen
            return 1
    except (ImportError, AttributeError):
        try:
            # Fallback for when running as installed package
            from lib import cli

            if hasattr(cli, "main"):
                return cli.main()
            else:
                return 1
        except (ImportError, AttributeError):
            return 1


if __name__ == "__main__":
    sys.exit(main())
