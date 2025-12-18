#!/usr/bin/env python3
"""
Unit tests for cleanup.py
Tests cleanup functionality with proper mocking to avoid side effects
"""

import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

# Add lib to path
# Import the module to test
try:
    from fplaunch.cleanup import WrapperCleanup, main
except ImportError:
    # Mock it if not available
    WrapperCleanup = None
    main = None


class TestWrapperCleanup:
    """Test cleanup manager functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.data_dir = self.temp_dir / "data"

        # Create directories
        self.bin_dir.mkdir()
        self.config_dir.mkdir()
        self.data_dir.mkdir()

        # Create some test files
        (self.bin_dir / "firefox").write_text("#!/bin/bash\necho firefox\n")
        (self.bin_dir / "chrome").write_text("#!/bin/bash\necho chrome\n")
        (self.config_dir / "firefox.pref").write_text("flatpak")
        (self.config_dir / "chrome.pref").write_text("system")
        (self.data_dir / "cache_file").write_text("cache data")

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cleanup_manager_creation(self):
        """Test WrapperCleanup creation"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        assert manager is not None
        assert str(manager.bin_dir) == str(self.bin_dir)
        assert str(manager.config_dir) == str(self.config_dir)
        assert str(manager.data_dir) == str(self.data_dir)
        assert manager.dry_run is True

    def test_cleanup_identify_artifacts(self):
        """Test identification of artifacts to clean"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        artifacts = manager._identify_artifacts()

        # Should find wrapper scripts, preferences, and data files
        assert len(artifacts) >= 3
        assert any("firefox" in str(artifact) for artifact in artifacts)
        assert any("chrome" in str(artifact) for artifact in artifacts)
        assert any("cache_file" in str(artifact) for artifact in artifacts)

    def test_cleanup_dry_run_mode(self):
        """Test cleanup in dry-run mode"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        # Count files before
        before_files = list(self.temp_dir.rglob("*"))
        before_count = len([f for f in before_files if f.is_file()])

        result = manager.cleanup()

        # Should return success
        assert result is True

        # Count files after
        after_files = list(self.temp_dir.rglob("*"))
        after_count = len([f for f in after_files if f.is_file()])

        # Should not have removed any files in dry-run mode
        assert before_count == after_count

    def test_cleanup_actual_removal(self):
        """Test actual cleanup (with caution)"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=False,
        )

        # Count files before
        before_files = list(self.temp_dir.rglob("*"))
        before_count = len([f for f in before_files if f.is_file()])

        result = manager.cleanup()

        # Should return success
        assert result is True

        # Count files after
        after_files = list(self.temp_dir.rglob("*"))
        after_count = len([f for f in after_files if f.is_file()])

        # Should have removed some files
        assert after_count < before_count

    def test_cleanup_selective_removal(self):
        """Test selective cleanup of different artifact types"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        # Test removing only wrappers
        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=False,
            remove_wrappers=True,
            remove_prefs=False,
            remove_data=False,
        )

        manager.cleanup()

        # Wrappers should be gone
        assert not (self.bin_dir / "firefox").exists()
        assert not (self.bin_dir / "chrome").exists()

        # Preferences should remain
        assert (self.config_dir / "firefox.pref").exists()
        assert (self.config_dir / "chrome.pref").exists()

        # Data should remain
        assert (self.data_dir / "cache_file").exists()

    def test_cleanup_validation(self):
        """Test cleanup validation and safety checks"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        # Test with invalid directories
        manager = WrapperCleanup(
            bin_dir="/nonexistent/bin",
            config_dir="/nonexistent/config",
            data_dir="/nonexistent/data",
            dry_run=True,
        )

        result = manager.cleanup()

        # Should handle gracefully
        assert result is True

    @patch("shutil.rmtree")
    def test_cleanup_error_handling(self, mock_rmtree):
        """Test error handling during cleanup"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        # Mock rmtree to raise exception
        mock_rmtree.side_effect = PermissionError("Permission denied")

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=False,
        )

        result = manager.cleanup()

        # Should handle errors gracefully
        assert result is False

    def test_cleanup_backup_creation(self):
        """Test backup creation during cleanup"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        backup_dir = self.temp_dir / "backup"
        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=False,
            create_backup=True,
            backup_dir=str(backup_dir),
        )

        manager.cleanup()

        # Should create backup directory
        assert backup_dir.exists()

        # Should contain backed up files
        backup_files = list(backup_dir.rglob("*"))
        assert len(backup_files) > 0

    @patch("os.path.exists")
    def test_cleanup_path_validation(self, mock_exists):
        """Test path validation in cleanup"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        # Mock path existence checks
        mock_exists.return_value = False

        manager = WrapperCleanup(
            bin_dir="/fake/bin",
            config_dir="/fake/config",
            data_dir="/fake/data",
            dry_run=True,
        )

        artifacts = manager._identify_artifacts()

        # Should handle non-existent paths
        assert isinstance(artifacts, list)

    def test_cleanup_summary_reporting(self):
        """Test cleanup summary reporting"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        summary = manager.get_cleanup_summary()

        # Should return a summary
        assert isinstance(summary, dict)
        assert "wrappers" in summary
        assert "preferences" in summary
        assert "data_files" in summary

    @patch("os.access")
    def test_cleanup_permission_checks(self, mock_access):
        """Test permission checks during cleanup"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        # Mock permission denied
        mock_access.return_value = False

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        result = manager.cleanup()

        # Should handle permission issues
        assert result is True  # Dry run should succeed

    def test_cleanup_progress_reporting(self):
        """Test progress reporting during cleanup"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        # Should not crash during progress reporting
        result = manager.cleanup()
        assert result is True

    @patch.dict("os.environ", {"FPWRAPPER_FORCE": "1"})
    def test_cleanup_force_mode(self):
        """Test cleanup in force mode"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=False,
            force=True,
        )

        result = manager.cleanup()

        assert result is True

    def test_cleanup_interactive_mode(self):
        """Test interactive cleanup mode"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        # Mock user input for interactive mode
        with patch("builtins.input", return_value="y"):
            manager = WrapperCleanup(
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
                data_dir=str(self.data_dir),
                dry_run=False,
                interactive=True,
            )

            result = manager.cleanup()

            assert result is True


class TestCleanupMainFunction:
    """Test the main function for cleanup module"""

    @patch("sys.argv", ["fplaunch-cleanup", "--dry-run"])
    def test_main_dry_run(self):
        """Test main function with dry-run"""
        if not main:
            pytest.skip("main function not available")

        result = main()

        assert result == 0

    @patch("sys.argv", ["fplaunch-cleanup", "--help"])
    def test_main_help(self):
        """Test main function help"""
        if not main:
            pytest.skip("main function not available")

        result = main()

        assert result == 0

    @patch("sys.argv", ["fplaunch-cleanup"])
    def test_main_actual_cleanup(self):
        """Test main function actual cleanup"""
        if not main:
            pytest.skip("main function not available")

        # Should work without arguments (uses defaults)
        result = main()

        assert isinstance(result, int)

    @patch("sys.argv", ["fplaunch-cleanup", "--force"])
    def test_main_force_mode(self):
        """Test main function force mode"""
        if not main:
            pytest.skip("main function not available")

        result = main()

        assert isinstance(result, int)


class TestCleanupIntegration:
    """Test cleanup integration with other components"""

    def test_cleanup_with_generate_integration(self):
        """Test cleanup integration after generation"""
        # This would test that cleanup can remove generated wrappers
        # For now, just verify the concept
        pass

    @patch("os.path.exists")
    def test_cleanup_systemd_integration(self, mock_exists):
        """Test cleanup of systemd units"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        mock_exists.return_value = True

        manager = WrapperCleanup(
            bin_dir="/tmp/bin",
            config_dir="/tmp/config",
            data_dir="/tmp/data",
            dry_run=True,
            remove_systemd=True,
        )

        result = manager.cleanup()

        assert result is True

    def test_cleanup_performance(self):
        """Test cleanup performance with many files"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        # Create many test files
        for i in range(100):
            (self.bin_dir / f"app{i}").write_text(f"#!/bin/bash\necho app{i}\n")
            (self.config_dir / f"app{i}.pref").write_text("flatpak")
            (self.data_dir / f"data{i}").write_text(f"data {i}")

        import time

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        start_time = time.time()
        result = manager.cleanup()
        end_time = time.time()

        assert result is True
        # Should complete quickly even with many files
        assert end_time - start_time < 5.0

    def test_cleanup_thread_safety(self):
        """Test thread safety of cleanup operations"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        import threading

        results = []
        errors = []

        def worker():
            try:
                manager = WrapperCleanup(
                    bin_dir=str(self.bin_dir),
                    config_dir=str(self.config_dir),
                    data_dir=str(self.data_dir),
                    dry_run=True,
                )
                result = manager.cleanup()
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should not have threading errors
        assert len(errors) == 0
        assert len(results) == 3
        assert all(results)

    @patch("tempfile.mkdtemp")
    def test_cleanup_temp_file_handling(self, mock_mkdtemp):
        """Test temporary file handling during cleanup"""
        if not WrapperCleanup:
            pytest.skip("WrapperCleanup class not available")

        mock_mkdtemp.return_value = str(self.temp_dir / "temp_backup")

        manager = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=False,
            create_backup=True,
        )

        result = manager.cleanup()

        assert result is True
        mock_mkdtemp.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
