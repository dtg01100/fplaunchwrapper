#!/usr/bin/env python3
"""Enhanced configuration management for fplaunchwrapper
Provides type-safe configuration handling with platform-specific paths,
schema validation, migration, and templating.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from platformdirs import user_config_dir, user_data_dir
except ImportError:
    # Fallback implementation
    def user_config_dir(appname):
        return os.path.expanduser(f"~/.config/{appname}")

    def user_data_dir(appname):
        return os.path.expanduser(f"~/.local/share/{appname}")


try:
    from pydantic import BaseModel, Field, ValidationError, field_validator

    PYDANTIC_AVAILABLE = True
except Exception:
    # Pydantic is optional. Provide minimal shims so the module can still be
    # imported and basic fallback behavior is possible when Pydantic is absent.
    PYDANTIC_AVAILABLE = False

    class BaseModel:  # minimal placeholder for type-checking and imports
        def __init__(self, *args, **kwargs):  # no-op
            pass

    def Field(*args, **kwargs):  # compatibility stub
        return None

    def field_validator(*args, **kwargs):  # decorator stub
        def _decorator(fn):
            return fn

        return _decorator

    class ValidationError(Exception):
        """Placeholder ValidationError when pydantic is not installed."""

        pass


try:
    import tomli
    import tomli_w

    TOML_AVAILABLE = True
except Exception:
    # TOML support is optional. Ensure the names exist so static analysis
    # and runtime code that tests TOML_AVAILABLE can reference them safely.
    tomli = None
    tomli_w = None
    TOML_AVAILABLE = False


from .exceptions import (
    ConfigError,
    ConfigFileNotFoundError,
    ConfigMigrationError,
    ConfigParseError,
    ConfigPermissionError,
    ConfigValidationError,
    FplaunchError,
)


# Valid hook failure modes
HOOK_FAILURE_MODES = ("abort", "warn", "ignore")


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
        default_factory=dict
    )  # Custom permission presets
    schema_version: int = 1  # Schema version for migration purposes
    cron_interval: int = 6  # Cron interval in hours (default: 6 hours)
    enable_notifications: bool = (
        True  # Enable desktop notifications for update failures
    )
    # Global hook failure mode defaults
    hook_failure_mode_default: str = "warn"
    pre_launch_failure_mode_default: str | None = (
        None  # Overrides hook_failure_mode_default for pre-launch
    )
    post_launch_failure_mode_default: str | None = (
        None  # Overrides hook_failure_mode_default for post-launch
    )


class EnhancedConfigManager:
    """Enhanced configuration management with type safety, validation,
    migration, and templating support.
    """

    CURRENT_SCHEMA_VERSION = 1

    def __init__(self, app_name="fplaunchwrapper") -> None:
        self.app_name = app_name
        # Resolve config/data directories using XDG variables with Path.home fallback
        xdg_config_home = os.environ.get(
            "XDG_CONFIG_HOME", str(Path.home() / ".config")
        )
        xdg_data_home = os.environ.get(
            "XDG_DATA_HOME", str(Path.home() / ".local" / "share")
        )
        self.config_dir = Path(xdg_config_home) / app_name
        self.data_dir = Path(xdg_data_home) / app_name
        self.config_file = self.config_dir / "config.toml"
        self.config = WrapperConfig()
        self.config.schema_version = self.CURRENT_SCHEMA_VERSION

        # Template variables for substitution
        self.template_variables = {
            "HOME": str(Path.home()),
            "XDG_CONFIG_HOME": os.environ.get(
                "XDG_CONFIG_HOME", str(Path.home() / ".config")
            ),
            "XDG_DATA_HOME": os.environ.get(
                "XDG_DATA_HOME", str(Path.home() / ".local" / "share")
            ),
            "XDG_CACHE_HOME": os.environ.get(
                "XDG_CACHE_HOME", str(Path.home() / ".cache")
            ),
            "CONFIG_DIR": str(self.config_dir),
            "DATA_DIR": str(self.data_dir),
        }

        # Ensure directories exist (best-effort; ignore read-only errors)
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

        # Load configuration
        try:
            self.load_config()
        except ConfigPermissionError as e:
            print(f"Warning: {e}", file=sys.stderr)
            print("Falling back to default configuration", file=sys.stderr)
            self._create_default_config()
        except (ConfigParseError, ConfigValidationError, ConfigMigrationError) as e:
            print(f"Warning: {e}", file=sys.stderr)
            print("Falling back to default configuration", file=sys.stderr)
            self._create_default_config()
        except ConfigError as e:
            print(f"Warning: Unexpected configuration error: {e}", file=sys.stderr)
            print("Falling back to default configuration", file=sys.stderr)
            self._create_default_config()

    def _substitute_variables(self, value: str) -> str:
        """Substitute template variables in a string.

        Variables are in the format ${VARIABLE_NAME} or $VARIABLE_NAME.

        Args:
            value: String containing variables to substitute

        Returns:
            String with variables substituted
        """

        def replace_variable(match) -> str:
            var_name = match.group(1) or match.group(2) or ""
            replacement = self.template_variables.get(var_name, match.group(0))
            return str(replacement) if replacement is not None else match.group(0)

        # Handle ${VARIABLE} format
        value = re.sub(r"\$\{([A-Za-z0-9_]+)\}", replace_variable, value)
        # Handle $VARIABLE format
        value = re.sub(r"\$([A-Za-z0-9_]+)", replace_variable, value)
        return value

    def _process_config_value(self, value: Any) -> Any:
        """Process configuration value with variable substitution.

        Handles nested structures (lists, dictionaries) recursively.

        Args:
            value: Value to process

        Returns:
            Processed value with variables substituted
        """
        if isinstance(value, str):
            return self._substitute_variables(value)
        elif isinstance(value, list):
            return [self._process_config_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._process_config_value(v) for k, v in value.items()}
        return value

    def load_config(self) -> None:
        """Load configuration from TOML file with migration and validation."""
        if self.config_file.exists():
            try:
                if TOML_AVAILABLE:
                    with open(self.config_file, "rb") as f:
                        data = tomli.load(f)
                    # Migrate configuration if needed
                    data = self._migrate_config(data)
                    # Parse configuration with validation
                    self._parse_config_data(data)
                else:
                    self._load_fallback_config()
            except OSError as e:
                raise ConfigPermissionError(
                    f"Cannot read configuration file {self.config_file}: {e}"
                ) from e
            except (ValueError, KeyError) as e:
                raise ConfigParseError(
                    f"Invalid configuration format in {self.config_file}: {e}"
                ) from e
            except ValidationError as e:
                raise ConfigValidationError(
                    f"Configuration validation failed for {self.config_file}: {e}"
                ) from e
        else:
            # File doesn't exist - this is not an error, just create defaults
            self._create_default_config()

    def save_config(self) -> None:
        """Save configuration to TOML file."""
        try:
            if TOML_AVAILABLE:
                data = self._serialize_config()
                with open(self.config_file, "wb") as f:
                    tomli_w.dump(data, f)
            else:
                self._save_fallback_config()
        except OSError as e:
            raise ConfigPermissionError(
                f"Cannot write configuration file {self.config_file}: {e}"
            ) from e
        except (ValueError, TypeError) as e:
            raise ConfigParseError(f"Failed to serialize configuration: {e}") from e

    def _migrate_config(self, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate configuration from older versions to current schema.

        Args:
            data: Raw configuration data to migrate

        Returns:
            Migrated configuration data

        Raises:
            ConfigMigrationError: If migration fails
        """
        try:
            # Get current version from data or assume 0 if not specified
            version = data.get("schema_version", 0)

            # Migration from version 0 to 1
            if version < 1:
                # Example migration: Rename old fields, restructure data, etc.
                # For demonstration purposes, we'll handle potential legacy fields
                if "legacy_blocklist" in data:
                    data["blocklist"] = data.get("legacy_blocklist", [])
                    del data["legacy_blocklist"]

                # Ensure all required fields exist
                if "permission_presets" not in data:
                    data["permission_presets"] = {}

                if "active_profile" not in data:
                    data["active_profile"] = "default"

            # Update to current version
            data["schema_version"] = self.CURRENT_SCHEMA_VERSION
            return data
        except Exception as e:
            raise ConfigMigrationError(f"Failed to migrate configuration: {e}") from e

    def _parse_config_data(self, data: dict[str, Any]) -> None:
        """Parse configuration data with validation and variable substitution."""
        # Process all values with variable substitution
        processed_data = self._process_config_value(data)

        # Validate with Pydantic if available
        if PYDANTIC_AVAILABLE:
            try:
                # Validate using Pydantic model
                validated_config = PydanticWrapperConfig(**processed_data)
                self._apply_validated_config(validated_config)
            except ValidationError as e:
                raise ConfigValidationError(
                    f"Configuration validation failed: {e}"
                ) from e
        else:
            # Fallback validation without Pydantic
            self._apply_unvalidated_config(processed_data)

    def _apply_validated_config(
        self, validated_config: "PydanticWrapperConfig"
    ) -> None:
        """Apply validated configuration from Pydantic model."""
        self.config.bin_dir = validated_config.bin_dir
        self.config.debug_mode = validated_config.debug_mode
        self.config.log_level = validated_config.log_level
        self.config.blocklist = validated_config.blocklist
        self.config.schema_version = self.CURRENT_SCHEMA_VERSION
        self.config.cron_interval = validated_config.cron_interval
        self.config.enable_notifications = validated_config.enable_notifications

        # Apply hook failure mode defaults
        self.config.hook_failure_mode_default = (
            validated_config.hook_failure_mode_default
        )
        self.config.pre_launch_failure_mode_default = (
            validated_config.pre_launch_failure_mode_default
        )
        self.config.post_launch_failure_mode_default = (
            validated_config.post_launch_failure_mode_default
        )

        # Convert Pydantic models to dataclasses
        self.config.global_preferences = AppPreferences(
            launch_method=validated_config.global_preferences.launch_method,
            env_vars=dict(validated_config.global_preferences.env_vars),
            pre_launch_script=validated_config.global_preferences.pre_launch_script,
            post_launch_script=validated_config.global_preferences.post_launch_script,
            custom_args=list(validated_config.global_preferences.custom_args),
            pre_launch_failure_mode=validated_config.global_preferences.pre_launch_failure_mode,
            post_launch_failure_mode=validated_config.global_preferences.post_launch_failure_mode,
        )

        # Process app preferences
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

        # Permission presets
        self.config.permission_presets = validated_config.permission_presets

    def _apply_unvalidated_config(self, data: dict[str, Any]) -> None:
        """Apply configuration without Pydantic validation (fallback)."""
        # Basic configuration
        self.config.bin_dir = data.get("bin_dir", self.config.bin_dir)
        self.config.debug_mode = data.get("debug_mode", self.config.debug_mode)
        self.config.log_level = data.get("log_level", self.config.log_level)
        self.config.cron_interval = data.get("cron_interval", self.config.cron_interval)
        self.config.enable_notifications = data.get(
            "enable_notifications", self.config.enable_notifications
        )

        # Hook failure mode defaults
        self.config.hook_failure_mode_default = data.get(
            "hook_failure_mode_default", "warn"
        )
        self.config.pre_launch_failure_mode_default = data.get(
            "pre_launch_failure_mode_default"
        )
        self.config.post_launch_failure_mode_default = data.get(
            "post_launch_failure_mode_default"
        )

        # Blocklist
        if "blocklist" in data:
            self.config.blocklist = list(data["blocklist"])

        # Permission presets
        if "permission_presets" in data:
            presets_data = data["permission_presets"]
            if isinstance(presets_data, dict):
                for preset_name, preset_data in presets_data.items():
                    if isinstance(preset_data, dict) and "permissions" in preset_data:
                        self.config.permission_presets[preset_name] = list(
                            preset_data["permissions"]
                        )
                    elif isinstance(preset_data, list):
                        # Support direct list format
                        self.config.permission_presets[preset_name] = list(preset_data)

        # Global preferences
        if "global_preferences" in data:
            gp_data = data["global_preferences"]
            self.config.global_preferences = AppPreferences(
                launch_method=gp_data.get("launch_method", "auto"),
                env_vars=dict(gp_data.get("env_vars", {})),
                pre_launch_script=gp_data.get("pre_launch_script"),
                post_launch_script=gp_data.get("post_launch_script"),
                custom_args=list(gp_data.get("custom_args", [])),
                pre_launch_failure_mode=gp_data.get("pre_launch_failure_mode"),
                post_launch_failure_mode=gp_data.get("post_launch_failure_mode"),
            )

        # App-specific preferences
        if "app_preferences" in data:
            for app_id, pref_data in data["app_preferences"].items():
                self.config.app_preferences[app_id] = AppPreferences(
                    launch_method=pref_data.get("launch_method", "auto"),
                    env_vars=dict(pref_data.get("env_vars", {})),
                    pre_launch_script=pref_data.get("pre_launch_script"),
                    post_launch_script=pref_data.get("post_launch_script"),
                    custom_args=list(pref_data.get("custom_args", [])),
                    pre_launch_failure_mode=pref_data.get("pre_launch_failure_mode"),
                    post_launch_failure_mode=pref_data.get("post_launch_failure_mode"),
                )

    def _serialize_config(self) -> dict[str, Any]:
        """Serialize configuration to TOML-compatible format with schema version."""
        data = {
            "schema_version": self.CURRENT_SCHEMA_VERSION,
            "bin_dir": str(self.config.bin_dir),
            "debug_mode": self.config.debug_mode,
            "log_level": self.config.log_level,
            "blocklist": self.config.blocklist,
            "cron_interval": self.config.cron_interval,
            "enable_notifications": self.config.enable_notifications,
            # Global hook failure mode defaults
            "hook_failure_mode_default": self.config.hook_failure_mode_default,
        }

        # Add optional hook failure mode defaults if set
        if self.config.pre_launch_failure_mode_default:
            data["pre_launch_failure_mode_default"] = (
                self.config.pre_launch_failure_mode_default
            )
        if self.config.post_launch_failure_mode_default:
            data["post_launch_failure_mode_default"] = (
                self.config.post_launch_failure_mode_default
            )

        # Global preferences
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
        # Add hook failure modes to global preferences if set
        if gp.pre_launch_failure_mode:
            data["global_preferences"]["pre_launch_failure_mode"] = (
                gp.pre_launch_failure_mode
            )
        if gp.post_launch_failure_mode:
            data["global_preferences"]["post_launch_failure_mode"] = (
                gp.post_launch_failure_mode
            )

        # App preferences
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
                # Add hook failure modes to app preferences if set
                if prefs.pre_launch_failure_mode:
                    app_data["pre_launch_failure_mode"] = prefs.pre_launch_failure_mode
                if prefs.post_launch_failure_mode:
                    app_data["post_launch_failure_mode"] = (
                        prefs.post_launch_failure_mode
                    )
                data["app_preferences"][app_id] = app_data

        # Permission presets
        if self.config.permission_presets:
            data["permission_presets"] = dict(self.config.permission_presets)

        return data

    def _create_default_config(self) -> None:
        """Create default configuration."""
        self.config.bin_dir = os.path.expanduser("~/bin")
        self.config.config_dir = str(self.config_dir)
        self.config.data_dir = str(self.data_dir)
        self.config.debug_mode = False
        self.config.log_level = "INFO"
        self.config.blocklist = []

    # Additional API used by tests
    def reset_to_defaults(self) -> None:
        """Reset configuration values back to defaults."""
        self._create_default_config()
        # Also persist defaults
        self.save_config()

    def _load_fallback_config(self) -> None:
        """Fallback config loading for systems without TOML support.

        Uses a simple key=value format for basic configuration.
        Only supports flat key-value pairs; complex nested configs require TOML.
        """
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
                        self.config.enable_notifications = value.lower() in (
                            "true",
                            "1",
                            "yes",
                        )
                    elif key == "hook_failure_mode_default":
                        if value in HOOK_FAILURE_MODES:
                            self.config.hook_failure_mode_default = value
        except OSError:
            self._create_default_config()

    def _save_fallback_config(self) -> None:
        """Fallback config saving for systems without TOML support.

        Uses a simple key=value format for basic configuration.
        """
        try:
            lines = [
                f"# fplaunchwrapper configuration (fallback format)",
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
                f"Cannot write configuration file {self.config_file}: {e}"
            ) from e

    def get_app_preferences(self, app_id: str) -> AppPreferences:
        """Get preferences for a specific app, falling back to global."""
        return self.config.app_preferences.get(app_id, self.config.global_preferences)

    def set_app_preferences(self, app_id: str, prefs: AppPreferences) -> None:
        """Set preferences for a specific app."""
        self.config.app_preferences[app_id] = prefs
        try:
            self.save_config()
        except ConfigError as e:
            print(f"Warning: Failed to save app preferences: {e}", file=sys.stderr)

    def add_to_blocklist(self, app_id: str) -> None:
        """Add app to blocklist."""
        if app_id not in self.config.blocklist:
            self.config.blocklist.append(app_id)
            try:
                self.save_config()
            except ConfigError as e:
                print(f"Warning: Failed to save blocklist: {e}", file=sys.stderr)

    def remove_from_blocklist(self, app_id: str) -> None:
        """Remove app from blocklist."""
        if app_id in self.config.blocklist:
            self.config.blocklist.remove(app_id)
            try:
                self.save_config()
            except ConfigError as e:
                print(f"Warning: Failed to save blocklist: {e}", file=sys.stderr)

    def is_blocked(self, app_id: str) -> bool:
        """Check if app is blocked."""
        return app_id in self.config.blocklist

    def get_effective_hook_failure_mode(
        self, app_id: str, hook_type: str, runtime_override: str | None = None
    ) -> str:
        """Get the effective hook failure mode for an app.

        Resolves the failure mode using this precedence (highest to lowest):
        1. Runtime CLI override
        2. Environment variable (FPWRAPPER_HOOK_FAILURE)
        3. Per-app configuration
        4. Global default for hook type (pre_launch_failure_mode_default or post_launch_failure_mode_default)
        5. Global default (hook_failure_mode_default)
        6. Built-in default ("warn")

        Args:
            app_id: Application identifier
            hook_type: Either "pre" or "post"
            runtime_override: Runtime CLI override for failure mode

        Returns:
            Effective failure mode: "abort", "warn", or "ignore"
        """
        # 1. Runtime override (highest priority)
        if runtime_override and runtime_override in HOOK_FAILURE_MODES:
            return runtime_override

        # 2. Environment variable
        env_mode = os.environ.get("FPWRAPPER_HOOK_FAILURE")
        if env_mode and env_mode in HOOK_FAILURE_MODES:
            return env_mode

        # 3. Per-app configuration
        prefs = self.get_app_preferences(app_id)
        if hook_type == "pre" and prefs.pre_launch_failure_mode:
            return prefs.pre_launch_failure_mode
        if hook_type == "post" and prefs.post_launch_failure_mode:
            return prefs.post_launch_failure_mode

        # 4. Global default for hook type
        if hook_type == "pre" and self.config.pre_launch_failure_mode_default:
            return self.config.pre_launch_failure_mode_default
        if hook_type == "post" and self.config.post_launch_failure_mode_default:
            return self.config.post_launch_failure_mode_default

        # 5. Global default
        if self.config.hook_failure_mode_default:
            return self.config.hook_failure_mode_default

        # 6. Built-in default
        return "warn"

    BUILTIN_PRESETS = {
        "development": [
            "--filesystem=home",
            "--filesystem=host",
            "--device=dri",
            "--socket=x11",
            "--socket=wayland",
            "--share=ipc",
        ],
        "media": [
            "--device=dri",
            "--socket=pulseaudio",
            "--socket=wayland",
            "--socket=x11",
            "--share=ipc",
            "--filesystem=~/Music",
            "--filesystem=~/Videos",
        ],
        "network": [
            "--share=network",
            "--share=ipc",
            "--socket=x11",
            "--socket=wayland",
        ],
        "minimal": ["--share=ipc"],
        "gaming": [
            "--device=dri",
            "--device=input",
            "--socket=pulseaudio",
            "--socket=wayland",
            "--socket=x11",
            "--share=ipc",
            "--share=network",
            "--filesystem=~/Games",
        ],
        "offline": [
            "--device=dri",
            "--socket=pulseaudio",
            "--socket=wayland",
            "--socket=x11",
            "--share=ipc",
            "--filesystem=home",
        ],
    }

    def list_permission_presets(self) -> list[str]:
        """List available permission preset names."""
        presets = set(self.BUILTIN_PRESETS.keys())
        presets.update(self.config.permission_presets.keys())
        return sorted(presets)

    def get_permission_preset(self, preset_name: str) -> list[str] | None:
        """Get permissions for a specific preset.

        Args:
            preset_name: Name of the preset to retrieve

        Returns:
            List of permission strings, or None if preset not found
        """
        preset_lower = preset_name.lower()
        if preset_lower in self.BUILTIN_PRESETS:
            return self.BUILTIN_PRESETS[preset_lower]
        return self.config.permission_presets.get(preset_name)

    def add_permission_preset(self, preset_name: str, permissions: list[str]) -> None:
        """Add or update a permission preset.

        Args:
            preset_name: Name for the preset
            permissions: List of permission strings (e.g., ['--filesystem=home', '--device=dri'])
        """
        self.config.permission_presets[preset_name] = list(permissions)
        self.save_config()

    def remove_permission_preset(self, preset_name: str) -> bool:
        """Remove a permission preset.

        Args:
            preset_name: Name of the preset to remove

        Returns:
            True if preset was removed, False if it didn't exist
        """
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
        """Create a new configuration profile.

        Args:
            profile_name: Name of the new profile
            copy_from: Profile name to copy configuration from (optional)

        Returns:
            True if successful, False otherwise
        """
        if not profile_name or profile_name == "default":
            return False

        profiles_dir = self.config_dir / "profiles"
        try:
            profiles_dir.mkdir(parents=True, exist_ok=True)
            profile_file = profiles_dir / f"{profile_name}.toml"

            if profile_file.exists():
                return False

            if copy_from and copy_from != "default":
                # Copy from another profile
                source_file = profiles_dir / f"{copy_from}.toml"
                if source_file.exists():
                    profile_file.write_text(source_file.read_text())
                else:
                    # Source doesn't exist, create empty
                    profile_file.write_text("")
            else:
                # Create new profile with default content
                profile_file.write_text("")

            return True
        except OSError:
            return False

    def switch_profile(self, profile_name: str) -> bool:
        """Switch to a different configuration profile.

        Args:
            profile_name: Name of the profile to switch to

        Returns:
            True if successful, False otherwise
        """
        if profile_name not in self.list_profiles():
            return False

        self.config.active_profile = profile_name
        self.save_config()

        # Reload configuration from the new profile
        if profile_name != "default":
            profiles_dir = self.config_dir / "profiles"
            profile_file = profiles_dir / f"{profile_name}.toml"
            if profile_file.exists():
                try:
                    if TOML_AVAILABLE:
                        with open(profile_file, "rb") as f:
                            data = tomli.load(f)
                        self._parse_config_data(data)
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
        """Set the cron interval in hours.

        Args:
            interval: Cron interval in hours (must be at least 1 hour)
        """
        if interval < 1:
            raise ValueError("Cron interval must be at least 1 hour")
        self.config.cron_interval = interval
        self.save_config()

    def get_enable_notifications(self) -> bool:
        """Get whether desktop notifications are enabled."""
        return self.config.enable_notifications

    def set_enable_notifications(self, enabled: bool) -> None:
        """Set whether desktop notifications are enabled.

        Args:
            enabled: True to enable notifications, False to disable
        """
        self.config.enable_notifications = enabled
        self.save_config()

    def export_profile(self, profile_name: str, export_path: Path) -> bool:
        """Export a profile to a file.

        Args:
            profile_name: Name of the profile to export
            export_path: Path where to save the exported profile

        Returns:
            True if successful, False otherwise
        """
        try:
            if profile_name == "default":
                content = self._serialize_config()
            else:
                profiles_dir = self.config_dir / "profiles"
                profile_file = profiles_dir / f"{profile_name}.toml"
                if not profile_file.exists():
                    return False
                content = profile_file.read_text()

            if TOML_AVAILABLE and isinstance(content, dict):
                with open(export_path, "wb") as f:
                    tomli_w.dump(content, f)
            elif isinstance(content, dict):
                # TOML library not available - write a safe string representation
                # so write_text receives a string (avoids type errors and preserves data).
                export_path.write_text(str(content))
            else:
                export_path.write_text(content)

            return True
        except (OSError, ValueError):
            return False

    def import_profile(self, profile_name: str, import_path: Path) -> bool:
        """Import a profile from a file.

        Args:
            profile_name: Name for the imported profile
            import_path: Path to the file to import from

        Returns:
            True if successful, False otherwise
        """
        if not import_path.exists():
            return False

        try:
            profiles_dir = self.config_dir / "profiles"
            profiles_dir.mkdir(parents=True, exist_ok=True)

            if profile_name == "default":
                return False  # Can't overwrite default profile

            profile_file = profiles_dir / f"{profile_name}.toml"
            profile_file.write_text(import_path.read_text())
            return True
        except OSError:
            return False


# Pydantic models for enhanced validation (if available)
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
                for arg in v:
                    if isinstance(arg, str):
                        # Check for dangerous shell metacharacters that could be used for injection
                        dangerous_chars = [
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
                        ]
                        for char in dangerous_chars:
                            if char in arg and not arg.startswith(
                                "--"
                            ):  # Allow in flags like --filesystem
                                msg = f"Custom argument contains potentially dangerous character '{char}': {arg}"
                                raise ValueError(msg)
            return v

        @field_validator("pre_launch_script", "post_launch_script")
        @classmethod
        def validate_script_path(cls, v):
            if v:
                # Check if script file exists after template substitution
                if not os.path.isfile(v):
                    msg = f"Script file does not exist: {v}"
                    raise ValueError(msg)

                # Security check: ensure script path doesn't access sensitive locations
                script_path = Path(v).resolve()

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
                    try:
                        script_path.relative_to(sensitive_dir)
                        msg = f"Script path is in a sensitive system directory: {v}"
                        raise ValueError(msg)
                    except ValueError:
                        # Not in sensitive directory, continue checking
                        pass

                # Additional check: ensure script is executable
                if not os.access(v, os.X_OK):
                    msg = f"Script file is not executable: {v}"
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
            default=True
        )  # Enable desktop notifications for update failures
        # Global hook failure mode defaults
        hook_failure_mode_default: str = Field(default="warn")
        pre_launch_failure_mode_default: str | None = Field(default=None)
        post_launch_failure_mode_default: str | None = Field(default=None)

        @field_validator("hook_failure_mode_default")
        @classmethod
        def validate_hook_failure_mode_default(cls, v):
            """Validate hook failure mode values."""
            if v is not None and v not in HOOK_FAILURE_MODES:
                msg = f"Invalid failure mode '{v}'. Must be one of: {', '.join(HOOK_FAILURE_MODES)}"
                raise ValueError(msg)
            return v or "warn"  # Default to "warn" if empty

        @field_validator(
            "pre_launch_failure_mode_default", "post_launch_failure_mode_default"
        )
        @classmethod
        def validate_optional_failure_mode(cls, v):
            """Validate optional hook failure mode values."""
            if v is not None and v not in HOOK_FAILURE_MODES:
                msg = f"Invalid failure mode '{v}'. Must be one of: {', '.join(HOOK_FAILURE_MODES)}"
                raise ValueError(msg)
            return v

        class Config:
            """Configuration for Pydantic model."""

            extra = "forbid"  # Forbid extra fields to maintain schema integrity


def create_config_manager():
    """Factory function for configuration manager."""
    return EnhancedConfigManager()


def main() -> None:
    """Command-line interface for configuration management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage fplaunchwrapper configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fplaunch-config init                   # Initialize configuration
  fplaunch-config block firefox          # Block Firefox from being wrapped
  fplaunch-config unblock firefox        # Unblock Firefox
  fplaunch-config list-presets           # List permission presets
  fplaunch-config get-preset gaming      # Get permissions for 'gaming' preset

Commands:
  init          Initialize default configuration
  show          Show current configuration
  block APP     Block application from being wrapped
  unblock APP   Unblock application
  list-presets  List all permission presets
  get-preset NAME Get permissions for a specific preset
        """,
    )

    parser.add_argument(
        "command",
        choices=["init", "show", "block", "unblock", "list-presets", "get-preset"],
        help="Configuration command to execute",
    )

    parser.add_argument(
        "value",
        nargs="?",
        help="Value for the command (app name for block/unblock, preset name for get-preset)",
    )

    args = parser.parse_args()

    if args.command == "init":
        config = create_config_manager()
        config.save_config()
        print("Configuration initialized successfully")

    elif args.command == "show":
        config = create_config_manager()
        config.save_config()  # This will show the config

    elif args.command == "block":
        if not args.value:
            parser.error("block command requires an app name")
        config = create_config_manager()
        config.add_to_blocklist(args.value)
        print(f"Blocked {args.value}")

    elif args.command == "unblock":
        if not args.value:
            parser.error("unblock command requires an app name")
        config = create_config_manager()
        config.remove_from_blocklist(args.value)
        print(f"Unblocked {args.value}")

    elif args.command == "list-presets":
        config = create_config_manager()
        presets = config.list_permission_presets()
        if presets:
            print("Available permission presets:")
            for preset in presets:
                print(f"  {preset}")
        else:
            print("No permission presets defined")

    elif args.command == "get-preset":
        if not args.value:
            parser.error("get-preset command requires a preset name")
        config = create_config_manager()
        permissions = config.get_permission_preset(args.value)
        if permissions:
            print(f"Permissions for preset '{args.value}':")
            for perm in permissions:
                print(f"  {perm}")
        else:
            print(f"Preset '{args.value}' not found", file=sys.stderr)
            sys.exit(1)


# CLI interface for testing
if __name__ == "__main__":
    main()
