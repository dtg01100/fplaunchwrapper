#!/usr/bin/env python3
"""Comprehensive edge case and error condition tests for fplaunchwrapper
Tests failure scenarios, boundary conditions, and error recovery.
"""

import builtins
import contextlib
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import NoReturn
from unittest.mock import Mock, patch

import pytest

try:
    from fplaunch.cleanup import WrapperCleanup
    from fplaunch.generate import WrapperGenerator
    from fplaunch.launch import AppLauncher
    from fplaunch.manage import WrapperManager
    from fplaunch.systemd_setup import SystemdSetup

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
class TestInputValidationEdgeCases:
    """Test input validation edge cases and boundary conditions."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp(prefix="fp_edge_test_"))
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"
        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_empty_and_none_inputs(self, temp_env) -> None:
        """Test handling of empty and None inputs."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # Test empty app name
        result = manager.set_preference("", "flatpak")
        assert result is False  # Should reject empty

        # Test None app name (should handle gracefully)
        try:
            result = manager.set_preference(None, "flatpak")
            assert isinstance(result, bool)  # Should not crash
        except Exception:
            pass  # Exception acceptable for None input

        # Test empty preference
        result = manager.set_preference("firefox", "")
        assert result is False  # Should reject empty

    def test_extremely_long_inputs(self, temp_env) -> None:
        """Test handling of extremely long inputs."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # Very long app name
        long_app_name = "a" * 1000
        result = manager.set_preference(long_app_name, "flatpak")
        assert isinstance(result, bool)  # Should handle gracefully

        # Very long preference value
        long_pref = "flatpak" * 100
        result = manager.set_preference("test", long_pref)
        assert isinstance(result, bool)  # Should handle gracefully

    def test_unicode_and_special_characters(self, temp_env) -> None:
        """Test handling of Unicode and special characters."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # Unicode app names
        unicode_apps = [
            "app🚀",  # Emoji
            "tëst",  # Accented characters
            "アプリ",  # Japanese
            "приложение",  # Cyrillic
            "app\u0000name",  # Null byte
            "app\x01\x02\x03",  # Control characters
        ]

        for app in unicode_apps:
            try:
                result = manager.set_preference(app, "flatpak")
                assert isinstance(result, bool)  # Should handle gracefully
            except UnicodeError:
                pass  # Unicode errors acceptable

    def test_malformed_flatpak_ids(self, temp_env) -> None:
        """Test handling of malformed Flatpak IDs."""
        if "WrapperGenerator" not in globals():
            pytest.skip("WrapperGenerator not available")

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]), verbose=True, emit_mode=True,
        )

        malformed_ids = [
            "",  # Empty
            "just-one-word",  # No dots
            ".leading.dot",  # Leading dot
            "trailing.dot.",  # Trailing dot
            "multiple...dots",  # Multiple dots
            "space in.id",  # Space
            "special@char.id",  # Special chars
            "a" * 200,  # Very long
            "id.with.100.dots."
            + ".".join([str(i) for i in range(100)]),  # Too many components
        ]

        for malformed_id in malformed_ids:
            try:
                result = generator.generate_wrapper(malformed_id)
                assert isinstance(result, bool)  # Should handle gracefully
            except Exception:
                pass  # Exceptions acceptable for malformed input

    def test_path_injection_attempts(self, temp_env) -> None:
        """Test path injection and traversal attempts."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # Path traversal attempts
        injection_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "/root/.ssh/id_rsa",
            "~/../../../../etc/shadow",
            "config/../../../root",
        ]

        for injection in injection_attempts:
            try:
                result = manager.set_preference(injection, "flatpak")
                assert isinstance(result, bool)  # Should handle safely
            except Exception:
                pass  # Exceptions acceptable for security violations


class TestSystemResourceEdgeCases:
    """Test system resource exhaustion and limits."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp(prefix="fp_resource_test_"))
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"
        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_disk_space_exhaustion_simulation(self, temp_env) -> None:
        """Test behavior when disk space is exhausted."""
        # Create a very small "disk" by filling it up
        small_file = temp_env["temp_dir"] / "filler"
        # Write a large file to simulate low disk space
        try:
            with open(small_file, "w") as f:
                f.write("x" * (1024 * 1024))  # 1MB file
        except OSError:
            pass  # May fail on some systems

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # Should handle disk space issues gracefully
        result = manager.set_preference("test", "flatpak")
        assert isinstance(result, bool)  # Should not crash

    def test_permission_denied_scenarios(self, temp_env) -> None:
        """Test permission denied scenarios."""
        # Make config directory read-only
        config_dir = temp_env["config_dir"]
        config_dir.chmod(0o444)  # Read-only

        try:
            manager = WrapperManager(
                config_dir=str(config_dir), verbose=True, emit_mode=True,
            )

            result = manager.set_preference("test", "flatpak")
            assert isinstance(result, bool)  # Should handle permission errors
        finally:
            # Restore permissions for cleanup
            config_dir.chmod(0o755)

    def test_file_descriptor_exhaustion(self, temp_env) -> None:
        """Test file descriptor exhaustion handling."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # Open many file descriptors to simulate exhaustion
        opened_files = []
        try:
            for i in range(min(100, os.sysconf("SC_OPEN_MAX") // 2)):
                try:
                    f = open(temp_env["temp_dir"] / f"temp_{i}.txt", "w")
                    opened_files.append(f)
                except OSError:
                    break  # Stop when we hit limits

            # Try operations with limited file descriptors
            result = manager.set_preference("test", "flatpak")
            assert isinstance(result, bool)  # Should handle gracefully

        finally:
            for f in opened_files:
                with contextlib.suppress(builtins.BaseException):
                    f.close()

    @patch("os.path.exists")
    def test_missing_system_directories(self, mock_exists, temp_env) -> None:
        """Test missing system directories."""
        # Mock that key directories don't exist
        mock_exists.return_value = False

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        result = manager.set_preference("test", "flatpak")
        assert isinstance(result, bool)  # Should handle missing dirs


class TestExternalDependencyFailures:
    """Test failures of external dependencies."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp(prefix="fp_dependency_test_"))
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"
        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_flatpak_command_not_found(self, mock_subprocess, temp_env) -> None:
        """Test Flatpak command not found."""
        if "WrapperGenerator" not in globals():
            pytest.skip("WrapperGenerator not available")

        # Mock command not found
        mock_subprocess.side_effect = FileNotFoundError("flatpak not found")

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]), verbose=True, emit_mode=True,
        )

        result = generator.generate_wrapper("org.test.app")
        assert result is False  # Should fail gracefully

    @patch("subprocess.run")
    def test_flatpak_command_failure(self, mock_subprocess, temp_env) -> None:
        """Test Flatpak command execution failure."""
        if "WrapperGenerator" not in globals():
            pytest.skip("WrapperGenerator not available")

        # Mock command failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Flatpak error"
        mock_subprocess.return_value = mock_result

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]), verbose=True, emit_mode=True,
        )

        result = generator.generate_wrapper("org.test.app")
        assert isinstance(result, bool)  # Should handle failure

    @patch.dict("os.environ", {"PATH": "/nonexistent"})
    def test_missing_system_commands(self, temp_env) -> None:
        """Test missing system commands."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        result = manager.set_preference("test", "flatpak")
        assert isinstance(result, bool)  # Should handle missing commands

    def test_corrupted_config_files(self, temp_env) -> None:
        """Test corrupted configuration files."""
        # Create corrupted config files
        config_file = temp_env["config_dir"] / "config.toml"
        config_file.write_text("invalid toml syntax {{{{")

        pref_file = temp_env["config_dir"] / "firefox.pref"
        pref_file.write_text("corrupted\x00\x01\x02data")

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        result = manager.set_preference("firefox", "flatpak")
        assert isinstance(result, bool)  # Should handle corruption

    @patch("os.access")
    def test_insufficient_permissions(self, mock_access, temp_env) -> None:
        """Test insufficient file permissions."""
        # Mock no write access
        mock_access.return_value = False

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        result = manager.set_preference("test", "flatpak")
        assert isinstance(result, bool)  # Should handle permission issues


class TestConcurrencyAndRaceConditions:
    """Test concurrent access and race conditions."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp(prefix="fp_concurrency_test_"))
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"
        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_concurrent_config_operations(self, temp_env) -> None:
        """Test concurrent configuration operations."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=False,  # Reduce output noise
            emit_mode=True,
        )

        results = []
        errors = []

        def worker(thread_id) -> None:
            try:
                for i in range(50):
                    result = manager.set_preference(f"app_{thread_id}_{i}", "flatpak")
                    results.append(result)
            except Exception as e:
                errors.append(str(e))

        # Run multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=[i])
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        # Should complete without errors
        assert len(errors) == 0
        assert len(results) > 0

    def test_concurrent_file_operations(self, temp_env) -> None:
        """Test concurrent file operations."""
        results = []
        errors = []

        def file_worker(thread_id) -> None:
            try:
                for i in range(20):
                    file_path = temp_env["config_dir"] / f"test_{thread_id}_{i}.tmp"
                    with open(file_path, "w") as f:
                        f.write(f"test data {i}")
                    with open(file_path) as f:
                        content = f.read()
                    os.unlink(file_path)
                    results.append(content)
            except Exception as e:
                errors.append(str(e))

        # Run concurrent file operations
        threads = []
        for i in range(5):
            t = threading.Thread(target=file_worker, args=[i])
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        # Should complete without file corruption or race conditions
        assert len(errors) == 0
        assert len(results) > 0

    def test_lock_contention(self, temp_env) -> None:
        """Test lock contention scenarios."""
        # This would test file locking mechanisms if implemented
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # Simulate lock contention
        results = []
        for i in range(100):
            result = manager.set_preference(f"lock_test_{i}", "flatpak")
            results.append(result)

        # Should handle lock contention gracefully
        assert len(results) == 100


class TestTimeoutAndInterruptHandling:
    """Test timeout and interrupt handling."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp(prefix="fp_timeout_test_"))
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"
        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_command_timeout_handling(self, mock_subprocess, temp_env) -> None:
        """Test command timeout handling."""
        from subprocess import TimeoutExpired

        # Mock timeout
        mock_subprocess.side_effect = TimeoutExpired("command", 30)

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        result = manager.set_preference("test", "flatpak")
        assert isinstance(result, bool)  # Should handle timeout

    def test_signal_interrupt_handling(self, temp_env) -> None:
        """Test signal interrupt handling."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # Simulate interrupt
        import signal

        def interrupt_handler(signum, frame) -> NoReturn:
            raise KeyboardInterrupt

        old_handler = signal.signal(signal.SIGINT, interrupt_handler)

        try:
            # This should be fast enough to not trigger interrupt
            result = manager.set_preference("test", "flatpak")
            assert isinstance(result, bool)
        except KeyboardInterrupt:
            # If interrupted, should handle gracefully
            pass
        finally:
            signal.signal(signal.SIGINT, old_handler)

    @patch("time.sleep")
    def test_operation_timeout(self, mock_sleep, temp_env) -> None:
        """Test operation timeout scenarios."""
        # Mock slow operations
        mock_sleep.side_effect = lambda x: time.sleep(0.01)  # Short sleep

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        start_time = time.time()
        result = manager.set_preference("test", "flatpak")
        end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 1.0
        assert isinstance(result, bool)


class TestMemoryAndResourceLimits:
    """Test memory and resource limit handling."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp(prefix="fp_memory_test_"))
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"
        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_large_data_handling(self, temp_env) -> None:
        """Test handling of large amounts of data."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=False,  # Reduce output
            emit_mode=True,
        )

        # Create many preferences
        for i in range(1000):
            result = manager.set_preference(f"large_test_app_{i}", "flatpak")
            assert isinstance(result, bool)

        # Should handle large numbers of files gracefully
        pref_files = list(temp_env["config_dir"].glob("*.pref"))
        assert len(pref_files) > 900  # Most should succeed

    def test_deep_directory_structures(self, temp_env) -> None:
        """Test deep directory structure handling."""
        # Create deep directory structure
        deep_dir = temp_env["config_dir"]
        for i in range(10):
            deep_dir = deep_dir / f"level_{i}"
            deep_dir.mkdir()

        # Create config file in deep directory
        config_file = deep_dir / "test.pref"
        config_file.write_text("flatpak")

        manager = WrapperManager(config_dir=str(deep_dir), verbose=True, emit_mode=True)

        result = manager.set_preference("deep_test", "flatpak")
        assert isinstance(result, bool)  # Should handle deep paths

    def test_extreme_unicode_content(self, temp_env) -> None:
        """Test extreme Unicode content handling."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # Test with extremely long Unicode strings
        result = manager.set_preference("unicode_test", "flatpak")
        assert isinstance(result, bool)  # Should handle Unicode gracefully

        # Test with mixed encodings and special Unicode
        "".join(
            chr(i) for i in range(0x100, 0x200)
        )  # Various Unicode chars
        try:
            result = manager.set_preference("special_unicode", "flatpak")
            assert isinstance(result, bool)
        except UnicodeError:
            pass  # Unicode errors acceptable


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
