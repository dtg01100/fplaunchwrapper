#!/usr/bin/env python3
"""Pydantic validation models for fplaunchwrapper configuration.

Pydantic is the primary validator when available. The validation logic
is split into pure-Python helpers (`_validate_*_safety`) that the
Pydantic field validators call, and that the unvalidated path in
`config_manager._apply_unvalidated_config` also calls. This means the
security model is enforced identically in both paths — there is no
"degraded mode" where dangerous inputs slip through when Pydantic is
absent.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config_constants import HOOK_FAILURE_MODES


class SecurityValidationError(ValueError):
    """Raised by the pure-Python safety helpers in this module.

    Subclasses ValueError so that Pydantic field validators (which only
    catch ValueError and re-wrap as ValidationError) handle these the
    same way they handled the original inline validator bodies. The
    unvalidated path in `config_manager._parse_config_data` catches this
    specific class -- NOT bare ValueError -- so an unexpected ValueError
    from elsewhere in the unvalidated path (e.g. a future int() parse
    error) propagates as a real exception rather than being silently
    re-labeled as a security validation failure.
    """


# Constants used by both the Pydantic validators and the unvalidated
# fallback path. Pulled out of method bodies so a single change updates
# both enforcement sites.
DANGEROUS_CHARS = [
    ";",
    "&",
    "|",
    "`",
    "$",
    "(",
    ")",
    "<",
    ">",
    '"',
    "'",
    "\\",
    "\n",
    "\r",
    "\t",
    " ",
    "\0",
]
SENSITIVE_DIRS = [
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


def _validate_failure_mode_safety(v: str | None) -> str | None:
    """Reject hook failure-mode values that are not in HOOK_FAILURE_MODES.

    Pure function, no pydantic dependency. Called from both the
    Pydantic field validator and the unvalidated path in
    `config_manager._apply_unvalidated_config`.
    """
    if v is not None and v not in HOOK_FAILURE_MODES:
        msg = f"Invalid failure mode '{v}'. Must be one of: {', '.join(HOOK_FAILURE_MODES)}"
        raise SecurityValidationError(msg)
    return v


def _validate_custom_args_safety(v: list[str]) -> list[str]:
    """Reject any custom arg containing a shell-metacharacter.

    Both ``--key=value`` and bare ``--flag`` forms are checked. The
    dangerous char must appear in the value (after the ``=``) or in
    the whole arg (when no ``=``). Pure function; called from both
    the Pydantic validator and the unvalidated path.
    """
    if not v:
        return v
    for arg in v:
        if not isinstance(arg, str):
            continue
        value = arg.split("=", 1)[1] if "=" in arg else arg
        for char in DANGEROUS_CHARS:
            if char in value:
                msg = f"Custom argument contains dangerous character '{char}': {arg}"
                raise SecurityValidationError(msg)
    return v


def _validate_script_path_safety(v: str | None) -> str | None:
    """Reject pre/post-launch scripts that are missing, non-executable,
    or in a sensitive system directory.

    Pure function; called from both the Pydantic validator and the
    unvalidated path.
    """
    if not v:
        return v
    substituted = v
    for var_name, var_value in [
        ("HOME", str(Path.home())),
        (
            "XDG_CONFIG_HOME",
            os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")),
        ),
        (
            "XDG_DATA_HOME",
            os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")),
        ),
    ]:
        substituted = substituted.replace(f"${{{var_name}}}", var_value)
        substituted = substituted.replace(f"${var_name}", var_value)

    try:
        if not Path(substituted).is_file():
            msg = f"Script file does not exist: {v} (resolved: {substituted})"
            raise SecurityValidationError(msg)
    except PermissionError as exc:
        msg = f"Script file does not exist or is not accessible: {v}"
        raise SecurityValidationError(msg) from exc

    script_path = Path(substituted).resolve()
    for sensitive_dir in SENSITIVE_DIRS:
        try:
            resolved_sensitive = sensitive_dir.resolve()
        except (OSError, RuntimeError):
            # /proc, /sys, etc. can fail to resolve on some platforms;
            # skip them rather than crashing the validator.
            continue
        # relative_to raises ValueError when the path is NOT under
        # sensitive_dir (the common case). We want to continue the loop
        # in that case, so use a flag rather than try/except ValueError
        # (which would also swallow our own "in_sensitive" raise below).
        in_sensitive = False
        try:
            script_path.relative_to(resolved_sensitive)
            in_sensitive = True
        except ValueError:
            pass
        if in_sensitive:
            msg = f"Script path is in a sensitive system directory: {v}"
            raise SecurityValidationError(msg)

    if not os.access(substituted, os.X_OK):
        msg = f"Script file is not executable: {v} (resolved: {substituted})"
        raise SecurityValidationError(msg)

    return v


# Pydantic is optional. Provide shims when not available.
PYDANTIC_AVAILABLE = False
BaseModel: Any = object
Field: Any = Any
field_validator: Any = Any
ValidationError: Any = Any


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


try:
    from pydantic import Field as _Field
    from pydantic import BaseModel as _BaseModel
    from pydantic import field_validator as _field_validator
    from pydantic import ValidationError as _ValidationError

    BaseModel = _BaseModel
    Field = _Field
    field_validator = _field_validator
    ValidationError = _ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Pydantic not available - use shims
    Field = _create_field_shim()
    field_validator = _create_field_validator_shim()

    class _RuntimeValidationError(Exception):
        pass

    ValidationError = _RuntimeValidationError


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
            """Validate hook failure mode values.

            Delegates to the pure-Python helper so the unvalidated path
            enforces the same rule.
            """
            return _validate_failure_mode_safety(v)

        @field_validator("custom_args")
        @classmethod
        def validate_custom_args(cls, v):
            """Validate custom arguments for security.

            Delegates to the pure-Python helper so the unvalidated path
            enforces the same rule.
            """
            return _validate_custom_args_safety(v)

        @field_validator("pre_launch_script", "post_launch_script")
        @classmethod
        def validate_script_path(cls, v):
            """Validate pre/post-launch script paths.

            Delegates to the pure-Python helper so the unvalidated path
            enforces the same rule.
            """
            return _validate_script_path_safety(v)

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


__all__ = [
    "BaseModel",
    "DANGEROUS_CHARS",
    "Field",
    "PYDANTIC_AVAILABLE",
    "SENSITIVE_DIRS",
    "SecurityValidationError",
    "ValidationError",
    "_validate_custom_args_safety",
    "_validate_failure_mode_safety",
    "_validate_script_path_safety",
    "field_validator",
]
