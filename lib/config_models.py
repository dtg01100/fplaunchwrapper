#!/usr/bin/env python3
"""Configuration models (dataclasses) for fplaunchwrapper."""

from dataclasses import dataclass, field

from .config_constants import HOOK_FAILURE_MODES, HookFailureMode, LaunchMethod


@dataclass
class AppPreferences:
    """Preferences for a specific Flatpak application."""

    launch_method: str = "auto"  # "auto", "system", "flatpak"
    env_vars: dict[str, str] = field(default_factory=dict)
    pre_launch_script: str | None = None
    post_launch_script: str | None = None
    custom_args: list[str] = field(default_factory=list)
    # Hook failure modes: "abort", "warn", "ignore", or None to inherit from global
    pre_launch_failure_mode: str | None = None
    post_launch_failure_mode: str | None = None


@dataclass
class WrapperConfig:
    """Main configuration for fplaunchwrapper."""

    bin_dir: str = ""
    config_dir: str = ""
    data_dir: str = ""
    blocklist: list[str] = field(default_factory=list)
    global_preferences: AppPreferences = field(default_factory=AppPreferences)
    app_preferences: dict[str, AppPreferences] = field(default_factory=dict)
    debug_mode: bool = False
    log_level: str = "INFO"
    active_profile: str = "default"  # Current active profile
    permission_presets: dict[str, list[str]] = field(
        default_factory=dict,
    )  # Custom permission presets
    schema_version: int = 1  # Schema version for migration purposes
    cron_interval: int = 6  # Cron interval in hours (default: 6 hours)
    enable_notifications: bool = True  # Enable desktop notifications for update failures
    # Global hook failure mode defaults
    hook_failure_mode_default: str = "warn"
    pre_launch_failure_mode_default: str | None = (
        None  # Overrides hook_failure_mode_default for pre-launch
    )
    post_launch_failure_mode_default: str | None = (
        None  # Overrides hook_failure_mode_default for post-launch
    )
