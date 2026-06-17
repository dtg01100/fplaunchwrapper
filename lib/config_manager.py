#!/usr/bin/env python3
"""Enhanced configuration management for fplaunchwrapper
Provides type-safe configuration handling with platform-specific paths,
schema validation, migration, and templating.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import cast
from typing import Any

from .config_constants import HOOK_FAILURE_MODES
from .config_manager_presets import BUILTIN_PRESETS

# Re-export the CLI entry-point from its dedicated module for backward
# compatibility with tests and external callers that import
# ``lib.config_manager.main``.  ``config_manager_cli`` does not import
# ``main()``), so this is not a real cyclic import.
from .config_manager_cli import main  # noqa: F401
from .config_models import AppPreferences, WrapperConfig
from .config_validation import (
    PYDANTIC_AVAILABLE,
    SecurityValidationError,
    _validate_custom_args_safety,
    _validate_failure_mode_safety,
    _validate_script_path_safety,
)

# Conditionally import PydanticAppPreferences when pydantic is available
try:
    # Re-exported for tests; pylint sees no internal use.
    from .config_validation import PydanticAppPreferences  # noqa: F401 pylint: disable=W0611
except ImportError:
    PydanticAppPreferences = None  # type: ignore[assignment, misc]
BaseModel: Any
Field: Any
ValidationError: Any
field_validator: Any

try:
    from pydantic import (
        BaseModel as _BaseModel,
        Field as _Field,
        ValidationError as _ValidationError,
        field_validator as _field_validator,
    )

    BaseModel, Field, ValidationError, field_validator = (
        _BaseModel,
        _Field,
        _ValidationError,
        _field_validator,
    )
except ImportError:

    class _RuntimeBaseModel:
        def __init__(self, *args, **kwargs):
            pass

    def _RuntimeField(*_args, **_kwargs):
        return None

    def _RuntimeFieldValidator(*_args, **_kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    class _RuntimeValidationError(Exception):
        pass

    BaseModel, Field, field_validator, ValidationError = (
        _RuntimeBaseModel,
        _RuntimeField,
        _RuntimeFieldValidator,
        _RuntimeValidationError,
    )

tomli: Any = None
tomli_w: Any = None
TOML_AVAILABLE: bool = False
try:
    import tomli as _tomli
    import tomli_w as _tomli_w

    tomli, tomli_w, TOML_AVAILABLE = _tomli, _tomli_w, True
except ImportError:
    TOML_AVAILABLE = False

from .exceptions import (  # noqa: E402
    ConfigError,
    ConfigMigrationError,
    ConfigParseError,
    ConfigPermissionError,
    ConfigValidationError,
)

from .paths import (  # noqa: E402
    get_default_config_dir,
    get_default_data_dir,
    ensure_dir,
)

try:
    from .config_validation import PydanticWrapperConfig
except ImportError:
    PydanticWrapperConfig = None  # type: ignore[assignment, misc]


class EnhancedConfigManager:
    """Enhanced configuration management with type safety, validation, migration, and templating support."""

    CURRENT_SCHEMA_VERSION = 1

    def __init__(
        self,
        app_name: str = "fplaunchwrapper",
        config_dir: str | Path | None = None,
    ) -> None:
        self.app_name = app_name
        self.config_dir = (
            Path(config_dir) if config_dir else get_default_config_dir(app_name)
        )
        self.data_dir = get_default_data_dir(app_name)
        self.config_file = self.config_dir / "config.toml"
        self.config = WrapperConfig()
        self.config.schema_version = self.CURRENT_SCHEMA_VERSION

        self.template_variables = {
            "HOME": str(Path.home()),
            "XDG_CONFIG_HOME": os.environ.get(
                "XDG_CONFIG_HOME",
                str(Path.home() / ".config"),
            ),
            "XDG_DATA_HOME": os.environ.get(
                "XDG_DATA_HOME",
                str(Path.home() / ".local" / "share"),
            ),
            "XDG_CACHE_HOME": os.environ.get(
                "XDG_CACHE_HOME",
                str(Path.home() / ".cache"),
            ),
            "CONFIG_DIR": str(self.config_dir),
            "DATA_DIR": str(self.data_dir),
        }

        try:
            ensure_dir(self.config_dir)
        except OSError as exc:
            logging.warning(
                "Could not create config directory %s: %s",
                self.config_dir,
                exc,
            )
        try:
            ensure_dir(self.data_dir)
        except OSError as exc:
            logging.warning(
                "Could not create data directory %s: %s",
                self.data_dir,
                exc,
            )

        try:
            self.load_config()
        except ConfigPermissionError as e:
            logging.warning(str(e))
            logging.warning("Falling back to default configuration")
            self._create_default_config()
        except (ConfigParseError, ConfigValidationError, ConfigMigrationError) as e:
            logging.warning(str(e))
            logging.warning("Falling back to default configuration")
            self._create_default_config()
        except ConfigError as e:
            logging.warning("Unexpected configuration error: %s", e)
            logging.warning("Falling back to default configuration")
            self._create_default_config()

    def _substitute_variables(self, value: str) -> str:
        r"""Substitute template variables in a string.

        Variables are in the format ${VARIABLE_NAME} or $VARIABLE_NAME.
        Escaped dollar signs (\$) are preserved as literal $.
        """
        escaped_placeholder = "\x00ESCAPED_DOLLAR\x00"
        value = value.replace("\\$", escaped_placeholder)

        def replace_variable(match) -> str:
            var_name = match.group(1) or match.group(2) or ""
            # `template_variables` is a `dict[str, str]` populated only
            # via `set_template_variable(name, str(value))`; the
            # `.get()` default is `match.group(0)` which is also str.
            # mypy still sees the value as Any, so we explicitly cast.
            return str(cast(Any, self.template_variables.get(var_name, match.group(0))))

        result = re.sub(r"\$([A-Za-z0-9_]+|\{[A-Za-z0-9_]+\})", replace_variable, value)
        return result.replace(escaped_placeholder, "$")

    def _process_config_value(self, value: Any) -> Any:
        """Process configuration value with variable substitution."""
        if isinstance(value, str):
            return self._substitute_variables(value)
        if isinstance(value, list):
            return [self._process_config_value(v) for v in value]
        if isinstance(value, dict):
            return {k: self._process_config_value(v) for k, v in value.items()}
        return value

    def load_config(self) -> None:
        """Load configuration from TOML file with migration and validation."""
        if self.config_file.exists():
            try:
                if TOML_AVAILABLE:
                    with Path(self.config_file).open("rb") as f:
                        data = tomli.load(f)
                    data = self._migrate_config(data)
                    self._parse_config_data(data)
                else:
                    self._load_fallback_config()
            except OSError as e:
                raise ConfigPermissionError(
                    f"Cannot read configuration file {self.config_file}: {e}",
                ) from e
            except (ValueError, KeyError) as e:
                raise ConfigParseError(
                    f"Invalid configuration format in {self.config_file}: {e}",
                ) from e
            except ValidationError as e:
                raise ConfigValidationError(
                    f"Configuration validation failed for {self.config_file}: {e}",
                ) from e
        else:
            self._create_default_config()

    def save_config(self) -> None:
        """Save configuration to TOML file."""
        try:
            ensure_dir(Path(self.config_file).parent)
            if TOML_AVAILABLE:
                data = self._serialize_config()
                with Path(self.config_file).open("wb") as f:
                    tomli_w.dump(data, f)
            else:
                self._save_fallback_config()
            Path(self.config_file).chmod(0o600)
        except OSError as e:
            raise ConfigPermissionError(
                f"Cannot write configuration file {self.config_file}: {e}",
            ) from e
        except (ValueError, TypeError) as e:
            raise ConfigParseError(f"Failed to serialize configuration: {e}") from e

    def _migrate_config(self, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate configuration from older versions to current schema."""
        try:
            version = data.get("schema_version", 0)
            if version < 1:
                if "legacy_blocklist" in data:
                    data["blocklist"] = data.get("legacy_blocklist", [])
                    del data["legacy_blocklist"]
                if "permission_presets" not in data:
                    data["permission_presets"] = {}
                if "active_profile" not in data:
                    data["active_profile"] = "default"
            data["schema_version"] = self.CURRENT_SCHEMA_VERSION
            return data
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ConfigMigrationError(f"Failed to migrate configuration: {e}") from e

    def _parse_config_data(self, data: dict[str, Any]) -> None:
        """Parse configuration data with validation and variable substitution.

        Two paths:
          - pydantic path (preferred): wraps everything in a Pydantic model
            which enforces field-level constraints (pattern, ge, etc.) and
            delegates field-validator functions to the same pure-Python
            helpers the unvalidated path uses.
          - unvalidated path: skips Pydantic field constraints, but calls
            the security-critical helpers directly. The security model is
            identical in both paths.
        """
        processed_data = self._process_config_value(data)

        if PYDANTIC_AVAILABLE and PydanticWrapperConfig is not None:
            try:
                validated_config = PydanticWrapperConfig(**processed_data)
                self._apply_validated_config(validated_config)
            except ValidationError as e:
                raise ConfigValidationError(
                    f"Configuration validation failed: {e}",
                ) from e
        else:
            try:
                self._apply_unvalidated_config(processed_data)
            except SecurityValidationError as e:
                # The pure-Python safety helpers raise
                # SecurityValidationError (a ValueError subclass) on
                # dangerous input. Surface as ConfigValidationError for
                # consistency with the pydantic path. Catching the
                # specific subclass (not bare ValueError) means an
                # unrelated ValueError from elsewhere in the unvalidated
                # path (e.g. a future int() parse error) propagates as a
                # real exception rather than being silently re-labeled as
                # a security validation failure.
                raise ConfigValidationError(
                    f"Configuration validation failed: {e}",
                ) from e

    def _apply_validated_config(self, validated_config: "PydanticWrapperConfig") -> None:
        """Apply validated configuration from Pydantic model."""
        self.config.bin_dir = validated_config.bin_dir
        self.config.config_dir = validated_config.config_dir
        self.config.data_dir = validated_config.data_dir
        self.config.active_profile = validated_config.active_profile
        self.config.debug_mode = validated_config.debug_mode
        self.config.log_level = validated_config.log_level
        self.config.blocklist = validated_config.blocklist
        self.config.schema_version = self.CURRENT_SCHEMA_VERSION
        self.config.cron_interval = validated_config.cron_interval
        self.config.enable_notifications = validated_config.enable_notifications
        self.config.hook_failure_mode_default = validated_config.hook_failure_mode_default
        self.config.pre_launch_failure_mode_default = (
            validated_config.pre_launch_failure_mode_default
        )
        self.config.post_launch_failure_mode_default = (
            validated_config.post_launch_failure_mode_default
        )

        self.config.global_preferences = AppPreferences(
            launch_method=validated_config.global_preferences.launch_method,
            env_vars=dict(validated_config.global_preferences.env_vars),
            pre_launch_script=validated_config.global_preferences.pre_launch_script,
            post_launch_script=validated_config.global_preferences.post_launch_script,
            custom_args=list(validated_config.global_preferences.custom_args),
            pre_launch_failure_mode=validated_config.global_preferences.pre_launch_failure_mode,
            post_launch_failure_mode=validated_config.global_preferences.post_launch_failure_mode,
        )

        self.config.app_preferences = {}
        for app_id, pref_model in validated_config.app_preferences.items():
            self.config.app_preferences[app_id] = AppPreferences(
                launch_method=pref_model.launch_method,
                env_vars=dict(pref_model.env_vars),
                pre_launch_script=pref_model.pre_launch_script,
                post_launch_script=pref_model.post_launch_script,
                custom_args=list(pref_model.custom_args),
                pre_launch_failure_mode=pref_model.pre_launch_failure_mode,
                post_launch_failure_mode=pref_model.post_launch_failure_mode,
            )

        self.config.permission_presets = validated_config.permission_presets

    def _apply_unvalidated_config(self, data: dict[str, Any]) -> None:
        """Apply configuration without Pydantic validation (fallback).

        Used when Pydantic is not installed (PYDANTIC_AVAILABLE is False).
        The Pydantic field-level constraints (log_level pattern, cron_interval
        range, etc.) are NOT enforced here — they are not security-critical.
        The security-critical checks (dangerous chars in custom args, script
        path safety, hook failure mode validity) ARE enforced via the same
        pure-Python helpers that the Pydantic validators call, so the
        security model is identical in both paths.
        """
        self.config.bin_dir = data.get("bin_dir", self.config.bin_dir)
        self.config.active_profile = data.get("active_profile", self.config.active_profile)
        self.config.debug_mode = data.get("debug_mode", self.config.debug_mode)
        self.config.log_level = data.get("log_level", self.config.log_level)
        self.config.cron_interval = data.get("cron_interval", self.config.cron_interval)
        self.config.enable_notifications = data.get(
            "enable_notifications", self.config.enable_notifications
        )
        self.config.hook_failure_mode_default = data.get("hook_failure_mode_default", "warn")
        self.config.pre_launch_failure_mode_default = data.get("pre_launch_failure_mode_default")
        self.config.post_launch_failure_mode_default = data.get("post_launch_failure_mode_default")

        if "blocklist" in data:
            blocklist_data = data["blocklist"]
            if isinstance(blocklist_data, list):
                self.config.blocklist = blocklist_data
            elif isinstance(blocklist_data, (tuple, set, frozenset)):
                self.config.blocklist = list(blocklist_data)
            else:
                self.config.blocklist = []

        if "permission_presets" in data:
            presets_data = data["permission_presets"]
            if isinstance(presets_data, dict):
                for preset_name, preset_data in presets_data.items():
                    if isinstance(preset_data, dict) and "permissions" in preset_data:
                        self.config.permission_presets[preset_name] = list(
                            preset_data["permissions"]
                        )
                    elif isinstance(preset_data, list):
                        self.config.permission_presets[preset_name] = list(preset_data)

        if "global_preferences" in data:
            gp_data = data["global_preferences"]
            # Security: run the same safety helpers the Pydantic validators
            # use. Raises ConfigValidationError on dangerous input.
            custom_args = list(gp_data.get("custom_args", []))
            _validate_custom_args_safety(custom_args)
            pre_launch_script = _validate_script_path_safety(
                gp_data.get("pre_launch_script")
            )
            post_launch_script = _validate_script_path_safety(
                gp_data.get("post_launch_script")
            )
            pre_launch_failure_mode = _validate_failure_mode_safety(
                gp_data.get("pre_launch_failure_mode")
            )
            post_launch_failure_mode = _validate_failure_mode_safety(
                gp_data.get("post_launch_failure_mode")
            )
            self.config.global_preferences = AppPreferences(
                launch_method=gp_data.get("launch_method", "auto"),
                env_vars=dict(gp_data.get("env_vars", {})),
                pre_launch_script=pre_launch_script,
                post_launch_script=post_launch_script,
                custom_args=custom_args,
                pre_launch_failure_mode=pre_launch_failure_mode,
                post_launch_failure_mode=post_launch_failure_mode,
            )

        if "app_preferences" in data:
            for app_id, pref_data in data["app_preferences"].items():
                custom_args = list(pref_data.get("custom_args", []))
                _validate_custom_args_safety(custom_args)
                pre_launch_script = _validate_script_path_safety(
                    pref_data.get("pre_launch_script")
                )
                post_launch_script = _validate_script_path_safety(
                    pref_data.get("post_launch_script")
                )
                pre_launch_failure_mode = _validate_failure_mode_safety(
                    pref_data.get("pre_launch_failure_mode")
                )
                post_launch_failure_mode = _validate_failure_mode_safety(
                    pref_data.get("post_launch_failure_mode")
                )
                self.config.app_preferences[app_id] = AppPreferences(
                    launch_method=pref_data.get("launch_method", "auto"),
                    env_vars=dict(pref_data.get("env_vars", {})),
                    pre_launch_script=pre_launch_script,
                    post_launch_script=post_launch_script,
                    custom_args=custom_args,
                    pre_launch_failure_mode=pre_launch_failure_mode,
                    post_launch_failure_mode=post_launch_failure_mode,
                )

    def _serialize_config(self) -> dict[str, Any]:
        """Serialize configuration to TOML-compatible format with schema version."""
        data: dict[str, Any] = {
            "schema_version": self.CURRENT_SCHEMA_VERSION,
            "bin_dir": str(self.config.bin_dir),
            "debug_mode": self.config.debug_mode,
            "log_level": self.config.log_level,
            "blocklist": self.config.blocklist,
            "cron_interval": self.config.cron_interval,
            "enable_notifications": self.config.enable_notifications,
            "hook_failure_mode_default": self.config.hook_failure_mode_default,
            "active_profile": self.config.active_profile,
        }

        if self.config.pre_launch_failure_mode_default:
            data["pre_launch_failure_mode_default"] = self.config.pre_launch_failure_mode_default
        if self.config.post_launch_failure_mode_default:
            data["post_launch_failure_mode_default"] = self.config.post_launch_failure_mode_default

        gp = self.config.global_preferences
        data["global_preferences"] = {
            "launch_method": gp.launch_method,
            "env_vars": dict(gp.env_vars),
            "custom_args": list(gp.custom_args),
        }
        if gp.pre_launch_script:
            data["global_preferences"]["pre_launch_script"] = gp.pre_launch_script
        if gp.post_launch_script:
            data["global_preferences"]["post_launch_script"] = gp.post_launch_script
        if gp.pre_launch_failure_mode:
            data["global_preferences"]["pre_launch_failure_mode"] = str(gp.pre_launch_failure_mode)
        if gp.post_launch_failure_mode:
            data["global_preferences"]["post_launch_failure_mode"] = str(
                gp.post_launch_failure_mode
            )

        if self.config.app_preferences:
            data["app_preferences"] = {}
            for app_id, prefs in self.config.app_preferences.items():
                app_data = {
                    "launch_method": prefs.launch_method,
                    "env_vars": dict(prefs.env_vars),
                    "custom_args": list(prefs.custom_args),
                }
                if prefs.pre_launch_script:
                    app_data["pre_launch_script"] = prefs.pre_launch_script
                if prefs.post_launch_script:
                    app_data["post_launch_script"] = prefs.post_launch_script
                if prefs.pre_launch_failure_mode:
                    app_data["pre_launch_failure_mode"] = str(prefs.pre_launch_failure_mode)
                if prefs.post_launch_failure_mode:
                    app_data["post_launch_failure_mode"] = str(prefs.post_launch_failure_mode)
                data["app_preferences"][app_id] = app_data

        if self.config.permission_presets:
            data["permission_presets"] = dict(self.config.permission_presets)

        return data

    def _create_default_config(self) -> None:
        """Create default configuration."""
        self.config.bin_dir = str(Path.home() / "bin")
        self.config.config_dir = str(self.config_dir)
        self.config.data_dir = str(self.data_dir)
        self.config.debug_mode = False
        self.config.log_level = "INFO"
        self.config.blocklist = []

    def reset_to_defaults(self) -> None:
        """Reset configuration values back to defaults."""
        self._create_default_config()
        self.save_config()

    def _load_fallback_config(self) -> None:
        """Fallback config loading for systems without TOML support."""
        if not self.config_file.exists():
            self._create_default_config()
            return

        try:
            content = self.config_file.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    if key == "bin_dir":
                        self.config.bin_dir = value
                    elif key == "debug_mode":
                        self.config.debug_mode = value.lower() in ("true", "1", "yes")
                    elif key == "log_level":
                        self.config.log_level = value.upper()
                    elif key == "cron_interval":
                        try:
                            self.config.cron_interval = int(value)
                        except ValueError:
                            pass
                    elif key == "enable_notifications":
                        self.config.enable_notifications = value.lower() in ("true", "1", "yes")
                    elif key == "hook_failure_mode_default":
                        if value in HOOK_FAILURE_MODES:
                            self.config.hook_failure_mode_default = value
        except OSError:
            self._create_default_config()

    def _save_fallback_config(self) -> None:
        """Fallback config saving for systems without TOML support."""
        try:
            lines = [
                "# fplaunchwrapper configuration (fallback format)",
                f"bin_dir={self.config.bin_dir}",
                f"debug_mode={self.config.debug_mode}",
                f"log_level={self.config.log_level}",
                f"cron_interval={self.config.cron_interval}",
                f"enable_notifications={self.config.enable_notifications}",
                f"hook_failure_mode_default={self.config.hook_failure_mode_default}",
            ]
            self.config_file.write_text("\n".join(lines) + "\n")
        except OSError as e:
            raise ConfigPermissionError(
                f"Cannot write configuration file {self.config_file}: {e}",
            ) from e

    def get_app_preferences(self, app_id: str) -> AppPreferences:
        """Get preferences for a specific app, falling back to global."""
        return self.config.app_preferences.get(app_id, self.config.global_preferences)

    def set_app_preferences(self, app_id: str, prefs: AppPreferences) -> None:
        """Set preferences for a specific app.

        Validates pre/post-launch script paths before persisting so a
        programmatic caller can't bypass the security checks that
        _parse_config_data runs on file-based config loads. Existing
        values that fail validation are rejected with
        ``SecurityValidationError``; ``None`` and missing paths are
        always allowed (they mean "no script").
        """
        # Defense in depth: re-run the same validator _parse_config_data
        # uses, so any caller of this public method gets the same
        # security guarantees as a file-based config load. _parse_config_data
        # already calls these helpers; this catches callers (CLI subcommands,
        # tests, third-party tools) that bypass the parser.
        if prefs.pre_launch_script is not None:
            _validate_script_path_safety(prefs.pre_launch_script)
        if prefs.post_launch_script is not None:
            _validate_script_path_safety(prefs.post_launch_script)
        # Failure-mode fields are also restricted to HOOK_FAILURE_MODES by
        # the validator; _parse_config_data enforces it, so we mirror that
        # here. None means "inherit from global default" and is allowed.
        if prefs.pre_launch_failure_mode is not None:
            _validate_failure_mode_safety(prefs.pre_launch_failure_mode)
        if prefs.post_launch_failure_mode is not None:
            _validate_failure_mode_safety(prefs.post_launch_failure_mode)
        # custom_args: same security rule as the parser.
        if prefs.custom_args:
            _validate_custom_args_safety(list(prefs.custom_args))

        self.config.app_preferences[app_id] = prefs
        try:
            self.save_config()
        except ConfigError as e:
            logging.warning("Failed to save app preferences: %s", e)

    def add_to_blocklist(self, app_id: str) -> None:
        """Add app to blocklist."""
        if app_id not in self.config.blocklist:
            self.config.blocklist.append(app_id)
            try:
                self.save_config()
            except ConfigError as e:
                logging.warning("Failed to save blocklist: %s", e)

    def remove_from_blocklist(self, app_id: str) -> None:
        """Remove app from blocklist."""
        if app_id in self.config.blocklist:
            self.config.blocklist.remove(app_id)
            try:
                self.save_config()
            except ConfigError as e:
                logging.warning("Failed to save blocklist: %s", e)

    def is_blocked(self, app_id: str) -> bool:
        """Check if app is blocked."""
        return app_id in self.config.blocklist

    def get_effective_hook_failure_mode(
        self,
        app_id: str,
        hook_type: str,
        runtime_override: str | None = None,
    ) -> str:
        """Get the effective hook failure mode for an app.

        Resolves the failure mode using this precedence (highest to lowest):
        1. Runtime CLI override
        2. Environment variable (FPWRAPPER_HOOK_FAILURE)
        3. Per-app configuration
        4. Global default for hook type (pre/post_launch_failure_mode_default)
        5. Global default (hook_failure_mode_default)
        6. Built-in default ("warn")
        """
        if runtime_override and runtime_override in HOOK_FAILURE_MODES:
            return runtime_override

        env_mode = os.environ.get("FPWRAPPER_HOOK_FAILURE")
        if env_mode and env_mode in HOOK_FAILURE_MODES:
            return env_mode

        prefs = self.get_app_preferences(app_id)
        if hook_type == "pre" and prefs.pre_launch_failure_mode:
            return prefs.pre_launch_failure_mode
        if hook_type == "post" and prefs.post_launch_failure_mode:
            return prefs.post_launch_failure_mode

        if hook_type == "pre" and self.config.pre_launch_failure_mode_default:
            return self.config.pre_launch_failure_mode_default
        if hook_type == "post" and self.config.post_launch_failure_mode_default:
            return self.config.post_launch_failure_mode_default

        if self.config.hook_failure_mode_default:
            return self.config.hook_failure_mode_default

        return "warn"

    BUILTIN_PRESETS = BUILTIN_PRESETS

    def list_permission_presets(self) -> list[str]:
        """List available permission preset names."""
        presets = set(self.BUILTIN_PRESETS.keys())
        presets.update(self.config.permission_presets.keys())
        return sorted(presets)

    def get_permission_preset(self, preset_name: str) -> list[str] | None:
        """Get permissions for a specific preset."""
        preset_lower = preset_name.lower()
        if preset_lower in self.BUILTIN_PRESETS:
            return self.BUILTIN_PRESETS[preset_lower]
        return self.config.permission_presets.get(preset_lower)

    def add_permission_preset(self, preset_name: str, permissions: list[str]) -> None:
        """Add or update a permission preset."""
        self.config.permission_presets[preset_name] = list(permissions)
        self.save_config()

    def remove_permission_preset(self, preset_name: str) -> bool:
        """Remove a permission preset."""
        if preset_name in self.config.permission_presets:
            del self.config.permission_presets[preset_name]
            self.save_config()
            return True
        return False

    def list_profiles(self) -> list[str]:
        """List available configuration profiles."""
        profiles_dir = self.config_dir / "profiles"
        if not profiles_dir.exists():
            return ["default"]

        profiles = ["default"]
        for profile_file in profiles_dir.glob("*.toml"):
            profile_name = profile_file.stem
            if profile_name not in profiles:
                profiles.append(profile_name)
        return sorted(profiles)

    def create_profile(self, profile_name: str, copy_from: str | None = None) -> bool:
        """Create a new configuration profile."""
        if not profile_name or profile_name == "default":
            return False

        profiles_dir = self.config_dir / "profiles"
        try:
            ensure_dir(profiles_dir)
            profile_file = profiles_dir / f"{profile_name}.toml"

            if profile_file.exists():
                return False

            if copy_from and copy_from != "default":
                source_file = profiles_dir / f"{copy_from}.toml"
                if source_file.exists():
                    profile_file.write_text(source_file.read_text())
                else:
                    profile_file.write_text("")
            else:
                profile_file.write_text("")

            return True
        except OSError:
            return False

    def switch_profile(self, profile_name: str) -> bool:
        """Switch to a different configuration profile."""
        if profile_name not in self.list_profiles():
            return False

        self.config.active_profile = profile_name
        self.save_config()

        if profile_name != "default":
            profiles_dir = self.config_dir / "profiles"
            profile_file = profiles_dir / f"{profile_name}.toml"
            if profile_file.exists():
                try:
                    if TOML_AVAILABLE:
                        with Path(profile_file).open("rb") as f:
                            data = tomli.load(f)
                        # Preserve active_profile: the profile's persisted
                        # data (e.g. from export_profile/import_profile) may
                        # contain an "active_profile" field with a different
                        # value, but the explicit set above is what we just
                        # asked for and must not be clobbered.
                        saved_active_profile = self.config.active_profile
                        self._parse_config_data(data)
                        self.config.active_profile = saved_active_profile
                    return True
                except (OSError, ValueError):
                    return False
        return True

    def get_active_profile(self) -> str:
        """Get the currently active profile name."""
        return self.config.active_profile

    def get_cron_interval(self) -> int:
        """Get the cron interval in hours."""
        return self.config.cron_interval

    def set_cron_interval(self, interval: int) -> None:
        """Set the cron interval in hours."""
        if interval < 1:
            raise ValueError("Cron interval must be at least 1 hour")
        self.config.cron_interval = interval
        self.save_config()

    def get_enable_notifications(self) -> bool:
        """Get whether desktop notifications are enabled."""
        return self.config.enable_notifications

    def set_enable_notifications(self, enabled: bool) -> None:
        """Set whether desktop notifications are enabled."""
        self.config.enable_notifications = enabled
        self.save_config()

    def export_profile(self, profile_name: str, export_path: Path) -> bool:
        """Export a profile to a file."""
        try:
            content: dict[str, Any] | str
            if profile_name == "default":
                content = self._serialize_config()
            else:
                profiles_dir = self.config_dir / "profiles"
                profile_file = profiles_dir / f"{profile_name}.toml"
                if not profile_file.exists():
                    return False
                profile_text = profile_file.read_text()
                if TOML_AVAILABLE:
                    try:
                        content = tomli.loads(profile_text)
                    except ValueError:
                        content = profile_text
                else:
                    content = profile_text

            if TOML_AVAILABLE and isinstance(content, dict):
                with Path(export_path).open("wb") as f:
                    tomli_w.dump(content, f)
            elif isinstance(content, dict):
                lines = ["# fplaunchwrapper profile export (fallback format)"]
                if "bin_dir" in content:
                    lines.append(f"bin_dir={content['bin_dir']}")
                if "debug_mode" in content:
                    lines.append(f"debug_mode={content['debug_mode']}")
                if "log_level" in content:
                    lines.append(f"log_level={content['log_level']}")
                if "cron_interval" in content:
                    lines.append(f"cron_interval={content['cron_interval']}")
                if "enable_notifications" in content:
                    lines.append(f"enable_notifications={content['enable_notifications']}")
                if "hook_failure_mode_default" in content:
                    lines.append(
                        f"hook_failure_mode_default={content['hook_failure_mode_default']}"
                    )
                export_path.write_text("\n".join(lines) + "\n")
            else:
                export_path.write_text(content)

            return True
        except (OSError, ValueError):
            return False

    def import_profile(self, profile_name: str, import_path: Path) -> bool:
        """Import a profile from a file."""
        if not import_path.exists():
            return False

        try:
            profiles_dir = self.config_dir / "profiles"
            ensure_dir(profiles_dir)

            if profile_name == "default":
                return False

            profile_file = profiles_dir / f"{profile_name}.toml"
            profile_file.write_text(import_path.read_text())
            return True
        except OSError:
            return False


def create_config_manager(config_dir: str | Path | None = None):
    """Factory function for configuration manager.

    Args:
        config_dir: Override the configuration directory. When provided,
            the manager reads and writes its config file there instead
            of the XDG default. Used by both the ``fplaunch`` Click CLI
            and the ``fplaunch-config`` argparse entry point to honour
            the ``--config-dir`` flag.
    """
    return EnhancedConfigManager(config_dir=config_dir)


__all__ = [
    "EnhancedConfigManager",
    "create_config_manager",
    "main",
    "BUILTIN_PRESETS",
]


if __name__ == "__main__":
    main()
