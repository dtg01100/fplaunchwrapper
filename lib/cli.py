#!/usr/bin/env python3
"""Modern CLI interface for fplaunchwrapper using Click
Provides a user-friendly command-line interface with rich formatting.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import builtins

try:
    import click

    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Initialize Rich consoles for stdout and stderr
console = Console() if RICH_AVAILABLE else None
console_err = Console(stderr=True) if RICH_AVAILABLE else None


def run_command(
    cmd: builtins.list[str],
    description: str = "",
    show_output: bool = True,
    emit_mode: bool = False,
) -> subprocess.CompletedProcess:
    """Run a command with optional progress display and emit support."""
    # Handle emit mode
    if emit_mode:
        cmd_str = " ".join(cmd)
        if console:
            console.print(f"[cyan]📋 EMIT:[/cyan] {cmd_str}")
            if description:
                console.print(f"[dim]   Purpose: {description}[/dim]")
        elif description:
            print(f"Purpose: {description}")

        # Return a mock completed process for emit mode
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    # Normal execution
    if description and console:
        with console.status(f"[bold green]{description}..."):
            result = subprocess.run(
                cmd, check=False, capture_output=not show_output, text=True
            )
    else:
        result = subprocess.run(
            cmd, check=False, capture_output=not show_output, text=True
        )

    return result


def find_fplaunch_script(script_name: str) -> Path | None:
    """Find fplaunch script in common locations."""
    search_paths = [
        Path.cwd() / script_name,
        Path.home() / ".local" / "bin" / script_name,
        Path("/usr/local/bin") / script_name,
        Path("/usr/bin") / script_name,
    ]

    for path in search_paths:
        if path.exists() and path.is_file() and os.access(path, os.X_OK):
            return path

    return None


def use_python_backend() -> bool:
    """Check if we should use Python backend instead of bash scripts."""
    try:
        import lib.generate
        import lib.launch
        import lib.manage

        return True
    except ImportError:
        return False


# Click-based CLI (if available)
if CLICK_AVAILABLE:

    @click.group()
    @click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
    @click.option(
        "--emit",
        is_flag=True,
        help="Emit commands instead of executing (dry run)",
    )
    @click.option(
        "--emit-verbose",
        is_flag=True,
        help="Show detailed file contents in emit mode",
    )
    @click.option(
        "--config-dir",
        type=click.Path(exists=True, dir_okay=True),
        help="Custom configuration directory",
    )
    @click.pass_context
    def cli(ctx, verbose, emit, emit_verbose, config_dir) -> None:
        """Fplaunchwrapper - Modern Flatpak wrapper management.

        A comprehensive tool for managing Flatpak application wrappers
        with automatic launch method detection and preference management.
        """
        ctx.ensure_object(dict)
        ctx.obj["verbose"] = verbose
        ctx.obj["emit"] = emit
        ctx.obj["emit_verbose"] = emit_verbose
        ctx.obj["config_dir"] = config_dir or os.path.expanduser(
            "~/.config/fplaunchwrapper",
        )

        # Set up environment
        if verbose and console:
            console.print("[bold blue]Verbose mode enabled[/bold blue]")
        if emit and console:
            console.print(
                "[yellow]🧪 EMIT MODE: Commands will be shown but not executed[/yellow]",
            )

    @cli.command()
    @click.argument(
        "bin_dir",
        type=click.Path(dir_okay=True, writable=True),
        required=False,
    )
    @click.option(
        "--emit",
        is_flag=True,
        help="Emit commands instead of executing (dry run)",
    )
    @click.option(
        "--emit-verbose",
        is_flag=True,
        help="Show detailed file contents in emit mode",
    )
    @click.pass_context
    def generate(ctx, bin_dir, emit, emit_verbose):
        """Generate Flatpak application wrappers.

        BIN_DIR: Directory to store wrapper scripts (default: ~/bin)

        This command scans installed Flatpak applications and creates
        wrapper scripts that intelligently choose between system packages
        and Flatpak applications based on user preferences.
        """
        if not bin_dir:
            bin_dir = os.path.expanduser("~/bin")

        # Use Python backend
        try:
            from .generate import WrapperGenerator

            generator = WrapperGenerator(
                bin_dir,
                ctx.obj["verbose"],
                emit or ctx.obj["emit"],
                emit_verbose or ctx.obj["emit_verbose"],
            )
            return generator.run()
        except ImportError as e:
            if console_err:
                console_err.print(
                    f"[red]Error:[/red] Failed to import wrapper generator: {e}",
                )
            else:
                import sys
                print(f"Error: Failed to import wrapper generator: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.argument("app_name", required=False)
    @click.option("--all", is_flag=True, help="List all wrappers")
    @click.pass_context
    def list(ctx, app_name, all) -> int | None:
        """List installed Flatpak wrappers.

        APP_NAME: Show details for specific application
        """
        # Use Python backend
        try:
            from .manage import WrapperManager

            manager = WrapperManager(ctx.obj["config_dir"], ctx.obj["verbose"])

            if app_name:
                # Show specific app details
                return 0 if manager.show_info(app_name) else 1
            # List all wrappers
            manager.display_wrappers()
            return 0

        except ImportError as e:
            if console_err:
                console_err.print(
                    f"[red]Error:[/red] Failed to import wrapper manager: {e}",
                )
            else:
                import sys
                print(f"Error: Failed to import wrapper manager: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.argument("app_name")
    @click.argument("preference", type=click.Choice(["system", "flatpak"]))
    @click.option(
        "--emit",
        is_flag=True,
        help="Emit commands instead of executing (dry run)",
    )
    @click.option(
        "--emit-verbose",
        is_flag=True,
        help="Show detailed file contents in emit mode",
    )
    @click.pass_context
    def set_pref(ctx, app_name, preference, emit, emit_verbose) -> int | None:
        """Set launch preference for an application.

        APP_NAME: Application name
        PREFERENCE: Preferred launch method (system or flatpak)
        """
        # Use Python backend
        try:
            from .manage import WrapperManager

            manager = WrapperManager(
                ctx.obj["config_dir"],
                ctx.obj["verbose"],
                emit or ctx.obj["emit"],
                emit_verbose or ctx.obj["emit_verbose"],
            )
            return 0 if manager.set_preference(app_name, preference) else 1

        except ImportError as e:
            if console_err:
                console_err.print(
                    f"[red]Error:[/red] Failed to import wrapper manager: {e}",
                )
            else:
                import sys
                print(f"Error: Failed to import wrapper manager: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.argument("app_name")
    @click.option(
        "--emit",
        is_flag=True,
        help="Emit commands instead of executing (dry run)",
    )
    @click.pass_context
    def launch(ctx, app_name, emit):
        """Launch a Flatpak application.

        APP_NAME: Application name to launch
        """
        # Use Python backend
        try:
            from .launch import AppLauncher

            launcher = AppLauncher(app_name)
            return 0 if launcher.launch() else 1
        except ImportError as e:
            if console_err:
                console_err.print(f"[red]Error:[/red] Failed to import launcher: {e}")
            else:
                import sys
                print(f"Error: Failed to import launcher: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.argument("app_name")
    @click.option(
        "--emit",
        is_flag=True,
        help="Emit commands instead of executing (dry run)",
    )
    @click.pass_context
    def remove(ctx, app_name, emit):
        """Remove a Flatpak wrapper.

        APP_NAME: Application name to remove
        """
        emit_mode = emit or ctx.obj["emit"]

        script_path = find_fplaunch_script("fplaunch-manage")
        if not script_path:
            if console_err:
                console_err.print("[red]Error:[/red] fplaunch-manage script not found")
            else:
                import sys
                print("Error: fplaunch-manage script not found", file=sys.stderr)
            return 1

        cmd = [str(script_path), "remove", app_name]
        result = run_command(
            cmd,
            f"Removing wrapper for {app_name}",
            emit_mode=emit_mode,
        )

        if result.returncode == 0:
            if console:
                console.print(
                    f"[green]✓[/green] Removed wrapper for [bold]{app_name}[/bold]",
                )
            else:
                print(f"Removed wrapper for {app_name}")
        elif not emit_mode:
            if console:
                console.print(f"[red]✗[/red] Failed to remove wrapper: {result.stderr}")
            else:
                import sys
                print(f"Error: Failed to remove wrapper: {result.stderr}", file=sys.stderr)
            return result.returncode

        return 0

    @cli.command()
    @click.option(
        "--emit",
        is_flag=True,
        help="Emit commands instead of executing (dry run)",
    )
    @click.pass_context
    def systemd_setup(ctx, emit) -> int:
        """Set up systemd user service for Flatpak monitoring.

        Creates and enables a systemd user service that automatically
        monitors for Flatpak installation changes and regenerates wrappers.
        """
        # Use Python backend
        try:
            from .systemd_setup import SystemdSetup

            setup = SystemdSetup()
            return setup.run()
        except ImportError as e:
            if console_err:
                console_err.print(f"[red]Error:[/red] Failed to import systemd setup: {e}")
            return 1

    @cli.command()
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Show what would be cleaned without actually removing files",
    )
    @click.option(
        "--force",
        is_flag=True,
        help="Force cleanup without confirmation",
    )
    @click.option(
        "--emit",
        is_flag=True,
        help="Emit commands instead of executing (dry run)",
    )
    @click.pass_context
    def cleanup(ctx, dry_run, force, emit) -> int:
        """Clean up orphaned wrapper files and artifacts.

        Removes wrapper scripts and configuration files that are no longer
        needed due to uninstalled Flatpak applications or outdated configurations.
        """
        # Use Python backend
        try:
            from .cleanup import WrapperCleanup

            cleanup_manager = WrapperCleanup(
                bin_dir=str(Path(ctx.obj["config_dir"]) / "bin"),
                dry_run=dry_run,
                force=force,
            )
            return cleanup_manager.run()
        except ImportError as e:
            if console_err:
                console_err.print(f"[red]Error:[/red] Failed to import cleanup: {e}")
            else:
                import sys
                print(f"Error: Failed to import cleanup: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.option(
        "--daemon",
        is_flag=True,
        help="Run in daemon mode (background)",
    )
    @click.option(
        "--emit",
        is_flag=True,
        help="Emit commands instead of executing (dry run)",
    )
    @click.pass_context
    def monitor(ctx, daemon, emit) -> int:
        """Start Flatpak monitoring daemon.

        Monitors for Flatpak installation changes and automatically
        regenerates wrappers when applications are installed or removed.
        """
        emit_mode = emit or ctx.obj["emit"]

        if emit_mode:
            if console:
                console.print(
                    "[cyan]📋 EMIT:[/cyan] Would start Flatpak monitoring daemon",
                )
                console.print(
                    "[dim]   Purpose: Monitor Flatpak installations and auto-regenerate wrappers[/dim]",
                )
            else:
                pass
            return 0

        # Use Python backend
        try:
            from .flatpak_monitor import main as monitor_main

            # Set up argv for monitor_main
            import sys

            original_argv = sys.argv
            try:
                if daemon:
                    sys.argv = ["monitor", "--daemon"]
                else:
                    sys.argv = ["monitor"]
                monitor_main()
                return 0
            finally:
                sys.argv = original_argv
        except ImportError as e:
            if console_err:
                console_err.print(f"[red]Error:[/red] Failed to import monitor: {e}")
            else:
                import sys
                print(f"Error: Failed to import monitor: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.argument("action", required=False)
    @click.argument("value", required=False)
    @click.option(
        "--emit",
        is_flag=True,
        help="Emit commands instead of executing (dry run)",
    )
    @click.pass_context
    def config(ctx, action, value, emit) -> int:
        """Manage fplaunchwrapper configuration.

        ACTION: Configuration action (show, init, block, unblock)
        VALUE: Value for the action (e.g., app name for block/unblock)
        """
        # Use Python backend
        try:
            from .config_manager import main as config_main

            # Set up argv for config_main
            import sys

            original_argv = sys.argv
            try:
                if action:
                    if value:
                        sys.argv = ["config", action, value]
                    else:
                        sys.argv = ["config", action]
                else:
                    sys.argv = ["config", "show"]
                config_main()
                return 0
            finally:
                sys.argv = original_argv
        except ImportError as e:
            if console_err:
                console_err.print(f"[red]Error:[/red] Failed to import config manager: {e}")
            else:
                import sys
                print(f"Error: Failed to import config manager: {e}", file=sys.stderr)
            return 1
    # (duplicate setup_systemd/monitor/config variants removed)

    @cli.command()
    @click.argument("action", required=False)
    @click.argument("name", required=False)
    @click.option("--copy-from", help="Copy configuration from existing profile")
    @click.pass_context
    def profiles(ctx, action, name, copy_from) -> int:
        """Manage configuration profiles.

        ACTION: Profile action (list, create, switch, current, export, import)
        NAME: Profile name (for create, switch, export, import actions)
        """
        try:
            from .config_manager import EnhancedConfigManager

            manager = EnhancedConfigManager()

            if not action or action == "list":
                # List all profiles
                profiles = manager.list_profiles()
                current = manager.get_active_profile()
                
                if console:
                    console.print("[bold]Available Profiles:[/bold]")
                    for profile in profiles:
                        marker = " ✓" if profile == current else ""
                        console.print(f"  {profile}{marker}")
                else:
                    for profile in profiles:
                        marker = " (current)" if profile == current else ""
                        print(f"  {profile}{marker}")
                return 0

            elif action == "create":
                if not name:
                    if console_err:
                        console_err.print("[red]Error:[/red] Profile name required for create action")
                    else:
                        print("Error: Profile name required for create action", file=sys.stderr)
                    return 1
                
                success = manager.create_profile(name, copy_from=copy_from)
                if success:
                    if console:
                        console.print(f"[green]✓[/green] Created profile: {name}")
                    else:
                        print(f"Created profile: {name}")
                    return 0
                else:
                    if console_err:
                        console_err.print(f"[red]Error:[/red] Failed to create profile: {name}")
                    else:
                        print(f"Error: Failed to create profile: {name}", file=sys.stderr)
                    return 1

            elif action == "switch":
                if not name:
                    if console_err:
                        console_err.print("[red]Error:[/red] Profile name required for switch action")
                    else:
                        print("Error: Profile name required for switch action", file=sys.stderr)
                    return 1
                
                success = manager.switch_profile(name)
                if success:
                    if console:
                        console.print(f"[green]✓[/green] Switched to profile: {name}")
                    else:
                        print(f"Switched to profile: {name}")
                    return 0
                else:
                    if console_err:
                        console_err.print(f"[red]Error:[/red] Failed to switch to profile: {name}")
                    else:
                        print(f"Error: Failed to switch to profile: {name}", file=sys.stderr)
                    return 1

            elif action == "current":
                current = manager.get_active_profile()
                if console:
                    console.print(f"Current profile: [bold]{current}[/bold]")
                else:
                    print(f"Current profile: {current}")
                return 0

            elif action == "export":
                if not name:
                    if console_err:
                        console_err.print("[red]Error:[/red] Profile name required for export action")
                    else:
                        print("Error: Profile name required for export action", file=sys.stderr)
                    return 1
                
                export_path = Path(name).with_suffix(".toml")
                success = manager.export_profile(name, export_path)
                if success:
                    if console:
                        console.print(f"[green]✓[/green] Exported profile to: {export_path}")
                    else:
                        print(f"Exported profile to: {export_path}")
                    return 0
                else:
                    if console_err:
                        console_err.print(f"[red]Error:[/red] Failed to export profile: {name}")
                    else:
                        print(f"Error: Failed to export profile: {name}", file=sys.stderr)
                    return 1

            elif action == "import":
                if not name:
                    if console_err:
                        console_err.print("[red]Error:[/red] Profile name and path required for import action")
                    else:
                        print("Error: Profile name and path required for import action", file=sys.stderr)
                    return 1
                
                import_path = Path(name)
                if not import_path.exists():
                    if console_err:
                        console_err.print(f"[red]Error:[/red] File not found: {import_path}")
                    else:
                        print(f"Error: File not found: {import_path}", file=sys.stderr)
                    return 1
                
                profile_name = import_path.stem
                success = manager.import_profile(profile_name, import_path)
                if success:
                    if console:
                        console.print(f"[green]✓[/green] Imported profile: {profile_name}")
                    else:
                        print(f"Imported profile: {profile_name}")
                    return 0
                else:
                    if console_err:
                        console_err.print(f"[red]Error:[/red] Failed to import profile from: {import_path}")
                    else:
                        print(f"Error: Failed to import profile from: {import_path}", file=sys.stderr)
                    return 1

            else:
                if console_err:
                    console_err.print(f"[red]Error:[/red] Unknown action: {action}")
                else:
                    print(f"Error: Unknown action: {action}", file=sys.stderr)
                return 1

        except ImportError as e:
            if console_err:
                console_err.print(f"[red]Error:[/red] Failed to import config manager: {e}")
            else:
                print(f"Error: Failed to import config manager: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.argument("action", required=False)
    @click.argument("name", required=False)
    @click.option("--permissions", multiple=True, help="Flatpak permissions (e.g., --filesystem=home)")
    @click.pass_context
    def presets(ctx, action, name, permissions) -> int:
        """Manage permission presets for sandbox editing.

        ACTION: Preset action (list, get, add, remove)
        NAME: Preset name
        """
        try:
            from .config_manager import EnhancedConfigManager

            manager = EnhancedConfigManager()

            if not action or action == "list":
                # List all presets
                presets = manager.list_permission_presets()
                
                if console:
                    if presets:
                        console.print("[bold]Available Permission Presets:[/bold]")
                        for preset_name in presets:
                            console.print(f"  {preset_name}")
                    else:
                        console.print("[yellow]No custom presets defined[/yellow]")
                else:
                    if presets:
                        print("Available Permission Presets:")
                        for preset_name in presets:
                            print(f"  {preset_name}")
                    else:
                        print("No custom presets defined")
                return 0

            elif action == "get":
                if not name:
                    if console_err:
                        console_err.print("[red]Error:[/red] Preset name required for get action")
                    else:
                        print("Error: Preset name required for get action", file=sys.stderr)
                    return 1
                
                perms = manager.get_permission_preset(name)
                if perms:
                    if console:
                        console.print(f"[bold]Preset: {name}[/bold]")
                        for perm in perms:
                            console.print(f"  {perm}")
                    else:
                        print(f"Preset: {name}")
                        for perm in perms:
                            print(f"  {perm}")
                    return 0
                else:
                    if console_err:
                        console_err.print(f"[red]Error:[/red] Preset not found: {name}")
                    else:
                        print(f"Error: Preset not found: {name}", file=sys.stderr)
                    return 1

            elif action == "add":
                if not name or not permissions:
                    if console_err:
                        console_err.print("[red]Error:[/red] Preset name and permissions required for add action")
                    else:
                        print("Error: Preset name and permissions required for add action", file=sys.stderr)
                    return 1
                
                manager.add_permission_preset(name, list(permissions))
                if console:
                    console.print(f"[green]✓[/green] Added preset: {name}")
                else:
                    print(f"Added preset: {name}")
                return 0

            elif action == "remove":
                if not name:
                    if console_err:
                        console_err.print("[red]Error:[/red] Preset name required for remove action")
                    else:
                        print("Error: Preset name required for remove action", file=sys.stderr)
                    return 1
                
                success = manager.remove_permission_preset(name)
                if success:
                    if console:
                        console.print(f"[green]✓[/green] Removed preset: {name}")
                    else:
                        print(f"Removed preset: {name}")
                    return 0
                else:
                    if console_err:
                        console_err.print(f"[red]Error:[/red] Preset not found: {name}")
                    else:
                        print(f"Error: Preset not found: {name}", file=sys.stderr)
                    return 1

            else:
                if console_err:
                    console_err.print(f"[red]Error:[/red] Unknown action: {action}")
                else:
                    print(f"Error: Unknown action: {action}", file=sys.stderr)
                return 1

        except ImportError as e:
            if console_err:
                console_err.print(f"[red]Error:[/red] Failed to import config manager: {e}")
            else:
                print(f"Error: Failed to import config manager: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.argument("action", required=False)
    @click.option(
        "--emit",
        is_flag=True,
        help="Emit commands instead of executing (dry run)",
    )
    @click.option(
        "--emit-verbose",
        is_flag=True,
        help="Show detailed file contents in emit mode",
    )
    @click.pass_context
    def systemd(ctx, action, emit, emit_verbose) -> int | None:
        """Manage optional systemd timer for automatic wrapper generation.

        ACTION: Systemd action (enable, disable, status, test)
        """
        try:
            from .systemd_setup import SystemdSetup

            setup = SystemdSetup(
                emit_mode=emit or ctx.obj.get("emit", False),
                emit_verbose=emit_verbose or ctx.obj.get("emit_verbose", False),
            )

            if not action or action == "enable":
                # Enable systemd timer/path units
                if console:
                    console.print("[bold cyan]Enabling systemd timer for wrapper generation...[/bold cyan]")
                
                # Check prerequisites
                if not setup.check_prerequisites():
                    if console_err:
                        console_err.print("[red]Error:[/red] Prerequisites not met for systemd setup")
                    else:
                        print("Error: Prerequisites not met for systemd setup", file=sys.stderr)
                    return 1
                
                # Install units
                if setup.install_systemd_units():
                    if console:
                        console.print("[green]✓[/green] Systemd timer enabled successfully")
                    else:
                        print("Systemd timer enabled successfully")
                    
                    if console:
                        console.print("[dim]Wrappers will be regenerated automatically on Flatpak changes[/dim]")
                    return 0
                else:
                    if console_err:
                        console_err.print("[red]Error:[/red] Failed to enable systemd timer")
                    else:
                        print("Error: Failed to enable systemd timer", file=sys.stderr)
                    return 1

            elif action == "disable":
                # Disable systemd timer/path units
                if console:
                    console.print("[bold cyan]Disabling systemd timer...[/bold cyan]")
                
                if setup.disable_systemd_units():
                    if console:
                        console.print("[green]✓[/green] Systemd timer disabled successfully")
                    else:
                        print("Systemd timer disabled successfully")
                    return 0
                else:
                    if console_err:
                        console_err.print("[red]Error:[/red] Failed to disable systemd timer")
                    else:
                        print("Error: Failed to disable systemd timer", file=sys.stderr)
                    return 1

            elif action == "status":
                # Check systemd timer status
                if console:
                    console.print("[bold cyan]Checking systemd timer status...[/bold cyan]")
                
                status = setup.check_systemd_status()
                if console:
                    if status.get("enabled"):
                        console.print("[green]✓[/green] Systemd timer is [bold green]enabled[/bold green]")
                    else:
                        console.print("[yellow]✗[/yellow] Systemd timer is [bold yellow]disabled[/bold yellow]")
                    
                    if status.get("active"):
                        console.print(f"  [green]Status:[/green] [bold green]active[/bold green]")
                    else:
                        console.print(f"  [yellow]Status:[/yellow] [bold yellow]inactive[/bold yellow]")
                    
                    if status.get("units"):
                        console.print("[bold]Units:[/bold]")
                        for unit_name, unit_status in status["units"].items():
                            status_color = "green" if unit_status else "red"
                            console.print(f"  [{status_color}]{'✓' if unit_status else '✗'}[/{status_color}] {unit_name}")
                else:
                    print(f"Systemd timer enabled: {status.get('enabled')}")
                    print(f"Systemd timer active: {status.get('active')}")
                return 0

            elif action == "test":
                # Test systemd timer installation
                if console:
                    console.print("[bold cyan]Testing systemd timer installation...[/bold cyan]")
                
                # Run in emit mode to show what would be installed
                setup_test = SystemdSetup(emit_mode=True, emit_verbose=True)
                if setup_test.check_prerequisites():
                    setup_test.install_systemd_units()
                    if console:
                        console.print("[green]✓[/green] Systemd timer test completed (no changes made)")
                    else:
                        print("Systemd timer test completed (no changes made)")
                    return 0
                else:
                    if console_err:
                        console_err.print("[red]Error:[/red] Prerequisites not met")
                    else:
                        print("Error: Prerequisites not met", file=sys.stderr)
                    return 1

            else:
                if console_err:
                    console_err.print(f"[red]Error:[/red] Unknown action: {action}")
                else:
                    print(f"Error: Unknown action: {action}", file=sys.stderr)
                return 1

        except ImportError as e:
            if console_err:
                console_err.print(f"[red]Error:[/red] Failed to import systemd setup: {e}")
            else:
                print(f"Error: Failed to import systemd setup: {e}", file=sys.stderr)
            return 1

    # Add command aliases for convenience
    # 'rm' is an alias for 'remove' (for shell users)
    cli.add_command(remove, name="rm")
    
    # 'show' is an alias for 'list' (intuitive alternative)
    cli.add_command(list, name="show")
    
    # 'pref' is an alias for 'set-pref' (shorter typing)
    cli.add_command(set_pref, name="pref")
    
    # 'clean' is an alias for 'cleanup'
    cli.add_command(cleanup, name="clean")

    # Export cli as main for entry point
    main = cli

    if __name__ == "__main__":
        sys.exit(main())

    def main() -> int:
        """Main entry point that wraps the Click CLI."""
        try:
            # Call the Click CLI group
            cli()
            return 0
        except SystemExit as e:
            # Click raises SystemExit, convert to int return code
            return e.code if isinstance(e.code, int) else (0 if e.code == 0 else 1)
        except Exception as e:
            # Handle any other exceptions
            if console_err:
                console_err.print(f"[red]Error:[/red] {e}")
            else:
                import sys
                print(f"Error: {e}", file=sys.stderr)
            return 1

else:
    # Fallback CLI without Click
    def main() -> int:
        """Fallback CLI without Click."""
        if len(sys.argv) < 2:
            return 1

        command = sys.argv[1]

        if command == "generate":
            bin_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/bin")
            script_path = find_fplaunch_script("fplaunch-generate")
            if script_path:
                return run_command(
                    [str(script_path), bin_dir],
                    f"Generating wrappers in {bin_dir}",
                ).returncode
            else:
                return 1

        elif command == "list":
            script_path = find_fplaunch_script("fplaunch-manage")
            if script_path:
                return run_command(
                    [str(script_path), "list"], "Listing wrappers"
                ).returncode
            else:
                return 1

        else:
            return 1

    if __name__ == "__main__":
        sys.exit(main())
