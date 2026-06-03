#!/usr/bin/env python3
"""Pydantic validation models for fplaunchwrapper configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config_constants import HOOK_FAILURE_MODES

# Pydantic is optional. Provide shims when not available.
PYDANTIC_AVAILABLE = False
BaseModel: Any = object
Field: Any = Any
field_validator: Any = Any


def _create_field_shim() -> Any:
    """Create a minimal Field shim for non-pydantic environments."""

    class _RuntimeField:
        def __init__(self, *args, **kwargs):
            self.default = kwargs.get("default")
            self.default_factory = kwargs.get("default_factory")
            self.pattern = kwargs.get("pattern")
            self.ge = kwargs.get("ge")

        def __call__(self, *args, **kwargs):
            return _RuntimeField()

    return _RuntimeField()


def _create_field_validator_shim() -> Any:
    """Create a minimal field_validator shim for non-pydantic environments."""

    class _RuntimeFieldValidator:
        def __init__(self, *args, **kwargs):
            self.fields = args[0] if args else []

        def __call__(self, func):
            return func

    return _RuntimeFieldValidator()


# Try to import pydantic
try:
    from pydantic import Field as _Field
    from pydantic import BaseModel as _BaseModel
    from pydantic import field_validator as _field_validator

    BaseModel = _BaseModel
    Field = _Field
    field_validator = _field_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Pydantic not available - use shims
    Field = _create_field_shim()
    field_validator = _create_field_validator_shim()


if PYDANTIC_AVAILABLE:

    class PydanticAppPreferences(BaseModel):
        launch_method: str = Field(default="auto", pattern="^(auto|system|flatpak)$")
        env_vars: dict[str, str] = Field(default_factory=dict)
        pre_launch_script: str | None = None
        post_launch_script: str | None = None
        custom_args: list[str] = Field(default_factory=list)
        pre_launch_failure_mode: str | None = Field(default=None)
        post_launch_failure_mode: str | None = Field(default=None)

        @field_validator("pre_launch_failure_mode", "post_launch_failure_mode")
        @classmethod
        def validate_failure_mode(cls, v):
            """Validate hook failure mode values."""
            if v is not None and v not in HOOK_FAILURE_MODES:
                msg = f"Invalid failure mode '{v}'. Must be one of: {', '.join(HOOK_FAILURE_MODES)}"
                raise ValueError(msg)
            return v

        @field_validator("custom_args")
        @classmethod
        def validate_custom_args(cls, v):
            """Validate custom arguments for security."""
            if v:
                dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", '"', "'", "\\"]
                for arg in v:
                    if isinstance(arg, str):
                        if arg.startswith("--"):
                            if "=" in arg:
                                _, value = arg.split("=", 1)
                                for char in dangerous_chars:
                                    if char in value:
                                        msg = (
                                            f"Custom argument value contains "
                                            f"dangerous character '{char}': {arg}"
                                        )
                                        raise ValueError(msg)
                        else:
                            for char in dangerous_chars:
                                if char in arg:
                                    msg = (
                                        f"Custom argument contains "
                                        f"dangerous character '{char}': {arg}"
                                    )
                                    raise ValueError(msg)
            return v

        @field_validator("pre_launch_script", "post_launch_script")
        @classmethod
        def validate_script_path(cls, v):
            if v:
                substituted = v
                for var_name, var_value in [
                    ("HOME", str(Path.home())),
                    (
                        "XDG_CONFIG_HOME",
                        os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")),
                    ),
                    (
                        "XDG_DATA_HOME",
                        os.environ.get(
                            "XDG_DATA_HOME",
                            str(Path.home() / ".local" / "share"),
                        ),
                    ),
                ]:
                    substituted = substituted.replace(f"${{{var_name}}}", var_value)
                    substituted = substituted.replace(f"${var_name}", var_value)

                try:
                    if not Path(substituted).is_file():
                        msg = f"Script file does not exist: {v} (resolved: {substituted})"
                        raise ValueError(msg)
                except PermissionError as exc:
                    msg = f"Script file does not exist or is not accessible: {v}"
                    raise ValueError(msg) from exc

                script_path = Path(substituted).resolve()
                sensitive_dirs = [
                    Path("/etc"),
                    Path("/usr"),
                    Path("/bin"),
                    Path("/sbin"),
                    Path("/boot"),
                    Path("/sys"),
                    Path("/proc"),
                    Path("/dev"),
                    Path("/root"),
                ]
                for sensitive_dir in sensitive_dirs:
                    resolved_sensitive = sensitive_dir.resolve()
                    in_sensitive = False
                    try:
                        script_path.relative_to(resolved_sensitive)
                        in_sensitive = True
                    except (ValueError, PermissionError):
                        pass
                    if in_sensitive:
                        msg = f"Script path is in a sensitive system directory: {v}"
                        raise ValueError(msg)

                if not os.access(substituted, os.X_OK):
                    msg = f"Script file is not executable: {v} (resolved: {substituted})"
                    raise ValueError(msg)

            return v

    class PydanticWrapperConfig(BaseModel):
        bin_dir: str = Field(default="")
        config_dir: str = Field(default="")
        data_dir: str = Field(default="")
        blocklist: list[str] = Field(default_factory=list)
        global_preferences: PydanticAppPreferences = Field(
            default_factory=PydanticAppPreferences,
        )
        app_preferences: dict[str, PydanticAppPreferences] = Field(default_factory=dict)
        debug_mode: bool = Field(default=False)
        log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARN|ERROR)$")
        active_profile: str = Field(default="default")
        permission_presets: dict[str, list[str]] = Field(default_factory=dict)
        schema_version: int = Field(default=1, ge=0)
        cron_interval: int = Field(default=6, ge=1)
        enable_notifications: bool = Field(default=True)
        hook_failure_mode_default: str = Field(default="warn")
        pre_launch_failure_mode_default: str = Field(default="abort")
        post_launch_failure_mode_default: str = Field(default="warn")
        hook_failure_modes: dict[str, str] = Field(default_factory=dict)
        update_check_interval: int = Field(default=24, ge=1)
        allow_portal_fallback: bool = Field(default=True)
        prefer_portal: bool = Field(default=False)
        verify_launches: bool = Field(default=True)
        launch_timeout: int = Field(default=30, ge=1)
        notification_level: str = Field(
            default="info",
            pattern="^(debug|info|warning|error|none)$",
        )
        log_rotation_size: int = Field(default=10, ge=1)
        log_retention_days: int = Field(default=7, ge=1)
        wrapper_template: str = Field(default="")
        custom_env_prefix: str = Field(default="")
        enable_profiling: bool = Field(default=False)

        @field_validator("log_level")
        @classmethod
        def validate_log_level(cls, v):
            if v not in ("DEBUG", "INFO", "WARN", "ERROR"):
                msg = f"Invalid log level '{v}'. Must be one of: DEBUG, INFO, WARN, ERROR"
                raise ValueError(msg)
            return v

        @field_validator("cron_interval")
        @classmethod
        def validate_cron_interval(cls, v):
            if v < 1:
                msg = f"Invalid cron interval '{v}'. Must be at least 1 hour"
                raise ValueError(msg)
            return v
