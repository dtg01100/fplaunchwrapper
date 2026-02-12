#!/usr/bin/env python3
"""Unit tests for safety.py
Tests all safety mechanisms including input validation, path traversal prevention,
wrapper validation, and test environment detection.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.safety import (
    canonicalize_path_no_resolve,
    is_dangerous_wrapper,
    is_test_environment,
    is_wrapper_file,
    safe_launch_check,
    sanitize_id_to_name,
    sanitize_string,
    validate_flatpak_id,
    validate_home_dir,
)


class TestIsTestEnvironment:
    """Test test environment detection."""

    def test_with_test_arg(self) -> None:
        """Test is_test_environment with test argument."""
        with patch.object(sys, "argv", ["script", "test"]):
            assert is_test_environment() is True

    def test_with_env_var(self) -> None:
        """Test is_test_environment with environment variable."""
        with patch.dict(os.environ, {"FPWRAPPER_TEST_ENV": "true"}):
            assert is_test_environment() is True

    def test_with_pytest_module(self) -> None:
        """Test is_test_environment with pytest module."""
        with patch.dict(sys.modules, {"pytest": None}):
            assert is_test_environment() is True

    def test_with_unittest_module(self) -> None:
        """Test is_test_environment with unittest module."""
        with patch.dict(sys.modules, {"unittest": None}):
            assert is_test_environment() is True

    def test_not_test_environment(self) -> None:
        """Test is_test_environment returns False when not in test environment."""
        with patch.object(sys, "argv", ["script"]):
            with patch.dict(os.environ, {"FPWRAPPER_TEST_ENV": "false"}):
                unittest_modules = [
                    mod for mod in sys.modules if mod.startswith("unittest")
                ]
                for mod in unittest_modules:
                    del sys.modules[mod]

                pytest_modules = [
                    mod
                    for mod in sys.modules
                    if mod.startswith("pytest") or "pytest" in mod
                ]
                for mod in pytest_modules:
                    del sys.modules[mod]

                assert is_test_environment() is False


class TestSanitizeString:
    """Test string sanitization."""

    def test_basic(self) -> None:
        """Test basic string sanitization."""
        result = sanitize_string("test")
        assert result == "test"

    def test_injection_prevention(self) -> None:
        """Test string sanitization against injection attacks."""
        malicious = '"; rm -rf / #'
        result = sanitize_string(malicious)
        assert result == '\\"\\; rm -rf / #'
        assert '"' not in result.replace('\\"', "")
        assert ";" not in result.replace("\\;", "")

    def test_shell_escapes(self) -> None:
        """Test escaping of shell metacharacters."""
        dangerous = "$(rm -rf /)`echo pwned`"
        result = sanitize_string(dangerous)
        assert "$" not in result.replace("\\$", "")
        assert "`" not in result.replace("\\`", "")


class TestValidateFlatpakId:
    """Test Flatpak ID validation."""

    def test_valid_ids(self) -> None:
        """Test valid Flatpak IDs."""
        assert validate_flatpak_id("org.mozilla.firefox") is True
        assert validate_flatpak_id("com.example.App123") is True
        assert validate_flatpak_id("org.gimp.GIMP") is True

    def test_invalid_ids(self) -> None:
        """Test invalid Flatpak IDs."""
        assert validate_flatpak_id("firefox") is False
        assert validate_flatpak_id("") is False
        assert validate_flatpak_id("no-dot-here") is False


class TestValidateHomeDir:
    """Test home directory validation."""

    def test_valid_path(self) -> None:
        """Test with valid path under HOME."""
        home_subdir = os.path.join(os.path.expanduser("~"), "test")
        result = validate_home_dir(home_subdir)
        assert result == home_subdir

    def test_invalid_path(self) -> None:
        """Test with system path outside HOME."""
        result = validate_home_dir("/usr/bin")
        assert result is None

    def test_path_traversal_attacks(self) -> None:
        """Test prevention of path traversal attacks."""
        attack_paths = [
            "/etc/passwd",
            "/root/.ssh/id_rsa",
            "/var/log/syslog",
        ]
        for attack_path in attack_paths:
            result = validate_home_dir(attack_path)
            assert result is None


class TestCanonicalizePath:
    """Test path canonicalization."""

    def test_basic(self) -> None:
        """Test basic path canonicalization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "test")
            result = canonicalize_path_no_resolve(test_path)
            assert result == Path(test_path)

    def test_relative_path(self) -> None:
        """Test relative path canonicalization."""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                result = canonicalize_path_no_resolve("../test")
                expected = Path(os.path.abspath("../test"))
                assert result == expected
            finally:
                os.chdir(original_cwd)


class TestSanitizeIdToName:
    """Test Flatpak ID to wrapper name sanitization."""

    @pytest.mark.parametrize(
        ("input_id", "expected"),
        [
            ("org.mozilla.firefox", "firefox"),
            ("com.example.Test-App_1.2.3", "3"),
            ("org.gimp.GIMP", "gimp"),
            ("com.valvesoftware.Steam", "steam"),
        ],
    )
    def test_basic(self, input_id: str, expected: str) -> None:
        """Test ID to name sanitization."""
        result = sanitize_id_to_name(input_id)
        assert result == expected


class TestIsWrapperFile:
    """Test wrapper file validation."""

    def test_valid_wrapper(self) -> None:
        """Test with valid wrapper file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/usr/bin/env bash\n")
            f.write("# Generated by fplaunchwrapper\n")
            f.write('NAME="test"\n')
            f.write('ID="org.test.app"\n')
            f.write('flatpak run "$ID" "$@"\n')
            temp_path = f.name

        try:
            result = is_wrapper_file(temp_path)
            assert result is True
        finally:
            os.unlink(temp_path)

    def test_invalid_interpreter(self) -> None:
        """Test with wrong shebang interpreter."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("#!/bin/python3\n")
            f.write("# Generated by fplaunchwrapper\n")
            f.write('NAME="test"\n')
            f.write('ID="org.test.app"\n')
            temp_path = f.name

        try:
            result = is_wrapper_file(temp_path)
            assert result is False
        finally:
            os.unlink(temp_path)

    def test_binary_content(self) -> None:
        """Test with binary file content."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"\x00\x01\x02\x03\x04\x05")
            binary_path = f.name

        try:
            result = is_wrapper_file(binary_path)
            assert result is False
        finally:
            os.unlink(binary_path)

    def test_symlink_rejection(self) -> None:
        """Test that symlinks are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sensitive_file = "/etc/passwd"
            symlink_path = os.path.join(tmpdir, "malicious_wrapper")

            try:
                os.symlink(sensitive_file, symlink_path)
                result = is_wrapper_file(symlink_path)
                assert result is False
            except OSError:
                pytest.skip("Cannot create symlinks in test environment")


class TestIsDangerousWrapper:
    """Test dangerous wrapper detection."""

    def test_dangerous_content(self, tmp_path: Path) -> None:
        """Test with dangerous wrapper content."""
        wrapper_path = tmp_path / "dangerous_wrapper"
        wrapper_path.write_text("flatpak run org.mozilla.firefox")
        assert is_dangerous_wrapper(wrapper_path) is True

    def test_safe_content(self, tmp_path: Path) -> None:
        """Test with safe wrapper content."""
        wrapper_path = tmp_path / "safe_wrapper"
        wrapper_path.write_text("#!/bin/bash\necho 'Hello, World!'")
        assert is_dangerous_wrapper(wrapper_path) is False

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test with nonexistent file."""
        wrapper_path = tmp_path / "nonexistent_wrapper"
        assert is_dangerous_wrapper(wrapper_path) is False


class TestSafeLaunchCheck:
    """Test safe launch checks."""

    def test_test_env_with_browser(self) -> None:
        """Test safe_launch_check in test environment with browser app."""
        with patch.object(sys, "argv", ["script", "test"]):
            assert safe_launch_check("firefox") is False

    def test_test_env_with_safe_app(self) -> None:
        """Test safe_launch_check in test environment with safe app."""
        with patch.object(sys, "argv", ["script", "test"]):
            assert safe_launch_check("gedit") is True

    def test_dangerous_wrapper(self, tmp_path: Path) -> None:
        """Test safe_launch_check with dangerous wrapper."""
        wrapper_path = tmp_path / "dangerous_wrapper"
        wrapper_path.write_text("flatpak run org.mozilla.firefox")
        with patch.object(sys, "argv", ["script", "test"]):
            assert safe_launch_check("firefox", wrapper_path) is False

    def test_safe_wrapper(self, tmp_path: Path) -> None:
        """Test safe_launch_check with safe wrapper."""
        wrapper_path = tmp_path / "safe_wrapper"
        wrapper_path.write_text("#!/bin/bash\necho 'Hello, World!'")
        with patch.object(sys, "argv", ["script", "test"]):
            assert safe_launch_check("gedit", wrapper_path) is True

    def test_not_test_env(self) -> None:
        """Test safe_launch_check not in test environment."""
        with patch.object(sys, "argv", ["script"]):
            with patch.dict(os.environ, {"FPWRAPPER_TEST_ENV": "false"}):
                assert safe_launch_check("firefox") is True


class TestSecurityEdgeCases:
    """Security edge case tests."""

    def test_large_input_handling(self) -> None:
        """Test handling of large inputs."""
        large_input = "test" * 10000
        import time

        start = time.time()
        result = sanitize_string(large_input)
        end = time.time()

        assert len(result) > 0
        assert end - start < 1.0

    def test_unicode_handling(self) -> None:
        """Test handling of unicode characters."""
        unicode_input = "café_настройка_設定"
        result = sanitize_id_to_name(f"org.example.{unicode_input}")
        assert result is not None
        assert len(result) > 0
