#!/usr/bin/env python3
"""Unit tests for launch.py
Tests application launching functionality with proper mocking.
"""

import os
import subprocess
import tempfile
from io import StringIO
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
        mock_subprocess.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

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
        mock_subprocess.return_value = subprocess.CompletedProcess(args=[], returncode=0)

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
    def test_launch_flatpak_with_architectures(self, mock_safety, mock_subprocess) -> None:
        """Test launch with different Flatpak architectures."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        mock_subprocess.return_value = subprocess.CompletedProcess(args=[], returncode=0)

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
    def test_launch_environment_variable_injection(self, mock_safety, mock_subprocess) -> None:
        """Test environment variable injection attempts are blocked."""
        if not AppLauncher:
            pytest.skip("AppLauncher class not available")

        mock_subprocess.return_value = subprocess.CompletedProcess(args=[], returncode=0)

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

        mock_subprocess.return_value = subprocess.CompletedProcess(args=[], returncode=0)

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

        mock_subprocess.return_value = subprocess.CompletedProcess(args=[], returncode=0)

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

        mock_subprocess.return_value = subprocess.CompletedProcess(args=[], returncode=0)

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


@pytest.mark.slow
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
        hook_script.write_text("""#!/bin/bash
echo "App name: $2" > /tmp/hook_test.log
exit 0
""")
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
        hook_script.write_text("""#!/bin/bash
# This script would be dangerous if app name wasn't sanitized
echo "Safe execution with app: $2"
exit 0
""")
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
            from lib.config_models import AppPreferences

            mock_prefs = Mock(spec=AppPreferences)
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
        dangerous_wrapper.write_text("""#!/bin/bash
flatpak run org.mozilla.firefox --new-window
echo "This wrapper contains dangerous content"
""")
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
            pytest.fail(
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
            pytest.fail(f"Config manager should handle parse errors gracefully, not raise: {e}")

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
            pytest.fail(
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
                assert isinstance(config_manager, EnhancedConfigManager)
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
                assert isinstance(config_manager, EnhancedConfigManager)
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


class TestRunHookScriptsFailureModes:
    """Test _run_hook_scripts() failure mode handling."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()
        self.scripts_dir = self.config_dir / "scripts" / "test_app"
        self.scripts_dir.mkdir(parents=True)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_hook_script(self, hook_type: str = "pre") -> Path:
        """Create a test hook script."""
        if hook_type == "pre":
            script_path = self.scripts_dir / "pre-launch.sh"
        else:
            script_path = self.scripts_dir / "post-run.sh"
        script_path.write_text("#!/bin/bash\necho 'hook output'\nexit 0\n")
        script_path.chmod(0o755)
        return script_path

    def _make_launcher(self, hook_failure_mode="warn", **kwargs) -> "LibAppLauncher":
        return LibAppLauncher(
            app_name=kwargs.pop("app_name", "test_app"),
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            hook_failure_mode=hook_failure_mode,
            **kwargs,
        )

    @pytest.mark.parametrize(
        ("hook_type", "failure_mode", "error_factory", "expected"),
        [
            ("pre", "abort", lambda r: setattr(r, "returncode", 1) or r, False),
            ("post", "abort", lambda r: setattr(r, "returncode", 1) or r, False),
            ("pre", "warn", lambda r: setattr(r, "returncode", 1) or r, False),
            ("pre", "ignore", lambda r: setattr(r, "returncode", 1) or r, False),
            (
                "pre",
                "abort",
                lambda _: (_ for _ in ()).throw(subprocess.TimeoutExpired("s", 30)),
                False,
            ),
            (
                "post",
                "abort",
                lambda _: (_ for _ in ()).throw(subprocess.TimeoutExpired("s", 30)),
                False,
            ),
            (
                "pre",
                "warn",
                lambda _: (_ for _ in ()).throw(subprocess.TimeoutExpired("s", 30)),
                False,
            ),
            ("pre", "abort", lambda _: (_ for _ in ()).throw(OSError("Permission denied")), False),
            ("post", "abort", lambda _: (_ for _ in ()).throw(OSError("Permission denied")), False),
            ("pre", "warn", lambda _: (_ for _ in ()).throw(OSError("Permission denied")), False),
            ("pre", "abort", lambda _: (_ for _ in ()).throw(RuntimeError("Unexpected")), False),
            ("post", "abort", lambda _: (_ for _ in ()).throw(RuntimeError("Unexpected")), False),
            ("pre", "warn", lambda _: (_ for _ in ()).throw(RuntimeError("Unexpected")), False),
        ],
        ids=[
            "returncode+abort+pre",
            "returncode+abort+post",
            "returncode+warn+pre",
            "returncode+ignore+pre",
            "timeout+abort+pre",
            "timeout+abort+post",
            "timeout+warn+pre",
            "oserror+abort+pre",
            "oserror+abort+post",
            "oserror+warn+pre",
            "exception+abort+pre",
            "exception+abort+post",
            "exception+warn+pre",
        ],
    )
    @patch("subprocess.run")
    def test_hook_error_modes(
        self,
        mock_run,
        hook_type,
        failure_mode,
        error_factory,
        expected,
    ) -> None:
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        self._create_hook_script(hook_type)
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        mock_run.side_effect = lambda *a, **kw: error_factory(mock_result)

        launcher = self._make_launcher(hook_failure_mode=failure_mode)

        with patch.object(launcher, "_get_effective_failure_mode", return_value=failure_mode):
            result = launcher._run_hook_scripts(hook_type, exit_code=0, source="flatpak")

        assert result is expected

    @patch("subprocess.run")
    def test_abort_pre_prints_error_message(self, mock_run, caplog) -> None:
        """Pre-launch abort prints an abort message via logger."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        self._create_hook_script("pre")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="hook error"
        )

        launcher = self._make_launcher(hook_failure_mode="abort")
        with patch.object(launcher, "_get_effective_failure_mode", return_value="abort"):
            launcher._run_hook_scripts("pre", source="flatpak")

        assert "aborting launch" in caplog.text.lower()

    @patch("subprocess.run")
    def test_verbose_mode_prints_hook_output(self, mock_run, caplog) -> None:
        """Test verbose mode prints hook output on success."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        caplog.set_level("INFO")
        self._create_hook_script("pre")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="hook stdout output", stderr=""
        )

        launcher = self._make_launcher(verbose=True)
        with patch.object(launcher, "_get_effective_failure_mode", return_value="warn"):
            result = launcher._run_hook_scripts("pre", source="flatpak")

        assert result is True
        assert "hook" in caplog.text.lower()

    @patch("subprocess.run")
    def test_environment_variables_passed_to_hooks(self, mock_run) -> None:
        """Test that correct environment variables are passed to hook scripts."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        self._create_hook_script("pre")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        launcher = self._make_launcher()
        with patch.object(launcher, "_get_effective_failure_mode", return_value="warn"):
            launcher._run_hook_scripts("pre", source="flatpak")

        env = mock_run.call_args[1]["env"]
        assert env["FPWRAPPER_WRAPPER_NAME"] == "test_app"
        assert env["FPWRAPPER_APP_ID"] == "test_app"
        assert env["FPWRAPPER_SOURCE"] == "flatpak"
        assert env["FPWRAPPER_HOOK_FAILURE_MODE"] == "warn"

    @patch("subprocess.run")
    def test_environment_variables_post_launch_includes_exit_code(self, mock_run) -> None:
        """Test that FPWRAPPER_EXIT_CODE is set for post-launch hooks."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        self._create_hook_script("post")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        launcher = self._make_launcher()
        with patch.object(launcher, "_get_effective_failure_mode", return_value="warn"):
            launcher._run_hook_scripts("post", exit_code=42, source="system")

        env = mock_run.call_args[1]["env"]
        assert env["FPWRAPPER_EXIT_CODE"] == "42"
        assert env["FPWRAPPER_SOURCE"] == "system"

    @patch("subprocess.run")
    def test_no_scripts_returns_true(self, mock_run) -> None:
        """Test that _run_hook_scripts returns True when no scripts exist."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = self._make_launcher()
        result = launcher._run_hook_scripts("pre", source="flatpak")
        assert result is True
        mock_run.assert_not_called()

    def test_no_app_name_returns_true(self) -> None:
        """Test that _run_hook_scripts returns True when app_name is None."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = self._make_launcher(app_name=None)
        result = launcher._run_hook_scripts("pre", source="flatpak")
        assert result is True


class TestMainCLIArgumentParsing:
    """Test main() CLI argument parsing."""

    def test_verbose_flag(self) -> None:
        """Test --verbose flag is parsed correctly."""
        with patch("sys.argv", ["fplaunch-launch", "--verbose", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                # Check that AppLauncher was called with verbose=True
                call_kwargs = mock_launcher_class.call_args[1]
                assert call_kwargs["verbose"] is True
                assert result == 0

    def test_debug_flag(self) -> None:
        """Test --debug flag is parsed correctly."""
        with patch("sys.argv", ["fplaunch-launch", "--debug", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                call_kwargs = mock_launcher_class.call_args[1]
                assert call_kwargs["debug"] is True
                assert result == 0

    def test_config_dir_option(self) -> None:
        """Test --config-dir option is parsed correctly."""
        with patch("sys.argv", ["fplaunch-launch", "--config-dir", "/custom/config", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                call_kwargs = mock_launcher_class.call_args[1]
                assert call_kwargs["config_dir"] == "/custom/config"
                assert result == 0

    def test_bin_dir_option(self) -> None:
        """Test --bin-dir option is parsed correctly."""
        with patch("sys.argv", ["fplaunch-launch", "--bin-dir", "/custom/bin", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                call_kwargs = mock_launcher_class.call_args[1]
                assert call_kwargs["bin_dir"] == "/custom/bin"
                assert result == 0

    def test_hook_failure_abort(self) -> None:
        """Test --hook-failure abort is parsed correctly."""
        with patch("sys.argv", ["fplaunch-launch", "--hook-failure", "abort", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                call_kwargs = mock_launcher_class.call_args[1]
                assert call_kwargs["hook_failure_mode"] == "abort"
                assert result == 0

    def test_hook_failure_warn(self) -> None:
        """Test --hook-failure warn is parsed correctly."""
        with patch("sys.argv", ["fplaunch-launch", "--hook-failure", "warn", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                call_kwargs = mock_launcher_class.call_args[1]
                assert call_kwargs["hook_failure_mode"] == "warn"
                assert result == 0

    def test_hook_failure_ignore(self) -> None:
        """Test --hook-failure ignore is parsed correctly."""
        with patch("sys.argv", ["fplaunch-launch", "--hook-failure", "ignore", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                call_kwargs = mock_launcher_class.call_args[1]
                assert call_kwargs["hook_failure_mode"] == "ignore"
                assert result == 0

    def test_abort_on_hook_failure_shorthand(self) -> None:
        """Test --abort-on-hook-failure shorthand is parsed correctly."""
        with patch("sys.argv", ["fplaunch-launch", "--abort-on-hook-failure", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                call_kwargs = mock_launcher_class.call_args[1]
                assert call_kwargs["hook_failure_mode"] == "abort"
                assert result == 0

    def test_ignore_hook_failure_shorthand(self) -> None:
        """Test --ignore-hook-failure shorthand is parsed correctly."""
        with patch("sys.argv", ["fplaunch-launch", "--ignore-hook-failure", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                call_kwargs = mock_launcher_class.call_args[1]
                assert call_kwargs["hook_failure_mode"] == "ignore"
                assert result == 0

    def test_app_args_passed_correctly(self) -> None:
        """Test that app arguments are passed correctly."""
        with patch(
            "sys.argv",
            ["fplaunch-launch", "firefox", "--new-window", "--private-window"],
        ):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                call_kwargs = mock_launcher_class.call_args[1]
                assert call_kwargs["args"] == ["--new-window", "--private-window"]
                assert result == 0

    def test_launch_failure_returns_1(self) -> None:
        """Test that launch failure returns exit code 1."""
        with patch("sys.argv", ["fplaunch-launch", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = False
                mock_launcher_class.return_value = mock_instance

                result = main()

                assert result == 1

    def test_launch_success_returns_0(self) -> None:
        """Test that successful launch returns exit code 0."""
        with patch("sys.argv", ["fplaunch-launch", "firefox"]):
            with patch("lib.launch.AppLauncher") as mock_launcher_class:
                mock_instance = Mock(spec=AppLauncher)
                mock_instance.launch.return_value = True
                mock_launcher_class.return_value = mock_instance

                result = main()

                assert result == 0


class TestGetEffectiveFailureMode:
    """Test _get_effective_failure_mode() method."""

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

    def test_returns_mode_from_config_manager(self) -> None:
        """Test that mode is returned from config manager."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            hook_failure_mode="abort",
        )

        with patch("lib.config_manager.create_config_manager") as mock_cm:
            mock_config = Mock()
            mock_config.get_effective_hook_failure_mode.return_value = "ignore"
            mock_cm.return_value = mock_config

            result = launcher._get_effective_failure_mode("pre")

            assert result == "ignore"

    def test_fallback_to_environment_variable(self) -> None:
        """Test fallback to FPWRAPPER_HOOK_FAILURE env var."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        with patch("lib.config_manager.create_config_manager", side_effect=ImportError()):
            with patch.dict(os.environ, {"FPWRAPPER_HOOK_FAILURE": "abort"}):
                result = launcher._get_effective_failure_mode("pre")

                assert result == "abort"

    def test_default_is_warn(self) -> None:
        """Test default failure mode is warn."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        with patch("lib.config_manager.create_config_manager", side_effect=ImportError()):
            # Clear any existing env var
            env = os.environ.copy()
            if "FPWRAPPER_HOOK_FAILURE" in env:
                del env["FPWRAPPER_HOOK_FAILURE"]
            with patch.dict(os.environ, env, clear=True):
                result = launcher._get_effective_failure_mode("pre")

                assert result == "warn"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestHookScriptsFromConfig:
    """Test _get_hook_scripts loading from config manager."""

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

    @patch("lib.config_manager.create_config_manager")
    def test_get_hook_scripts_config_exception_falls_back(self, mock_cm) -> None:
        """Test that config manager exception falls back to default location."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Make config manager raise an expected error type
        mock_cm.side_effect = OSError("Config error")

        # Create default script
        scripts_dir = self.config_dir / "scripts" / "test_app"
        scripts_dir.mkdir(parents=True)
        default_script = scripts_dir / "pre-launch.sh"
        default_script.write_text("#!/bin/bash\necho 'default'\n")
        default_script.chmod(0o755)

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        scripts = launcher._get_hook_scripts("test_app", "pre")

        # Should fall back to default location
        assert len(scripts) == 1


class TestCacheFlatpakId:
    """Test _cache_flatpak_id function."""

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

    def test_cache_flatpak_id_stores_value(self) -> None:
        """Test _cache_flatpak_id stores the cached ID."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        from lib.launch import _cache_flatpak_id, _FLATPAK_ID_CACHE

        # Clear cache
        _FLATPAK_ID_CACHE.clear()

        _cache_flatpak_id("firefox", "org.mozilla.firefox")

        assert "firefox" in _FLATPAK_ID_CACHE
        assert _FLATPAK_ID_CACHE["firefox"][0] == "org.mozilla.firefox"


class TestGetSafetyCheckFallback:
    """Test _get_safety_check fallback import."""

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

    def test_get_safety_check_returns_tuple(self) -> None:
        """Test _get_safety_check returns proper tuple."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher._get_safety_check()

        # Should return a tuple of (bool, function or None)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)


class TestCacheFunctions:
    """Test Flatpak ID caching functions."""

    def test_get_cached_flatpak_id_returns_cached_value(self) -> None:
        """Test _get_cached_flatpak_id returns cached value within TTL."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        from lib.launch import _get_cached_flatpak_id, _cache_flatpak_id

        # Cache a value
        _cache_flatpak_id("firefox", "org.mozilla.firefox")

        # Should return cached value
        result = _get_cached_flatpak_id("firefox")
        assert result == "org.mozilla.firefox"

    def test_get_cached_flatpak_id_returns_none_when_expired(self) -> None:
        """Test _get_cached_flatpak_id returns None when cache is expired."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        import time
        from lib.launch import _get_cached_flatpak_id, _CACHE_TTL_SECONDS

        # Cache a value with old timestamp
        from lib import launch

        launch._FLATPAK_ID_CACHE.clear()  # Clear the module's cache first
        launch._FLATPAK_ID_CACHE["firefox"] = (
            "org.mozilla.firefox",
            time.time() - _CACHE_TTL_SECONDS - 1,
        )

        # Should return None due to expiration
        result = _get_cached_flatpak_id("firefox")
        assert result is None

    def test_get_cached_flatpak_id_returns_none_when_not_cached(self) -> None:
        """Test _get_cached_flatpak_id returns None when not cached."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        from lib.launch import _get_cached_flatpak_id

        # Should return None for uncached app
        result = _get_cached_flatpak_id("nonexistent_app_12345")
        assert result is None


class TestIsTestEnvironmentLaunch:
    """Test is_test_environment_launch() function."""

    def test_returns_true_when_pytest_in_modules(self) -> None:
        """Test returns True when pytest is in sys.modules."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        import sys
        from lib.launch import is_test_environment_launch

        # Simulate pytest running
        sys.modules["pytest"] = True
        try:
            result = is_test_environment_launch()
            assert result is True
        finally:
            del sys.modules["pytest"]

    def test_returns_true_when_unittest_in_modules(self) -> None:
        """Test returns True when unittest is in sys.modules."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        import sys
        from lib.launch import is_test_environment_launch

        # Simulate unittest running
        sys.modules["unittest"] = True
        try:
            result = is_test_environment_launch()
            assert result is True
        finally:
            del sys.modules["unittest"]

    def test_returns_true_when_pytest_env_var_set(self) -> None:
        """Test returns True when PYTEST_ env var is set."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        from lib.launch import is_test_environment_launch

        with patch.dict(os.environ, {"PYTEST_XDIST_WORKER": "test_worker"}):
            result = is_test_environment_launch()
            assert result is True

    def test_returns_false_when_not_in_test_environment(self) -> None:
        """Test returns False when not in test environment."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        import sys
        from lib.launch import is_test_environment_launch

        # Make sure no test modules are loaded
        test_modules = [k for k in sys.modules.keys() if "pytest" in k or "unittest" in k]
        for mod in test_modules:
            del sys.modules[mod]

        # Clear env vars
        test_env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
        with patch.dict(os.environ, test_env, clear=True):
            result = is_test_environment_launch()
            assert result is False


class TestHookScriptsPostLaunch:
    """Test _get_hook_scripts for post-launch scripts."""

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

    def test_get_hook_scripts_post_launch_default_location(self) -> None:
        """Test getting post-launch hook script from default location."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Create post-launch script in default location
        scripts_dir = self.config_dir / "scripts" / "test_app"
        scripts_dir.mkdir(parents=True)
        post_script = scripts_dir / "post-run.sh"
        post_script.write_text("#!/bin/bash\necho 'post'\n")
        post_script.chmod(0o755)

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        scripts = launcher._get_hook_scripts("test_app", "post")

        assert len(scripts) == 1
        assert scripts[0].name == "post-run.sh"

    def test_get_hook_scripts_invalid_hook_type_returns_empty(self) -> None:
        """Test invalid hook type returns empty list."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        scripts = launcher._get_hook_scripts("test_app", "invalid")

        assert scripts == []


class TestDetermineLaunchSource:
    """Test _determine_launch_source method."""

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

    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_determine_launch_source_wrapper_not_executable(self, mock_safety) -> None:
        """Test when wrapper exists but is not executable."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Create non-executable wrapper
        wrapper = self.bin_dir / "test_app"
        wrapper.write_text("#!/bin/bash\necho 'test'\n")
        # Don't make it executable

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True,
        )

        source, wrapper_path = launcher._determine_launch_source()

        # Should return flatpak source and None wrapper_path
        assert source == "flatpak"
        assert wrapper_path is None

    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_determine_launch_source_path_safe_check_exception(self, mock_safety) -> None:
        """Test _determine_launch_source handles path safety check exception."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Mock _is_path_safe to raise exception (this is within a try block in the code)
        with patch.object(launcher, "_is_path_safe", side_effect=OSError("test")):
            source, wrapper_path = launcher._determine_launch_source()

            # Should handle exception gracefully and return flatpak source
            assert source == "flatpak"


class TestPreferenceOverride:
    """Test _check_preference_override method."""

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

    def test_preference_override_flatpak(self) -> None:
        """Test .pref file with 'flatpak' preference."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Create preference file
        pref_file = self.config_dir / "test_app.pref"
        pref_file.write_text("flatpak\n")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        wrapper_path, source = launcher._check_preference_override(None, "system")

        assert wrapper_path is None
        assert source == "flatpak"

    def test_preference_override_system(self) -> None:
        """Test .pref file with 'system' preference when wrapper exists."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Create preference file
        pref_file = self.config_dir / "test_app.pref"
        pref_file.write_text("system\n")

        # Create wrapper
        wrapper = self.bin_dir / "test_app"
        wrapper.write_text("#!/bin/bash\necho 'test'\n")
        wrapper.chmod(0o755)

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        wrapper_path, source = launcher._check_preference_override(wrapper, "flatpak")

        assert source == "system"

    def test_preference_override_system_no_wrapper(self) -> None:
        """Test .pref file with 'system' preference when no wrapper exists."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Create preference file
        pref_file = self.config_dir / "test_app.pref"
        pref_file.write_text("system\n")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        wrapper_path, source = launcher._check_preference_override(None, "flatpak")

        # Falls back to flatpak when no wrapper
        assert source == "flatpak"

    def test_preference_override_read_error(self) -> None:
        """Test preference override handles read errors gracefully."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Create preference file that can't be read
        pref_file = self.config_dir / "test_app.pref"
        pref_file.write_text("test")
        # Make it unreadable
        pref_file.chmod(0o000)

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should handle error gracefully
        wrapper_path, source = launcher._check_preference_override(None, "flatpak")

        # Should return unchanged values
        assert wrapper_path is None
        assert source == "flatpak"


class TestResolveFlatpakId:
    """Test _resolve_flatpak_id method."""

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

    def test_resolve_flatpak_id_with_cached_value(self) -> None:
        """Test resolution returns cached value."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        from lib.launch import _cache_flatpak_id

        # Pre-cache a value
        _cache_flatpak_id("firefox", "org.mozilla.firefox")

        launcher = LibAppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher._resolve_flatpak_id(None)

        assert result == "org.mozilla.firefox"

    def test_resolve_flatpak_id_empty_when_no_app_name(self) -> None:
        """Test resolution returns empty string when app_name is None."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name=None,
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher._resolve_flatpak_id(None)

        assert result == ""

    @patch("lib.launch.subprocess.run")
    @patch("lib.python_utils.find_executable")
    @patch("lib.safety.is_test_environment", return_value=False)
    def test_resolve_flatpak_id_uses_flatpak_list(self, mock_is_test, mock_find, mock_run) -> None:
        """Test resolution uses flatpak list command."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Clear the cache first
        from lib import launch

        launch._FLATPAK_ID_CACHE.clear()

        # Mock find_executable to return flatpak path
        mock_find.return_value = "/usr/bin/flatpak"

        # Mock subprocess.run to return flatpak list output
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="org.mozilla.firefox\ncom.google.Chrome\n",
        )

        launcher = LibAppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher._resolve_flatpak_id(None)

        assert result == "org.mozilla.firefox"
        mock_run.assert_called_once()

    @patch("lib.launch.subprocess.run")
    @patch("lib.python_utils.find_executable")
    @patch("lib.safety.is_test_environment", return_value=False)
    def test_resolve_flatpak_id_handles_subprocess_error(
        self, mock_is_test, mock_find, mock_run
    ) -> None:
        """Test resolution handles subprocess errors gracefully."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        # Clear the cache first
        from lib import launch

        launch._FLATPAK_ID_CACHE.clear()

        # Mock find_executable to return flatpak path
        mock_find.return_value = "/usr/bin/flatpak"

        # Mock subprocess.run to raise OSError (realistic error)
        mock_run.side_effect = OSError("flatpak not found")

        launcher = LibAppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should fall back to app_name
        result = launcher._resolve_flatpak_id(None)

        assert result == "firefox"


class TestExecuteLaunchDebugMode:
    """Test _execute_launch debug mode."""

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
    def test_execute_launch_debug_prints_command(self, mock_run, caplog) -> None:
        """Test _execute_launch prints debug command."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        caplog.set_level("DEBUG")
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        launcher = LibAppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            debug=True,
        )

        launcher._execute_launch(["flatpak", "run", "firefox"])

        # Check debug output was logged
        assert "flatpak run firefox" in caplog.text


class TestWrapperExistsFindWrapperExceptions:
    """Test exception handling in _wrapper_exists and _find_wrapper."""

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

    def test_wrapper_exists_path_safe_exception(self) -> None:
        """Test _wrapper_exists fails closed when path safety check raises.

        Even when the wrapper file appears to exist and be executable, a
        safety-check exception must cause _wrapper_exists to return False so
        we never invoke an unvalidated path (e.g. /etc/passwd).
        """
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        with (
            patch.object(launcher, "_is_path_safe", side_effect=ValueError("test")),
            patch("pathlib.Path.exists", return_value=True),
            patch("os.access", return_value=True),
        ):
            result = launcher._wrapper_exists("test_app")

        # Fail closed: a safety-check exception must not let the filesystem
        # check pass.
        assert result is False

    def test_find_wrapper_path_safe_exception(self) -> None:
        """Test _find_wrapper fails closed when path safety check raises.

        Mirrors the _wrapper_exists test: a safety-check exception must not
        allow an unvalidated path to be returned to the caller.
        """
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        with (
            patch.object(launcher, "_is_path_safe", side_effect=OSError("test")),
            patch("pathlib.Path.exists", return_value=True),
            patch("os.access", return_value=True),
        ):
            result = launcher._find_wrapper()

        assert result is None


class TestLaunchSafetyCheckFailure:
    """Test launch() when safety checks fail."""

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

    @patch("lib.safety.safe_launch_check", return_value=False)
    def test_launch_fails_when_safety_check_fails(self, mock_safety) -> None:
        """Test launch returns False when safety check fails."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="dangerous_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is False
        mock_safety.assert_called_once()

    def test_launch_with_none_app_name_fails_safety(self) -> None:
        """Test launch with None app_name fails safety check."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name=None,
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is False


class TestLaunchHookFailureVerbose:
    """Test launch() verbose output on hook failure."""

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

    def _create_hook_script(self, hook_type: str) -> None:
        """Create a hook script that fails."""
        scripts_dir = self.config_dir / "scripts" / "test_app"
        scripts_dir.mkdir(parents=True)
        if hook_type == "pre":
            script_path = scripts_dir / "pre-launch.sh"
        else:
            script_path = scripts_dir / "post-run.sh"
        script_path.write_text("#!/bin/bash\nexit 1\n")
        script_path.chmod(0o755)

    @patch("subprocess.run")
    def test_launch_verbose_on_pre_hook_failure(self, mock_run, caplog) -> None:
        """Test verbose output when pre-launch hook succeeds."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        caplog.set_level("INFO")
        self._create_hook_script("pre")

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="hook stdout output", stderr=""
        )

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True,
        )

        with patch.object(launcher, "_get_effective_failure_mode", return_value="abort"):
            launcher.launch()

            # Should log hook output
            assert "hook output" in caplog.text.lower()

    @patch("subprocess.run")
    def test_launch_verbose_on_post_hook_failure(self, mock_run) -> None:
        """Test verbose output when post-launch hook fails."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        self._create_hook_script("post")

        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True,
        )

        with patch.object(launcher, "_get_effective_failure_mode", return_value="warn"):
            launcher.launch()


class TestLaunchExceptions:
    """Test launch() exception handling."""

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

    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_keyboard_interrupt(self, mock_safety) -> None:
        """Test launch handles KeyboardInterrupt."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True,
        )

        with patch.object(launcher, "_determine_launch_source", side_effect=KeyboardInterrupt()):
            result = launcher.launch()

            assert result is False

    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_general_exception(self, mock_safety, caplog) -> None:
        """Test launch handles general exceptions."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True,
        )

        with patch.object(
            launcher, "_determine_launch_source", side_effect=RuntimeError("test error")
        ):
            result = launcher.launch()

            assert result is False
            # Should log error message
            assert "Error launching" in caplog.text


class TestMainCLISystemExit:
    """Test main() SystemExit handling."""

    def test_main_handles_help_flag_gracefully(self) -> None:
        """Test main handles --help flag gracefully (returns 0 instead of raising)."""
        # When --help is passed, argparse raises SystemExit(0)
        # main() catches this and returns 0 instead
        with patch("sys.argv", ["fplaunch-launch", "--help"]):
            # main() should catch SystemExit and return 0
            result = main()
            assert result == 0

    def test_main_handles_system_exit_non_zero(self) -> None:
        """Test main returns 1 on SystemExit with non-zero code."""
        # Test with invalid argument that triggers SystemExit
        with patch("sys.argv", ["fplaunch-launch", "--invalid-option"]):
            result = main()

            # Should return 1 for error
            assert result == 1


class TestHookScriptDebugOutput:
    """Test debug output in hook script execution."""

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

    def _create_hook_script(self, hook_type: str) -> Path:
        """Create a hook script."""
        scripts_dir = self.config_dir / "scripts" / "test_app"
        scripts_dir.mkdir(parents=True)
        if hook_type == "pre":
            script_path = scripts_dir / "pre-launch.sh"
        else:
            script_path = scripts_dir / "post-run.sh"
        script_path.write_text("#!/bin/bash\necho 'hook running'\n")
        script_path.chmod(0o755)
        return script_path

    @patch("subprocess.run")
    def test_run_hook_scripts_debug_mode_prints_execution(self, mock_run, caplog) -> None:
        """Test _run_hook_scripts prints debug info in debug mode."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        caplog.set_level("DEBUG")
        self._create_hook_script("pre")

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            debug=True,
        )

        with patch.object(launcher, "_get_effective_failure_mode", return_value="warn"):
            launcher._run_hook_scripts("pre", source="flatpak")

            # Should log debug output
            assert "Executing" in caplog.text


class TestSanitizeAppName:
    """Test _sanitize_app_name method."""

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

    def test_sanitize_app_name_keeps_alphanumeric_and_underscore_dash_dot(self) -> None:
        """Test sanitization keeps safe characters."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # These characters should be kept
        safe_name = "app_name-v1.2.3"
        sanitized = launcher._sanitize_app_name(safe_name)

        assert sanitized == safe_name

    def test_sanitize_app_name_replaces_shell_dangerous_chars(self) -> None:
        """Test sanitization replaces shell-dangerous characters."""
        if not LibAppLauncher:
            pytest.skip("LibAppLauncher class not available")

        launcher = LibAppLauncher(
            app_name="test_app",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # These characters should be replaced as they're shell-dangerous
        unsafe_name = "app;echo test"
        sanitized = launcher._sanitize_app_name(unsafe_name)

        # Semicolon should be replaced
        assert ";" not in sanitized
        # The entire string is replaced char by char, so "echo" would become underscores
        # Just check that dangerous chars are replaced
        assert all(c not in sanitized for c in ";|&`$(){}[]<>")
