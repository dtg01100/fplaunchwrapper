#!/usr/bin/env python3
"""Minimal Safe Integration Test - Constructor and Basic Functionality Only.

Tests that classes can be instantiated and basic methods called without side effects.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import modules safely
try:
    from lib.cleanup import WrapperCleanup
    from lib.generate import WrapperGenerator
    from lib.launch import AppLauncher
    from lib.manage import WrapperManager
    from lib.systemd_setup import SystemdSetup

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
class TestSafeConstructorValidation:
    """Test that all classes can be constructed safely with proper parameters."""

    def test_wrapper_generator_constructor(self) -> None:
        """Test WrapperGenerator can be created safely."""
        with patch("subprocess.run") as mock_run, patch(
            "os.path.exists",
            return_value=True,
        ):
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Test correct constructor parameters
            generator = WrapperGenerator(
                bin_dir="/tmp/test_bin",
                verbose=False,
                emit_mode=True,
            )

            assert generator is not None
            assert hasattr(generator, "generate_wrapper")

            # Test that method can be called (should be mocked)
            result = generator.generate_wrapper("org.test.app")
            assert result is not None

    def test_wrapper_manager_constructor(self) -> None:
        """Test WrapperManager can be created safely."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Test correct constructor parameters
            manager = WrapperManager(
                config_dir="/tmp/test_config",
                verbose=False,
                emit_mode=True,
                emit_verbose=False,
            )

            assert manager is not None
            assert hasattr(manager, "set_preference")

            # Test that method can be called (should be mocked)
            result = manager.set_preference("test_app", "flatpak")
            assert result is not None

    def test_wrapper_cleanup_constructor(self) -> None:
        """Test WrapperCleanup can be created safely."""
        with patch("os.path.exists", return_value=True), patch("shutil.rmtree"):
            # Test correct constructor parameters
            cleaner = WrapperCleanup(
                bin_dir="/tmp/test_bin",
                config_dir="/tmp/test_config",
                dry_run=True,  # Safe mode - no actual cleanup
                assume_yes=False,
            )

            assert cleaner is not None
            assert hasattr(cleaner, "perform_cleanup")

            # Test that method can be called (should be mocked/safe)
            result = cleaner.perform_cleanup()
            assert result is not None

    def test_app_launcher_constructor(self) -> None:
        """Test AppLauncher can be created safely."""
        with patch("subprocess.run") as mock_run, patch(
            "subprocess.Popen",
        ) as mock_popen:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            mock_popen.return_value = Mock()

            # Test correct constructor parameters
            launcher = AppLauncher(config_dir="/tmp/test_config")

            assert launcher is not None
            assert hasattr(launcher, "launch_app")

            # Test that method can be called (should be mocked)
            result = launcher.launch_app("org.test.app")
            assert result is not None

    def test_systemd_setup_constructor(self) -> None:
        """Test SystemdSetup can be created safely."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Test correct constructor parameters
            systemd = SystemdSetup(
                bin_dir="/tmp/test_bin",
                wrapper_script="/tmp/test_script",
                emit_mode=True,
                emit_verbose=False,
            )

            assert systemd is not None
            assert hasattr(systemd, "install_systemd_units")

            # Test that method can be called (should be mocked)
            result = systemd.install_systemd_units()
            assert result is not None

    def test_complete_isolation_validation(self) -> None:
        """Test that no real system operations occur."""
        import os

        # Track current working directory
        original_cwd = os.getcwd()

        # Track environment variables that matter
        original_path = os.environ.get("PATH", "")
        original_home = os.environ.get("HOME", "")

        try:
            with patch("subprocess.run") as mock_run, patch(
                "subprocess.Popen",
            ) as mock_popen, patch("os.path.exists", return_value=True), patch(
                "os.makedirs",
            ), patch("shutil.rmtree"), patch("os.remove"):
                mock_run.return_value = Mock(returncode=0, stdout="safe", stderr="")
                mock_popen.return_value = Mock()

                # Create directories
                safe_config = Path("/tmp/safe_config")
                safe_config.mkdir(parents=True, exist_ok=True)
                safe_bin = Path("/tmp/safe_bin")
                safe_bin.mkdir(parents=True, exist_ok=True)

                # Create bin_dir file to avoid read error
                (safe_config / "bin_dir").write_text(str(safe_bin))

                # Create all component instances
                generator = WrapperGenerator(
                    "/tmp/safe_bin",
                    verbose=False,
                    emit_mode=True,
                )
                manager = WrapperManager(
                    config_dir="/tmp/safe_config",
                    verbose=False,
                    emit_mode=True,
                )
                cleaner = WrapperCleanup(bin_dir="/tmp/safe_bin", dry_run=True)
                launcher = AppLauncher(config_dir="/tmp/safe_config")
                systemd = SystemdSetup(bin_dir="/tmp/safe_bin", emit_mode=True)

                # Call methods that would normally do dangerous operations
                generator.generate_wrapper("safe.test.app")
                manager.set_preference("safe_app", "flatpak")
                cleaner.perform_cleanup()
                launcher.launch_app("safe.test.app")
                systemd.install_systemd_units()

                # Verify mocks were called (operations were intercepted)
                assert mock_run.call_count > 0, "External commands should be mocked"

                # Verify working directory unchanged
                assert os.getcwd() == original_cwd, (
                    "Working directory should not change"
                )

                # Verify environment unchanged
                assert os.environ.get("PATH", "") == original_path, (
                    "PATH should not change"
                )
                assert os.environ.get("HOME", "") == original_home, (
                    "HOME should not change"
                )

        finally:
            # Restore if anything went wrong (defensive)
            os.chdir(original_cwd)
