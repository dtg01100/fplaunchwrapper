#!/usr/bin/env python3
"""Safety mechanisms to prevent accidental Firefox launches during tests."""

import os
import sys
from pathlib import Path


def is_test_environment() -> bool:
    """Check if we're running in a test environment."""
    # Check command line arguments
    if any("test" in arg.lower() for arg in sys.argv):
        return True
    
    # Check environment variables
    if os.environ.get("FPWRAPPER_TEST_ENV", "").lower() == "true":
        return True
    
    # Check if we're being imported by pytest or unittest
    if "pytest" in sys.modules:
        return True
    if "unittest" in sys.modules:
        return True
    
    # Check for pytest-specific environment variables
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    
    # Check for other pytest environment variables
    if any(key.startswith("PYTEST_") for key in os.environ):
        return True
    
    return False


def is_dangerous_wrapper(wrapper_path: Path) -> bool:
    """Check if a wrapper script contains dangerous commands."""
    try:
        if wrapper_path.exists():
            content = wrapper_path.read_text()
            dangerous_patterns = [
                "flatpak run org.mozilla.firefox",
                "flatpak run com.google.Chrome",
                "firefox ",  # Direct firefox command
                "google-chrome",
                "chromium",
            ]
            return any(pattern in content for pattern in dangerous_patterns)
    except (IOError, OSError, UnicodeDecodeError) as e:
        # Handle file reading exceptions
        pass
    return False


def safe_launch_check(app_name: str, wrapper_path=None) -> bool:
    """Perform safety checks before launching an application."""
    if is_test_environment():
        # In test environment, be extra cautious with browser launches
        if app_name and any(browser in app_name.lower() for browser in ["firefox", "chrome", "chromium"]):
            print(f"🛡️  Safety: Blocked {app_name} launch in test environment", file=sys.stderr)
            return False
        
        # Check wrapper content if provided
        if wrapper_path and is_dangerous_wrapper(wrapper_path):
            print(f"🛡️  Safety: Blocked dangerous wrapper {wrapper_path}", file=sys.stderr)
            return False
    
    return True