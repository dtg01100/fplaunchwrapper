#!/usr/bin/env python3
"""Systemd setup functionality for fplaunchwrapper
Replaces fplaunch-setup-systemd bash script with Python implementation.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


from .logging_utils import LoggingMixin
from .paths import get_default_bin_dir, ensure_dir
from .python_utils import atomic_write_text
from .validation import check_path_traversal, validate_app_id

CRON_DEFAULT_HOUR = 0
CRON_DEFAULT_INTERVAL = 6

# pylint: disable=too-many-instance-attributes


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

    def _run_systemctl(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a systemctl command with common options."""
        return subprocess.run(
            ["systemctl", "--user"] + list(args),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _run_crontab(
        self, *args: str, input_text: str | None = None, timeout: int = 10
    ) -> subprocess.CompletedProcess:
        """Run a crontab command with common options."""
        cmd = ["crontab"] + list(args)
        kwargs: dict[str, Any] = {
            "check": False,
            "capture_output": True,
            "text": True,
            "timeout": timeout,
        }
        if input_text is not None:
            kwargs["input"] = input_text
        return subprocess.run(cmd, **kwargs)

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
        # shlex.quote every interpolated value: paths containing spaces or
        # shell metacharacters must not break out of the systemd unit syntax
        # into a second shell command.
        return f"""[Unit]
Description=Flatpak Wrapper Generator
After=network.target

[Service]
Type=oneshot
ExecStart={shlex.quote(self.wrapper_script)} {shlex.quote(str(self.bin_dir))}
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
            ensure_dir(self.systemd_unit_dir)

            service_path = self.systemd_unit_dir / "fplaunch-wrapper.service"
            timer_path = self.systemd_unit_dir / "fplaunch-wrapper.timer"

            atomic_write_text(service_path, self.generate_systemd_service(), mode=0o644)
            atomic_write_text(timer_path, self.generate_systemd_timer(cron_interval), mode=0o644)

            # Reload systemd and enable timer; if any step fails, remove the
            # unit files so the user is not left with a half-installed setup.
            try:
                reload_result = self._run_systemctl("daemon-reload")
                if reload_result.returncode != 0:
                    raise RuntimeError(
                        f"systemctl daemon-reload failed: {reload_result.stderr.strip()}"
                    )
                enable_result = self._run_systemctl("enable", "--now", "fplaunch-wrapper.timer")
                if enable_result.returncode != 0:
                    raise RuntimeError(
                        f"systemctl enable failed: {enable_result.stderr.strip()}"
                    )
            except (RuntimeError, subprocess.TimeoutExpired, OSError):
                with contextlib.suppress(OSError):
                    service_path.unlink(missing_ok=True)
                with contextlib.suppress(OSError):
                    timer_path.unlink(missing_ok=True)
                raise

            self.log(
                f"Systemd service and timer installed (interval: {cron_interval}h)",
                "success",
            )
            return True
        except (OSError, subprocess.TimeoutExpired) as e:
            self.log(f"Failed to install systemd units: {e}", "error")
            return False

    def run(self, cron_interval: int = 6) -> int:
        """Main entry point for systemd setup."""
        if self.install_systemd_units(cron_interval):
            return 0
        return 1

    @staticmethod
    def _crontab_has_entry(existing_crontab: str, cron_script: Path, cron_interval: int) -> bool:
        """Check if crontab already has a matching entry for the given script."""
        for line in existing_crontab.splitlines():
            if line.strip() and not line.strip().startswith("#"):
                parts = line.split()
                cron_hour_match = str(CRON_DEFAULT_HOUR)
                if (
                    len(parts) >= 6
                    and parts[0] == cron_hour_match
                    and parts[1] == "*/{}".format(cron_interval)
                ):
                    cron_script_path = " ".join(parts[5:])
                    if str(cron_script) in cron_script_path or cron_script.name in cron_script_path:
                        return True
        return False

    def install_cron_job(self, cron_interval: int = CRON_DEFAULT_INTERVAL) -> bool:
        r"""Install a cron job as fallback when systemd is not available.

        Notes:
        * ``crontab -l`` is treated as authoritative: if it fails, the
          user's crontab is *not* modified. A previous version of this
          code treated a failed ``crontab -l`` as "empty crontab", which
          could clobber the user's existing entries on the subsequent
          ``crontab -`` call.
        * The script path is ``shlex.quote``\ d so a path containing
          spaces does not split into multiple cron field columns.
        * ``acquire_lock("generate")`` serializes concurrent
          ``fplaunch-setup-systemd`` / ``fplaunch-cleanup`` runs.
        """
        if self.emit_mode:
            return True
        try:
            if shutil.which("crontab") is None:
                self.log("Cron is not available on this system", "error")
                return False

            xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
            if xdg_config:
                config_home = Path(xdg_config)
            else:
                config_home = Path.home() / ".config"
            cron_dir = config_home / "cron"
            cron_dir.mkdir(parents=True, exist_ok=True)

            cron_script = cron_dir / "fplaunch-wrapper.sh"
            cron_script_content = (
                "#!/bin/bash\n"
                "# Auto-generated by fplaunchwrapper\n"
                f"{shlex.quote(self.wrapper_script)} {shlex.quote(str(self.bin_dir))}\n"
            )
            atomic_write_text(cron_script, cron_script_content, mode=0o755)

            cron_entry = (
                f"{CRON_DEFAULT_HOUR} */{cron_interval} * * * {cron_script}\n"
            )

            # Read the existing crontab; if it fails, refuse to overwrite.
            result = self._run_crontab("-l")
            if result.returncode != 0:
                self.log(
                    "Cannot read existing crontab; refusing to overwrite",
                    "error",
                )
                return False
            existing = result.stdout or ""

            if not self._crontab_has_entry(existing, cron_script, cron_interval):
                new_cron = existing.rstrip() + "\n" + cron_entry
                write_result = self._run_crontab("-", input_text=new_cron)
                if write_result.returncode != 0:
                    self.log(
                        f"Failed to install cron job: "
                        f"{write_result.stderr.strip()}",
                        "error",
                    )
                    return False
                self.log(f"Cron job installed (interval: {cron_interval}h)", "success")
            else:
                self.log("Cron job already exists", "info")

            return True
        except (OSError, subprocess.TimeoutExpired) as e:
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
            proc = self._run_systemctl("is-enabled", "fplaunch-wrapper.service")
            result["service"]["exists"] = (
                self.systemd_unit_dir / "fplaunch-wrapper.service"
            ).exists()
            result["service"]["enabled"] = proc.returncode == 0

            proc = self._run_systemctl("is-active", "fplaunch-wrapper.service")
            result["service"]["active"] = proc.stdout.strip() == "active"

            # Check timer
            result["timer"]["exists"] = (self.systemd_unit_dir / "fplaunch-wrapper.timer").exists()
            proc = self._run_systemctl("is-enabled", "fplaunch-wrapper.timer")
            result["timer"]["enabled"] = proc.returncode == 0

            proc = self._run_systemctl("is-active", "fplaunch-wrapper.timer")
            result["timer"]["active"] = proc.stdout.strip() == "active"

        except OSError:
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

        ``disable --now`` already stops the units, so the redundant
        ``stop`` block from a previous version is gone. ``disable``/
        ``daemon-reload`` failures are checked via ``returncode``.
        """
        if self.emit_mode:
            self.log("EMIT: Would disable systemd units", "emit")
            return True

        try:
            for unit in ("fplaunch-wrapper.timer", "fplaunch-wrapper.service"):
                result = self._run_systemctl("disable", "--now", unit)
                if result.returncode != 0:
                    self.log(
                        f"systemctl disable --now {unit} failed: "
                        f"{result.stderr.strip()}",
                        "error",
                    )
                    return False

            # Verify the units are within systemd_unit_dir before unlinking
            # (defense-in-depth against symlink redirect).
            service_path = self.systemd_unit_dir / "fplaunch-wrapper.service"
            timer_path = self.systemd_unit_dir / "fplaunch-wrapper.timer"
            path_path = self.systemd_unit_dir / "fplaunch-wrapper.path"

            for unit_path in (service_path, timer_path, path_path):
                if not unit_path.exists():
                    continue
                safe, error = check_path_traversal(unit_path, self.systemd_unit_dir)
                if not safe:
                    self.log(
                        f"Refusing to remove unit outside systemd dir: {error}",
                        "error",
                    )
                    return False
                unit_path.unlink(missing_ok=True)
                self.log(f"Removed: {unit_path}", "info")

            reload_result = self._run_systemctl("daemon-reload")
            if reload_result.returncode != 0:
                self.log(
                    f"systemctl daemon-reload failed: "
                    f"{reload_result.stderr.strip()}",
                    "error",
                )
                return False

            self.log("Systemd units disabled", "success")
            return True

        except (OSError, subprocess.TimeoutExpired) as e:
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
            if item.name.startswith("fplaunch-") and item.suffix in (
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
            ensure_dir(self.systemd_unit_dir)

            safe_app_id = app_id.replace("/", "_").replace(" ", "_")
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
            atomic_write_text(service_path, service_content, mode=0o644)

            try:
                reload_result = self._run_systemctl("daemon-reload")
                if reload_result.returncode != 0:
                    raise RuntimeError(
                        f"systemctl daemon-reload failed: {reload_result.stderr.strip()}"
                    )
                enable_result = self._run_systemctl("enable", service_name)
                if enable_result.returncode != 0:
                    raise RuntimeError(
                        f"systemctl enable failed: {enable_result.stderr.strip()}"
                    )
            except (RuntimeError, subprocess.TimeoutExpired, OSError):
                with contextlib.suppress(OSError):
                    service_path.unlink(missing_ok=True)
                raise

            self.log(f"Enabled app service for {safe_app_id}", "success")
            return True
        except (OSError, subprocess.TimeoutExpired) as e:
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
            safe_app_id = app_id.replace("/", "_").replace(" ", "_")
            service_name = f"fplaunch-{safe_app_id}.service"
            service_path = self.systemd_unit_dir / service_name

            # Use Path.relative_to() for robust path traversal prevention
            safe, error = check_path_traversal(service_path, self.systemd_unit_dir)
            if not safe:
                self.log(f"Path traversal detected in app_id: {error}", "error")
                return False
            self._run_systemctl("disable", service_name)

            if service_path.exists():
                service_path.unlink(missing_ok=True)

            self._run_systemctl("daemon-reload")

            self.log(f"Disabled app service for {safe_app_id}", "success")
            return True
        except (OSError, subprocess.TimeoutExpired) as e:
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
    """Get the directory for user systemd units.

    Uses the centralized path resolution from paths module.
    """
    from .paths import get_systemd_unit_dir as _get_systemd_unit_dir

    return _get_systemd_unit_dir()


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
    parser.add_argument(
        "--emit",
        action="store_true",
        help="Emit only (dry run); do not run systemctl or write unit files",
    )

    args = parser.parse_args()

    setup = SystemdSetup(
        bin_dir=args.bin_dir,
        wrapper_script=args.script,
        emit_mode=args.emit,
    )
    return setup.run(cron_interval=args.cron_interval)


if __name__ == "__main__":
    sys.exit(main())
