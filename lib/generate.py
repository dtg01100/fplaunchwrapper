#!/usr/bin/env python3
"""Wrapper generation functionality for fplaunchwrapper
Replaces fplaunch-generate bash script with Python implementation.


Import Pattern Notes:
====================
This module uses lazy imports for config_manager to avoid circular imports.
When config_manager imports from modules that eventually import back from
generate.py, we would get a circular import. The solution is to import
config_manager inside the function/method that needs it, rather than at
module level.

This pattern is intentional and documented:
1. Imports at module level: Core dependencies (exceptions, paths, safety)
2. Imports inside functions: Optional dependencies that could cause circular imports

Usage:
    try:
        from .config_manager import create_config_manager
        config = create_config_manager()
    except OSError:
        # Config manager unavailable, use defaults
        pass
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from importlib.resources import files as importlib_files

from rich.console import Console as _Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
)

from .exceptions import (
    ForbiddenNameError,
    WrapperGenerationError,
)
from .paths import ensure_dir
from .python_utils import (
    acquire_lock,
    find_executable,
    release_lock,
    sanitize_id_to_name,
)
from .logging_utils import LoggingMixin
from .safety import (
    get_wrapper_id,
    is_wrapper_file,
)

console = _Console()
logger = logging.getLogger(__name__)


class WrapperGenerator(LoggingMixin):
    """Generates Flatpak application wrappers."""

    def __init__(
        self,
        bin_dir: str | Path,
        config_dir: str | Path | None = None,
        verbose: bool = False,
        emit_mode: bool = False,
        emit_verbose: bool = False,
        **kwargs: Any,
    ) -> None:
        if not isinstance(bin_dir, (str, os.PathLike)):
            raise TypeError("bin_dir must be a string or path-like object")
        if config_dir is not None and not isinstance(config_dir, (str, os.PathLike)):
            raise TypeError("config_dir must be a string or path-like object or None")

        self.bin_dir = self._safe_resolve_bin_dir(bin_dir)
        self.verbose = verbose
        self.emit_mode = emit_mode
        self.emit_verbose = emit_verbose
        self.lock_name = "generate"
        self.config_dir = Path(config_dir) if config_dir else None

        if not self.emit_mode and self.config_dir is not None:
            ensure_dir(self.bin_dir)
            ensure_dir(self.config_dir)
            (self.config_dir / "bin_dir").write_text(str(self.bin_dir))

    @staticmethod
    def _enforce_home_boundary(resolved: Path, original_str: str, user_home: Path) -> Path:
        """Check resolved path is under home or /tmp, falling back to ~/bin if not."""
        try:
            resolved.relative_to(user_home)
        except ValueError:
            if str(resolved).startswith("/tmp/"):  # nosec B108
                return resolved
            print(
                f"Warning: bin_dir '{original_str}' resolves outside home directory, "
                f"falling back to {user_home / 'bin'}",
                file=sys.stderr,
            )
            resolved = user_home / "bin"
        return resolved

    def _safe_resolve_bin_dir(self, bin_dir: str | Path) -> Path:
        """Resolve bin_dir with symlink and boundary validation.

        Resolves symlinks but enforces home directory boundaries for ALL paths.
        Paths outside home are rejected and will fall back to ~/bin.
        This prevents path traversal attacks that could place wrappers in
        sensitive locations like /etc, /usr, or /root.

        Exception: /tmp paths are allowed since they're standard temporary
        directories and not sensitive system locations.
        """
        user_home = Path.home()
        bin_str = str(bin_dir)

        if bin_str.startswith("~"):
            resolved = Path(bin_dir).expanduser().resolve()
        elif Path(bin_str).is_absolute():
            resolved = Path(bin_str).resolve()
        else:
            resolved = Path(bin_str).expanduser().resolve()

        return self._enforce_home_boundary(resolved, bin_str, user_home)

    def is_forbidden_wrapper_name(self, name: str) -> bool:
        """Check if a wrapper name collides with basic system commands."""
        return name.lower() in ForbiddenNameError.FORBIDDEN_NAMES

    def run_command(
        self,
        cmd: list[str],
        description: str = "",
    ) -> subprocess.CompletedProcess:
        """Run a command and return its output."""
        if description and not self.verbose:
            with console.status(f"[bold green]{description}..."):
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
        else:
            if description and self.verbose:
                self.log(description, "debug")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result

    def get_installed_flatpaks(self) -> list[str]:
        """Get a list of installed Flatpak application IDs."""
        self.log("Fetching installed Flatpaks...", "debug")

        flatpak_path = find_executable("flatpak")
        if flatpak_path is None:
            raise WrapperGenerationError(
                "flatpak",
                "Failed to find flatpak executable in PATH",
            )

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
        stdout_str = str(result.stdout).strip()
        if stdout_str:
            for line in stdout_str.split("\n"):
                line = line.strip()
                if line and not line.startswith("Application ID"):
                    apps.append(line)

        # Also check system installations.
        # Required by TestWrapperGeneratorReal.test_get_installed_flatpaks_with_duplicates
        result_system = self.run_command(
            [flatpak_path, "list", "--app", "--columns=application", "--system"],
            "Checking system Flatpak installations",
        )
        if not result_system.returncode:
            stdout_system = str(result_system.stdout).strip()
            if stdout_system:
                for line in stdout_system.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("Application ID") and line not in apps:
                        apps.append(line)

        return sorted(set(apps))

    def is_blocklisted(self, app_id: str) -> bool:
        """Check if an app ID is in the blocklist."""
        if self.config_dir is None:
            return False
        blocklist_file = self.config_dir / "blocklist"
        if not blocklist_file.exists():
            return False

        try:
            content = blocklist_file.read_text()
            blocklisted = {line.strip() for line in content.split("\n") if line.strip()}
            return app_id in blocklisted
        except OSError as e:
            self.log(f"Failed to read blocklist: {e}", "warning")
            return False

    def create_wrapper_script(self, wrapper_name: str, app_id: str) -> str:
        """Create the content for a wrapper script using a template."""
        # Search for template in multiple locations
        candidates = []

        # 1. When installed: use importlib.resources to find template in package data
        try:
            template_file = importlib_files("lib") / "templates" / "wrapper.template.sh"
            candidates.append(Path(str(template_file)))
        except (TypeError, AttributeError, FileNotFoundError):
            pass

        # 2. Development mode: templates/ at project root
        candidates.append(
            Path(__file__).parent.parent / "templates" / "wrapper.template.sh",
        )

        # 3. Fallback: relative path (for running from project root)
        candidates.append(Path("templates/wrapper.template.sh"))

        # Find first existing path
        template_path = None
        for candidate in candidates:
            if candidate.exists():
                template_path = candidate
                break

        if template_path is None:
            msg = f"Wrapper template file not found: {candidates[0]}"
            raise WrapperGenerationError(app_id, msg)

        try:
            content = template_path.read_text()

            # Get failure mode default and script paths from config if possible
            failure_mode = "warn"
            pre_launch_script = ""
            post_launch_script = ""
            try:
                from .config_manager import create_config_manager

                config = create_config_manager()
                failure_mode = getattr(
                    config.config,
                    "hook_failure_mode_default",
                    "warn",
                )

                prefs = config.get_app_preferences(wrapper_name)
                pre_launch_script = prefs.pre_launch_script or ""
                post_launch_script = prefs.post_launch_script or ""
            except OSError:
                pass

            def _format_escape(s: str) -> str:
                # Escape for Python format string and bash injection prevention
                return (
                    s.replace("\\", "\\\\")
                    .replace("`", "\\`")
                    .replace("$", "\\$")
                    .replace("{", "{{")
                    .replace("}", "}}")
                )

            return content.format(
                wrapper_name=wrapper_name,
                app_id=app_id,
                config_dir=str(self.config_dir),
                bin_dir=str(self.bin_dir),
                hook_failure_mode_default=failure_mode,
                pre_launch_script=_format_escape(pre_launch_script),
                post_launch_script=_format_escape(post_launch_script),
            )

        except (OSError, KeyError, ValueError) as e:
            logger.exception("Failed to read wrapper template for %s", app_id)
            raise WrapperGenerationError(
                app_id,
                f"Failed to read wrapper template: {e}",
            ) from e

    def generate_wrapper(self, app_id: str, flatpak_id: str | None = None) -> bool:
        """Generate a wrapper for a specific Flatpak app."""
        if self.is_blocklisted(app_id):
            self.log(f"Skipping blocklisted app: {app_id}", "warning")
            return False

        try:
            wrapper_name = sanitize_id_to_name(app_id)
        except ForbiddenNameError:
            self.log(f"Skipping forbidden name: {app_id}", "warning")
            return False

        if not wrapper_name:
            self.log(f"Skipping invalid app ID: {app_id}", "warning")
            return False

        if self.is_forbidden_wrapper_name(wrapper_name):
            self.log(f"Skipping forbidden wrapper name: {wrapper_name}", "warning")
            return False

        target_flatpak_id = flatpak_id or app_id

        # Simple validation of flatpak_id
        # Valid Flatpak IDs use reverse-DNS notation and must start with a letter
        # and contain at least one dot (e.g., org.mozilla.firefox)
        if (
            not re.match(r"^[A-Za-z][A-Za-z0-9._-]*$", target_flatpak_id)
            or "." not in target_flatpak_id
        ):
            if flatpak_id is not None:
                self.log(f"Skipping invalid Flatpak ID: {target_flatpak_id}", "warning")
                return False
            target_flatpak_id = sanitize_id_to_name(app_id)
            if not target_flatpak_id:
                self.log(
                    f"Skipping invalid app ID (unsanitizable): {app_id}",
                    "warning",
                )
                return False

        wrapper_path = self.bin_dir / wrapper_name

        # Check for name collisions
        wrapper_existed = wrapper_path.exists()
        if wrapper_existed:
            existing_id = get_wrapper_id(str(wrapper_path))
            if existing_id is None:
                self.log(
                    f"Name collision for '{wrapper_name}': existing file not a wrapper",
                    "warning",
                )
                return False
            if existing_id != app_id:
                self.log(
                    f"Name collision for '{wrapper_name}': {existing_id} vs {app_id}",
                    "warning",
                )
                return False

        try:
            content = self.create_wrapper_script(wrapper_name, target_flatpak_id)
        except (OSError, KeyError, ValueError, WrapperGenerationError) as e:
            logger.exception("Failed to create wrapper for %s", app_id)
            self.log(f"Failed to create wrapper for {app_id}: {e}", "error")
            return False

        if self.emit_mode:
            action = "Update" if wrapper_existed else "Create"
            self.log(f"EMIT: Would {action.lower()} wrapper: {wrapper_name}")
            if self.emit_verbose:
                self.log(f"EMIT: File content for {wrapper_path}:")
                from rich.panel import Panel

                console.print(
                    Panel.fit(
                        content,
                        title=f"📄 {wrapper_name} wrapper script",
                        border_style="blue",
                    ),
                )
            return True

        try:
            wrapper_path.write_text(content)
            wrapper_path.chmod(0o755)
            if wrapper_existed:
                self.log(f"Updated wrapper: {wrapper_name}")
            else:
                self.log(f"Created wrapper: {wrapper_name}")
            return True
        except OSError as e:
            logger.exception("Failed to create wrapper %s", wrapper_name)
            self.log(f"Failed to create wrapper {wrapper_name}: {e}", "error")
            return False

    def cleanup_obsolete_wrappers(self, installed_apps: list[str]) -> int:
        """Remove wrappers for apps that are no longer installed."""
        removed_count = 0
        if not self.bin_dir.exists():
            return 0

        for item in self.bin_dir.iterdir():
            # Skip directories
            if item.is_dir():
                continue

            # Handle symlinks separately - check if they point to valid wrappers
            is_symlink = item.is_symlink()
            is_file = item.is_file()

            # Skip if not a file and not a symlink
            if not is_file and not is_symlink:
                continue

            remove_item = False
            if is_symlink:
                target = item.resolve()
                if not target.exists():
                    remove_item = True
                else:
                    wrapper_id = get_wrapper_id(str(target))
                    if wrapper_id and wrapper_id not in installed_apps:
                        remove_item = True
            elif is_wrapper_file(str(item)):
                wrapper_id = get_wrapper_id(str(item))
                if wrapper_id and wrapper_id not in installed_apps:
                    remove_item = True
            else:
                # Only remove non-wrapper files that are executable shell scripts
                # (potential legacy wrappers). Skip non-executable files to avoid
                # accidentally deleting user data.
                if os.access(item, os.X_OK) and is_file:
                    try:
                        with item.open("rb") as fh:
                            header = fh.read(2)
                            if header == b"#!":
                                remove_item = True
                    except OSError as e:
                        self.log(f"Could not read {item} header: {e}", "debug")

            if remove_item:
                self.log(f"Removing obsolete wrapper: {item.name}")
                if self.emit_mode:
                    removed_count += 1
                else:
                    try:
                        item.unlink()
                        removed_count += 1

                        # Remove associated files.
                        # Required by
                        # TestWrapperGeneratorReal.test_cleanup_obsolete_wrappers_removes_old
                        if self.config_dir is not None:
                            pref_file = self.config_dir / f"{item.name}.pref"
                            if pref_file.exists():
                                pref_file.unlink()

                            # Remove associated .env file
                            env_file = self.config_dir / f"{item.name}.env"
                            if env_file.exists():
                                env_file.unlink()

                            # Remove associated scripts directory
                            scripts_dir = self.config_dir / "scripts" / item.name
                            if scripts_dir.exists() and scripts_dir.is_dir():
                                shutil.rmtree(scripts_dir)
                            # Update aliases. Required by TestWrapperGeneratorReal.
                            # test_cleanup_obsolete_wrappers_removes_aliases
                            aliases_file = self.config_dir / "aliases"
                            if aliases_file.exists():
                                content = aliases_file.read_text()
                                new_content = "\n".join(
                                    line
                                    for line in content.split("\n")
                                    if not line.startswith(f"{item.name}:")
                                )
                                if new_content.strip():
                                    aliases_file.write_text(new_content)
                                else:
                                    aliases_file.unlink()
                    except OSError as e:
                        self.log(f"Failed to remove {item.name}: {e}", "warning")

        return removed_count

    def run(self) -> int:
        """Main entry point for wrapper generation."""
        try:
            if not self.emit_mode and not acquire_lock(self.lock_name, 30):
                self.log("Failed to acquire generation lock", "error")
                return 1

            try:
                apps = self.get_installed_flatpaks()
                app_count = len(apps)
                self.log(f"Found {app_count} Flatpak applications")

                if app_count == 0:
                    self.log("No Flatpak apps found", "warning")
                    return 0

                success_count = 0
                created, updated, skipped = self.generate_wrappers(apps)
                success_count = created + updated

                self.cleanup_obsolete_wrappers(apps)

                self.log(f"Generated {success_count} wrappers", "success")
                return 0
            finally:
                if not self.emit_mode:
                    release_lock(self.lock_name)
        except (OSError, ValueError) as e:
            self.log(f"Generation failed: {e}", "error")
            return 1

    def generate_wrappers(self, installed_apps: list[str]) -> tuple[int, int, int]:
        """Generate wrappers for all installed applications."""
        created_count = 0
        updated_count = 0
        skipped_count = 0

        # Pre-compute which wrappers already exist to track created vs updated
        existing_wrappers: set[str] = set()
        if self.bin_dir.exists():
            for item in self.bin_dir.iterdir():
                if item.is_file() and is_wrapper_file(str(item)):
                    wrapper_id = get_wrapper_id(str(item))
                    if wrapper_id:
                        existing_wrappers.add(wrapper_id)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            disable=not self.verbose and not sys.stdout.isatty(),
        ) as progress:
            task = progress.add_task(
                "Generating wrappers...",
                total=len(installed_apps),
            )
            for app_id in installed_apps:
                # Track if this app had a wrapper before
                had_wrapper_before = app_id in existing_wrappers

                if self.generate_wrapper(app_id):
                    if had_wrapper_before:
                        updated_count += 1
                    else:
                        created_count += 1
                else:
                    skipped_count += 1
                progress.update(task, advance=1)

        return created_count, updated_count, skipped_count


def main() -> int:
    """Command-line interface for wrapper generation."""
    parser = argparse.ArgumentParser(
        description="Generate Flatpak application wrappers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "bin_dir",
        nargs="?",
        default=str(Path("~/bin").expanduser()),
        help="Directory to store wrappers (default: ~/bin)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--emit",
        action="store_true",
        help="Emit commands instead of executing (dry run)",
    )

    parser.add_argument(
        "--emit-verbose",
        action="store_true",
        help="Show full content of wrappers in emit mode",
    )

    args = parser.parse_args()

    bin_dir = args.bin_dir or str(Path("~/bin").expanduser())

    generator = WrapperGenerator(
        bin_dir=bin_dir,
        verbose=args.verbose,
        emit_mode=args.emit,
        emit_verbose=args.emit_verbose,
    )
    return generator.run()


if __name__ == "__main__":
    sys.exit(main())
