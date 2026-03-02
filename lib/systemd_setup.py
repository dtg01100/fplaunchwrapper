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
from typing import Any

from rich.console import Console

from .paths import get_default_bin_dir

console = Console()
console_err = Console(stderr=True)


class SystemdSetup:
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
            os.path.expanduser("~/bin/fplaunch-generate"),
            os.path.expanduser("~/.local/bin/fplaunch-generate"),
        ]
        for p in common_paths:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        
        # Default to name only if not found
        return "fplaunch-generate"

    def _detect_flatpak_bin_dir(self) -> str:
        """Detect where Flatpak stores application binaries."""
        # Common locations
        paths = [
            "/var/lib/flatpak/exports/bin",
            os.path.expanduser("~/.local/share/flatpak/exports/bin"),
        ]
        for p in paths:
            if os.path.isdir(p):
                return p
        return ""

    def log(self, message: str, level: str = "info") -> None:
        """Log a message to appropriate stream."""
        if level == "error":
            console_err.print(f"[red]ERROR:[/red] {message}")
        elif level == "warning":
            console_err.print(f"[yellow]WARN:[/yellow] {message}")
        elif level == "success":
            console.print(f"[green]✓[/green] {message}")
        elif level in ["info", "emit"]:
            console.print(message)
        else:
            console.print(message)

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
            subprocess.run(["systemctl", "--user", "enable", "--now", "fplaunch-wrapper.timer"], check=False)
            
            self.log(f"Systemd service and timer installed (interval: {cron_interval}h)", "success")
            return True
        except Exception as e:
            self.log(f"Failed to install systemd units: {e}", "error")
            return False

    def run(self, cron_interval: int = 6) -> int:
        """Main entry point for systemd setup."""
        if self.install_systemd_units(cron_interval):
            return 0
        return 1


def get_systemd_unit_dir() -> Path:
    """Get the directory for user systemd units."""
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(xdg_config_home) / "systemd" / "user"


def main() -> int:
    """Command-line interface for systemd setup."""
    import argparse

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
