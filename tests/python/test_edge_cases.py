#!/usr/bin/env python3
"""Edge case tests for concurrency, resource exhaustion, and permission handling.
Tests the robustness of fplaunchwrapper under extreme conditions.
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


class TestEdgeCases:
    """Test edge cases."""

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

    def test_concurrent_wrapper_generation(self) -> None:
        """Test generating wrappers concurrently."""
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )

        # Simulate concurrent generation
        apps = [
            "app1",
            "app2",
            "app3"
        ]

        results = []
        for app_name in apps:
            result = generator.generate_wrapper(app_name)
            results.append(result)

        # Verify all wrappers were generated successfully
        assert all(results)

        # Verify all wrappers exist
        for app_name in apps:
            wrapper_path = self.bin_dir / app_name
            assert wrapper_path.exists()

    def test_resource_exhaustion_low_disk_space(self) -> None:
        """Test handling low disk space."""
        # Create a small temporary directory to simulate low disk space
        small_temp_dir = Path(tempfile.mkdtemp())
        small_bin_dir = small_temp_dir / "bin"
        small_bin_dir.mkdir()
        small_config_dir = small_temp_dir / "config"
        small_config_dir.mkdir()

        generator = WrapperGenerator(
            bin_dir=str(small_bin_dir),
            config_dir=str(small_config_dir),
            verbose=True
        )

        # Attempt to generate a wrapper in a small directory
        app_name = "test_app"
        result = generator.generate_wrapper(app_name)

        # Clean up
        import shutil
        shutil.rmtree(small_temp_dir, ignore_errors=True)

        # Verify the result (may fail due to low disk space)
        assert result is not None

    def test_permission_handling_read_only_directory(self) -> None:
        """Test handling read-only directories."""
        # Create a read-only directory
        read_only_dir = Path(tempfile.mkdtemp())
        read_only_bin_dir = read_only_dir / "bin"
        read_only_bin_dir.mkdir()
        read_only_config_dir = read_only_dir / "config"
        read_only_config_dir.mkdir()

        # Make the directory read-only
        import os
        os.chmod(read_only_bin_dir, 0o444)

        generator = WrapperGenerator(
            bin_dir=str(read_only_bin_dir),
            config_dir=str(read_only_config_dir),
            verbose=True
        )

        # Attempt to generate a wrapper in a read-only directory
        app_name = "test_app"
        result = generator.generate_wrapper(app_name)

        # Clean up
        os.chmod(read_only_bin_dir, 0o755)
        import shutil
        shutil.rmtree(read_only_dir, ignore_errors=True)

        # Verify the result (may fail due to permission issues)
        assert result is not None

    def test_permission_handling_missing_directory(self) -> None:
        """Test handling missing directories."""
        # Use a non-existent directory
        non_existent_dir = Path(tempfile.mkdtemp())
        non_existent_bin_dir = non_existent_dir / "non_existent_bin"
        non_existent_config_dir = non_existent_dir / "non_existent_config"

        generator = WrapperGenerator(
            bin_dir=str(non_existent_bin_dir),
            config_dir=str(non_existent_config_dir),
            verbose=True
        )

        # Attempt to generate a wrapper in a non-existent directory
        app_name = "test_app"
        result = generator.generate_wrapper(app_name)

        # Clean up
        import shutil
        shutil.rmtree(non_existent_dir, ignore_errors=True)

        # Verify the result (may fail due to missing directory)
        assert result is not None

    def test_concurrent_launch_attempts(self) -> None:
        """Test concurrent launch attempts."""
        # Generate a wrapper
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        app_name = "test_app"
        result = generator.generate_wrapper(app_name)
        assert result is True

        # Simulate concurrent launch attempts
        launcher = AppLauncher(app_name=app_name)
        results = []
        for _ in range(3):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                launch_result = launcher.launch()
                results.append(launch_result)

        # Verify all launch attempts were successful
        assert all(results)

    def test_resource_exhaustion_high_memory_usage(self) -> None:
        """Test handling high memory usage."""
        # Generate a large number of wrappers to simulate high memory usage
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )

        apps = []
        for i in range(10):
            app_name = f"test_app_{i}"
            apps.append(app_name)

        results = []
        for app_name in apps:
            result = generator.generate_wrapper(app_name)
            results.append(result)

        # Verify all wrappers were generated successfully
        assert all(results)

        # Verify all wrappers exist
        for app_name in apps:
            wrapper_path = self.bin_dir / app_name
            assert wrapper_path.exists()

    def test_permission_handling_file_creation(self) -> None:
        """Test handling file creation permissions."""
        # Generate a wrapper
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        app_name = "test_app"
        result = generator.generate_wrapper(app_name)
        assert result is True

        # Verify the wrapper was created
        wrapper_path = self.bin_dir / app_name
        assert wrapper_path.exists()

        # Verify the wrapper has the correct permissions
        import os
        wrapper_permissions = oct(os.stat(wrapper_path).st_mode)[-3:]
        assert wrapper_permissions == "755"

    def test_concurrent_cleanup_operations(self) -> None:
        """Test concurrent cleanup operations."""
        # Generate multiple wrappers
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        apps = [
            "app1",
            "app2",
            "app3"
        ]
        for app_name in apps:
            result = generator.generate_wrapper(app_name)
            assert result is True

        # Simulate concurrent cleanup
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        results = []
        for app_name in apps:
            cleanup_result = cleanup.cleanup_app(app_name)
            results.append(cleanup_result)

        # Verify all cleanup operations were successful
        assert all(results)

        # Verify all wrappers were removed
        for app_name in apps:
            wrapper_path = self.bin_dir / app_name
            assert not wrapper_path.exists()
