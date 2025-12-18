#!/usr/bin/env python3
"""
Modern CLI interface for fplaunchwrapper using Click
Provides a user-friendly command-line interface with rich formatting
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, List

try:
    import click

    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Initialize Rich console if available
console = Console() if RICH_AVAILABLE else None


def run_command(
    cmd: List[str],
    description: str = "",
    show_output: bool = True,
    emit_mode: bool = False,
) -> subprocess.CompletedProcess:
    """Run a command with optional progress display and emit support"""
    # Handle emit mode
    if emit_mode:
        cmd_str = " ".join(cmd)
        if console:
            console.print(f"[cyan]📋 EMIT:[/cyan] {cmd_str}")
            if description:
                console.print(f"[dim]   Purpose: {description}[/dim]")
        else:
            print(f"EMIT: {cmd_str}")
            if description:
                print(f"  Purpose: {description}")

        # Return a mock completed process for emit mode
        result = subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="", stderr=""
        )
        return result

    # Normal execution
    if description and console:
        with console.status(f"[bold green]{description}...") as status:
            result = subprocess.run(cmd, capture_output=not show_output, text=True)
    else:
        result = subprocess.run(cmd, capture_output=not show_output, text=True)

    return result


def find_fplaunch_script(script_name: str) -> Optional[Path]:
    """Find fplaunch script in common locations"""
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
    """Check if we should use Python backend instead of bash scripts"""
    try:
        import lib.generate
        import lib.manage
        import lib.launch

        return True
    except ImportError:
        return False


# Click-based CLI (if available)
if CLICK_AVAILABLE:

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
    @click.pass_context
    def cli(ctx, verbose, emit, emit_verbose, config_dir):
        """fplaunchwrapper - Modern Flatpak wrapper management

        A comprehensive tool for managing Flatpak application wrappers
        with automatic launch method detection and preference management.
        """
        ctx.ensure_object(dict)
        ctx.obj["verbose"] = verbose
        ctx.obj["emit"] = emit
        ctx.obj["emit_verbose"] = emit_verbose
        ctx.obj["config_dir"] = config_dir or os.path.expanduser(
            "~/.config/fplaunchwrapper"
        )

        # Set up environment
        if verbose and console:
            console.print("[bold blue]Verbose mode enabled[/bold blue]")
        if emit and console:
            console.print(
                "[yellow]🧪 EMIT MODE: Commands will be shown but not executed[/yellow]"
            )

    @cli.command()
    @click.argument(
        "bin_dir", type=click.Path(dir_okay=True, writable=True), required=False
    )
    @click.option(
        "--emit", is_flag=True, help="Emit commands instead of executing (dry run)"
    )
    @click.option(
        "--emit-verbose", is_flag=True, help="Show detailed file contents in emit mode"
    )
    @click.pass_context
    def generate(ctx, bin_dir, emit, emit_verbose):
        """Generate Flatpak application wrappers

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
            if console:
                console.print(
                    f"[red]Error:[/red] Failed to import wrapper generator: {e}"
                )
            else:
                print(
                    f"Error: Failed to import wrapper generator: {e}", file=sys.stderr
                )
            return 1

    @cli.command()
    @click.argument("app_name", required=False)
    @click.option("--all", is_flag=True, help="List all wrappers")
    @click.pass_context
    def list(ctx, app_name, all):
        """List installed Flatpak wrappers

        APP_NAME: Show details for specific application
        """
        # Use Python backend
        try:
            from .manage import WrapperManager

            manager = WrapperManager(ctx.obj["config_dir"], ctx.obj["verbose"])

            if app_name:
                # Show specific app details
                return 0 if manager.show_info(app_name) else 1
            else:
                # List all wrappers
                manager.display_wrappers()
                return 0

        except ImportError as e:
            if console:
                console.print(
                    f"[red]Error:[/red] Failed to import wrapper manager: {e}"
                )
            else:
                print(f"Error: Failed to import wrapper manager: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.argument("app_name")
    @click.argument("preference", type=click.Choice(["system", "flatpak"]))
    @click.option(
        "--emit", is_flag=True, help="Emit commands instead of executing (dry run)"
    )
    @click.option(
        "--emit-verbose", is_flag=True, help="Show detailed file contents in emit mode"
    )
    @click.pass_context
    def set_pref(ctx, app_name, preference, emit, emit_verbose):
        """Set launch preference for an application

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
            if console:
                console.print(
                    f"[red]Error:[/red] Failed to import wrapper manager: {e}"
                )
            else:
                print(f"Error: Failed to import wrapper manager: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.argument("app_name")
    @click.option(
        "--emit", is_flag=True, help="Emit commands instead of executing (dry run)"
    )
    @click.pass_context
    def launch(ctx, app_name, emit):
        """Launch a Flatpak application

        APP_NAME: Application name to launch
        """
        emit_mode = emit or ctx.obj["emit"]

        script_path = find_fplaunch_script("fplaunch-launch")
        if not script_path:
            # Try direct wrapper execution
            wrapper_path = Path(ctx.obj["config_dir"]) / "bin" / app_name
            if wrapper_path.exists():
                script_path = wrapper_path
            else:
                if console:
                    console.print("[red]Error:[/red] Launch script not found")
                else:
                    print("Error: Launch script not found")
                return 1

        cmd = [str(script_path), app_name]
        result = run_command(
            cmd, f"Launching {app_name}", show_output=False, emit_mode=emit_mode
        )

        if result.returncode != 0 and not emit_mode:
            if console:
                console.print(
                    f"[red]✗[/red] Failed to launch {app_name}: {result.stderr}"
                )
            else:
                print(f"Failed to launch {app_name}: {result.stderr}")
            return result.returncode

        return 0

    @cli.command()
    @click.argument("app_name")
    @click.option(
        "--emit", is_flag=True, help="Emit commands instead of executing (dry run)"
    )
    @click.pass_context
    def remove(ctx, app_name, emit):
        """Remove a Flatpak wrapper

        APP_NAME: Application name to remove
        """
        emit_mode = emit or ctx.obj["emit"]

        script_path = find_fplaunch_script("fplaunch-manage")
        if not script_path:
            if console:
                console.print("[red]Error:[/red] fplaunch-manage script not found")
            else:
                print("Error: fplaunch-manage script not found")
            return 1

        cmd = [str(script_path), "remove", app_name]
        result = run_command(
            cmd, f"Removing wrapper for {app_name}", emit_mode=emit_mode
        )

        if result.returncode == 0:
            if console:
                console.print(
                    f"[green]✓[/green] Removed wrapper for [bold]{app_name}[/bold]"
                )
            else:
                print(f"Removed wrapper for {app_name}")
        elif not emit_mode:
            if console:
                console.print(f"[red]✗[/red] Failed to remove wrapper: {result.stderr}")
            else:
                print(f"Failed to remove wrapper: {result.stderr}")
            return result.returncode

        return 0

    @cli.command()
    @click.option(
        "--emit", is_flag=True, help="Emit commands instead of executing (dry run)"
    )
    @click.pass_context
    def monitor(ctx, emit):
        """Start Flatpak monitoring daemon

        Monitors for Flatpak installation changes and automatically
        regenerates wrappers when applications are installed or removed.
        """
        emit_mode = emit or ctx.obj["emit"]

        if emit_mode:
            if console:
                console.print(
                    "[cyan]📋 EMIT:[/cyan] Would start Flatpak monitoring daemon"
                )
                console.print(
                    "[dim]   Purpose: Monitor Flatpak installations and auto-regenerate wrappers[/dim]"
                )
            else:
                print("EMIT: Would start Flatpak monitoring daemon")
                print(
                    "  Purpose: Monitor Flatpak installations and auto-regenerate wrappers"
                )
            return 0

        try:
            from lib.flatpak_monitor import start_flatpak_monitoring

            if console:
                console.print("[bold blue]Starting Flatpak monitoring...[/bold blue]")
                console.print("Press Ctrl+C to stop")

            monitor = start_flatpak_monitoring(daemon=False)

            if console:
                console.print("[green]✓[/green] Monitoring stopped")

        except ImportError:
            if console:
                console.print(
                    "[red]Error:[/red] Flatpak monitoring not available (install watchdog)"
                )
            else:
                print("Error: Flatpak monitoring not available (install watchdog)")
            return 1

        return 0

    @cli.command()
    @click.option(
        "--emit", is_flag=True, help="Emit commands instead of executing (dry run)"
    )
    @click.option(
        "--emit-verbose", is_flag=True, help="Show detailed file contents in emit mode"
    )
    @click.option(
        "--bin-dir", type=click.Path(dir_okay=True), help="Wrapper bin directory"
    )
    @click.option(
        "--script",
        type=click.Path(exists=True),
        help="Path to wrapper generation script",
    )
    @click.pass_context
    def setup_systemd(ctx, emit, emit_verbose, bin_dir, script):
        """Set up automatic Flatpak wrapper management

        This command sets up systemd user services for automatic wrapper
        regeneration when Flatpak applications are installed or removed.
        """
        try:
            from lib.systemd_setup import SystemdSetup

            setup = SystemdSetup(
                bin_dir=bin_dir,
                wrapper_script=script,
                emit_mode=emit or ctx.obj["emit"],
                emit_verbose=emit_verbose or ctx.obj["emit_verbose"],
            )
            return setup.run()

        except ImportError as e:
            if console:
                console.print(f"[red]Error:[/red] Failed to import systemd setup: {e}")
            else:
                print(f"Error: Failed to import systemd setup: {e}", file=sys.stderr)
            return 1

    @cli.command()
    @click.option(
        "--emit", is_flag=True, help="Emit commands instead of executing (dry run)"
    )
    @click.pass_context
    def config(ctx, emit):
        """Show current configuration

        Display current fplaunchwrapper configuration and settings.
        """
        emit_mode = emit or ctx.obj["emit"]

        if emit_mode:
            if console:
                console.print(
                    "[cyan]📋 EMIT:[/cyan] Would display current configuration"
                )
                console.print(
                    "[dim]   Purpose: Show fplaunchwrapper settings and directories[/dim]"
                )
            else:
                print("EMIT: Would display current configuration")
                print("  Purpose: Show fplaunchwrapper settings and directories")
            return 0

        try:
            from lib.config_manager import create_config_manager

            config = create_config_manager()

            if console:
                # Display configuration with rich formatting
                console.print(
                    Panel.fit(
                        f"[bold]Configuration Directory:[/bold] {config.config_dir}\n"
                        f"[bold]Data Directory:[/bold] {config.data_dir}\n"
                        f"[bold]Bin Directory:[/bold] {config.config.bin_dir}\n"
                        f"[bold]Debug Mode:[/bold] {config.config.debug_mode}\n"
                        f"[bold]Log Level:[/bold] {config.config.log_level}\n"
                        f"[bold]Blocked Apps:[/bold] {', '.join(config.config.blocklist) if config.config.blocklist else 'None'}",
                        title="fplaunchwrapper Configuration",
                    )
                )
            else:
                print("Configuration:")
                print(f"  Config dir: {config.config_dir}")
                print(f"  Data dir: {config.data_dir}")
                print(f"  Bin dir: {config.config.bin_dir}")
                print(f"  Debug mode: {config.config.debug_mode}")
                print(f"  Log level: {config.config.log_level}")
                print(f"  Blocked apps: {config.config.blocklist}")

        except ImportError:
            if console:
                console.print(
                    "[red]Error:[/red] Configuration management not available"
                )
            else:
                print("Error: Configuration management not available")
            return 1

        return 0

    if __name__ == "__main__":
        cli()

else:
    # Fallback CLI without Click
    def main():
        """Fallback CLI without Click"""
        if len(sys.argv) < 2:
            print("Usage: python cli.py <command> [args...]")
            print(
                "Available commands: generate, list, set-pref, launch, remove, monitor, config"
            )
            sys.exit(1)

        command = sys.argv[1]

        if command == "generate":
            bin_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/bin")
            script_path = find_fplaunch_script("fplaunch-generate")
            if script_path:
                result = run_command(
                    [str(script_path), bin_dir], f"Generating wrappers in {bin_dir}"
                )
                print(
                    "Wrapper generation completed"
                    if result.returncode == 0
                    else f"Failed: {result.stderr}"
                )
            else:
                print("Error: fplaunch-generate script not found")

        elif command == "list":
            script_path = find_fplaunch_script("fplaunch-manage")
            if script_path:
                result = run_command([str(script_path), "list"], "Listing wrappers")
                print(
                    result.stdout
                    if result.returncode == 0
                    else f"Failed: {result.stderr}"
                )
            else:
                print("Error: fplaunch-manage script not found")

        else:
            print(f"Unknown command: {command}")
            print(
                "Available commands: generate, list, set-pref, launch, remove, monitor, config"
            )

    if __name__ == "__main__":
        main()
