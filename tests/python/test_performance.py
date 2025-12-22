#!/usr/bin/env python3
"""Performance tests for scalability and memory usage.
Tests the performance of fplaunchwrapper under load.
"""

import tempfile
import time
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


class TestPerformance:
    """Test performance."""

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

    def test_scalability_large_number_of_wrappers(self) -> None:
        """Test generating a large number of wrappers."""
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )

        # Generate a large number of wrappers
        num_wrappers = 100
        apps = []
        for i in range(num_wrappers):
            app_name = f"test_app_{i}"
            flatpak_id = f"org.test.App{i}"
            apps.append((app_name, flatpak_id))

        start_time = time.time()
        results = []
        for app_name in apps:
            result = generator.generate_wrapper(app_name)
            results.append(result)
        end_time = time.time()

        # Verify all wrappers were generated successfully
        assert all(results)

        # Verify all wrappers exist
        for app_name in apps:
            wrapper_path = self.bin_dir / app_name
            assert wrapper_path.exists()

        # Verify the performance (should complete within a reasonable time)
        elapsed_time = end_time - start_time
        assert elapsed_time < 10  # Should complete within 10 seconds

    def test_memory_usage_during_wrapper_generation(self) -> None:
        """Test memory usage during wrapper generation."""
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )

        # Generate wrappers and monitor memory usage
        num_wrappers = 50
        apps = []
        for i in range(num_wrappers):
            app_name = f"test_app_{i}"
            flatpak_id = f"org.test.App{i}"
            apps.append((app_name, flatpak_id))

        start_time = time.time()
        results = []
        for app_name in apps:
            result = generator.generate_wrapper(app_name)
            results.append(result)
        end_time = time.time()

        # Verify all wrappers were generated successfully
        assert all(results)

        # Verify the performance (should complete within a reasonable time)
        elapsed_time = end_time - start_time
        assert elapsed_time < 5  # Should complete within 5 seconds

    def test_performance_launching_multiple_apps(self) -> None:
        """Test launching multiple apps."""
        # Generate multiple wrappers
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        num_apps = 20
        apps = []
        for i in range(num_apps):
            app_name = f"test_app_{i}"
            result = generator.generate_wrapper(app_name)
            assert result is True
            apps.append(app_name)

        # Launch each app and measure performance
        start_time = time.time()
        results = []
        for app_name in apps:
            launcher = AppLauncher(app_name=app_name)
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                launch_result = launcher.launch()
                results.append(launch_result)
        end_time = time.time()

        # Verify all launch attempts were successful
        assert all(results)

        # Verify the performance (should complete within a reasonable time)
        elapsed_time = end_time - start_time
        assert elapsed_time < 5  # Should complete within 5 seconds

    def test_scalability_cleanup_operations(self) -> None:
        """Test cleanup operations for a large number of wrappers."""
        # Generate a large number of wrappers
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        num_wrappers = 50
        apps = []
        for i in range(num_wrappers):
            app_name = f"test_app_{i}"
            result = generator.generate_wrapper(app_name)
            assert result is True
            apps.append(app_name)

        # Clean up all wrappers and measure performance
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir)
        )
        start_time = time.time()
        results = []
        for app_name in apps:
            cleanup_result = cleanup.cleanup_app(app_name)
            results.append(cleanup_result)
        end_time = time.time()

        # Verify all cleanup operations were successful
        assert all(results)

        # Verify all wrappers were removed
        for app_name in apps:
            wrapper_path = self.bin_dir / app_name
            assert not wrapper_path.exists()

        # Verify the performance (should complete within a reasonable time)
        elapsed_time = end_time - start_time
        assert elapsed_time < 5  # Should complete within 5 seconds

    def test_memory_usage_during_launch(self) -> None:
        """Test memory usage during app launch."""
        # Generate a wrapper
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        app_name = "test_app"
        result = generator.generate_wrapper(app_name)
        assert result is True

        # Launch the app multiple times and measure performance
        launcher = AppLauncher(app_name=app_name)
        num_launches = 10
        start_time = time.time()
        results = []
        for _ in range(num_launches):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                launch_result = launcher.launch()
                results.append(launch_result)
        end_time = time.time()

        # Verify all launch attempts were successful
        assert all(results)

        # Verify the performance (should complete within a reasonable time)
        elapsed_time = end_time - start_time
        assert elapsed_time < 2  # Should complete within 2 seconds

    def test_performance_wrapper_management(self) -> None:
        """Test performance of wrapper management operations."""
        # Generate multiple wrappers
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True
        )
        num_apps = 30
        apps = []
        for i in range(num_apps):
            app_name = f"test_app_{i}"
            result = generator.generate_wrapper(app_name)
            assert result is True
            apps.append(app_name)

        # Set preferences for all apps and measure performance
        manager = WrapperManager(
            config_dir=str(self.config_dir),
            verbose=True
        )
        start_time = time.time()
        results = []
        for app_name, flatpak_id in apps:
            pref_result = manager.set_preference(app_name, flatpak_id)
            results.append(pref_result)
        end_time = time.time()

        # Verify all preference operations were successful
        assert all(results)

        # Verify the performance (should complete within a reasonable time)
        elapsed_time = end_time - start_time
        assert elapsed_time < 3  # Should complete within 3 seconds

    def test_scalability_mixed_operations(self) -> None:
        """Test mixed operations (generate, launch, cleanup)."""
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir)
        )
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir)
        )

        # Perform mixed operations
        num_operations = 20
        start_time = time.time()
        for i in range(num_operations):
            app_name = f"test_app_{i}"

            # Generate a wrapper
            result = generator.generate_wrapper(app_name)
            assert result is True

            # Launch the app
            launcher = AppLauncher(app_name=app_name)
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                launch_result = launcher.launch()
                assert launch_result is True

            # Clean up the wrapper
            cleanup_result = cleanup.cleanup_app(app_name)
            assert cleanup_result is True
        end_time = time.time()

        # Verify the performance (should complete within a reasonable time)
        elapsed_time = end_time - start_time
        assert elapsed_time < 10  # Should complete within 10 seconds
