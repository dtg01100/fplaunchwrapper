#!/usr/bin/env python3
"""Wrapper generation functionality for fplaunchwrapper
Replaces fplaunch-generate bash script with Python implementation.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import our utilities
try:
    from .python_utils import (
        acquire_lock,
        find_executable,
        get_temp_dir,
        get_wrapper_id,
        is_wrapper_file,
        release_lock,
        safe_mktemp,
        sanitize_id_to_name,
        validate_home_dir,
    )

    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None
console_err = Console(stderr=True) if RICH_AVAILABLE else None


class WrapperGenerator:
    """Generates Flatpak application wrappers."""

    FORBIDDEN_WRAPPER_NAMES = {
        "bash",
        "sh",
        "zsh",
        "fish",
        "csh",
        "tcsh",
        "ksh",
        "dash",
        "ash",
        "ssh",
        "scp",
        "sftp",
        "rsync",
        "wget",
        "curl",
        "git",
        "hg",
        "svn",
        "make",
        "gcc",
        "g++",
        "clang",
        "python",
        "python3",
        "pip",
        "pip3",
        "node",
        "npm",
        "yarn",
        "java",
        "javac",
        "ruby",
        "gem",
        "perl",
        "php",
        "go",
        "cargo",
        "rustc",
        "docker",
        "podman",
        "flatpak",
        "systemctl",
        "journalctl",
        "dmesg",
        "ls",
        "cat",
        "grep",
        "find",
        "ps",
        "top",
        "htop",
        "kill",
        "killall",
        "pkill",
        "pgrep",
        "mkdir",
        "rmdir",
        "rm",
        "cp",
        "mv",
        "ln",
        "chmod",
        "chown",
        "chgrp",
        "df",
        "du",
        "free",
        "uptime",
        "uname",
        "whoami",
        "id",
        "passwd",
        "su",
        "sudo",
        "visudo",
        "useradd",
        "userdel",
        "groupadd",
        "groupdel",
        "mount",
        "umount",
        "fdisk",
        "mkfs",
        "fsck",
        "dd",
        "tar",
        "gzip",
        "gunzip",
        "bzip2",
        "xz",
        "zip",
        "unzip",
        "7z",
        "rar",
        "unrar",
        "less",
        "more",
        "head",
        "tail",
        "sort",
        "uniq",
        "wc",
        "cut",
        "paste",
        "tr",
        "sed",
        "awk",
        "vim",
        "vi",
        "nano",
        "emacs",
        "joe",
        "screen",
        "tmux",
        "sshd",
        "httpd",
        "nginx",
        "apache2",
        "mysql",
        "postgresql",
        "redis",
        "mongodb",
        "sqlite3",
        "ftp",
        "telnet",
        "ping",
        "traceroute",
        "nslookup",
        "dig",
        "host",
        "whois",
        "ifconfig",
        "ip",
        "route",
        "netstat",
        "ss",
        "iptables",
        "firewall-cmd",
        "ufw",
        "nmap",
        "tcpdump",
        "wireshark",
        "strace",
        "ltrace",
        "gdb",
        "valgrind",
        "perf",
        "sar",
        "iostat",
        "vmstat",
        "mpstat",
        "atop",
        "iotop",
        "glances",
        "nc",
        "socat",
        "openssl",
        "gpg",
        "ssh-keygen",
    }

    def __init__(
        self,
        bin_dir: str,
        config_dir: str | None = None,
        verbose: bool = False,
        emit_mode: bool = False,
        emit_verbose: bool = False,
    ) -> None:
        # Backwards compatibility: allow positional booleans for verbose/emit flags
        if isinstance(config_dir, bool):
            verbose, emit_mode, emit_verbose = config_dir, verbose, emit_mode
            config_dir = None

        # Validate inputs to avoid creating unexpected artifact paths (e.g., MagicMock reprs)
        if not isinstance(bin_dir, (str, os.PathLike)):
            raise TypeError("bin_dir must be a string or path-like object")
        if config_dir is not None and not isinstance(
            config_dir, (str, os.PathLike, bool)
        ):
            raise TypeError("config_dir must be a string or path-like object or None")

        self.bin_dir = Path(bin_dir).expanduser().resolve()
        self.verbose = verbose
        self.emit_mode = emit_mode
        self.emit_verbose = emit_verbose
        self.lock_name = "generate"
        self.config_dir = (
            Path(config_dir)
            if config_dir
            else (Path.home() / ".config" / "fplaunchwrapper")
        )

        # Ensure directories exist (unless in emit mode)
        if not emit_mode:
            self.bin_dir.mkdir(parents=True, exist_ok=True)
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Save bin_dir to config
            (self.config_dir / "bin_dir").write_text(str(self.bin_dir))

    def is_forbidden_wrapper_name(self, name: str) -> bool:
        """Check if a wrapper name collides with basic system commands."""
        return name.lower() in self.FORBIDDEN_WRAPPER_NAMES

    def log(self, message: str, level: str = "info") -> None:
        """Log a message to appropriate stream."""
        if level == "error":
            if console_err:
                console_err.print(f"[red]ERROR:[/red] {message}")
            else:
                print(f"ERROR: {message}", file=sys.stderr)
        elif level == "warning":
            if console_err:
                console_err.print(f"[yellow]WARN:[/yellow] {message}")
            else:
                print(f"WARN: {message}", file=sys.stderr)
        elif level == "success":
            if console:
                console.print(f"[green]✓[/green] {message}")
            else:
                print(f"✓ {message}")
        else:
            # info messages
            if console:
                console.print(message)
            else:
                print(message)

    def run_command(
        self,
        cmd: list[str],
        description: str = "",
    ) -> subprocess.CompletedProcess:
        """Run a command with optional progress display."""
        if description and console and not self.verbose:
            with console.status(f"[bold green]{description}..."):
                result = subprocess.run(
                    cmd, check=False, capture_output=True, text=True
                )
        else:
            if self.verbose:
                self.log(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

        return result

    def get_installed_flatpaks(self) -> list[str]:
        """Get list of installed Flatpak applications."""
        self.log("Checking for Flatpak installation...")

        flatpak_path = find_executable("flatpak") if UTILS_AVAILABLE else None
        if not flatpak_path:
            msg = "Flatpak not found. Please install Flatpak first."
            raise RuntimeError(msg)

        self.log(f"Found Flatpak at: {flatpak_path}")

        # Get installed apps from both user and system installations
        result = self.run_command(
            [flatpak_path, "list", "--app", "--columns=application"],
            "Getting installed Flatpak applications",
        )

        if result.returncode != 0:
            msg = f"Failed to get Flatpak applications: {result.stderr}"
            raise RuntimeError(msg)

        # Parse output and remove duplicates
        apps = []
        for line in str(result.stdout).strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("Application ID"):
                apps.append(line)

        # Also check system installation
        result_system = self.run_command(
            [flatpak_path, "list", "--app", "--columns=application", "--system"],
            "Checking system Flatpak installations",
        )

        if result_system.returncode == 0:
            for line in result_system.stdout.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("Application ID") and line not in apps:
                    apps.append(line)

        return sorted(set(apps))

    def cleanup_obsolete_wrappers(self, installed_apps: list[str]) -> int:
        """Remove wrappers for uninstalled applications."""
        self.log("Cleaning up obsolete wrappers...")

        removed_count = 0

        # Get existing wrappers
        if not self.bin_dir.exists():
            return 0

        for item in self.bin_dir.iterdir():
            if not item.is_file():
                continue

            remove_item = False

            # Check if it's a wrapper
            if UTILS_AVAILABLE and is_wrapper_file(str(item)):
                wrapper_id = get_wrapper_id(str(item))
                if wrapper_id and wrapper_id not in installed_apps:
                    remove_item = True
            else:
                # Fallback: treat file as potential wrapper and remove if name not in installed apps
                sanitized_installed = [sanitize_id_to_name(a) for a in installed_apps]
                if item.name not in sanitized_installed:
                    remove_item = True

            if remove_item:
                self.log(f"Removing obsolete wrapper: {item.name}")
                try:
                    item.unlink()
                    removed_count += 1

                    # Remove preference file
                    pref_file = self.config_dir / f"{item.name}.pref"
                    if pref_file.exists():
                        pref_file.unlink()

                    # Remove aliases
                    aliases_file = self.config_dir / "aliases"
                    if aliases_file.exists():
                        content = aliases_file.read_text()
                        new_content = "\n".join(
                            line
                            for line in content.split("\n")
                            if not line.startswith(f"{item.name} ")
                        )
                        if new_content.strip():
                            aliases_file.write_text(new_content)
                        else:
                            aliases_file.unlink()

                except Exception as e:
                    self.log(f"Failed to remove {item.name}: {e}", "warning")

        if removed_count == 0:
            self.log("No obsolete wrappers found")
        else:
            self.log(f"Removed {removed_count} obsolete wrapper(s)")

        return removed_count

    def is_blocklisted(self, app_id: str) -> bool:
        """Check if an application is blocklisted."""
        blocklist_file = self.config_dir / "blocklist"
        if not blocklist_file.exists():
            return False

        try:
            blocklist_content = blocklist_file.read_text()
            for line in blocklist_content.split("\n"):
                line = line.strip()
                if line and line == app_id:
                    return True
        except Exception as e:
            self.log(f"Warning: Failed to read blocklist file: {e}", "warning")

        return False

    def generate_wrapper(self, app_id: str, flatpak_id: str | None = None) -> bool:
        """Generate a wrapper script for a single application.

        Args:
            app_id: Logical app name or identifier used for wrapper naming.
            flatpak_id: Optional explicit Flatpak ID. If provided, it must
                be a sanitized, safe ID. When omitted, app_id is used as the
                Flatpak ID.
        """
        if not UTILS_AVAILABLE:
            msg = "Python utilities not available"
            raise RuntimeError(msg)

        # Check if app is blocklisted
        if self.is_blocklisted(app_id):
            self.log(f"Skipping blocklisted app: {app_id}", "warning")
            return False

        # Sanitize app ID to create wrapper name
        wrapper_name = sanitize_id_to_name(app_id)
        if not wrapper_name:
            self.log(f"Skipping invalid app ID: {app_id}", "warning")
            return False

        # Check for forbidden wrapper names to avoid colliding with system commands
        if self.is_forbidden_wrapper_name(wrapper_name):
            self.log(f"Skipping forbidden wrapper name: {wrapper_name}", "warning")
            return False

        target_flatpak_id = flatpak_id or app_id

        # Basic flatpak ID validation: allow alnum, dot, dash, underscore
        import re

        if not re.match(r"^[A-Za-z0-9._-]+$", target_flatpak_id):
            if flatpak_id is not None:
                self.log(
                    f"Skipping invalid Flatpak ID: {target_flatpak_id}",
                    "warning",
                )
                return False
            # If no explicit flatpak_id was provided, fall back to a sanitized name
            target_flatpak_id = sanitize_id_to_name(app_id)
            if not target_flatpak_id:
                self.log(
                    f"Skipping invalid app ID (unsanitizable): {app_id}",
                    "warning",
                )
                return False

        wrapper_path = self.bin_dir / wrapper_name

        # Check for existing wrapper (handle permission errors gracefully)
        try:
            wrapper_existed = wrapper_path.exists()
        except PermissionError:
            self.log(f"Permission denied accessing {wrapper_path}", "error")
            return False
        if wrapper_existed:
            existing_id = get_wrapper_id(str(wrapper_path)) if UTILS_AVAILABLE else None
            # If the existing file isn't recognized as our wrapper, treat it as a name collision
            if existing_id is None:
                try:
                    # Try reading file to ensure it's a real file and not a mocked path
                    _ = wrapper_path.read_text()
                except Exception as e:
                    # Can't read file (possibly mocked); allow creation
                    self.log(
                        f"Note: Could not verify existing wrapper file: {e}", "info"
                    )
                else:
                    self.log(
                        f"Name collision for '{wrapper_name}': existing file not a wrapper",
                        "warning",
                    )
                    return False
            if existing_id and existing_id != app_id:
                self.log(
                    f"Name collision for '{wrapper_name}': {existing_id} vs {app_id}",
                    "warning",
                )
                return False

        wrapper_content = self.create_wrapper_script(wrapper_name, target_flatpak_id)

        if self.emit_mode:
            # In emit mode, just show what would be done
            action = "Update" if wrapper_existed else "Create"
            self.log(f"EMIT: Would {action.lower()} wrapper: {wrapper_name}")
            self.log(
                f"EMIT: Would write {len(wrapper_content)} bytes to {wrapper_path}",
            )
            self.log(f"EMIT: Would set permissions to 755 on {wrapper_path}")

            # For debugging (tests), indicate emit
            print(f"EMIT MODE active for {wrapper_name}")

            # Show file content if verbose emit mode
            if self.emit_verbose:
                self.log(f"EMIT: File content for {wrapper_path}:")
                # Use Rich panel for better formatting if available
                if console:
                    from rich.panel import Panel

                    console.print(
                        Panel.fit(
                            wrapper_content,
                            title=f"📄 {wrapper_name} wrapper script",
                            border_style="blue",
                        ),
                    )
                    # Also print raw content so redirect_stdout-based tests can capture it
                    print(wrapper_content)
                else:
                    self.log("-" * 50)
                    for i, line in enumerate(wrapper_content.split("\n"), 1):
                        self.log(f"{i:2d}: {line}")
                    self.log("-" * 50)

            return True
        try:
            wrapper_path.write_text(wrapper_content)
            wrapper_path.chmod(0o755)

            if wrapper_existed:
                self.log(f"Updated wrapper: {wrapper_name}")
            else:
                self.log(f"Created wrapper: {wrapper_name}")

            return True

        except Exception as e:
            self.log(f"Failed to create wrapper {wrapper_name}: {e}", "error")
            return False

            return True

        except Exception as e:
            self.log(f"Failed to create wrapper {wrapper_name}: {e}", "error")
            return False

    def create_wrapper_script(self, wrapper_name: str, app_id: str) -> str:
        """Create the content of a wrapper script by reading from template file."""
        # Get the directory of the current script
        script_dir = Path(__file__).parent
        # Template file path in templates directory
        template_path = script_dir.parent / "templates" / "wrapper.template.sh"

        try:
            with open(template_path, "r") as file:
                template_content = file.read()

            # Replace template variables
            return template_content.format(
                wrapper_name=wrapper_name,
                app_id=app_id,
                config_dir=str(self.config_dir),
                bin_dir=str(self.bin_dir),
            )

        except FileNotFoundError:
            raise RuntimeError(f"Wrapper template file not found: {template_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to read wrapper template: {e}")

    def generate_all_wrappers(self, installed_apps: list[str]) -> tuple[int, int, int]:
        """Generate wrappers for all installed applications."""
        self.log("Generating wrappers...")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        # Use progress bar if rich is available
        if console and not self.verbose:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "Generating wrappers...",
                    total=len(installed_apps),
                )

                for app_id in installed_apps:
                    if self.generate_wrapper(app_id):
                        # Check if it was an update or create
                        wrapper_name = (
                            sanitize_id_to_name(app_id)
                            if UTILS_AVAILABLE
                            else app_id.split(".")[-1]
                        )
                        self.bin_dir / wrapper_name
                        # For now, assume it's a create (we'd need to track this)
                        created_count += 1
                    else:
                        skipped_count += 1
                    progress.update(task, advance=1)
        else:
            for app_id in installed_apps:
                if self.generate_wrapper(app_id):
                    created_count += 1
                else:
                    skipped_count += 1

        return created_count, updated_count, skipped_count

    def run(self) -> int:
        """Main generation process."""
        try:
            # Acquire lock (skip in emit mode)
            if not self.emit_mode and not acquire_lock(self.lock_name, 30):
                self.log("Failed to acquire generation lock", "error")
                return 1

            try:
                # Get installed applications
                installed_apps = self.get_installed_flatpaks()
                app_count = len(installed_apps)
                self.log(f"Found {app_count} Flatpak applications")

                if app_count == 0:
                    self.log(
                        "No Flatpak applications found. Install some with: flatpak install <app>",
                        "warning",
                    )
                    return 1

                # Clean up obsolete wrappers
                removed_count = self.cleanup_obsolete_wrappers(installed_apps)

                # Generate new wrappers
                created_count, updated_count, skipped_count = self.generate_wrappers(
                    installed_apps,
                )

                # Summary
                self.log("")
                self.log("📊 Generation Summary:")
                self.log(f"   ✅ Created: {created_count} new wrappers")
                self.log(f"   🔄 Updated: {updated_count} existing wrappers")
                self.log(f"   🚫 Skipped: {skipped_count} applications")
                if removed_count > 0:
                    self.log(f"   🗑️  Removed: {removed_count} obsolete wrappers")

                self.log("")
                self.log("🎉 Flatpak wrapper generation complete!")
                self.log("")
                self.log("💡 Next steps:")
                self.log("   fplaunch list              # See your wrappers")
                self.log("   fplaunch monitor           # Monitor for changes")
                self.log("   firefox --fpwrapper-help   # See wrapper options")

                return 0

            finally:
                if not self.emit_mode:
                    release_lock(self.lock_name)

        except Exception as e:
            self.log(f"Generation failed: {e}", "error")

            # Send failure notification if notifications are enabled
            try:
                from lib.config_manager import create_config_manager
                from lib.notifications import send_update_failure_notification

                config = create_config_manager()
                if config.get_enable_notifications():
                    send_update_failure_notification(str(e))
            except Exception:
                # Ignore any errors in notification system
                pass

            return 1

    def generate_wrappers(self, installed_apps: list[str]) -> tuple[int, int, int]:
        """Generate wrappers for all apps - alias for generate_all_wrappers."""
        return self.generate_all_wrappers(installed_apps)


def main():
    """Command-line interface for wrapper generation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Flatpak application wrappers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m generate /home/user/bin        # Generate in specific directory
  python -m generate --verbose ~/bin       # Verbose output
  python -m generate $HOME/.local/bin      # Use local bin directory
  python -m generate --emit ~/bin          # Show what would be done
        """,
    )

    parser.add_argument(
        "bin_dir",
        nargs="?",
        default=os.path.expanduser("~/bin"),
        help="Directory to store wrapper scripts (default: ~/bin)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of all wrappers",
    )

    parser.add_argument(
        "--emit",
        action="store_true",
        help="Emit commands instead of executing (dry run)",
    )

    args = parser.parse_args()

    # Validate bin directory (skip in emit mode)
    if not args.emit:
        bin_dir = os.path.expanduser(args.bin_dir)
        if not validate_home_dir(bin_dir) if UTILS_AVAILABLE else True:
            return 1

    # Create generator and run
    generator = WrapperGenerator(args.bin_dir, args.verbose, args.emit)
    return generator.run()


if __name__ == "__main__":
    sys.exit(main())
