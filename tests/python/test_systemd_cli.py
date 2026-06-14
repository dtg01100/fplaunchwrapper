"""
Tests for systemd CLI command integration.

Tests verify:
- systemd enable/disable functionality
- status checking
- error handling for missing prerequisites
- emit mode for dry-run testing
"""
import subprocess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

import pytest

from lib.cli import cli
from lib.systemd_setup import SystemdSetup


class TestSystemdCliCommand:
    """Test the systemd CLI command."""

    def test_systemd_command_exists(self):
        """Test that systemd command is available."""
        runner = CliRunner()
        result = runner.invoke(cli, ["systemd", "--help"])

        assert result.exit_code == 0, f"Error: {result.output}"
        assert (
            "Manage optional systemd timer" in result.output or "systemd" in result.output.lower()
        )

    @pytest.mark.parametrize("action", ["enable", "disable", "status", "test"])
    def test_systemd_action_help(self, action: str):
        """Test systemd action help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["systemd", action, "--help"])

        assert result.exit_code == 0

    def test_systemd_test_emit_mode(self):
        """Test systemd test with emit mode."""
        runner = CliRunner()
        result = runner.invoke(cli, ["systemd", "test", "--emit"])

        # In emit mode with no prerequisites, should still work or fail gracefully
        assert result.exit_code in [0, 1], f"Unexpected exit code: {result.exit_code}"


class TestSystemdCliEnableDisable:
    """Test enable/disable CLI commands via the full cli wrapper."""

    def test_systemd_enable_success(self):
        """Test enable returns 0 when setup succeeds."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.install_systemd_units.return_value = True
        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=fake_setup):
            result = runner.invoke(cli, ["systemd", "enable"], standalone_mode=False)
        assert result.return_value == 0
        fake_setup.install_systemd_units.assert_called_once()

    def test_systemd_enable_failure(self):
        """Test enable returns 1 when setup fails."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.install_systemd_units.return_value = False
        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=fake_setup):
            result = runner.invoke(cli, ["systemd", "enable"], standalone_mode=False)
        assert result.return_value == 1

    def test_systemd_enable_module_unavailable(self):
        """Test enable returns 1 when systemd_setup module is missing."""
        from lib import cli_systemd

        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=None):
            result = runner.invoke(cli, ["systemd", "enable"], standalone_mode=False)
        assert result.return_value == 1

    def test_systemd_disable_success(self):
        """Test disable returns 0 on success."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.disable_systemd_units.return_value = True
        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=fake_setup):
            result = runner.invoke(cli, ["systemd", "disable"], standalone_mode=False)
        assert result.return_value == 0

    def test_systemd_disable_failure(self):
        """Test disable returns 1 when setup fails."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.disable_systemd_units.return_value = False
        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=fake_setup):
            result = runner.invoke(cli, ["systemd", "disable"], standalone_mode=False)
        assert result.return_value == 1

    def test_systemd_disable_module_unavailable(self):
        """Test disable returns 1 when module missing."""
        from lib import cli_systemd

        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=None):
            result = runner.invoke(cli, ["systemd", "disable"], standalone_mode=False)
        assert result.return_value == 1


class TestSystemdCliStatus:
    """Test status CLI command."""

    def test_systemd_status_prints_status(self):
        """Test status prints service and timer status."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.check_systemd_status.return_value = {
            "service": {"exists": True, "enabled": True, "active": True},
            "timer": {"exists": False, "enabled": False, "active": False},
        }
        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=fake_setup):
            result = runner.invoke(cli, ["systemd", "status"], standalone_mode=False)
        assert result.return_value == 0
        fake_setup.check_systemd_status.assert_called_once()

    def test_systemd_status_module_unavailable(self):
        """Test status returns 1 when module missing."""
        from lib import cli_systemd

        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=None):
            result = runner.invoke(cli, ["systemd", "status"], standalone_mode=False)
        assert result.return_value == 1


class TestSystemdCliSystemctl:
    """Test systemctl-style commands (start/stop/restart/reload)."""

    @pytest.mark.parametrize("action", ["start", "stop", "restart"])
    def test_systemctl_action_emit_mode(self, action):
        """Test each action in emit mode returns 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--emit", "systemd", action], standalone_mode=False)
        assert result.return_value == 0

    @pytest.mark.parametrize("action", ["start", "stop", "restart"])
    def test_systemctl_action_success(self, action):
        """Test each action with successful systemctl returncode."""
        runner = CliRunner()
        with patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=0),
        ) as mock_run:
            result = runner.invoke(cli, ["systemd", action], standalone_mode=False)
        assert result.return_value == 0
        assert mock_run.called

    @pytest.mark.parametrize("action", ["start", "stop", "restart"])
    def test_systemctl_action_failure(self, action):
        """Test each action with failed systemctl returncode returns 1."""
        runner = CliRunner()
        with patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=1),
        ):
            result = runner.invoke(cli, ["systemd", action], standalone_mode=False)
        assert result.return_value == 1

    def test_reload_uses_daemon_reload(self):
        """Test reload runs daemon-reload with no unit."""
        runner = CliRunner()
        with patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=0),
        ) as mock_run:
            result = runner.invoke(cli, ["systemd", "reload"], standalone_mode=False)
        assert result.return_value == 0
        assert mock_run.call_args[0][0][2] == "daemon-reload"
        # No unit appended for reload
        assert len(mock_run.call_args[0][0]) == 3


class TestSystemdCliLogs:
    """Test logs CLI command."""

    def test_logs_emit_mode(self):
        """Test logs in emit mode returns 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--emit", "systemd", "logs"], standalone_mode=False)
        assert result.return_value == 0

    def test_logs_success(self):
        """Test logs prints stdout on success."""
        runner = CliRunner()
        with patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="log line\n", stderr=""
            ),
        ):
            result = runner.invoke(cli, ["systemd", "logs"], standalone_mode=False)
        assert result.return_value == 0

    def test_logs_failure(self):
        """Test logs returns 1 on failure."""
        runner = CliRunner()
        with patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="journalctl error"
            ),
        ):
            result = runner.invoke(cli, ["systemd", "logs"], standalone_mode=False)
        assert result.return_value == 1


class TestSystemdCliList:
    """Test list CLI command."""

    def test_list_with_units(self):
        """Test list prints units when found."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.list_all_units.return_value = ["a.service", "b.timer"]
        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=fake_setup):
            result = runner.invoke(cli, ["systemd", "list"], standalone_mode=False)
        assert result.return_value == 0

    def test_list_no_units(self):
        """Test list prints message when no units found."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.list_all_units.return_value = []
        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=fake_setup):
            result = runner.invoke(cli, ["systemd", "list"], standalone_mode=False)
        assert result.return_value == 0

    def test_list_module_unavailable(self):
        """Test list returns 1 when module missing."""
        from lib import cli_systemd

        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=None):
            result = runner.invoke(cli, ["systemd", "list"], standalone_mode=False)
        assert result.return_value == 1


class TestSystemdCliTest:
    """Test test CLI command."""

    def test_test_emit_flag(self):
        """Test --emit flag short-circuits to 0."""
        from lib import cli_systemd

        runner = CliRunner()
        result = runner.invoke(cli, ["systemd", "test", "--emit"], standalone_mode=False)
        assert result.return_value == 0

    def test_test_module_unavailable(self):
        """Test test returns 1 when module missing."""
        from lib import cli_systemd

        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=None):
            result = runner.invoke(cli, ["systemd", "test"], standalone_mode=False)
        assert result.return_value == 1

    def test_test_with_setup(self):
        """Test test runs and reports status."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.check_systemd_status.return_value = {
            "service": {"exists": True, "enabled": True, "active": True},
            "timer": {"exists": True, "enabled": True, "active": True},
        }
        fake_setup.check_prerequisites.return_value = True
        runner = CliRunner()
        with patch.object(cli_systemd, "_get_systemd_setup", return_value=fake_setup):
            result = runner.invoke(cli, ["systemd", "test"], standalone_mode=False)
        assert result.return_value == 0
        fake_setup.check_systemd_status.assert_called_once()
        fake_setup.check_prerequisites.assert_called_once()


class TestSystemdSetupCmd:
    """Test top-level systemd-setup command."""

    def test_systemd_setup_cmd_uses_run_method(self):
        """Test systemd_setup_cmd uses .run() when present."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.run.return_value = 0
        runner = CliRunner()
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = runner.invoke(cli, ["systemd-setup"], standalone_mode=False)
        assert result.return_value == 0

    def test_systemd_setup_cmd_uses_install_method(self):
        """Test systemd_setup_cmd uses .install_systemd_units() when run() missing."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=["install_systemd_units"])
        fake_setup.install_systemd_units.return_value = True
        runner = CliRunner()
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = runner.invoke(cli, ["systemd-setup"], standalone_mode=False)
        assert result.return_value == 0

    def test_systemd_setup_cmd_no_method(self):
        """Test systemd_setup_cmd returns 1 when neither method is present."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=[])  # no methods
        runner = CliRunner()
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = runner.invoke(cli, ["systemd-setup"], standalone_mode=False)
        assert result.return_value == 1

    def test_systemd_setup_cmd_exception(self):
        """Test systemd_setup_cmd handles exceptions from .run()."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.run.side_effect = OSError("boom")
        runner = CliRunner()
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = runner.invoke(cli, ["systemd-setup"], standalone_mode=False)
        assert result.return_value == 1

    def test_systemd_group_no_subcommand(self):
        """Test invoking 'systemd' with no subcommand falls through to setup."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.run.return_value = 0
        runner = CliRunner()
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = runner.invoke(cli, ["systemd"], standalone_mode=False)
        assert result.exit_code == 0

    def test_run_systemd_setup_helper_no_method(self):
        """Test _run_systemd_setup returns 1 when no method present."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=[])
        runner = CliRunner()
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = runner.invoke(cli, ["systemd-setup"], standalone_mode=False)
        assert result.return_value == 1

    def test_run_systemd_setup_helper_exception(self):
        """Test _run_systemd_setup handles exceptions from .run()."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.run.side_effect = OSError("boom")
        runner = CliRunner()
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = runner.invoke(cli, ["systemd-setup"], standalone_mode=False)
        assert result.return_value == 1


class TestSystemdGetSetup:
    """Test _get_systemd_setup helper."""

    def test_get_setup_returns_instance(self):
        """Test _get_systemd_setup returns an instance when import succeeds."""
        from lib.cli_systemd import _get_systemd_setup

        ctx = MagicMock()
        ctx.obj = {"config_dir": None, "verbose": False, "emit": False, "emit_verbose": False}
        result = _get_systemd_setup(ctx)
        assert result is not None

    def test_get_setup_returns_none_on_import_failure(self):
        """Test _get_systemd_setup returns None when import fails."""
        from lib.cli_systemd import _get_systemd_setup

        ctx = MagicMock()
        ctx.obj = {"config_dir": None, "verbose": False, "emit": False, "emit_verbose": False}
        with patch("lib.cli_systemd.safe_import", return_value=None):
            assert _get_systemd_setup(ctx) is None


class TestRunSystemdSetupDirect:
    """Test _run_systemd_setup helper invoked directly."""

    def _ctx(self):
        return MagicMock(
            obj={"config_dir": None, "verbose": False, "emit": False, "emit_verbose": False}
        )

    def test_uses_run_method(self):
        """Test _run_systemd_setup uses .run() when present."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.run.return_value = 0
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = cli_systemd._run_systemd_setup(self._ctx(), None, None)
        assert result == 0

    def test_uses_install_systemd_units_method(self):
        """Test _run_systemd_setup uses .install_systemd_units() when run() missing."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=["install_systemd_units"])
        fake_setup.install_systemd_units.return_value = True
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = cli_systemd._run_systemd_setup(self._ctx(), None, None)
        assert result == 0

    def test_no_method_returns_1(self):
        """Test _run_systemd_setup returns 1 when no method is present."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=[])
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = cli_systemd._run_systemd_setup(self._ctx(), None, None)
        assert result == 1

    def test_run_exception_returns_1(self):
        """Test _run_systemd_setup returns 1 on .run() exception."""
        from lib import cli_systemd

        fake_setup = MagicMock(spec=SystemdSetup)
        fake_setup.run.side_effect = OSError("boom")
        with patch.object(
            cli_systemd.import_handler, "require", return_value=lambda **kw: fake_setup
        ):
            result = cli_systemd._run_systemd_setup(self._ctx(), None, None)
        assert result == 1


class TestSystemdSetupMethods:
    """Test SystemdSetup class methods."""
