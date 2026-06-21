#!/usr/bin/env python3
"""Portal-aware launcher for Flatpak applications.

Uses flatpak-spawn to launch applications with proper XDG portal integration,
providing better sandbox awareness and file picker integration.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Optional


# Reject flatpak_ids that could be interpreted as command-line flags by
# flatpak-spawn / flatpak. A real Flatpak ID always starts with a letter
# (reverse-DNS) and contains no whitespace, no leading hyphen, and no shell
# metacharacters. Without this guard, an attacker-controlled app_id could
# inject arbitrary flags (e.g. ``--help`` or ``--env=LD_PRELOAD=...``).
_FLATPAK_ID_SAFE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._+-]*$")


def _check_flatpak_id_safe(flatpak_id: str) -> None:
    """Raise ValueError if ``flatpak_id`` is unsafe to pass positionally."""
    if not isinstance(flatpak_id, str) or not flatpak_id:
        raise ValueError(f"flatpak_id must be a non-empty string, got {flatpak_id!r}")
    if not _FLATPAK_ID_SAFE_RE.match(flatpak_id):
        raise ValueError(
            f"Unsafe flatpak_id {flatpak_id!r}: must match {_FLATPAK_ID_SAFE_RE.pattern}"
        )


def _get_flatpak_spawn_path() -> Optional[str]:
    """Resolve flatpak-spawn path at call time (not import time)."""
    return shutil.which("flatpak-spawn")


def is_portal_launcher_available() -> bool:
    """Check if flatpak-spawn is available for portal-aware launching."""
    return _get_flatpak_spawn_path() is not None


def launch_with_portal(
    flatpak_id: str,
    args: Optional[list[str]] = None,
    env_overrides: Optional[dict[str, str]] = None,
    cwd: Optional[str] = None,
    wait: bool = False,
) -> subprocess.CompletedProcess[str]:
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
        ValueError: If flatpak_id is unsafe to pass positionally.
        FileNotFoundError: If flatpak-spawn is not available
    """
    _check_flatpak_id_safe(flatpak_id)
    spawn_path = _get_flatpak_spawn_path()
    if not spawn_path:
        raise FileNotFoundError(
            "flatpak-spawn not found. Install flatpak-tools or use direct flatpak run.",
        )

    cmd = [spawn_path, "--host", "flatpak", "run"]

    if wait:
        cmd.append("--wait")

    cmd.append(flatpak_id)
    cmd.append("--")

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
        check=False,
    )


def launch_direct(
    flatpak_id: str,
    args: Optional[list[str]] = None,
    env_overrides: Optional[dict[str, str]] = None,
    cwd: Optional[str] = None,
    wait: bool = False,
) -> subprocess.CompletedProcess[str]:
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

    Raises:
        ValueError: If flatpak_id is unsafe to pass positionally.
    """
    _check_flatpak_id_safe(flatpak_id)
    cmd = ["flatpak", "run"]

    if wait:
        cmd.append("--wait")

    cmd.append(flatpak_id)
    cmd.append("--")

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
        check=False,
    )


def launch(
    flatpak_id: str,
    args: Optional[list[str]] = None,
    env_overrides: Optional[dict[str, str]] = None,
    cwd: Optional[str] = None,
    wait: bool = False,
    use_portal: bool = True,
) -> subprocess.CompletedProcess[str]:
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

    Raises:
        ValueError: If flatpak_id is unsafe to pass positionally.
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

    Raises:
        ValueError: If flatpak_id is unsafe to pass positionally.
    """
    _check_flatpak_id_safe(flatpak_id)
    if use_portal and is_portal_launcher_available():
        spawn_path = _get_flatpak_spawn_path()
        if spawn_path:
            cmd = [spawn_path, "--host", "flatpak", "run", flatpak_id, "--"]
        else:
            cmd = ["flatpak", "run", flatpak_id, "--"]
    else:
        cmd = ["flatpak", "run", flatpak_id, "--"]

    if args:
        cmd.extend(args)

    return cmd
