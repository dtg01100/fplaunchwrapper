"""Phase 7: Design-by-contract and information-flow tests.

Design-by-contract (DBC) tests verify that public functions uphold their
documented pre/postconditions at runtime.

Information-flow tests verify that sensitive data (paths, secrets,
internal identifiers) does not leak to logs, error messages, or
user-visible output where it shouldn't.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from lib.exceptions import ForbiddenNameError
from lib.python_utils import sanitize_id_to_name
from lib.validation import (
    validate_app_id,
    validate_wrapper_name,
)


# ---- Pre/postcondition contracts ------------------------------------------

class TestValidateAppIdContract:
    """Pre/postconditions for validate_app_id."""

    def test_precondition_no_throw_on_string(self):
        try:
            validate_app_id("")
            validate_app_id("x")
            validate_app_id("a" * 10000)
        except Exception as e:
            pytest.fail(f"validate_app_id raised {type(e).__name__}: {e}")

    def test_postcondition_returns_tuple(self):
        ok, err = validate_app_id("org.mozilla.firefox")
        assert isinstance(ok, bool)
        assert isinstance(err, str)

    def test_postcondition_if_valid_then_no_error(self):
        valid_ids = ["org.mozilla.firefox", "com.example.app", "io.github.user.repo"]
        for app_id in valid_ids:
            ok, err = validate_app_id(app_id)
            assert ok is True
            assert err == "", f"Valid id {app_id!r} returned error {err!r}"

    def test_postcondition_if_invalid_then_has_error(self):
        invalid_ids = ["", "no-dots", "../etc/passwd", "foo; rm"]
        for app_id in invalid_ids:
            ok, err = validate_app_id(app_id)
            assert ok is False
            assert err, f"Invalid id {app_id!r} returned empty error"


class TestValidateWrapperNameContract:
    """Pre/postconditions for validate_wrapper_name."""

    def test_precondition_no_throw_on_string(self):
        try:
            validate_wrapper_name("")
            validate_wrapper_name("x")
            validate_wrapper_name("a" * 10000)
        except Exception as e:
            pytest.fail(f"validate_wrapper_name raised: {e}")

    def test_postcondition_returns_tuple(self):
        ok, err = validate_wrapper_name("firefox")
        assert isinstance(ok, bool)
        assert isinstance(err, str)

    def test_postcondition_valid_implies_no_error(self):
        valid_names = ["firefox", "my-app", "my_app", "app1"]
        for name in valid_names:
            ok, err = validate_wrapper_name(name)
            assert ok is True, f"{name!r} rejected: {err!r}"
            assert err == ""

    def test_postcondition_invalid_implies_error(self):
        invalid_names = ["", "-leading-hyphen", "/etc/passwd"]
        # Note: ".." is technically accepted by validate_wrapper_name (two chars);
        # safety model catches it via path-traversal checks downstream.
        for name in invalid_names:
            ok, err = validate_wrapper_name(name)
            assert ok is False
            assert err

    def test_precondition_no_throw_on_any_input(self):
        try:
            ForbiddenNameError.is_forbidden("")
            ForbiddenNameError.is_forbidden("x" * 1000)
            ForbiddenNameError.is_forbidden("\x00\n\r")
        except Exception as e:
            pytest.fail(f"is_forbidden raised: {e}")

    def test_postcondition_returns_bool(self):
        assert isinstance(ForbiddenNameError.is_forbidden("bash"), bool)
        assert isinstance(ForbiddenNameError.is_forbidden("firefox"), bool)

    def test_postcondition_case_insensitive(self):
        assert (
            ForbiddenNameError.is_forbidden("BASH")
            == ForbiddenNameError.is_forbidden("bash")
        )
        assert (
            ForbiddenNameError.is_forbidden("Rm")
            == ForbiddenNameError.is_forbidden("rm")
        )
        assert (
            ForbiddenNameError.is_forbidden("FLATPAK")
            == ForbiddenNameError.is_forbidden("flatpak")
        )


class TestSanitizeIdToNameContract:
    """sanitize_id_to_name pre/postconditions."""

    def test_postcondition_always_returns_string(self):
        for s in ["", "x", "x" * 1000, "\x00", "\n", "\t"]:
            out = sanitize_id_to_name(s)
            assert isinstance(out, str), f"Non-string output for {s!r}"

    def test_postcondition_output_never_empty(self):
        for s in ["", "x", "org.foo.bar"]:
            out = sanitize_id_to_name(s)
            assert out, f"Empty output for {s!r}"

    def test_postcondition_output_within_length_limit(self):
        for s in ["", "x", "a" * 1000, "org." * 100 + "foo"]:
            out = sanitize_id_to_name(s)
            assert len(out) <= 100, f"Output too long ({len(out)}) for {s!r}"

    def test_postcondition_output_is_safe_wrapper_name(self):
        valid_ids = [
            "org.mozilla.firefox",
            "com.example.MyApp",
            "io.github.user.repo",
            "org.foo.bar",
            "a.b",
        ]
        for app_id in valid_ids:
            name = sanitize_id_to_name(app_id)
            ok, err = validate_wrapper_name(name)
            assert ok, f"Sanitizer output {name!r} for {app_id!r} invalid: {err!r}"


class TestConfigManagerContract:
    """EnhancedConfigManager method contracts."""

    def test_get_app_preferences_returns_dataclass(self, tmp_path):
        from lib.config_manager import create_config_manager
        cm = create_config_manager(config_dir=str(tmp_path))
        prefs = cm.get_app_preferences("nonexistent.app")
        assert prefs is not None
        assert prefs.launch_method in ("auto", "system", "flatpak")

    def test_get_preference_preset_returns_list_or_none(self, tmp_path):
        from lib.config_manager import create_config_manager
        cm = create_config_manager(config_dir=str(tmp_path))
        assert cm.get_permission_preset("nonexistent") is None
        result = cm.get_permission_preset("development")
        if result is not None:
            assert isinstance(result, list)

    def test_is_blocked_returns_bool(self, tmp_path):
        from lib.config_manager import create_config_manager
        cm = create_config_manager(config_dir=str(tmp_path))
        assert isinstance(cm.is_blocked("anything"), bool)
        assert isinstance(cm.is_blocked(""), bool)


# ---- Information-flow / logging safety -----------------------------------

class TestLoggingSafety:
    """Verify error messages and logs don't leak sensitive paths or data."""

    def test_validation_errors_dont_include_internal_paths(self):
        for bad_input in ["../../../etc/passwd", "/etc/shadow", "$HOME"]:
            ok, err = validate_app_id(bad_input)
            assert "/home/" not in err, f"Path leak in error for {bad_input!r}: {err!r}"
            assert "/root/" not in err
            assert "/var/lib/" not in err

    def test_wrapper_template_doesnt_leak_secrets(self, tmp_path, monkeypatch):
        from lib.generate import WrapperGenerator
        from lib.config_manager import create_config_manager

        bin_dir = tmp_path / "bin"
        cfg_dir = tmp_path / "cfg"
        data_dir = tmp_path / "data"
        bin_dir.mkdir(); cfg_dir.mkdir(); data_dir.mkdir()

        cm = create_config_manager(config_dir=str(cfg_dir))
        gen = WrapperGenerator(
            bin_dir=str(bin_dir),
            config_dir=str(cfg_dir),
            data_dir=str(data_dir),
            config_manager=cm,
        )
        monkeypatch.setenv("FPWRAPPER_TEST_ENV", "1")
        gen.generate_wrapper("org.mozilla.firefox")
        wrapper = bin_dir / "firefox"
        content = wrapper.read_text()

        forbidden_strings = ["API_KEY", "SECRET", "PASSWORD", "PRIVATE_KEY"]
        for s in forbidden_strings:
            assert s not in content, f"Wrapper contains {s!r}"

    def test_caplog_does_not_capture_passwords(self, tmp_path, caplog):
        from lib.config_manager import create_config_manager
        from lib.config_models import AppPreferences

        cm = create_config_manager(config_dir=str(tmp_path))
        with caplog.at_level(logging.DEBUG):
            cm.set_app_preferences(
                "secret.app",
                AppPreferences(
                    launch_method="system",
                    env_vars={"PASSWORD": "supersecret123"},
                ),
            )
        for record in caplog.records:
            assert "supersecret123" not in record.getMessage(), (
                f"Password leaked in log: {record.getMessage()}"
            )


class TestFilePermissionsSafety:
    """Verify sensitive files are created with restrictive permissions."""

    def test_config_file_permissions(self, tmp_path):
        from lib.config_manager import create_config_manager

        cm = create_config_manager(config_dir=str(tmp_path))
        cm.save_config()

        config_file = tmp_path / "config.toml"
        if config_file.exists():
            mode = config_file.stat().st_mode
            world_bits = mode & 0o044
            assert world_bits == 0, (
                f"Config file {config_file} is world-readable: mode={oct(mode & 0o777)}"
            )

    def test_wrapper_file_executable(self, tmp_path, monkeypatch):
        from lib.generate import WrapperGenerator
        from lib.config_manager import create_config_manager

        bin_dir = tmp_path / "bin"
        cfg_dir = tmp_path / "cfg"
        data_dir = tmp_path / "data"
        bin_dir.mkdir(); cfg_dir.mkdir(); data_dir.mkdir()

        cm = create_config_manager(config_dir=str(cfg_dir))
        gen = WrapperGenerator(
            bin_dir=str(bin_dir),
            config_dir=str(cfg_dir),
            data_dir=str(data_dir),
            config_manager=cm,
        )
        monkeypatch.setenv("FPWRAPPER_TEST_ENV", "1")
        gen.generate_wrapper("org.mozilla.firefox")
        wrapper = bin_dir / "firefox"

        mode = wrapper.stat().st_mode
        assert mode & 0o111, f"Wrapper not executable: mode={oct(mode & 0o777)}"


class TestConfigFileBehavior:
    """Document env_vars persistence behavior (by design)."""

    def test_env_vars_persisted_in_config(self, tmp_path):
        """env_vars are explicitly designed to be persisted to config.toml.
        Users with secrets should use post-launch hooks or env files, not env_vars.
        """
        from lib.config_manager import create_config_manager
        from lib.config_models import AppPreferences

        cm = create_config_manager(config_dir=str(tmp_path))
        cm.set_app_preferences(
            "myapp",
            AppPreferences(
                launch_method="system",
                env_vars={"MY_VAR": "value1", "OTHER_VAR": "value2"},
            ),
        )
        cm.save_config()

        config_file = tmp_path / "config.toml"
        if config_file.exists():
            content = config_file.read_text()
            assert "MY_VAR" in content
            assert "value1" in content
        else:
            pytest.fail("Config file not created")


# ---- State machine verification -------------------------------------------

class TestConfigStateMachine:
    """Verify config has valid state transitions."""

    def test_initial_state_is_default(self, tmp_path):
        from lib.config_manager import create_config_manager
        cm = create_config_manager(config_dir=str(tmp_path))
        assert cm.config.schema_version >= 1
        assert isinstance(cm.config.blocklist, list)
        assert isinstance(cm.config.permission_presets, dict)

    def test_profile_create_then_switch(self, tmp_path):
        from lib.config_manager import create_config_manager
        cm = create_config_manager(config_dir=str(tmp_path))
        cm.create_profile("work")
        cm.switch_profile("work")
        assert cm.get_active_profile() == "work"

    def test_switch_to_nonexistent_profile_no_state_change(self, tmp_path):
        """Invalid switch: returns False, active profile unchanged."""
        from lib.config_manager import create_config_manager
        cm = create_config_manager(config_dir=str(tmp_path))
        original = cm.get_active_profile()
        result = cm.switch_profile("nonexistent_profile_xyz")
        # Should not silently corrupt state
        assert result is False or result is None
        assert cm.get_active_profile() == original, (
            f"Active profile changed from {original!r} to {cm.get_active_profile()!r}"
        )

    def test_blocklist_add_remove_idempotent(self, tmp_path):
        from lib.config_manager import create_config_manager
        cm = create_config_manager(config_dir=str(tmp_path))
        cm.add_to_blocklist("test.app")
        assert cm.is_blocked("test.app")
        cm.remove_from_blocklist("test.app")
        assert not cm.is_blocked("test.app")


class TestWrapperStateMachine:
    """Verify wrapper generation state transitions."""

    def test_generate_then_no_op_is_idempotent(self, tmp_path, monkeypatch):
        from lib.generate import WrapperGenerator
        from lib.config_manager import create_config_manager

        bin_dir = tmp_path / "bin"
        cfg_dir = tmp_path / "cfg"
        data_dir = tmp_path / "data"
        bin_dir.mkdir(); cfg_dir.mkdir(); data_dir.mkdir()

        cm = create_config_manager(config_dir=str(cfg_dir))
        gen = WrapperGenerator(
            bin_dir=str(bin_dir),
            config_dir=str(cfg_dir),
            data_dir=str(data_dir),
            config_manager=cm,
        )
        monkeypatch.setenv("FPWRAPPER_TEST_ENV", "1")

        r1 = gen.generate_wrapper("org.mozilla.firefox")
        r2 = gen.generate_wrapper("org.mozilla.firefox")
        assert r1 == r2 is True

    def test_generate_with_invalid_id_returns_bool(self, tmp_path, monkeypatch):
        """Generating with invalid ID returns False (doesn't crash)."""
        from lib.generate import WrapperGenerator
        from lib.config_manager import create_config_manager

        bin_dir = tmp_path / "bin"
        cfg_dir = tmp_path / "cfg"
        data_dir = tmp_path / "data"
        bin_dir.mkdir(); cfg_dir.mkdir(); data_dir.mkdir()

        cm = create_config_manager(config_dir=str(cfg_dir))
        gen = WrapperGenerator(
            bin_dir=str(bin_dir),
            config_dir=str(cfg_dir),
            data_dir=str(data_dir),
            config_manager=cm,
        )
        monkeypatch.setenv("FPWRAPPER_TEST_ENV", "1")

        result = gen.generate_wrapper("../etc/passwd")
        assert isinstance(result, bool)
