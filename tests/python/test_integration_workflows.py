#!/usr/bin/env python3
"""Integration tests for cross-module interactions and end-to-end workflows.
Tests the interaction between different modules in fplaunchwrapper.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the project root to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fplaunch.generate import WrapperGenerator
from fplaunch.launch import AppLauncher
from fplaunch.manage import WrapperManager
from fplaunch.cleanup import WrapperCleanup


class TestIntegrationWorkflows:
    """Test integration workflows."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.bin_dir.mkdir()
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_wrapper_generation_and_launch(self) -> None:
        """Test generating a wrapper and launching it."""
        # Generate a wrapper
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        app_name = "test_app"
        flatpak_id = "org.test.App"
        result = generator.generate_wrapper(app_name, flatpak_id=flatpak_id)
        assert result is True

        # Verify the wrapper was created
        wrapper_path = self.bin_dir / app_name
        assert wrapper_path.exists()

        # Launch the app using the wrapper
        launcher = AppLauncher(app_name=app_name)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            launch_result = launcher.launch()
            assert launch_result is True

    def test_wrapper_management_and_cleanup(self) -> None:
        """Test managing wrappers and cleaning up."""
        # Generate a wrapper
        flatpak_id = "org.test.App"
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        app_name = "test_app"
        result = generator.generate_wrapper(app_name, flatpak_id=flatpak_id)
        assert result is True

        # Set a preference
        manager = WrapperManager(
            config_dir=str(self.config_dir),
            verbose=True
        )
        # Use standard preference value instead of flatpak_id
        pref_result = manager.set_preference(app_name, "flatpak")
        assert pref_result is True

        # Clean up the wrapper
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        cleanup_result = cleanup.cleanup_app(app_name)
        assert cleanup_result is True

        # Verify the wrapper was removed
        wrapper_path = self.bin_dir / app_name
        assert not wrapper_path.exists()

    def test_end_to_end_workflow(self) -> None:
        """Test a complete end-to-end workflow."""
        # Generate multiple wrappers
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        apps = [
            ("app1", "org.test.App1"),
            ("app2", "org.test.App2"),
            ("app3", "org.test.App3")
        ]
        for app_name, flatpak_id in apps:
            result = generator.generate_wrapper(app_name, flatpak_id=flatpak_id)
            assert result is True

        # Set preferences for the apps
        manager = WrapperManager(
            config_dir=str(self.config_dir),
            verbose=True
        )
        for app_name, flatpak_id in apps:
            pref_result = manager.set_preference(app_name, flatpak_id)
            assert pref_result is True

        # Launch each app
        for app_name, flatpak_id in apps:
            launcher = AppLauncher(app_name=app_name)
            with patch("subprocess.run") as mock_run, patch("fplaunch.safety.safe_launch_check", return_value=True):
                mock_run.return_value = Mock(returncode=0)
                launch_result = launcher.launch()
                assert launch_result is True

        # Clean up all wrappers
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        for app_name, _ in apps:
            cleanup_result = cleanup.cleanup_app(app_name)
            assert cleanup_result is True

        # Verify all wrappers were removed
        for app_name, _ in apps:
            wrapper_path = self.bin_dir / app_name
            assert not wrapper_path.exists()

    def test_cross_module_interaction(self) -> None:
        """Test interaction between WrapperManager and WrapperGenerator."""
        # Generate a wrapper
        flatpak_id = "org.test.App"
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        app_name = "test_app"
        result = generator.generate_wrapper(app_name, flatpak_id=flatpak_id)
        assert result is True

        # Use WrapperManager to set a preference
        manager = WrapperManager(
            config_dir=str(self.config_dir),
            verbose=True
        )
        pref_result = manager.set_preference(app_name, flatpak_id)
        assert pref_result is True

        # Verify the preference file was created
        pref_file = self.config_dir / f"{app_name}.pref"
        assert pref_file.exists()

        # Verify the preference content
        pref_content = pref_file.read_text()
        assert flatpak_id in pref_content

    def test_wrapper_generation_with_preferences(self) -> None:
        """Test generating wrappers with preferences."""
        # Set a preference first
        manager = WrapperManager(
            config_dir=str(self.config_dir),
            verbose=True
        )
        app_name = "test_app"
        flatpak_id = "org.test.App"
        pref_result = manager.set_preference(app_name, flatpak_id)
        assert pref_result is True

        # Generate a wrapper
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        result = generator.generate_wrapper(app_name, flatpak_id=flatpak_id)
        assert result is True

        # Verify the wrapper was created
        wrapper_path = self.bin_dir / app_name
        assert wrapper_path.exists()

        # Verify the wrapper content includes the flatpak_id
        wrapper_content = wrapper_path.read_text()
        assert flatpak_id in wrapper_content
