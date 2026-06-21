#!/usr/bin/env python3
"""Coverage tests for lib.notifications.

Targets the gap regions identified in the coverage report:
- line 86: send_notification isinstance validation (title/message)
- lines 139-161: the ``if __name__ == "__main__":`` entry point block
- send_update_failure_notification wrapper paths
"""

from __future__ import annotations

import io
import logging
import runpy
import subprocess
import sys
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from lib.notifications import (
    _sanitize_notification_text,
    notify_send_available,
    send_notification,
    send_update_failure_notification,
)


class TestSendNotificationIsinstanceValidation:
    """Cover line 86: ``not isinstance(title, str) or not isinstance(message, str)``."""

    def test_non_string_title_returns_false(self) -> None:
        """Integer title returns False; subprocess is never invoked."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            result = send_notification(123, "valid message")  # type: ignore[arg-type]

        assert result is False
        mock_run.assert_not_called()

    def test_non_string_message_returns_false(self) -> None:
        """None message returns False; subprocess is never invoked."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            result = send_notification("valid title", None)  # type: ignore[arg-type]

        assert result is False
        mock_run.assert_not_called()

    def test_both_non_string_returns_false(self) -> None:
        """Both title and message non-string returns False; subprocess never invoked."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            result = send_notification(None, 42)  # type: ignore[arg-type]

        assert result is False
        mock_run.assert_not_called()

    def test_list_title_returns_false(self) -> None:
        """List title returns False; subprocess is never invoked."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            result = send_notification(["injected"], "msg")  # type: ignore[arg-type]

        assert result is False
        mock_run.assert_not_called()


class TestSendNotificationUrgencyFallback:
    """Cover urgency validation: invalid urgency falls back to 'normal'."""

    @pytest.fixture
    def mock_run(self) -> Iterator[MagicMock]:
        with patch("lib.notifications.subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess(args=["notify-send"], returncode=0)
            yield m

    def test_extreme_urgency_falls_back_to_normal(self, mock_run) -> None:
        """Invalid urgency 'extreme' is replaced with 'normal'."""
        with patch("lib.notifications.notify_send_available", return_value=True):
            result = send_notification("Title", "Message", urgency="extreme")

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[2] == "normal"

    def test_empty_urgency_falls_back_to_normal(self, mock_run) -> None:
        """Empty urgency string is replaced with 'normal'."""
        with patch("lib.notifications.notify_send_available", return_value=True):
            result = send_notification("Title", "Message", urgency="")

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[2] == "normal"


class TestSendNotificationTimeoutFallback:
    """Cover timeout validation: non-int or negative falls back to 5000."""

    @pytest.fixture
    def mock_run(self) -> Iterator[MagicMock]:
        with patch("lib.notifications.subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess(args=["notify-send"], returncode=0)
            yield m

    def test_string_timeout_falls_back(self, mock_run) -> None:
        """String timeout falls back to 5000."""
        with patch("lib.notifications.notify_send_available", return_value=True):
            result = send_notification("Title", "Message", timeout="5000")  # type: ignore[arg-type]

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[4] == "5000"

    def test_float_timeout_falls_back(self, mock_run) -> None:
        """Float timeout falls back to 5000 (float is not isinstance(int))."""
        with patch("lib.notifications.notify_send_available", return_value=True):
            result = send_notification("Title", "Message", timeout=5000.0)  # type: ignore[arg-type]

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[4] == "5000"

    def test_none_timeout_falls_back(self, mock_run) -> None:
        """None timeout falls back to 5000."""
        with patch("lib.notifications.notify_send_available", return_value=True):
            result = send_notification("Title", "Message", timeout=None)  # type: ignore[arg-type]

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[4] == "5000"

    def test_negative_int_timeout_falls_back(self, mock_run) -> None:
        """Negative int timeout falls back to 5000."""
        with patch("lib.notifications.notify_send_available", return_value=True):
            result = send_notification("Title", "Message", timeout=-100)

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[4] == "5000"


class TestSendNotificationEmptyTitleFallback:
    """Cover empty-title sanitization fallback to 'Notification'."""

    def test_empty_string_title_falls_back(self) -> None:
        """Empty string title is replaced with 'Notification' after sanitization."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=["notify-send"], returncode=0
            )
            result = send_notification("", "Message")

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[5] == "Notification"

    def test_whitespace_only_title_kept(self) -> None:
        """Whitespace-only title is not empty after sanitization (no trim in sanitizer)."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=["notify-send"], returncode=0
            )
            result = send_notification("   ", "Message")

        assert result is True
        args = mock_run.call_args[0][0]
        # The sanitizer does not strip whitespace, so the title is preserved
        assert args[5] == "   "


class TestSendNotificationExecutionPaths:
    """Cover subprocess.run return value and exception handling."""

    def test_nonzero_exit_code_returns_false(self) -> None:
        """notify-send returning non-zero exit code returns False."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=["notify-send"], returncode=1, stderr="error"
            )
            result = send_notification("Title", "Message")

        assert result is False

    def test_oserror_returns_false_and_logs(self, caplog) -> None:
        """OSError from subprocess.run returns False and logs the failure."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            mock_run.side_effect = OSError("notify-send crashed")

            with caplog.at_level(logging.ERROR, logger="lib.notifications"):
                result = send_notification("Title", "Message")

        assert result is False
        assert any(
            "Failed to send notification" in record.getMessage()
            for record in caplog.records
        )

    def test_happy_path_returns_true(self) -> None:
        """Successful notify-send invocation returns True."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=["notify-send"], returncode=0
            )
            result = send_notification("Title", "Message")

        assert result is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "notify-send"
        assert cmd[2] == "normal"
        assert cmd[4] == "5000"
        assert cmd[5] == "Title"
        assert cmd[6] == "Message"


class TestSendNotificationNotifySendUnavailable:
    """Cover early-return when notify_send_available returns False."""

    def test_notify_send_unavailable_returns_false_early(self) -> None:
        """When notify-send is unavailable, send_notification returns False and skips subprocess."""
        with (
            patch("lib.notifications.notify_send_available", return_value=False),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            result = send_notification("Title", "Message")

        assert result is False
        mock_run.assert_not_called()


class TestSendUpdateFailureNotificationPaths:
    """Cover send_update_failure_notification wrapper function."""

    def test_happy_path_delegates_with_critical(self) -> None:
        """Happy path delegates to send_notification with critical urgency and 10s timeout."""
        with patch("lib.notifications.send_notification", return_value=True) as mock_send:
            result = send_update_failure_notification("Connection timeout")

        assert result is True
        mock_send.assert_called_once_with(
            title="Flatpak Wrapper Update Failed",
            message="Failed to regenerate Flatpak wrappers:\nConnection timeout",
            urgency="critical",
            timeout=10000,
        )

    def test_notify_send_missing_returns_false(self) -> None:
        """When notify-send is missing, returns False without invoking subprocess."""
        with (
            patch("lib.notifications.notify_send_available", return_value=False),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            result = send_update_failure_notification("Some error")

        assert result is False
        mock_run.assert_not_called()

    def test_oserror_in_underlying_send_returns_false(self) -> None:
        """When the underlying send_notification encounters an OSError, returns False."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            mock_run.side_effect = OSError("binary missing")
            result = send_update_failure_notification("Some error")

        assert result is False


class TestMainEntryPoint:
    """Cover the ``if __name__ == "__main__":`` block (lines 139-161).

    Uses ``runpy.run_module`` with ``run_name="__main__"`` to trigger the
    block, following the in-process pattern from test_help_completeness.py.
    The global ``subprocess.run`` is patched so no real binary is invoked.
    """

    @staticmethod
    def _run_as_main(argv: list[str]) -> str:
        """Execute lib.notifications as __main__ with given argv; return captured stdout."""
        with patch("subprocess.run") as mock_global_run:
            def side_effect(cmd, **kwargs):
                if cmd[0] == "which":
                    return subprocess.CompletedProcess(args=cmd, returncode=0)
                if cmd[0] == "notify-send":
                    return subprocess.CompletedProcess(args=cmd, returncode=0)
                return subprocess.CompletedProcess(args=cmd, returncode=1)
            mock_global_run.side_effect = side_effect

            old_argv = sys.argv
            old_stdout = sys.stdout
            old_module = sys.modules.get("lib.notifications")
            sys.argv = argv
            sys.stdout = io.StringIO()
            # Remove cached module so runpy.run_module re-executes it cleanly
            # and the if __name__ == "__main__" block is entered.
            sys.modules.pop("lib.notifications", None)
            try:
                runpy.run_module("lib.notifications", run_name="__main__")
            finally:
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                sys.argv = old_argv
                # Restore original module so subsequent tests see the same
                # module object they imported at test-file load time. Without
                # this, the next test that does `patch("lib.notifications.X")`
                # re-imports a fresh module and the patch never applies to
                # already-imported function references in the test file.
                if old_module is not None:
                    sys.modules["lib.notifications"] = old_module
                else:
                    sys.modules.pop("lib.notifications", None)
            return output

    def test_test_subcommand_path(self) -> None:
        """The 'test' subcommand runs availability check and sends a notification."""
        output = self._run_as_main(["lib.notifications", "test"])

        assert "Testing notify-send availability..." in output
        assert "notify-send available: True" in output
        assert "Testing notification..." in output
        assert "Notification sent successfully: True" in output

    def test_test_failure_subcommand_path(self) -> None:
        """The 'test-failure' subcommand sends a failure notification."""
        output = self._run_as_main(["lib.notifications", "test-failure"])

        assert "Testing failure notification..." in output
        assert "Failure notification sent successfully: True" in output

    def test_no_args_does_nothing(self) -> None:
        """Running with no extra args produces no output (len(sys.argv) == 1)."""
        output = self._run_as_main(["lib.notifications"])

        assert output == ""

    def test_test_subcommand_with_notify_send_missing(self) -> None:
        """The 'test' subcommand reports notify-send unavailable."""
        with patch("subprocess.run") as mock_global_run:
            mock_global_run.return_value = subprocess.CompletedProcess(
                args=["which"], returncode=1
            )

            old_argv = sys.argv
            old_stdout = sys.stdout
            old_module = sys.modules.get("lib.notifications")
            sys.argv = ["lib.notifications", "test"]
            sys.stdout = io.StringIO()
            sys.modules.pop("lib.notifications", None)
            try:
                runpy.run_module("lib.notifications", run_name="__main__")
            finally:
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                sys.argv = old_argv
                # Restore original module (see _run_as_main for rationale).
                if old_module is not None:
                    sys.modules["lib.notifications"] = old_module
                else:
                    sys.modules.pop("lib.notifications", None)
        assert "Testing notify-send availability..." in output
        assert "notify-send available: False" in output
        # No notification was attempted, so this line should not appear
        assert "Testing notification..." not in output


class TestSanitizeNotificationTextTruncation:
    """Cover line 43: long-text truncation branch in _sanitize_notification_text."""

    def test_text_over_500_chars_is_truncated(self) -> None:
        """Text longer than 500 chars is truncated and ends with '...'."""
        long_text = "x" * 1000
        result = _sanitize_notification_text(long_text)
        assert len(result) == 500
        assert result.endswith("...")

    def test_text_exactly_500_chars_unchanged(self) -> None:
        """Text of exactly 500 chars is NOT truncated (not strictly greater)."""
        text = "y" * 500
        result = _sanitize_notification_text(text)
        assert result == text
        assert not result.endswith("...")

    def test_long_title_in_send_notification_triggers_truncation(self) -> None:
        """A long title passed to send_notification is truncated before sending."""
        with (
            patch("lib.notifications.notify_send_available", return_value=True),
            patch("lib.notifications.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=["notify-send"], returncode=0
            )
            long_title = "T" * 800
            result = send_notification(long_title, "msg")

        assert result is True
        sent_title = mock_run.call_args[0][0][5]
        assert len(sent_title) == 500
        assert sent_title.endswith("...")


class TestNotifySendAvailableException:
    """Cover lines 59-61: exception handler in notify_send_available."""

    def test_oserror_returns_false(self) -> None:
        """OSError from subprocess.run in notify_send_available returns False."""
        with patch("lib.notifications.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("which not found")
            result = notify_send_available()

        assert result is False

    def test_subprocess_error_returns_false(self) -> None:
        """CalledProcessError from subprocess.run in notify_send_available returns False."""
        with patch("lib.notifications.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.SubprocessError("failed")
            result = notify_send_available()

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
