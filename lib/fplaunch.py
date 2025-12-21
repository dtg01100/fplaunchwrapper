#!/usr/bin/env python3
"""fplaunchwrapper - Modern Flatpak wrapper management system
Main entry point for all operations.
"""

import os
import sys

# Add lib directory to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))


def main():
    """Main entry point."""
    try:
        from .cli import cli

        return cli()
    except ImportError:
        try:
            # Fallback for when running as installed package
            from fplaunch.cli import cli

            return cli()
        except ImportError:
            return 1


if __name__ == "__main__":
    sys.exit(main())
