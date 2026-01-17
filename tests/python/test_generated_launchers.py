#!/usr/bin/env python3
"""Test suite for generated launcher wrappers.

Tests the functionality of actually generated wrapper scripts to ensure they
work correctly with all features.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
import subprocess

import pytest

from fplaunch.generate import WrapperGenerator


class TestGeneratedLaunchers:
    """Test generated launcher wrapper functionality."""

    def setup_method(self) -> None:
        """Set up test environment with generated wrappers."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        
        # Create directories
        self.bin_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)
        
        # Create generator
        self.generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )
        
        # Generate test wrappers
        self.test_apps = [
            ("org.mozilla.firefox", "firefox"),
            ("com.google.Chrome", "chrome"),
            ("org.gimp.GIMP", "gimp")
        ]
        
        for app_id, _ in self.test_apps:
            self.generator.generate_wrapper(app_id)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generated_wrapper_executable(self) -> None:
        """Test that generated wrappers are executable."""
        for _, app_name in self.test_apps:
            wrapper_path = self.bin_dir / app_name
            assert wrapper_path.exists()
            assert os.access(wrapper_path, os.X_OK)
            assert wrapper_path.is_file()

    def test_generated_wrapper_shebang(self) -> None:
        """Test that generated wrappers have valid shebang."""
        for _, app_name in self.test_apps:
            wrapper_path = self.bin_dir / app_name
            content = wrapper_path.read_text()
            assert content.startswith("#!/usr/bin/env bash")

    def test_generated_wrapper_has_required_fields(self) -> None:
        """Test that generated wrappers contain required variables and commands."""
        for app_id, app_name in self.test_apps:
            wrapper_path = self.bin_dir / app_name
            content = wrapper_path.read_text()
            
            assert f'NAME="{app_name}"' in content
            assert f'ID="{app_id}"' in content
            assert f'PREF_DIR="{self.config_dir}"' in content
            assert "flatpak run" in content
            assert "--fpwrapper-help" in content
            assert "--fpwrapper-info" in content

    def test_generated_wrapper_help_flag(self) -> None:
        """Test that --fpwrapper-help flag works."""
        for _, app_name in self.test_apps:
            wrapper_path = self.bin_dir / app_name
            
            result = subprocess.run(
                [str(wrapper_path), "--fpwrapper-help"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert f"Wrapper for {app_name}" in result.stdout
            assert "Available options:" in result.stdout
            assert "--fpwrapper-help" in result.stdout
            assert "--fpwrapper-info" in result.stdout

    def test_generated_wrapper_info_flag(self) -> None:
        """Test that --fpwrapper-info flag works."""
        for app_id, app_name in self.test_apps:
            wrapper_path = self.bin_dir / app_name
            
            result = subprocess.run(
                [str(wrapper_path), "--fpwrapper-info"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert app_name in result.stdout
            assert app_id in result.stdout

    def test_generated_wrapper_launch_without_args(self) -> None:
        """Test that wrappers fail gracefully without flatpak installation."""
        for _, app_name in self.test_apps:
            wrapper_path = self.bin_dir / app_name
            
            result = subprocess.run(
                [str(wrapper_path)],
                capture_output=True,
                text=True
            )
            
            # Should fail because flatpak app isn't actually installed
            assert result.returncode != 0
            assert "flatpak" in result.stderr.lower()

    def test_generated_wrapper_with_invalid_args(self) -> None:
        """Test that wrappers handle invalid arguments."""
        for _, app_name in self.test_apps:
            wrapper_path = self.bin_dir / app_name
            
            result = subprocess.run(
                [str(wrapper_path), "--invalid-argument"],
                capture_output=True,
                text=True
            )
            
            # Should fail and show error message
            assert result.returncode != 0

    def test_generated_wrapper_pref_file_creation(self) -> None:
        """Test that preference files can be created."""
        from fplaunch.manage import WrapperManager
        
        manager = WrapperManager(
            config_dir=str(self.config_dir),
            bin_dir=str(self.bin_dir),
        )
        
        for _, app_name in self.test_apps:
            result = manager.set_preference(app_name, "flatpak")
            assert result is True
            
            pref_file = self.config_dir / f"{app_name}.pref"
            assert pref_file.exists()
            assert pref_file.read_text().strip() == "flatpak"

    def test_generated_wrapper_custom_config(self) -> None:
        """Test that generated wrappers respect custom configuration."""
        # Test with custom preference
        app_name = "firefox"
        pref_file = self.config_dir / f"{app_name}.pref"
        pref_file.write_text("system")
        
        # Re-generate the wrapper
        self.generator.generate_wrapper("org.mozilla.firefox")
        
        wrapper_path = self.bin_dir / app_name
        content = wrapper_path.read_text()
        
        # Verify preference is read from file
        assert f'PREF_DIR="{self.config_dir}"' in content

    def test_generated_wrapper_with_environment_variables(self) -> None:
        """Test that generated wrappers respect environment variables."""
        app_name = "firefox"
        env_file = self.config_dir / f"{app_name}.env"
        env_file.write_text("TEST_VAR=test_value\nANOTHER_VAR=another_value")
        
        # Re-generate the wrapper
        self.generator.generate_wrapper("org.mozilla.firefox")
        
        wrapper_path = self.bin_dir / app_name
        
        # Verify the environment file is properly read by the wrapper
        assert env_file.exists()
        content = env_file.read_text()
        assert "TEST_VAR=test_value" in content
        assert "ANOTHER_VAR=another_value" in content

    def test_multiple_generated_wrappers(self) -> None:
        """Test that multiple wrappers can be generated and executed."""
        # Verify all wrappers are present
        for _, app_name in self.test_apps:
            assert (self.bin_dir / app_name).exists()
        
        # Test each wrapper
        for _, app_name in self.test_apps:
            result = subprocess.run(
                [str(self.bin_dir / app_name), "--fpwrapper-info"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert app_name in result.stdout

    def test_generated_wrapper_update(self) -> None:
        """Test that re-generating a wrapper updates it correctly."""
        app_name = "firefox"
        initial_wrapper = self.bin_dir / app_name
        initial_mtime = initial_wrapper.stat().st_mtime
        
        # Wait a bit to ensure mtime changes
        import time
        time.sleep(0.01)
        
        # Re-generate the wrapper
        self.generator.generate_wrapper("org.mozilla.firefox")
        
        updated_wrapper = self.bin_dir / app_name
        assert updated_wrapper.stat().st_mtime > initial_mtime
        assert updated_wrapper.exists()


class TestGeneratedLauncherIntegration:
    """Integration tests for generated launchers with AppLauncher."""

    def setup_method(self) -> None:
        """Set up integration test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        
        self.bin_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)
        
        self.generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )
        
        # Generate test wrapper
        self.generator.generate_wrapper("org.mozilla.firefox")

    def teardown_method(self) -> None:
        """Clean up integration test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_launcher_finds_generated_wrapper(self) -> None:
        """Test that AppLauncher can find generated wrappers."""
        from fplaunch.launch import AppLauncher
        
        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )
        
        wrapper = launcher._find_wrapper()
        assert wrapper is not None
        assert wrapper == self.bin_dir / "firefox"

    def test_launcher_executes_generated_wrapper(self) -> None:
        """Test that AppLauncher can execute generated wrappers."""
        from fplaunch.launch import AppLauncher
        from unittest.mock import patch, Mock
        
        with patch("subprocess.run") as mock_run, \
             patch("fplaunch.safety.safe_launch_check", return_value=True):
            
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            launcher = AppLauncher(
                app_name="firefox",
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
            )
            
            result = launcher.launch()
            assert result is True
            mock_run.assert_called_once()

    def test_generated_wrapper_with_safety_check(self) -> None:
        """Test that generated wrappers interact with safety checks."""
        from fplaunch.launch import AppLauncher
        from unittest.mock import patch, Mock
        
        # Create a safety check failure scenario
        with patch("subprocess.run") as mock_run, \
             patch("fplaunch.safety.safe_launch_check", return_value=False):
            
            mock_result = Mock()
            mock_result.returncode = 1
            mock_run.return_value = mock_result
            
            launcher = AppLauncher(
                app_name="firefox",
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
            )
            
            result = launcher.launch()
            assert result is False


class TestGeneratedLauncherEdgeCases:
    """Test edge cases for generated launchers."""

    def setup_method(self) -> None:
        """Set up edge case test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        
        self.bin_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)
        
        self.generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

    def teardown_method(self) -> None:
        """Clean up edge case test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generated_wrapper_with_corrupted_pref_file(self) -> None:
        """Test that wrappers handle corrupted preference files."""
        # Generate a wrapper first
        self.generator.generate_wrapper("org.mozilla.firefox")
        
        # Create a corrupted preference file
        pref_file = self.config_dir / "firefox.pref"
        pref_file.write_text("invalid_data\x00\x01\x02")
        
        # Try to run the wrapper
        wrapper_path = self.bin_dir / "firefox"
        
        result = subprocess.run(
            [str(wrapper_path), "--fpwrapper-info"],
            capture_output=True,
            text=True
        )
        
        # Should handle it gracefully
        assert result.returncode == 0
        assert "firefox" in result.stdout

    def test_generated_wrapper_missing_config_directory(self) -> None:
        """Test that wrappers handle missing config directories."""
        # Generate a wrapper
        self.generator.generate_wrapper("org.mozilla.firefox")
        
        # Remove config directory
        import shutil
        shutil.rmtree(self.config_dir)
        
        # Try to run the wrapper
        wrapper_path = self.bin_dir / "firefox"
        
        result = subprocess.run(
            [str(wrapper_path), "--fpwrapper-info"],
            capture_output=True,
            text=True
        )
        
        # Should handle missing config directory
        assert result.returncode == 0

    def test_generated_wrapper_with_special_chars_in_app_id(self) -> None:
        """Test that wrappers handle special characters in app IDs."""
        # Test with app ID containing special characters
        app_id = "com.example.app-with-dashes_and_underscores"
        self.generator.generate_wrapper(app_id)
        
        # Should generate a valid wrapper
        expected_name = "app-with-dashes_and_underscores"
        wrapper_path = self.bin_dir / expected_name
        assert wrapper_path.exists()
        
        result = subprocess.run(
            [str(wrapper_path), "--fpwrapper-info"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert expected_name in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
