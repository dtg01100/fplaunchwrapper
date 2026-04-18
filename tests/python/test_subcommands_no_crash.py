#!/usr/bin/env python3
"""Targeted CLI dispatch checks for help pages, usage errors, and runtime paths.

This covers help output, representative Click usage failures, and a small set
of runtime dispatch checks without claiming broad non-crash smoke coverage.
"""

import subprocess
from unittest.mock import Mock, call, patch

import pytest
from click.testing import CliRunner

import lib.cli as cli_module

from lib.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestSubcommandHelpAndUsage:
    """Verify help pages, usage errors, and representative command dispatch."""

    def test_main_cli_shows_help(self, runner):
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "usage:" in result.output.lower()

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
        """Commands requiring args should return Click usage errors."""
        result = runner.invoke(cli, [command])
        assert result.exit_code != 0
        assert "usage:" in result.output.lower()
        assert "missing argument" in result.output.lower()

    def test_set_pref_without_args_fails_gracefully(self, runner):
        result = runner.invoke(cli, ["set-pref"])
        assert result.exit_code != 0
        assert "usage:" in result.output.lower()
        assert "missing argument" in result.output.lower()

    def test_presets_get_without_arg_fails_gracefully(self, runner):
        result = runner.invoke(cli, ["presets", "get"])
        assert result.exit_code != 0
        assert "usage:" in result.output.lower()
        assert "required" in result.output.lower()

    @pytest.mark.parametrize(
        "cmd",
        [
            [],
            ["generate"],
            ["list"],
            ["launch"],
            ["cleanup"],
            ["config"],
            ["monitor"],
            ["search"],
            ["install"],
            ["uninstall"],
            ["manifest"],
            ["set-pref"],
            ["systemd"],
            ["profiles"],
            ["presets"],
        ],
    )
    def test_help_pages_return_zero(self, runner, cmd):
        result = runner.invoke(cli, cmd + ["--help"])

        assert result.exit_code == 0
        assert "usage:" in result.output.lower()


class TestSubcommandExceptionHandling:
    """Test that subcommands handle exceptions gracefully."""

    def test_invalid_command_does_not_crash(self, runner):
        result = runner.invoke(cli, ["invalid-command-xyz"])
        assert result.exit_code != 0
        assert "no such command" in result.output.lower()

    def test_command_with_too_many_args_fails_gracefully(self, runner):
        result = runner.invoke(cli, ["list", "arg1", "arg2", "arg3"])
        assert result.exit_code != 0
        assert "usage:" in result.output.lower()
        assert "unexpected extra arguments" in result.output.lower()

    def test_global_option_after_command_handled(self, runner):
        result = runner.invoke(cli, ["list", "--verbose"])
        assert result.exit_code != 0
        assert "no such option" in result.output.lower()


class TestSubcommandImportErrors:
    """Test that import failures are handled gracefully."""

    def test_runtime_commands_dispatch_through_import_handler(self, runner, tmp_path):
        """Verify runtime command execution reaches import_handler.require."""

        required_symbols = {
            ("lib.generate", "WrapperGenerator"): type(
                "FakeGenerator",
                (),
                {
                    "__init__": lambda self, **kwargs: None,
                    "run": lambda self: 0,
                },
            ),
            ("lib.manage", "WrapperManager"): type(
                "FakeManager",
                (),
                {
                    "__init__": lambda self, **kwargs: None,
                    "display_wrappers": lambda self: None,
                    "remove_wrapper": lambda self, name, force=False: True,
                },
            ),
            ("lib.cleanup", "WrapperCleanup"): type(
                "FakeCleanup",
                (),
                {
                    "__init__": lambda self, **kwargs: None,
                    "run": lambda self: 0,
                },
            ),
            ("lib.config_manager", "create_config_manager"): lambda: Mock(),
            ("lib.flatpak_monitor", "main"): lambda **kwargs: None,
        }
        commands = [
            (["generate", str(tmp_path / "bin")], ("lib.generate", "WrapperGenerator")),
            (["list"], ("lib.manage", "WrapperManager")),
            (["remove", "firefox", "--force"], ("lib.manage", "WrapperManager")),
            (["cleanup"], ("lib.cleanup", "WrapperCleanup")),
            (["config"], ("lib.config_manager", "create_config_manager")),
            (["monitor"], ("lib.flatpak_monitor", "main")),
            (["install", "org.example.App"], ("lib.generate", "WrapperGenerator")),
            (["uninstall", "org.example.App"], ("lib.manage", "WrapperManager")),
        ]

        def fake_require(module_name, symbol_name):
            return required_symbols[(module_name, symbol_name)]

        with patch.object(cli_module.import_handler, "require", side_effect=fake_require) as mock_require, patch.object(
            cli_module,
            "run_command",
            return_value=subprocess.CompletedProcess(args=["flatpak"], returncode=0, stdout="", stderr=""),
        ):
            for argv, expected in commands:
                result = runner.invoke(cli, argv, standalone_mode=False)
                assert result.return_value == 0, f"{argv!r} did not dispatch cleanly"

        assert mock_require.call_args_list == [call(*expected) for _, expected in commands]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
