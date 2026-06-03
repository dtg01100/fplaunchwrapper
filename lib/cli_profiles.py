#!/usr/bin/env python3
"""CLI profiles commands and groups."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import click
from lib.cli_imports import console, console_err, get_config_manager

if TYPE_CHECKING:
    from click import Context

logger = logging.getLogger(__name__)


@click.group(name="profiles", invoke_without_command=True)
@click.pass_context
def profiles_group(ctx: "Context") -> None:  # pylint: disable=W0613
    """Manage configuration profiles (list/current/create/switch/export/import)."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(profiles_list)


@profiles_group.command(name="list")
@click.pass_context
def profiles_list(ctx: "Context") -> int:  # pylint: disable=W0613
    """List available profiles."""
    cfg = get_config_manager()
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
def profiles_create(ctx: "Context", profile_name: str, copy_from: str | None) -> int:  # pylint: disable=W0613
    """Create a new profile."""
    cfg = get_config_manager()
    if profile_name in cfg.list_profiles():
        console_err.print(f"[red]Error:[/red] Profile '{profile_name}' already exists")
        return 1
    try:
        if copy_from:
            if copy_from not in cfg.list_profiles():
                console_err.print(f"[red]Error:[/red] Profile '{copy_from}' not found")
                return 1
        cfg.create_profile(profile_name, copy_from=copy_from)
        console.print(f"[green]Created profile:[/green] {profile_name}")
        return 0
    except Exception as e:  # pylint: disable=W0718
        logger.exception("Profile command failed: %s", e)
        console_err.print(f"[red]Error:[/red] {e}")
        return 1


@profiles_group.command(name="switch")
@click.argument("profile_name")
@click.pass_context
def profiles_switch(ctx: "Context", profile_name: str) -> int:  # pylint: disable=W0613
    """Switch to a profile."""
    cfg = get_config_manager()
    if profile_name not in cfg.list_profiles():
        console_err.print(f"[red]Error:[/red] Profile '{profile_name}' not found")
        return 1
    try:
        cfg.switch_profile(profile_name)
        console.print(f"[green]Switched to profile:[/green] {profile_name}")
        return 0
    except Exception as e:  # pylint: disable=W0718
        logger.exception("Profile command failed: %s", e)
        console_err.print(f"[red]Error:[/red] {e}")
        return 1


@profiles_group.command(name="current")
@click.pass_context
def profiles_current(ctx: "Context") -> int:  # pylint: disable=W0613
    """Show current profile."""
    cfg = get_config_manager()
    current = cfg.get_active_profile()
    console.print(f"Current profile: [bold]{current}[/bold]")
    return 0


@profiles_group.command(name="export")
@click.argument("profile_name")
@click.argument("output_file", required=False)
@click.pass_context
def profiles_export(ctx: "Context", profile_name: str, output_file: str | None) -> int:  # pylint: disable=W0613
    """Export a profile to a file."""
    cfg = get_config_manager()
    if profile_name not in cfg.list_profiles():
        console_err.print(f"[red]Error:[/red] Profile '{profile_name}' not found")
        return 1
    export_path = Path(output_file) if output_file else Path(f"{profile_name}.toml")
    try:
        cfg.export_profile(profile_name, export_path)
        console.print(f"[green]Exported profile:[/green] {profile_name} to {export_path}")
        return 0
    except Exception as e:  # pylint: disable=W0718
        logger.exception("Profile command failed: %s", e)
        console_err.print(f"[red]Error:[/red] {e}")
        return 1


@profiles_group.command(name="import")
@click.argument("input_file")
@click.argument("profile_name", required=False)
@click.pass_context
def profiles_import(ctx: "Context", input_file: str, profile_name: str | None) -> int:  # pylint: disable=W0613
    """Import a profile from a file."""
    cfg = get_config_manager()
    import_path = Path(input_file)
    name = profile_name or import_path.stem
    if name in cfg.list_profiles():
        console_err.print(f"[red]Error:[/red] Profile '{name}' already exists")
        return 1
    try:
        cfg.import_profile(name, import_path)
        console.print(f"[green]Imported profile:[/green] {name} from {import_path}")
        return 0
    except Exception as e:  # pylint: disable=W0718
        logger.exception("Profile command failed: %s", e)
        console_err.print(f"[red]Error:[/red] {e}")
        return 1
