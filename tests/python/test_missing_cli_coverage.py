#!/usr/bin/env python3
"""Tests for CLI commands that were missing coverage.

Tests profiles, presets, install, uninstall, and manifest commands
using Click CLI testing framework.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner


import lib.cli as cli_module


@pytest.fixture
def runner():
    """Create Click CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_bin_dir():
    """Create temporary bin directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestProfilesCLI:
    """Test profiles CLI command."""

    def test_profiles_list_shows_default(self, runner, temp_config_dir):
        """Test profiles list shows default profile."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["profiles"])

            assert result.exit_code == 0
            assert "default" in result.output.lower()

    def test_profiles_create(self, runner, temp_config_dir):
        """Test creating a new profile."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["profiles", "create", "work"])

            assert result.exit_code == 0
            assert "created" in result.output.lower()

    def test_profiles_create_requires_name(self, runner, temp_config_dir):
        """Test profiles create requires profile name."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["profiles", "create"])

            assert result.exit_code != 0
            assert "missing argument" in result.output.lower()

    def test_profiles_switch(self, runner, temp_config_dir):
        """Test switching profiles."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            # First create a profile
            runner.invoke(cli_module.cli, ["profiles", "create", "test"])

            # Then switch to it
            result = runner.invoke(cli_module.cli, ["profiles", "switch", "test"])

            assert result.exit_code == 0
            assert "switched" in result.output.lower()

    def test_profiles_current(self, runner, temp_config_dir):
        """Test showing current profile."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["profiles", "current"])

            assert result.exit_code == 0
            assert "current" in result.output.lower()

    def test_profiles_export(self, runner, temp_config_dir, tmp_path):
        """Test exporting a profile."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            _ = tmp_path / "test_profile.toml"
            result = runner.invoke(cli_module.cli, ["profiles", "export", "default"])

            assert result.exit_code == 0
            assert "exported profile" in result.output.lower()

    def test_profiles_import(self, runner, temp_config_dir, tmp_path):
        """Test importing a profile."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            # Create a dummy profile file
            profile_file = tmp_path / "import_profile.toml"
            profile_file.write_text("[app_preferences]\n")

            result = runner.invoke(cli_module.cli, ["profiles", "import", str(profile_file)])

            assert result.exit_code == 0
            assert "imported profile" in result.output.lower()

    def test_profiles_invalid_action(self, runner, temp_config_dir):
        """Test profiles with invalid action."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["profiles", "invalid"])

            assert result.exit_code != 0
            assert "no such command" in result.output.lower()


class TestPresetsCLI:
    """Test presets CLI command."""

    def test_presets_list(self, runner, temp_config_dir):
        """Test listing permission presets."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["presets"])

            assert result.exit_code == 0
            assert "presets" in result.output.lower()

    def test_presets_list_without_action(self, runner, temp_config_dir):
        """Test presets without action defaults to list."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["presets"])

            assert result.exit_code == 0

    def test_presets_get_requires_name(self, runner, temp_config_dir):
        """Test presets get requires preset name."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["presets", "get"])

            assert result.exit_code != 0
            assert "required" in result.output.lower()

    def test_presets_get_invalid_preset(self, runner, temp_config_dir):
        """Test presets get with invalid preset name."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(
                cli_module.cli,
                ["presets", "get", "nonexistent"],
                standalone_mode=False,
            )

            assert result.return_value == 1
            assert "not found" in result.output.lower()

    def test_presets_add_requires_name_and_permissions(self, runner, temp_config_dir):
        """Test presets add requires name and permissions."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(
                cli_module.cli,
                ["presets", "add", "test"],
                standalone_mode=False,
            )

            assert result.return_value == 1
            assert "at least one permission is required" in result.output.lower()

    def test_presets_add(self, runner, temp_config_dir):
        """Test adding a new preset."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(
                cli_module.cli,
                [
                    "presets",
                    "add",
                    "test_preset",
                    "-p",
                    "filesystem=home",
                    "-p",
                    "socket=pulseaudio",
                ],
            )

            assert result.exit_code == 0
            assert "added preset" in result.output.lower()

    def test_presets_remove_requires_name(self, runner, temp_config_dir):
        """Test presets remove requires preset name."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["presets", "remove"])

            assert result.exit_code != 0
            assert "missing argument" in result.output.lower()

    def test_presets_invalid_action(self, runner, temp_config_dir):
        """Test presets with invalid action."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["presets", "invalid"])

            assert result.exit_code != 0
            assert "no such command" in result.output.lower()


class TestInstallCLI:
    """Test install CLI command."""

    @patch("subprocess.run")
    @patch("lib.generate.WrapperGenerator")
    def test_install_emit_mode(self, mock_generator, mock_run, runner):
        """Test install in emit mode doesn't actually install."""
        mock_run.return_value = Mock(returncode=0)
        result = runner.invoke(cli_module.cli, ["install", "--emit", "org.example.app"])

        assert result.exit_code == 0
        assert "emit" in result.output.lower()

    @patch("subprocess.run")
    @patch("lib.generate.WrapperGenerator")
    def test_install_flatpak_success(self, mock_generator, mock_run, runner, temp_config_dir):
        """Test successful install of Flatpak app."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_generator.return_value.run.return_value = 0
        result = runner.invoke(
            cli_module.cli,
            [
                "install",
                "org.example.app",  # Valid Flatpak name with 2 periods
            ],
        )

        assert result.exit_code == 0
        # Should have tried to install flatpak
        assert mock_run.called

    @patch("lib.cli.run_command")
    def test_install_flatpak_failure_returns_error_exit_and_message(self, mock_run_command, runner):
        """Test failed Flatpak install returns the subprocess exit code."""
        mock_run_command.return_value = Mock(returncode=7, stderr="permission denied")

        result = runner.invoke(
            cli_module.cli,
            ["install", "org.example.app"],
            standalone_mode=False,
        )

        assert result.return_value == 7
        assert "failed to install flatpak app" in result.output.lower()

    @patch("subprocess.run")
    @patch("lib.generate.WrapperGenerator")
    def test_install_requires_app_name(self, mock_generator, mock_run, runner):
        """Test install requires app name argument."""
        result = runner.invoke(cli_module.cli, ["install"])

        assert result.exit_code != 0
        assert "missing argument" in result.output.lower()


class TestUninstallCLI:
    """Test uninstall CLI command."""

    @patch("subprocess.run")
    @patch("lib.manage.WrapperManager")
    def test_uninstall_emit_mode(self, mock_manager, mock_run, runner):
        """Test uninstall in emit mode doesn't actually uninstall."""
        result = runner.invoke(cli_module.cli, ["uninstall", "--emit", "org.example.app"])

        assert result.exit_code == 0
        assert "emit" in result.output.lower()

    @patch("subprocess.run")
    def test_uninstall_success(self, mock_run, runner, temp_config_dir):
        """Test successful uninstall."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        result = runner.invoke(
            cli_module.cli,
            [
                "uninstall",
                "org.example.app",
            ],
        )

        assert result.exit_code == 0
        assert "uninstalled" in result.output.lower()

    @patch("subprocess.run")
    def test_uninstall_with_data_removal(self, mock_run, runner, temp_config_dir):
        """Test uninstall with --remove-data flag."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        result = runner.invoke(
            cli_module.cli,
            [
                "uninstall",
                "--remove-data",
                "org.example.app",
            ],
        )

        assert result.exit_code == 0
        # Should have called with --delete-data flag
        call_args = mock_run.call_args[0][0]
        assert "--delete-data" in call_args


class TestManifestCLI:
    """Test manifest CLI command."""

    @patch("subprocess.run")
    def test_manifest_emit_mode(self, mock_run, runner):
        """Test manifest in emit mode."""
        result = runner.invoke(cli_module.cli, ["manifest", "--emit", "org.example.app"])

        assert result.exit_code == 0
        assert "emit" in result.output.lower()

    @patch("subprocess.run")
    def test_manifest_success(self, mock_run, runner):
        """Test successful manifest retrieval."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"id": "org.example.app"}',
            stderr="",
        )
        result = runner.invoke(cli_module.cli, ["manifest", "org.example.app"])

        assert result.exit_code == 0
        # The manifest command doesn't print to Click's output on success;
        # it lets flatpak output go directly to stdout. Verify the subprocess
        # was called correctly instead.
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "flatpak" in call_args
        assert "--show-manifest" in call_args
        assert "org.example.app" in call_args

    @patch("subprocess.run")
    def test_manifest_calls_flatpak_correctly(self, mock_run, runner):
        """Test manifest command calls flatpak info --show-manifest."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        result = runner.invoke(cli_module.cli, ["manifest", "org.example.app"])

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args == ["flatpak", "info", "--show-manifest", "org.example.app"]

    @patch("subprocess.run")
    def test_manifest_failure_returns_error_exit_and_message(self, mock_run, runner):
        mock_run.return_value = Mock(returncode=1, stderr="App not found")

        result = runner.invoke(cli_module.cli, ["manifest", "org.example.app"])

        assert result.exit_code == 1
        assert "failed to get manifest" in result.output.lower()
