#!/usr/bin/env python3
"""CLI commands for fplaunchwrapper.

This module defines the main Click CLI group and registers commands from
submodules. Commands are split into logical groups:
- cli_generation: generate, list, install, uninstall, remove, pref commands
- cli_system: launch, cleanup, clean, monitor commands
- cli_systemd: systemd-setup and systemd-* commands
- cli_profiles: profiles group and subcommands
- cli_presets: presets group and subcommands
- cli_inspect: info, search/discover, files, manifest, config commands
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

import click
from lib.cli_utils import console, console_err

try:
    from . import __version__ as FPLAUNCH_VERSION
except ImportError:
    FPLAUNCH_VERSION = "unknown"

logger = logging.getLogger(__name__)

# Import all command functions directly from submodules
from lib.cli_generation import (  # noqa: E402
    generate,
    list_wrappers,
    install,
    uninstall,
    remove,
    rm,
    set_pref,
    pref,
)
from lib.cli_system import (  # noqa: E402
    launch,
    cleanup,
    clean,
    monitor,
)
from lib.cli_systemd import (  # noqa: E402
    systemd_setup_cmd,
    systemd_group,
)
from lib.cli_profiles import (  # noqa: E402
    profiles_group,
)
from lib.cli_presets import (  # noqa: E402
    presets_group,
)
from lib.cli_inspect import (  # noqa: E402
    info,
    search,
    discover,
    files,
    manifest,
    config,
)
# Re-export utilities for backward compatibility with tests
from lib.cli_utils import run_command  # noqa: E402, F401, W0611
from lib.cli_generation import import_handler  # noqa: E402, F401, W0611
@click.group(invoke_without_command=True)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config-dir", help="Override config directory")
@click.option("--bin-dir", help="Override bin directory (where wrappers are installed)")
@click.option(
    "--emit",
    is_flag=True,
    help="Emit mode: show commands without executing (dry run)",
)
@click.option(
    "--emit-verbose",
    is_flag=True,
    help="Verbose emit mode: show detailed command info",
)
@click.version_option(version=FPLAUNCH_VERSION, prog_name="fplaunch")
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    config_dir: str | None,
    bin_dir: str | None,
    emit: bool,
    emit_verbose: bool,
) -> None:
    """Main entry point for fplaunchwrapper CLI (Click-based)."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_dir"] = config_dir
    ctx.obj["bin_dir"] = bin_dir
    ctx.obj["emit"] = emit
    ctx.obj["emit_verbose"] = emit_verbose
    # Show help only when CLI is invoked with no subcommand
    if not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


# Register all commands with the CLI group
cli.add_command(generate)
cli.add_command(list_wrappers)
cli.add_command(install)
cli.add_command(uninstall)
cli.add_command(remove)
cli.add_command(rm)
cli.add_command(set_pref)
cli.add_command(pref)
cli.add_command(launch)
cli.add_command(cleanup)
cli.add_command(clean)
cli.add_command(monitor)
cli.add_command(systemd_setup_cmd)
cli.add_command(systemd_group)
cli.add_command(profiles_group)
cli.add_command(presets_group)
cli.add_command(info)
cli.add_command(search)
cli.add_command(discover)
cli.add_command(files)
cli.add_command(manifest)
cli.add_command(config)


def main(argv: Optional[list[str]] = None) -> int:
    """Entrypoint used by console scripts. Dispatch to Click."""
    argv = argv if argv is not None else sys.argv[1:]
    try:
        result = cli.main(args=argv, prog_name="fplaunch", standalone_mode=False)
        return result if isinstance(result, int) else 0
    except SystemExit as e:
        code = e.code
        if isinstance(code, int):
            return code
        return 1
    except Exception as e:
        logger.exception("CLI main error: %s", e)
        console_err.print(f"[red]Error:[/red] {e}")
        return 1
