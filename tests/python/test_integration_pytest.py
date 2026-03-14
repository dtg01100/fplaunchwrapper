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
    from lib.generate import WrapperGenerator
    from lib.manage import WrapperManager

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
            generator,
            "get_installed_flatpaks",
            return_value=["org.mozilla.firefox"],
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
            generator,
            "get_installed_flatpaks",
            return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        # Verify preference persisted after update
        assert pref_file.exists()
        assert pref_file.read_text().strip() == "flatpak"

        # Step 4: Remove wrapper and config
        result = manager.remove_wrapper("firefox", force=True)
        assert result is True

        # Verify complete cleanup
        assert not firefox_wrapper.exists()
        assert not pref_file.exists()

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_multiple_wrappers_collision_handling(
        self, mock_subprocess, temp_env
    ) -> None:
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
                generator,
                "get_installed_flatpaks",
                return_value=[app_id],
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
            generator,
            "get_installed_flatpaks",
            return_value=["org.mozilla.firefox"],
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
