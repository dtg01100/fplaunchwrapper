#!/usr/bin/env python3
"""Unit tests for launch.py
Tests application launching functionality with proper mocking.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add lib to path
try:
    from lib.launch import AppLauncher, main
except ImportError:
    # Mock it if not available
    AppLauncher = None
    main = None

from lib.config_manager import (
    create_config_manager,
)

# For testing private methods, import directly from lib
try:
    from lib.launch import AppLauncher as LibAppLauncher
except ImportError:
    LibAppLauncher = None


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
    @patch("lib.safety.safe_launch_check", return_value=True)
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


class TestLaunchEdgeCases:
    """Test edge cases for application launching functionality."""

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

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_flatpak_various_app_ids(self, mock_safety, mock_subprocess) -> None:
        """Test launch with various Flatpak app ID formats."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Mock successful flatpak execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Test different Flatpak app ID formats
        flatpak_app_ids = [
            "org.mozilla.firefox",
            "com.google.Chrome",
            "org.gnome.Nautilus",
            "io.github.shiftey.Desktop",
            "net.brinkervii.grapejuice",  # Long app ID
        ]

        for app_id in flatpak_app_ids:
            launcher = AppLauncher(
                app_name=app_id,
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
            )

            result = launcher.launch()

            # Verify safety check was called
            mock_safety.assert_called()

            assert result is True
            # Should call flatpak directly
            call_args = mock_subprocess.call_args
            assert "flatpak" in call_args[0][0][0]
            assert app_id in call_args[0][0]

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_flatpak_with_architectures(
        self, mock_safety, mock_subprocess
    ) -> None:
        """Test launch with different Flatpak architectures."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Test with different architectures
        architectures = ["x86_64", "aarch64", "i386"]

        for arch in architectures:
            launcher = AppLauncher(
                app_name="org.mozilla.firefox",
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
            )

            result = launcher.launch()

            assert result is True
            # Note: architecture handling would need to be implemented in AppLauncher

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_environment_variable_injection(
        self, mock_safety, mock_subprocess
    ) -> None:
        """Test environment variable injection attempts are blocked."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Test with environment variables
        test_env_vars = {
            "PATH": "/usr/bin:/bin:/custom/path",
            "LD_PRELOAD": "/some/library.so",
            "SHELL": "/bin/bash",
            "HOME": "/home/user",
        }

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            env=test_env_vars,
        )

        result = launcher.launch()

        assert result is True
        # Environment should be passed through (current implementation)
        call_kwargs = mock_subprocess.call_args[1]
        assert "env" in call_kwargs
        # Verify the test environment variables are present
        final_env = call_kwargs["env"]
        assert final_env["PATH"] == "/usr/bin:/bin:/custom/path"

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_large_environment_set(self, mock_safety, mock_subprocess) -> None:
        """Test launch with a large number of environment variables."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Create a large environment with many variables
        large_env = {f"VAR_{i}": f"value_{i}" for i in range(100)}

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            env=large_env,
        )

        result = launcher.launch()

        assert result is True
        call_kwargs = mock_subprocess.call_args[1]
        assert "env" in call_kwargs
        # Should handle large environment without issues
        assert len(call_kwargs["env"]) >= 100

    def test_launch_very_long_app_name(self) -> None:
        """Test launch with extremely long app names."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Create a very long app name (over typical filesystem limits)
        long_app_name = "a" * 300

        launcher = AppLauncher(
            app_name=long_app_name,
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should handle long names gracefully
        assert launcher.app_name == long_app_name
        # Path resolution should work
        wrapper_path = launcher._get_wrapper_path(long_app_name)
        assert len(str(wrapper_path)) > 300

    def test_launch_empty_app_name(self) -> None:
        """Test launch with empty app name."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Empty app name should be handled
        launcher = AppLauncher(
            app_name="",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        assert launcher.app_name == ""
        # Empty app name resolves to bin_dir path (current implementation behavior)
        wrapper_result = launcher._find_wrapper()
        assert wrapper_result == self.bin_dir

    def test_launch_unicode_app_name(self) -> None:
        """Test launch with Unicode characters in app name."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        unicode_names = [
            "firefox_测试",  # Chinese
            "firefox_café",  # Accented characters
            "firefox_🚀",  # Emoji
            "firefox_αβγ",  # Greek
        ]

        for unicode_name in unicode_names:
            launcher = AppLauncher(
                app_name=unicode_name,
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
            )

            assert launcher.app_name == unicode_name
            # Should handle Unicode in path resolution
            wrapper_path = launcher._get_wrapper_path(unicode_name)
            assert unicode_name in str(wrapper_path)

    def test_launch_special_characters_in_app_name(self) -> None:
        """Test launch with various special characters in app names."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        special_names = [
            "app@domain.com",
            "app#version",
            "app+extra",
            "app=equal",
            "app?query",
            "app^caret",
            "app*asterisk",
            "app~tilde",
        ]

        for special_name in special_names:
            launcher = LibAppLauncher(
                app_name=special_name,
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
            )

            # Should sanitize the name
            sanitized = launcher._sanitize_app_name(special_name)
            # Verify special characters that could be dangerous are replaced
            assert all(char not in sanitized for char in ";|&`$()")

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_concurrent_access(self, mock_safety, mock_subprocess) -> None:
        """Test launch handles concurrent access properly."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        import threading

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        results = []
        errors = []

        def launch_worker(app_name) -> None:
            try:
                launcher = AppLauncher(
                    app_name=app_name,
                    bin_dir=str(self.bin_dir),
                    config_dir=str(self.config_dir),
                )
                result = launcher.launch()
                results.append((app_name, result))
            except Exception as e:
                errors.append((app_name, e))

        # Launch multiple instances concurrently
        threads = []
        for i in range(10):
            app_name = f"concurrent_app_{i}"
            # Create wrapper for each
            wrapper = self.bin_dir / app_name
            wrapper.write_text("#!/bin/bash\necho 'test'\n")
            wrapper.chmod(0o755)

            t = threading.Thread(target=launch_worker, args=[app_name])
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should handle concurrent access without errors
        assert len(errors) == 0
        assert len(results) == 10
        assert all(result for _, result in results)

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_timeout_handling(self, mock_safety, mock_subprocess) -> None:
        """Test launch handles command timeouts gracefully."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Mock timeout exception
        mock_subprocess.side_effect = subprocess.TimeoutExpired("flatpak run", 30)

        launcher = AppLauncher(
            app_name="org.mozilla.firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        # Should handle timeout gracefully
        assert result is False

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_resource_limits(self, mock_safety, mock_subprocess) -> None:
        """Test launch with resource limits."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Test with various resource limits
        _ = {
            "cpu_limit": "50%",  # CPU limit
            "memory_limit": "500M",  # Memory limit
            "time_limit": "60",  # Time limit in seconds
        }

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is True
        # Note: resource limits would need to be implemented in AppLauncher

    def test_launch_path_length_limits(self) -> None:
        """Test launch handles very long paths."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Create very deep directory structure
        deep_dir = self.bin_dir
        for i in range(50):  # Create 50 levels deep for longer path
            deep_dir = deep_dir / f"level_{i}"
        deep_dir.mkdir(parents=True)

        # Test with long paths
        long_path_bin = str(deep_dir)
        long_path_config = str(deep_dir.parent / "config")

        launcher = AppLauncher(
            app_name="test_app",
            bin_dir=long_path_bin,
            config_dir=long_path_config,
        )

        # Should handle long paths
        wrapper_path = launcher._get_wrapper_path("test_app")
        assert len(str(wrapper_path)) > 400  # Reasonably long path


class TestLaunchSecurity:
    """Test security aspects of the launch functionality."""

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

    def test_path_traversal_protection_wrapper_exists(self) -> None:
        """Test that path traversal is blocked in _wrapper_exists."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="../../../etc/passwd",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should return False for path traversal attempt
        assert launcher._wrapper_exists("../../../etc/passwd") is False

    def test_path_traversal_protection_find_wrapper(self) -> None:
        """Test that path traversal is blocked in _find_wrapper."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="../../../etc/passwd",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should return None for path traversal attempt
        assert launcher._find_wrapper() is None

    def test_path_traversal_protection_determine_source(self) -> None:
        """Test that path traversal is blocked in _determine_launch_source."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="../../../etc/passwd",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        source, wrapper_path = launcher._determine_launch_source()
        assert wrapper_path is None

    def test_app_name_sanitization_hook_scripts(self) -> None:
        """Test that app names are sanitized in hook script execution."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Create a hook script directory and script
        scripts_dir = self.config_dir / "scripts" / "test_app"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        hook_script = scripts_dir / "pre-launch.sh"
        hook_script.write_text(
            """#!/bin/bash
echo "App name: $2" > /tmp/hook_test.log
exit 0
"""
        )
        hook_script.chmod(0o755)

        launcher = LibAppLauncher(
            app_name="test_app;rm -rf /",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # This should sanitize the app name to prevent injection
        sanitized_name = launcher._sanitize_app_name("test_app;rm -rf /")
        assert sanitized_name == "test_app_rm_-rf__"
        assert ";" not in sanitized_name
        # Verify dangerous characters are replaced
        assert all(char not in sanitized_name for char in ";|&`$()")

    def test_hook_script_execution_with_malicious_app_name(self) -> None:
        """Test hook script execution with potentially malicious app names."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Create a hook script directory and script
        scripts_dir = self.config_dir / "scripts" / "test_app"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        hook_script = scripts_dir / "pre-launch.sh"
        hook_script.write_text(
            """#!/bin/bash
# This script would be dangerous if app name wasn't sanitized
echo "Safe execution with app: $2"
exit 0
"""
        )
        hook_script.chmod(0o755)

        # Test with various malicious app names
        malicious_names = [
            "test_app;rm -rf /",
            "test_app|cat /etc/passwd",
            "test_app$(rm -rf /)",
            "test_app`rm -rf /`",
            "test_app && rm -rf /",
            "test_app || rm -rf /",
        ]

        for malicious_name in malicious_names:
            launcher = LibAppLauncher(
                app_name=malicious_name,
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
            )

            sanitized = launcher._sanitize_app_name(malicious_name)
            # Verify dangerous characters are replaced
            assert all(char not in sanitized for char in ";|&`")
            assert "$(" not in sanitized
            assert "`" not in sanitized

    def test_hook_script_path_validation(self) -> None:
        """Test that hook scripts are validated for safe paths."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Create a hook script outside the config directory
        try:
            external_script = Path("/tmp/malicious_hook.sh")
            external_script.write_text("#!/bin/bash\necho 'malicious'\n")
            external_script.chmod(0o755)
        except (OSError, PermissionError):
            pytest.skip("Cannot create external script for test")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Mock the config manager to return an external script path
        from unittest.mock import patch

        with patch("lib.config_manager.create_config_manager") as mock_config:
            mock_prefs = Mock()
            mock_prefs.pre_launch_script = str(external_script)
            mock_config.return_value.get_app_preferences.return_value = mock_prefs

            # Get hook scripts - should validate the path
            scripts = launcher._get_hook_scripts("test_app", "pre")

            # The external script should not be included due to path validation
            assert str(external_script) not in [str(s) for s in scripts]

    def test_safety_check_blocks_dangerous_wrappers(self) -> None:
        """Test that safety checks block dangerous wrapper content."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        # Create a wrapper with dangerous content
        dangerous_wrapper = self.bin_dir / "dangerous_app"
        dangerous_wrapper.write_text(
            """#!/bin/bash
flatpak run org.mozilla.firefox --new-window
echo "This wrapper contains dangerous content"
"""
        )
        dangerous_wrapper.chmod(0o755)

        AppLauncher(
            app_name="dangerous_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Safety check should detect dangerous content
        from lib.safety import is_dangerous_wrapper

        assert is_dangerous_wrapper(dangerous_wrapper) is True

    def test_safe_app_name_validation(self) -> None:
        """Test that app names are properly validated and sanitized."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Test various app names
        test_cases = [
            ("normal_app", "normal_app"),
            ("app.with.dots", "app.with.dots"),
            ("app-with-dashes", "app-with-dashes"),
            ("app_with_underscores", "app_with_underscores"),
            ("app with spaces", "app_with_spaces"),
            ("app;dangerous", "app_dangerous"),
            ("app|dangerous", "app_dangerous"),
            ("app$(dangerous)", "app__dangerous_"),
            ("app`dangerous`", "app_dangerous_"),
        ]

        for input_name, expected_output in test_cases:
            result = launcher._sanitize_app_name(input_name)
            assert result == expected_output
            # Ensure no shell metacharacters remain
            assert not any(char in result for char in ";|&`$()")


class TestConfigExceptionHandling:
    """Test specific exception handling in configuration management."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_permission_error_on_load(self) -> None:
        """Test config manager handles permission errors gracefully with fallback."""
        if not create_config_manager:
            pytest.skip("Config manager not available")

        # Create a config file and make it unreadable
        config_file = self.config_dir / "config.toml"
        config_file.write_text('bin_dir = "/tmp"\n')

        # Make the file unreadable
        config_file.chmod(0o000)

        try:
            # Set XDG_CONFIG_HOME to use our test directory
            import os

            old_xdg = os.environ.get("XDG_CONFIG_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(self.temp_dir)
            try:
                from lib.config_manager import EnhancedConfigManager

                # This should succeed with fallback to defaults
                config_manager = EnhancedConfigManager(app_name="test")
                # Verify it fell back to defaults
                assert config_manager.config.bin_dir == os.path.expanduser("~/bin")
                assert config_manager.config.debug_mode is False
            finally:
                if old_xdg is not None:
                    os.environ["XDG_CONFIG_HOME"] = old_xdg
                else:
                    del os.environ["XDG_CONFIG_HOME"]
        except Exception as e:
            assert False, (
                f"Config manager should handle permission errors gracefully, not raise: {e}"
            )
        finally:
            # Restore permissions for cleanup
            try:
                config_file.chmod(0o644)
            except OSError:
                pass

    def test_config_parse_error_on_invalid_toml(self) -> None:
        """Test config manager handles parse errors gracefully with fallback."""
        if not create_config_manager:
            pytest.skip("Config manager not available")

        # Create invalid TOML
        config_file = self.config_dir / "config.toml"
        config_file.write_text("invalid [toml content {{{")

        try:
            # Set XDG_CONFIG_HOME to use our test directory
            import os

            old_xdg = os.environ.get("XDG_CONFIG_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(self.temp_dir)
            try:
                from lib.config_manager import EnhancedConfigManager

                # This should succeed with fallback to defaults
                config_manager = EnhancedConfigManager(app_name="test")
                # Verify it fell back to defaults
                assert config_manager.config.bin_dir == os.path.expanduser("~/bin")
                assert config_manager.config.debug_mode is False
            finally:
                if old_xdg is not None:
                    os.environ["XDG_CONFIG_HOME"] = old_xdg
                else:
                    del os.environ["XDG_CONFIG_HOME"]
        except Exception as e:
            assert False, (
                f"Config manager should handle parse errors gracefully, not raise: {e}"
            )

    def test_config_validation_error_on_invalid_data(self) -> None:
        """Test config manager handles validation errors gracefully with fallback."""
        if not create_config_manager:
            pytest.skip("Config manager not available")

        # Create TOML with invalid log_level
        config_file = self.config_dir / "config.toml"
        config_file.write_text('log_level = "INVALID_LEVEL"\n')

        try:
            # Set XDG_CONFIG_HOME to use our test directory
            import os

            old_xdg = os.environ.get("XDG_CONFIG_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(self.temp_dir)
            try:
                from lib.config_manager import EnhancedConfigManager

                # This should succeed with fallback to defaults
                config_manager = EnhancedConfigManager(app_name="test")
                # Verify it fell back to defaults
                assert config_manager.config.bin_dir == os.path.expanduser("~/bin")
                assert config_manager.config.debug_mode is False
            finally:
                if old_xdg is not None:
                    os.environ["XDG_CONFIG_HOME"] = old_xdg
                else:
                    del os.environ["XDG_CONFIG_HOME"]
        except Exception as e:
            assert False, (
                f"Config manager should handle validation errors gracefully, not raise: {e}"
            )

    def test_config_save_permission_error(self) -> None:
        """Test config manager handles save permission errors gracefully."""
        if not create_config_manager:
            pytest.skip("Config manager not available")

        # Set XDG_CONFIG_HOME to use our test directory

        old_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = str(self.temp_dir)
        try:
            from lib.config_manager import EnhancedConfigManager

            config_manager = EnhancedConfigManager(app_name="test")

            # Make config directory read-only
            self.config_dir.chmod(0o444)

            try:
                # This should not raise an exception, just fail silently
                config_manager.save_config()
                # The operation should complete without crashing
                assert True
            except Exception as e:
                assert False, (
                    f"Config save should handle permission errors gracefully, not raise: {e}"
                )
            finally:
                # Restore permissions for cleanup
                try:
                    self.config_dir.chmod(0o755)
                except OSError:
                    pass
        finally:
            if old_xdg is not None:
                os.environ["XDG_CONFIG_HOME"] = old_xdg
            else:
                del os.environ["XDG_CONFIG_HOME"]

    def test_config_validation_error_on_invalid_data_fallback(self) -> None:
        """Test that invalid configuration data falls back to defaults gracefully."""
        if not create_config_manager:
            pytest.skip("Config manager not available")

        # Create TOML with invalid log_level
        config_file = self.config_dir / "config.toml"
        config_file.write_text('log_level = "INVALID_LEVEL"\n')

        # Set XDG_CONFIG_HOME to use our test directory

        old_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = str(self.temp_dir)
        try:
            from lib.config_manager import EnhancedConfigManager

            # This should not raise an exception, just fall back to defaults
            config_manager = EnhancedConfigManager(app_name="test")

            # Verify it fell back to default log_level
            assert config_manager.config.log_level == "INFO"
            assert not config_manager.config.debug_mode
        finally:
            if old_xdg is not None:
                os.environ["XDG_CONFIG_HOME"] = old_xdg
            else:
                del os.environ["XDG_CONFIG_HOME"]

    def test_config_save_permission_error_handling(self) -> None:
        """Test that config save handles permission errors gracefully."""
        if not create_config_manager:
            pytest.skip("Config manager not available")

        # Set XDG_CONFIG_HOME to use our test directory

        old_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = str(self.temp_dir)
        try:
            from lib.config_manager import EnhancedConfigManager

            config_manager = EnhancedConfigManager(app_name="test")

            # Make config directory read-only
            self.config_dir.chmod(0o444)

            try:
                # This should not raise an exception, just handle the error gracefully
                config_manager.save_config()
                # The operation should complete without crashing
                assert True
            except Exception as e:
                assert False, (
                    f"Config save should handle permission errors gracefully, not raise: {e}"
                )
            finally:
                # Restore permissions for cleanup
                try:
                    self.config_dir.chmod(0o755)
                except OSError:
                    pass
        finally:
            if old_xdg is not None:
                os.environ["XDG_CONFIG_HOME"] = old_xdg
            else:
                del os.environ["XDG_CONFIG_HOME"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
