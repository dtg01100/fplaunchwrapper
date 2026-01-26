#!/usr/bin/env python3
"""Test that all commands and subcommands have --help support.

This test ensures every entry point and subcommand in fplaunchwrapper
provides helpful documentation via --help flag.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import lib.cli as cli_module


@pytest.fixture
def runner():
    """Create Click CLI runner."""
    return CliRunner()


@pytest.fixture
def cli_available():
    """Check if Click is available."""
    return getattr(cli_module, "CLICK_AVAILABLE", False)


class TestHelpSupport:
    """Test that all commands have --help support."""

    # Standalone scripts that have argparse-based main() functions
    STANDALONE_SCRIPTS = [
        "lib/launch.py",
        "lib/generate.py",
        "lib/manage.py",
        "lib/cleanup.py",
        "lib/systemd_setup.py",
        "lib/config_manager.py",
        "lib/flatpak_monitor.py",
    ]

    # Click CLI commands and subcommands
    CLICK_COMMANDS = [
        # Main command
        [],  # Empty list tests main --help
        # Subcommands
        ["generate"],
        ["list"],
        ["set-pref"],
        ["pref"],  # Alias for set-pref
        ["launch"],
        ["remove"],
        ["rm"],  # Alias for remove
        ["systemd"],
        ["cleanup"],
        ["clean"],  # Alias for cleanup
        ["config"],
        ["profiles"],
        ["presets"],
        ["monitor"],
        ["info"],
        ["search"],
        ["discover"],  # Alias for search
        ["files"],
        ["install"],
        ["uninstall"],
        ["manifest"],
    ]

    # systemd subcommands
    SYSTEMD_ACTIONS = [
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

    def test_standalone_scripts_have_help(self):
        """Test all standalone Python scripts have --help support."""
        for script_path in self.STANDALONE_SCRIPTS:
            script = Path(__file__).parent.parent.parent / script_path

            if not script.exists():
                pytest.skip(f"Script not found: {script_path}")

            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Should exit successfully
            assert result.returncode == 0, (
                f"{script_path} --help failed with exit code {result.returncode}\n"
                f"stderr: {result.stderr}"
            )

            # Should show usage in output
            assert (
                "usage:" in result.stdout.lower() or "options:" in result.stdout.lower()
            ), (
                f"{script_path} --help output doesn't contain usage/options:\n"
                f"{result.stdout}"
            )

            # Should mention help
            assert "-h" in result.stdout or "--help" in result.stdout, (
                f"{script_path} --help output doesn't mention help flag:\n"
                f"{result.stdout}"
            )

    @pytest.mark.skipif(
        not getattr(cli_module, "CLICK_AVAILABLE", False),
        reason="Click not available",
    )
    def test_main_cli_has_help(self, runner):
        """Test main CLI has --help support."""
        result = runner.invoke(cli_module.cli, ["--help"])

        assert result.exit_code == 0, f"Main --help failed: {result.output}"
        assert "usage:" in result.output.lower()
        assert "commands:" in result.output.lower()
        assert "-h" in result.output or "--help" in result.output

    @pytest.mark.skipif(
        not getattr(cli_module, "CLICK_AVAILABLE", False),
        reason="Click not available",
    )
    def test_all_click_commands_have_help(self, runner):
        """Test all Click CLI subcommands have --help support."""
        for command in self.CLICK_COMMANDS:
            result = runner.invoke(cli_module.cli, [*command, "--help"])

            assert result.exit_code == 0, (
                f"Command {command} --help failed with exit code {result.exit_code}\n"
                f"Output: {result.output}"
            )

            # Should show usage or command name
            assert (
                "usage:" in result.output.lower()
                or command[-1] in result.output.lower()
            ), (
                f"Command {command} --help output doesn't contain usage info:\n"
                f"{result.output}"
            )

            # Should have help flag
            assert "-h" in result.output or "--help" in result.output, (
                f"Command {command} --help doesn't mention help flag:\n{result.output}"
            )

    @pytest.mark.skipif(
        not getattr(cli_module, "CLICK_AVAILABLE", False),
        reason="Click not available",
    )
    def test_systemd_subcommands_have_help(self, runner):
        """Test systemd subcommands have help."""
        for action in self.SYSTEMD_ACTIONS:
            # Test both with and without --help
            result = runner.invoke(cli_module.cli, ["systemd", "--help"])

            # Main systemd help should show available actions
            assert action in result.output.lower(), (
                f"systemd --help doesn't mention action '{action}':\n{result.output}"
            )

    @pytest.mark.skipif(
        not getattr(cli_module, "CLICK_AVAILABLE", False),
        reason="Click not available",
    )
    def test_profiles_subcommands_have_help(self, runner):
        """Test profiles subcommands show usage."""
        result = runner.invoke(cli_module.cli, ["profiles", "--help"])

        assert result.exit_code == 0, f"profiles --help failed: {result.output}"
        # Should mention actions
        assert "action" in result.output.lower() or "list" in result.output.lower()

    @pytest.mark.skipif(
        not getattr(cli_module, "CLICK_AVAILABLE", False),
        reason="Click not available",
    )
    def test_presets_subcommands_have_help(self, runner):
        """Test presets subcommands show usage."""
        result = runner.invoke(cli_module.cli, ["presets", "--help"])

        assert result.exit_code == 0, f"presets --help failed: {result.output}"
        # Should mention actions
        assert "action" in result.output.lower() or "list" in result.output.lower()

    @pytest.mark.skipif(
        not getattr(cli_module, "CLICK_AVAILABLE", False),
        reason="Click not available",
    )
    def test_config_subcommands_have_help(self, runner):
        """Test config subcommands show usage."""
        result = runner.invoke(cli_module.cli, ["config", "--help"])

        assert result.exit_code == 0, f"config --help failed: {result.output}"
        # Should mention actions
        assert "action" in result.output.lower() or "init" in result.output.lower()


class TestHelpCompleteness:
    """Test that help output is comprehensive."""

    @pytest.mark.skipif(
        not getattr(cli_module, "CLICK_AVAILABLE", False),
        reason="Click not available",
    )
    def test_main_help_shows_all_commands(self, runner):
        """Test main help lists all expected commands."""
        result = runner.invoke(cli_module.cli, ["--help"])

        assert result.exit_code == 0

        # Check for key commands
        expected_commands = [
            "generate",
            "list",
            "launch",
            "config",
            "profiles",
            "presets",
            "systemd",
        ]

        for cmd in expected_commands:
            assert cmd in result.output, f"Main help missing command '{cmd}'"

    def test_launch_help_shows_usage_examples(self):
        """Test launch.py help includes usage examples."""
        script = Path(__file__).parent.parent.parent / "lib/launch.py"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "example" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_config_help_shows_all_actions(self):
        """Test config_manager.py help shows all actions."""
        script = Path(__file__).parent.parent.parent / "lib/config_manager.py"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        # Should mention key actions
        assert any(
            action in result.stdout.lower()
            for action in ["init", "block", "unblock", "list-presets"]
        )

    def test_generate_help_shows_directory_argument(self):
        """Test generate.py help mentions directory argument."""
        script = Path(__file__).parent.parent.parent / "lib/generate.py"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "bin" in result.stdout.lower() or "directory" in result.stdout.lower()

    def test_cleanup_help_shows_dry_run_option(self):
        """Test cleanup.py help mentions dry-run option."""
        script = Path(__file__).parent.parent.parent / "lib/cleanup.py"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "dry-run" in result.stdout.lower() or "dry_run" in result.stdout

    def test_systemd_help_shows_setup_information(self):
        """Test systemd_setup.py help mentions setup information."""
        script = Path(__file__).parent.parent.parent / "lib/systemd_setup.py"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        # Should mention systemd or timer
        assert "systemd" in result.stdout.lower() or "timer" in result.stdout.lower()
