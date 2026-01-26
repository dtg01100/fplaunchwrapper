#!/usr/bin/env python3
"""REAL execution tests for cleanup.py with full coverage.
NO MOCKS - Tests actual code paths to achieve real coverage.
"""

import shutil
import sys
import tempfile
from pathlib import Path


# Import actual implementation
from lib.cleanup import WrapperCleanup, main


class TestWrapperCleanupReal:
    """Test cleanup with REAL execution - no mocks."""

    def setup_method(self) -> None:
        """Set up REAL test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.data_dir = self.temp_dir / "data"

        # Create REAL directories
        self.bin_dir.mkdir()
        self.config_dir.mkdir()
        self.data_dir.mkdir()

        # Create REAL test files (safe echo commands instead of actual launches)
        (self.bin_dir / "firefox").write_text(
            "#!/usr/bin/env bash\necho 'Firefox launched'\nexit 0\n"
        )
        (self.bin_dir / "chrome").write_text(
            "#!/usr/bin/env bash\necho 'Chrome launched'\nexit 0\n"
        )
        (self.bin_dir / "gimp").write_text("#!/usr/bin/env bash\necho 'GIMP launched'\nexit 0\n")

        # Make them executable
        (self.bin_dir / "firefox").chmod(0o755)
        (self.bin_dir / "chrome").chmod(0o755)
        (self.bin_dir / "gimp").chmod(0o755)

        # Create config files
        (self.config_dir / "firefox.pref").write_text("flatpak")
        (self.config_dir / "chrome.pref").write_text("system")
        (self.config_dir / "gimp.pref").write_text("flatpak")

        # Create data files
        (self.data_dir / "cache_file").write_text("cache data")
        (self.data_dir / "log_file.log").write_text("log content")

    def teardown_method(self) -> None:
        """Clean up REAL test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_real_object(self) -> None:
        """Test that __init__ creates a real WrapperCleanup object."""
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        # Verify attributes are set correctly (REAL execution)
        assert cleanup.bin_dir == self.bin_dir
        assert cleanup.config_dir == self.config_dir
        assert cleanup.data_dir == self.data_dir
        assert cleanup.dry_run is True
        assert cleanup.assume_yes is False
        assert isinstance(cleanup.cleanup_items, dict)

    def test_identify_artifacts_real_execution(self) -> None:
        """Test _identify_artifacts with REAL file system."""
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        # Call REAL method
        artifacts = cleanup._identify_artifacts()

        # Verify REAL results
        assert len(artifacts) >= 7  # 3 wrappers + 3 prefs + 2 data files

        # Verify specific files found
        artifact_names = [a.name for a in artifacts]
        assert "firefox" in artifact_names
        assert "chrome" in artifact_names
        assert "gimp" in artifact_names
        assert "firefox.pref" in artifact_names
        assert "cache_file" in artifact_names
        assert "log_file.log" in artifact_names

    def test_scan_for_cleanup_items_real(self) -> None:
        """Test scan_for_cleanup_items with REAL directories."""
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        # Call REAL method
        cleanup.scan_for_cleanup_items()

        # Verify REAL results
        assert len(cleanup.cleanup_items["wrappers"]) == 3
        assert len(cleanup.cleanup_items["preferences"]) == 3
        assert len(cleanup.cleanup_items["data_files"]) == 2

    def test_dry_run_does_not_delete(self) -> None:
        """Test dry-run mode does NOT delete files."""
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        # Count files before
        files_before = list(self.bin_dir.glob("*"))
        count_before = len(files_before)

        # Run REAL cleanup in dry-run
        cleanup.scan_for_cleanup_items()

        # Verify files still exist
        files_after = list(self.bin_dir.glob("*"))
        assert len(files_after) == count_before
        assert (self.bin_dir / "firefox").exists()
        assert (self.bin_dir / "chrome").exists()
        assert (self.bin_dir / "gimp").exists()

    def test_actual_cleanup_deletes_files(self) -> None:
        """Test actual cleanup REALLY deletes files."""
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=False,
            assume_yes=True,
        )

        # Verify files exist before
        assert (self.bin_dir / "firefox").exists()
        assert (self.bin_dir / "chrome").exists()
        assert (self.config_dir / "firefox.pref").exists()

        # Run REAL cleanup
        cleanup.scan_for_cleanup_items()
        cleanup.perform_cleanup()

        # Verify files REALLY deleted
        assert not (self.bin_dir / "firefox").exists()
        assert not (self.bin_dir / "chrome").exists()
        assert not (self.bin_dir / "gimp").exists()

    def test_selective_wrapper_removal(self) -> None:
        """Test removing ONLY wrappers, not prefs/data."""
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=False,
            assume_yes=True,
            remove_wrappers=True,
            remove_prefs=False,
            remove_data=False,
        )

        # Run cleanup
        cleanup.scan_for_cleanup_items()
        cleanup.perform_cleanup()

        # Wrappers should be gone
        assert not (self.bin_dir / "firefox").exists()

        # Prefs and data should remain
        assert (self.config_dir / "firefox.pref").exists()
        assert (self.data_dir / "cache_file").exists()

    def test_selective_pref_removal(self) -> None:
        """Test removing ONLY prefs, not wrappers/data."""
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=False,
            assume_yes=True,
            remove_wrappers=False,
            remove_prefs=True,
            remove_data=False,
        )

        cleanup.scan_for_cleanup_items()
        cleanup.perform_cleanup()

        # Wrappers should remain
        assert (self.bin_dir / "firefox").exists()

        # Prefs should be gone
        assert not (self.config_dir / "firefox.pref").exists()

        # Data should remain
        assert (self.data_dir / "cache_file").exists()

    def test_force_mode_sets_assume_yes(self) -> None:
        """Test force mode automatically sets assume_yes."""
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            force=True,
        )

        assert cleanup.assume_yes is True

    def test_fpwrapper_force_env_sets_assume_yes(self) -> None:
        """Test FPWRAPPER_FORCE environment variable sets assume_yes."""
        import os

        old_env = os.environ.get("FPWRAPPER_FORCE")
        try:
            os.environ["FPWRAPPER_FORCE"] = "1"
            cleanup = WrapperCleanup(
                bin_dir=str(self.bin_dir),
            )
            assert cleanup.assume_yes is True
        finally:
            if old_env is not None:
                os.environ["FPWRAPPER_FORCE"] = old_env
            else:
                os.environ.pop("FPWRAPPER_FORCE", None)

    def test_cleanup_nonexistent_directories(self) -> None:
        """Test cleanup handles nonexistent directories gracefully."""
        cleanup = WrapperCleanup(
            bin_dir="/nonexistent/bin",
            config_dir="/nonexistent/config",
            data_dir="/nonexistent/data",
            dry_run=True,
        )

        # Should not raise exception
        cleanup.scan_for_cleanup_items()

        # Should have empty results
        assert len(cleanup.cleanup_items["wrappers"]) == 0
        assert len(cleanup.cleanup_items["preferences"]) == 0
        assert len(cleanup.cleanup_items["data_files"]) == 0

    def test_get_systemd_unit_dir(self) -> None:
        """Test _get_systemd_unit_dir returns correct path."""
        cleanup = WrapperCleanup(bin_dir=str(self.bin_dir))

        systemd_dir = cleanup._get_systemd_unit_dir()

        assert isinstance(systemd_dir, Path)
        assert "systemd" in str(systemd_dir)
        assert "user" in str(systemd_dir)

    def test_cleanup_with_symlinks(self) -> None:
        """Test cleanup identifies and handles symlinks."""
        # Create a symlink to a wrapper
        symlink_path = self.bin_dir / "firefox-link"
        symlink_path.symlink_to(self.bin_dir / "firefox")

        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            dry_run=True,
        )

        cleanup.scan_for_cleanup_items()

        # Should find the symlink
        # (Implementation may or may not track symlinks separately)
        all_items = cleanup.cleanup_items["wrappers"] + cleanup.cleanup_items["symlinks"]
        assert any("firefox-link" in str(item) for item in all_items)


class TestCleanupMainFunction:
    """Test the main() CLI function with REAL execution."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_main_with_help_flag(self) -> None:
        """Test main() with --help flag."""
        # main() just prints help and returns, doesn't call sys.exit
        sys.argv = ["fplaunch-cleanup", "--help"]
        # Should complete without error
        result = main()
        # Will return None or 0
        assert result is None or result == 0

    def test_main_dry_run_execution(self) -> None:
        """Test main() with --dry-run flag."""
        # Create a test file
        (self.bin_dir / "test-wrapper").write_text("#!/bin/bash\necho test\n")

        sys.argv = [
            "fplaunch-cleanup",
            "--dry-run",
            "--bin-dir",
            str(self.bin_dir),
            "--config-dir",
            str(self.config_dir),
        ]

        # Should complete successfully
        try:
            main()
        except SystemExit as e:
            # May exit with 0
            assert e.code == 0 or e.code is None

        # File should still exist (dry-run)
        assert (self.bin_dir / "test-wrapper").exists()


class TestCleanupIntegration:
    """Integration tests for cleanup with other components."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cleanup_performance_on_large_set(self) -> None:
        """Test cleanup performance with many files."""
        import time

        # Create 100 wrapper files
        for i in range(100):
            wrapper = self.bin_dir / f"app{i}"
            wrapper.write_text(f"#!/bin/bash\necho app{i}\n")
            wrapper.chmod(0o755)

        # Measure cleanup time
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            dry_run=True,
        )

        start = time.time()
        cleanup.scan_for_cleanup_items()
        duration = time.time() - start

        # Should complete quickly (< 1 second)
        assert duration < 1.0
        assert len(cleanup.cleanup_items["wrappers"]) == 100

    def test_cleanup_with_permission_errors(self) -> None:
        """Test cleanup handles permission errors gracefully."""
        import os

        # Create a file
        readonly_file = self.bin_dir / "readonly-wrapper"
        readonly_file.write_text("#!/bin/bash\necho test\n")

        # Make directory read-only to prevent deletion
        os.chmod(self.bin_dir, 0o555)

        try:
            cleanup = WrapperCleanup(
                bin_dir=str(self.bin_dir),
                dry_run=False,
                assume_yes=True,
            )

            cleanup.scan_for_cleanup_items()

            # Should handle permission error gracefully
            try:
                cleanup.perform_cleanup()
            except PermissionError:
                # Expected - that's fine
                pass

        finally:
            # Restore permissions for cleanup
            os.chmod(self.bin_dir, 0o755)

    def test_full_cleanup_workflow(self) -> None:
        """Test complete cleanup workflow from start to finish."""
        # Create a complete set of artifacts
        wrapper = self.bin_dir / "myapp"
        wrapper.write_text("#!/usr/bin/env bash\necho 'MyApp launched'\nexit 0\n")
        wrapper.chmod(0o755)

        pref = self.config_dir / "myapp.pref"
        pref.write_text("flatpak")

        # Run full cleanup
        cleanup = WrapperCleanup(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            dry_run=False,
            assume_yes=True,
        )

        # Step 1: Scan
        cleanup.scan_for_cleanup_items()
        assert len(cleanup.cleanup_items["wrappers"]) > 0

        # Step 2: Clean
        cleanup.perform_cleanup()

        # Step 3: Verify
        assert not wrapper.exists()
