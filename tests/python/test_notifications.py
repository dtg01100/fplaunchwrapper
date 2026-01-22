#!/usr/bin/env python3
"""Comprehensive test suite for fplaunchwrapper notifications module
Tests all notification functionality with proper mocking and fixtures.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

try:
    from lib.notifications import (
        notify_send_available,
        send_notification,
        send_update_failure_notification,
    )
except ImportError:
    # Fallback for when modules aren't available
    notify_send_available = send_notification = send_update_failure_notification = None


class TestNotifySendAvailable:
    """Test notify_send_available function."""

    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run for testing."""
        with patch("fplaunch.notifications.subprocess.run") as mock:
            yield mock

    def test_notify_send_available_true(self, mock_subprocess_run):
        """Test that notify_send_available returns True when notify-send is found."""
        if not notify_send_available:
            pytest.skip("notifications module not available")

        # Mock successful which command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        result = notify_send_available()
        assert result is True

        # Verify which command was called
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "which"
        assert args[1] == "notify-send"

    def test_notify_send_available_false(self, mock_subprocess_run):
        """Test that notify_send_available returns False when notify-send is not found."""
        if not notify_send_available:
            pytest.skip("notifications module not available")

        # Mock failed which command
        mock_result = Mock()
        mock_result.returncode = 1  # Command not found
        mock_subprocess_run.return_value = mock_result

        result = notify_send_available()
        assert result is False

    def test_notify_send_available_exception(self, mock_subprocess_run):
        """Test that notify_send_available returns False on exception."""
        if not notify_send_available:
            pytest.skip("notifications module not available")

        # Mock exception
        mock_subprocess_run.side_effect = Exception("Command failed")

        result = notify_send_available()
        assert result is False


class TestSendNotification:
    """Test send_notification function."""

    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run for testing."""
        with patch("fplaunch.notifications.subprocess.run") as mock:
            yield mock

    @pytest.fixture
    def mock_notify_available(self):
        """Mock notify_send_available to return True."""
        with patch("fplaunch.notifications.notify_send_available", return_value=True):
            yield

    def test_send_notification_basic(self, mock_subprocess_run, mock_notify_available):
        """Test basic notification sending."""
        if not send_notification:
            pytest.skip("notifications module not available")

        # Mock successful notify-send
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        result = send_notification("Test Title", "Test Message")
        assert result is True

        # Verify notify-send was called with correct arguments
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "notify-send"
        assert args[2] == "normal"  # Default urgency
        assert args[4] == "5000"  # Default timeout
        assert args[5] == "Test Title"
        assert args[6] == "Test Message"

    def test_send_notification_with_urgency(
        self, mock_subprocess_run, mock_notify_available
    ):
        """Test notification with custom urgency."""
        if not send_notification:
            pytest.skip("notifications module not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        # Test low urgency
        result = send_notification("Title", "Message", urgency="low")
        assert result is True
        args = mock_subprocess_run.call_args[0][0]
        assert args[2] == "low"

        # Test normal urgency
        result = send_notification("Title", "Message", urgency="normal")
        assert result is True
        args = mock_subprocess_run.call_args[0][0]
        assert args[2] == "normal"

        # Test critical urgency
        result = send_notification("Title", "Message", urgency="critical")
        assert result is True
        args = mock_subprocess_run.call_args[0][0]
        assert args[2] == "critical"

    def test_send_notification_with_timeout(
        self, mock_subprocess_run, mock_notify_available
    ):
        """Test notification with custom timeout."""
        if not send_notification:
            pytest.skip("notifications module not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        result = send_notification("Title", "Message", timeout=10000)
        assert result is True
        args = mock_subprocess_run.call_args[0][0]
        assert args[4] == "10000"

    def test_send_notification_unavailable(self, mock_subprocess_run):
        """Test notification when notify-send is not available."""
        if not send_notification:
            pytest.skip("notifications module not available")

        # Mock notify_send_available returning False
        with patch("fplaunch.notifications.notify_send_available", return_value=False):
            result = send_notification("Title", "Message")
            assert result is False

            # Verify subprocess.run was not called
            mock_subprocess_run.assert_not_called()

    def test_send_notification_failure(
        self, mock_subprocess_run, mock_notify_available
    ):
        """Test notification when notify-send command fails."""
        if not send_notification:
            pytest.skip("notifications module not available")

        # Mock failed notify-send
        mock_result = Mock()
        mock_result.returncode = 1
        mock_subprocess_run.return_value = mock_result

        result = send_notification("Title", "Message")
        assert result is False

    def test_send_notification_exception(
        self, mock_subprocess_run, mock_notify_available
    ):
        """Test notification when an exception occurs."""
        if not send_notification:
            pytest.skip("notifications module not available")

        # Mock exception
        mock_subprocess_run.side_effect = Exception("notify-send crashed")

        result = send_notification("Title", "Message")
        assert result is False


class TestSendUpdateFailureNotification:
    """Test send_update_failure_notification function."""

    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run for testing."""
        with patch("fplaunch.notifications.subprocess.run") as mock:
            yield mock

    @pytest.fixture
    def mock_notify_available(self):
        """Mock notify_send_available to return True."""
        with patch("fplaunch.notifications.notify_send_available", return_value=True):
            yield

    def test_send_update_failure_notification_basic(
        self, mock_subprocess_run, mock_notify_available
    ):
        """Test basic update failure notification."""
        if not send_update_failure_notification:
            pytest.skip("notifications module not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        error_msg = "Connection timeout when checking for updates"
        result = send_update_failure_notification(error_msg)
        assert result is True

        # Verify correct arguments
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "notify-send"
        assert args[2] == "critical"  # Critical urgency for failures
        assert args[4] == "10000"  # 10 second timeout for failures
        assert args[5] == "Flatpak Wrapper Update Failed"
        assert "Failed to regenerate Flatpak wrappers:" in args[6]
        assert error_msg in args[6]

    def test_send_update_failure_notification_unavailable(self, mock_subprocess_run):
        """Test update failure notification when notify-send is unavailable."""
        if not send_update_failure_notification:
            pytest.skip("notifications module not available")

        with patch("fplaunch.notifications.notify_send_available", return_value=False):
            result = send_update_failure_notification("Error message")
            assert result is False

            mock_subprocess_run.assert_not_called()

    def test_send_update_failure_notification_long_message(
        self, mock_subprocess_run, mock_notify_available
    ):
        """Test update failure notification with long error message."""
        if not send_update_failure_notification:
            pytest.skip("notifications module not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        long_error = "This is a very long error message " * 10
        result = send_update_failure_notification(long_error)
        assert result is True

        args = mock_subprocess_run.call_args[0][0]
        assert long_error in args[6]


class TestNotificationSecurity:
    """Security-focused tests for notifications."""

    def test_notification_command_injection(self):
        """Test that notification parameters are properly escaped."""
        if not send_notification:
            pytest.skip("notifications module not available")

        with patch("fplaunch.notifications.subprocess.run") as mock_run, patch(
            "lib.notifications.notify_send_available", return_value=True
        ):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Test with potential injection attempts
            malicious_inputs = [
                '"; rm -rf / #',
                "$(rm -rf /)",
                "`whoami`",
                "${HOME}",
            ]

            for malicious_input in malicious_inputs:
                send_notification("Title", malicious_input)

                # Verify the command was called with the list (not shell string)
                # This ensures injection is prevented
                call_args = mock_run.call_args[0][0]
                assert isinstance(call_args, list)
                assert call_args[6] == malicious_input

    def test_notification_unicode(self):
        """Test notification with unicode characters."""
        if not send_notification:
            pytest.skip("notifications module not available")

        with patch("fplaunch.notifications.subprocess.run") as mock_run, patch(
            "lib.notifications.notify_send_available", return_value=True
        ):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            unicode_title = "🚀 Notification"
            unicode_message = "Unicode: áéíóú, 你好, Привет, مرحبا"

            result = send_notification(unicode_title, unicode_message)
            assert result is True

            args = mock_run.call_args[0][0]
            assert args[5] == unicode_title
            assert args[6] == unicode_message

    def test_notification_empty_strings(self):
        """Test notification with empty strings."""
        if not send_notification:
            pytest.skip("notifications module not available")

        with patch("fplaunch.notifications.subprocess.run") as mock_run, patch(
            "lib.notifications.notify_send_available", return_value=True
        ):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = send_notification("", "")
            assert result is True

            args = mock_run.call_args[0][0]
            assert args[5] == ""
            assert args[6] == ""


class TestNotificationEdgeCases:
    """Edge case tests for notifications."""

    def test_notification_invalid_urgency(self):
        """Test notification with invalid urgency level."""
        if not send_notification:
            pytest.skip("notifications module not available")

        with patch("fplaunch.notifications.subprocess.run") as mock_run, patch(
            "lib.notifications.notify_send_available", return_value=True
        ):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Pass an invalid urgency - function should still work
            # (notify-send will handle invalid values)
            result = send_notification("Title", "Message", urgency="invalid")
            assert result is True

            args = mock_run.call_args[0][0]
            assert args[2] == "invalid"

    def test_notification_zero_timeout(self):
        """Test notification with zero timeout."""
        if not send_notification:
            pytest.skip("notifications module not available")

        with patch("fplaunch.notifications.subprocess.run") as mock_run, patch(
            "lib.notifications.notify_send_available", return_value=True
        ):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = send_notification("Title", "Message", timeout=0)
            assert result is True

            args = mock_run.call_args[0][0]
            assert args[4] == "0"

    def test_notification_negative_timeout(self):
        """Test notification with negative timeout."""
        if not send_notification:
            pytest.skip("notifications module not available")

        with patch("fplaunch.notifications.subprocess.run") as mock_run, patch(
            "lib.notifications.notify_send_available", return_value=True
        ):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = send_notification("Title", "Message", timeout=-5000)
            assert result is True

            args = mock_run.call_args[0][0]
            assert args[4] == "-5000"

    def test_notification_very_long_message(self):
        """Test notification with very long message."""
        if not send_notification:
            pytest.skip("notifications module not available")

        with patch("fplaunch.notifications.subprocess.run") as mock_run, patch(
            "lib.notifications.notify_send_available", return_value=True
        ):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            long_message = "x" * 10000  # 10KB message
            result = send_notification("Title", long_message)
            assert result is True

            args = mock_run.call_args[0][0]
            assert args[6] == long_message


class TestNotificationIntegration:
    """Integration tests for notifications."""

    def test_notification_chain_available_and_send(self):
        """Test the complete chain: check availability and send notification."""
        if not (notify_send_available and send_notification):
            pytest.skip("notifications module not available")

        with patch("fplaunch.notifications.subprocess.run") as mock_run:
            # Mock which command (availability check)
            which_result = Mock()
            which_result.returncode = 0

            # Mock notify-send command
            notify_result = Mock()
            notify_result.returncode = 0

            # Set up the mock to return different results for different calls
            def side_effect(*args, **kwargs):
                if args[0][0] == "which":
                    return which_result
                elif args[0][0] == "notify-send":
                    return notify_result
                return Mock(returncode=1)

            mock_run.side_effect = side_effect

            # Test the full flow
            is_available = notify_send_available()
            assert is_available is True

            sent = send_notification("Test", "Message")
            assert sent is True

    def test_notification_chain_unavailable(self):
        """Test chain when notify-send is not available."""
        if not (notify_send_available and send_notification):
            pytest.skip("notifications module not available")

        with patch("fplaunch.notifications.subprocess.run") as mock_run:
            # Mock which command to return failure
            which_result = Mock()
            which_result.returncode = 1

            mock_run.return_value = which_result

            # Check availability
            is_available = notify_send_available()
            assert is_available is False

            # Send notification (should return False without calling notify-send)
            sent = send_notification("Test", "Message")
            assert sent is False


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])
