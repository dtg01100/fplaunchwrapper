"""
Tests for systemd CLI command integration.

Tests verify:
- systemd enable/disable functionality
- status checking
- error handling for missing prerequisites
- emit mode for dry-run testing
"""

import os
import sys
from unittest.mock import patch
import pytest

# Add lib to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

try:
    from click.testing import CliRunner
    from cli import cli

    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False
    pytest.skip("Click not available", allow_module_level=True)


class TestSystemdCliCommand:
    """Test the systemd CLI command."""

    def test_systemd_command_exists(self):
        """Test that systemd command is available."""
        runner = CliRunner()
        result = runner.invoke(cli, ["systemd", "--help"])

        assert result.exit_code == 0, f"Error: {result.output}"
        assert (
            "Manage optional systemd timer" in result.output
            or "systemd" in result.output.lower()
        )

    def test_systemd_enable_help(self):
        """Test systemd enable action help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["systemd", "enable", "--help"])

        # Should show help without error
        assert result.exit_code == 0

    def test_systemd_disable_help(self):
        """Test systemd disable action help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["systemd", "disable", "--help"])

        # Should show help without error
        assert result.exit_code == 0

    def test_systemd_status_help(self):
        """Test systemd status action help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["systemd", "status", "--help"])

        # Should show help without error
        assert result.exit_code == 0

    def test_systemd_test_help(self):
        """Test systemd test action help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["systemd", "test", "--help"])

        # Should show help without error
        assert result.exit_code == 0

    def test_systemd_test_emit_mode(self):
        """Test systemd test with emit mode."""
        runner = CliRunner()
        result = runner.invoke(cli, ["systemd", "test", "--emit"])

        # In emit mode with no prerequisites, should still work or fail gracefully
        assert result.exit_code in [0, 1], f"Unexpected exit code: {result.exit_code}"


class TestSystemdSetupMethods:
    """Test SystemdSetup class methods."""

    def test_disable_systemd_units_success(self):
        """Test disable_systemd_units returns True on success."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup(emit_mode=True)
        result = setup.disable_systemd_units()

        assert result is True, "disable_systemd_units should return True in emit mode"

    def test_check_systemd_status_returns_dict(self):
        """Test check_systemd_status returns proper dict."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup()
        status = setup.check_systemd_status()

        assert isinstance(status, dict), "Should return a dictionary"
        assert "enabled" in status, "Should have 'enabled' key"
        assert "active" in status, "Should have 'active' key"
        assert "units" in status, "Should have 'units' key"
        assert isinstance(status["enabled"], bool), "enabled should be bool"
        assert isinstance(status["active"], bool), "active should be bool"
        assert isinstance(status["units"], dict), "units should be dict"

    def test_check_systemd_status_with_no_systemctl(self):
        """Test check_systemd_status when systemctl is unavailable."""
        from lib.systemd_setup import SystemdSetup

        with patch("shutil.which", return_value=None):
            setup = SystemdSetup()
            status = setup.check_systemd_status()

            assert status["enabled"] is False
            assert status["active"] is False
            assert status["units"] == {}

    def test_check_systemd_status_with_enabled_units(self):
        """Test check_systemd_status with enabled units."""
        from lib.systemd_setup import SystemdSetup

        with patch("shutil.which", return_value="/bin/systemctl"):
            with patch("subprocess.run") as mock_run:
                # Create a mock that returns appropriate responses based on arguments
                def mock_response(args, **kwargs):
                    class MockResult:
                        def __init__(self, returncode, stdout="", stderr=""):
                            self.returncode = returncode
                            self.stdout = stdout
                            self.stderr = stderr

                    # Check which command is being run
                    if (
                        args[0] == "systemctl"
                        and args[1] == "--user"
                        and args[2] == "is-enabled"
                    ):
                        return MockResult(0, stdout="enabled")
                    elif (
                        args[0] == "systemctl"
                        and args[1] == "--user"
                        and args[2] == "is-active"
                    ):
                        return MockResult(0, stdout="active")
                    elif (
                        args[0] == "systemctl"
                        and args[1] == "--user"
                        and args[2] == "show"
                    ):
                        return MockResult(0, stdout="ActiveState=active")
                    else:
                        return MockResult(0, stdout="")

                mock_run.side_effect = mock_response

                setup = SystemdSetup()
                status = setup.check_systemd_status()

                assert status["enabled"] is True
                assert status["active"] is True
                assert len(status["units"]) == 3  # service, path, timer
                for unit in [
                    "flatpak-wrappers.service",
                    "flatpak-wrappers.path",
                    "flatpak-wrappers.timer",
                ]:
                    assert status["units"].get(unit, {}).get("enabled") is True

    def test_check_systemd_status_with_disabled_units(self):
        """Test check_systemd_status with disabled units."""
        from lib.systemd_setup import SystemdSetup

        with patch("shutil.which", return_value="/bin/systemctl"):
            with patch("subprocess.run") as mock_run:
                # Set up mock to return failure (1) for all calls
                mock_run.return_value.returncode = 1
                mock_run.return_value.stdout = b""
                mock_run.return_value.stderr = b""

                setup = SystemdSetup()
                status = setup.check_systemd_status()

                assert status["enabled"] is False
                assert status["active"] is False
                all_disabled = all(
                    status["units"].get(unit, {}).get("enabled") is False
                    for unit in [
                        "flatpak-wrappers.service",
                        "flatpak-wrappers.path",
                        "flatpak-wrappers.timer",
                    ]
                )
                assert all_disabled is True


class TestSystemdSetupIntegration:
    """Integration tests for SystemdSetup with actual environment."""

    def test_disable_systemd_gracefully_handles_missing_dir(self):
        """Test disable_systemd_units handles missing unit directory gracefully."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup(emit_mode=True)

        # In emit mode, should succeed
        result = setup.disable_systemd_units()
        assert result is True

    def test_systemd_setup_exception_handling(self):
        """Test that SystemdSetup handles exceptions gracefully."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup()

        with patch("subprocess.run", side_effect=Exception("Test exception")):
            status = setup.check_systemd_status()

            # Should return safe defaults on exception
            assert status["enabled"] is False
            assert status["active"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
