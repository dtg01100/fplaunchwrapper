#!/usr/bin/env python3
"""CLI systemd commands and groups."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

import click

from lib.cli_utils import console, console_err
from lib.cli_generation import import_handler
from lib.import_utils import safe_import

if TYPE_CHECKING:
    from click import Context

logger = logging.getLogger(__name__)


def _get_systemd_setup(ctx: "Context") -> Any:
    """Get a configured SystemdSetup instance."""
    SystemdSetup = safe_import("lib.systemd_setup", "SystemdSetup")
    if SystemdSetup is None:
        return None
    return SystemdSetup(
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )


@click.command(name="systemd-setup")
@click.argument("bin_dir", required=False)
@click.argument("wrapper_script", required=False)
@click.pass_context
def systemd_setup_cmd(
    ctx: "Context",
    bin_dir: str | None,
    wrapper_script: str | None,
) -> int:
    """Install/enable systemd units for automatic wrapper generation."""
    SystemdSetup = import_handler.require("lib.systemd_setup", "SystemdSetup")
    setup = SystemdSetup(
        bin_dir=bin_dir,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
        wrapper_script=wrapper_script,
    )
    try:
        if hasattr(setup, "run"):
            result = setup.run()
            return 0 if result == 0 else 1
        if hasattr(setup, "install_systemd_units"):
            result = setup.install_systemd_units()
            return 0 if result else 1
    except Exception as e:
        logger.exception("Systemd setup failed: %s", e)
        console_err.print(f"[red]Error:[/red] {e}")
        return 1
    console_err.print(
        "[red]Error:[/red] SystemdSetup has no valid method "
        "(neither 'run' nor 'install_systemd_units')"
    )
    return 1


@click.group(name="systemd", invoke_without_command=True)
@click.pass_context
def systemd_group(ctx: "Context") -> None:
    """Manage systemd user units (enable|disable|status|start|stop|restart|
    reload|logs|list|test)."""
    if ctx.invoked_subcommand is None:
        _run_systemd_setup(ctx, None, None)


def _run_systemd_setup(
    ctx: "Context",
    bin_dir: str | None = None,
    wrapper_script: str | None = None,
) -> int:
    """Underlying systemd setup implementation."""
    SystemdSetup = import_handler.require("lib.systemd_setup", "SystemdSetup")
    setup = SystemdSetup(
        bin_dir=bin_dir,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
        wrapper_script=wrapper_script,
    )
    try:
        if hasattr(setup, "run"):
            result = setup.run()
            return 0 if result == 0 else 1
        if hasattr(setup, "install_systemd_units"):
            result = setup.install_systemd_units()
            return 0 if result else 1
    except Exception as e:
        logger.exception("Systemd setup failed: %s", e)
        console_err.print(f"[red]Error:[/red] {e}")
        return 1
    console_err.print(
        "[red]Error:[/red] SystemdSetup has no valid method "
        "(neither 'run' nor 'install_systemd_units')"
    )
    return 1


@systemd_group.command(name="enable")
@click.pass_context
def systemd_enable(ctx: "Context") -> int:
    """Enable the systemd service for automatic wrapper generation."""
    setup = _get_systemd_setup(ctx)
    if setup is None:
        console_err.print("[red]Error:[/red] systemd_setup module not available")
        return 1
    return 0 if setup.install_systemd_units() else 1


@systemd_group.command(name="disable")
@click.option(
    "--yes",
    "-y",
    "assume_yes",
    is_flag=True,
    help="Assume yes to deleting systemd unit files (otherwise prompts on TTY)",
)
@click.pass_context
def systemd_disable(ctx: "Context", assume_yes: bool) -> int:
    """Disable the systemd service and remove its unit files."""
    setup = _get_systemd_setup(ctx)
    if setup is None:
        console_err.print("[red]Error:[/red] systemd_setup module not available")
        return 1
    if not assume_yes and not os.environ.get("FPWRAPPER_FORCE") and not click.confirm(
        "Disable systemd units and remove their unit files?",
        default=False,
        err=True,
    ):
        console.print("Disable cancelled.")
        return 1
    return 0 if setup.disable_systemd_units() else 1


@systemd_group.command(name="status")
@click.pass_context
def systemd_status(ctx: "Context") -> int:
    """Show status of the systemd service."""
    setup = _get_systemd_setup(ctx)
    if setup is None:
        console_err.print("[red]Error:[/red] systemd_setup module not available")
        return 1
    status = setup.check_systemd_status()
    console.print("[bold]fplaunch-wrapper.service:[/bold]")
    console.print(f"  Exists:   {status['service']['exists']}")
    console.print(f"  Enabled:  {status['service']['enabled']}")
    console.print(f"  Active:   {status['service']['active']}")
    console.print("[bold]fplaunch-wrapper.timer:[/bold]")
    console.print(f"  Exists:   {status['timer']['exists']}")
    console.print(f"  Enabled:  {status['timer']['enabled']}")
    console.print(f"  Active:   {status['timer']['active']}")
    return 0


def _systemctl_command(
    ctx: "Context", action: str, unit: str | None = "fplaunch-wrapper.timer"
) -> int:
    """Run a systemctl command with emit-mode awareness."""
    import subprocess

    emit_mode = ctx.obj.get("emit", False)
    if emit_mode:
        console.print(f"[yellow]EMIT: Would run systemctl {action}[/yellow]")
        return 0
    cmd = ["systemctl", "--user", action]
    if unit:
        cmd.append(unit)
    result = subprocess.run(cmd, check=False, timeout=30)
    return 0 if result.returncode == 0 else 1


@systemd_group.command(name="start")
@click.pass_context
def systemd_start(ctx: "Context") -> int:
    """Start the systemd service immediately."""
    return _systemctl_command(ctx, "start")


@systemd_group.command(name="stop")
@click.pass_context
def systemd_stop(ctx: "Context") -> int:
    """Stop the systemd service."""
    return _systemctl_command(ctx, "stop")


@systemd_group.command(name="restart")
@click.pass_context
def systemd_restart(ctx: "Context") -> int:
    """Restart the systemd service."""
    return _systemctl_command(ctx, "restart")


@systemd_group.command(name="reload")
@click.pass_context
def systemd_reload(ctx: "Context") -> int:
    """Reload systemd daemon configuration."""
    return _systemctl_command(ctx, "daemon-reload", unit=None)


@systemd_group.command(name="logs")
@click.pass_context
def systemd_logs(ctx: "Context") -> int:
    """View systemd service logs."""
    import subprocess

    emit_mode = ctx.obj.get("emit", False)
    if emit_mode:
        console.print("[yellow]EMIT: Would show systemd logs[/yellow]")
        return 0
    result = subprocess.run(
        ["journalctl", "--user", "-u", "fplaunch-wrapper.service", "-n", "50"],
        check=False,
        text=True,
        timeout=30,
    )
    if result.stdout:
        console.print(result.stdout)
    if result.returncode != 0 and result.stderr:
        console_err.print(result.stderr)
    return 0 if result.returncode == 0 else 1


@systemd_group.command(name="list")
@click.pass_context
def systemd_list(ctx: "Context") -> int:
    """List managed systemd units."""
    setup = _get_systemd_setup(ctx)
    if setup is None:
        console_err.print("[red]Error:[/red] systemd_setup module not available")
        return 1
    units = setup.list_all_units()
    if units:
        console.print("[bold]Managed systemd units:[/bold]")
        for unit in units:
            console.print(f"  {unit}")
    else:
        console.print("No fplaunchwrapper systemd units found")
    return 0


@systemd_group.command(name="test")
@click.option(
    "--emit",
    is_flag=True,
    help="Emit commands instead of executing (dry run)",
)
@click.pass_context
def systemd_test(ctx: "Context", emit: bool) -> int:
    """Test systemd configuration."""
    emit_mode = emit or ctx.obj.get("emit", False)
    if emit_mode:
        console.print("[yellow]EMIT: Would test systemd configuration[/yellow]")
        return 0
    setup = _get_systemd_setup(ctx)
    if setup is None:
        console_err.print("[red]Error:[/red] systemd_setup module not available")
        return 1
    status = setup.check_systemd_status()
    prerequisites_ok = setup.check_prerequisites()
    console.print("[bold]Systemd Configuration Test Results:[/bold]")
    console.print(f"  Prerequisites OK: {prerequisites_ok}")
    console.print(f"  Service exists:    {status['service']['exists']}")
    console.print(f"  Timer exists:       {status['timer']['exists']}")
    return 0
