#!/usr/bin/env python3
"""Unit tests for launch.py
Tests application launching functionality with proper mocking.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add lib to path
try:
    from fplaunch.launch import AppLauncher, main
except ImportError:
    # Mock it if not available
    AppLauncher = None
    main = None


class TestApplicationLauncher:
    """Test application launching functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_application_launcher_creation(self) -> None:
        """Test AppLauncher creation."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        assert launcher is not None
        assert launcher.app_name == "firefox"
        assert str(launcher.bin_dir) == str(self.bin_dir)
        assert str(launcher.config_dir) == str(self.config_dir)

    @patch("subprocess.run")
    @patch("fplaunch.safety.safe_launch_check", return_value=True)
    def test_launch_successful_execution(self, mock_safety, mock_subprocess) -> None:
        """Test successful application launch (safety mocked)."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Mock successful execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        # Verify safety check was called
        mock_safety.assert_called_once()
        
        assert result is True
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_launch_command_not_found(self, mock_subprocess) -> None:
        """Test launch when command is not found."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Mock command not found
        mock_subprocess.side_effect = FileNotFoundError("Command not found")

        launcher = AppLauncher(
            app_name="nonexistent_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is False

    @patch("subprocess.run")
    @patch("fplaunch.safety.safe_launch_check", return_value=True)
    def test_launch_with_arguments(self, mock_safety, mock_subprocess) -> None:
        """Test launch with command line arguments (safety mocked)."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Mock successful execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            args=["--new-window", "https://example.com"],
        )

        result = launcher.launch()

        # Verify safety check was called
        mock_safety.assert_called_once()
        
        assert result is True
        # Verify arguments were passed
        call_args = mock_subprocess.call_args
        assert "--new-window" in call_args[0][0]
        assert "https://example.com" in call_args[0][0]

    @patch("subprocess.run")
    @patch("fplaunch.safety.safe_launch_check", return_value=True)
    def test_launch_wrapper_preference_handling(self, mock_safety, mock_subprocess) -> None:
        """Test launch respects wrapper preferences (safety mocked)."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Create a mock wrapper script
        wrapper_script = self.bin_dir / "firefox"
        wrapper_script.write_text("#!/bin/bash\necho 'test'\n")
        wrapper_script.chmod(0o755)

        # Mock successful execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        # Verify safety check was called
        mock_safety.assert_called_once()
        
        assert result is True
        # Should attempt to run the wrapper script
        call_args = mock_subprocess.call_args
        expected_cmd = [str(self.bin_dir / "firefox")]
        assert call_args[0][0] == expected_cmd

    def test_launch_wrapper_existence_check(self) -> None:
        """Test launch checks if wrapper exists."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Create a wrapper script
        wrapper_path = self.bin_dir / "test_app"
        wrapper_path.write_text("#!/bin/bash\necho 'test app'\n")
        wrapper_path.chmod(0o755)

        launcher = AppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should find the wrapper
        assert launcher._find_wrapper() == wrapper_path

    def test_launch_wrapper_not_found(self) -> None:
        """Test launch when wrapper doesn't exist."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        launcher = AppLauncher(
            app_name="nonexistent_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should return None for missing wrapper
        assert launcher._find_wrapper() is None

    @patch("subprocess.run")
    @patch("fplaunch.safety.safe_launch_check", return_value=True)
    def test_launch_fallback_to_flatpak(self, mock_safety, mock_subprocess) -> None:
        """Test fallback to direct Flatpak execution (safety mocked)."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Mock flatpak command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="org.mozilla.firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Remove wrapper to force fallback
        wrapper_path = self.bin_dir / "org.mozilla.firefox"
        if wrapper_path.exists():
            wrapper_path.unlink()

        result = launcher.launch()

        # Verify safety check was called
        mock_safety.assert_called_once()
        
        assert result is True
        # Should call flatpak directly
        call_args = mock_subprocess.call_args
        assert "flatpak" in call_args[0][0][0]

    @patch("subprocess.run")
    def test_launch_error_handling(self, mock_subprocess) -> None:
        """Test error handling during launch."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Mock command failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Permission denied"
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is False

    @patch.dict("os.environ", {"FPWRAPPER_DEBUG": "1"})
    @patch("subprocess.run")
    @patch("fplaunch.safety.safe_launch_check", return_value=True)
    def test_launch_debug_mode(self, mock_safety, mock_subprocess) -> None:
        """Test launch in debug mode (safety mocked)."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        # Verify safety check was called
        mock_safety.assert_called_once()
        
        assert result is True
        # Should still work in debug mode

    def test_launch_path_resolution(self) -> None:
        """Test launch path resolution logic."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        launcher = AppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Test path resolution
        expected_path = self.bin_dir / "test_app"
        assert launcher._get_wrapper_path("test_app") == expected_path

    @patch("os.access")
    def test_launch_wrapper_validation(self, mock_access) -> None:
        """Test wrapper validation logic."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Create a wrapper file
        wrapper_script = self.bin_dir / "test_app"
        wrapper_script.write_text("#!/bin/bash\necho 'test'\n")
        wrapper_script.chmod(0o755)

        launcher = AppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should validate wrapper exists
        mock_access.return_value = True
        assert launcher._wrapper_exists("test_app") is True

        # Test when file doesn't exist
        mock_access.return_value = False
        assert launcher._wrapper_exists("nonexistent") is False

    @patch("subprocess.run")
    @patch("fplaunch.safety.safe_launch_check", return_value=True)
    def test_launch_environment_preservation(self, mock_safety, mock_subprocess) -> None:
        """Test that launch preserves environment (safety mocked)."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Set up environment
        test_env = {"TEST_VAR": "test_value"}

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            env=test_env,
        )

        result = launcher.launch()

        assert result is True
        # Check that env was passed
        call_kwargs = mock_subprocess.call_args[1]
        assert "env" in call_kwargs

    def test_launch_argument_validation(self) -> None:
        """Test launch argument validation."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Valid app names
        valid_names = ["firefox", "org.mozilla.firefox", "chrome", "vlc"]

        for app_name in valid_names:
            launcher = AppLauncher(
                app_name=app_name,
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
            )
            assert launcher.app_name == app_name

    @patch("subprocess.run")
    def test_launch_timeout_handling(self, mock_subprocess) -> None:
        """Test launch timeout handling."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        from subprocess import TimeoutExpired

        # Mock timeout
        mock_subprocess.side_effect = TimeoutExpired("timeout", 30)

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is False


class TestLaunchMainFunction:
    """Test the main function for launch module."""

    @patch("sys.argv", ["fplaunch-launch", "firefox"])
    @patch("fplaunch.launch.AppLauncher.launch")
    def test_main_function_basic(self, mock_launch) -> None:
        """Test main function basic operation."""
        if not main:
            pytest.skip("main function not available")

        mock_launch.return_value = True

        result = main()

        assert result == 0
        mock_launch.assert_called_once()

    @patch("sys.argv", ["fplaunch-launch", "firefox", "--help"])
    def test_main_function_help(self) -> None:
        """Test main function help handling."""
        if not main:
            pytest.skip("main function not available")

        result = main()

        # Help is not handled, so it fails
        assert result == 1

    @patch("sys.argv", ["fplaunch-launch"])
    def test_main_function_no_args(self) -> None:
        """Test main function with no arguments."""
        if not main:
            pytest.skip("main function not available")

        result = main()

        # Should show usage and exit with error
        assert result != 0

    @patch("sys.argv", ["fplaunch-launch", "nonexistent_app"])
    @patch("fplaunch.launch.AppLauncher.launch")
    def test_main_function_app_not_found(self, mock_launch) -> None:
        """Test main function when app is not found."""
        if not main:
            pytest.skip("main function not available")

        mock_launch.return_value = False

        result = main()

        assert result != 0
        mock_launch.assert_called_once()


class TestLaunchIntegration:
    """Test launch integration with other components."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    @patch("fplaunch.safety.safe_launch_check", return_value=True)
    def test_launch_with_config_manager(self, mock_safety, mock_subprocess) -> None:
        """Test launch integration with config manager (safety mocked)."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        # Verify safety check was called
        mock_safety.assert_called_once()
        
        assert result is True
        # Should respect configuration from config dir

    def test_launch_wrapper_script_execution(self) -> None:
        """Test that launch can execute wrapper scripts."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Create a test wrapper script
        wrapper_path = self.bin_dir / "test_wrapper"
        wrapper_path.write_text("""#!/bin/bash
echo "Wrapper executed with args: $@"
exit 0
""")
        wrapper_path.chmod(0o755)

        launcher = AppLauncher(
            app_name="test_wrapper",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should find and be able to execute the wrapper
        wrapper = launcher._find_wrapper()
        assert wrapper == wrapper_path
        assert wrapper.exists()
        assert os.access(wrapper, os.X_OK)

    @patch("subprocess.run")
    @patch("fplaunch.safety.safe_launch_check", return_value=True)
    def test_launch_performance(self, mock_safety, mock_subprocess) -> None:
        """Test launch performance (safety mocked)."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        import time

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        start_time = time.time()
        result = launcher.launch()
        end_time = time.time()

        # Verify safety check was called
        mock_safety.assert_called_once()
        
        assert result is True
        # Should complete quickly
        assert end_time - start_time < 1.0

    def test_launch_thread_safety(self) -> None:
        """Test thread safety of launch operations."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        import threading

        results = []
        errors = []

        def worker(app_name) -> None:
            try:
                AppLauncher(
                    app_name=app_name,
                    bin_dir=str(self.bin_dir),
                    config_dir=str(self.config_dir),
                )
                # Just test creation, not actual launch
                results.append(f"success_{app_name}")
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=[f"app{i}"])
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should not have threading errors
        assert len(errors) == 0
        assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
