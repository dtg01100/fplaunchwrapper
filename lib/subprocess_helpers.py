#!/usr/bin/env python3
"""Subprocess helper functions for fplaunchwrapper."""

from __future__ import annotations

import subprocess
from typing import Any


def run_systemctl(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    """Run a systemctl command with common options."""
    return subprocess.run(
        ["systemctl", "--user"] + list(args),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_crontab(
    *args: str, input_text: str | None = None, timeout: int = 10
) -> subprocess.CompletedProcess[str]:
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
