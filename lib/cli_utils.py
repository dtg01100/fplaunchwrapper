#!/usr/bin/env python3
"""CLI utility functions for fplaunchwrapper."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()
console_err = Console(stderr=True)


def run_command(
    cmd: list[str],
    description: str = "",
    show_output: bool = True,
    emit_mode: bool = False,
) -> subprocess.CompletedProcess[str] | None:
    """Run a subprocess command, optionally showing a Rich status message.

    Returns None in emit mode to indicate no actual execution occurred.
    """
    if emit_mode:
        cmd_str = " ".join(cmd)
        console.print(f"[cyan]📋 EMIT:[/cyan] {cmd_str}")
        if description:
            console.print(f"[dim]   Purpose: {description}[/dim]")
        return None

    if description:
        with console.status(f"[bold green]{description}..."):
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=not show_output,
                text=True,
                timeout=30,
            )
    else:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=not show_output,
            text=True,
            timeout=30,
        )

    return result


def find_fplaunch_script(script_name: str) -> Optional[Path]:
    """Search common locations for a helper script (e.g., fplaunch-generate)."""
    candidates = [
        Path.cwd() / script_name,
        Path.home() / ".local" / "bin" / script_name,
        Path("/usr/local/bin") / script_name,
        Path("/usr/bin") / script_name,
    ]
    for p in candidates:
        if p.exists() and p.is_file() and os.access(p, os.X_OK):
            return p
    return None
