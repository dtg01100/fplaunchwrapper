#!/usr/bin/env python3
"""Focused pytest coverage for lib.python_utils."""

import os

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
        """Test lock timeout behavior under contention."""
        if not acquire_lock or not release_lock:
            pytest.skip("Locking not available")

        lock_name = f"timeout-test-{os.getpid()}"

        assert acquire_lock(lock_name, timeout_seconds=5) is True
        try:
            result = acquire_lock(lock_name, timeout_seconds=0.01)
            assert result is not True
        finally:
            assert release_lock(lock_name) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
