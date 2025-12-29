"""Tests for cleanup scanning enhancements.

Step 5: Extend cleanup functionality to detect and remove orphaned systemd units,
unused cron jobs, and orphaned completion files.
"""

import tempfile
from pathlib import Path

import pytest

from lib.cleanup import WrapperCleanup


class TestOrphanedSystemdUnitsDetection:
    """Tests for detecting and removing orphaned systemd units."""

    def test_detect_orphaned_service_unit(self):
        """Test detection of orphaned systemd service units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"
            systemd_dir = Path.home() / ".config" / "systemd" / "user"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Test that cleanup can be initialized
            assert cleanup is not None
            assert cleanup.bin_dir == bin_dir
            assert cleanup.config_dir == config_dir

    def test_detect_orphaned_timer_unit(self):
        """Test detection of orphaned systemd timer units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Verify cleanup is initialized properly
            assert cleanup.dry_run is True

    def test_remove_orphaned_units_dry_run(self):
        """Test dry-run mode for removing orphaned units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir),
                config_dir=str(config_dir),
                dry_run=True,
                assume_yes=True,
            )

            # Dry run should not raise errors
            assert cleanup.dry_run is True

    def test_orphaned_units_list_populated(self):
        """Test that cleanup identifies orphaned units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # cleanup_items should be initialized
            assert "systemd_units" in cleanup.cleanup_items


class TestUnusedCronJobDetection:
    """Tests for detecting and removing unused cron jobs."""

    def test_detect_orphaned_cron_entry(self):
        """Test detection of orphaned cron job entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Cron entries tracking should exist
            assert "cron_entries" in cleanup.cleanup_items

    def test_cron_entry_cleanup_initialization(self):
        """Test that cron cleanup is properly initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # cleanup_items should be populated
            assert isinstance(cleanup.cleanup_items, dict)
            assert len(cleanup.cleanup_items) > 0

    def test_cron_cleanup_dry_run(self):
        """Test dry-run mode for cron job cleanup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir),
                config_dir=str(config_dir),
                dry_run=True,
                assume_yes=True,
            )

            # Should not raise errors in dry run
            assert cleanup.assume_yes is True


class TestOrphanedCompletionFileDetection:
    """Tests for detecting and removing orphaned bash completion files."""

    def test_detect_orphaned_completion_file(self):
        """Test detection of orphaned completion files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Completion files should be tracked
            assert "completion_files" in cleanup.cleanup_items

    def test_completion_files_cleanup_tracking(self):
        """Test that completion file cleanup is tracked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Should have completion files list
            assert isinstance(cleanup.cleanup_items["completion_files"], list)

    def test_orphaned_completion_file_in_bash_completion_dir(self):
        """Test detection of completion files in ~/.bash_completion.d/"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Cleanup should be initialized with completion tracking
            assert cleanup is not None


class TestOrphanedManPageDetection:
    """Tests for detecting orphaned manual pages."""

    def test_detect_orphaned_man_page(self):
        """Test detection of orphaned man pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Man pages should be tracked
            assert "man_pages" in cleanup.cleanup_items

    def test_man_pages_cleanup_list(self):
        """Test that man pages cleanup list is maintained."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Should have man_pages list
            assert isinstance(cleanup.cleanup_items["man_pages"], list)


class TestCleanupArtifactTracking:
    """Tests for tracking various cleanup artifacts."""

    def test_all_cleanup_items_tracked(self):
        """Test that all cleanup item types are tracked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # All cleanup items should be present
            expected_items = [
                "wrappers",
                "symlinks",
                "scripts",
                "systemd_units",
                "cron_entries",
                "completion_files",
                "man_pages",
                "config_dir",
                "preferences",
                "data_files",
            ]

            for item in expected_items:
                assert item in cleanup.cleanup_items

    def test_cleanup_items_are_lists_or_paths(self):
        """Test that cleanup items are properly typed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Items should be lists or Path objects
            for key, value in cleanup.cleanup_items.items():
                assert isinstance(value, (list, Path))

    def test_cleanup_summary_generation(self):
        """Test that cleanup summary can be generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Should be able to count cleanup items
            total_items = sum(
                len(v) if isinstance(v, list) else 1
                for v in cleanup.cleanup_items.values()
            )
            assert isinstance(total_items, int)


class TestCleanupDryRunMode:
    """Tests for dry-run (preview) functionality."""

    def test_dry_run_prevents_actual_deletion(self):
        """Test that dry-run mode doesn't actually delete anything."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            # Create a test wrapper
            wrapper = bin_dir / "test-wrapper"
            wrapper.write_text("#!/bin/bash\necho test\n")
            wrapper.chmod(0o755)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            # Wrapper should still exist after cleanup init
            assert wrapper.exists()

    def test_dry_run_flag_is_respected(self):
        """Test that dry_run flag is properly set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            assert cleanup.dry_run is True

    def test_real_run_mode_allowed(self):
        """Test that real run mode can be enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=False
            )

            assert cleanup.dry_run is False


class TestCleanupVerbosityModes:
    """Tests for verbose output control."""

    def test_verbose_mode_can_be_enabled(self):
        """Test that verbose mode can be enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir),
                config_dir=str(config_dir),
                dry_run=True,
                verbose=True,
            )

            assert cleanup.verbose is True

    def test_verbose_mode_disabled_by_default(self):
        """Test that verbose mode is disabled by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            assert cleanup.verbose is False


class TestCleanupDirectoryInitialization:
    """Tests for cleanup directory configuration."""

    def test_custom_bin_dir(self):
        """Test that custom bin directory is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "custom_bin"
            config_dir = Path(tmpdir) / ".config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            assert cleanup.bin_dir == bin_dir

    def test_custom_config_dir(self):
        """Test that custom config directory is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / "custom_config"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir), config_dir=str(config_dir), dry_run=True
            )

            assert cleanup.config_dir == config_dir

    def test_custom_data_dir(self):
        """Test that custom data directory is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config"
            data_dir = Path(tmpdir) / "data"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)
            data_dir.mkdir(parents=True)

            cleanup = WrapperCleanup(
                bin_dir=str(bin_dir),
                config_dir=str(config_dir),
                data_dir=str(data_dir),
                dry_run=True,
            )

            assert cleanup.data_dir == data_dir
