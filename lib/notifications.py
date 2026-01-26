#!/usr/bin/env python3
"""Notification functionality for fplaunchwrapper
Provides desktop notification support using notify-send (Linux standard),
with fallback if notify-send is not available or notifications are disabled.
"""
from __future__ import annotations

import subprocess
import sys
from typing import Any


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
    title: str, message: str, urgency: str = "normal", timeout: int = 5000  # milliseconds
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

    try:
        cmd = ["notify-send", "-u", urgency, "-t", str(timeout), title, message]
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
