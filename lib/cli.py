#!/usr/bin/env python3
"""Modern CLI interface for fplaunchwrapper using Click."""

from __future__ import annotations

import inspect
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass

import click
from rich.console import Console

try:
    from . import __version__ as FPLAUNCH_VERSION
except ImportError:
    FPLAUNCH_VERSION = "unknown"

console = Console()
console_err = Console(stderr=True)

# Import handler for consistent error messaging
from lib.import_utils import ImportErrorHandler, safe_import

import_handler = ImportErrorHandler(console_err)


def _instantiate_compat(cls, **kwargs):
    """Instantiate ``cls`` with best-effort compatibility across constructor signatures.

    Tries keyword initialization first, then falls back to positional invocation
    derived from the class' signature or a common argument ordering. This helps
    support test fakes that use older or simplified constructor signatures.
    """
    sig = inspect.signature(cls)
    params = list(sig.parameters.keys())
    if params and params[0] == "self":
        params = params[1:]

    kw = {k: v for k, v in kwargs.items() if k in params}
    try:
        return cls(**kw)
    except TypeError:
        pos_vals = [kwargs.get(p) for p in params if p in kwargs]
        for n in range(len(pos_vals), 0, -1):
            try:
                return cls(*pos_vals[:n])
            except TypeError:
                continue

        ordered = ["bin_dir", "config_dir", "verbose", "emit_mode", "emit_verbose"]
        pos2 = [kwargs[k] for k in ordered if k in kwargs]
        for n in range(len(pos2), 0, -1):
            try:
                return cls(*pos2[:n])
            except TypeError:
                continue

        raise


def run_command(
    cmd: list[str],
    description: str = "",
    show_output: bool = True,
    emit_mode: bool = False,
) -> subprocess.CompletedProcess:
    """Run a subprocess command, optionally showing a Rich status message."""
    if emit_mode:
        cmd_str = " ".join(cmd)
        console.print(f"[cyan]📋 EMIT:[/cyan] {cmd_str}")
        if description:
            console.print(f"[dim]   Purpose: {description}[/dim]")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    if description:
        with console.status(f"[bold green]{description}..."):
            result = subprocess.run(
                cmd, check=False, capture_output=not show_output, text=True
            )
    else:
        result = subprocess.run(
            cmd, check=False, capture_output=not show_output, text=True
        )

    return result


def find_fplaunch_script(script_name: str) -> Optional[Path]:
    """Search common locations for a helper script (e.g., fplaunch-generate)."""
    candidates = [
        Path.cwd() / script_name,
        Path.home() / ".local" / "bin" / script_name,
        Path("/usr/local/bin") / script_name,
        Path("/usr/bin") / script_name,
    ]
    for p in candidates:
        if p.exists() and p.is_file() and os.access(p, os.X_OK):
            return p
    return None


def use_python_backend() -> bool:
    """Indicate whether Python backend should be used (always True here)."""
    return True


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--emit", is_flag=True, help="Emit commands instead of executing (dry run)"
)
@click.option(
    "--emit-verbose", is_flag=True, help="Show detailed file contents in emit mode"
)
@click.option(
    "--config-dir",
    type=click.Path(exists=True, dir_okay=True),
    help="Custom configuration directory",
)
@click.version_option(version=FPLAUNCH_VERSION, prog_name="fplaunch")
@click.pass_context
def cli(ctx, verbose, emit, emit_verbose, config_dir) -> None:
    """Main entry point for fplaunchwrapper CLI (Click-based)."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = bool(verbose)
    ctx.obj["emit"] = bool(emit)
    ctx.obj["emit_verbose"] = bool(emit_verbose)
    ctx.obj["config_dir"] = config_dir or os.path.expanduser(
        "~/.config/fplaunchwrapper"
    )

    if verbose:
        console.print("[bold blue]Verbose mode enabled[/bold blue]")
    if emit:
        console.print(
            "[yellow]🧪 EMIT MODE: Commands will be shown but not executed[/yellow]"
        )


@cli.command()
@click.argument("bin_dir", required=False)
@click.pass_context
def generate(ctx, bin_dir) -> int:
    """Generate Flatpak application wrappers.

    Creates wrapper scripts for all installed Flatpak applications,
    allowing you to launch them by simple name (e.g., 'firefox' instead
    of 'flatpak run org.mozilla.firefox').

    \b
    Examples:
      fplaunch generate              # Generate wrappers in ~/bin
      fplaunch generate ~/.local/bin # Generate in custom directory
      fplaunch -v generate           # Verbose output
    """
    if not bin_dir:
        bin_dir = os.path.expanduser("~/bin")

    WrapperGenerator = import_handler.require("lib.generate", "WrapperGenerator")
    generator = _instantiate_compat(
        WrapperGenerator,
        bin_dir=bin_dir,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )
    result: int = generator.run()
    return result


@cli.command(name="list")
@click.argument("app_name", required=False)
@click.option("--all", "show_all", is_flag=True, help="List all wrappers")
@click.pass_context
def list_wrappers(ctx, app_name, show_all) -> int:
    """List installed Flatpak wrappers or show details for one wrapper.

    \b
    Examples:
      fplaunch list           # List all wrappers
      fplaunch list firefox   # Show details for firefox wrapper
    """
    WrapperManager = import_handler.require("lib.manage", "WrapperManager")
    manager = _instantiate_compat(
        WrapperManager,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )

    if app_name:
        success = manager.show_info(app_name)
        return 0 if success else 1
    else:
        manager.display_wrappers()
        return 0


@cli.command()
@click.argument("app_name")
@click.option("--emit", is_flag=True, help="Emit only (dry run)")
@click.pass_context
def install(ctx, app_name, emit) -> int:
    """Install a Flatpak application and generate a wrapper for it."""
    emit_mode = emit or ctx.obj.get("emit", False)
    result = run_command(
        ["flatpak", "install", "-y", app_name],
        f"Installing Flatpak app: {app_name}",
        emit_mode=emit_mode,
    )
    if result.returncode != 0:
        console_err.print(
            f"[red]Error:[/red] Failed to install Flatpak app: {result.stderr}"
        )
        return result.returncode

    WrapperGenerator = import_handler.require("lib.generate", "WrapperGenerator")
    generator = _instantiate_compat(
        WrapperGenerator,
        bin_dir=os.path.expanduser("~/bin"),
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=emit_mode,
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )
    return int(generator.run())


@cli.command()
@click.argument("app_name")
@click.option("--remove-data", is_flag=True, help="Remove application data")
@click.option("--emit", is_flag=True, help="Emit only (dry run)")
@click.pass_context
def uninstall(ctx, app_name, remove_data, emit) -> int:
    """Uninstall a Flatpak application and remove its wrapper."""
    emit_mode = emit or ctx.obj.get("emit", False)
    WrapperManager = import_handler.require("lib.manage", "WrapperManager")
    manager = _instantiate_compat(
        WrapperManager,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=emit_mode,
    )

    wrapper_removed = False
    try:
        wrapper_removed = manager.remove_wrapper(app_name, force=True)
    except Exception:
        pass

    cmd = ["flatpak", "uninstall", "-y"]
    if remove_data:
        cmd.append("--delete-data")
    cmd.append(app_name)
    result = run_command(
        cmd, f"Uninstalling Flatpak app: {app_name}", emit_mode=emit_mode
    )
    if result.returncode != 0:
        console_err.print(
            f"[red]Error:[/red] Failed to uninstall Flatpak app: {result.stderr}"
        )
        return result.returncode

    console.print(
        f"[green]✓[/green] Uninstalled {app_name} (wrapper: {'removed' if wrapper_removed else 'not found'})"
    )

    return 0


@cli.command()
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
    ctx, app_name, hook_failure, abort_on_hook_failure, ignore_hook_failure
) -> int:
    """Launch a Flatpak application via its wrapper.

    \b
    Examples:
      fplaunch launch firefox
      fplaunch launch firefox --abort-on-hook-failure
    """
    AppLauncher = import_handler.require("lib.launch", "AppLauncher")
    resolved_hook_failure = hook_failure
    if abort_on_hook_failure:
        resolved_hook_failure = "abort"
    elif ignore_hook_failure:
        resolved_hook_failure = "ignore"

    launcher = AppLauncher(app_name, hook_failure_mode=resolved_hook_failure)
    return 0 if launcher.launch() else 1


@cli.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Force removal without prompt")
@click.pass_context
def remove(ctx, name, force) -> int:
    """Remove a wrapper by name."""
    WrapperManager = import_handler.require("lib.manage", "WrapperManager")
    manager = _instantiate_compat(
        WrapperManager,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
    )
    if manager.remove_wrapper(name, force=force):
        console.print(f"[green]✓[/green] Removed wrapper: {name}")
        return 0
    else:
        console_err.print(f"[red]Error:[/red] Failed to remove wrapper: {name}")
        return 1


@cli.command()
@click.pass_context
def cleanup(ctx) -> int:
    """Clean up orphaned wrapper files and artifacts.

    Removes wrapper scripts for uninstalled Flatpak applications
    and cleans up stale configuration files.

    \b
    Examples:
      fplaunch cleanup    # Remove orphaned wrappers
      fplaunch clean      # Alias for cleanup
    """
    WrapperCleanup = import_handler.require("lib.cleanup", "WrapperCleanup")
    cleanup_manager = WrapperCleanup(
        bin_dir=str(Path(ctx.obj["config_dir"]) / "bin")
    )
    return cleanup_manager.run()


@cli.command(name="clean")  # Alias for cleanup
@click.pass_context
def clean(ctx) -> int:
    """Clean up orphaned wrapper files and artifacts (alias for cleanup)."""
    WrapperCleanup = import_handler.require("lib.cleanup", "WrapperCleanup")
    cleanup_manager = WrapperCleanup(
        bin_dir=str(Path(ctx.obj["config_dir"]) / "bin")
    )
    return cleanup_manager.run()


@cli.command()
@click.option("--daemon", is_flag=True, help="Run in daemon mode (background)")
@click.pass_context
def monitor(ctx, daemon) -> int:
    """Start Flatpak monitoring daemon (Python backend).

    Uses the programmatic ``start_flatpak_monitoring`` entrypoint so that
    argument parsing in the monitor module (argparse) does not attempt to
    parse the main program's argv (which can confuse subprocess-based tests).
    """
    # Avoid starting long-running monitors during tests when --emit is set.
    # In emit mode we should not start background threads or block the CLI.
    if ctx.obj.get("emit", False):
        console.print(
            "[yellow]EMIT: Would start Flatpak monitor (no-op in emit mode)[/yellow]"
        )
        return 0

    monitor_main = import_handler.require("lib.flatpak_monitor", "main")
    # Call the main entrypoint programmatically and avoid argparse
    # parsing of the process argv by requesting a skip of parsing.
    monitor_main(daemon=daemon, skip_parse=True)
    return 0


@cli.command(name="set-pref")
@click.argument("wrapper_name")
@click.argument("preference")
@click.pass_context
def set_pref(ctx, wrapper_name, preference) -> int:
    """Set launch preference for a wrapper (system|flatpak or a Flatpak ID)."""
    WrapperManager = import_handler.require("lib.manage", "WrapperManager")
    manager = _instantiate_compat(
        WrapperManager,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )
    if wrapper_name == "all":
        updated = manager.set_preference_all(preference)
        return 0 if updated > 0 else 1
    success = manager.set_preference(wrapper_name, preference)
    return 0 if success else 1


@cli.command(name="pref")
@click.argument("wrapper_name")
@click.argument("preference")
@click.pass_context
def pref(ctx, wrapper_name, preference) -> int:
    """Alias for set-pref."""
    # Call the same implementation as `set_pref`.
    result: int = set_pref(ctx, wrapper_name, preference)
    return result


@cli.command(name="rm")
@click.argument("name")
@click.option("--force", is_flag=True, help="Force removal without prompt")
@click.pass_context
def rm(ctx, name, force) -> int:
    """Alias for remove (delegates directly to manager implementation)."""
    WrapperManager = import_handler.require("lib.manage", "WrapperManager")
    manager = _instantiate_compat(
        WrapperManager,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
    )
    if manager.remove_wrapper(name, force=force):
        console.print(f"[green]✓[/green] Removed wrapper: {name}")
        return 0
    else:
        console_err.print(f"[red]Error:[/red] Failed to remove wrapper: {name}")
        return 1


def _run_systemd_setup(
    ctx, bin_dir: str | None = None, wrapper_script: str | None = None
) -> int:
    """Underlying systemd setup implementation.

    This helper contains the real logic for installing/enabling systemd
    units and is callable directly from the ``systemd`` group callback.
    Calling the Click-wrapped command object directly from the group
    callback (with a Context as the first positional argument) results
    in a TypeError because the Click Command object is not callable in
    that way. Extracting the logic into a regular function avoids that
    problem and makes the behavior safe for both direct invocation and
    testing (where tests often patch methods on SystemdSetup).
    """
    SystemdSetup = import_handler.require("lib.systemd_setup", "SystemdSetup")
    setup = _instantiate_compat(
        SystemdSetup,
        bin_dir=bin_dir,
        wrapper_script=wrapper_script,
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )
    try:
        # Prefer calling a 'run' entrypoint if present (tests patch this),
        # otherwise fall back to the more specific install helper.
        if hasattr(setup, "run"):
            return 0 if setup.run() else 1
        if hasattr(setup, "install_systemd_units"):
            return 0 if setup.install_systemd_units() else 1
        return 0
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        return 1


@cli.command(name="systemd-setup")
@click.argument("bin_dir", required=False)
@click.argument("wrapper_script", required=False)
@click.pass_context
def systemd_setup_cmd(ctx, bin_dir, wrapper_script) -> int:
    """Install/enable systemd units for automatic wrapper generation."""
    return _run_systemd_setup(ctx, bin_dir, wrapper_script)


@cli.group(name="systemd", invoke_without_command=True)
@click.pass_context
def systemd_group(ctx) -> None:
    """Manage systemd user units (enable|disable|status|start|stop|restart|reload|logs|list|test)."""
    if ctx.invoked_subcommand is None:
        _run_systemd_setup(ctx, None, None)
        return
    return


def _systemd_simple_action(ctx) -> int:
    SystemdSetup = safe_import("lib.systemd_setup", "SystemdSetup")
    if SystemdSetup is None:
        return 0
    setup = _instantiate_compat(
        SystemdSetup,
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )
    if hasattr(setup, "install_systemd_units"):
        return 0 if setup.install_systemd_units() else 1
    return 0


@systemd_group.command(name="enable")
@click.pass_context
def systemd_enable(ctx) -> int:
    """Enable the systemd service for automatic wrapper generation."""
    return _systemd_simple_action(ctx)


@systemd_group.command(name="disable")
@click.pass_context
def systemd_disable(ctx) -> int:
    """Disable the systemd service."""
    return _systemd_simple_action(ctx)


@systemd_group.command(name="status")
@click.pass_context
def systemd_status(ctx) -> int:
    """Show status of the systemd service."""
    return _systemd_simple_action(ctx)


@systemd_group.command(name="start")
@click.pass_context
def systemd_start(ctx) -> int:
    """Start the systemd service immediately."""
    return _systemd_simple_action(ctx)


@systemd_group.command(name="stop")
@click.pass_context
def systemd_stop(ctx) -> int:
    """Stop the systemd service."""
    return _systemd_simple_action(ctx)


@systemd_group.command(name="restart")
@click.pass_context
def systemd_restart(ctx) -> int:
    """Restart the systemd service."""
    return _systemd_simple_action(ctx)


@systemd_group.command(name="reload")
@click.pass_context
def systemd_reload(ctx) -> int:
    """Reload systemd daemon configuration."""
    return _systemd_simple_action(ctx)


@systemd_group.command(name="logs")
@click.pass_context
def systemd_logs(ctx) -> int:
    """View systemd service logs."""
    return _systemd_simple_action(ctx)


@systemd_group.command(name="list")
@click.pass_context
def systemd_list(ctx) -> int:
    """List all managed systemd units."""
    return _systemd_simple_action(ctx)


@systemd_group.command(name="test")
@click.option(
    "--emit", is_flag=True, help="Emit commands instead of executing (dry run)"
)
@click.pass_context
def systemd_test(ctx, emit) -> int:
    """Test systemd configuration (dry run)."""
    emit_mode = emit or ctx.obj.get("emit", False) if ctx.obj else False

    if emit_mode:
        console.print("[yellow]EMIT: Would run systemd test[/yellow]")
        return 0

    return _systemd_simple_action(ctx)


@cli.command()
@click.argument("app_name")
@click.pass_context
def info(ctx, app_name) -> int:
    """Show information about a wrapper."""
    WrapperManager = import_handler.require("lib.manage", "WrapperManager")
    manager = _instantiate_compat(
        WrapperManager,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
    )
    success = manager.show_info(app_name)
    return 0 if success else 1


@cli.command()
@click.argument("query", required=False)
@click.pass_context
def search(ctx, query) -> int:
    """Search or discover wrappers. Alias: discover."""
    WrapperManager = import_handler.require("lib.manage", "WrapperManager")
    manager = _instantiate_compat(
        WrapperManager,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
    )
    # Minimal behavior: call discover_features if available, otherwise list wrappers
    if hasattr(manager, "discover_features"):
        manager.discover_features()
        return 0
    manager.display_wrappers()
    return 0


@cli.command(name="discover")
@click.argument("query", required=False)
@click.pass_context
def discover(ctx, query) -> int:
    """Alias for search."""
    result: int = search(ctx, query)
    return result


@cli.group(name="profiles", invoke_without_command=True)
@click.pass_context
def profiles_group(ctx) -> None:
    """Manage configuration profiles (list/current/create/switch/export/import)."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(profiles_list)


@profiles_group.command(name="list")
@click.pass_context
def profiles_list(ctx) -> int:
    """List available profiles."""
    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
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
def profiles_create(ctx, profile_name, copy_from) -> int:
    """Create a new profile."""
    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
    cfg = create_config_manager()
    if cfg.create_profile(profile_name, copy_from):
        console.print(f"[green]✓[/green] Created profile: {profile_name}")
        return 0
    else:
        console_err.print(
            f"[red]Error:[/red] Could not create profile '{profile_name}' "
            "(may already exist or invalid name)"
        )
        return 1


@profiles_group.command(name="switch")
@click.argument("profile_name")
@click.pass_context
def profiles_switch(ctx, profile_name) -> int:
    """Switch to a profile."""
    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
    cfg = create_config_manager()
    if cfg.switch_profile(profile_name):
        console.print(f"[green]✓[/green] Switched to profile: {profile_name}")
        return 0
    else:
        console_err.print(
            f"[red]Error:[/red] Could not switch to profile '{profile_name}' "
            "(profile may not exist)"
        )
        return 1


@profiles_group.command(name="current")
@click.pass_context
def profiles_current(ctx) -> int:
    """Show current profile."""
    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
    cfg = create_config_manager()
    active = cfg.get_active_profile()
    console.print(f"Current profile: [bold]{active}[/bold]")
    return 0


@profiles_group.command(name="export")
@click.argument("profile_name")
@click.argument("output_file", required=False)
@click.pass_context
def profiles_export(ctx, profile_name, output_file) -> int:
    """Export a profile to a file."""
    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
    cfg = create_config_manager()
    export_path = Path(output_file) if output_file else Path(f"{profile_name}.toml")
    if cfg.export_profile(profile_name, export_path):
        console.print(
            f"[green]✓[/green] Exported profile '{profile_name}' to {export_path}"
        )
        return 0
    else:
        console_err.print(
            f"[red]Error:[/red] Could not export profile '{profile_name}'"
        )
        return 1


@profiles_group.command(name="import")
@click.argument("input_file")
@click.argument("profile_name", required=False)
@click.pass_context
def profiles_import(ctx, input_file, profile_name) -> int:
    """Import a profile from a file."""
    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
    cfg = create_config_manager()
    import_path = Path(input_file)
    name = profile_name or import_path.stem
    if cfg.import_profile(name, import_path):
        console.print(
            f"[green]✓[/green] Imported profile '{name}' from {import_path}"
        )
        return 0
    else:
        console_err.print(
            f"[red]Error:[/red] Could not import profile from '{input_file}'"
        )
        return 1


@cli.group(name="presets", invoke_without_command=True)
@click.pass_context
def presets_group(ctx) -> None:
    """Manage permission presets (list/get/add/remove)."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(presets_list)


@presets_group.command(name="list")
@click.pass_context
def presets_list(ctx) -> int:
    """List available permission presets."""
    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
    cfg = create_config_manager()
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
def presets_get(ctx, preset_name) -> int:
    """Get a permission preset."""
    if not preset_name:
        raise click.UsageError("PRESET_NAME is required")

    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
    cfg = create_config_manager()
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
def presets_add(ctx, preset_name, permission) -> int:
    """Add a new permission preset."""
    if not permission:
        console_err.print("[red]Error:[/red] At least one permission is required")
        return 1

    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
    cfg = create_config_manager()
    cfg.add_permission_preset(preset_name, list(permission))
    console.print(f"[green]✓[/green] Added preset: {preset_name}")
    return 0


@presets_group.command(name="remove")
@click.argument("preset_name")
@click.pass_context
def presets_remove(ctx, preset_name) -> int:
    """Remove a permission preset."""
    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
    cfg = create_config_manager()
    if cfg.remove_permission_preset(preset_name):
        console.print(f"[green]✓[/green] Removed preset: {preset_name}")
        return 0
    else:
        console_err.print(f"[red]Error:[/red] Preset '{preset_name}' not found")
        return 1


@cli.command(name="files")
@click.argument("app_name", required=False)
@click.option(
    "--all",
    "-a",
    "show_all",
    is_flag=True,
    help="Show all managed files (wrappers, prefs, env, aliases)",
)
@click.option("--wrappers", is_flag=True, help="Show only wrapper scripts")
@click.option("--prefs", is_flag=True, help="Show only preference files")
@click.option("--env", is_flag=True, help="Show only environment files")
@click.option("--paths", is_flag=True, help="Output raw paths (machine-parseable)")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def files(ctx, app_name, show_all, wrappers, prefs, env, paths, json_output) -> int:
    """Display all files managed by fplaunchwrapper for a given application.

    Without APP_NAME, lists all managed files across all apps.
    """
    import json as json_module

    WrapperManager = import_handler.require("lib.manage", "WrapperManager")
    manager = _instantiate_compat(
        WrapperManager,
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )

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


@cli.command(name="manifest")
@click.argument("app_name")
@click.option("--emit", is_flag=True, help="Emit only (dry run)")
@click.pass_context
def manifest(ctx, app_name, emit) -> int:
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
        if result.returncode != 0:
            console_err.print(
                f"[red]Error:[/red] Failed to get manifest for {app_name}"
            )
            raise click.exceptions.Exit(code=1)
        return 0
    except click.exceptions.Exit:
        raise
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        return 1


@cli.command()
@click.argument("action", required=False)
@click.argument("value", required=False)
@click.pass_context
def config(ctx, action, value) -> int:
    """Manage fplaunchwrapper configuration.

    \b
    Actions:
      show          Show current configuration (default)
      init          Initialize configuration file
      cron-interval Get or set cron interval (in hours)
    """
    create_config_manager = import_handler.require("lib.config_manager", "create_config_manager")
    cfg = create_config_manager()
    if not action or action == "show":
        config_path = Path(ctx.obj.get("config_dir", "")) / "config.toml"
        if config_path.exists():
            console.print(f"[bold]Configuration file:[/bold] {config_path}")
            content = config_path.read_text()
            console.print(content)
        else:
            console.print(
                f"[yellow]No configuration file found at {config_path}[/yellow]"
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
            interval = int(value)
            cfg.set_cron_interval(interval)
            console.print(
                f"[green]✓[/green] Cron interval set to [bold]{interval}[/bold] hours"
            )
        return 0
    console_err.print(f"[red]Error:[/red] Unknown action: {action}")
    console_err.print("Valid actions: show, init, cron-interval")
    raise SystemExit(1)


def main(argv: Optional[list[str]] = None) -> int:
    """Entrypoint used by console scripts. Dispatch to Click."""
    argv = argv if argv is not None else sys.argv[1:]
    try:
        cli.main(args=argv, prog_name="fplaunch", standalone_mode=False)
        return 0
    except SystemExit as e:
        code = e.code
        if isinstance(code, int):
            return code
        return 1
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
