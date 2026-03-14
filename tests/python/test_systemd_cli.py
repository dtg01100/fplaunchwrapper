"""
Tests for systemd CLI command integration.

Tests verify:
- systemd enable/disable functionality
- status checking
- error handling for missing prerequisites
- emit mode for dry-run testing
"""

from unittest.mock import patch
import pytest

from click.testing import CliRunner
from lib.cli import cli


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
        assert "service" in status, "Should have 'service' key"
        assert "timer" in status, "Should have 'timer' key"
        assert isinstance(status["service"], dict), "service should be dict"
        assert isinstance(status["timer"], dict), "timer should be dict"
        assert "enabled" in status["service"], "service should have 'enabled' key"
        assert "active" in status["service"], "service should have 'active' key"
        assert "exists" in status["service"], "service should have 'exists' key"
        assert "enabled" in status["timer"], "timer should have 'enabled' key"
        assert "active" in status["timer"], "timer should have 'active' key"
        assert "exists" in status["timer"], "timer should have 'exists' key"

    def test_check_systemd_status_with_no_systemctl(self):
        """Test check_systemd_status when systemctl is unavailable."""
        from lib.systemd_setup import SystemdSetup

        with patch("shutil.which", return_value=None):
            setup = SystemdSetup()
            status = setup.check_systemd_status()

            assert status["service"]["enabled"] is False
            assert status["service"]["active"] is False
            assert status["service"]["exists"] is False
            assert status["timer"]["enabled"] is False
            assert status["timer"]["active"] is False
            assert status["timer"]["exists"] is False

    def test_check_systemd_status_with_enabled_units(self):
        """Test check_systemd_status with enabled units."""
        from lib.systemd_setup import SystemdSetup

        with patch("shutil.which", return_value="/bin/systemctl"):
            with patch("subprocess.run") as mock_run:

                def mock_response(args, **kwargs):
                    class MockResult:
                        def __init__(self, returncode, stdout="", stderr=""):
                            self.returncode = returncode
                            self.stdout = stdout
                            self.stderr = stderr

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
                    else:
                        return MockResult(0, stdout="")

                mock_run.side_effect = mock_response

                setup = SystemdSetup()

                assert setup.check_systemd_status()["service"]["enabled"] is True
                assert setup.check_systemd_status()["service"]["active"] is True
                assert setup.check_systemd_status()["timer"]["enabled"] is True
                assert setup.check_systemd_status()["timer"]["active"] is True

    def test_check_systemd_status_with_disabled_units(self):
        """Test check_systemd_status with disabled units."""
        from lib.systemd_setup import SystemdSetup

        with patch("shutil.which", return_value="/bin/systemctl"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 1
                mock_run.return_value.stdout = b""
                mock_run.return_value.stderr = b""

                setup = SystemdSetup()
                status = setup.check_systemd_status()

                assert status["service"]["enabled"] is False
                assert status["service"]["active"] is False
                assert status["timer"]["enabled"] is False
                assert status["timer"]["active"] is False


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

            assert status["service"]["enabled"] is False
            assert status["service"]["active"] is False
            assert status["timer"]["enabled"] is False
            assert status["timer"]["active"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
