#!/usr/bin/env python3
"""CLI profiles commands and groups."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import click

# Use shared import_handler from cli_generation (imported via cli_commands)
from lib.cli_generation import import_handler
from lib.cli_utils import console, console_err

if TYPE_CHECKING:
    from click import Context

logger = logging.getLogger(__name__)


@click.group(name="profiles", invoke_without_command=True)
@click.pass_context
def profiles_group(ctx: "Context") -> None:
    """Manage configuration profiles (list/current/create/switch/export/import)."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(profiles_list)


@profiles_group.command(name="list")
@click.pass_context
def profiles_list(ctx: "Context") -> int:
    """List available profiles."""
    create_config_manager = import_handler.require(
        "lib.config_manager",
        "create_config_manager",
    )
    cfg = create_config_manager()
    profiles = cfg.list_profiles()
    active = cfg.get_active_profile()
    for profile in profiles:
        if profile == active:
            console.print(f"[bold green]* {profile}[/bold green]")
        else:
            console.print(f"  {profile}")
    return 0


@profiles_group.command(name="create")
@click.argument("profile_name")
@click.option("--copy-from", help="Copy configuration from existing profile")
@click.pass_context
def profiles_create(ctx: "Context", profile_name: str, copy_from: str | None) -> int:
    """Create a new profile."""
    create_config_manager = import_handler.require(
        "lib.config_manager",
        "create_config_manager",
    )
    cfg = create_config_manager()
    if cfg.create_profile(profile_name, copy_from):
        console.print(f"[green]Created profile:[/green] {profile_name}")
        return 0
    console_err.print(
        f"[red]Error:[/red] Could not create profile '{profile_name}' "
        "(may already exist or invalid name)",
    )
    return 1


@profiles_group.command(name="switch")
@click.argument("profile_name")
@click.pass_context
def profiles_switch(ctx: "Context", profile_name: str) -> int:
    """Switch to a profile."""
    create_config_manager = import_handler.require(
        "lib.config_manager",
        "create_config_manager",
    )
    cfg = create_config_manager()
    if cfg.switch_profile(profile_name):
        console.print(f"[green]Switched to profile:[/green] {profile_name}")
        return 0
    console_err.print(
        f"[red]Error:[/red] Could not switch to profile '{profile_name}' (profile may not exist)",
    )
    return 1


@profiles_group.command(name="current")
@click.pass_context
def profiles_current(ctx: "Context") -> int:
    """Show current profile."""
    create_config_manager = import_handler.require(
        "lib.config_manager",
        "create_config_manager",
    )
    cfg = create_config_manager()
    active = cfg.get_active_profile()
    console.print(f"Current profile: [bold]{active}[/bold]")
    return 0


@profiles_group.command(name="export")
@click.argument("profile_name")
@click.argument("output_file", required=False)
@click.pass_context
def profiles_export(ctx: "Context", profile_name: str, output_file: str | None) -> int:
    """Export a profile to a file."""
    create_config_manager = import_handler.require(
        "lib.config_manager",
        "create_config_manager",
    )
    cfg = create_config_manager()
    export_path = Path(output_file) if output_file else Path(f"{profile_name}.toml")
    if cfg.export_profile(profile_name, export_path):
        console.print(
            f"[green]Exported profile '{profile_name}' to {export_path}[/green]",
        )
        return 0
    console_err.print(
        f"[red]Error:[/red] Could not export profile '{profile_name}'",
    )
    return 1


@profiles_group.command(name="import")
@click.argument("input_file")
@click.argument("profile_name", required=False)
@click.pass_context
def profiles_import(ctx: "Context", input_file: str, profile_name: str | None) -> int:
    """Import a profile from a file."""
    create_config_manager = import_handler.require(
        "lib.config_manager",
        "create_config_manager",
    )
    cfg = create_config_manager()
    import_path = Path(input_file)
    name = profile_name or import_path.stem
    if cfg.import_profile(name, import_path):
        console.print(f"[green]Imported profile '{name}' from {import_path}[/green]")
        return 0
    console_err.print(
        f"[red]Error:[/red] Could not import profile from '{input_file}'",
    )
    return 1
