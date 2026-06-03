#!/usr/bin/env python3
"""Command-line interface for fplaunchwrapper configuration management.

This module contains the ``main()`` function used by the ``fplaunch-config``
console script. The configuration manager class itself lives in
``lib.config_manager``.
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    """Command-line interface for configuration management."""
    parser = argparse.ArgumentParser(
        description="Manage fplaunchwrapper configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fplaunch-config init                   # Initialize configuration
  fplaunch-config block firefox          # Block Firefox from being wrapped
  fplaunch-config unblock firefox        # Unblock Firefox
  fplaunch-config list-presets           # List permission presets
  fplaunch-config get-preset gaming      # Get permissions for 'gaming' preset

Commands:
  init          Initialize default configuration
  show          Show current configuration
  block APP     Block application from being wrapped
  unblock APP   Unblock application
  list-presets  List all permission presets
  get-preset NAME Get permissions for a specific preset
        """,
    )

    parser.add_argument(
        "command",
        choices=["init", "show", "block", "unblock", "list-presets", "get-preset"],
        help="Configuration command to execute",
    )

    parser.add_argument(
        "value",
        nargs="?",
        help="Value for the command (app name for block/unblock, preset name for get-preset)",
    )

    args = parser.parse_args()

    # Local import to keep CLI entry-point fast and isolated from
    # the rest of the package.
    from lib.config_manager import create_config_manager

    if args.command == "init":
        config = create_config_manager()
        config.save_config()
        print("Configuration initialized successfully")

    elif args.command == "show":
        config = create_config_manager()
        if config.config_file.exists():
            print(config.config_file.read_text())
        else:
            print(f"No configuration file found at {config.config_file}")
            print("Run 'fplaunch config init' to create one")

    elif args.command == "block":
        if not args.value:
            parser.error("block command requires an app name")
        config = create_config_manager()
        config.add_to_blocklist(args.value)
        print(f"Blocked {args.value}")

    elif args.command == "unblock":
        if not args.value:
            parser.error("unblock command requires an app name")
        config = create_config_manager()
        config.remove_from_blocklist(args.value)
        print(f"Unblocked {args.value}")

    elif args.command == "list-presets":
        config = create_config_manager()
        presets = config.list_permission_presets()
        if presets:
            print("Available permission presets:")
            for preset in presets:
                print(f"  {preset}")
        else:
            print("No permission presets defined")

    elif args.command == "get-preset":
        if not args.value:
            parser.error("get-preset command requires a preset name")
        config = create_config_manager()
        permissions = config.get_permission_preset(args.value)
        if permissions:
            print(f"Permissions for preset '{args.value}':")
            for perm in permissions:
                print(f"  {perm}")
        else:
            print(f"Preset '{args.value}' not found", file=sys.stderr)
            sys.exit(1)


__all__ = ["main"]


if __name__ == "__main__":
    main()
