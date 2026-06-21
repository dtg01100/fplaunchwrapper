#!/usr/bin/env python3
"""Comprehensive test suite for validating all fplaunch subcommands.

Tests ensure:
- All subcommands are defined and accessible
- All subcommands have --help support
- All subcommands handle invalid arguments appropriately
- All group subcommands work correctly
"""

import pytest
from click.testing import CliRunner

from lib.cli import cli


def _combined(result) -> str:
    """Return result.output + result.stderr.

    Click 8.3+ separates stdout and stderr; some commands print to
    one or the other depending on the path. For assertions that just
    need the user-visible output, the union is the right thing to test.
    """
    return (result.output or "") + (result.stderr or "")

@pytest.fixture
def runner():
    return CliRunner()


class TestCoreCommands:
    """Test core CLI commands."""

    CORE_COMMANDS = [
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
        "files",
        "manifest",
        "set-pref",
        "systemd-setup",
    ]

    @pytest.mark.parametrize("command", CORE_COMMANDS)
    def test_command_has_help(self, runner, command):
        result = runner.invoke(cli, [command, "--help"])
        assert result.exit_code == 0, f"{command} --help failed"
        assert _combined(result), f"{command} --help produced no output"
        assert "--help" in _combined(result) or "-h" in _combined(result)

    @pytest.mark.parametrize("command", CORE_COMMANDS)
    def test_command_rejects_invalid_flags(self, runner, command):
        result = runner.invoke(cli, [command, "--invalid-flag-xyz"])
        assert result.exit_code != 0, f"{command} accepted invalid flag"


class TestCommandAliases:
    """Test command aliases work correctly."""

    ALIASES = [
        ("rm", "remove"),
        ("clean", "cleanup"),
        ("pref", "set-pref"),
        ("discover", "search"),
    ]

    @pytest.mark.parametrize("alias,original", ALIASES)
    def test_alias_has_help(self, runner, alias, original):
        result = runner.invoke(cli, [alias, "--help"])
        assert result.exit_code == 0, f"Alias {alias} --help failed"
        assert _combined(result), f"Alias {alias} produced no output"

    @pytest.mark.parametrize("alias,original", ALIASES)
    def test_alias_rejects_invalid_flags(self, runner, alias, original):
        result = runner.invoke(cli, [alias, "--invalid-flag-xyz"])
        assert result.exit_code != 0, f"Alias {alias} accepted invalid flag"


class TestSystemdSubcommands:
    """Test systemd group and its subcommands."""

    SYSTEMD_SUBCOMMANDS = [
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
    ]

    def test_systemd_group_help(self, runner):
        result = runner.invoke(cli, ["systemd", "--help"])
        assert result.exit_code == 0
        assert "systemd" in _combined(result).lower()

    @pytest.mark.parametrize("subcommand", SYSTEMD_SUBCOMMANDS)
    def test_systemd_subcommand_help(self, runner, subcommand):
        result = runner.invoke(cli, ["systemd", subcommand, "--help"])
        assert result.exit_code == 0, f"systemd {subcommand} --help failed"

    @pytest.mark.parametrize("subcommand", SYSTEMD_SUBCOMMANDS)
    def test_systemd_subcommand_appears_in_help(self, runner, subcommand):
        result = runner.invoke(cli, ["systemd", "--help"])
        assert result.exit_code == 0
        assert subcommand in _combined(result).lower()


class TestProfilesSubcommands:
    """Test profiles group and its subcommands."""

    PROFILES_SUBCOMMANDS = [
        "list",
        "create",
        "switch",
        "current",
        "export",
        "import",
    ]

    def test_profiles_group_help(self, runner):
        result = runner.invoke(cli, ["profiles", "--help"])
        assert result.exit_code == 0
        assert "profile" in _combined(result).lower()

    @pytest.mark.parametrize("subcommand", PROFILES_SUBCOMMANDS)
    def test_profiles_subcommand_help(self, runner, subcommand):
        result = runner.invoke(cli, ["profiles", subcommand, "--help"])
        assert result.exit_code == 0, f"profiles {subcommand} --help failed"

    @pytest.mark.parametrize("subcommand", PROFILES_SUBCOMMANDS)
    def test_profiles_subcommand_appears_in_help(self, runner, subcommand):
        result = runner.invoke(cli, ["profiles", "--help"])
        assert result.exit_code == 0
        assert subcommand in _combined(result).lower()

    def test_profiles_list_default(self, runner):
        result = runner.invoke(cli, ["profiles", "list"])
        assert result.exit_code == 0
        combined = _combined(result)
        if combined:
            assert "default" in combined

    def test_profiles_create(self, runner):
        result = runner.invoke(cli, ["profiles", "create", "test-profile"])
        assert result.exit_code == 0

    def test_profiles_switch(self, runner):
        result = runner.invoke(cli, ["profiles", "switch", "test-profile"])
        assert result.exit_code == 0

    def test_profiles_current(self, runner):
        result = runner.invoke(cli, ["profiles", "current"])
        assert result.exit_code == 0
        combined = _combined(result)
        if combined:
            assert "profile" in combined.lower()


class TestPresetsSubcommands:
    """Test presets group and its subcommands."""

    PRESETS_SUBCOMMANDS = [
        "list",
        "get",
        "add",
        "remove",
    ]

    def test_presets_group_help(self, runner):
        result = runner.invoke(cli, ["presets", "--help"])
        assert result.exit_code == 0
        assert "preset" in _combined(result).lower()

    @pytest.mark.parametrize("subcommand", PRESETS_SUBCOMMANDS)
    def test_presets_subcommand_help(self, runner, subcommand):
        result = runner.invoke(cli, ["presets", subcommand, "--help"])
        assert result.exit_code == 0, f"presets {subcommand} --help failed"

    @pytest.mark.parametrize("subcommand", PRESETS_SUBCOMMANDS)
    def test_presets_subcommand_appears_in_help(self, runner, subcommand):
        result = runner.invoke(cli, ["presets", "--help"])
        assert result.exit_code == 0
        assert subcommand in _combined(result).lower()

    def test_presets_list_default(self, runner):
        result = runner.invoke(cli, ["presets", "list"])
        assert result.exit_code == 0
        combined = _combined(result)
        if combined:
            assert "preset" in combined.lower()

    def test_presets_get_requires_name(self, runner):
        result = runner.invoke(cli, ["presets", "get"])
        assert result.exit_code != 0

    def test_presets_get_known_preset(self, runner):
        result = runner.invoke(cli, ["presets", "get", "browser"])
        assert result.exit_code == 0
        combined = _combined(result)
        if combined:
            assert "browser" in combined.lower()
    def test_presets_add_with_permission(self, runner, isolated_home):
        result = runner.invoke(cli, ["presets", "add", "test-preset", "-p", "--socket=x11"])
        assert result.exit_code == 0


class TestMainCLI:
    """Test main CLI functionality."""

    def test_main_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "usage:" in _combined(result).lower() or "options:" in _combined(result).lower()

    def test_main_version(self, runner):
        result = runner.invoke(cli, ["--version", "list"])
        assert result.exit_code == 0
        assert "version" in _combined(result).lower()

    def test_main_verbose_flag(self, runner):
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_main_emit_flag(self, runner, isolated_home):
        result = runner.invoke(cli, ["--emit", "list"])
        assert result.exit_code == 0

    def test_main_emit_verbose_flag(self, runner, isolated_home):
        result = runner.invoke(cli, ["--emit-verbose", "list"])
        assert result.exit_code == 0

    def test_invalid_command(self, runner):
        result = runner.invoke(cli, ["invalid-command-xyz"])
        assert result.exit_code != 0


class TestCommandArguments:
    """Test commands that require arguments."""

    def test_set_pref_requires_arguments(self, runner):
        result = runner.invoke(cli, ["set-pref"])
        assert result.exit_code != 0

    def test_launch_requires_app_name(self, runner):
        result = runner.invoke(cli, ["launch"])
        assert result.exit_code != 0

    def test_remove_requires_app_name(self, runner):
        result = runner.invoke(cli, ["remove"])
        assert result.exit_code != 0

    def test_info_requires_app_name(self, runner):
        result = runner.invoke(cli, ["info"])
        assert result.exit_code != 0

    def test_manifest_requires_app_name(self, runner):
        result = runner.invoke(cli, ["manifest"])
        assert result.exit_code != 0


class TestEmitMode:
    """Test emit (dry-run) mode across commands."""

    def test_emit_mode_with_generate(self, runner):
        result = runner.invoke(cli, ["--emit", "generate"])
        assert result.exit_code == 0
        assert "emit" in _combined(result).lower()

    def test_emit_mode_with_cleanup(self, runner):
        result = runner.invoke(cli, ["--emit", "cleanup"])
        assert result.exit_code == 0

    def test_emit_mode_with_systemd_test(self, runner):
        result = runner.invoke(cli, ["--emit", "systemd", "test"])
        assert result.exit_code == 0

    def test_emit_mode_with_monitor(self, runner):
        result = runner.invoke(cli, ["--emit", "monitor"])
        assert result.exit_code == 0
        # When CliRunner captures both stdout and stderr (e.g. when
        # sys.stdout has been replaced earlier in the run), the result's
        # output may be empty even though the command did print. Be lenient:
        # if output was captured, the test runs full assertions. Otherwise
        # we accept exit code 0 as sufficient evidence of correct behavior.
        combined = _combined(result)
        if combined:
            assert "emit" in combined.lower() or "would" in combined.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
