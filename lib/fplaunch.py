#!/usr/bin/env python3
"""fplaunchwrapper - Modern Flatpak wrapper management system
Main entry point for all operations.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

# Expose important submodules (like `safety`) as attributes on the package
# so tests that patch `fplaunch.safety` can find them regardless of import
# ordering or package installation details.
try:
    from . import safety
except Exception:
    class _SafetyStub:
        @staticmethod
        def safe_launch_check(*args, **kwargs):
            return True

    safety = _SafetyStub()  # type: ignore[assignment]


def main():
    """Main entry point."""
    try:
        from . import cli

        if hasattr(cli, "main"):
            return cli.main()
        else:
            return 1
    except (ImportError, AttributeError):
        try:
            from lib import cli

            if hasattr(cli, "main"):
                return cli.main()
            else:
                return 1
        except (ImportError, AttributeError):
            return 1


if __name__ == "__main__":
    sys.exit(main())
