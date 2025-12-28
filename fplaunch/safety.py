#!/usr/bin/env python3
"""Shim that re-exports the real safety module from lib/.

Keeping this file ensures ``from fplaunch.safety import ...`` works
consistently in tests and runtime.
"""

from lib.safety import *  # type: ignore  # re-export

__all__ = [
    "is_test_environment",
    "is_dangerous_wrapper",
    "safe_launch_check",
]