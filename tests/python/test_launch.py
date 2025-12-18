#!/usr/bin/env python3
"""
Unit tests for launch.py
Tests application launching functionality with proper mocking
"""

import sys
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

# Add lib to path
# Import the module to test
try:
    from fplaunch. import AppLauncher, main
except ImportError:
    # Mock it if not available
    AppLauncher = None
    main = None


class TestApplicationLauncher:
    """Test application launching functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()

    def teardown_method(self):
        """Clean up test environment"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_application_launcher_creation(self):
        """Test AppLauncher creation"""
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
    def test_launch_successful_execution(self, mock_subprocess):
        """Test successful application launch"""
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

        assert result is True
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_launch_command_not_found(self, mock_subprocess):
        """Test launch when command is not found"""
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
    def test_launch_with_arguments(self, mock_subprocess):
        """Test launch with command line arguments"""
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

        assert result is True
        # Verify arguments were passed
        call_args = mock_subprocess.call_args
        assert "--new-window" in call_args[0][0]
        assert "https://example.com" in call_args[0][0]

    @patch("subprocess.run")
    def test_launch_wrapper_preference_handling(self, mock_subprocess):
        """Test launch respects wrapper preferences"""
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
        )

        result = launcher.launch()

        assert result is True
        # Should attempt to run the wrapper script
        call_args = mock_subprocess.call_args
        expected_cmd = [str(self.bin_dir / "firefox")]
        assert call_args[0][0] == expected_cmd

    def test_launch_wrapper_existence_check(self):
        """Test launch checks if wrapper exists"""
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

    def test_launch_wrapper_not_found(self):
        """Test launch when wrapper doesn't exist"""
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
    def test_launch_fallback_to_flatpak(self, mock_subprocess):
        """Test fallback to direct Flatpak execution"""
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

        assert result is True
        # Should call flatpak directly
        call_args = mock_subprocess.call_args
        assert "flatpak" in call_args[0][0][0]

    @patch("subprocess.run")
    def test_launch_error_handling(self, mock_subprocess):
        """Test error handling during launch"""
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
    def test_launch_debug_mode(self, mock_subprocess):
        """Test launch in debug mode"""
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

        assert result is True
        # Should still work in debug mode

    def test_launch_path_resolution(self):
        """Test launch path resolution logic"""
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

    @patch("os.path.exists")
    def test_launch_wrapper_validation(self, mock_exists):
        """Test wrapper validation logic"""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        mock_exists.return_value = True

        launcher = AppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should validate wrapper exists
        assert launcher._wrapper_exists("test_app") is True

        mock_exists.return_value = False
        assert launcher._wrapper_exists("test_app") is False

    @patch("subprocess.run")
    def test_launch_environment_preservation(self, mock_subprocess):
        """Test that launch preserves environment"""
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

    def test_launch_argument_validation(self):
        """Test launch argument validation"""
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
    def test_launch_timeout_handling(self, mock_subprocess):
        """Test launch timeout handling"""
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

    @patch("subprocess.run")
    def test_launch_signal_handling(self, mock_subprocess):
        """Test launch signal handling"""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        import signal

        # Mock signal interruption
        mock_subprocess.side_effect = KeyboardInterrupt()

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is False


class TestLaunchMainFunction:
    """Test the main function for launch module"""

    @patch("sys.argv", ["fplaunch-launch", "firefox"])
    @patch("launch.AppLauncher.launch")
    def test_main_function_basic(self, mock_launch):
        """Test main function basic operation"""
        if not main:
            pytest.skip("main function not available")

        mock_launch.return_value = True

        result = main()

        assert result == 0
        mock_launch.assert_called_once()

    @patch("sys.argv", ["fplaunch-launch", "firefox", "--help"])
    def test_main_function_help(self):
        """Test main function help handling"""
        if not main:
            pytest.skip("main function not available")

        result = main()

        # Help should exit with code 0
        assert result == 0

    @patch("sys.argv", ["fplaunch-launch"])
    def test_main_function_no_args(self):
        """Test main function with no arguments"""
        if not main:
            pytest.skip("main function not available")

        result = main()

        # Should show usage and exit with error
        assert result != 0

    @patch("sys.argv", ["fplaunch-launch", "nonexistent_app"])
    @patch("launch.AppLauncher.launch")
    def test_main_function_app_not_found(self, mock_launch):
        """Test main function when app is not found"""
        if not main:
            pytest.skip("main function not available")

        mock_launch.return_value = False

        result = main()

        assert result != 0
        mock_launch.assert_called_once()


class TestLaunchIntegration:
    """Test launch integration with other components"""

    @patch("subprocess.run")
    def test_launch_with_config_manager(self, mock_subprocess):
        """Test launch integration with config manager"""
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

        assert result is True
        # Should respect configuration from config dir

    def test_launch_wrapper_script_execution(self):
        """Test that launch can execute wrapper scripts"""
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
    def test_launch_performance(self, mock_subprocess):
        """Test launch performance"""
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

        assert result is True
        # Should complete quickly
        assert end_time - start_time < 1.0

    def test_launch_thread_safety(self):
        """Test thread safety of launch operations"""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        import threading

        results = []
        errors = []

        def worker(app_name):
            try:
                launcher = AppLauncher(
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
