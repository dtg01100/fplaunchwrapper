"""Direct unit tests for lib.cli_utils."""

import io
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from lib.cli_utils import find_fplaunch_script, run_command


SCRIPT_NAME = "fplaunch-cli-utils-unlikely-script-xyz"


@pytest.fixture
def capture_console(monkeypatch):
    """Replace lib.cli_utils.console with a Console that writes to StringIO."""
    buffer = io.StringIO()
    new_console = Console(file=buffer, force_terminal=False, width=200)
    monkeypatch.setattr("lib.cli_utils.console", new_console)
    return buffer, new_console


class TestRunCommandEmit:
    """run_command in emit_mode prints commands and returns None."""

    def test_emit_returns_none(self, capture_console):
        """emit_mode returns None without invoking subprocess.run."""
        buf, _ = capture_console
        with patch("subprocess.run") as mock_run:
            result = run_command(["echo", "hi"], emit_mode=True)
        assert result is None
        mock_run.assert_not_called()

    def test_emit_prints_emit_marker(self, capture_console):
        """emit_mode prints the cyan 'EMIT:' line with the joined command."""
        buf, _ = capture_console
        run_command(["echo", "hi", "there"], emit_mode=True)
        out = buf.getvalue()
        assert "EMIT:" in out
        assert "echo hi there" in out

    def test_emit_with_description_prints_purpose(self, capture_console):
        """emit_mode with a description also prints the dim 'Purpose:' line."""
        buf, _ = capture_console
        run_command(
            ["echo", "hi"], description="make some noise", emit_mode=True
        )
        out = buf.getvalue()
        assert "EMIT:" in out
        assert "Purpose:" in out
        assert "make some noise" in out

    def test_emit_without_description_omits_purpose(self, capture_console):
        """emit_mode with no description does not print a 'Purpose:' line."""
        buf, _ = capture_console
        run_command(["echo", "hi"], emit_mode=True)
        out = buf.getvalue()
        assert "Purpose:" not in out


class TestRunCommandExecution:
    """run_command executes the subprocess and returns the CompletedProcess."""

    @pytest.fixture
    def ok_run(self):
        """Patch subprocess.run to return a successful CompletedProcess."""
        result = subprocess.CompletedProcess(
            args=["echo", "hi"], returncode=0, stdout="hi\n", stderr=""
        )
        with patch("subprocess.run", return_value=result) as mock_run:
            yield mock_run

    def test_description_true_uses_console_status(self, monkeypatch, ok_run):
        """description path runs inside console.status and returns the result."""
        new_console = MagicMock()
        monkeypatch.setattr("lib.cli_utils.console", new_console)

        result = run_command(
            ["echo", "hi"], description="doing it", show_output=False
        )
        assert result is not None
        assert result.returncode == 0
        new_console.status.assert_called_once()
        status_msg = new_console.status.call_args.args[0]
        assert "doing it" in status_msg
        ok_run.assert_called_once()

    def test_description_false_skips_console_status(self, monkeypatch, ok_run):
        """description='' runs without entering console.status."""
        new_console = MagicMock()
        monkeypatch.setattr("lib.cli_utils.console", new_console)

        result = run_command(["echo", "hi"], show_output=False)
        assert result is not None
        assert result.returncode == 0
        new_console.status.assert_not_called()
        ok_run.assert_called_once()

    def test_show_output_false_passes_capture_output_true(self, ok_run):
        """show_output=False -> capture_output=True with text and timeout=30."""
        run_command(["echo", "hi"], show_output=False)
        kwargs = ok_run.call_args.kwargs
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is False
        assert kwargs["timeout"] == 30

    def test_show_output_true_passes_capture_output_false(self, ok_run):
        """show_output=True -> capture_output=False."""
        run_command(["echo", "hi"], show_output=True)
        kwargs = ok_run.call_args.kwargs
        assert kwargs["capture_output"] is False

    def test_show_output_false_inside_description_path(self, ok_run):
        """capture_output follows show_output inside the description branch too."""
        run_command(
            ["echo", "hi"], description="x", show_output=False
        )
        kwargs = ok_run.call_args.kwargs
        assert kwargs["capture_output"] is True

    def test_propagates_timeout_expired(self):
        """subprocess.TimeoutExpired is not swallowed by run_command."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["sleep"], timeout=30),
        ):
            with pytest.raises(subprocess.TimeoutExpired):
                run_command(["sleep", "60"], show_output=False)


class TestFindFplaunchScript:
    """find_fplaunch_script searches cwd then common PATH locations."""

    def test_returns_none_when_nothing_exists(self, monkeypatch, tmp_path):
        """Returns None when no candidate path exists."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        result = find_fplaunch_script("definitely-not-a-real-script-xyz123")
        assert result is None

    def test_finds_executable_in_cwd(self, monkeypatch, tmp_path):
        """Finds an executable file located in the current working directory."""
        script = tmp_path / SCRIPT_NAME
        script.write_text("#!/bin/sh\necho hi\n")
        script.chmod(0o755)
        monkeypatch.chdir(tmp_path)
        result = find_fplaunch_script(SCRIPT_NAME)
        assert result == script

    def test_skips_non_executable_file(self, monkeypatch, tmp_path):
        """A non-+x file in cwd is skipped and not returned."""
        script = tmp_path / SCRIPT_NAME
        script.write_text("#!/bin/sh\necho hi\n")
        script.chmod(0o644)
        monkeypatch.chdir(tmp_path)
        result = find_fplaunch_script(SCRIPT_NAME)
        assert result is None

    def test_finds_in_local_bin(self, monkeypatch, tmp_path):
        """Finds an executable in $HOME/.local/bin when cwd has no match."""
        local_bin = tmp_path / ".local" / "bin"
        local_bin.mkdir(parents=True)
        script = local_bin / SCRIPT_NAME
        script.write_text("#!/bin/sh\necho hi\n")
        script.chmod(0o755)
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        result = find_fplaunch_script(SCRIPT_NAME)
        assert result == script

    def test_cwd_takes_precedence_over_local_bin(self, monkeypatch, tmp_path):
        """cwd match is returned before ~/.local/bin match is considered."""
        cwd_script = tmp_path / SCRIPT_NAME
        cwd_script.write_text("#!/bin/sh\necho cwd\n")
        cwd_script.chmod(0o755)

        local_bin = tmp_path / ".local" / "bin"
        local_bin.mkdir(parents=True)
        home_script = local_bin / SCRIPT_NAME
        home_script.write_text("#!/bin/sh\necho home\n")
        home_script.chmod(0o755)

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        result = find_fplaunch_script(SCRIPT_NAME)
        assert result == cwd_script
