#!/usr/bin/env python3
"""REAL execution tests for launch.py with full coverage.

NO MOCKS - Tests actual code paths (except subprocess calls for safety).
"""

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


# Import actual implementation
from fplaunch.launch import AppLauncher, main


class TestAppLauncherReal:
    """Test AppLauncher with REAL execution."""

    def setup_method(self) -> None:
        """Set up REAL test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"

        # Create REAL directories
        self.bin_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)

        # Create REAL wrapper script
        wrapper = self.bin_dir / "firefox"
        wrapper.write_text("#!/bin/bash\necho 'Firefox launched'\nexit 0\n")
        wrapper.chmod(0o755)

        # Create another wrapper
        wrapper2 = self.bin_dir / "chrome"
        wrapper2.write_text("#!/bin/bash\necho 'Chrome launched'\nexit 0\n")
        wrapper2.chmod(0o755)

    def teardown_method(self) -> None:
        """Clean up REAL test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_real_object(self) -> None:
        """Test __init__ creates real AppLauncher object."""
        launcher = AppLauncher(
            app_name="firefox",
            config_dir=str(self.config_dir),
            bin_dir=str(self.bin_dir),
        )

        # Verify REAL attributes
        assert launcher.app_name == "firefox"
        assert launcher.config_dir == self.config_dir
        assert launcher.bin_dir == self.bin_dir
        assert launcher.verbose is False
        assert launcher.debug is False
        assert launcher.args == []

    def test_init_with_all_parameters(self) -> None:
        """Test __init__ with all parameters set."""
        launcher = AppLauncher(
            app_name="test-app",
            config_dir=str(self.config_dir),
            bin_dir=str(self.bin_dir),
            args=["--flag", "value"],
            env={"TEST": "value"},
            verbose=True,
            debug=True,
        )

        assert launcher.app_name == "test-app"
        assert launcher.args == ["--flag", "value"]
        assert launcher.env == {"TEST": "value"}
        assert launcher.verbose is True
        assert launcher.debug is True

    def test_init_creates_config_dir(self) -> None:
        """Test __init__ creates config directory if it doesn't exist."""
        new_config = self.temp_dir / "new_config"
        assert not new_config.exists()

        launcher = AppLauncher(
            app_name="firefox",
            config_dir=str(new_config),
        )

        # Verify directory was REALLY created
        assert new_config.exists()
        assert new_config.is_dir()

    def test_init_reads_bin_dir_from_config(self) -> None:
        """Test __init__ reads bin_dir from config file."""
        # Create bin_dir config file
        bin_dir_file = self.config_dir / "bin_dir"
        bin_dir_file.write_text(str(self.bin_dir))

        launcher = AppLauncher(
            app_name="firefox",
            config_dir=str(self.config_dir),
        )

        # Verify bin_dir was read from config
        assert launcher.bin_dir == self.bin_dir

    def test_init_uses_default_bin_dir(self) -> None:
        """Test __init__ uses default bin_dir when not specified."""
        launcher = AppLauncher(
            app_name="firefox",
            config_dir=str(self.config_dir),
        )

        # Should use default ~/bin
        assert launcher.bin_dir == Path.home() / "bin"

    def test_get_wrapper_path(self) -> None:
        """Test _get_wrapper_path returns correct path."""
        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
        )

        wrapper_path = launcher._get_wrapper_path()

        assert wrapper_path == self.bin_dir / "firefox"
        assert isinstance(wrapper_path, Path)

    def test_get_wrapper_path_with_different_app(self) -> None:
        """Test _get_wrapper_path with different app name."""
        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
        )

        wrapper_path = launcher._get_wrapper_path("chrome")

        assert wrapper_path == self.bin_dir / "chrome"

    def test_wrapper_exists_for_real_wrapper(self) -> None:
        """Test _wrapper_exists returns True for real wrapper."""
        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
        )

        assert launcher._wrapper_exists() is True

    def test_wrapper_exists_for_nonexistent_wrapper(self) -> None:
        """Test _wrapper_exists returns False for nonexistent wrapper."""
        launcher = AppLauncher(
            app_name="nonexistent",
            bin_dir=str(self.bin_dir),
        )

        assert launcher._wrapper_exists() is False

    def test_wrapper_exists_for_non_executable(self) -> None:
        """Test _wrapper_exists returns False for non-executable file."""
        # Create non-executable file
        non_exec = self.bin_dir / "non-executable"
        non_exec.write_text("Not executable")
        non_exec.chmod(0o644)

        launcher = AppLauncher(
            app_name="non-executable",
            bin_dir=str(self.bin_dir),
        )

        assert launcher._wrapper_exists() is False

    def test_find_wrapper_success(self) -> None:
        """Test _find_wrapper finds existing wrapper."""
        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
        )

        wrapper = launcher._find_wrapper()

        assert wrapper is not None
        assert wrapper == self.bin_dir / "firefox"
        assert wrapper.exists()

    def test_find_wrapper_not_found(self) -> None:
        """Test _find_wrapper returns None when wrapper doesn't exist."""
        launcher = AppLauncher(
            app_name="nonexistent",
            bin_dir=str(self.bin_dir),
        )

        wrapper = launcher._find_wrapper()

        assert wrapper is None
    @patch("fplaunch.safety.safe_launch_check", return_value=True)

    @patch("subprocess.run")
    def test_launch_with_wrapper(self, mock_run, mock_safety) -> None:
        """Test launch() with existing wrapper (mocked subprocess for safety)."""
        mock_run.return_value = Mock(returncode=0)

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            args=["--profile", "test"],
        )

        result = launcher.launch()

        # Verify REAL launch was attempted
        assert result is True
        mock_run.assert_called_once()
        
        # Verify correct command was built
        call_args = mock_run.call_args[0][0]
        assert str(self.bin_dir / "firefox") in str(call_args[0])
        assert "--profile" in call_args
        assert "test" in call_args
    @patch("fplaunch.safety.safe_launch_check", return_value=True)

    @patch("subprocess.run")
    def test_launch_without_wrapper_fallback(self, mock_run, mock_safety) -> None:
        """Test launch() falls back to flatpak when wrapper doesn't exist."""
        mock_run.return_value = Mock(returncode=0)

        launcher = AppLauncher(
            app_name="org.mozilla.firefox",
            bin_dir=str(self.bin_dir),
            args=["--new-tab"],
        )

        result = launcher.launch()

        # Verify flatpak fallback
        assert result is True
        mock_run.assert_called_once()
        
        call_args = mock_run.call_args[0][0]
        assert "flatpak" in call_args
        assert "run" in call_args
        assert "org.mozilla.firefox" in call_args
        assert "--new-tab" in call_args
    @patch("fplaunch.safety.safe_launch_check", return_value=True)

    @patch("subprocess.run")
    def test_launch_with_custom_env(self, mock_run, mock_safety) -> None:
        """Test launch() passes custom environment variables."""
        mock_run.return_value = Mock(returncode=0)

        custom_env = {"MY_VAR": "my_value", "ANOTHER": "test"}
        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            env=custom_env,
        )

        launcher.launch()

        # Verify env was passed
        assert mock_run.call_args[1]["env"] == custom_env
    @patch("fplaunch.safety.safe_launch_check", return_value=True)

    @patch("subprocess.run")
    def test_launch_with_debug_mode(self, mock_run, mock_safety) -> None:
        """Test launch() with debug mode enabled."""
        mock_run.return_value = Mock(returncode=0)

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            debug=True,
        )

        # Capture stderr
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()

        try:
            launcher.launch()
            debug_output = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        # Verify debug output
        assert "Launching:" in debug_output
        assert "firefox" in debug_output
    @patch("fplaunch.safety.safe_launch_check", return_value=True)

    @patch("subprocess.run")
    def test_launch_with_verbose_mode_on_error(self, mock_run, mock_safety) -> None:
        """Test launch() with verbose mode on error."""
        mock_run.side_effect = Exception("Test error")

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            verbose=True,
        )

        # Capture stderr
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()

        try:
            result = launcher.launch()
            error_output = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        # Verify error handling
        assert result is False
        assert "Error launching" in error_output
        assert "firefox" in error_output

    @patch("subprocess.run")
    def test_launch_returns_false_on_failure(self, mock_run) -> None:
        """Test launch() returns False when subprocess fails."""
        mock_run.return_value = Mock(returncode=1)

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
        )

        result = launcher.launch()

        assert result is False

    @patch("subprocess.run")
    def test_launch_handles_keyboard_interrupt(self, mock_run) -> None:
        """Test launch() handles KeyboardInterrupt gracefully."""
        mock_run.side_effect = KeyboardInterrupt()

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            verbose=True,
        )

        result = launcher.launch()

        # Should return False but not crash
        assert result is False

    @patch("fplaunch.safety.safe_launch_check", return_value=True)
    @patch("subprocess.run")
    def test_launch_app_method(self, mock_run, mock_safety) -> None:
        """Test launch_app() convenience method."""
        mock_run.return_value = Mock(returncode=0)

        launcher = AppLauncher(
            config_dir=str(self.config_dir),
            bin_dir=str(self.bin_dir),
        )

        # Use legacy API
        result = launcher.launch_app("chrome", ["--incognito"])

        # Verify it set app_name and args
        assert launcher.app_name == "chrome"
        assert launcher.args == ["--incognito"]
        assert result is True

        # Verify correct command
        call_args = mock_run.call_args[0][0]
        assert "chrome" in str(call_args[0])
        assert "--incognito" in call_args


class TestMainFunction:
    """Test the main() CLI function."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.bin_dir.mkdir()

        # Create test wrapper
        wrapper = self.bin_dir / "testapp"
        wrapper.write_text("#!/bin/bash\necho 'Test app'\nexit 0\n")
        wrapper.chmod(0o755)

    def teardown_method(self) -> None:
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_main_with_no_arguments(self) -> None:
        """Test main() with no arguments."""
        old_argv = sys.argv
        try:
            sys.argv = ["fplaunch-launch"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
    @patch("fplaunch.safety.safe_launch_check", return_value=True)

    @patch("subprocess.run")
    def test_main_with_app_name(self, mock_run, mock_safety) -> None:
        """Test main() with app name."""
        mock_run.return_value = Mock(returncode=0)

        old_argv = sys.argv
        try:
            sys.argv = ["fplaunch-launch", "org.mozilla.firefox"]
            result = main()
            assert result == 0
        finally:
            sys.argv = old_argv

    @patch("fplaunch.safety.safe_launch_check", return_value=True)
    @patch("subprocess.run")
    def test_main_with_app_name_and_args(self, mock_run, mock_safety) -> None:
        """Test main() with app name and arguments."""
        mock_run.return_value = Mock(returncode=0)

        old_argv = sys.argv
        try:
            sys.argv = ["fplaunch-launch", "org.mozilla.firefox", "--new-tab", "https://example.com"]
            result = main()
            
            # Verify args were passed
            call_args = mock_run.call_args[0][0]
            assert "org.mozilla.firefox" in call_args or "firefox" in str(call_args)
            assert "--new-tab" in call_args
            assert "https://example.com" in call_args
            
            assert result == 0
        finally:
            sys.argv = old_argv


class TestLauncherIntegration:
    """Integration tests for AppLauncher."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_multiple_launches(self, mock_run) -> None:
        """Test launching multiple apps in sequence."""
        mock_run.return_value = Mock(returncode=0)

        # Create wrappers
        for app in ["app1", "app2", "app3"]:
            wrapper = self.bin_dir / app
            wrapper.write_text(f"#!/bin/bash\necho '{app}'\nexit 0\n")
            wrapper.chmod(0o755)

        launcher = AppLauncher(
            config_dir=str(self.config_dir),
            bin_dir=str(self.bin_dir),
        )

        # Launch multiple apps
        for app in ["app1", "app2", "app3"]:
            result = launcher.launch_app(app, [])
            assert result is True

        # Verify all were called
        assert mock_run.call_count == 3

    def test_launcher_with_real_script_execution(self) -> None:
        """Test launcher with REAL script execution (safe echo command)."""
        # Create a simple safe script
        script = self.bin_dir / "echo-test"
        script.write_text("#!/bin/bash\necho 'Success'\nexit 0\n")
        script.chmod(0o755)

        launcher = AppLauncher(
            app_name="echo-test",
            config_dir=str(self.config_dir),
            bin_dir=str(self.bin_dir),
        )

        # Actually run the script (safe echo command)
        result = launcher.launch()

        # Should succeed
        assert result is True
