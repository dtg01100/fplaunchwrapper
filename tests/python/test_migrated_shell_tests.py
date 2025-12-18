#!/usr/bin/env python3
"""
Convert shell tests to pytest - Phase 1
Replace old bash implementation tests with pytest equivalents
"""

import pytest
import tempfile
import subprocess
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
from pathlib import Path

# Add lib to path
# Import modules to test
try:
    from fplaunch.generate import WrapperGenerator
    from fplaunch.manage import WrapperManager
    from fplaunch.systemd_setup import SystemdSetup
    from fplaunch. import AppLauncher
    from fplaunch. import WrapperCleanup
except ImportError:
    # Will be tested in individual test functions
    pass


class TestWrapperGeneration:
    """Replace test_wrapper_generation.sh with pytest"""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment"""
        temp_dir = Path(tempfile.mkdtemp())
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"
        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_basic_wrapper_generation(self, mock_subprocess, temp_env):
        """Test basic wrapper generation - replaces test_wrapper_generation.sh Test 1"""
        if not "WrapperGenerator" in globals():
            pytest.skip("WrapperGenerator not available")

        # Mock flatpak command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "org.mozilla.firefox\ncom.google.chrome"
        mock_subprocess.return_value = mock_result

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]), verbose=True, emit_mode=False
        )

        # Mock the get_installed_flatpaks method
        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"]
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")

            assert result is True

            # Check wrapper was created
            wrapper_path = temp_env["bin_dir"] / "firefox"
            assert wrapper_path.exists()
            assert wrapper_path.stat().st_mode & 0o111  # executable

            # Check wrapper content
            content = wrapper_path.read_text()
            assert "org.mozilla.firefox" in content
            assert "#!/usr/bin/env bash" in content

    @patch("subprocess.run")
    def test_name_collision_detection(self, mock_subprocess, temp_env):
        """Test name collision detection - replaces test_wrapper_generation.sh Test 2"""
        if not "WrapperGenerator" in globals():
            pytest.skip("WrapperGenerator not available")

        # Create existing wrapper
        existing_wrapper = temp_env["bin_dir"] / "code"
        existing_wrapper.write_text('#!/bin/bash\necho "existing code"\n')
        existing_wrapper.chmod(0o755)

        # Mock flatpak command returning app with same name
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "com.visualstudio.code"
        mock_subprocess.return_value = mock_result

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]), verbose=True, emit_mode=False
        )

        # This should skip due to collision
        with patch.object(
            generator, "get_installed_flatpaks", return_value=["com.visualstudio.code"]
        ):
            result = generator.generate_wrapper("com.visualstudio.code")

            # Should return False due to collision
            assert result is False

    @patch("subprocess.run")
    def test_blocklist_functionality(self, mock_subprocess, temp_env):
        """Test blocklist functionality - replaces test_wrapper_generation.sh Test 3"""
        if not "WrapperGenerator" in globals():
            pytest.skip("WrapperGenerator not available")

        # Create blocklist file
        blocklist_file = temp_env["config_dir"] / "blocklist"
        blocklist_file.write_text("org.mozilla.firefox\n")

        # Mock flatpak command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "org.mozilla.firefox\ncom.google.chrome"
        mock_subprocess.return_value = mock_result

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Firefox should be blocked
        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"]
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is False  # Should be blocked

        # Chrome should work
        with patch.object(
            generator, "get_installed_flatpaks", return_value=["com.google.chrome"]
        ):
            result = generator.generate_wrapper("com.google.chrome")
            assert result is True

            # Check chrome wrapper was created
            chrome_wrapper = temp_env["bin_dir"] / "chrome"
            assert chrome_wrapper.exists()

    def test_invalid_name_handling(self, temp_env):
        """Test invalid name handling - replaces test_wrapper_generation.sh Test 5"""
        if not "WrapperGenerator" in globals():
            pytest.skip("WrapperGenerator not available")

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]), verbose=True, emit_mode=False
        )

        # Test invalid names
        invalid_apps = [
            "com.example.my app",  # space
            "com.example.my-app",  # hyphen (should be valid)
            "com.example.123app",  # starts with number (should be valid)
        ]

        for app_id in invalid_apps:
            result = generator.generate_wrapper(app_id)
            # Should handle gracefully (may return False for invalid names)
            assert isinstance(result, bool)

    @patch("subprocess.run")
    def test_environment_variable_loading(self, mock_subprocess, temp_env):
        """Test environment variable loading - replaces test_wrapper_generation.sh Test 5"""
        if not "WrapperGenerator" in globals():
            pytest.skip("WrapperGenerator not available")

        # Create env file
        env_file = temp_env["config_dir"] / "firefox.env"
        env_file.write_text("export TEST_VAR=test_value\n")

        # Mock flatpak command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"]
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")

            assert result is True

            # Check wrapper contains env loading
            wrapper_content = (temp_env["bin_dir"] / "firefox").read_text()
            assert "load_env_vars" in wrapper_content or "source" in wrapper_content

    @patch("subprocess.run")
    def test_pre_launch_script_execution(self, mock_subprocess, temp_env):
        """Test pre-launch script execution - replaces test_wrapper_generation.sh Test 6"""
        if not "WrapperGenerator" in globals():
            pytest.skip("WrapperGenerator not available")

        # Create pre-launch script
        script_dir = temp_env["config_dir"] / "scripts" / "firefox"
        script_dir.mkdir(parents=True)
        pre_script = script_dir / "pre-launch.sh"
        pre_script.write_text('#!/bin/bash\necho "pre-launch executed"\n')
        pre_script.chmod(0o755)

        # Mock flatpak command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"]
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")

            assert result is True

            # Check wrapper contains pre-launch script execution
            wrapper_content = (temp_env["bin_dir"] / "firefox").read_text()
            assert "run_pre_launch_script" in wrapper_content

    @patch("subprocess.run")
    def test_preference_handling(self, mock_subprocess, temp_env):
        """Test preference handling - replaces test_wrapper_generation.sh Test 7"""
        if not "WrapperGenerator" in globals():
            pytest.skip("WrapperGenerator not available")

        # Create preference file
        pref_file = temp_env["config_dir"] / "firefox.pref"
        pref_file.write_text("flatpak\n")

        # Mock flatpak command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"]
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")

            assert result is True

            # Check wrapper contains preference loading
            wrapper_content = (temp_env["bin_dir"] / "firefox").read_text()
            assert "PREF_FILE" in wrapper_content

    def test_wrapper_cleanup_obsolete(self, temp_env):
        """Test wrapper cleanup for uninstalled apps - replaces test_wrapper_generation.sh Test 8"""
        if not "WrapperGenerator" in globals():
            pytest.skip("WrapperGenerator not available")

        # Create obsolete wrapper
        old_wrapper = temp_dir / "bin" / "oldapp"
        old_wrapper.write_text("#!/bin/bash\necho oldapp\n")
        old_wrapper.chmod(0o755)

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Mock empty installed apps (oldapp no longer installed)
        with patch.object(generator, "get_installed_flatpaks", return_value=[]):
            removed_count = generator.cleanup_obsolete_wrappers([])

            # Should have removed oldapp
            assert not old_wrapper.exists()
            assert removed_count >= 1


class TestManagementFunctions:
    """Replace test_management_functions.sh with pytest"""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment"""
        temp_dir = Path(tempfile.mkdtemp())
        config_dir = temp_dir / "config"
        bin_dir = temp_dir / "bin"
        config_dir.mkdir()
        bin_dir.mkdir()

        yield {"temp_dir": temp_dir, "config_dir": config_dir, "bin_dir": bin_dir}

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_preference_setting(self, temp_env):
        """Test preference setting - replaces test_management_functions.sh Test 1"""
        if not "WrapperManager" in globals():
            pytest.skip("WrapperManager not available")

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=False
        )

        # Test valid preference
        result = manager.set_preference("firefox", "flatpak")
        assert result is True

        # Check preference file was created
        pref_file = temp_env["config_dir"] / "firefox.pref"
        assert pref_file.exists()
        assert pref_file.read_text().strip() == "flatpak"

        # Test invalid preference
        result = manager.set_preference("chrome", "invalid")
        assert result is False

    def test_alias_management(self, temp_env):
        """Test alias management - replaces test_management_functions.sh Test 2"""
        if not "WrapperManager" in globals():
            pytest.skip("WrapperManager not available")

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=False
        )

        # Create a wrapper first
        wrapper_path = temp_env["bin_dir"] / "firefox"
        wrapper_path.write_text("#!/bin/bash\necho firefox\n")
        wrapper_path.chmod(0o755)

        # Create alias
        result = manager.create_alias("browser", "firefox")
        assert result is True

        # Check alias file was created
        alias_file = temp_env["config_dir"] / "aliases"
        assert alias_file.exists()
        content = alias_file.read_text()
        assert "browser:firefox" in content

        # Test duplicate alias
        result = manager.create_alias("browser", "chrome")
        assert result is False  # Should fail

    def test_environment_variable_management(self, temp_env):
        """Test environment variable management - replaces test_management_functions.sh Test 3"""
        if not "WrapperManager" in globals():
            pytest.skip("WrapperManager not available")

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=False
        )

        # Set environment variable
        result = manager.set_environment_variable("firefox", "TEST_VAR", "test_value")
        assert result is True

        # Check env file was created
        env_file = temp_env["config_dir"] / "firefox.env"
        assert env_file.exists()
        content = env_file.read_text()
        assert "TEST_VAR=test_value" in content

    def test_blocklist_management(self, temp_env):
        """Test blocklist management - replaces test_management_functions.sh Test 4"""
        if not "WrapperManager" in globals():
            pytest.skip("WrapperManager not available")

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=False
        )

        # Block an app
        result = manager.block_app("org.mozilla.firefox")
        assert result is True

        # Check blocklist file
        blocklist_file = temp_env["config_dir"] / "blocklist"
        assert blocklist_file.exists()
        content = blocklist_file.read_text()
        assert "org.mozilla.firefox" in content

        # Unblock the app
        result = manager.unblock_app("org.mozilla.firefox")
        assert result is True

        # Check it was removed
        content = blocklist_file.read_text()
        assert "org.mozilla.firefox" not in content

    def test_export_import_preferences(self, temp_env):
        """Test export/from fplaunch import preferences - replaces test_management_functions.sh Test 6"""
        if not "WrapperManager" in globals():
            pytest.skip("WrapperManager not available")

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=False
        )

        # Create some preferences
        manager.set_preference("firefox", "flatpak")
        manager.set_preference("chrome", "system")

        # Export preferences
        export_file = temp_env["temp_dir"] / "prefs.json"
        result = manager.export_preferences(str(export_file))
        assert result is True
        assert export_file.exists()

        # Clear preferences
        (temp_env["config_dir"] / "firefox.pref").unlink()
        (temp_env["config_dir"] / "chrome.pref").unlink()

        # Import preferences
        result = manager.import_preferences(str(export_file))
        assert result is True

        # Check preferences were restored
        assert (temp_env["config_dir"] / "firefox.pref").exists()
        assert (temp_env["config_dir"] / "chrome.pref").exists()

    def test_script_management(self, temp_env):
        """Test script management - replaces test_management_functions.sh Test 7"""
        if not "WrapperManager" in globals():
            pytest.skip("WrapperManager not available")

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=False
        )

        # Create pre-launch script
        script_content = '#!/bin/bash\necho "pre-launch"\n'
        result = manager.set_pre_launch_script("firefox", script_content)
        assert result is True

        # Check script file was created
        script_dir = temp_env["config_dir"] / "scripts" / "firefox"
        pre_script = script_dir / "pre-launch.sh"
        assert pre_script.exists()
        assert pre_script.read_text() == script_content
        assert os.access(pre_script, os.X_OK)

    def test_wrapper_removal(self, temp_env):
        """Test wrapper removal - replaces test_management_functions.sh Test 8"""
        if not "WrapperManager" in globals():
            pytest.skip("WrapperManager not available")

        # Create test files
        wrapper_file = temp_env["bin_dir"] / "testapp"
        wrapper_file.write_text("#!/bin/bash\necho testapp\n")
        wrapper_file.chmod(0o755)

        pref_file = temp_env["config_dir"] / "testapp.pref"
        pref_file.write_text("flatpak\n")

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Remove wrapper
        result = manager.remove_wrapper("testapp")
        assert result is True

        # Check files were removed
        assert not wrapper_file.exists()
        assert not pref_file.exists()

    def test_list_wrappers(self, temp_env):
        """Test list wrappers - replaces test_management_functions.sh Test 9"""
        if not "WrapperManager" in globals():
            pytest.skip("WrapperManager not available")

        # Create test wrapper
        wrapper_file = temp_env["bin_dir"] / "testapp"
        wrapper_file.write_text("#!/bin/bash\necho testapp\n")
        wrapper_file.chmod(0o755)

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # List wrappers
        wrappers = manager.list_wrappers()
        assert len(wrappers) >= 1
        assert "testapp" in wrappers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
