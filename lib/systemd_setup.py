#!/usr/bin/env python3
"""
Systemd setup functionality for fplaunchwrapper
Replaces fplaunch-setup-systemd bash script with Python implementation
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


class SystemdSetup:
    """Set up systemd units for automatic wrapper management"""

    def __init__(
        self, bin_dir: Optional[str] = None, wrapper_script: Optional[str] = None
    ):
        self.bin_dir = Path(bin_dir or (Path.home() / "bin"))
        self.wrapper_script = wrapper_script or self._find_wrapper_script()
        self.systemd_unit_dir = self._get_systemd_unit_dir()
        self.flatpak_bin_dir = self._detect_flatpak_bin_dir()

    def _find_wrapper_script(self) -> str:
        """Find the wrapper generation script"""
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
        """Get systemd user unit directory"""
        xdg_config_home = os.environ.get(
            "XDG_CONFIG_HOME", str(Path.home() / ".config")
        )
        return Path(xdg_config_home) / "systemd" / "user"

    def _detect_flatpak_bin_dir(self) -> str:
        """Detect Flatpak binary directory"""
        candidates = [
            str(Path.home() / ".local" / "share" / "flatpak" / "exports" / "bin"),
            "/var/lib/flatpak/exports/bin",
        ]

        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate

        # Try to get from flatpak command
        try:
            result = subprocess.run(
                ["flatpak", "--print-updated-env"], capture_output=True, text=True
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
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Default fallback
        return str(Path.home() / ".local" / "share" / "flatpak" / "exports" / "bin")

    def log(self, message: str, level: str = "info"):
        """Log a message"""
        if level == "error":
            print(f"ERROR: {message}", file=sys.stderr)
        elif level == "warning":
            print(f"WARNING: {message}", file=sys.stderr)
        elif level == "success":
            if console:
                console.print(f"[green]✓[/green] {message}")
            else:
                print(f"SUCCESS: {message}")
        else:
            print(message)

    def check_prerequisites(self) -> bool:
        """Check if prerequisites are met"""
        # Check if Flatpak is installed
        if not self._command_available("flatpak"):
            self.log("Error: Flatpak not installed.", "error")
            return False

        # Check if wrapper script exists
        if not os.path.exists(self.wrapper_script.split()[0]):
            self.log(
                f"Error: Wrapper script not found at {self.wrapper_script}", "error"
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
        """Check if a command is available"""
        return subprocess.run(["which", command], capture_output=True).returncode == 0

    def _systemd_available(self) -> bool:
        """Check if systemd user services are available"""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "status"], capture_output=True
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def create_service_unit(self) -> str:
        """Create the service unit content"""
        return f"""[Unit]
Description=Generate Flatpak wrapper scripts

[Service]
Type=oneshot
ExecStart={self.wrapper_script} {self.bin_dir}
"""

    def create_path_unit(self) -> str:
        """Create the path unit content"""
        return f"""[Unit]
Description=Watch for Flatpak app changes

[Path]
PathChanged={self.flatpak_bin_dir}
Unit=flatpak-wrappers.service

[Install]
WantedBy=default.target
"""

    def create_timer_unit(self) -> str:
        """Create the timer unit content"""
        return f"""[Unit]
Description=Timer for Flatpak wrapper generation

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
"""

    def install_systemd_units(self) -> bool:
        """Install and enable systemd units"""
        try:
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

            # Reload daemon
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"], capture_output=True
            )

            # Enable and start path unit
            subprocess.run(
                ["systemctl", "--user", "enable", "flatpak-wrappers.path"],
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "--user", "start", "flatpak-wrappers.path"],
                capture_output=True,
            )

            # Enable and start timer unit
            subprocess.run(
                ["systemctl", "--user", "enable", "flatpak-wrappers.timer"],
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "--user", "start", "flatpak-wrappers.timer"],
                capture_output=True,
            )

            self.log("Systemd units installed and started", "success")
            self.log(
                "Wrappers will update automatically on user Flatpak changes and daily"
            )
            self.log("(System Flatpak changes require manual run or wait for timer)")

            return True

        except Exception as e:
            self.log(f"Failed to install systemd units: {e}", "error")
            return False

    def install_cron_job(self) -> bool:
        """Install cron job as fallback"""
        if not self._command_available("crontab"):
            self.log("Neither systemd nor crontab available.", "error")
            self.log(
                f"Please run '{self.wrapper_script} {self.bin_dir}' manually to update wrappers."
            )
            return False

        try:
            cron_job = f"0 */6 * * * {self.wrapper_script} {self.bin_dir}"

            # Check if cron job already exists
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            if result.returncode == 0 and self.wrapper_script in result.stdout:
                self.log("Cron job already exists. Wrappers will update every 6 hours.")
                return True

            # Add cron job
            if result.returncode == 0:
                new_cron = result.stdout.rstrip() + "\n" + cron_job + "\n"
            else:
                new_cron = cron_job + "\n"

            subprocess.run(
                ["crontab", "-"], input=new_cron, text=True, capture_output=True
            )

            self.log("Cron job added for wrapper updates every 6 hours.", "success")
            self.log("(System Flatpak changes require manual run.)")

            return True

        except Exception as e:
            self.log(f"Failed to install cron job: {e}", "error")
            return False

    def run(self) -> int:
        """Main setup process"""
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
                f"Please run '{self.wrapper_script} {self.bin_dir}' manually to update wrappers."
            )
            return 1

        except Exception as e:
            self.log(f"Setup failed: {e}", "error")
            return 1


def main():
    """Command-line interface for systemd setup"""
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
