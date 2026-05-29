#!/usr/bin/env python3
"""CLI system commands: launch, cleanup, clean, monitor."""

from __future__ import annotations

from pathlib import Path

import click
from lib.cli_utils import console, console_err
from lib.cli_generation import import_handler


@click.command()
@click.argument("app_name")
@click.option(
    "--hook-failure",
    type=click.Choice(["abort", "warn", "ignore"]),
    default=None,
    help="Override hook failure mode for this launch (abort, warn, or ignore)",
)
@click.option(
    "--abort-on-hook-failure",
    is_flag=True,
    default=False,
    help="Abort launch if any hook fails (shorthand for --hook-failure abort)",
)
@click.option(
    "--ignore-hook-failure",
    is_flag=True,
    default=False,
    help="Ignore hook failures silently (shorthand for --hook-failure ignore)",
)
@click.pass_context
def launch(
    ctx: click.Context,
    app_name: str,
    hook_failure: str | None,
    abort_on_hook_failure: bool,
    ignore_hook_failure: bool,
) -> int:
    """Launch a Flatpak application via its wrapper."""
    AppLauncher = import_handler.require("lib.launch", "AppLauncher")
    resolved_hook_failure = hook_failure
    if abort_on_hook_failure:
        resolved_hook_failure = "abort"
    elif ignore_hook_failure:
        resolved_hook_failure = "ignore"

    launcher = AppLauncher(
        app_name,
        config_dir=ctx.obj.get("config_dir"),
        bin_dir=ctx.obj.get("bin_dir"),
        hook_failure_mode=resolved_hook_failure,
    )
    return 0 if launcher.launch() else 1


@click.command()
@click.pass_context
def cleanup(ctx: click.Context) -> int:
    """Clean up orphaned wrapper files and artifacts."""
    from lib.paths import resolve_bin_dir

    config_dir_str = ctx.obj.get("config_dir", "~/.config/fplaunchwrapper")
    try:
        config_dir = Path(config_dir_str).expanduser()
    except Exception:
        config_dir = Path.home() / ".config" / "fplaunchwrapper"
    try:
        bin_dir = resolve_bin_dir(explicit_dir=None, config_dir=config_dir)
    except Exception:
        bin_dir = Path.home() / "bin"
    if bin_dir is None:
        bin_dir = Path.home() / "bin"
    WrapperCleanup = import_handler.require("lib.cleanup", "WrapperCleanup")
    cleanup_manager = WrapperCleanup(bin_dir=str(bin_dir))
    return int(cleanup_manager.run())


@click.command(name="clean")
@click.pass_context
def clean(ctx: click.Context) -> int:
    """Clean up orphaned wrapper files and artifacts (alias for cleanup)."""
    return int(ctx.invoke(cleanup))


@click.command()
@click.option("--daemon", is_flag=True, help="Run in daemon mode (background)")
@click.pass_context
def monitor(ctx: click.Context, daemon: bool) -> int:  # pylint: disable=W0613
    """Start Flatpak monitoring daemon (Python backend)."""
    if ctx.obj.get("emit", False):
        console.print(
            "[yellow]EMIT: Would start Flatpak monitor (no-op in emit mode)[/yellow]",
        )
        return 0

    # Always use daemon mode to avoid blocking in test environments
    # The service runs in background and handles events
    monitor_main = import_handler.require("lib.flatpak_monitor", "main")
    monitor_main(daemon=True, skip_parse=True)
    return 0


def register_commands(cli_group: click.Group) -> None:
    """Register all system commands with the CLI group."""
    cli_group.add_command(launch)
    cli_group.add_command(cleanup)
    cli_group.add_command(clean)
    cli_group.add_command(monitor)
