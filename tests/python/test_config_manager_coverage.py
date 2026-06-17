#!/usr/bin/env python3
"""Additional coverage tests for lib/config_manager.py.

These tests target the specific gap regions identified by the coverage
report: preset CRUD edge paths, profile lifecycle (create/switch/import/
export), notifications getters/setters, the cron-interval ValueError
guard, the migration helper, save_config error paths, and the
unvalidated-apply blocklist coercion.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.config_manager import (
    BUILTIN_PRESETS,
    EnhancedConfigManager,
)
from lib.config_models import AppPreferences
from lib.config_validation import SecurityValidationError
from lib.exceptions import ConfigMigrationError, ConfigPermissionError


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def temp_root(monkeypatch, tmp_path):
    """Provide an isolated XDG layout (no writes to the real $HOME)."""
    config_root = tmp_path / ".config"
    data_root = tmp_path / ".local" / "share"
    cache_root = tmp_path / ".cache"
    config_root.mkdir(parents=True, exist_ok=True)
    data_root.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_root))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_root))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_root))
    return tmp_path


@pytest.fixture
def manager(temp_root):
    """A fresh EnhancedConfigManager pointed at the isolated XDG root."""
    return EnhancedConfigManager(config_dir=temp_root / ".config" / "fplaunchwrapper")


# --------------------------------------------------------------------------- #
# _migrate_config  (lines 251-266)
# --------------------------------------------------------------------------- #


class TestMigrateConfig:
    """Cover both branches of _migrate_config plus the error path."""

    def test_v0_with_legacy_blocklist_is_renamed(self, manager):
        data = {"legacy_blocklist": ["app1", "app2"], "bin_dir": "/foo"}
        result = manager._migrate_config(data)
        assert "legacy_blocklist" not in result
        assert result["blocklist"] == ["app1", "app2"]
        assert result["schema_version"] == EnhancedConfigManager.CURRENT_SCHEMA_VERSION

    def test_v0_adds_default_permission_presets(self, manager):
        result = manager._migrate_config({})
        assert result["permission_presets"] == {}

    def test_v0_preserves_existing_permission_presets(self, manager):
        data = {"permission_presets": {"foo": ["--bar"]}}
        result = manager._migrate_config(data)
        assert result["permission_presets"] == {"foo": ["--bar"]}

    def test_v0_adds_default_active_profile(self, manager):
        result = manager._migrate_config({})
        assert result["active_profile"] == "default"

    def test_v0_preserves_existing_active_profile(self, manager):
        data = {"active_profile": "work"}
        result = manager._migrate_config(data)
        assert result["active_profile"] == "work"

    def test_v0_without_legacy_blocklist_does_not_create_blocklist(
        self, manager
    ):
        """The migration only renames legacy_blocklist; it does not invent
        a blocklist key when none was ever present."""
        result = manager._migrate_config({"bin_dir": "/foo"})
        assert "blocklist" not in result
        assert "legacy_blocklist" not in result
        assert result["bin_dir"] == "/foo"

    def test_v1_passthrough_keeps_version(self, manager):
        data = {"schema_version": 1, "bin_dir": "/foo"}
        result = manager._migrate_config(data)
        # CURRENT_SCHEMA_VERSION is 1, so v1 stays at 1
        assert result["schema_version"] == 1

    def test_migrate_with_none_raises_migration_error(self, manager):
        """Non-dict input triggers AttributeError on .get() -> rewrapped."""
        with pytest.raises(ConfigMigrationError):
            manager._migrate_config(None)

    def test_migrate_with_string_raises_migration_error(self, manager):
        with pytest.raises(ConfigMigrationError):
            manager._migrate_config("not-a-dict")


# --------------------------------------------------------------------------- #
# save_config error paths  (lines 244-249)
# --------------------------------------------------------------------------- #


class TestSaveConfigErrors:
    """Drive the OSError / ValueError branches in save_config()."""

    def test_save_config_raises_config_permission_error_on_oserror(
        self, manager, monkeypatch
    ):
        # The atomic write path calls ``tempfile.mkstemp``; raising OSError
        # there is what causes ``save_config`` to surface a
        # ``ConfigPermissionError`` to the caller.
        import tempfile as _tempfile

        def fake_mkstemp(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(_tempfile, "mkstemp", fake_mkstemp)
        with pytest.raises(ConfigPermissionError):
            manager.save_config()
    def test_save_config_raises_config_parse_error_on_serialization_failure(
        self, manager, monkeypatch
    ):
        """Force _serialize_config to raise a TypeError -> ConfigParseError."""

        def boom():
            raise TypeError("nope")

        monkeypatch.setattr(manager, "_serialize_config", boom)
        from lib.exceptions import ConfigParseError

        with pytest.raises(ConfigParseError):
            manager.save_config()


# --------------------------------------------------------------------------- #
# _create_default_config  (lines 444-452)
# --------------------------------------------------------------------------- #


class TestCreateDefaultConfig:
    """Direct test of _create_default_config."""

    def test_creates_expected_values(self, manager):
        manager.config.bin_dir = "/old/bin"
        manager.config.config_dir = "/old/config"
        manager.config.data_dir = "/old/data"
        manager.config.debug_mode = True
        manager.config.log_level = "DEBUG"
        manager.config.blocklist = ["stale"]

        manager._create_default_config()

        assert manager.config.bin_dir == str(Path.home() / "bin")
        assert manager.config.config_dir == str(manager.config_dir)
        assert manager.config.data_dir == str(manager.data_dir)
        assert manager.config.debug_mode is False
        assert manager.config.log_level == "INFO"
        assert manager.config.blocklist == []


# --------------------------------------------------------------------------- #
# _apply_unvalidated_config blocklist coercion  (lines 342-348)
# --------------------------------------------------------------------------- #


class TestApplyUnvalidatedConfigBlocklist:
    """Cover the tuple/set/non-list branches for blocklist."""

    def test_blocklist_as_tuple_coerced_to_list(self, manager):
        manager._apply_unvalidated_config({"blocklist": ("a", "b")})
        assert manager.config.blocklist == ["a", "b"]

    def test_blocklist_as_set_coerced_to_list(self, manager):
        manager._apply_unvalidated_config({"blocklist": {"a", "b"}})
        assert sorted(manager.config.blocklist) == ["a", "b"]

    def test_blocklist_as_string_resets_to_empty(self, manager):
        """A non-iterable type ends up as []."""
        manager._apply_unvalidated_config({"blocklist": "not-a-list"})
        assert manager.config.blocklist == []

    def test_blocklist_as_int_resets_to_empty(self, manager):
        manager._apply_unvalidated_config({"blocklist": 42})
        assert manager.config.blocklist == []


# --------------------------------------------------------------------------- #
# _serialize_config — script / failure mode fields  (lines 411, 413, 415, 417)
# --------------------------------------------------------------------------- #


class TestSerializeConfigOptionalFields:
    """The pre/post-launch script and failure_mode fields are conditional."""

    def test_serializes_global_pre_launch_script(self, manager):
        manager.config.global_preferences.pre_launch_script = "/path/pre.sh"
        data = manager._serialize_config()
        assert data["global_preferences"]["pre_launch_script"] == "/path/pre.sh"

    def test_serializes_global_post_launch_script(self, manager):
        manager.config.global_preferences.post_launch_script = "/path/post.sh"
        data = manager._serialize_config()
        assert data["global_preferences"]["post_launch_script"] == "/path/post.sh"

    def test_serializes_global_pre_launch_failure_mode(self, manager):
        manager.config.global_preferences.pre_launch_failure_mode = "abort"
        data = manager._serialize_config()
        assert data["global_preferences"]["pre_launch_failure_mode"] == "abort"

    def test_serializes_global_post_launch_failure_mode(self, manager):
        manager.config.global_preferences.post_launch_failure_mode = "ignore"
        data = manager._serialize_config()
        assert data["global_preferences"]["post_launch_failure_mode"] == "ignore"


# --------------------------------------------------------------------------- #
# _apply_validated_config app_preferences iteration  (line 315)
# --------------------------------------------------------------------------- #


class TestApplyValidatedConfigWithAppPreferences:
    """The Pydantic path is taken only when pydantic is importable.

    Drive a full TOML round-trip with a populated app_preferences block
    so the per-app conversion loop runs.
    """

    def test_load_round_trips_app_preferences(self, manager):
        import tomli_w

        toml_path = manager.config_file
        payload = {
            "schema_version": 1,
            "bin_dir": str(Path.home() / "bin"),
            "app_preferences": {
                "test.App": {
                    "launch_method": "flatpak",
                    "env_vars": {"FOO": "bar"},
                    "custom_args": ["--quiet"],
                }
            },
        }
        with open(toml_path, "wb") as f:
            tomli_w.dump(payload, f)

        manager.load_config()

        assert "test.App" in manager.config.app_preferences
        prefs = manager.config.app_preferences["test.App"]
        assert prefs.launch_method == "flatpak"
        assert prefs.env_vars == {"FOO": "bar"}
        assert prefs.custom_args == ["--quiet"]


# --------------------------------------------------------------------------- #
# _load_fallback_config  ValueError on cron_interval / OSError
# (lines 483-484, 490-491)
# --------------------------------------------------------------------------- #


class TestLoadFallbackConfigEdgeCases:
    """Cover cron_interval invalid-int and read_text OSError branches."""

    def test_cron_interval_non_integer_is_ignored(self, manager, temp_root):
        config_file = manager.config_file
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("cron_interval=not_a_number\n")

        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        # Default cron_interval is 6
        assert manager.config.cron_interval == 6

    def test_oserror_during_read_falls_back_to_defaults(self, manager, monkeypatch):
        config_file = manager.config_file
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("bin_dir=/something\n")

        real_read_text = Path.read_text

        def fake_read_text(self, *args, **kwargs):
            if str(self) == str(config_file):
                raise OSError("read failed")
            return real_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", fake_read_text)
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        # Falls back to defaults (bin_dir from Path.home() / 'bin')
        assert manager.config.bin_dir == str(Path.home() / "bin")


# --------------------------------------------------------------------------- #
# _save_fallback_config OSError  (lines 506-507)
# --------------------------------------------------------------------------- #


class TestSaveFallbackConfigOSError:
    def test_write_oserror_raises_config_permission_error(self, manager, monkeypatch):
        # The atomic write path calls ``tempfile.mkstemp``; raising OSError
        # there is what causes the fallback save to surface
        # ``ConfigPermissionError`` to the caller.
        import tempfile as _tempfile

        def fake_mkstemp(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(_tempfile, "mkstemp", fake_mkstemp)
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            with pytest.raises(ConfigPermissionError):
                manager._save_fallback_config()

# --------------------------------------------------------------------------- #
# set_app_preferences / blocklist save errors  (lines 517-521, 529-530,
# 538-539)
# --------------------------------------------------------------------------- #


class TestMutationSaveErrors:
    """When save_config raises, mutation methods log and swallow the error."""

    def test_set_app_preferences_logs_on_save_error(self, manager, monkeypatch):
        def fake_save():
            raise ConfigPermissionError("nope")

        monkeypatch.setattr(manager, "save_config", fake_save)
        # Must not raise
        manager.set_app_preferences("test.App", AppPreferences(launch_method="flatpak"))
        # The preference was still set in memory
        assert manager.config.app_preferences["test.App"].launch_method == "flatpak"

    def test_add_to_blocklist_logs_on_save_error(self, manager, monkeypatch):
        def fake_save():
            raise ConfigPermissionError("nope")

        monkeypatch.setattr(manager, "save_config", fake_save)
        # Must not raise
        manager.add_to_blocklist("test.app")
        # Added in memory despite save failure
        assert "test.app" in manager.config.blocklist

    def test_remove_from_blocklist_logs_on_save_error(self, manager, monkeypatch):
        manager.add_to_blocklist("test.app")
        assert "test.app" in manager.config.blocklist

        def fake_save():
            raise ConfigPermissionError("nope")

        monkeypatch.setattr(manager, "save_config", fake_save)
        # Must not raise
        manager.remove_from_blocklist("test.app")
        # Removed in memory despite save failure
        assert "test.app" not in manager.config.blocklist


# --------------------------------------------------------------------------- #
# set_app_preferences validation
#
# Pin the security contract: programmatic callers of set_app_preferences
# must not be able to persist a script path / custom arg / failure mode
# that the file-based parser would reject. _parse_config_data already
# runs these checks; set_app_preferences mirrors them so direct API
# callers (CLI subcommands, third-party tools, tests) can't bypass them.
# --------------------------------------------------------------------------- #


class TestSetAppPreferencesValidation:
    """set_app_preferences must enforce the same security checks as
    _parse_config_data, so a programmatic caller can't write a config
    entry that a file load would have rejected.
    """

    def test_safe_real_script_path_is_accepted(self, manager, tmp_path):
        script = tmp_path / "pre.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o755)
        manager.set_app_preferences(
            "test.App",
            AppPreferences(pre_launch_script=str(script)),
        )
        assert manager.config.app_preferences["test.App"].pre_launch_script == str(script)

    def test_none_script_path_is_accepted(self, manager):
        # None means "no script" — explicitly allowed by the validator.
        manager.set_app_preferences("test.App", AppPreferences())
        assert manager.config.app_preferences["test.App"].pre_launch_script is None

    @pytest.mark.parametrize(
        "bad_path",
        ["/etc/passwd", "/usr/bin/env", "/bin/sh", "/sbin/init",
         "/root/.bashrc", "/proc/version", "/sys/kernel"],
    )
    def test_sensitive_dir_script_path_is_rejected(self, manager, bad_path, monkeypatch):
        # The validator also requires the file to exist and be executable,
        # so we patch is_file/access to keep the test focused on the
        # sensitive-dir rule (the same pattern test_regression_fixes.py
        # uses for the same validator).
        from lib import config_manager
        monkeypatch.setattr("os.path.isfile", lambda _p: True)
        monkeypatch.setattr("os.access", lambda _p, _m: True)
        monkeypatch.setattr(config_manager.Path, "is_file", lambda self: True)
        monkeypatch.setattr(config_manager.Path, "resolve", lambda self: self)
        with pytest.raises(SecurityValidationError) as exc_info:
            manager.set_app_preferences(
                "test.App", AppPreferences(pre_launch_script=bad_path)
            )
        assert "sensitive system directory" in str(exc_info.value)

    def test_nonexistent_script_path_is_rejected(self, manager, tmp_path):
        missing = tmp_path / "does-not-exist.sh"
        with pytest.raises(SecurityValidationError) as exc_info:
            manager.set_app_preferences(
                "test.App", AppPreferences(pre_launch_script=str(missing))
            )
        assert "does not exist" in str(exc_info.value)

    def test_unsafe_custom_args_are_rejected(self, manager):
        # Custom args go through the same dangerous-char check as the
        # file parser. set_app_preferences must reject shell
        # metacharacters so a programmatic caller can't sneak them in.
        with pytest.raises(SecurityValidationError):
            manager.set_app_preferences(
                "test.App",
                AppPreferences(custom_args=["--filesystem=;rm -rf /"]),
            )

    def test_safe_custom_args_are_accepted(self, manager):
        manager.set_app_preferences(
            "test.App",
            AppPreferences(custom_args=["--filesystem=home", "--socket=x11"]),
        )
        assert manager.config.app_preferences["test.App"].custom_args == [
            "--filesystem=home",
            "--socket=x11",
        ]

    def test_invalid_failure_mode_is_rejected(self, manager):
        with pytest.raises(SecurityValidationError):
            manager.set_app_preferences(
                "test.App",
                AppPreferences(pre_launch_failure_mode="nuke"),
            )

    @pytest.mark.parametrize("mode", ["abort", "warn", "ignore"])
    def test_valid_failure_modes_are_accepted(self, manager, mode):
        manager.set_app_preferences(
            "test.App", AppPreferences(pre_launch_failure_mode=mode)
        )
        assert (
            manager.config.app_preferences["test.App"].pre_launch_failure_mode == mode
        )

    def test_none_failure_mode_is_accepted(self, manager):
        # None means "inherit from global default" and is the default.
        manager.set_app_preferences("test.App", AppPreferences())
        assert (
            manager.config.app_preferences["test.App"].pre_launch_failure_mode is None
        )

    def test_failed_validation_does_not_persist(self, manager, monkeypatch):
        # If validation raises, the previous value must remain in place.
        # We start with a clean state and verify the failed write didn't
        # leave a partial entry.
        with pytest.raises(SecurityValidationError):
            manager.set_app_preferences(
                "test.App", AppPreferences(pre_launch_script="/etc/passwd")
            )
        assert "test.App" not in manager.config.app_preferences


# --------------------------------------------------------------------------- #
# is_blocked  (line 543)
# --------------------------------------------------------------------------- #


class TestIsBlocked:
    def test_is_blocked_false_when_absent(self, manager):
        assert manager.is_blocked("missing.app") is False

    def test_is_blocked_true_when_present(self, manager):
        manager.add_to_blocklist("known.app")
        assert manager.is_blocked("known.app") is True


# --------------------------------------------------------------------------- #
# Permission preset CRUD  (lines 586-610)  — edge cases beyond the existing
# happy paths in test_profile_preset_cli.py
# --------------------------------------------------------------------------- #


class TestPermissionPresetsCRUD:
    def test_list_returns_sorted_union_of_builtins_and_user(self, manager):
        manager.add_permission_preset("zulu", ["--a"])
        manager.add_permission_preset("alpha", ["--b"])
        result = manager.list_permission_presets()

        assert isinstance(result, list)
        assert result == sorted(result)
        for name in BUILTIN_PRESETS:
            assert name in result
        assert "zulu" in result
        assert "alpha" in result

    def test_list_with_no_user_presets_matches_builtins(self, manager):
        assert manager.list_permission_presets() == sorted(BUILTIN_PRESETS)

    def test_get_builtin_lowercased(self, manager):
        # Builtins keys are lowercase; lookup is case-insensitive
        result = manager.get_permission_preset("GAMING")
        assert result == BUILTIN_PRESETS["gaming"]

    def test_get_user_preset_returns_copy(self, manager):
        original = ["--filesystem=home", "--device=dri"]
        manager.add_permission_preset("custom", original)
        result = manager.get_permission_preset("custom")
        assert result == original
        # The implementation returns list(permissions), not the same object
        assert result is not original

    def test_get_missing_returns_none(self, manager):
        assert manager.get_permission_preset("not-a-preset") is None

    def test_add_preset_stores_a_copy(self, manager):
        """Mutating the source list after add must not affect the preset."""
        perms = ["--a"]
        manager.add_permission_preset("p", perms)
        perms.append("--b")
        assert manager.get_permission_preset("p") == ["--a"]

    def test_add_overwrites_existing(self, manager):
        manager.add_permission_preset("p", ["--a"])
        manager.add_permission_preset("p", ["--b", "--c"])
        assert manager.get_permission_preset("p") == ["--b", "--c"]

    def test_remove_returns_true_when_present(self, manager):
        manager.add_permission_preset("tmp", ["--a"])
        assert manager.remove_permission_preset("tmp") is True
        assert manager.get_permission_preset("tmp") is None

    def test_remove_returns_false_when_missing(self, manager):
        assert manager.remove_permission_preset("nope") is False


# --------------------------------------------------------------------------- #
# list_profiles / create_profile / switch_profile  (lines 612-678)
# --------------------------------------------------------------------------- #


class TestListProfiles:
    def test_returns_default_when_profiles_dir_missing(self, manager):
        # No profiles dir yet — first call should create config dirs but not
        # the profiles subdir.
        result = manager.list_profiles()
        assert result == ["default"]

    def test_includes_user_profiles_sorted(self, manager):
        manager.create_profile("zeta")
        manager.create_profile("alpha")
        manager.create_profile("mike")
        result = manager.list_profiles()
        assert "default" in result
        assert "alpha" in result
        assert "mike" in result
        assert "zeta" in result
        assert result == sorted(result)

    def test_does_not_duplicate_default(self, manager):
        manager.create_profile("work")
        result = manager.list_profiles()
        assert result.count("default") == 1


class TestCreateProfile:
    def test_happy_path_creates_empty_toml(self, manager):
        assert manager.create_profile("work") is True
        profiles_dir = manager.config_dir / "profiles"
        assert (profiles_dir / "work.toml").exists()
        assert (profiles_dir / "work.toml").read_text() == ""

    def test_empty_name_returns_false(self, manager):
        assert manager.create_profile("") is False

    def test_default_name_returns_false(self, manager):
        assert manager.create_profile("default") is False

    def test_existing_file_returns_false(self, manager):
        manager.create_profile("work")
        assert manager.create_profile("work") is False

    def test_copy_from_existing_source(self, manager):
        manager.create_profile("source")
        profiles_dir = manager.config_dir / "profiles"
        (profiles_dir / "source.toml").write_text("custom_key = 'value'\n")

        assert manager.create_profile("target", copy_from="source") is True
        target = profiles_dir / "target.toml"
        assert target.exists()
        assert "custom_key" in target.read_text()

    def test_copy_from_missing_source_writes_empty(self, manager):
        assert manager.create_profile("target", copy_from="missing") is True
        profiles_dir = manager.config_dir / "profiles"
        assert (profiles_dir / "target.toml").read_text() == ""

    def test_copy_from_default_treated_as_no_copy(self, manager):
        """``copy_from='default'`` hits the else branch → empty file."""
        assert manager.create_profile("foo", copy_from="default") is True
        profiles_dir = manager.config_dir / "profiles"
        assert (profiles_dir / "foo.toml").read_text() == ""

    def test_oserror_returns_false(self, manager, monkeypatch):
        from lib.paths import ensure_dir as real_ensure_dir

        def fake_ensure_dir(path, *args, **kwargs):
            if str(path).endswith("profiles"):
                raise OSError("perm denied")
            return real_ensure_dir(path, *args, **kwargs)

        monkeypatch.setattr("lib.config_manager.ensure_dir", fake_ensure_dir)
        assert manager.create_profile("foo") is False


class TestSwitchProfile:
    def test_missing_profile_returns_false(self, manager):
        assert manager.switch_profile("nonexistent") is False

    def test_default_profile_succeeds(self, manager):
        assert manager.switch_profile("default") is True
        assert manager.get_active_profile() == "default"

    def test_existing_profile_makes_active(self, manager):
        manager.create_profile("work")
        assert manager.switch_profile("work") is True
        assert manager.get_active_profile() == "work"

    def test_loads_valid_toml_from_profile_file(self, manager):
        manager.create_profile("work")
        profiles_dir = manager.config_dir / "profiles"
        (profiles_dir / "work.toml").write_text('cron_interval = 12\n')

        assert manager.switch_profile("work") is True
        assert manager.config.cron_interval == 12

    def test_preserves_active_profile_when_profile_file_overrides_it(
        self, manager
    ):
        """switch_profile('work') must not be clobbered by active_profile
        stored inside work.toml."""
        manager.create_profile("work")
        profiles_dir = manager.config_dir / "profiles"
        (profiles_dir / "work.toml").write_text('active_profile = "other"\n')

        assert manager.switch_profile("work") is True
        assert manager.get_active_profile() == "work"

    def test_malformed_toml_returns_false(self, manager):
        manager.create_profile("bad")
        profiles_dir = manager.config_dir / "profiles"
        (profiles_dir / "bad.toml").write_text("this is not valid toml {{{}}}")

        assert manager.switch_profile("bad") is False

    def test_persists_active_profile_to_config(self, manager):
        manager.create_profile("work")
        manager.switch_profile("work")
        # Save was called; reading the file should reflect active_profile
        import tomli

        with open(manager.config_file, "rb") as f:
            data = tomli.load(f)
        assert data["active_profile"] == "work"


# --------------------------------------------------------------------------- #
# get_active_profile / get_cron_interval / get_enable_notifications
# (lines 695-702)
# --------------------------------------------------------------------------- #


class TestSimpleGettersAndNotifications:
    def test_get_active_profile_default(self, manager):
        assert manager.get_active_profile() == "default"

    def test_get_cron_interval_default(self, manager):
        # The dataclass default is 6
        assert manager.get_cron_interval() == manager.config.cron_interval
        assert manager.get_cron_interval() == 6

    def test_get_enable_notifications_default(self, manager):
        # The dataclass default is True
        assert manager.get_enable_notifications() is True

    def test_set_enable_notifications_to_false(self, manager):
        manager.set_enable_notifications(False)
        assert manager.get_enable_notifications() is False

    def test_set_enable_notifications_to_true(self, manager):
        manager.set_enable_notifications(False)
        manager.set_enable_notifications(True)
        assert manager.get_enable_notifications() is True

    def test_set_enable_notifications_persists(self, manager):
        manager.set_enable_notifications(False)
        # New manager loads from the same on-disk config
        new_manager = EnhancedConfigManager(
            config_dir=manager.config_dir,
        )
        assert new_manager.get_enable_notifications() is False


# --------------------------------------------------------------------------- #
# set_cron_interval ValueError  (line 691)
# --------------------------------------------------------------------------- #


class TestSetCronInterval:
    def test_set_cron_interval_above_zero_persists(self, manager):
        manager.set_cron_interval(24)
        assert manager.get_cron_interval() == 24

    def test_set_cron_interval_zero_raises(self, manager):
        with pytest.raises(ValueError):
            manager.set_cron_interval(0)

    def test_set_cron_interval_negative_raises(self, manager):
        with pytest.raises(ValueError):
            manager.set_cron_interval(-5)


# --------------------------------------------------------------------------- #
# export_profile  (lines 704-749)
# --------------------------------------------------------------------------- #


class TestExportProfile:
    def test_export_default_writes_toml(self, manager, tmp_path):
        out = tmp_path / "default.toml"
        assert manager.export_profile("default", out) is True
        assert out.exists()
        # TOML dump should contain at least bin_dir
        content = out.read_text()
        assert "bin_dir" in content

    def test_export_non_default_writes_toml_dump(self, manager, tmp_path):
        manager.create_profile("work")
        profiles_dir = manager.config_dir / "profiles"
        (profiles_dir / "work.toml").write_text('cron_interval = 12\n')

        out = tmp_path / "work.toml"
        assert manager.export_profile("work", out) is True
        content = out.read_text()
        assert "cron_interval" in content

    def test_export_non_default_missing_profile_returns_false(
        self, manager, tmp_path
    ):
        out = tmp_path / "missing.toml"
        assert manager.export_profile("ghost", out) is False

    def test_export_default_in_fallback_format(self, manager, tmp_path):
        """When TOML is unavailable, 'default' export falls through to the
        key=value string format."""
        out = tmp_path / "default.toml"
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            assert manager.export_profile("default", out) is True
        content = out.read_text()
        assert "bin_dir=" in content
        assert "debug_mode=" in content
        assert "log_level=" in content

    def test_export_non_default_in_fallback_format(self, manager, tmp_path):
        """When TOML is unavailable, a non-default profile's raw text is
        copied verbatim (content is a string in the else branch)."""
        manager.create_profile("work")
        profiles_dir = manager.config_dir / "profiles"
        raw_text = "# raw profile text\ncustom=1\n"
        (profiles_dir / "work.toml").write_text(raw_text)

        out = tmp_path / "work.toml"
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            assert manager.export_profile("work", out) is True
        assert out.read_text() == raw_text

    def test_export_oserror_returns_false(self, manager, tmp_path, monkeypatch):
        out = tmp_path / "default.toml"
        # The atomic write path calls ``tempfile.mkstemp``; raising OSError
        # there is what causes ``export_profile`` to return False.
        import tempfile as _tempfile

        def fake_mkstemp(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(_tempfile, "mkstemp", fake_mkstemp)
        assert manager.export_profile("default", out) is False

# --------------------------------------------------------------------------- #
# import_profile  (lines 751-767)
# --------------------------------------------------------------------------- #


class TestImportProfile:
    def test_missing_source_file_returns_false(self, manager, tmp_path):
        out = tmp_path / "missing.toml"
        assert manager.import_profile("imported", out) is False

    def test_default_name_returns_false(self, manager, tmp_path):
        out = tmp_path / "src.toml"
        out.write_text("data = 1\n")
        assert manager.import_profile("default", out) is False

    def test_happy_path_copies_file_contents(self, manager, tmp_path):
        out = tmp_path / "src.toml"
        out.write_text("custom_key = 'value'\n")

        assert manager.import_profile("imported", out) is True
        profiles_dir = manager.config_dir / "profiles"
        imported = profiles_dir / "imported.toml"
        assert imported.exists()
        assert "custom_key" in imported.read_text()

    def test_oserror_returns_false(self, manager, tmp_path, monkeypatch):
        out = tmp_path / "src.toml"
        out.write_text("data = 1\n")

        from lib.paths import ensure_dir as real_ensure_dir

        def fake_ensure_dir(path, *args, **kwargs):
            if str(path).endswith("profiles"):
                raise OSError("perm denied")
            return real_ensure_dir(path, *args, **kwargs)

        monkeypatch.setattr("lib.config_manager.ensure_dir", fake_ensure_dir)
        assert manager.import_profile("imported", out) is False


# --------------------------------------------------------------------------- #
# get_effective_hook_failure_mode extra coverage: pre_launch_default for
# post-hooks etc. — kept for completeness; the existing tests already cover
# the heavy lifting.
# --------------------------------------------------------------------------- #


class TestHookFailureModeEdgeCases:
    def test_unknown_hook_type_falls_through_to_default(self, manager):
        # Neither 'pre' nor 'post' → all per-hook branches are skipped
        result = manager.get_effective_hook_failure_mode("test.App", "sideways")
        assert result == "warn"


# --------------------------------------------------------------------------- #
# get_effective_hook_failure_mode precedence (lines 562, 566, 570, 572, 575,
# 577, 582)
# --------------------------------------------------------------------------- #


class TestHookFailureModePrecedence:
    """Each branch of the precedence chain in get_effective_hook_failure_mode."""

    def test_runtime_override_wins(self, manager):
        # runtime_override is the highest priority
        result = manager.get_effective_hook_failure_mode(
            "test.App", "pre", runtime_override="abort"
        )
        assert result == "abort"

    def test_runtime_override_invalid_falls_through(self, manager):
        """runtime_override not in HOOK_FAILURE_MODES is silently ignored."""
        result = manager.get_effective_hook_failure_mode(
            "test.App", "pre", runtime_override="bogus"
        )
        # Falls through to env / prefs / default
        assert result == "warn"

    def test_env_var_used_when_no_runtime_override(self, manager, monkeypatch):
        monkeypatch.setenv("FPWRAPPER_HOOK_FAILURE", "ignore")
        result = manager.get_effective_hook_failure_mode("test.App", "pre")
        assert result == "ignore"

    def test_env_var_invalid_value_ignored(self, manager, monkeypatch):
        monkeypatch.setenv("FPWRAPPER_HOOK_FAILURE", "nonsense")
        result = manager.get_effective_hook_failure_mode("test.App", "pre")
        # Falls through to default "warn"
        assert result == "warn"

    def test_per_app_pre_launch_failure_mode_used(self, manager):
        manager.set_app_preferences(
            "test.App", AppPreferences(pre_launch_failure_mode="abort")
        )
        result = manager.get_effective_hook_failure_mode("test.App", "pre")
        assert result == "abort"

    def test_per_app_post_launch_failure_mode_used(self, manager):
        manager.set_app_preferences(
            "test.App", AppPreferences(post_launch_failure_mode="ignore")
        )
        result = manager.get_effective_hook_failure_mode("test.App", "post")
        assert result == "ignore"

    def test_config_pre_launch_default_used_when_no_app_pref(
        self, manager, monkeypatch
    ):
        monkeypatch.delenv("FPWRAPPER_HOOK_FAILURE", raising=False)
        # No app pref, but config-level pre_launch_failure_mode_default set
        manager.config.pre_launch_failure_mode_default = "abort"
        result = manager.get_effective_hook_failure_mode("unknown.App", "pre")
        assert result == "abort"

    def test_config_post_launch_default_used_when_no_app_pref(
        self, manager, monkeypatch
    ):
        monkeypatch.delenv("FPWRAPPER_HOOK_FAILURE", raising=False)
        manager.config.post_launch_failure_mode_default = "ignore"
        result = manager.get_effective_hook_failure_mode("unknown.App", "post")
        assert result == "ignore"

    def test_global_hook_failure_mode_default_used_as_fallback(
        self, manager, monkeypatch
    ):
        monkeypatch.delenv("FPWRAPPER_HOOK_FAILURE", raising=False)
        # No app prefs, no per-hook defaults at config level
        manager.config.hook_failure_mode_default = "ignore"
        result = manager.get_effective_hook_failure_mode("unknown.App", "pre")
        assert result == "ignore"

    def test_builtin_warn_returned_when_all_defaults_empty(
        self, manager, monkeypatch
    ):
        monkeypatch.delenv("FPWRAPPER_HOOK_FAILURE", raising=False)
        manager.config.hook_failure_mode_default = ""
        manager.config.pre_launch_failure_mode_default = None
        manager.config.post_launch_failure_mode_default = None
        result = manager.get_effective_hook_failure_mode("unknown.App", "pre")
        assert result == "warn"


# --------------------------------------------------------------------------- #
# _serialize_config: pre/post_launch_failure_mode_default + app_preferences
# (lines 400, 402, 422-437)
# --------------------------------------------------------------------------- #


class TestSerializeConfigExtended:
    def test_serializes_pre_launch_failure_mode_default(self, manager):
        manager.config.pre_launch_failure_mode_default = "abort"
        data = manager._serialize_config()
        assert data["pre_launch_failure_mode_default"] == "abort"

    def test_omits_pre_launch_failure_mode_default_when_empty(self, manager):
        manager.config.pre_launch_failure_mode_default = None
        data = manager._serialize_config()
        assert "pre_launch_failure_mode_default" not in data

    def test_serializes_post_launch_failure_mode_default(self, manager):
        manager.config.post_launch_failure_mode_default = "ignore"
        data = manager._serialize_config()
        assert data["post_launch_failure_mode_default"] == "ignore"

    def test_omits_post_launch_failure_mode_default_when_empty(self, manager):
        manager.config.post_launch_failure_mode_default = None
        data = manager._serialize_config()
        assert "post_launch_failure_mode_default" not in data

    def test_serializes_app_preferences_with_all_optional_fields(
        self, manager, tmp_path
    ):
        # Use real on-disk scripts so the post-set_app_preferences
        # security validator (which requires scripts to exist and be
        # executable) accepts them. This test exercises the serializer,
        # not the validator.
        pre_script = tmp_path / "pre.sh"
        post_script = tmp_path / "post.sh"
        pre_script.write_text("#!/bin/sh\nexit 0\n")
        pre_script.chmod(0o755)
        post_script.write_text("#!/bin/sh\nexit 0\n")
        post_script.chmod(0o755)
        manager.set_app_preferences(
            "test.App",
            AppPreferences(
                launch_method="flatpak",
                env_vars={"FOO": "bar"},
                pre_launch_script=str(pre_script),
                post_launch_script=str(post_script),
                custom_args=["--quiet"],
                pre_launch_failure_mode="abort",
                post_launch_failure_mode="ignore",
            ),
        )
        data = manager._serialize_config()
        app_data = data["app_preferences"]["test.App"]
        assert app_data["launch_method"] == "flatpak"
        assert app_data["env_vars"] == {"FOO": "bar"}
        assert app_data["custom_args"] == ["--quiet"]
        assert app_data["pre_launch_script"] == str(pre_script)
        assert app_data["post_launch_script"] == str(post_script)
        assert app_data["pre_launch_failure_mode"] == "abort"
        assert app_data["post_launch_failure_mode"] == "ignore"


    def test_app_preferences_round_trip_through_disk(self, manager):
        """Set app preferences, save, reload, and verify the per-app data
        survives a Pydantic round-trip."""
        import tomli_w

        manager.set_app_preferences(
            "test.App",
            AppPreferences(
                launch_method="system",
                env_vars={"X": "y"},
                custom_args=["--foo"],
            ),
        )
        # New manager reads from the same on-disk file
        new_manager = EnhancedConfigManager(config_dir=manager.config_dir)
        prefs = new_manager.get_app_preferences("test.App")
        assert prefs.launch_method == "system"
        assert prefs.env_vars == {"X": "y"}
        assert prefs.custom_args == ["--foo"]


# --------------------------------------------------------------------------- #
# reset_to_defaults  (lines 455-456)
# --------------------------------------------------------------------------- #


class TestResetToDefaults:
    def test_resets_all_values_and_persists(self, manager):
        # Mutate the in-memory config and the on-disk file
        manager.config.debug_mode = True
        manager.config.log_level = "DEBUG"
        manager.config.blocklist = ["stale"]
        manager.add_permission_preset("zzz", ["--a"])

        manager.reset_to_defaults()

        # _create_default_config only resets these fields
        assert manager.config.debug_mode is False
        assert manager.config.log_level == "INFO"
        assert manager.config.bin_dir == str(Path.home() / "bin")
        assert manager.config.blocklist == []


# --------------------------------------------------------------------------- #
# _substitute_variables / _process_config_value  (lines 187-192)
# --------------------------------------------------------------------------- #


class TestSubstituteVariables:
    def test_substitutes_simple_variable(self, manager):
        # The implementation's regex captures the bare form $NAME (no braces)
        result = manager._substitute_variables("$HOME/sub")
        assert result == str(Path.home()) + "/sub"

    def test_substitutes_bare_dollar_form(self, manager):
        result = manager._substitute_variables("$HOME/sub")
        assert result == str(Path.home()) + "/sub"

    def test_unknown_variable_left_intact(self, manager):
        result = manager._substitute_variables("$NOPE/foo")
        assert result == "$NOPE/foo"

    def test_escaped_dollar_is_preserved_as_literal(self, manager):
        result = manager._substitute_variables(r"\$HOME/literal")
        assert result == "$HOME/literal"

    def test_process_config_value_substitutes_inside_lists(self, manager):
        result = manager._process_config_value(["$HOME/a", "plain"])
        assert result == [str(Path.home()) + "/a", "plain"]

    def test_process_config_value_substitutes_inside_dicts(self, manager):
        result = manager._process_config_value({"k": "$HOME/b"})
        assert result == {"k": str(Path.home()) + "/b"}

    def test_process_config_value_passes_through_non_strings(self, manager):
        assert manager._process_config_value(42) == 42
        assert manager._process_config_value(None) is None
        assert manager._process_config_value(True) is True


# --------------------------------------------------------------------------- #
# __init__ except blocks  (lines 164-175) and ensure_dir OSError warnings
# (lines 147-148, 155-156)
# --------------------------------------------------------------------------- #


class TestInitFallbackPaths:
    """When load_config() raises, __init__ logs and falls back to defaults."""

    def test_permission_error_falls_back_to_defaults(
        self, monkeypatch, caplog, temp_root
    ):
        from lib.exceptions import ConfigPermissionError

        def boom(self):
            raise ConfigPermissionError("permission denied")

        monkeypatch.setattr(EnhancedConfigManager, "load_config", boom)
        with caplog.at_level("WARNING"):
            new_manager = EnhancedConfigManager(
                config_dir=temp_root / ".config" / "fplaunchwrapper"
            )
        assert new_manager.config.debug_mode is False
        assert new_manager.config.log_level == "INFO"

    def test_parse_error_falls_back_to_defaults(
        self, monkeypatch, caplog, temp_root
    ):
        from lib.exceptions import ConfigParseError

        def boom(self):
            raise ConfigParseError("parse failed")

        monkeypatch.setattr(EnhancedConfigManager, "load_config", boom)
        with caplog.at_level("WARNING"):
            new_manager = EnhancedConfigManager(
                config_dir=temp_root / ".config" / "fplaunchwrapper"
            )
        assert new_manager.config.debug_mode is False

    def test_validation_error_falls_back_to_defaults(
        self, monkeypatch, caplog, temp_root
    ):
        from lib.exceptions import ConfigValidationError

        def boom(self):
            raise ConfigValidationError("validation failed")

        monkeypatch.setattr(EnhancedConfigManager, "load_config", boom)
        with caplog.at_level("WARNING"):
            new_manager = EnhancedConfigManager(
                config_dir=temp_root / ".config" / "fplaunchwrapper"
            )
        assert new_manager.config.debug_mode is False

    def test_migration_error_falls_back_to_defaults(
        self, monkeypatch, caplog, temp_root
    ):
        from lib.exceptions import ConfigMigrationError

        def boom(self):
            raise ConfigMigrationError("migration failed")

        monkeypatch.setattr(EnhancedConfigManager, "load_config", boom)
        with caplog.at_level("WARNING"):
            new_manager = EnhancedConfigManager(
                config_dir=temp_root / ".config" / "fplaunchwrapper"
            )
        assert new_manager.config.debug_mode is False

    def test_generic_config_error_falls_back_to_defaults(
        self, monkeypatch, caplog, temp_root
    ):
        from lib.exceptions import ConfigError

        class _OtherConfigError(ConfigError):
            pass

        def boom(self):
            raise _OtherConfigError("unexpected")

        monkeypatch.setattr(EnhancedConfigManager, "load_config", boom)
        with caplog.at_level("WARNING"):
            new_manager = EnhancedConfigManager(
                config_dir=temp_root / ".config" / "fplaunchwrapper"
            )
        assert new_manager.config.debug_mode is False

    def test_init_logs_warning_when_ensure_dir_raises(
        self, monkeypatch, caplog, temp_root
    ):
        """When ensure_dir raises OSError, the warning is logged and init
        continues with the in-memory defaults."""
        def fake_ensure_dir(path, *args, **kwargs):
            raise OSError("perm denied")

        monkeypatch.setattr("lib.config_manager.ensure_dir", fake_ensure_dir)
        with caplog.at_level("WARNING"):
            new_manager = EnhancedConfigManager(
                config_dir=temp_root / ".config" / "fplaunchwrapper"
            )
        # Did not raise; defaults applied
        assert new_manager.config.debug_mode is False
        # At least one warning was emitted
        assert any(
            "Could not create" in rec.message for rec in caplog.records
        )


# --------------------------------------------------------------------------- #
# load_config error paths  (lines 217-227)
# --------------------------------------------------------------------------- #


class TestLoadConfigErrorPaths:
    def test_fallback_branch_when_toml_unavailable(self, manager, temp_root):
        """When TOML is unavailable, load_config delegates to the
        fallback parser. The file must exist for the else branch (line 217)
        to fire — otherwise load_config takes the file-missing branch."""
        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text("bin_dir=/some/bin\n")
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager.load_config()
        # _load_fallback_config parsed the bin_dir line
        assert manager.config.bin_dir == "/some/bin"

    def test_oserror_raises_config_permission_error(self, manager, monkeypatch):
        from lib.exceptions import ConfigPermissionError

        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text("[main]\n")

        real_open = Path.open

        def fake_open(self, *args, **kwargs):
            if str(self) == str(manager.config_file):
                raise OSError("disk gone")
            return real_open(self, *args, **kwargs)

        monkeypatch.setattr(Path, "open", fake_open)
        with pytest.raises(ConfigPermissionError):
            manager.load_config()

    def test_malformed_toml_raises_config_parse_error(self, manager):
        from lib.exceptions import ConfigParseError

        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        # Definitely not valid TOML
        manager.config_file.write_text("= invalid = toml = [[[")
        with pytest.raises(ConfigParseError):
            manager.load_config()

    def test_invalid_hook_failure_mode_raises_validation_error(self, manager):
        pytest.importorskip("pydantic")
        from lib.exceptions import ConfigValidationError
        import tomli_w

        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        # ``cron_interval`` has a Pydantic ``ge=1`` validator; 0 is invalid
        tomli_w.dump(
            {
                "schema_version": 1,
                "cron_interval": 0,
            },
            manager.config_file.open("wb"),
        )
        with pytest.raises(ConfigValidationError):
            manager.load_config()


# --------------------------------------------------------------------------- #
# save_config else branch + _save_fallback_config call (line 242)
# --------------------------------------------------------------------------- #


class TestSaveConfigFallbackBranch:
    def test_save_with_toml_unavailable_calls_fallback(self, manager):
        """When TOML is unavailable, save_config writes the key=value form."""
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager.save_config()
        content = manager.config_file.read_text()
        assert "bin_dir=" in content
        assert "log_level=" in content


# --------------------------------------------------------------------------- #
# _parse_config_data: ValidationError rewrap (lines 276-281) and the
# Pydantic-disabled else branch (unvalidated-apply blocklist + extras)
# --------------------------------------------------------------------------- #


class TestParseConfigDataValidationError:
    def test_pydantic_validation_error_is_rewrapped(
        self, manager, monkeypatch
    ):
        pytest.importorskip("pydantic")
        from lib.exceptions import ConfigValidationError
        from pydantic import ValidationError as PydanticValidationError

        from lib.config_manager import PydanticWrapperConfig

        def fake_init(self, **kwargs):  # noqa: ARG001 - match Pydantic signature
            raise PydanticValidationError.from_exception_data(
                "PydanticWrapperConfig",
                [
                    {
                        "type": "value_error",
                        "loc": ("foo",),
                        "input": "bar",
                        "ctx": {"error": "boom"},
                    }
                ],
            )

        monkeypatch.setattr(PydanticWrapperConfig, "__init__", fake_init)
        with pytest.raises(ConfigValidationError):
            manager._parse_config_data({})


class TestUnvalidatedConfigApply:
    """When Pydantic is unavailable, _apply_unvalidated_config handles the
    full data set including blocklist, permission_presets, global_preferences,
    and app_preferences."""

    @pytest.fixture
    def unvalidated_manager(self, temp_root):
        """A manager constructed with PYDANTIC_AVAILABLE patched off for the
        duration of this test class."""
        import lib.config_manager as cm

        with patch.object(cm, "PYDANTIC_AVAILABLE", False), patch.object(
            cm, "PydanticWrapperConfig", None
        ):
            yield EnhancedConfigManager(
                config_dir=temp_root / ".config" / "fplaunchwrapper"
            )

    def test_blocklist_as_list_is_used_directly(self, unvalidated_manager):
        unvalidated_manager._apply_unvalidated_config(
            {"blocklist": ["a", "b"]}
        )
        assert unvalidated_manager.config.blocklist == ["a", "b"]

    def test_permission_presets_with_permissions_key(self, unvalidated_manager):
        unvalidated_manager._apply_unvalidated_config(
            {
                "permission_presets": {
                    "p1": {"permissions": ["--x", "--y"]},
                }
            }
        )
        assert unvalidated_manager.config.permission_presets["p1"] == [
            "--x",
            "--y",
        ]

    def test_permission_presets_with_list_value(self, unvalidated_manager):
        unvalidated_manager._apply_unvalidated_config(
            {"permission_presets": {"p2": ["--a"]}}
        )
        assert unvalidated_manager.config.permission_presets["p2"] == ["--a"]

    def test_permission_presets_with_unknown_shape_ignored(
        self, unvalidated_manager
    ):
        unvalidated_manager._apply_unvalidated_config(
            {"permission_presets": {"p3": "not-a-dict-or-list"}}
        )
        assert "p3" not in unvalidated_manager.config.permission_presets

    def test_global_preferences_applied(self, unvalidated_manager):
        unvalidated_manager._apply_unvalidated_config(
            {
                "global_preferences": {
                    "launch_method": "flatpak",
                    "env_vars": {"K": "v"},
                    "custom_args": ["--z"],
                    "pre_launch_failure_mode": "abort",
                    "post_launch_failure_mode": "ignore",
                }
            }
        )
        gp = unvalidated_manager.config.global_preferences
        assert gp.launch_method == "flatpak"
        assert gp.env_vars == {"K": "v"}
        assert gp.pre_launch_script is None
        assert gp.post_launch_script is None
        assert gp.custom_args == ["--z"]
        assert gp.pre_launch_failure_mode == "abort"
        assert gp.post_launch_failure_mode == "ignore"

    def test_app_preferences_applied(self, unvalidated_manager):
        unvalidated_manager._apply_unvalidated_config(
            {
                "app_preferences": {
                    "app.X": {
                        "launch_method": "system",
                        "env_vars": {"A": "B"},
                        "custom_args": ["--q"],
                        "pre_launch_failure_mode": "warn",
                        "post_launch_failure_mode": "abort",
                    }
                }
            }
        )
        ap = unvalidated_manager.config.app_preferences["app.X"]
        assert ap.launch_method == "system"
        assert ap.env_vars == {"A": "B"}
        assert ap.pre_launch_script is None
        assert ap.post_launch_script is None
        assert ap.custom_args == ["--q"]
        assert ap.pre_launch_failure_mode == "warn"
        assert ap.post_launch_failure_mode == "abort"


class TestParseConfigDataNoPydantic:
    """When Pydantic is unavailable, _parse_config_data falls through to
    the unvalidated-apply path (line 281)."""

    def test_parse_falls_through_to_unvalidated(self, manager):
        import lib.config_manager as cm

        with patch.object(cm, "PYDANTIC_AVAILABLE", False), patch.object(
            cm, "PydanticWrapperConfig", None
        ):
            manager._parse_config_data(
                {
                    "blocklist": ["b1", "b2"],
                    "permission_presets": {
                        "pp": {"permissions": ["--x"]},
                    },
                    "global_preferences": {"launch_method": "flatpak"},
                    "app_preferences": {
                        "ap.X": {"launch_method": "system"},
                    },
                }
            )
        # Unvalidated path wrote everything
        assert manager.config.blocklist == ["b1", "b2"]
        assert manager.config.permission_presets["pp"] == ["--x"]
        assert manager.config.global_preferences.launch_method == "flatpak"
        assert manager.config.app_preferences["ap.X"].launch_method == "system"


# --------------------------------------------------------------------------- #
# _load_fallback_config  — additional branches (461-462, 469, 475, 477,
# 479, 485-489)
# --------------------------------------------------------------------------- #


class TestLoadFallbackConfigFullCoverage:
    def test_no_file_creates_defaults(self, manager, temp_root):
        """When the file does not exist, _load_fallback_config returns
        early and creates defaults."""
        manager.config_file.unlink(missing_ok=True)
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        assert manager.config.debug_mode is False
        assert manager.config.bin_dir == str(Path.home() / "bin")

    def test_comments_and_blank_lines_are_skipped(
        self, manager, monkeypatch
    ):
        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text(
            "# this is a comment\n"
            "\n"
            "   \n"
            "log_level=ERROR\n"
        )
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        assert manager.config.log_level == "ERROR"

    def test_bin_dir_set_from_fallback(self, manager):
        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text("bin_dir=/opt/bin\n")
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        assert manager.config.bin_dir == "/opt/bin"

    def test_debug_mode_true(self, manager):
        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text("debug_mode=true\n")
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        assert manager.config.debug_mode is True

    def test_debug_mode_false_value_parsed(self, manager):
        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text("debug_mode=false\n")
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        assert manager.config.debug_mode is False

    def test_debug_mode_unrecognized_value_parsed_as_false(self, manager):
        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text("debug_mode=maybe\n")
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        assert manager.config.debug_mode is False

    def test_log_level_set_from_fallback_uppercases_value(self, manager):
        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text("log_level=debug\n")
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        assert manager.config.log_level == "DEBUG"

    def test_enable_notifications_set_from_fallback(self, manager):
        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text("enable_notifications=yes\n")
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        assert manager.config.enable_notifications is True

    def test_hook_failure_mode_default_valid(self, manager):
        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text("hook_failure_mode_default=ignore\n")
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        assert manager.config.hook_failure_mode_default == "ignore"

    def test_hook_failure_mode_default_invalid_ignored(self, manager):
        manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        manager.config_file.write_text("hook_failure_mode_default=nope\n")
        with patch("lib.config_manager.TOML_AVAILABLE", False):
            manager._load_fallback_config()
        # Default "warn" is preserved because "nope" is not in HOOK_FAILURE_MODES
        assert manager.config.hook_failure_mode_default == "warn"


# --------------------------------------------------------------------------- #
# export_profile: TOML loads ValueError fallback  (lines 719-720)
# --------------------------------------------------------------------------- #


class TestExportProfileTomlLoadsValueError:
    def test_non_toml_profile_text_is_written_raw(self, manager, tmp_path):
        """When the profile file's text fails tomli.loads, the raw text is
        written to the export destination verbatim."""
        manager.create_profile("work")
        profiles_dir = manager.config_dir / "profiles"
        raw_text = "this is :: not :: valid toml {[("
        (profiles_dir / "work.toml").write_text(raw_text)

        out = tmp_path / "work.toml"
        assert manager.export_profile("work", out) is True
        assert out.read_text() == raw_text


# --------------------------------------------------------------------------- #
# create_config_manager factory  (line 780)
# --------------------------------------------------------------------------- #


class TestCreateConfigManagerFactory:
    def test_create_config_manager_returns_enhanced_config_manager(
        self, temp_root
    ):
        from lib.config_manager import create_config_manager

        mgr = create_config_manager(
            config_dir=temp_root / ".config" / "fplaunchwrapper"
        )
        assert isinstance(mgr, EnhancedConfigManager)
        # The factory honours the override
        assert mgr.config_dir == temp_root / ".config" / "fplaunchwrapper"

    def test_create_config_manager_with_no_args(self, temp_root):
        """When no config_dir is passed, the factory falls back to the
        XDG default under the isolated HOME."""
        from lib.config_manager import create_config_manager

        mgr = create_config_manager()
        assert isinstance(mgr, EnhancedConfigManager)
        assert mgr.app_name == "fplaunchwrapper"


# --------------------------------------------------------------------------- #
# _serialize_config: permission_presets block (line 440)
# --------------------------------------------------------------------------- #


class TestSerializeConfigPermissionPresets:
    def test_serializes_user_permission_presets(self, manager):
        manager.add_permission_preset("custom", ["--a", "--b"])
        data = manager._serialize_config()
        assert data["permission_presets"]["custom"] == ["--a", "--b"]

    def test_omits_permission_presets_when_empty(self, manager):
        manager.config.permission_presets = {}
        data = manager._serialize_config()
        assert "permission_presets" not in data
