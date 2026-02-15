#!/usr/bin/env python3
"""Wrapper generation functionality for fplaunchwrapper
Replaces fplaunch-generate bash script with Python implementation.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from rich.console import Console as _Console
from rich.progress import (
    BarColumn as _BarColumn,
)
from rich.progress import (
    Progress as _Progress,
)
from rich.progress import (
    SpinnerColumn as _SpinnerColumn,
)
from rich.progress import (
    TextColumn as _TextColumn,
)

Console = _Console
BarColumn = _BarColumn
Progress = _Progress
SpinnerColumn = _SpinnerColumn
TextColumn = _TextColumn

# Define fallback functions first with explicit types
def _acquire_lock_fallback(name: str, timeout: float = 30) -> bool:
    return False

def _find_executable_fallback(name: str) -> str | None:
    return None

def _get_wrapper_id_fallback(path: str) -> str | None:
    return None

def _is_wrapper_file_fallback(path: str) -> bool:
    return False

def _release_lock_fallback(name: str) -> bool:
    return False

def _sanitize_id_to_name_fallback(app_id: str) -> str:
    return ""

def _validate_home_dir_fallback(path: str) -> str | None:
    return None

class _ForbiddenNameError(Exception):
    FORBIDDEN_NAMES: frozenset[str] = frozenset()

class _WrapperGenerationError(Exception):
    def __init__(self, app_id: str, message: str):
        self.app_id = app_id
        super().__init__(message)

from typing import Union

acquire_lock: Callable[[str, float], bool | None] = _acquire_lock_fallback
find_executable: Callable[[str], str | None] = _find_executable_fallback
get_wrapper_id: Callable[[str], str | None] = _get_wrapper_id_fallback
is_wrapper_file: Callable[[str], bool] = _is_wrapper_file_fallback
release_lock: Callable[[str], bool | None] = _release_lock_fallback
sanitize_id_to_name: Callable[[str], str] = _sanitize_id_to_name_fallback
validate_home_dir: Callable[[str], str | None] = _validate_home_dir_fallback

ForbiddenNameError: Any = _ForbiddenNameError
WrapperGenerationError: Any = _WrapperGenerationError

try:
    from .exceptions import (
        ForbiddenNameError as _ForbiddenNameErrorReal,
        WrapperGenerationError as _WrapperGenerationErrorReal,
    )
    from .python_utils import (
        acquire_lock as _acquire_lock_real,
        find_executable as _find_executable_real,
        release_lock as _release_lock_real,
    )
    from .safety import (
        get_wrapper_id as _get_wrapper_id_real,
        is_wrapper_file as _is_wrapper_file_real,
        sanitize_id_to_name as _sanitize_id_to_name_real,
        validate_home_dir as _validate_home_dir_real,
    )
    acquire_lock = _acquire_lock_real
    find_executable = _find_executable_real
    release_lock = _release_lock_real
    get_wrapper_id = _get_wrapper_id_real
    is_wrapper_file = _is_wrapper_file_real
    sanitize_id_to_name = _sanitize_id_to_name_real
    validate_home_dir = _validate_home_dir_real
    ForbiddenNameError = _ForbiddenNameErrorReal
    WrapperGenerationError = _WrapperGenerationErrorReal
    UTILS_AVAILABLE = True
except Exception:
    UTILS_AVAILABLE = False

console = _Console()
console_err = _Console(stderr=True)


class WrapperGenerator:
    """Generates Flatpak application wrappers."""

    def __init__(
        self,
        bin_dir: str,
        config_dir: str | None | bool = None,
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
        return name.lower() in ForbiddenNameError.FORBIDDEN_NAMES

    def log(self, message: str, level: str = "info") -> None:
        """Log a message to appropriate stream."""
        if level == "error":
            console_err.print(f"[red]ERROR:[/red] {message}")
        elif level == "warning":
            console_err.print(f"[yellow]WARN:[/yellow] {message}")
        elif level == "success":
            console.print(f"[green]✓[/green] {message}")
        else:
            console.print(message)

    def run_command(
        self,
        cmd: list[str],
        description: str = "",
    ) -> subprocess.CompletedProcess:
        """Run a command with optional progress display."""
        if description and not self.verbose:
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
            raise WrapperGenerationError(
                "flatpak", "Flatpak not found. Please install Flatpak first."
            )

        self.log(f"Found Flatpak at: {flatpak_path}")

        result = self.run_command(
            [flatpak_path, "list", "--app", "--columns=application"],
            "Getting installed Flatpak applications",
        )

        if result.returncode != 0:
            raise WrapperGenerationError(
                "flatpak",
                f"Failed to get Flatpak applications: {result.stderr}",
            )

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

        if not self.bin_dir.exists():
            return 0

        for item in self.bin_dir.iterdir():
            if not item.is_file():
                continue

            remove_item = False

            if UTILS_AVAILABLE and is_wrapper_file(str(item)):
                wrapper_id = get_wrapper_id(str(item))
                if wrapper_id and wrapper_id not in installed_apps:
                    remove_item = True
            else:
                sanitized_installed = [sanitize_id_to_name(a) for a in installed_apps]
                if item.name not in sanitized_installed:
                    remove_item = True

            if remove_item:
                self.log(f"Removing obsolete wrapper: {item.name}")
                try:
                    item.unlink()
                    removed_count += 1

                    pref_file = self.config_dir / f"{item.name}.pref"
                    if pref_file.exists():
                        pref_file.unlink()

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
            raise WrapperGenerationError(app_id, "Python utilities not available")

        if self.is_blocklisted(app_id):
            self.log(f"Skipping blocklisted app: {app_id}", "warning")
            return False

        wrapper_name = sanitize_id_to_name(app_id)
        if not wrapper_name:
            self.log(f"Skipping invalid app ID: {app_id}", "warning")
            return False

        if self.is_forbidden_wrapper_name(wrapper_name):
            self.log(f"Skipping forbidden wrapper name: {wrapper_name}", "warning")
            return False

        target_flatpak_id = flatpak_id or app_id

        import re

        if not re.match(r"^[A-Za-z0-9._-]+$", target_flatpak_id):
            if flatpak_id is not None:
                self.log(
                    f"Skipping invalid Flatpak ID: {target_flatpak_id}",
                    "warning",
                )
                return False
            target_flatpak_id = sanitize_id_to_name(app_id)
            if not target_flatpak_id:
                self.log(
                    f"Skipping invalid app ID (unsanitizable): {app_id}",
                    "warning",
                )
                return False

        wrapper_path = self.bin_dir / wrapper_name

        try:
            wrapper_existed = wrapper_path.exists()
        except PermissionError:
            self.log(f"Permission denied accessing {wrapper_path}", "error")
            return False
        if wrapper_existed:
            existing_id = get_wrapper_id(str(wrapper_path)) if UTILS_AVAILABLE else None
            if existing_id is None:
                try:
                    _ = wrapper_path.read_text()
                except Exception as e:
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
            action = "Update" if wrapper_existed else "Create"
            self.log(f"EMIT: Would {action.lower()} wrapper: {wrapper_name}")
            self.log(
                f"EMIT: Would write {len(wrapper_content)} bytes to {wrapper_path}",
            )
            self.log(f"EMIT: Would set permissions to 755 on {wrapper_path}")

            print(f"EMIT MODE active for {wrapper_name}")

            if self.emit_verbose:
                self.log(f"EMIT: File content for {wrapper_path}:")
                from rich.panel import Panel

                console.print(
                    Panel.fit(
                        wrapper_content,
                        title=f"📄 {wrapper_name} wrapper script",
                        border_style="blue",
                    ),
                )
                print(wrapper_content)

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

    def create_wrapper_script(self, wrapper_name: str, app_id: str) -> str:
        """Create the content of a wrapper script by reading from template file."""
        script_dir = Path(__file__).parent
        template_path = script_dir.parent / "templates" / "wrapper.template.sh"

        hook_failure_mode_default = "warn"
        try:
            from lib.config_manager import create_config_manager
            config = create_config_manager()
            hook_failure_mode_default = config.config.hook_failure_mode_default or "warn"
        except Exception:
            pass  # Use default

        try:
            with open(template_path, "r") as file:
                template_content = file.read()

            return template_content.format(
                wrapper_name=wrapper_name,
                app_id=app_id,
                config_dir=str(self.config_dir),
                bin_dir=str(self.bin_dir),
                hook_failure_mode_default=hook_failure_mode_default,
            )

        except FileNotFoundError as e:
            raise WrapperGenerationError(
                app_id, f"Wrapper template file not found: {template_path}"
            ) from e
        except Exception as e:
            raise WrapperGenerationError(
                app_id, f"Failed to read wrapper template: {e}"
            ) from e

    def generate_all_wrappers(self, installed_apps: list[str]) -> tuple[int, int, int]:
        """Generate wrappers for all installed applications."""
        self.log("Generating wrappers...")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        if not self.verbose:
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
            if not self.emit_mode and not acquire_lock(self.lock_name, 30):
                self.log("Failed to acquire generation lock", "error")
                return 1

            try:
                installed_apps = self.get_installed_flatpaks()
                app_count = len(installed_apps)
                self.log(f"Found {app_count} Flatpak applications")

                if app_count == 0:
                    self.log(
                        "No Flatpak applications found. Install some with: flatpak install <app>",
                        "warning",
                    )
                    return 1

                removed_count = self.cleanup_obsolete_wrappers(installed_apps)

                created_count, updated_count, skipped_count = self.generate_wrappers(
                    installed_apps,
                )

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

            try:
                from lib.config_manager import create_config_manager
                from lib.notifications import send_update_failure_notification

                config = create_config_manager()
                if config.get_enable_notifications():
                    send_update_failure_notification(str(e))
            except Exception:
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

    if not args.emit:
        bin_dir = os.path.expanduser(args.bin_dir)
        if not validate_home_dir(bin_dir) if UTILS_AVAILABLE else True:
            return 1

    generator = WrapperGenerator(args.bin_dir, args.verbose, args.emit)
    return generator.run()


if __name__ == "__main__":
    sys.exit(main())
