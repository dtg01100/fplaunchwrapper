#!/usr/bin/env python3
"""
fplaunchwrapper - Modern Flatpak wrapper management system
Main entry point for all operations
"""

import sys
import os
from pathlib import Path

# Add lib directory to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))


def main():
    """Main entry point"""
    try:
        from .cli import cli

        return cli()
    except ImportError:
        try:
            # Fallback for when running as installed package
            from fplaunch.cli import cli

            return cli()
        except ImportError as e:
            print(f"CLI not available: {e}", file=sys.stderr)
            print("Please ensure all dependencies are installed:", file=sys.stderr)
            print("  uv pip install -e '.[advanced]'", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
