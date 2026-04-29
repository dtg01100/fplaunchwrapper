#!/usr/bin/env python3
"""Systemd setup functionality for fplaunchwrapper
Replaces fplaunch-setup-systemd bash script with Python implementation.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .logging_utils import LoggingMixin
from .paths import get_default_bin_dir
from .validation import check_path_traversal, validate_app_id


class SystemdSetup(LoggingMixin):
    """Set up systemd units for automatic wrapper management."""

    def __init__(
        self,
        bin_dir: str | Path | None = None,
        config_dir: str | Path | None = None,
        verbose: bool = False,
        emit_mode: bool = False,
        emit_verbose: bool = False,
        wrapper_script: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.bin_dir = Path(bin_dir) if bin_dir else get_default_bin_dir()
        self.config_dir = Path(config_dir) if config_dir else None
        self.wrapper_script = wrapper_script or self._find_wrapper_script()
        self.systemd_unit_dir = get_systemd_unit_dir()
        self.flatpak_bin_dir = self._detect_flatpak_bin_dir()
        self.verbose = verbose
        self.emit_mode = emit_mode
        self.emit_verbose = emit_verbose

    def _find_wrapper_script(self) -> str:
        """Find the wrapper generation script."""
        # Try finding in PATH
        script = shutil.which("fplaunch-generate")
        if script:
            return script

        # Try common locations
        common_paths = [
            "/usr/bin/fplaunch-generate",
            "/usr/local/bin/fplaunch-generate",
            str(Path("~/bin/fplaunch-generate").expanduser()),
            str(Path("~/.local/bin/fplaunch-generate").expanduser()),
        ]
        for p in common_paths:
            if Path(p).is_file() and os.access(p, os.X_OK):
                return p

        # Default to name only if not found
        return "fplaunch-generate"

    def _detect_flatpak_bin_dir(self) -> str:
        """Detect where Flatpak stores application binaries."""
        # Common locations
        paths = [
            "/var/lib/flatpak/exports/bin",
            str(Path("~/.local/share/flatpak/exports/bin").expanduser()),
        ]
        for p in paths:
            if Path(p).is_dir():
                return p
        return ""

    def generate_systemd_service(self) -> str:
        """Generate content for the systemd service file."""
        return f"""[Unit]
Description=Flatpak Wrapper Generator
After=network.target

[Service]
Type=oneshot
ExecStart={self.wrapper_script} {self.bin_dir}
StandardOutput=journal

[Install]
WantedBy=default.target
"""

    def generate_systemd_timer(self, interval: int = 6) -> str:
        """Generate content for the systemd timer file."""
        return f"""[Unit]
Description=Run Flatpak Wrapper Generator every {interval} hours

[Timer]
OnBootSec=5min
OnUnitActiveSec={interval}h
Unit=fplaunch-wrapper.service

[Install]
WantedBy=timers.target
"""

    def install_systemd_units(self, cron_interval: int = 6) -> bool:
        """Install and enable systemd service and timer."""
        if self.emit_mode:
            self.log("EMIT: Would install systemd service and timer", "emit")
            return True

        try:
            self.systemd_unit_dir.mkdir(parents=True, exist_ok=True)

            service_path = self.systemd_unit_dir / "fplaunch-wrapper.service"
            timer_path = self.systemd_unit_dir / "fplaunch-wrapper.timer"

            service_path.write_text(self.generate_systemd_service())
            timer_path.write_text(self.generate_systemd_timer(cron_interval))

            # Reload systemd
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)

            # Enable and start timer
            subprocess.run(
                ["systemctl", "--user", "enable", "--now", "fplaunch-wrapper.timer"],
                check=False,
            )

            self.log(
                f"Systemd service and timer installed (interval: {cron_interval}h)",
                "success",
            )
            return True
        except Exception as e:
            self.log(f"Failed to install systemd units: {e}", "error")
            return False

    def run(self, cron_interval: int = 6) -> int:
        """Main entry point for systemd setup."""
        if self.install_systemd_units(cron_interval):
            return 0
        return 1

    def install_cron_job(self, cron_interval: int = 6) -> bool:
        """Install a cron job as fallback when systemd is not available.

        Args:
            cron_interval: Interval in hours between runs

        Returns:
            True if successful, False otherwise
        """
        if self.emit_mode:
            self.log(f"EMIT: Would install cron job with interval {cron_interval}h", "emit")
            return True

        try:
            if shutil.which("crontab") is None:
                self.log("Cron is not available on this system", "error")
                return False

            cron_dir = Path.home() / ".config" / "cron"
            cron_dir.mkdir(parents=True, exist_ok=True)

            cron_script = cron_dir / "fplaunch-wrapper.sh"
            cron_script.write_text(f"""#!/bin/bash
# Auto-generated by fplaunchwrapper
{self.wrapper_script} {self.bin_dir}
""")
            cron_script.chmod(0o755)

            # Create crontab entry
            cron_entry = f"0 */{cron_interval} * * * {cron_script}\n"

            # Check if crontab already has entry for this script
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            existing = result.stdout if result.returncode == 0 else ""

            script_already_installed = False
            for line in existing.splitlines():
                if line.strip() and not line.strip().startswith("#"):
                    parts = line.split()
                    if (
                        len(parts) >= 6
                        and parts[0] == "0"
                        and parts[1] == "*/{}".format(cron_interval)
                    ):
                        cron_script_path = " ".join(parts[5:])
                        if (
                            str(cron_script) in cron_script_path
                            or cron_script.name in cron_script_path
                        ):
                            script_already_installed = True
                            break

            if not script_already_installed:
                new_cron = existing.rstrip() + "\n" + cron_entry
                subprocess.run(["crontab", "-"], input=new_cron, text=True, check=False)
                self.log(f"Cron job installed (interval: {cron_interval}h)", "success")
            else:
                self.log("Cron job already exists", "info")

            return True
        except Exception as e:
            self.log(f"Failed to install cron job: {e}", "error")
            return False

    def create_service_unit(self) -> str:
        """Create service unit content."""
        return self.generate_systemd_service()

    def create_timer_unit(self) -> str:
        """Create timer unit content."""
        return self.generate_systemd_timer()

    def create_path_unit(self) -> str:
        """Create path unit content for monitoring directory changes."""
        return f"""[Unit]
Description=Monitor Flatpak exports directory for changes

[Path]
PathModified={self.flatpak_bin_dir}
Unit=fplaunch-wrapper.service

[Install]
WantedBy=paths.target
"""

    def check_systemd_status(self) -> dict[str, Any]:
        """Check the status of systemd units.

        Returns:
            Dict with status information for each unit
        """
        result: dict[str, Any] = {
            "service": {"exists": False, "enabled": False, "active": False},
            "timer": {"exists": False, "enabled": False, "active": False},
        }

        # Check if systemctl is available
        if not shutil.which("systemctl"):
            return result

        try:
            # Check service
            proc = subprocess.run(
                ["systemctl", "--user", "is-enabled", "fplaunch-wrapper.service"],
                capture_output=True,
                text=True,
            )
            result["service"]["exists"] = (
                self.systemd_unit_dir / "fplaunch-wrapper.service"
            ).exists()
            result["service"]["enabled"] = proc.returncode == 0

            proc = subprocess.run(
                ["systemctl", "--user", "is-active", "fplaunch-wrapper.service"],
                capture_output=True,
                text=True,
            )
            result["service"]["active"] = proc.stdout.strip() == "active"

            # Check timer
            result["timer"]["exists"] = (self.systemd_unit_dir / "fplaunch-wrapper.timer").exists()
            proc = subprocess.run(
                ["systemctl", "--user", "is-enabled", "fplaunch-wrapper.timer"],
                capture_output=True,
                text=True,
            )
            result["timer"]["enabled"] = proc.returncode == 0

            proc = subprocess.run(
                ["systemctl", "--user", "is-active", "fplaunch-wrapper.timer"],
                capture_output=True,
                text=True,
            )
            result["timer"]["active"] = proc.stdout.strip() == "active"

        except Exception:
            pass

        return result

    def check_prerequisites(self) -> bool:
        """Check that all prerequisites are met.

        Returns:
            True if all prerequisites are met, False otherwise
        """
        # Check flatpak is installed
        if not shutil.which("flatpak"):
            self.log("flatpak command not found", "error")
            return False

        # Check wrapper script exists
        if not shutil.which(self.wrapper_script):
            if not Path(self.wrapper_script).exists():
                self.log(f"Wrapper script not found: {self.wrapper_script}", "error")
                return False

        # Check bin_dir is writable
        if self.bin_dir.exists() and not os.access(self.bin_dir, os.W_OK):
            self.log(f"Bin directory not writable: {self.bin_dir}", "error")
            return False

        return True

    def disable_systemd_units(self) -> bool:
        """Disable and remove systemd units.

        Returns:
            True if successful, False otherwise
        """
        if self.emit_mode:
            self.log("EMIT: Would disable systemd units", "emit")
            return True

        try:
            # Stop and disable timer
            subprocess.run(
                ["systemctl", "--user", "disable", "--now", "fplaunch-wrapper.timer"],
                check=False,
            )

            # Stop and disable service
            subprocess.run(
                ["systemctl", "--user", "disable", "--now", "fplaunch-wrapper.service"],
                check=False,
            )

            # Remove unit files
            service_path = self.systemd_unit_dir / "fplaunch-wrapper.service"
            timer_path = self.systemd_unit_dir / "fplaunch-wrapper.timer"
            path_path = self.systemd_unit_dir / "fplaunch-wrapper.path"

            for unit_path in [service_path, timer_path, path_path]:
                if unit_path.exists():
                    unit_path.unlink()
                    self.log(f"Removed: {unit_path}", "info")

            # Reload systemd
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)

            self.log("Systemd units disabled", "success")
            return True
        except Exception as e:
            self.log(f"Failed to disable systemd units: {e}", "error")
            return False

    def list_all_units(self) -> list[str]:
        """List all fplaunch systemd units.

        Returns:
            List of unit names
        """
        units: list[str] = []
        if not self.systemd_unit_dir.exists():
            return units

        for item in self.systemd_unit_dir.iterdir():
            if item.name.startswith("fplaunch") and item.suffix in (
                ".service",
                ".timer",
                ".path",
            ):
                units.append(item.name)

        return sorted(units)

    def enable_app_service(self, app_id: str) -> bool:
        """Enable per-app systemd service for a Flatpak application.

        Args:
            app_id: The Flatpak application ID

        Returns:
            True if successful, False otherwise
        """
        valid, error = validate_app_id(app_id)
        if not valid:
            self.log(error, "error")
            return False

        if self.emit_mode:
            self.log(f"EMIT: Would enable app service for {app_id}", "emit")
            return True

        try:
            self.systemd_unit_dir.mkdir(parents=True, exist_ok=True)

            safe_app_id = app_id
            service_name = f"fplaunch-{safe_app_id}.service"
            service_path = self.systemd_unit_dir / service_name

            # Use Path.relative_to() for robust path traversal prevention
            safe, error = check_path_traversal(service_path, self.systemd_unit_dir)
            if not safe:
                self.log(f"Path traversal detected in app_id: {error}", "error")
                return False

            # Use shlex.quote for ExecStart argument to avoid accidental unit syntax injection
            exec_app = shlex.quote(safe_app_id)
            service_content = f"""[Unit]
Description=Wrapper for {safe_app_id}
After=network.target

[Service]
Type=oneshot
ExecStart=flatpak run {exec_app}
"""
            service_path.write_text(service_content)

            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
            subprocess.run(["systemctl", "--user", "enable", service_name], check=False)

            self.log(f"Enabled app service for {safe_app_id}", "success")
            return True
        except Exception as e:
            self.log(f"Failed to enable app service: {e}", "error")
            return False

    def disable_app_service(self, app_id: str) -> bool:
        """Disable per-app systemd service for a Flatpak application.

        Args:
            app_id: The Flatpak application ID

        Returns:
            True if successful, False otherwise
        """
        valid, error = validate_app_id(app_id)
        if not valid:
            self.log(error, "error")
            return False

        if self.emit_mode:
            self.log(f"EMIT: Would disable app service for {app_id}", "emit")
            return True

        try:
            safe_app_id = app_id
            service_name = f"fplaunch-{safe_app_id}.service"
            service_path = self.systemd_unit_dir / service_name

            # Use Path.relative_to() for robust path traversal prevention
            safe, error = check_path_traversal(service_path, self.systemd_unit_dir)
            if not safe:
                self.log(f"Path traversal detected in app_id: {error}", "error")
                return False

            subprocess.run(
                ["systemctl", "--user", "disable", service_name],
                check=False,
            )

            if service_path.exists():
                service_path.unlink()

            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)

            self.log(f"Disabled app service for {safe_app_id}", "success")
            return True
        except Exception as e:
            self.log(f"Failed to disable app service: {e}", "error")
            return False

    def list_app_services(self) -> list[str]:
        """List all app-specific services.

        Returns:
            List of app IDs that have services enabled
        """
        apps: list[str] = []
        if not self.systemd_unit_dir.exists():
            return apps

        for item in self.systemd_unit_dir.iterdir():
            if item.name.startswith("fplaunch-") and item.suffix == ".service":
                # Extract app ID from service name
                app_id = item.stem.replace("fplaunch-", "", 1)
                if app_id:
                    apps.append(app_id)

        return sorted(apps)


def get_systemd_unit_dir() -> Path:
    """Get the directory for user systemd units."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg_config:
        xdg_config_home = xdg_config
    else:
        xdg_config_home = str(Path.home() / ".config")
    return Path(xdg_config_home) / "systemd" / "user"


def main() -> int:
    """Command-line interface for systemd setup."""
    parser = argparse.ArgumentParser(
        description="Set up systemd units for fplaunchwrapper",
    )

    parser.add_argument(
        "--bin-dir",
        help="Directory where wrappers are stored",
    )

    parser.add_argument(
        "--script",
        help="Path to fplaunch-generate script",
    )

    parser.add_argument(
        "--cron-interval",
        type=int,
        default=6,
        help="Interval in hours for automatic generation (minimum: 1 hour)",
    )

    args = parser.parse_args()

    setup = SystemdSetup(bin_dir=args.bin_dir, wrapper_script=args.script)
    return setup.run(cron_interval=args.cron_interval)


if __name__ == "__main__":
    sys.exit(main())
