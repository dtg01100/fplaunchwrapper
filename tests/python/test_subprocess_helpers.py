"""Tests for lib.subprocess_helpers."""

import subprocess
from unittest.mock import patch

from lib.subprocess_helpers import run_crontab, run_systemctl


class TestRunSystemctl:
    """Test run_systemctl helper."""

    def test_passes_args_to_systemctl(self):
        """Test that args are passed as 'systemctl --user <args>'."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_systemctl("status", "fplaunch-wrapper.service")
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["systemctl", "--user", "status", "fplaunch-wrapper.service"]

    def test_uses_default_timeout(self):
        """Test default timeout is 30 seconds."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_systemctl("is-active")
        assert mock_run.call_args.kwargs.get("timeout") == 30

    def test_custom_timeout(self):
        """Test custom timeout is respected."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_systemctl("is-active", timeout=5)
        assert mock_run.call_args.kwargs.get("timeout") == 5

    def test_captures_output_as_text(self):
        """Test that output is captured as text."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_systemctl("is-active")
        kwargs = mock_run.call_args.kwargs
        assert kwargs.get("capture_output") is True
        assert kwargs.get("text") is True
        assert kwargs.get("check") is False

    def test_returns_completed_process(self):
        """Test that the helper returns a CompletedProcess."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="active", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = run_systemctl("is-active")
        assert result.returncode == 0
        assert result.stdout == "active"

    def test_with_no_args(self):
        """Test that calling with no extra args still works."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_systemctl()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["systemctl", "--user"]


class TestRunCrontab:
    """Test run_crontab helper."""

    def test_passes_args_to_crontab(self):
        """Test that args are passed as 'crontab <args>'."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_crontab("-l")
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["crontab", "-l"]

    def test_uses_default_timeout(self):
        """Test default timeout is 10 seconds."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_crontab("-l")
        assert mock_run.call_args.kwargs.get("timeout") == 10

    def test_custom_timeout(self):
        """Test custom timeout is respected."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_crontab("-l", timeout=2)
        assert mock_run.call_args.kwargs.get("timeout") == 2

    def test_passes_input_when_provided(self):
        """Test that input_text is passed to subprocess when provided."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_crontab("-", input_text="0 * * * * /usr/bin/fplaunch\n")
        assert mock_run.call_args.kwargs.get("input") == "0 * * * * /usr/bin/fplaunch\n"

    def test_no_input_when_none(self):
        """Test that input is not in kwargs when input_text is None."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_crontab("-l")
        assert "input" not in mock_run.call_args.kwargs

    def test_captures_output_as_text(self):
        """Test that output is captured as text."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_crontab("-l")
        kwargs = mock_run.call_args.kwargs
        assert kwargs.get("capture_output") is True
        assert kwargs.get("text") is True
        assert kwargs.get("check") is False

    def test_returns_completed_process(self):
        """Test that the helper returns a CompletedProcess."""
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="0 * * * * echo hi", stderr=""
        )
        with patch("subprocess.run", return_value=mock_result):
            result = run_crontab("-l")
        assert result.returncode == 0
        assert "echo hi" in result.stdout
