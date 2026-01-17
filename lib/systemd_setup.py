#!/usr/bin/env python3
"""Systemd setup functionality for fplaunchwrapper
Replaces fplaunch-setup-systemd bash script with Python implementation.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from rich.console import Console

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


class SystemdSetup:
    """Set up systemd units for automatic wrapper management."""

    def __init__(
        self,
        bin_dir: str | None = None,
        wrapper_script: str | None = None,
        emit_mode: bool = False,
        emit_verbose: bool = False,
    ) -> None:
        self.bin_dir = Path(bin_dir or (Path.home() / "bin"))
        self.wrapper_script = wrapper_script or self._find_wrapper_script()
        self.systemd_unit_dir = self._get_systemd_unit_dir()
        self.flatpak_bin_dir = self._detect_flatpak_bin_dir()
        self.emit_mode = emit_mode
        self.emit_verbose = emit_verbose

    def _find_wrapper_script(self) -> str:
        """Find the wrapper generation script."""
        # Try various locations
        candidates = [
            Path.cwd() / "fplaunch-generate",
            Path.cwd() / "lib" / "generate.py",
            Path.home() / ".local" / "bin" / "fplaunch-generate",
            Path("/usr/local/bin") / "fplaunch-generate",
            Path("/usr/bin") / "fplaunch-generate",
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return str(candidate)

        # Fallback to Python module
        return f"{sys.executable} -m fplaunch.generate"

    def _get_systemd_unit_dir(self) -> Path:
        """Get systemd user unit directory."""
        xdg_config_home = os.environ.get(
            "XDG_CONFIG_HOME",
            str(Path.home() / ".config"),
        )
        return Path(xdg_config_home) / "systemd" / "user"

    def _detect_flatpak_bin_dir(self) -> str:
        """Detect Flatpak binary directory."""
        candidates = [
            str(Path.home() / ".local" / "share" / "flatpak" / "exports" / "bin"),
            "/var/lib/flatpak/exports/bin",
        ]

        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate

        # Try to get from flatpak command
        flatpak_path = shutil.which("flatpak")
        if flatpak_path:
            try:
                result = subprocess.run(
                    [flatpak_path, "--print-updated-env"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    # Look for PATH entries
                    for line in result.stdout.split("\n"):
                        if line.startswith("PATH="):
                            path_value = line.split("=", 1)[1]
                            paths = path_value.split(":")
                            for path in paths:
                                if (
                                    "flatpak" in path
                                    and "exports" in path
                                    and "bin" in path
                                ):
                                    return path
            except (subprocess.CalledProcessError, OSError):
                pass

        # Default fallback
        return str(Path.home() / ".local" / "share" / "flatpak" / "exports" / "bin")

    def log(self, message: str, level: str = "info") -> None:
        """Log a message."""
        if level == "error":
            if console:
                console.print(f"[red]✗[/red] {message}", file=sys.stderr)
            else:
                print(f"Error: {message}", file=sys.stderr)
        elif level == "warning":
            if console:
                console.print(f"[yellow]⚠[/yellow] {message}")
            else:
                print(f"Warning: {message}")
        elif level == "success":
            if console:
                console.print(f"[green]✓[/green] {message}")
            else:
                print(f"✓ {message}")
        elif level == "info" or level == "":
            if console:
                console.print(message)
            else:
                print(message)

    def check_prerequisites(self) -> bool:
        """Check if prerequisites are met."""
        # Check if Flatpak is installed
        if not self._command_available("flatpak"):
            self.log("Error: Flatpak not installed.", "error")
            return False

        # Check if wrapper script exists
        if not os.path.exists(self.wrapper_script.split()[0]):
            self.log(
                f"Error: Wrapper script not found at {self.wrapper_script}",
                "error",
            )
            return False

        # Check if systemd is available
        if not self._systemd_available():
            self.log(
                "Systemd user services not available, will try cron fallback.",
                "warning",
            )

        return True

    def _command_available(self, command: str) -> bool:
        """Check if a command is available."""
        return shutil.which(command) is not None

    def _systemd_available(self) -> bool:
        """Check if systemd user services are available."""
        systemctl_path = shutil.which("systemctl")
        if not systemctl_path:
            return False
        try:
            result = subprocess.run(
                [systemctl_path, "--user", "status"],
                check=False,
                capture_output=True,
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, OSError):
            return False

    def create_service_unit(self) -> str:
        """Create the service unit content."""
        return f"""[Unit]
Description=Generate Flatpak wrapper scripts

[Service]
Type=oneshot
ExecStart={self.wrapper_script} {self.bin_dir}
"""

    def create_path_unit(self) -> str:
        """Create the path unit content."""
        return f"""[Unit]
Description=Watch for Flatpak app changes

[Path]
PathChanged={self.flatpak_bin_dir}
Unit=flatpak-wrappers.service

[Install]
WantedBy=default.target
"""

    def create_timer_unit(self) -> str:
        """Create the timer unit content."""
        return """[Unit]
Description=Timer for Flatpak wrapper generation

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
"""

    def install_systemd_units(self) -> bool:
        """Install and enable systemd units."""
        try:
            if self.emit_mode:
                # In emit mode, just show what would be done
                self.log("EMIT: Would create systemd unit directory")

                service_unit_path = self.systemd_unit_dir / "flatpak-wrappers.service"
                path_unit_path = self.systemd_unit_dir / "flatpak-wrappers.path"
                timer_unit_path = self.systemd_unit_dir / "flatpak-wrappers.timer"

                self.log(f"EMIT: Would write service unit to {service_unit_path}")
                self.log(f"EMIT: Would write path unit to {path_unit_path}")
                self.log(f"EMIT: Would write timer unit to {timer_unit_path}")

                # Show file contents if verbose emit mode
                if self.emit_verbose:
                    service_content = self.create_service_unit()
                    path_content = self.create_path_unit()
                    timer_content = self.create_timer_unit()

                    if console:
                        from rich.panel import Panel

                        console.print(
                            Panel.fit(
                                service_content,
                                title="📄 flatpak-wrappers.service",
                                border_style="blue",
                            ),
                        )
                        console.print(
                            Panel.fit(
                                path_content,
                                title="📄 flatpak-wrappers.path",
                                border_style="green",
                            ),
                        )
                        console.print(
                            Panel.fit(
                                timer_content,
                                title="📄 flatpak-wrappers.timer",
                                border_style="yellow",
                            ),
                        )
                        # Also print raw contents for stdout capture in tests
                        print(service_content)
                        print(path_content)
                        print(timer_content)
                    else:
                        self.log("=" * 50)
                        self.log("Service unit content:")
                        self.log("-" * 30)
                        for line in service_content.split("\n"):
                            self.log(line)
                        self.log("=" * 50)
                        self.log("Path unit content:")
                        self.log("-" * 30)
                        for line in path_content.split("\n"):
                            self.log(line)
                        self.log("=" * 50)
                        self.log("Timer unit content:")
                        self.log("-" * 30)
                        for line in timer_content.split("\n"):
                            self.log(line)
                        self.log("=" * 50)

                self.log("EMIT: Would run: systemctl --user daemon-reload")
                self.log(
                    "EMIT: Would run: systemctl --user enable flatpak-wrappers.path",
                )
                self.log(
                    "EMIT: Would run: systemctl --user start flatpak-wrappers.path",
                )
                self.log(
                    "EMIT: Would run: systemctl --user enable flatpak-wrappers.timer",
                )
                self.log(
                    "EMIT: Would run: systemctl --user start flatpak-wrappers.timer",
                )
                return True
            # Create unit directory
            self.systemd_unit_dir.mkdir(parents=True, exist_ok=True)

            # Write unit files
            service_unit = self.systemd_unit_dir / "flatpak-wrappers.service"
            path_unit = self.systemd_unit_dir / "flatpak-wrappers.path"
            timer_unit = self.systemd_unit_dir / "flatpak-wrappers.timer"

            service_unit.write_text(self.create_service_unit())
            path_unit.write_text(self.create_path_unit())
            timer_unit.write_text(self.create_timer_unit())

            self.log("Created systemd unit files")

            # Get systemctl path
            systemctl_path = shutil.which("systemctl")
            if not systemctl_path:
                self.log("systemctl not found, cannot manage systemd units", "error")
                return False

            # Reload daemon
            subprocess.run(
                [systemctl_path, "--user", "daemon-reload"],
                check=False,
                capture_output=True,
            )

            # Enable and start path unit
            subprocess.run(
                [systemctl_path, "--user", "enable", "flatpak-wrappers.path"],
                check=False,
                capture_output=True,
            )
            subprocess.run(
                [systemctl_path, "--user", "start", "flatpak-wrappers.path"],
                check=False,
                capture_output=True,
            )

            # Enable and start timer unit
            subprocess.run(
                [systemctl_path, "--user", "enable", "flatpak-wrappers.timer"],
                check=False,
                capture_output=True,
            )
            subprocess.run(
                [systemctl_path, "--user", "start", "flatpak-wrappers.timer"],
                check=False,
                capture_output=True,
            )

            self.log("Systemd units installed and started", "success")
            self.log(
                "Wrappers will update automatically on user Flatpak changes and daily",
            )
            self.log(
                "(System Flatpak changes require manual run or wait for timer)",
            )

            return True

        except Exception as e:
            self.log(f"Failed to install systemd units: {e}", "error")
            return False

    def install_cron_job(self) -> bool:
        """Install cron job as fallback."""
        crontab_path = shutil.which("crontab")
        if not crontab_path:
            self.log("Neither systemd nor crontab available.", "error")
            self.log(
                f"Please run '{self.wrapper_script} {self.bin_dir}' manually to update wrappers.",
            )
            return False

        try:
            cron_job = f"0 */6 * * * {self.wrapper_script} {self.bin_dir}"

            # Check if cron job already exists
            result = subprocess.run(
                [crontab_path, "-l"],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and self.wrapper_script in result.stdout:
                self.log("Cron job already exists. Wrappers will update every 6 hours.")
                return True

            # Add cron job
            if result.returncode == 0:
                new_cron = result.stdout.rstrip() + "\n" + cron_job + "\n"
            else:
                new_cron = cron_job + "\n"

            subprocess.run(
                [crontab_path, "-"],
                check=False,
                input=new_cron,
                text=True,
                capture_output=True,
            )

            self.log("Cron job added for wrapper updates every 6 hours.", "success")
            self.log("(System Flatpak changes require manual run.)")

            return True

        except Exception as e:
            self.log(f"Failed to install cron job: {e}", "error")
            return False

    def run(self) -> int:
        """Main setup process."""
        try:
            self.log("Setting up automatic Flatpak wrapper management...")

            # Check prerequisites
            if not self.check_prerequisites():
                return 1

            self.log(f"Using wrapper script: {self.wrapper_script}")
            self.log(f"Using bin directory: {self.bin_dir}")
            self.log(f"Monitoring Flatpak bin directory: {self.flatpak_bin_dir}")

            # Try systemd first, then cron fallback
            if self._systemd_available():
                if self.install_systemd_units():
                    return 0
            else:
                self.log("Systemd not available, trying cron fallback...")

            if self.install_cron_job():
                return 0

            # Neither systemd nor cron worked
            self.log("Automatic setup failed.", "error")
            self.log(
                f"Please run '{self.wrapper_script} {self.bin_dir}' manually to update wrappers.",
            )
            return 1

        except Exception as e:
            self.log(f"Setup failed: {e}", "error")
            return 1

    # App-specific service management
    def enable_app_service(self, app_id: str) -> bool:
        """Enable automatic wrapper monitoring for a specific app.
        
        Creates an app-specific timer that monitors for wrapper updates.
        """
        if not app_id:
            return False

        systemctl_path = shutil.which("systemctl")
        if not systemctl_path:
            self.log("systemctl not found", "error")
            return False

        try:
            # Create app-specific timer unit
            service_name = f"flatpak-wrapper-{app_id}.service"
            timer_name = f"flatpak-wrapper-{app_id}.timer"

            if self.emit_mode:
                self.log(f"EMIT: Would create service unit for {app_id}")
                self.log(f"EMIT: Would enable {timer_name}")
                return True

            # Create service unit
            service_content = f"""[Unit]
Description=Generate wrapper for {app_id}

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'test -x {self.wrapper_script} && {self.wrapper_script} {self.bin_dir} {app_id}'
"""

            service_file = self.systemd_unit_dir / service_name
            service_file.write_text(service_content)
            self.log(f"Created service unit: {service_name}")

            # Create timer unit (runs daily for this app)
            timer_content = f"""[Unit]
Description=Timer for {app_id} wrapper generation

[Timer]
OnCalendar=daily
Persistent=true
Unit={service_name}

[Install]
WantedBy=timers.target
"""

            timer_file = self.systemd_unit_dir / timer_name
            timer_file.write_text(timer_content)
            self.log(f"Created timer unit: {timer_name}")

            # Enable the timer
            result = subprocess.run(
                [systemctl_path, "--user", "enable", timer_name],
                check=False,
                capture_output=True,
            )

            if result.returncode == 0:
                self.log(f"Enabled timer for {app_id}", "success")
                return True
            else:
                self.log(f"Failed to enable timer for {app_id}", "error")
                return False

        except Exception as e:
            self.log(f"Error enabling service for {app_id}: {e}", "error")
            return False

    def disable_app_service(self, app_id: str) -> bool:
        """Disable app-specific wrapper monitoring service.
        
        Removes the app-specific timer and service units.
        """
        if not app_id:
            return False

        systemctl_path = shutil.which("systemctl")
        if not systemctl_path:
            self.log("systemctl not found", "error")
            return False

        try:
            timer_name = f"flatpak-wrapper-{app_id}.timer"
            service_name = f"flatpak-wrapper-{app_id}.service"

            if self.emit_mode:
                self.log(f"EMIT: Would disable {timer_name}")
                self.log(f"EMIT: Would remove {service_name}")
                return True

            # Disable timer
            subprocess.run(
                [systemctl_path, "--user", "disable", timer_name],
                check=False,
                capture_output=True,
            )

            # Stop timer if running
            subprocess.run(
                [systemctl_path, "--user", "stop", timer_name],
                check=False,
                capture_output=True,
            )

            # Remove unit files
            timer_file = self.systemd_unit_dir / timer_name
            service_file = self.systemd_unit_dir / service_name

            if timer_file.exists():
                timer_file.unlink()
                self.log(f"Removed timer unit: {timer_name}")

            if service_file.exists():
                service_file.unlink()
                self.log(f"Removed service unit: {service_name}")

            # Reload daemon
            subprocess.run(
                [systemctl_path, "--user", "daemon-reload"],
                check=False,
                capture_output=True,
            )

            self.log(f"Disabled service for {app_id}", "success")
            return True

        except Exception as e:
            self.log(f"Error disabling service for {app_id}: {e}", "error")
            return False

    def reload_services(self) -> bool:
        """Reload systemd user daemon to apply unit changes."""
        systemctl_path = shutil.which("systemctl")
        if not systemctl_path:
            self.log("systemctl not found", "error")
            return False

        try:
            if self.emit_mode:
                self.log("EMIT: Would reload systemd user daemon")
                return True

            result = subprocess.run(
                [systemctl_path, "--user", "daemon-reload"],
                check=False,
                capture_output=True,
            )

            if result.returncode == 0:
                self.log("Reloaded systemd user daemon", "success")
                return True
            else:
                self.log("Failed to reload systemd user daemon", "error")
                return False

        except Exception as e:
            self.log(f"Error reloading services: {e}", "error")
            return False

    def list_app_services(self) -> list[str]:
        """List all app-specific services that are enabled."""
        try:
            apps = []
            for unit_file in self.systemd_unit_dir.glob("flatpak-wrapper-*.timer"):
                # Extract app_id from filename
                app_id = unit_file.stem.replace("flatpak-wrapper-", "")
                apps.append(app_id)
            return sorted(apps)
        except Exception:
            return []

    def disable_systemd_units(self) -> bool:
        """Disable and remove systemd units."""
        try:
            if self.emit_mode:
                self.log("EMIT: Would disable systemd units")
                return True

            # Check if units exist
            if not self.systemd_unit_dir.exists():
                self.log("Systemd unit directory does not exist", "warning")
                return False

            # Disable and remove units
            unit_names = ["flatpak-wrappers.service", "flatpak-wrappers.path", "flatpak-wrappers.timer"]
            
            for unit_name in unit_names:
                unit_path = self.systemd_unit_dir / unit_name
                if unit_path.exists():
                    try:
                        # Disable the unit
                        subprocess.run(
                            ["systemctl", "--user", "disable", unit_name],
                            check=False,
                            capture_output=True,
                        )
                        # Stop the unit
                        subprocess.run(
                            ["systemctl", "--user", "stop", unit_name],
                            check=False,
                            capture_output=True,
                        )
                        # Remove the unit file
                        unit_path.unlink()
                    except Exception:
                        pass

            # Reload systemd daemon
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=False,
                capture_output=True,
            )
            
            return True

        except Exception:
            return False

    def check_systemd_status(self) -> dict:
        """Check the status of systemd timer units."""
        try:
            systemctl_path = shutil.which("systemctl")
            if not systemctl_path:
                return {"enabled": False, "active": False, "units": {}}

            status = {
                "enabled": False,
                "active": False,
                "units": {}
            }

            unit_names = ["flatpak-wrappers.service", "flatpak-wrappers.path", "flatpak-wrappers.timer"]
            
            for unit_name in unit_names:
                # Check if enabled
                result = subprocess.run(
                    ["systemctl", "--user", "is-enabled", unit_name],
                    check=False,
                    capture_output=True,
                )
                enabled = result.returncode == 0
                
                # Check if active
                result = subprocess.run(
                    ["systemctl", "--user", "is-active", unit_name],
                    check=False,
                    capture_output=True,
                )
                active = result.returncode == 0
                
                status["units"][unit_name] = enabled and active
                
                if enabled:
                    status["enabled"] = True
                if active:
                    status["active"] = True

            return status

        except Exception:
            return {"enabled": False, "active": False, "units": {}}

    # Legacy compatibility aliases for testing
    def enable_service(self, app_id: str) -> bool:
        """Legacy alias for enable_app_service (for backward compatibility)."""
        return self.enable_app_service(app_id)

    def disable_service(self, app_id: str) -> bool:
        """Legacy alias for disable_app_service (for backward compatibility)."""
        return self.disable_app_service(app_id)


def main():
    """Command-line interface for systemd setup."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Set up automatic Flatpak wrapper management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script sets up automatic wrapper regeneration using:

1. systemd user services (preferred):
   - Path unit monitors Flatpak binary directory for changes
   - Service regenerates wrappers when apps are installed/removed
   - Timer runs daily regeneration

2. Cron job fallback (if systemd unavailable):
   - Runs wrapper regeneration every 6 hours

Examples:
  python -m systemd_setup                    # Auto-detect settings
  python -m systemd_setup --bin-dir ~/bin   # Custom bin directory
  python -m systemd_setup --script /path/to/generate  # Custom script
        """,
    )

    parser.add_argument("--bin-dir", help="Wrapper bin directory (default: ~/bin)")

    parser.add_argument("--script", help="Path to wrapper generation script")

    args = parser.parse_args()

    setup = SystemdSetup(bin_dir=args.bin_dir, wrapper_script=args.script)
    return setup.run()


if __name__ == "__main__":
    sys.exit(main())
