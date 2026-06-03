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
from lib.cli_utils import console, console_err
from lib.cli_imports import build_manager, get_config_manager

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
    from lib.cli import run_command  # lazy import to allow test patching  # noqa: E501, F401

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


@click.command()
@click.argument("action", required=False)
@click.argument("value", required=False)
@click.pass_context
def config(ctx: "Context", action: Optional[str], value: Optional[str]) -> int:  # pylint: disable=W0613
    """Manage fplaunchwrapper configuration.

    \b
    Actions:
      show          Show current configuration (default)
      init          Initialize configuration file
      cron-interval Get or set cron interval (in hours)
    """
    cfg = get_config_manager()
    if not action or action == "show":
        config_path = cfg.config_file
        if config_path.exists():
            console.print(f"[bold]Configuration file:[/bold] {config_path}")
            content = config_path.read_text()
            console.print(content)
        else:
            console.print(
                f"[yellow]No configuration file found at {config_path}[/yellow]",
            )
            console.print("Run 'fplaunch config init' to create one")
        return 0
    if action == "init":
        cfg.save_config()
        console.print("[green]✓[/green] Configuration initialized")
        return 0
    if action == "cron-interval":
        if not value:
            interval = cfg.get_cron_interval()
            console.print(f"Current cron interval: [bold]{interval}[/bold] hours")
        else:
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
    console_err.print(f"[red]Error:[/red] Unknown action: {action}")
    console_err.print("Valid actions: show, init, cron-interval")
    raise SystemExit(1)
