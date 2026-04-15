#!/usr/bin/env python3
"""Portal-aware launcher for Flatpak applications.

Uses flatpak-spawn to launch applications with proper XDG portal integration,
providing better sandbox awareness and file picker integration.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional


# Check for flatpak-spawn availability
FLATPAK_SPAWN_PATH: Optional[str] = shutil.which("flatpak-spawn")


def is_portal_launcher_available() -> bool:
    """Check if flatpak-spawn is available for portal-aware launching."""
    return FLATPAK_SPAWN_PATH is not None


def launch_with_portal(
    flatpak_id: str,
    args: Optional[list[str]] = None,
    env_overrides: Optional[dict[str, str]] = None,
    cwd: Optional[str] = None,
    wait: bool = False,
) -> subprocess.CompletedProcess:
    """Launch a Flatpak application via flatpak-spawn with portal support.

    flatpak-spawn forwards portal requests (file picker, etc.) to the host,
    providing better integration than direct flatpak run.

    Args:
        flatpak_id: The Flatpak application ID (e.g., "org.mozilla.firefox")
        args: Optional arguments to pass to the application
        env_overrides: Optional environment variable overrides
        cwd: Working directory for the command
        wait: Whether to wait for the process to exit

    Returns:
        CompletedProcess result

    Raises:
        FileNotFoundError: If flatpak-spawn is not available
    """
    if not FLATPAK_SPAWN_PATH:
        raise FileNotFoundError(
            "flatpak-spawn not found. Install flatpak-tools or use direct flatpak run."
        )

    cmd = [FLATPAK_SPAWN_PATH, "--host", "flatpak", "run"]

    if wait:
        cmd.append("--wait")

    cmd.append(flatpak_id)

    if args:
        cmd.extend(args)

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        cmd,
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def launch_direct(
    flatpak_id: str,
    args: Optional[list[str]] = None,
    env_overrides: Optional[dict[str, str]] = None,
    cwd: Optional[str] = None,
    wait: bool = False,
) -> subprocess.CompletedProcess:
    """Launch a Flatpak application directly with flatpak run.

    This is the fallback when flatpak-spawn is not available.

    Args:
        flatpak_id: The Flatpak application ID
        args: Optional arguments to pass to the application
        env_overrides: Optional environment variable overrides
        cwd: Working directory for the command
        wait: Whether to wait for the process to exit

    Returns:
        CompletedProcess result
    """
    cmd = ["flatpak", "run"]

    if wait:
        cmd.append("--wait")

    cmd.append(flatpak_id)

    if args:
        cmd.extend(args)

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        cmd,
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def launch(
    flatpak_id: str,
    args: Optional[list[str]] = None,
    env_overrides: Optional[dict[str, str]] = None,
    cwd: Optional[str] = None,
    wait: bool = False,
    use_portal: bool = True,
) -> subprocess.CompletedProcess:
    """Launch a Flatpak application.

    Args:
        flatpak_id: The Flatpak application ID
        args: Optional arguments to pass to the application
        env_overrides: Optional environment variable overrides
        cwd: Working directory for the command
        wait: Whether to wait for the process to exit
        use_portal: Whether to prefer flatpak-spawn for portal support (default: True)

    Returns:
        CompletedProcess result
    """
    if use_portal and is_portal_launcher_available():
        return launch_with_portal(flatpak_id, args, env_overrides, cwd, wait)
    return launch_direct(flatpak_id, args, env_overrides, cwd, wait)


def get_launch_command(
    flatpak_id: str,
    args: Optional[list[str]] = None,
    use_portal: bool = True,
) -> list[str]:
    """Get the command that would be executed for launching.

    Useful for generating wrapper scripts.

    Args:
        flatpak_id: The Flatpak application ID
        args: Optional arguments
        use_portal: Whether to use flatpak-spawn

    Returns:
        Command as list of strings
    """
    if use_portal and is_portal_launcher_available():
        cmd = [FLATPAK_SPAWN_PATH, "--host", "flatpak", "run", flatpak_id]
    else:
        cmd = ["flatpak", "run", flatpak_id]

    if args:
        cmd.extend(args)

    return cmd
