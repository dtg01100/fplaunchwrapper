#!/usr/bin/env python3
"""Pydantic validation models for fplaunchwrapper configuration.

These models are only available when pydantic is installed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config_constants import HOOK_FAILURE_MODES

# Pydantic is optional. Use Any for all pydantic types to avoid static type conflicts.
# This allows the module to work whether pydantic is installed or not.
BaseModel: Any
Field: Any
field_validator: Any

try:
    from pydantic import Field as _Field
    from pydantic import field_validator as _field_validator

    Field = _Field
    field_validator = _field_validator
except ImportError:
    # Pydantic is optional. Provide minimal shims.
    class _RuntimeField:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            return _RuntimeField()

    class _RuntimeFieldValidator:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            return _RuntimeFieldValidator()

    Field = _RuntimeField
    field_validator = _RuntimeFieldValidator


# Check if pydantic is available at runtime
PYDANTIC_AVAILABLE: bool
try:
    from pydantic import BaseModel as _BaseModel

    BaseModel = _BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Minimal shim when pydantic is not available
    class BaseModel:
        pass

    PYDANTIC_AVAILABLE = False


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
                # Substitute template variables before checking existence
                # This handles paths like ${HOME}/scripts/pre-launch.sh
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

                # Check if script file exists after template substitution
                try:
                    if not Path(substituted).is_file():
                        msg = f"Script file does not exist: {v} (resolved: {substituted})"
                        raise ValueError(msg)
                except PermissionError as exc:
                    # Can't check file existence - treat as if it doesn't exist
                    msg = f"Script file does not exist or is not accessible: {v}"
                    raise ValueError(msg) from exc
                # Note: We resolve the path BEFORE the loop to catch symlinks that might
                # point outside sensitive directories (e.g., /bin -> /usr/bin)
                script_path = Path(substituted).resolve()
                # Define sensitive directories that scripts should not access
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
                # Check if script is in a sensitive directory
                for sensitive_dir in sensitive_dirs:
                    # Resolve both paths so that symlinked system directories
                    # (e.g. /root -> /var/roothome) are correctly matched.
                    resolved_sensitive = sensitive_dir.resolve()
                    in_sensitive = False
                    try:
                        script_path.relative_to(resolved_sensitive)
                        in_sensitive = True
                    except (ValueError, PermissionError):
                        # relative_to() raises ValueError when path is not under
                        # resolved_sensitive — that is the expected "not a match" case.
                        # PermissionError can occur when stat() fails on inaccessible dirs
                        # like /root when running as non-root user.
                        pass
                    if in_sensitive:
                        msg = f"Script path is in a sensitive system directory: {v}"
                        raise ValueError(msg)
                # Additional check: ensure script is executable
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
        cron_interval: int = Field(default=6, ge=1)  # Minimum 1 hour interval
        enable_notifications: bool = Field(
            default=True,
        )  # Enable desktop notifications for update failures
        # Global hook failure mode defaults
        hook_failure_mode_default: str = Field(default="warn")
        pre_launch_failure_mode_default: str | None = Field(default=None)
        post_launch_failure_mode_default: str | None = Field(default=None)

        model_config = {"extra": "forbid"}

        @field_validator("hook_failure_mode_default")
        @classmethod
        def validate_hook_failure_mode_default(cls, v):
            """Validate hook failure mode values."""
            if v is None or v == "":
                return "warn"
            if v not in HOOK_FAILURE_MODES:
                msg = f"Invalid failure mode '{v}'. Must be one of: {', '.join(HOOK_FAILURE_MODES)}"
                raise ValueError(msg)
            return v

        @field_validator(
            "pre_launch_failure_mode_default",
            "post_launch_failure_mode_default",
        )
        @classmethod
        def validate_optional_failure_mode(cls, v):
            """Validate optional hook failure mode values."""
            if v is not None and v not in HOOK_FAILURE_MODES:
                msg = f"Invalid failure mode '{v}'. Must be one of: {', '.join(HOOK_FAILURE_MODES)}"
                raise ValueError(msg)
            return v
