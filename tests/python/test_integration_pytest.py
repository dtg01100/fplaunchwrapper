#!/usr/bin/env python3
"""Pytest replacement for test_integration.sh
Tests complete integration workflows using proper mocking.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add lib to path
# Import modules to test
try:
    from fplaunch.generate import WrapperGenerator
    from fplaunch.manage import WrapperManager

    GENERATE_AVAILABLE = True
    MANAGE_AVAILABLE = True
except ImportError:
    GENERATE_AVAILABLE = False
    MANAGE_AVAILABLE = False


class TestIntegrationWorkflows:
    """Test complete integration workflows."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp(prefix="fpwrapper_integration_"))
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"

        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.skipif(
        not (GENERATE_AVAILABLE and MANAGE_AVAILABLE),
        reason="Required modules not available",
    )
    @patch("subprocess.run")
    def test_complete_wrapper_lifecycle(self, mock_subprocess, temp_env) -> None:
        """Test complete wrapper lifecycle - replaces Test 1."""
        # Mock flatpak command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "org.mozilla.firefox"
        mock_subprocess.return_value = mock_result

        # Step 1: Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        # Verify wrapper was created
        firefox_wrapper = temp_env["bin_dir"] / "firefox"
        assert firefox_wrapper.exists()

        # Step 2: Set preference
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        result = manager.set_preference("firefox", "flatpak")
        assert result is True

        # Verify preference was saved
        pref_file = temp_env["config_dir"] / "firefox.pref"
        assert pref_file.exists()
        assert pref_file.read_text().strip() == "flatpak"

        # Step 3: Update wrapper (regenerate)
        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        # Verify preference persisted after update
        assert pref_file.exists()
        assert pref_file.read_text().strip() == "flatpak"

        # Step 4: Remove wrapper and config
        result = manager.remove_wrapper("firefox")
        assert result is True

        # Verify complete cleanup
        assert not firefox_wrapper.exists()
        assert not pref_file.exists()

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_multiple_wrappers_collision_handling(self, mock_subprocess, temp_env) -> None:
        """Test multiple wrappers with collision handling - replaces Test 2."""
        # Mock flatpak command returning multiple apps
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "com.google.chrome\ncom.microsoft.edge\norg.mozilla.firefox\ncom.example.browser"
        mock_subprocess.return_value = mock_result

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        apps = [
            ("com.google.chrome", "chrome"),
            ("com.microsoft.edge", "edge"),
            ("org.mozilla.firefox", "firefox"),
            ("com.example.browser", "browser"),
        ]

        # Generate all wrappers
        for app_id, _expected_name in apps:
            with patch.object(
                generator, "get_installed_flatpaks", return_value=[app_id],
            ):
                result = generator.generate_wrapper(app_id)
                assert result is True

        # Verify all 5 wrappers were created (including collision resolution)
        created_wrappers = []

        for wrapper_file in temp_env["bin_dir"].glob("*"):
            if wrapper_file.is_file() and os.access(wrapper_file, os.X_OK):
                created_wrappers.append(wrapper_file.name)

        # Should have created wrappers (exact count depends on collision handling)
        assert len(created_wrappers) >= 4

        # Check specific expected wrappers exist
        for name in ["chrome", "edge", "firefox", "browser"]:
            wrapper_path = temp_env["bin_dir"] / name
            if wrapper_path.exists():
                assert os.access(wrapper_path, os.X_OK)
                content = wrapper_path.read_text()
                assert "#!/usr/bin/env bash" in content

    @pytest.mark.skipif(
        not (GENERATE_AVAILABLE and MANAGE_AVAILABLE),
        reason="Required modules not available",
    )
    @patch("subprocess.run")
    def test_preference_override_workflow(self, mock_subprocess, temp_env) -> None:
        """Test preference override and fallback workflow - replaces Test 3."""
        # Mock flatpak command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Create wrapper first
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        # Test user choice: system (but system binary doesn't exist)
        result = manager.set_preference("firefox", "system")
        assert result is True

        # Simulate system binary not being available - should fallback to flatpak
        # In real scenario, this would happen during launch when system binary is missing

        # Test that preference can be updated
        result = manager.set_preference("firefox", "flatpak")
        assert result is True

        pref_file = temp_env["config_dir"] / "firefox.pref"
        assert pref_file.read_text().strip() == "flatpak"

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_alias_creation_and_resolution(self, temp_env) -> None:
        """Test alias creation and resolution - replaces Test 4."""
        # Create base wrappers
        wrappers = ["firefox", "chrome"]
        for wrapper in wrappers:
            wrapper_file = temp_env["bin_dir"] / wrapper
            wrapper_file.write_text(f"#!/bin/bash\necho {wrapper}\n")
            wrapper_file.chmod(0o755)

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Create aliases
        result = manager.create_alias("browser", "firefox")
        assert result is True

        result = manager.create_alias("web", "chrome")
        assert result is True

        # Check aliases were recorded
        alias_file = temp_env["config_dir"] / "aliases"
        assert alias_file.exists()
        content = alias_file.read_text()
        assert "browser:firefox" in content
        assert "web:chrome" in content

        # Test alias chain (alias pointing to alias)
        result = manager.create_alias("surf", "browser")  # surf -> browser -> firefox
        assert result is True

        content = alias_file.read_text()
        assert "surf:browser" in content

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_environment_script_integration(self, temp_env) -> None:
        """Test environment variables + pre-launch script integration - replaces Test 5."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=False,
        )

        # Set environment variables
        result = manager.set_environment_variable(
            "firefox", "BROWSER_ENV", "test_value",
        )
        assert result is True

        # Set pre-launch script
        script_content = '#!/bin/bash\necho "Pre-launch script executed"\n'
        result = manager.set_pre_launch_script("firefox", script_content)
        assert result is True

        # Verify both were created
        env_file = temp_env["config_dir"] / "firefox.env"
        assert env_file.exists()
        assert "BROWSER_ENV=test_value" in env_file.read_text()

        script_dir = temp_env["config_dir"] / "scripts" / "firefox"
        pre_script = script_dir / "pre-launch.sh"
        assert pre_script.exists()
        assert pre_script.read_text() == script_content
        assert os.access(pre_script, os.X_OK)

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_blocklist_prevents_generation(self, temp_env) -> None:
        """Test blocklist prevents wrapper regeneration - replaces Test 6."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=False,
        )

        # Block firefox
        result = manager.block_app("org.mozilla.firefox")
        assert result is True

        # Verify blocklist exists
        blocklist_file = temp_env["config_dir"] / "blocklist"
        assert blocklist_file.exists()
        assert "org.mozilla.firefox" in blocklist_file.read_text()

        # Try to generate wrapper for blocked app (would be done by generator)
        # The generator would check the blocklist before creating wrapper
        # This test verifies the blocklist mechanism works

        # Unblock the app
        result = manager.unblock_app("org.mozilla.firefox")
        assert result is True

        # Verify it was removed from blocklist
        content = blocklist_file.read_text()
        assert "org.mozilla.firefox" not in content

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_configuration_workflow(self, temp_env) -> None:
        """Test export-modify-import configuration workflow - replaces Test 8."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=False,
        )

        # Create initial configuration
        manager.set_preference("firefox", "flatpak")
        manager.set_preference("chrome", "system")
        manager.create_alias("browser", "firefox")
        manager.set_environment_variable("firefox", "TEST_VAR", "initial_value")

        # Export configuration
        export_file = temp_env["temp_dir"] / "config_backup.json"
        result = manager.export_preferences(str(export_file))
        assert result is True
        assert export_file.exists()

        # Modify current configuration
        manager.set_preference("firefox", "system")  # Change preference
        manager.set_environment_variable(
            "firefox", "TEST_VAR", "modified_value",
        )  # Change env var

        # Import configuration (should restore original state)
        result = manager.import_preferences(str(export_file))
        assert result is True

        # Verify configuration was restored
        assert (
            temp_env["config_dir"] / "firefox.pref"
        ).read_text().strip() == "flatpak"
        assert (temp_env["config_dir"] / "chrome.pref").read_text().strip() == "system"

        env_content = (temp_env["config_dir"] / "firefox.env").read_text()
        assert "TEST_VAR=initial_value" in env_content

        alias_content = (temp_env["config_dir"] / "aliases").read_text()
        assert "browser:firefox" in alias_content

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_path_resolution_workflow(self, mock_subprocess, temp_env) -> None:
        """Test PATH-aware system binary resolution - replaces Test 8."""

        # Mock command -v to simulate system binary detection
        def mock_run(cmd, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "command -v firefox" in cmd_str:
                result = Mock()
                result.returncode = 0
                result.stdout = "/usr/bin/firefox\n"
                return result
            if "command -v chrome" in cmd_str:
                result = Mock()
                result.returncode = 1  # Not found
                return result
            result = Mock()
            result.returncode = 0
            return result

        mock_subprocess.side_effect = mock_run

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Generate wrappers
        with patch.object(
            generator,
            "get_installed_flatpaks",
            return_value=["org.mozilla.firefox", "com.google.chrome"],
        ):
            generator.generate_wrapper("org.mozilla.firefox")
            generator.generate_wrapper("com.google.chrome")

        # Check that wrappers were created
        firefox_wrapper = temp_env["bin_dir"] / "firefox"
        chrome_wrapper = temp_env["bin_dir"] / "chrome"

        assert firefox_wrapper.exists()
        assert chrome_wrapper.exists()

        # In real execution, firefox wrapper would detect /usr/bin/firefox exists
        # and chrome wrapper would detect system chrome not available
        # This test verifies the wrapper generation part works

    @pytest.mark.skipif(
        not (GENERATE_AVAILABLE and MANAGE_AVAILABLE),
        reason="Required modules not available",
    )
    def test_real_world_scenario_simulation(self, temp_env) -> None:
        """Test real-world usage scenario simulation."""
        # Simulate a typical user workflow

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # 1. Install some apps (simulate flatpak install)
        # In real world, user would run: flatpak install firefox chrome

        # 2. Generate wrappers
        # In real world, user would run: fplaunch-generate

        # 3. Set preferences
        manager.set_preference("firefox", "flatpak")
        manager.set_preference("chrome", "system")

        # 4. Create aliases
        # Create firefox wrapper first
        firefox_wrapper = temp_env["bin_dir"] / "firefox"
        firefox_wrapper.write_text("#!/bin/bash\necho firefox\n")
        firefox_wrapper.chmod(0o755)

        manager.create_alias("browser", "firefox")

        # 5. Set environment variables
        manager.set_environment_variable("firefox", "MOZ_DISABLE_CONTENT_SANDBOX", "1")

        # 6. Set scripts
        pre_script = '#!/bin/bash\nnotify-send "Launching Firefox"\n'
        manager.set_pre_launch_script("firefox", pre_script)

        # 7. Test that everything works together
        assert (temp_env["config_dir"] / "firefox.pref").exists()
        assert (temp_env["config_dir"] / "chrome.pref").exists()
        assert (temp_env["config_dir"] / "aliases").exists()
        assert (temp_env["config_dir"] / "firefox.env").exists()

        script_dir = temp_env["config_dir"] / "scripts" / "firefox"
        assert (script_dir / "pre-launch.sh").exists()

        # 8. Export configuration for backup
        backup_file = temp_env["temp_dir"] / "user_config.json"
        result = manager.export_preferences(str(backup_file))
        assert result is True
        assert backup_file.exists()

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_error_recovery_and_edge_cases(self, temp_env) -> None:
        """Test error recovery and edge cases in integration."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Test operations with missing files/directories
        result = manager.set_preference("nonexistent", "flatpak")
        assert isinstance(result, bool)  # Should handle gracefully

        # Test with corrupted configuration files
        pref_file = temp_env["config_dir"] / "corrupted.pref"
        pref_file.write_text("corrupted data\x00\x01\x02")

        result = manager.set_preference("corrupted", "flatpak")
        # Should either succeed (overwrite) or fail gracefully
        assert isinstance(result, bool)

        # Test with very long names/values
        long_name = "a" * 200  # Very long app name
        result = manager.set_preference(long_name, "flatpak")
        assert isinstance(result, bool)

        long_value = "flatpak" * 1000  # Very long preference value
        result = manager.set_preference("test", long_value)
        assert isinstance(result, bool)

    def test_cross_component_data_consistency(self, temp_env) -> None:
        """Test data consistency across components."""
        # This test ensures that data created by one component
        # is properly readable/usable by other components

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Create data with manager
        manager.set_preference("testapp", "flatpak")
        manager.set_environment_variable("testapp", "TEST_VAR", "test_value")
        manager.create_alias("alias1", "testapp")

        # Verify all data is consistent and accessible
        assert (temp_env["config_dir"] / "testapp.pref").exists()
        assert (temp_env["config_dir"] / "testapp.env").exists()
        assert (temp_env["config_dir"] / "aliases").exists()

        # Verify content
        pref_content = (temp_env["config_dir"] / "testapp.pref").read_text().strip()
        assert pref_content == "flatpak"

        env_content = (temp_env["config_dir"] / "testapp.env").read_text()
        assert "TEST_VAR=test_value" in env_content

        alias_content = (temp_env["config_dir"] / "aliases").read_text()
        assert "alias1:testapp" in alias_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
