#!/usr/bin/env python3
"""Notification functionality for fplaunchwrapper
Provides desktop notification support using notify-send (Linux standard),
with fallback if notify-send is not available or notifications are disabled.
"""

from __future__ import annotations

import re
import subprocess
import sys


def _sanitize_notification_text(text: str) -> str:
    """Sanitize text for use in notifications.

    Removes or escapes potentially problematic characters that could be
    interpreted by notify-send or the desktop notification system.

    Args:
        text: The text to sanitize

    Returns:
        Sanitized text safe for notifications
    """
    if not text:
        return ""

    # Remove null bytes which could truncate the message
    text = text.replace("\x00", "")

    # Remove backticks which could be interpreted as command substitution
    text = text.replace("`", "")

    # Remove dollar signs followed by parentheses or braces (command substitution)
    text = re.sub(r"\$\(", "(cmd)", text)
    text = re.sub(r"\$\{", "{", text)

    # Limit length to prevent buffer overflow attacks
    max_length = 500
    if len(text) > max_length:
        text = text[: max_length - 3] + "..."

    return text


def notify_send_available() -> bool:
    """Check if notify-send command is available on the system."""
    try:
        result = subprocess.run(
            ["which", "notify-send"], check=False, capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def send_notification(
    title: str,
    message: str,
    urgency: str = "normal",
    timeout: int = 5000,  # milliseconds
) -> bool:
    """Send a desktop notification using notify-send.

    Args:
        title: Notification title
        message: Notification body text
        urgency: Urgency level (low, normal, critical)
        timeout: Notification duration in milliseconds

    Returns:
        True if notification was sent successfully, False otherwise
    """
    if not notify_send_available():
        return False

    # Validate and sanitize inputs
    if not isinstance(title, str) or not isinstance(message, str):
        return False

    # Validate urgency level
    if urgency not in ("low", "normal", "critical"):
        urgency = "normal"

    # Validate timeout (must be positive integer)
    if not isinstance(timeout, int) or timeout < 0:
        timeout = 5000

    # Sanitize title and message
    safe_title = _sanitize_notification_text(title)
    safe_message = _sanitize_notification_text(message)

    if not safe_title:
        safe_title = "Notification"

    try:
        cmd = [
            "notify-send",
            "-u",
            urgency,
            "-t",
            str(timeout),
            safe_title,
            safe_message,
        ]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to send notification: {e}", file=sys.stderr)
        return False


def send_update_failure_notification(error_message: str) -> bool:
    """Send a notification specifically for update/wrapper regeneration failures.

    Args:
        error_message: The error message to include in the notification

    Returns:
        True if notification was sent successfully, False otherwise
    """
    return send_notification(
        title="Flatpak Wrapper Update Failed",
        message=f"Failed to regenerate Flatpak wrappers:\n{error_message}",
        urgency="critical",
        timeout=10000,  # Show for 10 seconds
    )


if __name__ == "__main__":
    # Test notification functionality
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            print("Testing notify-send availability...")
            available = notify_send_available()
            print(f"notify-send available: {available}")

            if available:
                print("Testing notification...")
                success = send_notification(
                    "fplaunchwrapper Test",
                    "This is a test notification",
                    urgency="normal",
                    timeout=3000,
                )
                print(f"Notification sent successfully: {success}")
        elif sys.argv[1] == "test-failure":
            print("Testing failure notification...")
            success = send_update_failure_notification(
                "Connection timeout when checking for updates"
            )
            print(f"Failure notification sent successfully: {success}")
