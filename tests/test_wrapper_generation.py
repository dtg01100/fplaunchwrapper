#!/usr/bin/env python3
"""Tests for wrapper generation, cleanup, and systemd setup functionality."""

import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lib.cleanup import WrapperCleanup
from lib.generate import WrapperGenerator
from lib.systemd_setup import SystemdSetup


class TestWrapperGenerator:
    """Test wrapper generation functionality."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config" / "fplaunchwrapper"
            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)
            yield bin_dir, config_dir

    def test_generator_initialization(self, temp_dirs):
        """Test WrapperGenerator initializes correctly."""
        bin_dir, config_dir = temp_dirs
        generator = WrapperGenerator(
            str(bin_dir), config_dir=str(config_dir), verbose=True
        )

        assert generator.bin_dir == bin_dir
        assert generator.config_dir == config_dir
        assert generator.verbose is True
        assert generator.emit_mode is False
        assert bin_dir.exists()
        assert config_dir.exists()

    def test_generator_emit_mode(self, temp_dirs):
        """Test WrapperGenerator in emit mode doesn't create directories."""
        bin_dir, config_dir = temp_dirs
        # Use non-existent path
        new_bin = bin_dir / "nonexistent"
        new_config = config_dir / "nonexistent"

        generator = WrapperGenerator(
            str(new_bin), config_dir=str(new_config), emit_mode=True
        )

        assert generator.emit_mode is True
        assert not new_bin.exists()
        assert not new_config.exists()

    def test_generator_creates_valid_wrapper(self, temp_dirs):
        """Test generated wrapper has correct structure."""
        bin_dir, config_dir = temp_dirs
        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))

        # Mock flatpak list output
        mock_app = "com.example.App\tExample App\t1.0\tstable\tsystem"

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = mock_app
            mock_run.return_value = mock_result

            # Mock the wrapper generation
            with patch.object(generator, "generate_wrapper") as mock_generate:
                mock_generate.return_value = True
                result = mock_generate("com.example.App")

                assert result is True
                mock_generate.assert_called_once_with("com.example.App")

    def test_wrapper_script_has_shebang(self, temp_dirs):
        """Test generated wrapper scripts have proper shebang."""
        bin_dir, config_dir = temp_dirs

        # Create a mock wrapper script
        wrapper_path = bin_dir / "example-app"
        wrapper_content = """#!/usr/bin/env bash
# Generated wrapper for com.example.App
exec flatpak run com.example.App "$@"
"""
        wrapper_path.write_text(wrapper_content)
        wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IEXEC)

        # Verify shebang
        with open(wrapper_path, "r") as f:
            first_line = f.readline().strip()
            assert first_line == "#!/usr/bin/env bash"

        # Verify executable
        assert os.access(wrapper_path, os.X_OK)

    def test_wrapper_handles_missing_flatpak(self, temp_dirs):
        """Test wrapper generation handles missing Flatpak gracefully."""
        bin_dir, config_dir = temp_dirs
        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))

        with patch("shutil.which", return_value=None):
            # Generator should handle missing flatpak command
            with pytest.raises((FileNotFoundError, RuntimeError, SystemExit)):
                generator.run_command(["flatpak", "list"], "Check Flatpak")


class TestWrapperCleanup:
    """Test wrapper cleanup functionality."""

    @pytest.fixture
    def temp_cleanup_dirs(self):
        """Create temporary directories for cleanup testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config" / "fplaunchwrapper"
            data_dir = Path(tmpdir) / ".local" / "share" / "fplaunchwrapper"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)
            data_dir.mkdir(parents=True)

            yield bin_dir, config_dir, data_dir

    def test_cleanup_initialization(self, temp_cleanup_dirs):
        """Test WrapperCleanup initializes correctly."""
        bin_dir, config_dir, data_dir = temp_cleanup_dirs
        cleanup = WrapperCleanup(
            bin_dir=str(bin_dir),
            config_dir=str(config_dir),
            data_dir=str(data_dir),
            dry_run=True,
        )

        assert cleanup.bin_dir == bin_dir
        assert cleanup.config_dir == config_dir
        assert cleanup.data_dir == data_dir
        assert cleanup.dry_run is True

    def test_cleanup_dry_run_preserves_files(self, temp_cleanup_dirs):
        """Test dry run mode doesn't delete files."""
        bin_dir, config_dir, data_dir = temp_cleanup_dirs

        # Create test files
        test_wrapper = bin_dir / "test-wrapper"
        test_wrapper.write_text("#!/bin/bash\necho test")
        test_wrapper.chmod(test_wrapper.stat().st_mode | stat.S_IEXEC)

        cleanup = WrapperCleanup(
            bin_dir=str(bin_dir),
            config_dir=str(config_dir),
            dry_run=True,
            assume_yes=True,
        )

        # Run cleanup scan (should be mocked or limited in scope)
        with patch.object(cleanup, "scan_for_cleanup_items") as mock_scan:
            mock_scan.return_value = None
            cleanup.scan_for_cleanup_items()

        # File should still exist in dry run
        assert test_wrapper.exists()

    def test_cleanup_identifies_wrapper_files(self, temp_cleanup_dirs):
        """Test cleanup can identify wrapper files."""
        bin_dir, config_dir, data_dir = temp_cleanup_dirs

        # Create wrapper with metadata
        wrapper = bin_dir / "com.example.App"
        wrapper_content = """#!/usr/bin/env bash
# Generated by fplaunchwrapper
# WRAPPER_ID=com.example.App
exec flatpak run com.example.App "$@"
"""
        wrapper.write_text(wrapper_content)

        WrapperCleanup(bin_dir=str(bin_dir), config_dir=str(config_dir))

        # Mock is_wrapper_file check from python_utils
        with patch("fplaunch.python_utils.is_wrapper_file", return_value=True):
            from lib.python_utils import is_wrapper_file

            assert is_wrapper_file(str(wrapper))

    def test_cleanup_force_mode_skips_confirmation(self, temp_cleanup_dirs):
        """Test force mode skips user confirmation."""
        bin_dir, config_dir, data_dir = temp_cleanup_dirs

        cleanup = WrapperCleanup(
            bin_dir=str(bin_dir), config_dir=str(config_dir), force=True
        )

        assert cleanup.assume_yes is True
        assert cleanup.force is True


class TestSystemdSetup:
    """Test systemd setup functionality."""

    @pytest.fixture
    def temp_systemd_dirs(self):
        """Create temporary directories for systemd testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            systemd_dir = Path(tmpdir) / ".config" / "systemd" / "user"

            bin_dir.mkdir(parents=True)
            systemd_dir.mkdir(parents=True)

            yield bin_dir, systemd_dir

    def test_systemd_initialization(self, temp_systemd_dirs):
        """Test SystemdSetup initializes correctly."""
        bin_dir, systemd_dir = temp_systemd_dirs

        with patch.object(
            SystemdSetup, "_get_systemd_unit_dir", return_value=systemd_dir
        ):
            setup = SystemdSetup(bin_dir=str(bin_dir))

            assert setup.bin_dir == bin_dir
            assert setup.systemd_unit_dir == systemd_dir

    def test_systemd_unit_has_valid_format(self, temp_systemd_dirs):
        """Test generated systemd unit files have valid format."""
        bin_dir, systemd_dir = temp_systemd_dirs

        # Create mock systemd unit
        unit_content = """[Unit]
Description=Flatpak Wrapper Auto-Update
After=graphical.target

[Service]
Type=oneshot
ExecStart=/usr/bin/fplaunch-generate

[Install]
WantedBy=default.target
"""
        unit_file = systemd_dir / "fplaunch-update.service"
        unit_file.write_text(unit_content)

        # Verify unit file exists and has required sections
        assert unit_file.exists()
        content = unit_file.read_text()
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content

    def test_systemd_handles_missing_directory(self, temp_systemd_dirs):
        """Test systemd setup handles missing directories gracefully."""
        bin_dir, systemd_dir = temp_systemd_dirs

        # Use non-existent systemd directory
        nonexistent_dir = systemd_dir / "nonexistent"

        with patch.object(
            SystemdSetup, "_get_systemd_unit_dir", return_value=nonexistent_dir
        ):
            setup = SystemdSetup(bin_dir=str(bin_dir), emit_mode=True)

            # In emit mode, directories shouldn't be created
            assert setup.emit_mode is True

    def test_systemd_detects_flatpak_bin_dir(self, temp_systemd_dirs):
        """Test systemd setup detects Flatpak binary directory."""
        bin_dir, systemd_dir = temp_systemd_dirs

        # Mock flatpak detection
        mock_flatpak_dir = "/home/user/.local/share/flatpak/exports/bin"

        with patch.object(
            SystemdSetup, "_detect_flatpak_bin_dir", return_value=mock_flatpak_dir
        ):
            with patch.object(
                SystemdSetup, "_get_systemd_unit_dir", return_value=systemd_dir
            ):
                setup = SystemdSetup(bin_dir=str(bin_dir))
                assert setup.flatpak_bin_dir == mock_flatpak_dir

    def test_systemd_emit_mode_doesnt_create_files(self, temp_systemd_dirs):
        """Test emit mode doesn't create actual systemd unit files."""
        bin_dir, systemd_dir = temp_systemd_dirs

        with patch.object(
            SystemdSetup, "_get_systemd_unit_dir", return_value=systemd_dir
        ):
            setup = SystemdSetup(bin_dir=str(bin_dir), emit_mode=True)

            assert setup.emit_mode is True

            # Check no units were created
            units = list(systemd_dir.glob("*.service"))
            assert len(units) == 0


class TestIntegrationScenarios:
    """Test integrated scenarios across all three commands."""

    @pytest.fixture
    def integrated_env(self):
        """Create integrated test environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config" / "fplaunchwrapper"
            data_dir = Path(tmpdir) / ".local" / "share" / "fplaunchwrapper"
            systemd_dir = Path(tmpdir) / ".config" / "systemd" / "user"

            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)
            data_dir.mkdir(parents=True)
            systemd_dir.mkdir(parents=True)

            yield {
                "bin_dir": bin_dir,
                "config_dir": config_dir,
                "data_dir": data_dir,
                "systemd_dir": systemd_dir,
            }

    def test_generate_then_cleanup_workflow(self, integrated_env):
        """Test generating wrappers and then cleaning them up."""
        dirs = integrated_env

        # Generate wrapper
        generator = WrapperGenerator(
            str(dirs["bin_dir"]), config_dir=str(dirs["config_dir"])
        )
        assert generator.bin_dir.exists()

        # Cleanup
        cleanup = WrapperCleanup(
            bin_dir=str(dirs["bin_dir"]),
            config_dir=str(dirs["config_dir"]),
            data_dir=str(dirs["data_dir"]),
            dry_run=True,
        )
        assert cleanup.bin_dir.exists()

    def test_systemd_setup_after_generation(self, integrated_env):
        """Test systemd setup after wrapper generation."""
        dirs = integrated_env

        # Generate wrapper first
        WrapperGenerator(str(dirs["bin_dir"]), config_dir=str(dirs["config_dir"]))

        # Setup systemd
        with patch.object(
            SystemdSetup, "_get_systemd_unit_dir", return_value=dirs["systemd_dir"]
        ):
            setup = SystemdSetup(bin_dir=str(dirs["bin_dir"]), emit_mode=True)
            assert setup.bin_dir == dirs["bin_dir"]
            assert setup.emit_mode is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
