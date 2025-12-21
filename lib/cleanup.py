#!/usr/bin/env python3
"""Cleanup functionality for fplaunchwrapper.

Replaces fplaunch-cleanup bash script with Python implementation.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.prompt import Confirm

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import our utilities
try:
    from python_utils import is_wrapper_file

    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


class WrapperCleanup:
    """Clean up Flatpak wrapper artifacts."""

    def __init__(
        self,
        bin_dir: str | None = None,
        config_dir: str | None = None,
        dry_run: bool = False,
        assume_yes: bool = False,
    ) -> None:
        """Initialize the cleanup utility.

        Args:
            bin_dir: Directory containing wrappers
            config_dir: Directory containing configuration
            dry_run: Show what would be done without doing it
            assume_yes: Don't prompt for confirmation

        """
        self.dry_run = dry_run
        self.assume_yes = assume_yes

        # Set up directories
        self.bin_dir = Path(bin_dir or (Path.home() / "bin"))
        self.config_dir = Path(
            config_dir or (Path.home() / ".config" / "fplaunchwrapper"),
        )
        self.systemd_unit_dir = self._get_systemd_unit_dir()

        # Summary of what will be cleaned
        self.cleanup_items = {
            "wrappers": [],
            "symlinks": [],
            "scripts": [],
            "systemd_units": [],
            "cron_entries": [],
            "completion_files": [],
            "man_pages": [],
            "config_dir": [self.config_dir] if self.config_dir.exists() else [],
        }

    def _get_systemd_unit_dir(self) -> Path:
        """Get systemd user unit directory."""
        xdg_config_home = os.environ.get(
            "XDG_CONFIG_HOME",
            str(Path.home() / ".config"),
        )
        return Path(xdg_config_home) / "systemd" / "user"

    def scan_for_cleanup_items(self) -> None:
        """Scan for items that can be cleaned up."""
        self.log("Scanning for cleanup items...")

        # 1. Scan wrapper directory
        if self.bin_dir.exists():
            for item in self.bin_dir.iterdir():
                if item.is_file():
                    if UTILS_AVAILABLE and is_wrapper_file(str(item)):
                        self.cleanup_items["wrappers"].append(item)
                    elif item.name in [
                        "fplaunch-manage",
                        "fplaunch-generate",
                        "fplaunch-setup-systemd",
                        "fplaunch-cleanup",
                    ]:
                        self.cleanup_items["scripts"].append(item)
                elif item.is_symlink():
                    # Check if symlink points to a wrapper
                    try:
                        target = item.readlink()
                        if target.is_absolute():
                            target_path = target
                        else:
                            target_path = self.bin_dir / target

                        if UTILS_AVAILABLE and is_wrapper_file(str(target_path)):
                            self.cleanup_items["symlinks"].append(item)
                    except (OSError, RuntimeError):
                        pass

        # 2. Scan systemd units
        systemd_units = [
            "flatpak-wrappers.service",
            "flatpak-wrappers.path",
            "flatpak-wrappers.timer",
        ]

        for unit in systemd_units:
            unit_path = self.systemd_unit_dir / unit
            if unit_path.exists():
                self.cleanup_items["systemd_units"].append(unit_path)

        # 3. Check bash completion
        bash_completion = Path.home() / ".bashrc.d" / "fplaunch_completion.bash"
        if bash_completion.exists():
            self.cleanup_items["completion_files"].append(bash_completion)

        # 4. Check man pages
        man_dir = Path.home() / ".local" / "share" / "man"
        if man_dir.exists():
            for manpage in man_dir.glob("man1/fplaunch-*.1"):
                self.cleanup_items["man_pages"].append(manpage)
            for manpage in man_dir.glob("man7/fplaunchwrapper.*"):
                self.cleanup_items["man_pages"].append(manpage)

        # 5. Check cron entries
        if self._has_cron_entries():
            self.cleanup_items["cron_entries"].append("fplaunch-generate entries")

    def _has_cron_entries(self) -> bool:
        """Check if there are cron entries to clean up."""
        crontab_path = shutil.which("crontab")
        if not crontab_path:
            return False
        try:
            result = subprocess.run(
                [crontab_path, "-l"],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return "fplaunch-generate" in result.stdout
        except (subprocess.CalledProcessError, OSError):
            pass
        return False

    def log(self, message: str, level: str = "info") -> None:
        """Log a message."""
        if level == "error":
            sys.stderr.write(f"ERROR: {message}\n")
        elif level == "warning":
            sys.stderr.write(f"WARNING: {message}\n")
        else:
            sys.stdout.write(f"{message}\n")

    def confirm_cleanup(self) -> bool:
        """Show cleanup summary and get confirmation."""
        self.log("")
        self.log("About to clean per-user artifacts for fplaunchwrapper:")
        self.log(f"- Wrapper directory: {self.bin_dir}")
        self.log(f"- Config directory:  {self.config_dir}")
        self.log(f"- systemd units in:  {self.systemd_unit_dir}")
        self.log("- Bash completion:   ~/.bashrc.d/fplaunch_completion.bash")
        self.log("- Man pages:         ~/.local/share/man")
        self.log("")

        # Show detailed breakdown
        total_items = 0
        for category, items in self.cleanup_items.items():
            if items:
                count = len(items)
                total_items += count
                if category == "config_dir":
                    self.log(f"- Configuration directory ({count} item)")
                elif category == "cron_entries":
                    self.log(f"- Cron entries ({count} item)")
                else:
                    self.log(f"- {category.capitalize()}: {count} items")

        if total_items == 0:
            self.log("No cleanup items found.")
            return True

        self.log(f"\nTotal items to remove: {total_items}")

        if self.dry_run:
            self.log("\nDRY RUN - No changes will be made.")
            return True

        if self.assume_yes:
            return True

        # Get user confirmation
        if console:
            return Confirm.ask("Proceed with cleanup?")
        response = input("Proceed with cleanup? (y/N): ").strip().lower()
        return response in ["y", "yes"]

    def perform_cleanup(self) -> bool:
        """Perform the actual cleanup."""
        try:
            # 1. Stop and disable systemd units
            self._cleanup_systemd_units()

            # 2. Remove cron entries
            self._cleanup_cron_entries()

            # 3. Remove wrappers, symlinks, and scripts
            self._cleanup_wrappers_and_scripts()

            # 4. Remove bash completion
            self._cleanup_completion_files()

            # 5. Remove man pages
            self._cleanup_man_pages()

            # 6. Remove config directory
            self._cleanup_config_dir()

            self.log("Cleanup complete.")
            return True

        except (OSError, subprocess.CalledProcessError, ValueError) as e:
            self.log(f"Cleanup failed: {e}", "error")
            return False

    def _cleanup_systemd_units(self) -> None:
        """Stop, disable and remove systemd units."""
        if not self.cleanup_items["systemd_units"]:
            return

        # Stop and disable services
        systemctl_path = shutil.which("systemctl")
        if systemctl_path:
            self.log("Stopping and disabling systemd units...")
            if not self.dry_run:
                # Stop services
                subprocess.run(
                    [
                        systemctl_path,
                        "--user",
                        "stop",
                        "flatpak-wrappers.path",
                        "flatpak-wrappers.timer",
                        "flatpak-wrappers.service",
                    ],
                    check=False,
                    capture_output=True,
                )

                # Disable services
                subprocess.run(
                    [
                        systemctl_path,
                        "--user",
                        "disable",
                        "flatpak-wrappers.path",
                        "flatpak-wrappers.timer",
                        "flatpak-wrappers.service",
                    ],
                    check=False,
                    capture_output=True,
                )

                # Reload daemon
                subprocess.run(
                    [systemctl_path, "--user", "daemon-reload"],
                    check=False,
                    capture_output=True,
                )

        # Remove unit files
        for unit_path in self.cleanup_items["systemd_units"]:
            self._remove_file(unit_path, f"Removing systemd unit: {unit_path}")

    def _cleanup_cron_entries(self) -> None:
        """Remove cron entries."""
        if not self.cleanup_items["cron_entries"]:
            return

        crontab_path = shutil.which("crontab")
        if crontab_path:
            self.log("Removing cron entries...")
            if not self.dry_run:
                try:
                    # Get current crontab
                    result = subprocess.run(
                        [crontab_path, "-l"],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        current_cron = result.stdout
                        # Remove lines containing fplaunch-generate
                        new_cron = "\n".join(
                            line
                            for line in current_cron.split("\n")
                            if "fplaunch-generate" not in line
                        )
                        # Update crontab
                        subprocess.run(
                            [crontab_path, "-"],
                            check=False,
                            input=new_cron,
                            text=True,
                            capture_output=True,
                        )
                except (subprocess.CalledProcessError, OSError):
                    pass

    def _cleanup_wrappers_and_scripts(self) -> None:
        """Remove wrappers, symlinks, and scripts."""
        # Remove wrappers
        for wrapper in self.cleanup_items["wrappers"]:
            self._remove_file(wrapper, f"Removing wrapper: {wrapper}")

        # Remove symlinks
        for symlink in self.cleanup_items["symlinks"]:
            self._remove_file(symlink, f"Removing symlink: {symlink}")

        # Remove scripts
        for script in self.cleanup_items["scripts"]:
            self._remove_file(script, f"Removing script: {script}")

        # Remove lib directory if it exists
        lib_dir = self.bin_dir / "lib"
        if lib_dir.exists() and lib_dir.is_dir():
            self._remove_directory(lib_dir, f"Removing library directory: {lib_dir}")

    def _cleanup_completion_files(self) -> None:
        """Remove bash completion files."""
        for completion_file in self.cleanup_items["completion_files"]:
            self._remove_file(
                completion_file,
                f"Removing completion file: {completion_file}",
            )

    def _cleanup_man_pages(self) -> None:
        """Remove man pages."""
        for manpage in self.cleanup_items["man_pages"]:
            self._remove_file(manpage, f"Removing man page: {manpage}")

        # Clean up empty directories
        if not self.dry_run:
            man_dir = Path.home() / ".local" / "share" / "man"
            for subdir in ["man1", "man7"]:
                subdir_path = man_dir / subdir
                if subdir_path.exists() and not any(subdir_path.iterdir()):
                    with contextlib.suppress(OSError):
                        subdir_path.rmdir()

            if man_dir.exists() and not any(man_dir.iterdir()):
                with contextlib.suppress(OSError):
                    man_dir.rmdir()

    def _cleanup_config_dir(self) -> None:
        """Remove configuration directory."""
        if self.cleanup_items["config_dir"]:
            config_dir = self.cleanup_items["config_dir"][0]  # It's now a list
            self._remove_directory(
                config_dir,
                f"Removing config directory: {config_dir}",
            )

    def _remove_file(self, path: Path, description: str) -> None:
        """Remove a file with logging."""
        self.log(description)
        if not self.dry_run:
            try:
                path.unlink(missing_ok=True)
            except OSError as e:
                self.log(f"Warning: Failed to remove {path}: {e}", "warning")

    def _remove_directory(self, path: Path, description: str) -> None:
        """Remove a directory with logging."""
        self.log(description)
        if not self.dry_run:
            try:
                shutil.rmtree(path)
            except OSError as e:
                self.log(f"Warning: Failed to remove {path}: {e}", "warning")

    def _command_available(self, command: str) -> bool:
        """Check if a command is available."""
        return shutil.which(command) is not None

    def run(self) -> int:
        """Run the cleanup process."""
        try:
            # Scan for items to clean up
            self.scan_for_cleanup_items()

            # Show summary and get confirmation
            if not self.confirm_cleanup():
                self.log("Cleanup cancelled.")
                return 0

            # Perform cleanup
            if self.dry_run:
                self.log("DRY RUN - No files were removed.")
                return 0

            if self.perform_cleanup():
                return 0
            return 1

        except (
            OSError,
            subprocess.CalledProcessError,
            ValueError,
            KeyboardInterrupt,
        ) as e:
            self.log(f"Cleanup failed: {e}", "error")
            return 1


def main() -> int:
    """Command-line interface for cleanup."""
    parser = argparse.ArgumentParser(
        description="Clean up Flatpak wrapper artifacts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cleanup                        # Interactive cleanup
  python -m cleanup --yes                  # Non-interactive cleanup
  python -m cleanup --dry-run              # Show what would be removed
  python -m cleanup --bin-dir ~/my-bin     # Specify custom bin directory

This removes:
- Generated wrapper scripts
- Alias symlinks
- Configuration directory
- systemd user units
- Cron job entries
- Bash completion files
- Man pages
        """,
    )

    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Proceed without confirmation",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without deleting",
    )

    parser.add_argument("--bin-dir", help="Override wrapper bin directory")

    parser.add_argument("--config-dir", help="Override configuration directory")

    args = parser.parse_args()

    cleanup = WrapperCleanup(
        bin_dir=args.bin_dir,
        config_dir=args.config_dir,
        dry_run=args.dry_run,
        assume_yes=args.yes,
    )

    return cleanup.run()


if __name__ == "__main__":
    sys.exit(main())
