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

from rich.console import Console

console = Console()


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
                    for line in str(result.stdout).split("\n"):
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
            console.print(f"[red]✗[/red] {message}")
        elif level == "warning":
            console.print(f"[yellow]⚠[/yellow] {message}")
        elif level == "success":
            console.print(f"[green]✓[/green] {message}")
        elif level == "info" or level == "":
            console.print(message)

    def check_prerequisites(self) -> bool:
        """Check if prerequisites are met with detailed error reporting."""
        # Check if Flatpak is installed
        if not self._command_available("flatpak"):
            self.log(
                "Error: Flatpak not installed. Please install Flatpak first.", "error"
            )
            return False

        # Check if wrapper script exists
        if self.wrapper_script.startswith(f"{sys.executable} -m"):
            module_name = self.wrapper_script.split()[-1]
            self.log(f"Using Python module: {module_name}")
        else:
            script_path = self.wrapper_script.split()[0]
            if script_path.startswith("/") or script_path.startswith("."):
                if not os.path.exists(script_path):
                    self.log(
                        f"Error: Wrapper script not found at {script_path}",
                        "error",
                    )
                    return False
                if not os.access(script_path, os.X_OK):
                    self.log(
                        f"Warning: Wrapper script at {script_path} is not executable",
                        "warning",
                    )
            else:
                if not shutil.which(script_path):
                    self.log(
                        f"Error: Wrapper script '{script_path}' not found in PATH",
                        "error",
                    )
                    return False

        # Check if systemd is available
        if not self._systemd_available():
            self.log(
                "Systemd user services not available, will try cron fallback.",
                "warning",
            )

        # Check if bin directory is valid
        try:
            if not self.bin_dir.exists():
                self.log(
                    f"Warning: Bin directory {self.bin_dir} does not exist, will be created",
                    "warning",
                )
            elif not os.access(self.bin_dir, os.W_OK):
                self.log(
                    f"Error: Bin directory {self.bin_dir} is not writable",
                    "error",
                )
                return False
        except Exception as e:
            self.log(
                f"Error checking bin directory: {e}",
                "error",
            )
            return False

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
Unit=flatpak-wrappers.service

[Install]
WantedBy=timers.target
"""

    def install_systemd_units(self) -> bool:
        """Install and enable systemd units with detailed error handling."""
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
            try:
                self.systemd_unit_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.log(f"Failed to create systemd unit directory: {e}", "error")
                return False

            # Write unit files
            service_unit = self.systemd_unit_dir / "flatpak-wrappers.service"
            path_unit = self.systemd_unit_dir / "flatpak-wrappers.path"
            timer_unit = self.systemd_unit_dir / "flatpak-wrappers.timer"

            try:
                service_unit.write_text(self.create_service_unit())
                path_unit.write_text(self.create_path_unit())
                timer_unit.write_text(self.create_timer_unit())
            except Exception as e:
                self.log(f"Failed to write systemd unit files: {e}", "error")
                return False

            self.log("Created systemd unit files")

            # Get systemctl path
            systemctl_path = shutil.which("systemctl")
            if not systemctl_path:
                self.log("systemctl not found, cannot manage systemd units", "error")
                return False

            # Reload daemon
            try:
                result = subprocess.run(
                    [systemctl_path, "--user", "daemon-reload"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.log(
                        f"Failed to reload systemd daemon: {result.stderr}", "error"
                    )
                    return False
            except Exception as e:
                self.log(f"Failed to reload systemd daemon: {e}", "error")
                return False

            # Enable and start path unit
            try:
                result = subprocess.run(
                    [systemctl_path, "--user", "enable", "flatpak-wrappers.path"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.log(f"Failed to enable path unit: {result.stderr}", "error")
                    return False
            except Exception as e:
                self.log(f"Failed to enable path unit: {e}", "error")
                return False

            try:
                result = subprocess.run(
                    [systemctl_path, "--user", "start", "flatpak-wrappers.path"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.log(f"Failed to start path unit: {result.stderr}", "error")
                    return False
            except Exception as e:
                self.log(f"Failed to start path unit: {e}", "error")
                return False

            # Enable and start timer unit
            try:
                result = subprocess.run(
                    [systemctl_path, "--user", "enable", "flatpak-wrappers.timer"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.log(f"Failed to enable timer unit: {result.stderr}", "error")
                    return False
            except Exception as e:
                self.log(f"Failed to enable timer unit: {e}", "error")
                return False

            try:
                result = subprocess.run(
                    [systemctl_path, "--user", "start", "flatpak-wrappers.timer"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.log(f"Failed to start timer unit: {result.stderr}", "error")
                    return False
            except Exception as e:
                self.log(f"Failed to start timer unit: {e}", "error")
                return False

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

    def install_cron_job(self, cron_interval: int = 6) -> bool:
        """Install cron job as fallback."""
        if self.emit_mode:
            self.log(f"EMIT: Would check for crontab")
            self.log(
                f"EMIT: Would install cron job: 0 */{cron_interval} * * * {self.wrapper_script} {self.bin_dir}"
            )
            return True

        crontab_path = shutil.which("crontab")
        if not crontab_path:
            self.log("Neither systemd nor crontab available.", "error")
            self.log(
                f"Please run '{self.wrapper_script} {self.bin_dir}' manually to update wrappers.",
            )
            return False

        try:
            cron_job = f"0 */{cron_interval} * * * {self.wrapper_script} {self.bin_dir}"

            # Check if cron job already exists
            result = subprocess.run(
                [crontab_path, "-l"],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and self.wrapper_script in str(result.stdout):
                self.log(
                    f"Cron job already exists. Wrappers will update every {cron_interval} hours."
                )
                return True

            # Add cron job
            if result.returncode == 0:
                new_cron = str(result.stdout).rstrip() + "\n" + cron_job + "\n"
            else:
                new_cron = cron_job + "\n"

            subprocess.run(
                [crontab_path, "-"],
                check=False,
                input=new_cron,
                text=True,
                capture_output=True,
            )

            self.log(
                f"Cron job added for wrapper updates every {cron_interval} hours.",
                "success",
            )
            self.log("(System Flatpak changes require manual run.)")

            return True

        except Exception as e:
            self.log(f"Failed to install cron job: {e}", "error")
            return False

    def run(self, cron_interval: int = 6) -> int:
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

            if self.install_cron_job(cron_interval):
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

            import shlex

            safe_wrapper_script = shlex.quote(str(self.wrapper_script))
            safe_bin_dir = shlex.quote(str(self.bin_dir))
            safe_app_id = shlex.quote(str(app_id))

            service_content = f"""[Unit]
Description=Generate wrapper for {app_id}

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'test -x {safe_wrapper_script} && {safe_wrapper_script} {safe_bin_dir} {safe_app_id}'
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
                text=True,
            )

            if result.returncode == 0:
                self.log("Reloaded systemd user daemon", "success")
                return True
            else:
                self.log(
                    f"Failed to reload systemd user daemon: {result.stderr}", "error"
                )
                return False

        except Exception as e:
            self.log(f"Error reloading services: {e}", "error")
            return False

    def start_unit(self, unit_name: str) -> bool:
        """Start a systemd unit."""
        systemctl_path = shutil.which("systemctl")
        if not systemctl_path:
            self.log("systemctl not found", "error")
            return False

        try:
            if self.emit_mode:
                self.log(f"EMIT: Would start {unit_name}")
                return True

            result = subprocess.run(
                [systemctl_path, "--user", "start", unit_name],
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.log(f"Started {unit_name}", "success")
                return True
            else:
                self.log(f"Failed to start {unit_name}: {result.stderr}", "error")
                return False

        except Exception as e:
            self.log(f"Error starting {unit_name}: {e}", "error")
            return False

    def stop_unit(self, unit_name: str) -> bool:
        """Stop a systemd unit."""
        systemctl_path = shutil.which("systemctl")
        if not systemctl_path:
            self.log("systemctl not found", "error")
            return False

        try:
            if self.emit_mode:
                self.log(f"EMIT: Would stop {unit_name}")
                return True

            result = subprocess.run(
                [systemctl_path, "--user", "stop", unit_name],
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.log(f"Stopped {unit_name}", "success")
                return True
            else:
                self.log(f"Failed to stop {unit_name}: {result.stderr}", "error")
                return False

        except Exception as e:
            self.log(f"Error stopping {unit_name}: {e}", "error")
            return False

    def restart_unit(self, unit_name: str) -> bool:
        """Restart a systemd unit."""
        systemctl_path = shutil.which("systemctl")
        if not systemctl_path:
            self.log("systemctl not found", "error")
            return False

        try:
            if self.emit_mode:
                self.log(f"EMIT: Would restart {unit_name}")
                return True

            result = subprocess.run(
                [systemctl_path, "--user", "restart", unit_name],
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.log(f"Restarted {unit_name}", "success")
                return True
            else:
                self.log(f"Failed to restart {unit_name}: {result.stderr}", "error")
                return False

        except Exception as e:
            self.log(f"Error restarting {unit_name}: {e}", "error")
            return False

    def reload_unit(self, unit_name: str) -> bool:
        """Reload a systemd unit."""
        systemctl_path = shutil.which("systemctl")
        if not systemctl_path:
            self.log("systemctl not found", "error")
            return False

        try:
            if self.emit_mode:
                self.log(f"EMIT: Would reload {unit_name}")
                return True

            result = subprocess.run(
                [systemctl_path, "--user", "reload", unit_name],
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.log(f"Reloaded {unit_name}", "success")
                return True
            else:
                self.log(f"Failed to reload {unit_name}: {result.stderr}", "error")
                return False

        except Exception as e:
            self.log(f"Error reloading {unit_name}: {e}", "error")
            return False

    def show_unit_logs(self, unit_name: str, lines: int = 20) -> str:
        """Show logs for a systemd unit."""
        journalctl_path = shutil.which("journalctl")
        if not journalctl_path:
            self.log("journalctl not found", "error")
            return ""

        try:
            if self.emit_mode:
                self.log(f"EMIT: Would show logs for {unit_name}")
                return ""

            result = subprocess.run(
                [
                    journalctl_path,
                    "--user",
                    "-u",
                    unit_name,
                    "-n",
                    str(lines),
                    "--no-pager",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return str(result.stdout)
            else:
                self.log(
                    f"Failed to get logs for {unit_name}: {result.stderr}", "error"
                )
                return ""

        except Exception as e:
            self.log(f"Error getting logs for {unit_name}: {e}", "error")
            return ""

    def list_all_units(self) -> list[str]:
        """List all flatpak-related systemd units."""
        try:
            units = []
            # Glob doesn't support brace expansion, need separate patterns
            for pattern in ["flatpak-*.service", "flatpak-*.path", "flatpak-*.timer"]:
                for unit_file in self.systemd_unit_dir.glob(pattern):
                    units.append(unit_file.name)
            return sorted(units)
        except Exception as e:
            self.log(f"Error listing units: {e}", "error")
            return []

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

            if not self.systemd_unit_dir.exists():
                self.log("No systemd units to disable", "info")
                return True

            unit_names = [
                "flatpak-wrappers.service",
                "flatpak-wrappers.path",
                "flatpak-wrappers.timer",
            ]

            success = True
            for unit_name in unit_names:
                unit_path = self.systemd_unit_dir / unit_name
                if unit_path.exists():
                    try:
                        subprocess.run(
                            ["systemctl", "--user", "disable", unit_name],
                            check=False,
                            capture_output=True,
                        )
                        subprocess.run(
                            ["systemctl", "--user", "stop", unit_name],
                            check=False,
                            capture_output=True,
                        )
                        unit_path.unlink()
                        self.log(f"Disabled and removed {unit_name}", "success")
                    except Exception as e:
                        self.log(f"Failed to remove {unit_name}: {e}", "error")
                        success = False

            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=False,
                capture_output=True,
            )

            return success

        except Exception as e:
            self.log(f"Error disabling systemd units: {e}", "error")
            return False

    def check_systemd_status(self) -> dict:
        """Check the status of systemd timer units with detailed information."""
        try:
            systemctl_path = shutil.which("systemctl")
            if not systemctl_path:
                return {
                    "enabled": False,
                    "active": False,
                    "units": {},
                    "failed": False,
                    "last_run": None,
                    "next_run": None,
                    "load_state": None,
                }

            status = {
                "enabled": False,
                "active": False,
                "failed": False,
                "last_run": None,
                "next_run": None,
                "load_state": None,
                "units": {},
            }

            unit_names = [
                "flatpak-wrappers.service",
                "flatpak-wrappers.path",
                "flatpak-wrappers.timer",
            ]

            for unit_name in unit_names:
                unit_info = {}

                # Check if unit file exists
                unit_path = self.systemd_unit_dir / unit_name
                unit_info["exists"] = unit_path.exists()

                # Check if enabled
                result = subprocess.run(
                    ["systemctl", "--user", "is-enabled", unit_name],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                unit_info["enabled"] = result.returncode == 0
                unit_info["enabled_status"] = str(result.stdout).strip()

                # Check if active
                result = subprocess.run(
                    ["systemctl", "--user", "is-active", unit_name],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                unit_info["active"] = result.returncode == 0
                unit_info["active_status"] = str(result.stdout).strip()

                # Check load state
                result = subprocess.run(
                    ["systemctl", "--user", "show", unit_name, "--property=LoadState"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    parts = str(result.stdout).strip().split("=", 1)
                    if len(parts) == 2:
                        unit_info["load_state"] = parts[1]

                # Check active state details
                result = subprocess.run(
                    [
                        "systemctl",
                        "--user",
                        "show",
                        unit_name,
                        "--property=ActiveState",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    parts = str(result.stdout).strip().split("=", 1)
                    if len(parts) == 2:
                        unit_info["active_state"] = parts[1]

                # Check for failures
                result = subprocess.run(
                    ["systemctl", "--user", "show", unit_name, "--property=Result"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    parts = str(result.stdout).strip().split("=", 1)
                    if len(parts) == 2:
                        unit_info["result"] = parts[1]
                        if unit_info["result"] == "fail":
                            status["failed"] = True

                # Get last run time for services/timers
                if unit_name.endswith(".service") or unit_name.endswith(".timer"):
                    result = subprocess.run(
                        [
                            "systemctl",
                            "--user",
                            "show",
                            unit_name,
                            "--property=ActiveEnterTimestamp",
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        parts = str(result.stdout).strip().split("=", 1)
                        if len(parts) == 2:
                            timestamp = parts[1]
                            if timestamp:
                                unit_info["last_run"] = timestamp

                # Get next run time for timers
                if unit_name.endswith(".timer"):
                    result = subprocess.run(
                        ["systemctl", "--user", "list-timers", unit_name, "--no-pager"],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0 and unit_name in str(result.stdout):
                        lines = str(result.stdout).strip().split("\n")[1:]
                        for line in lines:
                            if unit_name in line:
                                parts = line.split()
                                if len(parts) > 1:
                                    unit_info["next_run"] = parts[0] + " " + parts[1]

                status["units"][unit_name] = unit_info

                if unit_info["enabled"]:
                    status["enabled"] = True
                if unit_info["active"]:
                    status["active"] = True

                # Update overall load state
                if unit_info.get("load_state"):
                    status["load_state"] = unit_info["load_state"]

            return status

        except Exception as e:
            self.log(f"Error checking systemd status: {e}", "error")
            return {
                "enabled": False,
                "active": False,
                "failed": False,
                "last_run": None,
                "next_run": None,
                "load_state": None,
                "units": {},
            }

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
   - Runs wrapper regeneration at configured interval (default: 6 hours)

Examples:
  python -m systemd_setup                    # Auto-detect settings
  python -m systemd_setup --bin-dir ~/bin   # Custom bin directory
  python -m systemd_setup --script /path/to/generate  # Custom script
  python -m systemd_setup --cron-interval 4  # Run every 4 hours
        """,
    )

    parser.add_argument("--bin-dir", help="Wrapper bin directory (default: ~/bin)")

    parser.add_argument("--script", help="Path to wrapper generation script")

    parser.add_argument(
        "--cron-interval",
        type=int,
        default=6,
        help="Cron interval in hours (default: 6 hours, minimum: 1 hour)",
    )

    args = parser.parse_args()

    setup = SystemdSetup(bin_dir=args.bin_dir, wrapper_script=args.script)
    # Pass cron interval to run method
    return setup.run(cron_interval=args.cron_interval)


if __name__ == "__main__":
    sys.exit(main())
