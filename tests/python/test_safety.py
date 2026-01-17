#!/usr/bin/env python3
"""Unit tests for safety.py
Tests safety mechanisms to prevent accidental Firefox launches during tests.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch


# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fplaunch.safety import is_test_environment, is_dangerous_wrapper, safe_launch_check


class TestSafety:
    """Test safety mechanisms."""

    def test_is_test_environment_with_test_arg(self) -> None:
        """Test is_test_environment with test argument."""
        with patch.object(sys, "argv", ["script", "test"]):
            assert is_test_environment() is True

    def test_is_test_environment_with_env_var(self) -> None:
        """Test is_test_environment with environment variable."""
        with patch.dict(os.environ, {"FPWRAPPER_TEST_ENV": "true"}):
            assert is_test_environment() is True

    def test_is_test_environment_with_pytest_module(self) -> None:
        """Test is_test_environment with pytest module."""
        with patch.dict(sys.modules, {"pytest": None}):
            assert is_test_environment() is True

    def test_is_test_environment_with_unittest_module(self) -> None:
        """Test is_test_environment with unittest module."""
        with patch.dict(sys.modules, {"unittest": None}):
            assert is_test_environment() is True

    def test_is_test_environment_false(self) -> None:
        """Test is_test_environment returns False when not in test environment."""
        with patch.object(sys, "argv", ["script"]):
            with patch.dict(os.environ, {"FPWRAPPER_TEST_ENV": "false"}):
                # Temporarily remove unittest modules to simulate non-test environment
                unittest_modules = [mod for mod in sys.modules if mod.startswith('unittest')]
                for mod in unittest_modules:
                    del sys.modules[mod]
                
                # Also remove pytest modules
                pytest_modules = [mod for mod in sys.modules if mod.startswith('pytest') or 'pytest' in mod]
                for mod in pytest_modules:
                    del sys.modules[mod]
                
                try:
                    assert is_test_environment() is False
                finally:
                    # Restore unittest modules
                    pass

    def test_is_dangerous_wrapper_with_dangerous_content(self, tmp_path: Path) -> None:
        """Test is_dangerous_wrapper with dangerous content."""
        wrapper_path = tmp_path / "dangerous_wrapper"
        wrapper_path.write_text("flatpak run org.mozilla.firefox")
        assert is_dangerous_wrapper(wrapper_path) is True

    def test_is_dangerous_wrapper_with_safe_content(self, tmp_path: Path) -> None:
        """Test is_dangerous_wrapper with safe content."""
        wrapper_path = tmp_path / "safe_wrapper"
        wrapper_path.write_text("#!/bin/bash\necho 'Hello, World!'")
        assert is_dangerous_wrapper(wrapper_path) is False

    def test_is_dangerous_wrapper_with_nonexistent_file(self, tmp_path: Path) -> None:
        """Test is_dangerous_wrapper with nonexistent file."""
        wrapper_path = tmp_path / "nonexistent_wrapper"
        assert is_dangerous_wrapper(wrapper_path) is False

    def test_safe_launch_check_in_test_environment_with_browser(self) -> None:
        """Test safe_launch_check in test environment with browser app."""
        with patch.object(sys, "argv", ["script", "test"]):
            assert safe_launch_check("firefox") is False

    def test_safe_launch_check_in_test_environment_with_safe_app(self) -> None:
        """Test safe_launch_check in test environment with safe app."""
        with patch.object(sys, "argv", ["script", "test"]):
            assert safe_launch_check("gedit") is True

    def test_safe_launch_check_with_dangerous_wrapper(self, tmp_path: Path) -> None:
        """Test safe_launch_check with dangerous wrapper."""
        wrapper_path = tmp_path / "dangerous_wrapper"
        wrapper_path.write_text("flatpak run org.mozilla.firefox")
        with patch.object(sys, "argv", ["script", "test"]):
            assert safe_launch_check("firefox", wrapper_path) is False

    def test_safe_launch_check_with_safe_wrapper(self, tmp_path: Path) -> None:
        """Test safe_launch_check with safe wrapper."""
        wrapper_path = tmp_path / "safe_wrapper"
        wrapper_path.write_text("#!/bin/bash\necho 'Hello, World!'")
        with patch.object(sys, "argv", ["script", "test"]):
            assert safe_launch_check("gedit", wrapper_path) is True

    def test_safe_launch_check_not_in_test_environment(self) -> None:
        """Test safe_launch_check not in test environment."""
        with patch.object(sys, "argv", ["script"]):
            with patch.dict(os.environ, {"FPWRAPPER_TEST_ENV": "false"}):
                assert safe_launch_check("firefox") is True
