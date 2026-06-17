"""Verify that the unvalidated fallback path in _apply_unvalidated_config
enforces the same security model as the Pydantic path.

Prior to this test, the unvalidated path silently bypassed the
dangerous-character check on custom_args, the script-path safety
check on pre_launch_script / post_launch_script, and the failure-mode
whitelist on pre_launch_failure_mode / post_launch_failure_mode.
This is a regression test to make sure the security checks are
present in both paths.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.config_manager import (
    EnhancedConfigManager,
    PYDANTIC_AVAILABLE,
    PydanticWrapperConfig,
    ConfigValidationError,
)


@pytest.fixture
def unvalidated_manager():
    """An EnhancedConfigManager with Pydantic availability forced off.

    This forces _parse_config_data down the unvalidated fallback path,
    where security is enforced by the pure-Python helpers in
    config_validation rather than by Pydantic field validators.
    """
    with tempfile.TemporaryDirectory() as tmp, \
         patch("lib.config_manager.PYDANTIC_AVAILABLE", False), \
         patch("lib.config_manager.PydanticWrapperConfig", None):
        yield EnhancedConfigManager(config_dir=Path(tmp))


@pytest.fixture
def validated_manager():
    """A regular EnhancedConfigManager that uses the Pydantic path."""
    with tempfile.TemporaryDirectory() as tmp:
        yield EnhancedConfigManager(config_dir=Path(tmp))


def _has_safety_check(exc: BaseException) -> bool:
    """Return True if the error message contains one of the known
    safety-check error prefixes. Lets us assert the RIGHT check fired
    without coupling to exact wording."""
    msg = str(exc).lower()
    return any(
        needle in msg
        for needle in (
            "dangerous character",
            "sensitive system directory",
            "script file does not exist",
            "script file is not executable",
            "invalid failure mode",
        )
    )


class TestUnvalidatedPathEnforcesDangerousChars:
    """The unvalidated path must reject dangerous chars in custom_args."""

    @pytest.mark.parametrize(
        "bad_arg",
        [
            "--filesystem=;rm -rf /",
            "--flag|pipe",  # bare-flag form (regression: previously bypassed)
            "--key=`whoami`",
            "--val=$(rm -rf /)",
            "not-a-flag;ls",
        ],
    )
    def test_rejects_dangerous_char_in_global_preferences(
        self, unvalidated_manager, bad_arg
    ) -> None:
        with pytest.raises(ConfigValidationError) as exc_info:
            unvalidated_manager._parse_config_data(
                {"global_preferences": {"custom_args": [bad_arg]}}
            )
        assert _has_safety_check(exc_info.value), (
            f"Expected safety-check error for {bad_arg!r}, got: {exc_info.value}"
        )

    def test_rejects_dangerous_char_in_app_preferences(self, unvalidated_manager) -> None:
        with pytest.raises(ConfigValidationError):
            unvalidated_manager._parse_config_data(
                {"app_preferences": {"app.X": {"custom_args": ["--filesystem=;rm"]}}}
            )

    def test_accepts_safe_custom_args(self, unvalidated_manager) -> None:
        # Sanity: the safety check doesn't reject legitimate args.
        unvalidated_manager._parse_config_data(
            {"global_preferences": {"custom_args": ["--filesystem=/home/user", "--device=/dev/dri"]}}
        )
        assert unvalidated_manager.config.global_preferences.custom_args == [
            "--filesystem=/home/user",
            "--device=/dev/dri",
        ]


class TestUnvalidatedPathEnforcesScriptPathSafety:
    """The unvalidated path must reject missing / non-executable /
    sensitive-dir pre_launch_script and post_launch_script paths."""

    def test_rejects_nonexistent_script(self, unvalidated_manager) -> None:
        with pytest.raises(ConfigValidationError) as exc_info:
            unvalidated_manager._parse_config_data(
                {"global_preferences": {"pre_launch_script": "/nonexistent/path.sh"}}
            )
        assert _has_safety_check(exc_info.value)

    def test_rejects_sensitive_dir_script(self, unvalidated_manager) -> None:
        with pytest.raises(ConfigValidationError) as exc_info:
            unvalidated_manager._parse_config_data(
                {"global_preferences": {"pre_launch_script": "/etc/passwd"}}
            )
        # Either the not-executable or sensitive-dir check should fire;
        # the important thing is the security check runs.
        assert _has_safety_check(exc_info.value)

    def test_accepts_none(self, unvalidated_manager) -> None:
        # None is the default and should never be flagged.
        unvalidated_manager._parse_config_data(
            {"global_preferences": {"pre_launch_script": None}}
        )
        assert unvalidated_manager.config.global_preferences.pre_launch_script is None

    def test_accepts_existing_executable_script(
        self, unvalidated_manager, tmp_path
    ) -> None:
        # Write a real executable and verify it passes.
        script = tmp_path / "pre.sh"
        script.write_text("#!/bin/sh\necho hi\n")
        script.chmod(0o755)
        unvalidated_manager._parse_config_data(
            {"global_preferences": {"pre_launch_script": str(script)}}
        )
        assert unvalidated_manager.config.global_preferences.pre_launch_script == str(script)


class TestUnvalidatedPathEnforcesFailureModeWhitelist:
    """The unvalidated path must reject failure-mode values not in
    HOOK_FAILURE_MODES."""

    @pytest.mark.parametrize(
        "bad_mode",
        ["bogus", "ALWAYS", "true", "1", ""],
    )
    def test_rejects_invalid_failure_mode(
        self, unvalidated_manager, bad_mode
    ) -> None:
        with pytest.raises(ConfigValidationError) as exc_info:
            unvalidated_manager._parse_config_data(
                {"global_preferences": {"pre_launch_failure_mode": bad_mode}}
            )
        assert _has_safety_check(exc_info.value)

    @pytest.mark.parametrize("good_mode", ["abort", "warn", "ignore"])
    def test_accepts_valid_failure_mode(
        self, unvalidated_manager, good_mode
    ) -> None:
        unvalidated_manager._parse_config_data(
            {"global_preferences": {"pre_launch_failure_mode": good_mode}}
        )
        assert (
            unvalidated_manager.config.global_preferences.pre_launch_failure_mode
            == good_mode
        )


class TestValidatedAndUnvalidatedPathsAreEquivalent:
    """The same input must produce the same accept/reject decision in
    both paths. The only difference should be HOW the safety check
    runs (pydantic field validator vs. direct helper call), not WHETHER
    it runs."""

    @pytest.mark.parametrize(
        "data",
        [
            {"global_preferences": {"custom_args": ["--filesystem=;rm -rf /"]}},
            {"global_preferences": {"pre_launch_failure_mode": "bogus"}},
            {"app_preferences": {"x": {"custom_args": ["--flag|pipe"]}}},
        ],
    )
    def test_both_paths_reject_same_inputs(self, validated_manager, unvalidated_manager, data) -> None:
        with pytest.raises(ConfigValidationError):
            validated_manager._parse_config_data(data)
        with pytest.raises(ConfigValidationError):
            unvalidated_manager._parse_config_data(data)

    def test_both_paths_accept_same_inputs(self, validated_manager, unvalidated_manager) -> None:
        data = {
            "global_preferences": {
                "launch_method": "auto",
                "env_vars": {"K": "v"},
                "custom_args": ["--filesystem=/home/user"],
                "pre_launch_failure_mode": "warn",
            }
        }
        validated_manager._parse_config_data(data)
        unvalidated_manager._parse_config_data(data)
        # Both should produce the same effective state.
        assert (
            validated_manager.config.global_preferences.launch_method
            == unvalidated_manager.config.global_preferences.launch_method
        )
        assert (
            validated_manager.config.global_preferences.env_vars
            == unvalidated_manager.config.global_preferences.env_vars
        )
        assert (
            validated_manager.config.global_preferences.custom_args
            == unvalidated_manager.config.global_preferences.custom_args
        )
        assert (
            validated_manager.config.global_preferences.pre_launch_failure_mode
            == unvalidated_manager.config.global_preferences.pre_launch_failure_mode
        )
