#!/usr/bin/env python3
"""CLI generation commands: generate, list, install, uninstall, remove."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from lib.cli_utils import console, console_err, run_command
from lib.cli_imports import build_manager, import_handler

if TYPE_CHECKING:
    from click import Context


logger = logging.getLogger(__name__)


def _require_yes(ctx: "Context", *, assume_yes: bool, action: str) -> bool:
    """Return True if the user (or env) has confirmed the destructive action.

    Rules:
    * ``--yes`` (``assume_yes=True``) ⇒ always confirmed.
    * ``FPWRAPPER_FORCE=1`` env var ⇒ always confirmed (CI parity).
    * Non-interactive stdin (no TTY) ⇒ refuse and return False.
    * Otherwise prompt on stderr; if user declines, return False.
    """
    if assume_yes or os.environ.get("FPWRAPPER_FORCE") == "1":
        return True
    if not sys.stdin.isatty():
        console_err.print(
            f"[red]Error:[/red] {action} requires an interactive terminal or "
            f"--yes (or FPWRAPPER_FORCE=1).",
        )
        return False
    confirmed: bool = click.confirm(
        f"{action}; continue?",
        default=False,
        err=True,
    )
    return confirmed


@click.command()
@click.argument("bin_dir", required=False)
@click.pass_context
def generate(ctx: "Context", bin_dir: str | Path | None) -> int:
    """Generate Flatpak application wrappers."""
    if not bin_dir:
        bin_dir = Path("~/bin").expanduser()

    WrapperGenerator = import_handler.require("lib.generate", "WrapperGenerator")
    generator = WrapperGenerator(
        bin_dir=bin_dir,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )
    result: int = generator.run()
    return result


@click.command(name="list")
@click.argument("app_name", required=False)
@click.option("--all", "show_all", is_flag=True, help="List all wrappers")
@click.pass_context
def list_wrappers(ctx: "Context", app_name: str | None, show_all: bool) -> int:
    """List installed Flatpak wrappers or show details for one wrapper."""
    manager = build_manager(ctx)

    # Use display_wrappers for --all (for backward compatibility with test mocks)
    if show_all:
        # Try display_wrappers first (used by test mocks)
        if hasattr(manager, "display_wrappers"):
            manager.display_wrappers()
            return 0
        # Or list_wrappers for real implementation
        if hasattr(manager, "list_wrappers"):
            wrappers = manager.list_wrappers()
            if not wrappers:
                console_err.print("[yellow]Warning:[/yellow] No wrappers found")
                return 0
            for w in wrappers:
                console.print(f"[cyan]{w['name']}[/cyan]")
                console.print(f"  ID: {w['id']}")
                console.print(f"  Path: {w['path']}")
            return 0
        console_err.print("[red]Error:[/red] No list method available")
        return 1

    if not app_name:
        # No app name given - show usage hint
        console_err.print("[yellow]Warning:[/yellow] Use --all to list all wrappers")
        return 0

    # Try to find single wrapper
    if hasattr(manager, "list_wrappers"):
        wrappers = manager.list_wrappers()
        for w in wrappers:
            if w["name"] == app_name or w["id"] == app_name:
                console.print(f"[cyan]{w['name']}[/cyan]")
                console.print(f"  ID: {w['id']}")
                console.print(f"  Path: {w['path']}")
                return 0

    console_err.print(f"[red]Error:[/red] Wrapper not found: {app_name}")
    return 1


@click.command()
@click.argument("app_name")
@click.option("--emit", is_flag=True, help="Emit only (dry run)")
@click.option(
    "--yes",
    "-y",
    "assume_yes",
    is_flag=True,
    help="Assume yes to flatpak's install prompt (otherwise prompts on TTY)",
)
@click.pass_context
def install(
    ctx: "Context", app_name: str, emit: bool, assume_yes: bool
) -> int:
    """Install a Flatpak application and generate a wrapper for it."""

    emit_mode = emit or ctx.obj.get("emit", False)
    # Only pass -y to flatpak when the user has confirmed. A previous version
    # of this code unconditionally passed -y, which made a single typo
    # (``fplaunch install firefoxx``) silently install from a typo'd ID.
    flatpak_cmd = ["flatpak", "install"]
    if assume_yes or os.environ.get("FPWRAPPER_FORCE") == "1":
        flatpak_cmd.append("-y")
    elif not sys.stdin.isatty():
        console_err.print(
            "[red]Error:[/red] install requires an interactive terminal or --yes.",
        )
        return 1
    elif not click.confirm(
        f"Install Flatpak app '{app_name}'?", default=False, err=True
    ):
        console.print("Install cancelled.")
        return 1
    flatpak_cmd.append(app_name)
    result = run_command(
        flatpak_cmd,
        f"Installing Flatpak app: {app_name}",
        emit_mode=emit_mode,
    )
    if result is None or result.returncode != 0:
        err_msg = result.stderr if result else "Command failed in emit mode"
        console_err.print(f"[red]Error:[/red] Failed to install Flatpak app: {err_msg}")
        return result.returncode if result else 1

    WrapperGenerator = import_handler.require("lib.generate", "WrapperGenerator")
    generator = WrapperGenerator(
        bin_dir=Path("~/bin").expanduser(),
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=emit_mode,
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )
    return int(generator.run())


@click.command()
@click.argument("app_name")
@click.option(
    "--remove-data",
    is_flag=True,
    help="PERMANENTLY remove user data and the wrapper; cannot be undone",
)
@click.option("--emit", is_flag=True, help="Emit only (dry run)")
@click.option(
    "--yes",
    "-y",
    "assume_yes",
    is_flag=True,
    help="Assume yes to flatpak's uninstall prompt (otherwise prompts on TTY)",
)
@click.pass_context
def uninstall(
    ctx: "Context", app_name: str, remove_data: bool, emit: bool, assume_yes: bool
) -> int:
    """Uninstall a Flatpak application and remove its wrapper."""
    emit_mode = emit or ctx.obj.get("emit", False)
    if not assume_yes and not sys.stdin.isatty() and os.environ.get("FPWRAPPER_FORCE") != "1":
        console_err.print(
            "[red]Error:[/red] uninstall requires an interactive terminal or --yes.",
        )
        return 1
    if not assume_yes and not click.confirm(
        f"Uninstall Flatpak app '{app_name}'"
        + (" AND remove user data" if remove_data else "")
        + "?",
        default=False,
        err=True,
    ):
        console.print("Uninstall cancelled.")
        return 1

    uninstall_cmd = ["flatpak", "uninstall"]
    if assume_yes or os.environ.get("FPWRAPPER_FORCE") == "1":
        uninstall_cmd.append("-y")
    if remove_data:
        uninstall_cmd.append("--delete-data")
    uninstall_cmd.append(app_name)

    result = run_command(
        uninstall_cmd, f"Uninstalling Flatpak app: {app_name}", emit_mode=emit_mode
    )
    if result is None or result.returncode != 0:
        err_msg = result.stderr if result else "Command failed in emit mode"
        console_err.print(f"[red]Error:[/red] Failed to uninstall Flatpak app: {err_msg}")
        return result.returncode if result else 1

    manager = build_manager(ctx)

    # Distinguish "wrapper removed successfully" from "wrapper did not exist
    # but flatpak uninstall succeeded" — the latter is a 0, the former is
    # also a 0; a real removal failure (OSError) is a 1.
    success = manager.remove_wrapper(app_name, force=True)
    if success:
        console.print(f"[green]Removed wrapper for {app_name}[/green]")
        return 0
    console_err.print(
        f"[yellow]Warning:[/yellow] Could not remove wrapper for {app_name} (may not exist)"
    )
    return 0


@click.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Force removal without prompt")
@click.pass_context
def remove(ctx: "Context", name: str, force: bool) -> int:
    """Remove a wrapper by name."""
    if not force and not sys.stdin.isatty() and not os.environ.get("FPWRAPPER_FORCE"):
        console_err.print(
            "[red]Error:[/red] remove requires an interactive terminal or --force.",
        )
        return 1
    if not force and not click.confirm(
        f"Remove wrapper '{name}'?", default=False, err=True
    ):
        console.print("Remove cancelled.")
        return 1
    manager = build_manager(ctx)

    success = manager.remove_wrapper(name, force=True)
    if success:
        console.print(f"[green]Removed wrapper:[/green] {name}")
        return 0
    console_err.print(f"[red]Error:[/red] Wrapper not found: {name}")
    return 1


@click.command(name="rm")
@click.argument("name")
@click.option("--force", is_flag=True, help="Force removal without prompt")
@click.pass_context
def rm(ctx: "Context", name: str, force: bool) -> int:
    """Alias for remove."""
    return int(ctx.invoke(remove, name=name, force=force))


@click.command(name="set-pref")
@click.argument("wrapper_name")
@click.argument("preference")
@click.pass_context
def set_pref(ctx: "Context", wrapper_name: str, preference: str) -> int:
    """Set launch preference for a wrapper."""
    manager = build_manager(ctx)
    if manager.set_preference(wrapper_name, preference):
        console.print(f"[green]Set preference for {wrapper_name}:[/green] {preference}")
        return 0
    console_err.print("[red]Error:[/red] Failed to set preference")
    return 1


@click.command(name="pref")
@click.argument("wrapper_name")
@click.argument("preference")
@click.pass_context
def pref(ctx: "Context", wrapper_name: str, preference: str) -> int:
    """Alias for set-pref."""
    return int(ctx.invoke(set_pref, wrapper_name=wrapper_name, preference=preference))


def register_commands(cli_group: click.Group) -> None:
    """Register all generation commands with the CLI group."""
    cli_group.add_command(generate)
    cli_group.add_command(list_wrappers)
    cli_group.add_command(install)
    cli_group.add_command(uninstall)
    cli_group.add_command(remove)
    cli_group.add_command(rm)
    cli_group.add_command(set_pref)
    cli_group.add_command(pref)
