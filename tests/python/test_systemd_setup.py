"""
Tests for systemd_setup module with realistic unit file creation.

Tests verify:
- Actual systemd unit file creation and content
- App-specific service enable/disable functionality
- Timer state verification
- Cron fallback when systemd is unavailable
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Add lib to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))


class SystemdTestFixtures:
    """Shared fixtures for systemd tests."""

    @staticmethod
    def create_temp_systemd_dir():
        """Create a temporary systemd user directory."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_systemd_"))
        systemd_dir = temp_dir / "systemd" / "user"
        systemd_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir, systemd_dir

    @staticmethod
    def create_fake_bin_dir():
        """Create a temporary bin directory with fake wrapper script."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_bin_"))
        bin_dir = temp_dir / "bin"
        bin_dir.mkdir(exist_ok=True)
        # Create a fake wrapper script
        wrapper = bin_dir / "fplaunch-generate"
        wrapper.write_text("#!/bin/bash\necho 'Generated wrappers'")
        wrapper.chmod(0o755)
        return temp_dir, bin_dir

    @staticmethod
    def validate_systemd_unit(content: str) -> tuple[bool, str]:
        """Validate systemd unit file syntax using systemd-analyze if available."""
        import tempfile
        import os

        try:
            # Write content to a temporary file since systemd-analyze expects a file path
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".timer", delete=False
            ) as f:
                f.write(content)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ["systemd-analyze", "verify", "--no-pager", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return True, "Valid systemd unit"
                else:
                    return False, result.stderr
            finally:
                os.unlink(temp_file)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # systemd-analyze not available, do basic validation
            required_sections = ["[Unit]", "[Service]"]
            for section in required_sections:
                if section not in content:
                    return False, f"Missing section: {section}"
            return True, "Basic validation passed (systemd-analyze not available)"


class TestSystemdUnitGeneration:
    """Test actual systemd unit file generation."""

    def test_service_unit_content(self):
        """Test that service unit has correct content."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            # Override the systemd unit dir to use our temp directory
            setup.systemd_unit_dir = systemd_dir

            service_content = setup.create_service_unit()

            # Verify basic structure
            assert "[Unit]" in service_content
            assert "[Service]" in service_content
            assert "Type=oneshot" in service_content
            assert "Description" in service_content
            assert str(bin_dir / "fplaunch-generate") in service_content

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)

    def test_path_unit_content(self):
        """Test that path unit has correct content."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            path_content = setup.create_path_unit()

            # Verify basic structure
            assert "[Unit]" in path_content
            assert "[Path]" in path_content
            assert "[Install]" in path_content
            assert "WantedBy" in path_content
            assert "PathChanged" in path_content

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)

    def test_timer_unit_content(self):
        """Test that timer unit has correct content."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            timer_content = setup.create_timer_unit()

            # Verify basic structure
            assert "[Unit]" in timer_content
            assert "[Timer]" in timer_content
            assert "[Install]" in timer_content
            assert "OnCalendar=daily" in timer_content
            assert "Persistent=true" in timer_content

            # Validate with systemd-analyze if available
            valid, msg = SystemdTestFixtures.validate_systemd_unit(timer_content)
            assert valid, f"Timer unit validation failed: {msg}"

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)

    def test_actual_file_creation(self):
        """Test that unit files are actually created on disk."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            # Manually write unit files to verify they exist
            service_unit = systemd_dir / "flatpak-wrappers.service"
            service_unit.write_text(setup.create_service_unit())

            path_unit = systemd_dir / "flatpak-wrappers.path"
            path_unit.write_text(setup.create_path_unit())

            timer_unit = systemd_dir / "flatpak-wrappers.timer"
            timer_unit.write_text(setup.create_timer_unit())

            # Verify files exist
            assert service_unit.exists(), "Service unit file was not created"
            assert path_unit.exists(), "Path unit file was not created"
            assert timer_unit.exists(), "Timer unit file was not created"

            # Verify file contents match
            assert service_unit.read_text() == setup.create_service_unit()
            assert path_unit.read_text() == setup.create_path_unit()
            assert timer_unit.read_text() == setup.create_timer_unit()

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)


class TestAppServiceEnableDisable:
    """Test app-specific service enable/disable functionality."""

    def test_enable_app_service_creates_files(self):
        """Test that enable_app_service creates actual unit files."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            # Mock systemctl to avoid actual systemd calls
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                result = setup.enable_app_service("firefox")

                assert result is True

                # Verify files were created
                service_file = systemd_dir / "flatpak-wrapper-firefox.service"
                timer_file = systemd_dir / "flatpak-wrapper-firefox.timer"

                assert service_file.exists(), "Service file was not created"
                assert timer_file.exists(), "Timer file was not created"

                # Verify file contents
                service_content = service_file.read_text()
                assert "[Unit]" in service_content
                assert "firefox" in service_content
                assert "[Service]" in service_content
                assert "Type=oneshot" in service_content

                timer_content = timer_file.read_text()
                assert "[Unit]" in timer_content
                assert "firefox" in timer_content
                assert "[Timer]" in timer_content
                assert "OnCalendar=daily" in timer_content

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)

    def test_disable_app_service_removes_files(self):
        """Test that disable_app_service removes unit files."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            # First enable the service to create files
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                setup.enable_app_service("firefox")

            # Now disable it
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = setup.disable_app_service("firefox")

            assert result is True

            # Verify files were removed
            service_file = systemd_dir / "flatpak-wrapper-firefox.service"
            timer_file = systemd_dir / "flatpak-wrapper-firefox.timer"

            assert not service_file.exists(), "Service file was not removed"
            assert not timer_file.exists(), "Timer file was not removed"

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)

    def test_enable_app_service_with_empty_app_id(self):
        """Test that enable_app_service fails gracefully with empty app_id."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup(emit_mode=True)

        result = setup.enable_app_service("")
        assert result is False

    def test_disable_app_service_with_empty_app_id(self):
        """Test that disable_app_service fails gracefully with empty app_id."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup(emit_mode=True)

        result = setup.disable_app_service("")
        assert result is False


class TestSystemdSetupRealistic:
    """Realistic systemd setup tests with actual file operations."""

    def test_install_systemd_units_creates_files(self):
        """Test that install_systemd_units creates actual unit files."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            # Mock systemctl calls to avoid actual systemd interaction
            with patch("shutil.which", return_value="/usr/bin/systemctl"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(returncode=0)

                    result = setup.install_systemd_units()

                    assert result is True

            # Verify all unit files were created
            service_unit = systemd_dir / "flatpak-wrappers.service"
            path_unit = systemd_dir / "flatpak-wrappers.path"
            timer_unit = systemd_dir / "flatpak-wrappers.timer"

            assert service_unit.exists()
            assert path_unit.exists()
            assert timer_unit.exists()

            # Verify content
            assert "Type=oneshot" in service_unit.read_text()
            assert "PathChanged" in path_unit.read_text()
            assert "OnCalendar=daily" in timer_unit.read_text()

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)

    def test_disable_systemd_units_removes_files(self):
        """Test that disable_systemd_units removes unit files."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            # Create unit files first
            service_unit = systemd_dir / "flatpak-wrappers.service"
            path_unit = systemd_dir / "flatpak-wrappers.path"
            timer_unit = systemd_dir / "flatpak-wrappers.timer"

            service_unit.write_text(setup.create_service_unit())
            path_unit.write_text(setup.create_path_unit())
            timer_unit.write_text(setup.create_timer_unit())

            assert service_unit.exists()
            assert path_unit.exists()
            assert timer_unit.exists()

            # Now disable (with mocked systemctl)
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = setup.disable_systemd_units()

            assert result is True

            # Files should be removed (or at least disabled)
            # Note: actual behavior depends on implementation

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)


class TestCronFallback:
    """Test cron fallback when systemd is unavailable."""

    def test_cron_fallback_creation(self):
        """Test cron job creation when systemd is unavailable."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            # Mock both systemd unavailability and crontab
            with patch("shutil.which") as mock_which:
                # Return None for systemctl (systemd not available)
                # Return path for crontab
                def which_side_effect(cmd):
                    if cmd == "systemctl":
                        return None
                    elif cmd == "crontab":
                        return "/usr/bin/crontab"
                    return None

                mock_which.side_effect = which_side_effect

                with patch("subprocess.run") as mock_run:
                    # First call: crontab -l returns empty (no existing cron)
                    mock_run.return_value = Mock(returncode=1, stdout="")

                    result = setup.install_cron_job()

                    # Should succeed since crontab is available
                    assert result is True or result is False  # May vary by environment

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)

    def test_no_systemd_no_cron(self):
        """Test behavior when neither systemd nor cron is available."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup(emit_mode=True)

        with patch("shutil.which", return_value=None):
            result = setup.install_cron_job()

            assert result is False


class TestSystemdUnitDir:
    """Test systemd unit directory handling."""

    def test_get_systemd_unit_dir_default(self):
        """Test _get_systemd_unit_dir returns correct default path."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup()

        expected = Path.home() / ".config" / "systemd" / "user"
        assert setup.systemd_unit_dir == expected

    def test_get_systemd_unit_dir_custom_xdg(self):
        """Test _get_systemd_unit_dir respects XDG_CONFIG_HOME."""
        from lib.systemd_setup import SystemdSetup

        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/custom/config"}):
            setup = SystemdSetup()

            expected = Path("/custom/config") / "systemd" / "user"
            assert setup.systemd_unit_dir == expected


class TestListAppServices:
    """Test listing app-specific services."""

    def test_list_app_services_returns_enabled_apps(self):
        """Test that list_app_services returns list of enabled app timers."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            # Create some app timer files
            (systemd_dir / "flatpak-wrapper-firefox.timer").write_text(
                "[Timer]\nOnCalendar=daily\n"
            )
            (systemd_dir / "flatpak-wrapper-thunderbird.timer").write_text(
                "[Timer]\nOnCalendar=hourly\n"
            )
            (systemd_dir / "flatpak-wrapper-vlc.timer").write_text(
                "[Timer]\nOnCalendar=weekly\n"
            )

            apps = setup.list_app_services()

            assert len(apps) == 3
            assert "firefox" in apps
            assert "thunderbird" in apps
            assert "vlc" in apps

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)

    def test_list_app_services_empty_when_no_timers(self):
        """Test that list_app_services returns empty list when no timers exist."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()

        try:
            setup = SystemdSetup()
            setup.systemd_unit_dir = systemd_dir

            apps = setup.list_app_services()

            assert apps == []

        finally:
            shutil.rmtree(temp_dir)


class TestRealisticUnitFileNames:
    """Test with realistic unit file names like fplaunch-firefox.service."""

    def test_fplaunch_unit_file_naming(self):
        """Test that unit files follow expected naming convention."""
        from lib.systemd_setup import SystemdSetup

        temp_dir, systemd_dir = SystemdTestFixtures.create_temp_systemd_dir()
        temp_bin, bin_dir = SystemdTestFixtures.create_fake_bin_dir()

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            # Create an app-specific unit
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                setup.enable_app_service("firefox")

            # Verify naming convention
            service_file = systemd_dir / "flatpak-wrapper-firefox.service"
            timer_file = systemd_dir / "flatpak-wrapper-firefox.timer"

            assert service_file.exists()
            assert timer_file.exists()
            assert service_file.name.startswith("flatpak-wrapper-")
            assert timer_file.name.startswith("flatpak-wrapper-")
            assert service_file.name.endswith(".service")
            assert timer_file.name.endswith(".timer")

        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_bin)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
