#!/usr/bin/env python3
"""
Enhanced configuration management for fplaunchwrapper
Provides type-safe configuration handling with platform-specific paths
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

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
except ImportError:
    PYDANTIC_AVAILABLE = False

try:
    import tomli
    import tomli_w

    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False


@dataclass
class AppPreferences:
    """Preferences for a specific Flatpak application"""

    launch_method: str = "auto"  # "auto", "system", "flatpak"
    env_vars: Dict[str, str] = field(default_factory=dict)
    pre_launch_script: Optional[str] = None
    post_launch_script: Optional[str] = None
    custom_args: List[str] = field(default_factory=list)


@dataclass
class WrapperConfig:
    """Main configuration for fplaunchwrapper"""

    bin_dir: str = ""
    config_dir: str = ""
    data_dir: str = ""
    blocklist: List[str] = field(default_factory=list)
    global_preferences: AppPreferences = field(default_factory=AppPreferences)
    app_preferences: Dict[str, AppPreferences] = field(default_factory=dict)
    debug_mode: bool = False
    log_level: str = "INFO"


class EnhancedConfigManager:
    """Enhanced configuration management with type safety and validation"""

    def __init__(self, app_name="fplaunchwrapper"):
        self.app_name = app_name
        self.config_dir = Path(user_config_dir(app_name))
        self.data_dir = Path(user_data_dir(app_name))
        self.config_file = self.config_dir / "config.toml"
        self.config = WrapperConfig()

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.load_config()

    def load_config(self):
        """Load configuration from TOML file"""
        if self.config_file.exists():
            try:
                if TOML_AVAILABLE:
                    with open(self.config_file, "rb") as f:
                        data = tomli.load(f)
                    self._parse_config_data(data)
                else:
                    self._load_fallback_config()
            except Exception as e:
                print(f"Warning: Failed to load config: {e}", file=sys.stderr)
                self._create_default_config()
        else:
            self._create_default_config()

    def save_config(self):
        """Save configuration to TOML file"""
        try:
            if TOML_AVAILABLE:
                data = self._serialize_config()
                with open(self.config_file, "wb") as f:
                    tomli_w.dump(data, f)
            else:
                self._save_fallback_config()
        except Exception as e:
            print(f"Warning: Failed to save config: {e}", file=sys.stderr)

    def _parse_config_data(self, data: Dict[str, Any]):
        """Parse configuration data with validation"""
        # Basic configuration
        self.config.bin_dir = data.get("bin_dir", self.config.bin_dir)
        self.config.debug_mode = data.get("debug_mode", self.config.debug_mode)
        self.config.log_level = data.get("log_level", self.config.log_level)

        # Blocklist
        if "blocklist" in data:
            self.config.blocklist = list(data["blocklist"])

        # Global preferences
        if "global_preferences" in data:
            gp_data = data["global_preferences"]
            self.config.global_preferences = AppPreferences(
                launch_method=gp_data.get("launch_method", "auto"),
                env_vars=dict(gp_data.get("env_vars", {})),
                pre_launch_script=gp_data.get("pre_launch_script"),
                post_launch_script=gp_data.get("post_launch_script"),
                custom_args=list(gp_data.get("custom_args", [])),
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
                )

    def _serialize_config(self) -> Dict[str, Any]:
        """Serialize configuration to TOML-compatible format"""
        data = {
            "bin_dir": str(self.config.bin_dir),
            "debug_mode": self.config.debug_mode,
            "log_level": self.config.log_level,
            "blocklist": self.config.blocklist,
        }

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
                data["app_preferences"][app_id] = app_data

        return data

    def _create_default_config(self):
        """Create default configuration"""
        self.config.bin_dir = os.path.expanduser("~/bin")
        self.config.config_dir = str(self.config_dir)
        self.config.data_dir = str(self.data_dir)

    def _load_fallback_config(self):
        """Fallback config loading for systems without TOML support"""
        # Implement fallback logic here
        pass

    def _save_fallback_config(self):
        """Fallback config saving for systems without TOML support"""
        # Implement fallback logic here
        pass

    def get_app_preferences(self, app_id: str) -> AppPreferences:
        """Get preferences for a specific app, falling back to global"""
        return self.config.app_preferences.get(app_id, self.config.global_preferences)

    def set_app_preferences(self, app_id: str, prefs: AppPreferences):
        """Set preferences for a specific app"""
        self.config.app_preferences[app_id] = prefs
        self.save_config()

    def add_to_blocklist(self, app_id: str):
        """Add app to blocklist"""
        if app_id not in self.config.blocklist:
            self.config.blocklist.append(app_id)
            self.save_config()

    def remove_from_blocklist(self, app_id: str):
        """Remove app from blocklist"""
        if app_id in self.config.blocklist:
            self.config.blocklist.remove(app_id)
            self.save_config()

    def is_blocked(self, app_id: str) -> bool:
        """Check if app is blocked"""
        return app_id in self.config.blocklist


# Pydantic models for enhanced validation (if available)
if PYDANTIC_AVAILABLE:

    class PydanticAppPreferences(BaseModel):
        launch_method: str = Field(default="auto", pattern="^(auto|system|flatpak)$")
        env_vars: Dict[str, str] = Field(default_factory=dict)
        pre_launch_script: Optional[str] = None
        post_launch_script: Optional[str] = None
        custom_args: List[str] = Field(default_factory=list)

        @field_validator("launch_method")
        @classmethod
        def validate_launch_method(cls, v):
            if v not in ["auto", "system", "flatpak"]:
                raise ValueError("launch_method must be auto, system, or flatpak")
            return v

        @field_validator("pre_launch_script", "post_launch_script")
        @classmethod
        def validate_script_path(cls, v):
            if v and not os.path.isfile(v):
                raise ValueError(f"Script file does not exist: {v}")
            return v

    class PydanticWrapperConfig(BaseModel):
        bin_dir: str = Field(default="")
        config_dir: str = Field(default="")
        data_dir: str = Field(default="")
        blocklist: List[str] = Field(default_factory=list)
        global_preferences: PydanticAppPreferences = Field(
            default_factory=PydanticAppPreferences
        )
        app_preferences: Dict[str, PydanticAppPreferences] = Field(default_factory=dict)
        debug_mode: bool = Field(default=False)
        log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARN|ERROR)$")


def create_config_manager():
    """Factory function for configuration manager"""
    return EnhancedConfigManager()


# CLI interface for testing
if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "init":
            # Initialize configuration
            config = create_config_manager()
            config.save_config()
            print("Configuration initialized")

        elif cmd == "show":
            # Show current configuration
            config = create_config_manager()
            print(f"Config dir: {config.config_dir}")
            print(f"Data dir: {config.data_dir}")
            print(f"Bin dir: {config.config.bin_dir}")
            print(f"Blocklist: {config.config.blocklist}")
            print(f"Debug mode: {config.config.debug_mode}")

        elif cmd == "block":
            if len(sys.argv) < 3:
                print("Usage: python config_manager.py block <app_id>")
                sys.exit(1)
            config = create_config_manager()
            config.add_to_blocklist(sys.argv[2])
            print(f"Blocked {sys.argv[2]}")

        elif cmd == "unblock":
            if len(sys.argv) < 3:
                print("Usage: python config_manager.py unblock <app_id>")
                sys.exit(1)
            config = create_config_manager()
            config.remove_from_blocklist(sys.argv[2])
            print(f"Unblocked {sys.argv[2]}")

        else:
            print("Unknown command. Available: init, show, block, unblock")
            sys.exit(1)
    else:
        print("Configuration manager CLI")
        print("Usage: python config_manager.py <command>")
        print("Commands: init, show, block <app_id>, unblock <app_id>")
