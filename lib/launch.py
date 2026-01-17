#!/usr/bin/env python3
"""Application launcher for fplaunchwrapper
Replaces fplaunch-launch bash script with Python implementation.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Import our utilities
try:
    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False

# Import safety mechanisms using lazy loading to avoid circular imports
# SAFETY_AVAILABLE = False  # Will be set lazily


class AppLauncher:
    """Launch Flatpak applications with preference handling."""

    def __init__(
        self,
        app_name: str | None = None,
        config_dir: str | None = None,
        bin_dir: str | None = None,
        args: list[str] | None = None,
        env: dict | None = None,
        verbose: bool = False,
        debug: bool = False,
    ) -> None:
        self.app_name = app_name
        self.verbose = verbose
        self.debug = debug
        self.env = env

        self.config_dir = Path(
            config_dir or (Path.home() / ".config" / "fplaunchwrapper"),
        )
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Get bin directory - prioritize parameter, then config, then default
        if bin_dir:
            self.bin_dir = Path(bin_dir)
        else:
            bin_dir_file = self.config_dir / "bin_dir"
            if bin_dir_file.exists():
                self.bin_dir = Path(bin_dir_file.read_text().strip())
            else:
                self.bin_dir = Path.home() / "bin"

        self.args = args or []
        self._safety_check = None  # Lazy-loaded safety check function

    def _get_safety_check(self):
        """Lazy load safety module to avoid circular imports."""
        if self._safety_check is None:
            try:
                from fplaunch.safety import safe_launch_check
                self._safety_check = safe_launch_check
                return True, self._safety_check
            except ImportError:
                # Safety module not available, allow all launches
                self._safety_check = lambda *args, **kwargs: True
                return True, self._safety_check
        return True, self._safety_check

    def _get_hook_scripts(self, app_name: str, hook_type: str) -> list[Path]:
        """Get pre or post-launch hook scripts for an app.
        
        Hook scripts are stored in:
        - ~/.config/fplaunchwrapper/hooks/{app_name}.{pre,post}.sh
        - ~/.config/fplaunchwrapper/hooks/{app_name}/{pre,post}/*.sh
        """
        hooks_dir = self.config_dir / "hooks"
        scripts = []

        # Single hook files
        if hook_type in ["pre", "post"]:
            single_hook = hooks_dir / f"{app_name}.{hook_type}.sh"
            if single_hook.exists() and os.access(single_hook, os.X_OK):
                scripts.append(single_hook)

        # Hook directory
        hook_dir = hooks_dir / app_name / hook_type
        if hook_dir.exists() and hook_dir.is_dir():
            for script in sorted(hook_dir.glob("*.sh")):
                if script.is_file() and os.access(script, os.X_OK):
                    scripts.append(script)

        return scripts

    def _substitute_environment(self, script_path: Path) -> str:
        """Substitute environment variables in hook script content."""
        content = script_path.read_text()

        # Available substitutions
        env_vars = {
            "APP_NAME": self.app_name or "",
            "APP_ID": self.app_name or "",
            "WRAPPER_PATH": str(self._get_wrapper_path()),
            "CONFIG_DIR": str(self.config_dir),
            "BIN_DIR": str(self.bin_dir),
            "HOME": str(Path.home()),
        }

        # Add custom environment if provided
        if self.env:
            env_vars.update(self.env)

        # Substitute ${VAR} patterns
        for var_name, var_value in env_vars.items():
            content = content.replace(f"${{{var_name}}}", str(var_value))
            content = content.replace(f"${var_name}", str(var_value))

        return content

    def _run_hook_scripts(self, hook_type: str) -> bool:
        """Run pre or post-launch hook scripts.
        
        Args:
            hook_type: Either 'pre' or 'post'
            
        Returns:
            True if all scripts succeeded or no scripts exist, False if any failed
        """
        scripts = self._get_hook_scripts(self.app_name, hook_type)

        if not scripts:
            return True

        if self.verbose:
            print(f"Running {hook_type}-launch scripts for {self.app_name}", file=sys.stderr)

        for script_path in scripts:
            try:
                if self.debug:
                    print(f"Executing {hook_type} hook: {script_path}", file=sys.stderr)

                # Try running the script directly
                result = subprocess.run(
                    [str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    if self.verbose:
                        print(
                            f"Warning: {hook_type} hook failed ({script_path}): {result.stderr}",
                            file=sys.stderr,
                        )
                    # Don't fail the whole launch if hook fails
                    if hook_type == "pre":
                        # Pre-hooks are more critical
                        return False

                elif self.verbose and result.stdout:
                    print(f"{hook_type} hook output: {result.stdout}", file=sys.stderr)

            except subprocess.TimeoutExpired:
                if self.verbose:
                    print(
                        f"Warning: {hook_type} hook timed out ({script_path})",
                        file=sys.stderr,
                    )
                if hook_type == "pre":
                    return False
            except Exception as e:
                if self.verbose:
                    print(
                        f"Warning: Error running {hook_type} hook ({script_path}): {e}",
                        file=sys.stderr,
                    )
                if hook_type == "pre":
                    return False

        return True

    def launch_app(self, app_name: str, args: list[str] | None = None) -> bool:
        """Convenience wrapper for legacy API: set the app name and call launch."""
        self.app_name = app_name
        self.args = args or []
        return self.launch()

    # Backwards compatibility: provide launch_app method

    def _get_wrapper_path(self, app_name: str | None = None) -> Path:
        """Get the wrapper path for an application."""
        name = app_name or self.app_name
        return self.bin_dir / name

    def _wrapper_exists(self, app_name: str | None = None) -> bool:
        """Check if wrapper exists and is executable."""
        wrapper_path = self._get_wrapper_path(app_name)
        return wrapper_path.exists() and os.access(wrapper_path, os.X_OK)

    def _find_wrapper(self) -> Path | None:
        """Find the wrapper script for the application."""
        wrapper_path = self._get_wrapper_path()
        if wrapper_path.exists() and os.access(wrapper_path, os.X_OK):
            return wrapper_path
        return None

    def launch(self) -> bool:
        """Launch the application with pre/post-launch hook support."""
        try:
            # Safety check using lazy-loaded safety module
            safety_available, safe_launch_check = self._get_safety_check()
            if safety_available and not safe_launch_check(self.app_name, self._find_wrapper()):
                return False

            # Run pre-launch hooks
            if not self._run_hook_scripts("pre"):
                if self.verbose:
                    print(f"Pre-launch hooks failed for {self.app_name}", file=sys.stderr)
                return False

            wrapper_path = self._find_wrapper()

            if not wrapper_path:
                # Fallback to flatpak
                cmd = ["flatpak", "run", self.app_name, *self.args]
            else:
                cmd = [str(wrapper_path), *self.args]

            if self.debug:
                print(f"Launching: {' '.join(cmd)}", file=sys.stderr)

            run_kwargs = {"capture_output": False}
            if self.env:
                run_kwargs["env"] = self.env

            result = subprocess.run(cmd, **run_kwargs)
            launch_success = result.returncode == 0

            # Run post-launch hooks (even if launch failed)
            if not self._run_hook_scripts("post"):
                if self.verbose:
                    print(f"Post-launch hooks failed for {self.app_name}", file=sys.stderr)
                # Don't fail based on post-launch hook failure
                # (app already launched)

            return launch_success

        except KeyboardInterrupt:
            if self.verbose:
                print(f"Launch interrupted for {self.app_name}", file=sys.stderr)
            return False
        except Exception as e:
            if self.verbose:
                print(f"Error launching {self.app_name}: {e}", file=sys.stderr)
            return False


def main():
    """Command-line interface for launching applications."""
    if len(sys.argv) < 2:
        return 1

    app_name = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    launcher = AppLauncher(app_name, args=args)
    return 0 if launcher.launch() else 1


if __name__ == "__main__":
    sys.exit(main())
