#!/usr/bin/env python3
"""Tests for CLI commands that were missing coverage.

Tests profiles, presets, install, uninstall, and manifest commands
using Click CLI testing framework.
"""

import io

import pytest

# Only import if available, skip if not
try:
    from click.testing import CliRunner
    import lib.cli as cli_module

    HAS_CLI = True
except ImportError:
    HAS_CLI = False


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def captured_console(monkeypatch):
    """Capture Rich Console output to a StringIO for verification.

    CliRunner does not capture Rich Console output reliably when running in
    the full test suite, so we redirect Rich output to a StringIO that we
    can check directly.
    """
    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(cli_module.console, "_file", out)
    monkeypatch.setattr(cli_module.console_err, "_file", err)
    return out, err


class TestProfilesCLI:
    """Test profiles CLI command."""

    def test_profiles_list_shows_default(self, cli_runner, isolated_home, captured_console):
        """Test profiles list shows default profile."""
        out, err = captured_console
        result = cli_runner.invoke(cli_module.cli, ["profiles"])
        assert result.exit_code == 0
        output = (out.getvalue() + err.getvalue()).lower()
        assert "default" in output

    def test_profiles_create(self, cli_runner, isolated_home, captured_console):
        """Test creating a new profile."""
        out, err = captured_console
        result = cli_runner.invoke(cli_module.cli, ["profiles", "create", "work"])
        assert result.exit_code == 0
        output = (out.getvalue() + err.getvalue()).lower()
        assert "created" in output

    def test_profiles_create_requires_name(self, cli_runner, isolated_home):
        """Test profiles create requires profile name."""
        result = cli_runner.invoke(cli_module.cli, ["profiles", "create"])
        assert result.exit_code != 0
        output = result.output.lower()
        assert "missing argument" in output

    def test_profiles_switch(self, cli_runner, isolated_home, captured_console):
        """Test switching profiles."""
        out, err = captured_console
        cli_runner.invoke(cli_module.cli, ["profiles", "create", "test"])
        result = cli_runner.invoke(cli_module.cli, ["profiles", "switch", "test"])
        assert result.exit_code == 0
        output = (out.getvalue() + err.getvalue()).lower()
        assert "switched" in output

    def test_profiles_current(self, cli_runner, isolated_home, captured_console):
        """Test showing current profile."""
        out, err = captured_console
        result = cli_runner.invoke(cli_module.cli, ["profiles", "current"])
        assert result.exit_code == 0
        output = (out.getvalue() + err.getvalue()).lower()
        assert "current" in output

    def test_profiles_export(self, cli_runner, isolated_home, tmp_path):
        """Test exporting a profile."""
        output_file = tmp_path / "test_profile.toml"
        result = cli_runner.invoke(
            cli_module.cli, ["profiles", "export", "default", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists()

    def test_profiles_import(self, cli_runner, isolated_home, tmp_path, captured_console):
        """Test importing a profile."""
        out, err = captured_console
        profile_file = tmp_path / "import_profile.toml"
        profile_file.write_text("[app_preferences]\n")
        result = cli_runner.invoke(cli_module.cli, ["profiles", "import", str(profile_file)])
        assert result.exit_code == 0
        output = (out.getvalue() + err.getvalue()).lower()
        assert "imported" in output

    def test_profiles_invalid_action(self, cli_runner, isolated_home):
        """Test profiles with invalid action."""
        result = cli_runner.invoke(cli_module.cli, ["profiles", "invalid"])
        assert result.exit_code != 0
        output = result.output.lower()
        assert "no such command" in output


class TestPresetsCLI:
    """Test presets CLI command."""

    def test_presets_list(self, cli_runner, isolated_home, captured_console):
        """Test listing permission presets."""
        out, err = captured_console
        result = cli_runner.invoke(cli_module.cli, ["presets"])
        assert result.exit_code == 0
        output = (out.getvalue() + err.getvalue()).lower()
        assert "presets" in output

    def test_presets_list_without_action(self, cli_runner, isolated_home):
        """Test presets without action defaults to list."""
        result = cli_runner.invoke(cli_module.cli, ["presets"])
        assert result.exit_code == 0

    def test_presets_get_requires_name(self, cli_runner, isolated_home):
        """Test presets get requires preset name."""
        result = cli_runner.invoke(cli_module.cli, ["presets", "get"])
        assert result.exit_code != 0
        output = result.output.lower()
        assert "required" in output

    def test_presets_remove_requires_name(self, cli_runner, isolated_home):
        """Test presets remove requires preset name."""
        result = cli_runner.invoke(cli_module.cli, ["presets", "remove"])
        assert result.exit_code != 0
        output = result.output.lower()
        assert "missing argument" in output

    def test_presets_invalid_action(self, cli_runner, isolated_home):
        """Test presets with invalid action."""
        result = cli_runner.invoke(cli_module.cli, ["presets", "invalid"])
        assert result.exit_code != 0
        output = result.output.lower()
        assert "no such command" in output


class TestInstallCLI:
    """Test install CLI command."""

    def test_install_requires_app_name(self, cli_runner, isolated_home):
        """Test install requires app name argument."""
        result = cli_runner.invoke(cli_module.cli, ["install"])
        assert result.exit_code != 0
        output = result.output.lower()
        assert "missing argument" in output


class TestUninstallCLI:
    """Test uninstall CLI command."""

    def test_uninstall_with_data_removal(self, cli_runner, isolated_home):
        """Test uninstall with --remove-data flag sets correct flag."""
        from unittest.mock import Mock, patch

        with (
            patch("subprocess.run") as mock_run,
            patch("lib.manage.WrapperManager") as mock_manager,
        ):
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            mock_manager.return_value.remove_wrapper.return_value = True
            result = cli_runner.invoke(
                cli_module.cli, ["uninstall", "--remove-data", "org.example.app"]
            )
            assert result.exit_code == 0
            call_args = mock_run.call_args[0][0]
            assert "--delete-data" in call_args


class TestManifestCLI:
    """Test manifest CLI command."""

    def test_manifest_calls_flatpak_correctly(self, cli_runner, isolated_home):
        """Test manifest command calls flatpak info --show-manifest."""
        from unittest.mock import patch, Mock

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            result = cli_runner.invoke(cli_module.cli, ["manifest", "org.example.app"])
            assert result.exit_code == 0
            call_args = mock_run.call_args[0][0]
            assert call_args == ["flatpak", "info", "--show-manifest", "org.example.app"]
