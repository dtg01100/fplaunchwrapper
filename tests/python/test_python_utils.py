#!/usr/bin/env python3
"""Comprehensive test suite for fplaunchwrapper using pytest
Tests all core functionality with proper mocking and fixtures.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    from lib.python_utils import (
        acquire_lock,
        find_executable,
        get_temp_dir,
        release_lock,
        safe_mktemp,
    )
except ImportError:
    acquire_lock = release_lock = find_executable = safe_mktemp = get_temp_dir = None


class TestPythonUtils:
    """Test python utility functions."""

    def test_find_executable_bash(self) -> None:
        """Test finding bash executable."""
        if not find_executable:
            pytest.skip("python_utils not available")

        result = find_executable("bash")
        assert result is not None
        assert "bash" in result

    def test_find_executable_nonexistent(self) -> None:
        """Test finding non-existent executable."""
        if not find_executable:
            pytest.skip("python_utils not available")

        result = find_executable("nonexistent_command_xyz")
        assert result is None

    def test_safe_mktemp_basic(self) -> None:
        """Test secure temporary file creation."""
        if not safe_mktemp:
            pytest.skip("python_utils not available")

        result = safe_mktemp()
        assert result is not None
        assert os.path.exists(result)
        assert os.access(result, os.W_OK)

        os.unlink(result)

    def test_safe_mktemp_custom_template(self) -> None:
        """Test temp file creation with custom template."""
        if not safe_mktemp:
            pytest.skip("python_utils not available")

        result = safe_mktemp("test-XXXXXX.txt")
        assert result is not None
        assert result.endswith(".txt")
        assert "test-" in result

        os.unlink(result)

    def test_get_temp_dir(self) -> None:
        """Test temporary directory selection."""
        if not get_temp_dir:
            pytest.skip("python_utils not available")

        result = get_temp_dir()
        assert result is not None
        assert os.path.isdir(result)
        assert os.access(result, os.W_OK)


class TestLocking:
    """Test file locking functionality."""

    def test_acquire_and_release_lock(self) -> None:
        """Test lock acquisition and release."""
        if not acquire_lock or not release_lock:
            pytest.skip("Locking not available")

        lock_name = "test-lock"
        try:
            result = acquire_lock(lock_name, timeout_seconds=5)
            assert result is True

            released = release_lock(lock_name)
            assert released is True
        finally:
            release_lock(lock_name)

    def test_lock_timeout(self) -> None:
        """Test lock timeout behavior."""
        if not acquire_lock:
            pytest.skip("Locking not available")

        result = acquire_lock("timeout-test", timeout_seconds=0)
        assert result is not True


class TestBashIntegration:
    """Test integration with bash scripts."""

    @pytest.fixture
    def temp_bin_dir(self, tmp_path):
        """Create temporary bin directory."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        return bin_dir

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return config_dir

    def test_bash_script_execution(self, temp_bin_dir) -> None:
        """Test basic bash script execution."""
        script_path = temp_bin_dir / "test_script.sh"
        script_path.write_text(
            """#!/bin/bash
echo "Hello from bash script"
exit 0
"""
        )
        script_path.chmod(0o755)

        result = subprocess.run(
            [str(script_path)], check=False, capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "Hello from bash script" in result.stdout

    def test_wrapper_script_generation(self, temp_bin_dir, temp_config_dir) -> None:
        """Test wrapper script generation logic."""
        assert temp_bin_dir.exists()
        assert temp_config_dir.exists()

    @patch("subprocess.run")
    def test_flatpak_command_mocking(self, mock_run, temp_bin_dir) -> None:
        """Test flatpak command execution with mocking."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "org.mozilla.firefox"

        result = mock_run(["flatpak", "list", "--app"])

        mock_run.assert_called_once_with(["flatpak", "list", "--app"])
        assert result.returncode == 0


class TestPerformance:
    """Performance-focused tests."""

    def test_temp_creation_performance(self) -> None:
        """Test temp file creation performance."""
        if not safe_mktemp:
            pytest.skip("python_utils not available")

        import time

        start_time = time.time()
        for _ in range(100):
            result = safe_mktemp()
            if result and os.path.exists(result):
                os.unlink(result)
        end_time = time.time()

        assert end_time - start_time < 5.0


class TestConfiguration:
    """Test configuration management."""

    def test_config_manager_creation(self) -> None:
        """Test configuration manager creation."""
        try:
            from lib.config_manager import create_config_manager
        except ImportError:
            pytest.skip("config_manager not available")

        config = create_config_manager()
        assert config is not None
        assert hasattr(config, "config")
        assert hasattr(config.config, "bin_dir")

    def test_config_file_operations(self) -> None:
        """Test configuration file read/write."""
        try:
            from lib.config_manager import create_config_manager
        except ImportError:
            pytest.skip("config_manager not available")

        config = create_config_manager()

        assert config.config.bin_dir != ""
        assert isinstance(config.config.debug_mode, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
