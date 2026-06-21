#!/usr/bin/env python3
"""CLI presets commands and groups."""

from __future__ import annotations

import click

from lib.cli_imports import build_config_manager, console, console_err


@click.group(name="presets", invoke_without_command=True)
@click.pass_context
def presets_group(ctx: "click.Context") -> None:
    """Manage permission presets (list/get/add/remove)."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(presets_list)


@presets_group.command(name="list")
@click.pass_context
def presets_list(ctx: "click.Context") -> int:  # pylint: disable=W0613
    """List available permission presets."""
    cfg = build_config_manager(ctx)
    presets = cfg.list_permission_presets()
    if presets:
        console.print("Available presets:")
        for preset in presets:
            console.print(f"  [green]{preset}[/green]")
    else:
        console.print("No custom presets defined")
    return 0


@presets_group.command(name="get")
@click.argument("preset_name", required=False)
@click.pass_context
def presets_get(ctx: "click.Context", preset_name) -> int:  # pylint: disable=W0613
    """Get a permission preset."""
    if not preset_name:
        raise click.UsageError("PRESET_NAME is required")

    cfg = build_config_manager(ctx)
    permissions = cfg.get_permission_preset(preset_name)
    if permissions is None:
        console_err.print(f"[red]Error:[/red] Preset '{preset_name}' not found")
        return 1

    console.print(f"[yellow]Preset {preset_name}:[/yellow]")
    for perm in permissions:
        console.print(f"  {perm}")
    return 0


@presets_group.command(name="add")
@click.argument("preset_name")
@click.option("-p", "--permission", multiple=True, help="Add a permission")
@click.pass_context
def presets_add(ctx: "click.Context", preset_name: str, permission: tuple[str, ...]) -> int:  # pylint: disable=W0613  # noqa: E501
    """Add a new permission preset."""
    if not permission:
        console_err.print("[red]Error:[/red] At least one permission is required")
        return 1

    cfg = build_config_manager(ctx)
    cfg.add_permission_preset(preset_name, list(permission))
    console.print(f"[green]Added preset:[/green] {preset_name}")
    return 0


@presets_group.command(name="remove")
@click.argument("preset_name")
@click.pass_context
def presets_remove(ctx, preset_name):
    """Remove a permission preset."""
    cfg = build_config_manager(ctx)
    if cfg.remove_permission_preset(preset_name):
        console.print(f"[green]Removed preset:[/green] {preset_name}")
        return 0
    console_err.print(f"[red]Error:[/red] Preset '{preset_name}' not found")
    return 1
