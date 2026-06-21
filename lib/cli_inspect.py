#!/usr/bin/env python3
"""CLI inspect commands: info, search, discover, files, manifest, config.

These commands are read-only / diagnostic in nature: they inspect the
current state of wrappers, configuration, and Flatpak installs.
"""

from __future__ import annotations

import json as json_module
import logging
from typing import TYPE_CHECKING, Optional

import click
from lib.cli_utils import console, console_err, run_command
from lib.cli_imports import build_config_manager, build_manager

if TYPE_CHECKING:
    from click import Context

logger = logging.getLogger(__name__)


@click.command()
@click.argument("app_name")
@click.pass_context
def info(ctx: "Context", app_name: str) -> int:
    """Show information about a wrapper."""
    manager = build_manager(ctx)
    success = manager.show_info(app_name)
    return 0 if success else 1


@click.command()
@click.argument("query", required=False)
@click.pass_context
def search(ctx: "Context", query: Optional[str]) -> int:  # pylint: disable=W0613
    """Search or discover wrappers. Alias: discover."""
    manager = build_manager(ctx)
    # Minimal behavior: call discover_features if available, otherwise list wrappers
    if hasattr(manager, "discover_features"):
        manager.discover_features()
        return 0
    manager.display_wrappers()
    return 0


@click.command(name="discover")
@click.argument("query", required=False)
@click.pass_context
def discover(ctx: "Context", query: Optional[str]) -> int:
    """Discover wrapper capabilities (alias for search)."""
    return int(ctx.invoke(search, query=query))


@click.command(name="files")  # pylint: disable=R0913
@click.argument("app_name", required=False)
@click.option("--all", "show_all", is_flag=True, help="Show all file types")
@click.option("--wrappers", is_flag=True, help="Show only wrapper files")
@click.option("--prefs", is_flag=True, help="Show only preference files")
@click.option("--env", is_flag=True, help="Show only environment files")
@click.option("--paths", is_flag=True, help="Output raw paths (machine-parseable)")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def files(
    ctx: "Context",
    app_name: Optional[str],
    show_all: bool,
    wrappers: bool,
    prefs: bool,
    env: bool,
    paths: bool,
    json_output: bool,
) -> int:
    """Display all files managed by fplaunchwrapper for a given application.

    Without APP_NAME, lists all managed files across all apps.
    """
    manager = build_manager(ctx)

    file_type = None
    if wrappers:
        file_type = "wrappers"
    elif prefs:
        file_type = "prefs"
    elif env:
        file_type = "env"
    elif show_all:
        file_type = "all"

    managed_files = manager.list_managed_files(app_name, file_type)

    if not managed_files:
        if app_name:
            console.print(f"[yellow]No managed files found for {app_name}[/yellow]")
        else:
            console.print("[yellow]No managed files found[/yellow]")
        return 0

    if json_output:
        console.print(json_module.dumps(managed_files, indent=2))
    elif paths:
        for app_files in managed_files.values():
            for file_info in app_files:
                console.print(file_info["path"])
    else:
        for app, files_list in managed_files.items():
            if app == "_aliases":
                for file_info in files_list:
                    console.print(f"Aliases:    {file_info['path']}")
                continue

            if app_name:
                console.print(f"[bold]Files for {app}:[/bold]")
                for file_info in files_list:
                    file_type_display = file_info["type"].capitalize()
                    console.print(f"  {file_type_display:<12} {file_info['path']}")
            else:
                console.print(f"\n[bold]{app}:[/bold]")
                for file_info in files_list:
                    file_type_display = file_info["type"].capitalize()
                    console.print(f"  {file_type_display:<12} {file_info['path']}")

    return 0


@click.command(name="manifest")
@click.argument("app_name")
@click.option("--emit", is_flag=True, help="Emit only (dry run)")
@click.pass_context
def manifest(ctx: "Context", app_name: str, emit: bool) -> int:
    """Show manifest information for a Flatpak application."""

    if not app_name:
        console.print("[red]Error:[/red] APP_NAME is required")
        return 1

    emit_mode = emit or ctx.obj.get("emit", False)

    if emit_mode:
        console.print(f"[yellow]EMIT: Would show manifest for {app_name}[/yellow]")
        return 0

    try:
        result = run_command(
            ["flatpak", "info", "--show-manifest", app_name],
            f"Getting manifest for {app_name}",
            show_output=True,
            emit_mode=emit_mode,
        )
        if result is None or result.returncode != 0:
            console_err.print(
                f"[red]Error:[/red] Failed to get manifest for {app_name}",
            )
            raise click.exceptions.Exit(code=1)
        return 0
    except click.exceptions.Exit:
        raise
    except Exception as e:  # pylint: disable=W0718
        logger.exception("Manifest command failed for %s: %s", app_name, e)
        console_err.print(f"[red]Error:[/red] {e}")
        return 1


@click.group(name="config", invoke_without_command=True)
@click.pass_context
def config(ctx: "Context") -> int:  # pylint: disable=W0613
    """Manage fplaunchwrapper configuration.

    \b
    Subcommands:
      show            Show current configuration (default)
      init            Initialize configuration file
      cron-interval   Get or set cron interval (in hours)
      block APP       Block application from being wrapped
      unblock APP     Unblock application
      list-presets    List permission presets
      get-preset NAME Get permissions for a specific preset
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(config_show)
    return 0


@config.command("show")
@click.pass_context
def config_show(ctx: "Context") -> int:
    """Show the current configuration file contents."""
    cfg = build_config_manager(ctx)
    config_path = cfg.config_file
    if config_path.exists():
        console.print(f"[bold]Configuration file:[/bold] {config_path}")
        console.print(config_path.read_text())
    else:
        console.print(
            f"[yellow]No configuration file found at {config_path}[/yellow]",
        )
        console.print("Run 'fplaunch config init' to create one")
    return 0


@config.command("init")
@click.pass_context
def config_init(ctx: "Context") -> int:
    """Initialize the configuration file."""
    cfg = build_config_manager(ctx)
    cfg.save_config()
    console.print("[green]✓[/green] Configuration initialized")
    return 0


@config.command("cron-interval")
@click.argument("value", required=False)
@click.pass_context
def config_cron_interval(ctx: "Context", value: Optional[str]) -> int:
    """Get or set the cron interval (in hours)."""
    cfg = build_config_manager(ctx)
    if not value:
        interval = cfg.get_cron_interval()
        console.print(f"Current cron interval: [bold]{interval}[/bold] hours")
        return 0
    try:
        interval = int(value)
    except ValueError:
        console_err.print(f"[red]Error:[/red] Invalid interval value: {value}")
        return 1
    cfg.set_cron_interval(interval)
    console.print(
        f"[green]✓[/green] Cron interval set to [bold]{interval}[/bold] hours",
    )
    return 0


@config.command("block")
@click.argument("app_id")
@click.pass_context
def config_block(ctx: "Context", app_id: str) -> int:
    """Block an application from being wrapped."""
    cfg = build_config_manager(ctx)
    cfg.add_to_blocklist(app_id)
    console.print(f"[green]✓[/green] Blocked {app_id}")
    return 0


@config.command("unblock")
@click.argument("app_id")
@click.pass_context
def config_unblock(ctx: "Context", app_id: str) -> int:
    """Unblock a previously blocked application."""
    cfg = build_config_manager(ctx)
    cfg.remove_from_blocklist(app_id)
    console.print(f"[green]✓[/green] Unblocked {app_id}")
    return 0


@config.command("list-presets")
@click.pass_context
def config_list_presets(ctx: "Context") -> int:
    """List all permission presets."""
    cfg = build_config_manager(ctx)
    presets = cfg.list_permission_presets()
    if presets:
        console.print("Available permission presets:")
        for preset in presets:
            console.print(f"  {preset}")
    else:
        console.print("No permission presets defined")
    return 0


@config.command("get-preset")
@click.argument("preset_name")
@click.pass_context
def config_get_preset(ctx: "Context", preset_name: str) -> int:
    """Get the permissions for a specific preset."""
    cfg = build_config_manager(ctx)
    permissions = cfg.get_permission_preset(preset_name)
    if permissions is None:
        console_err.print(
            f"[red]Error:[/red] Preset '{preset_name}' not found",
        )
        return 1
    console.print(f"Permissions for preset '{preset_name}':")
    for perm in permissions:
        console.print(f"  {perm}")
    return 0
