#!/usr/bin/env python3
"""Unit tests for portal_launcher.py.

Tests portal-aware launching, command construction, and subprocess interactions.
Uses mocks for subprocess calls and external dependencies.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest


class TestPortalLauncherAvailability:
    """Tests for flatpak-spawn availability detection."""

    @patch("lib.portal_launcher.shutil.which")
    def test_is_portal_launcher_available_true(self, mock_which: MagicMock) -> None:
        """Test that portal launcher is available when flatpak-spawn is found."""
        from lib.portal_launcher import is_portal_launcher_available

        mock_which.return_value = "/usr/bin/flatpak-spawn"

        with patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn"):
            result = is_portal_launcher_available()
            assert result is True

    @patch("lib.portal_launcher.shutil.which")
    def test_is_portal_launcher_available_false(self, mock_which: MagicMock) -> None:
        """Test that portal launcher is unavailable when flatpak-spawn is not found."""
        from lib.portal_launcher import is_portal_launcher_available

        with patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", None):
            result = is_portal_launcher_available()
            assert result is False


class TestLaunchWithPortal:
    """Tests for launch_with_portal function."""

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_launches_with_flatpak_spawn(self, mock_run: MagicMock) -> None:
        """Test that launch_with_portal uses flatpak-spawn."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_with_portal("org.mozilla.firefox")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "/usr/bin/flatpak-spawn"
        assert "--host" in cmd
        assert "flatpak" in cmd
        assert "run" in cmd
        assert "org.mozilla.firefox" in cmd

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_passes_arguments_to_command(self, mock_run: MagicMock) -> None:
        """Test that application arguments are passed through."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_with_portal(
            "org.mozilla.firefox", args=["--private-window", "https://example.com"]
        )

        cmd = mock_run.call_args[0][0]
        assert "--private-window" in cmd
        assert "https://example.com" in cmd

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_wait_flag_adds_wait_argument(self, mock_run: MagicMock) -> None:
        """Test that wait=True adds --wait to command."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_with_portal("org.mozilla.firefox", wait=True)

        cmd = mock_run.call_args[0][0]
        assert "--wait" in cmd

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_environment_overrides_applied(self, mock_run: MagicMock) -> None:
        """Test that environment variable overrides are applied."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_with_portal(
            "org.mozilla.firefox", env_overrides={"DISPLAY": ":1"}
        )

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert env["DISPLAY"] == ":1"
        assert "HOME" in env

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_cwd_is_passed(self, mock_run: MagicMock) -> None:
        """Test that working directory is passed to subprocess."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_with_portal("org.mozilla.firefox", cwd="/tmp")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == "/tmp"

    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", None)
    def test_raises_error_when_spawn_not_available(self) -> None:
        """Test that FileNotFoundError is raised when flatpak-spawn is not available."""
        from lib.portal_launcher import launch_with_portal

        with pytest.raises(FileNotFoundError) as exc_info:
            launch_with_portal("org.mozilla.firefox")

        assert "flatpak-spawn not found" in str(exc_info.value)

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_returns_completed_process(self, mock_run: MagicMock) -> None:
        """Test that subprocess.CompletedProcess is returned."""
        from lib.portal_launcher import launch_with_portal

        expected = MagicMock(returncode=0, stdout="output", stderr="")
        mock_run.return_value = expected

        result = launch_with_portal("org.mozilla.firefox")

        assert result == expected

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_captures_output(self, mock_run: MagicMock) -> None:
        """Test that subprocess is called with capture_output."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_with_portal("org.mozilla.firefox")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["capture_output"] is True
        assert call_kwargs["text"] is True


class TestLaunchDirect:
    """Tests for launch_direct function."""

    @patch("lib.portal_launcher.subprocess.run")
    def test_launches_with_flatpak_run(self, mock_run: MagicMock) -> None:
        """Test that launch_direct uses flatpak run."""
        from lib.portal_launcher import launch_direct

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_direct("org.mozilla.firefox")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "flatpak"
        assert cmd[1] == "run"
        assert cmd[2] == "org.mozilla.firefox"

    @patch("lib.portal_launcher.subprocess.run")
    def test_passes_arguments_to_command(self, mock_run: MagicMock) -> None:
        """Test that application arguments are passed through."""
        from lib.portal_launcher import launch_direct

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_direct("org.mozilla.firefox", args=["--version"])

        cmd = mock_run.call_args[0][0]
        assert "--version" in cmd

    @patch("lib.portal_launcher.subprocess.run")
    def test_wait_flag_adds_wait_argument(self, mock_run: MagicMock) -> None:
        """Test that wait=True adds --wait to command."""
        from lib.portal_launcher import launch_direct

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_direct("org.mozilla.firefox", wait=True)

        cmd = mock_run.call_args[0][0]
        assert "--wait" in cmd

    @patch("lib.portal_launcher.subprocess.run")
    def test_environment_overrides_applied(self, mock_run: MagicMock) -> None:
        """Test that environment variable overrides are applied."""
        from lib.portal_launcher import launch_direct

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_direct(
            "org.mozilla.firefox", env_overrides={"GTK_THEME": "dark"}
        )

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert env["GTK_THEME"] == "dark"
        assert "HOME" in env

    @patch("lib.portal_launcher.subprocess.run")
    def test_cwd_is_passed(self, mock_run: MagicMock) -> None:
        """Test that working directory is passed to subprocess."""
        from lib.portal_launcher import launch_direct

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        launch_direct("org.mozilla.firefox", cwd="/home/user")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == "/home/user"

    @patch("lib.portal_launcher.subprocess.run")
    def test_returns_completed_process(self, mock_run: MagicMock) -> None:
        """Test that subprocess.CompletedProcess is returned."""
        from lib.portal_launcher import launch_direct

        expected = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.return_value = expected

        result = launch_direct("org.mozilla.firefox")

        assert result == expected


class TestLaunch:
    """Tests for launch function (dispatcher)."""

    @patch("lib.portal_launcher.is_portal_launcher_available")
    @patch("lib.portal_launcher.launch_with_portal")
    def test_uses_portal_when_available_and_requested(
        self, mock_portal: MagicMock, mock_available: MagicMock
    ) -> None:
        """Test that portal launcher is used when available."""
        from lib.portal_launcher import launch

        mock_available.return_value = True
        mock_portal.return_value = MagicMock(returncode=0)

        launch("org.mozilla.firefox", use_portal=True)

        mock_portal.assert_called_once()
        mock_available.assert_called_once()

    @patch("lib.portal_launcher.is_portal_launcher_available")
    @patch("lib.portal_launcher.launch_direct")
    def test_uses_direct_when_portal_unavailable(
        self, mock_direct: MagicMock, mock_available: MagicMock
    ) -> None:
        """Test that direct launch is used when portal is unavailable."""
        from lib.portal_launcher import launch

        mock_available.return_value = False
        mock_direct.return_value = MagicMock(returncode=0)

        launch("org.mozilla.firefox", use_portal=True)

        mock_direct.assert_called_once()

    @patch("lib.portal_launcher.is_portal_launcher_available")
    @patch("lib.portal_launcher.launch_direct")
    def test_uses_direct_when_portal_disabled(
        self, mock_direct: MagicMock, mock_available: MagicMock
    ) -> None:
        """Test that direct launch is used when use_portal=False."""
        from lib.portal_launcher import launch

        mock_available.return_value = True
        mock_direct.return_value = MagicMock(returncode=0)

        launch("org.mozilla.firefox", use_portal=False)

        mock_direct.assert_called_once()

    @patch("lib.portal_launcher.is_portal_launcher_available")
    @patch("lib.portal_launcher.launch_with_portal")
    def test_passes_all_arguments_to_portal_launcher(
        self, mock_portal: MagicMock, mock_available: MagicMock
    ) -> None:
        """Test that all arguments are passed through to portal launcher."""
        from lib.portal_launcher import launch

        mock_available.return_value = True
        mock_portal.return_value = MagicMock(returncode=0)

        launch(
            "org.mozilla.firefox",
            args=["--private"],
            env_overrides={"VAR": "value"},
            cwd="/tmp",
            wait=True,
            use_portal=True,
        )

        mock_portal.assert_called_once_with(
            "org.mozilla.firefox",
            ["--private"],
            {"VAR": "value"},
            "/tmp",
            True,
        )

    @patch("lib.portal_launcher.is_portal_launcher_available")
    @patch("lib.portal_launcher.launch_direct")
    def test_passes_all_arguments_to_direct_launcher(
        self, mock_direct: MagicMock, mock_available: MagicMock
    ) -> None:
        """Test that all arguments are passed through to direct launcher."""
        from lib.portal_launcher import launch

        mock_available.return_value = False
        mock_direct.return_value = MagicMock(returncode=0)

        launch(
            "org.mozilla.firefox",
            args=["--version"],
            env_overrides={"DISPLAY": ":0"},
            cwd="/home",
            wait=False,
            use_portal=False,
        )

        mock_direct.assert_called_once_with(
            "org.mozilla.firefox",
            ["--version"],
            {"DISPLAY": ":0"},
            "/home",
            False,
        )


class TestGetLaunchCommand:
    """Tests for get_launch_command function."""

    @patch("lib.portal_launcher.is_portal_launcher_available")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_returns_portal_command_when_available(
        self, mock_available: MagicMock
    ) -> None:
        """Test that portal command is returned when available."""
        from lib.portal_launcher import get_launch_command

        mock_available.return_value = True

        result = get_launch_command("org.mozilla.firefox", use_portal=True)

        assert result[0] == "/usr/bin/flatpak-spawn"
        assert "--host" in result
        assert "flatpak" in result
        assert "run" in result
        assert "org.mozilla.firefox" in result

    @patch("lib.portal_launcher.is_portal_launcher_available")
    def test_returns_direct_command_when_portal_unavailable(
        self, mock_available: MagicMock
    ) -> None:
        """Test that direct command is returned when portal is unavailable."""
        from lib.portal_launcher import get_launch_command

        mock_available.return_value = False

        result = get_launch_command("org.mozilla.firefox", use_portal=True)

        assert result[0] == "flatpak"
        assert result[1] == "run"
        assert result[2] == "org.mozilla.firefox"

    @patch("lib.portal_launcher.is_portal_launcher_available")
    def test_returns_direct_command_when_disabled(
        self, mock_available: MagicMock
    ) -> None:
        """Test that direct command is returned when portal is disabled."""
        from lib.portal_launcher import get_launch_command

        mock_available.return_value = True

        result = get_launch_command("org.mozilla.firefox", use_portal=False)

        assert result[0] == "flatpak"
        assert result[1] == "run"

    @patch("lib.portal_launcher.is_portal_launcher_available")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_appends_arguments(self, mock_available: MagicMock) -> None:
        """Test that arguments are appended to command."""
        from lib.portal_launcher import get_launch_command

        mock_available.return_value = True

        result = get_launch_command(
            "org.mozilla.firefox", args=["--profile", "/tmp/profile"]
        )

        assert "--profile" in result
        assert "/tmp/profile" in result

    @patch("lib.portal_launcher.is_portal_launcher_available")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_empty_args_does_not_double_list(self, mock_available: MagicMock) -> None:
        """Test that None args doesn't add extra elements."""
        from lib.portal_launcher import get_launch_command

        mock_available.return_value = True

        result = get_launch_command("org.mozilla.firefox", args=None)

        firefox_count = result.count("org.mozilla.firefox")
        assert firefox_count == 1

    @patch("lib.portal_launcher.is_portal_launcher_available")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_returns_list_of_strings(self, mock_available: MagicMock) -> None:
        """Test that result is a list of strings."""
        from lib.portal_launcher import get_launch_command

        mock_available.return_value = True

        result = get_launch_command("org.example.app")

        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)


class TestCommandConstruction:
    """Integration tests for command construction scenarios."""

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_full_portal_launch_command_structure(self, mock_run: MagicMock) -> None:
        """Test complete command structure for portal launch."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0)

        launch_with_portal(
            "com.example.app",
            args=["--flag", "value"],
            env_overrides={"ENV1": "val1"},
            cwd="/custom/cwd",
            wait=True,
        )

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        kwargs = call_args[1]

        assert cmd == [
            "/usr/bin/flatpak-spawn",
            "--host",
            "flatpak",
            "run",
            "--wait",
            "com.example.app",
            "--flag",
            "value",
        ]
        assert kwargs["cwd"] == "/custom/cwd"
        assert kwargs["env"]["ENV1"] == "val1"
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True

    @patch("lib.portal_launcher.subprocess.run")
    def test_full_direct_launch_command_structure(self, mock_run: MagicMock) -> None:
        """Test complete command structure for direct launch."""
        from lib.portal_launcher import launch_direct

        mock_run.return_value = MagicMock(returncode=0)

        launch_direct(
            "com.example.app",
            args=["--arg1"],
            env_overrides={"KEY": "VALUE"},
            cwd="/work/dir",
            wait=True,
        )

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        kwargs = call_args[1]

        assert cmd == [
            "flatpak",
            "run",
            "--wait",
            "com.example.app",
            "--arg1",
        ]
        assert kwargs["cwd"] == "/work/dir"
        assert kwargs["env"]["KEY"] == "VALUE"


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_handles_subprocess_errors(self, mock_run: MagicMock) -> None:
        """Test that subprocess errors are propagated."""
        from lib.portal_launcher import launch_with_portal

        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["flatpak-spawn", "--host", "flatpak", "run", "org.test.app"],
            output="error output",
        )

        with pytest.raises(subprocess.CalledProcessError):
            launch_with_portal("org.test.app")

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_handles_none_env_overrides(self, mock_run: MagicMock) -> None:
        """Test that None env_overrides doesn't cause issues."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0)

        launch_with_portal("org.test.app", env_overrides=None)

        call_kwargs = mock_run.call_args[1]
        assert "HOME" in call_kwargs["env"]

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_handles_empty_args_list(self, mock_run: MagicMock) -> None:
        """Test that empty args list works correctly."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0)

        launch_with_portal("org.test.app", args=[])

        cmd = mock_run.call_args[0][0]
        assert cmd[-1] == "org.test.app"

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_special_characters_in_args(self, mock_run: MagicMock) -> None:
        """Test that special characters in args are preserved."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0)

        launch_with_portal(
            "org.test.app",
            args=["--option=value", 'arg with "quotes"', "path/to/file"],
        )

        cmd = mock_run.call_args[0][0]
        assert "--option=value" in cmd
        assert 'arg with "quotes"' in cmd
        assert "path/to/file" in cmd
