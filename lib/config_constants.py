#!/usr/bin/env python3
"""Configuration constants for fplaunchwrapper."""

from enum import Enum


class LaunchMethod(str, Enum):
    SYSTEM = "system"
    FLATPAK = "flatpak"
    AUTO = "auto"


class HookFailureMode(str, Enum):
    ABORT = "abort"
    WARN = "warn"
    IGNORE = "ignore"


# Valid hook failure modes
HOOK_FAILURE_MODES = tuple(HookFailureMode)
