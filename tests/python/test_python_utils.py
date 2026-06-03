#!/usr/bin/env python3
"""Focused pytest coverage for lib.python_utils."""

import os
from pathlib import Path
import tempfile

import pytest

try:
    from lib.python_utils import (
        acquire_lock,
        canonicalize_path_no_resolve,
        find_executable,
        get_temp_dir,
        get_wrapper_id,
        is_wrapper_file,
        release_lock,
        safe_mktemp,
        sanitize_id_to_name,
        sanitize_string,
        validate_home_dir,
    )
except ImportError:
    acquire_lock = release_lock = find_executable = safe_mktemp = get_temp_dir = None
    canonicalize_path_no_resolve = validate_home_dir = None
    is_wrapper_file = get_wrapper_id = None
    sanitize_id_to_name = sanitize_string = None


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

    def test_find_executable_absolute_path(self) -> None:
        """Test finding executable via absolute path."""
        if not find_executable:
            pytest.skip("python_utils not available")

        bash = find_executable("bash")
        assert bash is not None
        # Use the resolved bash path
        result = find_executable(bash)
        assert result is not None

    def test_find_executable_absolute_nonexistent(self) -> None:
        """Test absolute path that doesn't exist returns None."""
        if not find_executable:
            pytest.skip("python_utils not available")

        result = find_executable("/nonexistent/path/to/binary")
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

    def test_safe_mktemp_no_xxxxxx(self) -> None:
        """Test safe_mktemp with template lacking XXXXXX uses it as prefix."""
        if not safe_mktemp:
            pytest.skip("python_utils not available")

        result = safe_mktemp("no-suffix-template")
        assert result is not None
        assert "no-suffix-template" in result
        os.unlink(result)

    def test_safe_mktemp_invalid_dir(self) -> None:
        """Test safe_mktemp with invalid dir falls back to tempdir."""
        if not safe_mktemp:
            pytest.skip("python_utils not available")

        result = safe_mktemp("test-XXXXXX", dir_param="/nonexistent/directory")
        assert result is not None
        os.unlink(result)

    def test_get_temp_dir(self) -> None:
        """Test temporary directory selection."""
        if not get_temp_dir:
            pytest.skip("python_utils not available")

        result = get_temp_dir()
        assert result is not None
        assert os.path.isdir(result)
        assert os.access(result, os.W_OK)

    def test_sanitize_string_empty(self) -> None:
        """Test sanitizing an empty string returns empty."""
        if not sanitize_string:
            pytest.skip("python_utils not available")
        assert sanitize_string("") == ""

    def test_sanitize_string_none(self) -> None:
        """Test sanitizing None returns empty."""
        if not sanitize_string:
            pytest.skip("python_utils not available")
        assert sanitize_string(None) == ""  # type: ignore[arg-type]

    def test_sanitize_string_special_chars(self) -> None:
        """Test sanitizing special characters adds escapes."""
        if not sanitize_string:
            pytest.skip("python_utils not available")
        result = sanitize_string("hello;world")
        assert "\\;" in result

    def test_canonicalize_path_no_resolve(self) -> None:
        """Test canonicalize_path_no_resolve returns absolute Path."""
        if not canonicalize_path_no_resolve:
            pytest.skip("python_utils not available")
        result = canonicalize_path_no_resolve("./relative/path")
        assert result is not None
        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_canonicalize_path_no_resolve_tilde(self) -> None:
        """Test tilde expansion in canonicalize_path_no_resolve."""
        if not canonicalize_path_no_resolve:
            pytest.skip("python_utils not available")
        result = canonicalize_path_no_resolve("~")
        assert result is not None
        assert str(Path.home()) in str(result)

    def test_validate_home_dir_in_home(self) -> None:
        """Test validate_home_dir accepts path inside HOME."""
        if not validate_home_dir:
            pytest.skip("python_utils not available")
        result = validate_home_dir("~/subdir")
        assert result is not None
        assert str(Path.home()) in result

    def test_validate_home_dir_none(self) -> None:
        """Test validate_home_dir returns None for None input."""
        if not validate_home_dir:
            pytest.skip("python_utils not available")
        assert validate_home_dir(None) is None

    def test_validate_home_dir_outside_home(self) -> None:
        """Test validate_home_dir returns None for paths outside HOME."""
        if not validate_home_dir:
            pytest.skip("python_utils not available")
        result = validate_home_dir("/etc/passwd")
        assert result is None

    def test_sanitize_id_to_name_basic(self) -> None:
        """Test sanitize_id_to_name for normal Flatpak IDs."""
        if not sanitize_id_to_name:
            pytest.skip("python_utils not available")
        assert sanitize_id_to_name("org.mozilla.firefox") == "firefox"
        assert sanitize_id_to_name("com.example.App") == "app"

    def test_sanitize_id_to_name_special_chars(self) -> None:
        """Test sanitize_id_to_name replaces special chars with hyphens."""
        if not sanitize_id_to_name:
            pytest.skip("python_utils not available")
        result = sanitize_id_to_name("org.example.app with space")
        assert " " not in result

    def test_sanitize_id_to_name_empty_falls_back_to_hash(self) -> None:
        """Test sanitize_id_to_name falls back to hash when result is empty."""
        if not sanitize_id_to_name:
            pytest.skip("python_utils not available")
        result = sanitize_id_to_name(".....")
        assert result.startswith("app-")

    def test_sanitize_id_to_name_truncates(self) -> None:
        """Test sanitize_id_to_name truncates to 100 chars."""
        if not sanitize_id_to_name:
            pytest.skip("python_utils not available")
        long_id = "org.example." + "x" * 200
        result = sanitize_id_to_name(long_id)
        assert len(result) <= 100

    def test_is_wrapper_file_valid(self) -> None:
        """Test is_wrapper_file accepts a valid wrapper."""
        if not is_wrapper_file:
            pytest.skip("python_utils not available")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\n")
            f.write("# Generated by fplaunchwrapper\n")
            f.write('NAME="firefox"\n')
            f.write('ID="org.mozilla.firefox"\n')
            f.flush()
            os.chmod(f.name, 0o755)
            try:
                assert is_wrapper_file(f.name) is True
            finally:
                os.unlink(f.name)

    def test_is_wrapper_file_too_large(self) -> None:
        """Test is_wrapper_file rejects files larger than MAX_FILE_SIZE."""
        if not is_wrapper_file:
            pytest.skip("python_utils not available")
        from lib.python_utils import MAX_FILE_SIZE

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\n# Generated by fplaunchwrapper\n")
            f.write(f"# {'x' * (MAX_FILE_SIZE + 1)}\n")
            f.write('ID="org.test.large"\n')
            f.flush()
            os.chmod(f.name, 0o755)
            try:
                assert is_wrapper_file(f.name) is False
            finally:
                os.unlink(f.name)

    def test_is_wrapper_file_no_shebang(self) -> None:
        """Test is_wrapper_file rejects files without shebang."""
        if not is_wrapper_file:
            pytest.skip("python_utils not available")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("not a script\n")
            f.flush()
            try:
                assert is_wrapper_file(f.name) is False
            finally:
                os.unlink(f.name)

    def test_is_wrapper_file_not_generated(self) -> None:
        """Test is_wrapper_file rejects files without Generated-by marker."""
        if not is_wrapper_file:
            pytest.skip("python_utils not available")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\n# not generated by us\nNAME=x\nID=y\n")
            f.flush()
            os.chmod(f.name, 0o755)
            try:
                assert is_wrapper_file(f.name) is False
            finally:
                os.unlink(f.name)

    def test_is_wrapper_file_nonexistent(self) -> None:
        """Test is_wrapper_file returns False for nonexistent path."""
        if not is_wrapper_file:
            pytest.skip("python_utils not available")
        assert is_wrapper_file("/nonexistent/path/wrapper.sh") is False

    def test_get_wrapper_id_from_quoted(self) -> None:
        """Test get_wrapper_id extracts from ID="..." format."""
        if not get_wrapper_id:
            pytest.skip("python_utils not available")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write('#!/bin/bash\nID="org.mozilla.firefox"\n')
            f.flush()
            try:
                assert get_wrapper_id(f.name) == "org.mozilla.firefox"
            finally:
                os.unlink(f.name)

    def test_get_wrapper_id_from_comment(self) -> None:
        """Test get_wrapper_id falls back to Flatpak ID: comment format."""
        if not get_wrapper_id:
            pytest.skip("python_utils not available")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\n# Flatpak ID: org.example.app\n")
            f.flush()
            try:
                assert get_wrapper_id(f.name) == "org.example.app"
            finally:
                os.unlink(f.name)

    def test_get_wrapper_id_nonexistent(self) -> None:
        """Test get_wrapper_id returns None for nonexistent file."""
        if not get_wrapper_id:
            pytest.skip("python_utils not available")
        assert get_wrapper_id("/nonexistent/path") is None


class TestLocking:
    """Test file locking functionality."""

    def test_acquire_and_release_lock(self) -> None:
        """Test lock acquisition and release."""
        if not acquire_lock or not release_lock:
            pytest.skip("Locking not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            lock_dir = Path(tmpdir)
            lock_name = "test-lock"
            try:
                result = acquire_lock(lock_name, timeout_seconds=5, lock_dir=lock_dir)
                assert result is True

                released = release_lock(lock_name, lock_dir=lock_dir)
                assert released is True
            finally:
                release_lock(lock_name, lock_dir=lock_dir)

    def test_lock_timeout(self) -> None:
        """Test lock timeout behavior under contention."""
        if not acquire_lock or not release_lock:
            pytest.skip("Locking not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            lock_dir = Path(tmpdir)
            lock_name = f"timeout-test-{os.getpid()}"

            assert acquire_lock(lock_name, timeout_seconds=5, lock_dir=lock_dir) is True
            try:
                result = acquire_lock(lock_name, timeout_seconds=0.01, lock_dir=lock_dir)
                assert result is not True
            finally:
                assert release_lock(lock_name, lock_dir=lock_dir) is True

    def test_release_lock_when_not_held(self) -> None:
        """Test releasing a non-existent lock returns False."""
        if not release_lock:
            pytest.skip("Locking not available")
        with tempfile.TemporaryDirectory() as tmpdir:
            assert release_lock("never-held", lock_dir=Path(tmpdir)) is False

    def test_release_lock_wrong_pid(self) -> None:
        """Test releasing a lock held by another PID returns False."""
        if not acquire_lock or not release_lock:
            pytest.skip("Locking not available")
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_dir = Path(tmpdir)
            lock_name = "other-pid-lock"
            # Manually create a pid file with a different PID
            pidfile = lock_dir / f"{lock_name}.pid"
            lockfile = lock_dir / f"{lock_name}.lock"
            lockfile.mkdir()
            pidfile.write_text("999999:0")  # PID unlikely to be ours
            try:
                result = release_lock(lock_name, lock_dir=lock_dir)
                assert result is False
            finally:
                import contextlib
                with contextlib.suppress(OSError):
                    lockfile.rmdir()
                with contextlib.suppress(OSError):
                    pidfile.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
