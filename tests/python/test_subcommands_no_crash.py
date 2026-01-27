#!/usr/bin/env python3
"""Test that all subcommands can be invoked without crashing.

This ensures no subcommand has basic syntax errors, import failures,
or other issues that would cause immediate crashes.
"""

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestSubcommandsDoNotCrash:
    """Ensure all subcommands can be invoked without crashing."""

    def test_main_cli_does_not_crash(self, runner):
        result = runner.invoke(cli, [])
        assert result.exit_code in [0, 2], "Main CLI crashed unexpectedly"

    @pytest.mark.parametrize(
        "command",
        [
            "generate",
            "list",
            "cleanup",
            "config",
            "search",
            "files",
        ],
    )
    def test_commands_without_required_args_do_not_crash(self, runner, command):
        """Commands that can run without args should not crash."""
        result = runner.invoke(cli, ["--emit", command])
        assert result.exit_code == 0, (
            f"{command} crashed with exit code {result.exit_code}"
        )
        assert result.exception is None, (
            f"{command} raised exception: {result.exception}"
        )

    @pytest.mark.parametrize(
        "command",
        [
            "launch",
            "remove",
            "install",
            "uninstall",
            "manifest",
            "info",
        ],
    )
    def test_commands_with_required_args_fail_gracefully(self, runner, command):
        """Commands requiring args should fail gracefully, not crash."""
        result = runner.invoke(cli, [command])
        assert result.exit_code != 0, f"{command} should fail without required args"
        acceptable = result.exception is None or (
            isinstance(result.exception, SystemExit) and result.exception.code == 2
        )
        assert acceptable, (
            f"{command} crashed with unexpected exception: {result.exception}"
        )

    def test_set_pref_without_args_fails_gracefully(self, runner):
        result = runner.invoke(cli, ["set-pref"])
        assert result.exit_code != 0
        acceptable = (
            result.exception is None
            or isinstance(result.exception, SystemExit)
            and result.exception.code == 2
        )
        assert acceptable

    def test_systemd_group_does_not_crash(self, runner):
        result = runner.invoke(cli, ["--emit", "systemd"])
        assert result.exit_code == 0, "systemd group crashed"
        assert result.exception is None

    @pytest.mark.parametrize(
        "subcommand",
        [
            "enable",
            "disable",
            "status",
            "start",
            "stop",
            "restart",
            "reload",
            "logs",
            "list",
            "test",
        ],
    )
    def test_systemd_subcommands_do_not_crash(self, runner, subcommand):
        result = runner.invoke(cli, ["--emit", "systemd", subcommand])
        assert result.exit_code == 0, f"systemd {subcommand} crashed"
        assert result.exception is None

    def test_profiles_group_does_not_crash(self, runner):
        result = runner.invoke(cli, ["profiles"])
        assert result.exit_code == 0, "profiles group crashed"
        assert result.exception is None

    @pytest.mark.parametrize("subcommand", ["list", "current"])
    def test_profiles_subcommands_without_args_do_not_crash(self, runner, subcommand):
        result = runner.invoke(cli, ["profiles", subcommand])
        assert result.exit_code == 0, f"profiles {subcommand} crashed"
        assert result.exception is None

    @pytest.mark.parametrize(
        "subcommand,args",
        [
            ("create", ["test-profile"]),
            ("switch", ["test-profile"]),
            ("export", ["test-profile"]),
            ("import", ["test-file.json"]),
        ],
    )
    def test_profiles_subcommands_with_args_do_not_crash(
        self, runner, subcommand, args
    ):
        result = runner.invoke(cli, ["profiles", subcommand] + args)
        assert result.exception is None, f"profiles {subcommand} crashed with exception"

    def test_presets_group_does_not_crash(self, runner):
        result = runner.invoke(cli, ["presets"])
        assert result.exit_code == 0, "presets group crashed"
        assert result.exception is None

    def test_presets_list_does_not_crash(self, runner):
        result = runner.invoke(cli, ["presets", "list"])
        assert result.exit_code == 0, "presets list crashed"
        assert result.exception is None

    def test_presets_get_without_arg_fails_gracefully(self, runner):
        result = runner.invoke(cli, ["presets", "get"])
        assert result.exit_code != 0
        acceptable = (
            result.exception is None
            or isinstance(result.exception, SystemExit)
            and result.exception.code == 2
        )
        assert acceptable

    def test_presets_get_with_arg_does_not_crash(self, runner):
        result = runner.invoke(cli, ["presets", "get", "browser"])
        assert result.exception is None, "presets get crashed"

    def test_presets_add_with_or_without_permission_does_not_crash(self, runner):
        result = runner.invoke(cli, ["presets", "add", "test"])
        assert result.exception is None, "presets add crashed"

    def test_presets_add_with_permission_does_not_crash(self, runner):
        result = runner.invoke(cli, ["presets", "add", "test", "-p", "--socket=x11"])
        assert result.exception is None, "presets add crashed"

    def test_presets_remove_does_not_crash(self, runner):
        result = runner.invoke(cli, ["presets", "remove", "test"])
        assert result.exception is None, "presets remove crashed"

    def test_monitor_does_not_crash_in_emit_mode(self, runner):
        result = runner.invoke(cli, ["--emit", "monitor"])
        assert result.exit_code == 0, "monitor crashed in emit mode"
        assert result.exception is None

    def test_systemd_setup_does_not_crash_in_emit_mode(self, runner):
        result = runner.invoke(cli, ["--emit", "systemd-setup"])
        assert result.exit_code == 0, "systemd-setup crashed in emit mode"
        assert result.exception is None

    @pytest.mark.parametrize("alias", ["rm", "clean", "pref", "discover"])
    def test_aliases_do_not_crash(self, runner, alias):
        result = runner.invoke(cli, [alias, "--help"])
        assert result.exit_code == 0, f"Alias {alias} crashed"
        assert result.exception is None

    def test_all_commands_with_help_flag_do_not_crash(self, runner):
        """Smoke test: every command with --help should not crash."""
        commands = [
            [],
            ["generate"],
            ["list"],
            ["launch"],
            ["remove"],
            ["cleanup"],
            ["config"],
            ["monitor"],
            ["info"],
            ["search"],
            ["install"],
            ["uninstall"],
            ["files"],
            ["manifest"],
            ["set-pref"],
            ["systemd-setup"],
            ["systemd"],
            ["profiles"],
            ["presets"],
            ["rm"],
            ["clean"],
            ["pref"],
            ["discover"],
        ]

        for cmd in commands:
            result = runner.invoke(cli, cmd + ["--help"])
            cmd_str = " ".join(cmd) if cmd else "main"
            assert result.exception is None, (
                f"{cmd_str} --help crashed: {result.exception}"
            )
            assert result.exit_code == 0, (
                f"{cmd_str} --help failed with code {result.exit_code}"
            )

    def test_emit_mode_prevents_crashes_in_destructive_commands(self, runner):
        """Emit mode should prevent actual execution and crashes."""
        potentially_destructive = [
            ["generate", "~/bin"],
            ["cleanup"],
            ["systemd", "enable"],
            ["systemd-setup"],
            ["monitor"],
        ]

        for cmd in potentially_destructive:
            result = runner.invoke(cli, ["--emit"] + cmd)
            cmd_str = " ".join(cmd)
            assert result.exception is None, (
                f"{cmd_str} crashed in emit mode: {result.exception}"
            )


class TestSubcommandExceptionHandling:
    """Test that subcommands handle exceptions gracefully."""

    def test_invalid_command_does_not_crash(self, runner):
        result = runner.invoke(cli, ["invalid-command-xyz"])
        assert result.exit_code != 0
        assert result.exception is None or "No such command" in str(result.output)

    def test_command_with_too_many_args_fails_gracefully(self, runner):
        result = runner.invoke(cli, ["list", "arg1", "arg2", "arg3"])
        acceptable = result.exception is None or isinstance(
            result.exception, SystemExit
        )
        assert acceptable, "Command with extra args crashed"

    def test_global_option_after_command_handled(self, runner):
        result = runner.invoke(cli, ["list", "--verbose"])
        acceptable = result.exception is None or isinstance(
            result.exception, SystemExit
        )
        assert acceptable, "Global option after command crashed"

    def test_empty_invocation_does_not_crash(self, runner):
        result = runner.invoke(cli, [])
        assert result.exception is None, "Empty invocation crashed"

    def test_multiple_flags_do_not_crash(self, runner):
        result = runner.invoke(cli, ["--verbose", "--emit", "--emit-verbose", "list"])
        assert result.exception is None, "Multiple flags crashed"


class TestSubcommandImportErrors:
    """Test that import failures are handled gracefully."""

    def test_commands_import_their_modules(self, runner):
        """Verify commands can actually import their backend modules."""
        commands_with_imports = [
            "generate",
            "list",
            "launch",
            "remove",
            "cleanup",
            "config",
            "monitor",
            "info",
            "search",
            "install",
            "uninstall",
            "manifest",
            "set-pref",
            "systemd-setup",
        ]

        for cmd in commands_with_imports:
            result = runner.invoke(cli, [cmd, "--help"])
            assert "Failed to import" not in result.output, f"{cmd} has import errors"
            assert result.exit_code == 0, f"{cmd} failed to import modules"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
