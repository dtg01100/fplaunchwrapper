#!/usr/bin/env python3
"""Tests for lib/exceptions.py exception classes.

This module provides comprehensive test coverage for the custom exception
classes defined in lib/exceptions.py.
"""

import pytest

from lib.exceptions import (
    AppNotFoundError,
    ForbiddenNameError,
    FplaunchError,
    InvalidFlatpakIdError,
    LaunchBlockedError,
    PathTraversalError,
    WrapperExistsError,
    WrapperGenerationError,
    WrapperNotFoundError,
)


class TestFplaunchError:
    """Tests for the base FplaunchError exception."""

    def test_constructor_with_details(self):
        """Test constructor with message and details."""
        error = FplaunchError("Test error", {"key": "value"})
        
        assert error.message == "Test error"
        assert error.details == {"key": "value"}

    def test_constructor_without_details(self):
        """Test constructor without details defaults to empty dict."""
        error = FplaunchError("Test error")
        
        assert error.message == "Test error"
        assert error.details == {}

    def test_string_representation_with_details(self):
        """Test string representation includes details when present."""
        error = FplaunchError("Test error", {"key": "value"})
        
        error_str = str(error)
        assert "Test error" in error_str
        assert "key" in error_str
        assert "value" in error_str

    def test_string_representation_without_details(self):
        """Test string representation without details."""
        error = FplaunchError("Test error")
        
        error_str = str(error)
        assert error_str == "Test error"


class TestWrapperExistsError:
    """Tests for WrapperExistsError exception."""

    def test_constructor_with_wrapper_path(self):
        """Test constructor with wrapper_path parameter."""
        error = WrapperExistsError(wrapper_name="test-wrapper", wrapper_path="/path/to/wrapper")
        
        assert error.wrapper_name == "test-wrapper"
        assert error.wrapper_path == "/path/to/wrapper"
        assert error.details["wrapper_name"] == "test-wrapper"
        assert error.details["wrapper_path"] == "/path/to/wrapper"

    def test_constructor_without_wrapper_path(self):
        """Test constructor without wrapper_path parameter."""
        error = WrapperExistsError(wrapper_name="test-wrapper")
        
        assert error.wrapper_name == "test-wrapper"
        assert error.wrapper_path is None
        assert error.details["wrapper_name"] == "test-wrapper"
        assert "wrapper_path" not in error.details

    def test_string_representation_contains_path(self):
        """Test string representation contains the wrapper path."""
        error = WrapperExistsError(wrapper_name="my-wrapper", wrapper_path="/usr/local/bin/my-wrapper")
        
        error_str = str(error)
        assert "my-wrapper" in error_str
        assert "/usr/local/bin/my-wrapper" in error_str

    def test_string_representation_without_path(self):
        """Test string representation without wrapper path."""
        error = WrapperExistsError(wrapper_name="my-wrapper")
        
        error_str = str(error)
        assert "my-wrapper" in error_str
        assert "Wrapper already exists" in error_str


class TestWrapperNotFoundError:
    """Tests for WrapperNotFoundError exception."""

    def test_constructor_with_searched_paths(self):
        """Test constructor with searched_paths parameter."""
        searched = ["/path/one", "/path/two", "/path/three"]
        error = WrapperNotFoundError(wrapper_name="missing-wrapper", searched_paths=searched)
        
        assert error.wrapper_name == "missing-wrapper"
        assert error.searched_paths == searched
        assert error.details["wrapper_name"] == "missing-wrapper"
        assert error.details["searched_paths"] == searched

    def test_constructor_without_searched_paths(self):
        """Test constructor without searched_paths parameter."""
        error = WrapperNotFoundError(wrapper_name="missing-wrapper")
        
        assert error.wrapper_name == "missing-wrapper"
        assert error.searched_paths is None
        assert error.details["wrapper_name"] == "missing-wrapper"
        assert "searched_paths" not in error.details

    def test_string_representation_contains_paths(self):
        """Test string representation contains the searched paths."""
        searched = ["/usr/bin", "/usr/local/bin"]
        error = WrapperNotFoundError(wrapper_name="my-wrapper", searched_paths=searched)
        
        error_str = str(error)
        assert "my-wrapper" in error_str
        assert "/usr/bin" in error_str
        assert "/usr/local/bin" in error_str

    def test_string_representation_without_paths(self):
        """Test string representation without searched paths."""
        error = WrapperNotFoundError(wrapper_name="my-wrapper")
        
        error_str = str(error)
        assert "my-wrapper" in error_str
        assert "Wrapper not found" in error_str


class TestWrapperGenerationError:
    """Tests for WrapperGenerationError exception."""

    def test_constructor_with_details(self):
        """Test constructor with app_id, reason, and details parameters."""
        extra_details = {"template_error": "missing variable", "line": 42}
        error = WrapperGenerationError(
            app_id="com.example.App",
            reason="Template rendering failed",
            details=extra_details
        )
        
        assert error.app_id == "com.example.App"
        assert error.reason == "Template rendering failed"
        assert error.details["app_id"] == "com.example.App"
        assert error.details["reason"] == "Template rendering failed"
        assert error.details["template_error"] == "missing variable"
        assert error.details["line"] == 42

    def test_constructor_without_extra_details(self):
        """Test constructor without extra details parameter."""
        error = WrapperGenerationError(
            app_id="com.example.App",
            reason="Permission denied"
        )
        
        assert error.app_id == "com.example.App"
        assert error.reason == "Permission denied"
        assert error.details["app_id"] == "com.example.App"
        assert error.details["reason"] == "Permission denied"

    def test_string_representation(self):
        """Test string representation contains app_id and reason."""
        error = WrapperGenerationError(
            app_id="com.example.App",
            reason="Template error"
        )
        
        error_str = str(error)
        assert "com.example.App" in error_str
        assert "Template error" in error_str
        assert "Failed to generate wrapper" in error_str


class TestAppNotFoundError:
    """Tests for AppNotFoundError exception."""

    def test_constructor_with_app_name(self):
        """Test constructor with app_name parameter."""
        error = AppNotFoundError(app_name="nonexistent-app")
        
        assert error.app_name == "nonexistent-app"
        assert error.details["app_name"] == "nonexistent-app"

    def test_string_representation(self):
        """Test string representation contains app name."""
        error = AppNotFoundError(app_name="my-app")
        
        error_str = str(error)
        assert "my-app" in error_str
        assert "Application not found" in error_str


class TestLaunchBlockedError:
    """Tests for LaunchBlockedError exception."""

    def test_constructor_with_details(self):
        """Test constructor with app_name, reason, and details parameters."""
        extra_details = {"blocked_by": "safety_check", "severity": "high"}
        error = LaunchBlockedError(
            app_name="dangerous-app",
            reason="Security policy violation",
            details=extra_details
        )
        
        assert error.app_name == "dangerous-app"
        assert error.reason == "Security policy violation"
        assert error.details["app_name"] == "dangerous-app"
        assert error.details["reason"] == "Security policy violation"
        assert error.details["blocked_by"] == "safety_check"
        assert error.details["severity"] == "high"

    def test_constructor_without_extra_details(self):
        """Test constructor without extra details parameter."""
        error = LaunchBlockedError(
            app_name="blocked-app",
            reason="Forbidden name"
        )
        
        assert error.app_name == "blocked-app"
        assert error.reason == "Forbidden name"
        assert error.details["app_name"] == "blocked-app"
        assert error.details["reason"] == "Forbidden name"

    def test_string_representation_contains_details(self):
        """Test string representation contains reason and details."""
        error = LaunchBlockedError(
            app_name="my-app",
            reason="Policy violation",
            details={"policy": "strict"}
        )
        
        error_str = str(error)
        assert "my-app" in error_str
        assert "Policy violation" in error_str
        assert "Launch blocked" in error_str


class TestForbiddenNameError:
    """Tests for ForbiddenNameError exception."""

    def test_constructor_is_builtin_true(self):
        """Test constructor with is_builtin=True (default)."""
        error = ForbiddenNameError(name="bash", is_builtin=True)
        
        assert error.name == "bash"
        assert error.is_builtin is True
        assert error.details["name"] == "bash"
        assert error.details["is_builtin"] is True
        assert "system command" in str(error)

    def test_constructor_is_builtin_false(self):
        """Test constructor with is_builtin=False (user blocklist)."""
        error = ForbiddenNameError(name="custom-blocked", is_builtin=False)
        
        assert error.name == "custom-blocked"
        assert error.is_builtin is False
        assert error.details["name"] == "custom-blocked"
        assert error.details["is_builtin"] is False
        assert "user blocklist" in str(error)

    def test_is_forbidden_classmethod_with_forbidden_name(self):
        """Test is_forbidden() classmethod returns True for forbidden names."""
        assert ForbiddenNameError.is_forbidden("bash") is True
        assert ForbiddenNameError.is_forbidden("BASH") is True  # Case insensitive
        assert ForbiddenNameError.is_forbidden("python") is True
        assert ForbiddenNameError.is_forbidden("PYTHON3") is True
        assert ForbiddenNameError.is_forbidden("sudo") is True
        assert ForbiddenNameError.is_forbidden("rm") is True

    def test_is_forbidden_classmethod_with_allowed_name(self):
        """Test is_forbidden() classmethod returns False for allowed names."""
        assert ForbiddenNameError.is_forbidden("my-safe-app") is False
        assert ForbiddenNameError.is_forbidden("com.example.App") is False
        assert ForbiddenNameError.is_forbidden("firefox") is False
        assert ForbiddenNameError.is_forbidden("code") is False

    def test_is_forbidden_is_case_insensitive(self):
        """Test that is_forbidden() is case insensitive."""
        assert ForbiddenNameError.is_forbidden("BASH") is True
        assert ForbiddenNameError.is_forbidden("Bash") is True
        assert ForbiddenNameError.is_forbidden("BaSh") is True
        assert ForbiddenNameError.is_forbidden("SUDO") is True
        assert ForbiddenNameError.is_forbidden("SuDo") is True

    def test_forbidden_names_set_is_frozen(self):
        """Test that FORBIDDEN_NAMES is a frozenset (immutable)."""
        assert isinstance(ForbiddenNameError.FORBIDDEN_NAMES, frozenset)

    def test_forbidden_names_contains_common_commands(self):
        """Test that FORBIDDEN_NAMES contains common dangerous commands."""
        forbidden = ForbiddenNameError.FORBIDDEN_NAMES
        # Shells
        assert "bash" in forbidden
        assert "zsh" in forbidden
        assert "sh" in forbidden
        # Package managers
        assert "pip" in forbidden
        assert "npm" in forbidden
        # System commands
        assert "sudo" in forbidden
        assert "rm" in forbidden
        # Development tools
        assert "git" in forbidden
        assert "python" in forbidden
        assert "docker" in forbidden


class TestPathTraversalError:
    """Tests for PathTraversalError exception."""

    def test_constructor_with_base_dir(self):
        """Test constructor with attempted_path and base_dir parameters."""
        error = PathTraversalError(path="../../../etc/passwd", base_dir="/home/user/wrappers")
        
        assert error.path == "../../../etc/passwd"
        assert error.base_dir == "/home/user/wrappers"
        assert error.details["path"] == "../../../etc/passwd"
        assert error.details["base_dir"] == "/home/user/wrappers"

    def test_constructor_without_base_dir(self):
        """Test constructor without base_dir parameter."""
        error = PathTraversalError(path="../../../etc/passwd")
        
        assert error.path == "../../../etc/passwd"
        assert error.base_dir is None
        assert error.details["path"] == "../../../etc/passwd"
        assert "base_dir" not in error.details

    def test_string_representation_with_base_dir(self):
        """Test string representation contains base directory."""
        error = PathTraversalError(path="../secret", base_dir="/safe/dir")
        
        error_str = str(error)
        assert "../secret" in error_str
        assert "/safe/dir" in error_str
        assert "Path traversal" in error_str
        assert "escapes base directory" in error_str

    def test_string_representation_without_base_dir(self):
        """Test string representation without base directory."""
        error = PathTraversalError(path="../../../etc/passwd")
        
        error_str = str(error)
        assert "../../../etc/passwd" in error_str
        assert "Path traversal detected" in error_str
        assert "escapes base directory" not in error_str


class TestInvalidFlatpakIdError:
    """Tests for InvalidFlatpakIdError exception."""

    def test_constructor_with_reason(self):
        """Test constructor with app_id and reason parameters."""
        error = InvalidFlatpakIdError(app_id="invalid..id", reason="Contains consecutive dots")
        
        assert error.app_id == "invalid..id"
        assert error.reason == "Contains consecutive dots"
        assert error.details["app_id"] == "invalid..id"
        assert error.details["reason"] == "Contains consecutive dots"

    def test_constructor_without_reason(self):
        """Test constructor without reason parameter."""
        error = InvalidFlatpakIdError(app_id="bad-id")
        
        assert error.app_id == "bad-id"
        assert error.reason is None
        assert error.details["app_id"] == "bad-id"
        assert error.details["reason"] is None

    def test_string_representation_contains_reason(self):
        """Test string representation contains the reason."""
        error = InvalidFlatpakIdError(
            app_id="invalid..flatpak",
            reason="Contains consecutive dots"
        )
        
        error_str = str(error)
        assert "invalid..flatpak" in error_str
        assert "Contains consecutive dots" in error_str
        assert "Invalid Flatpak ID" in error_str

    def test_string_representation_without_reason(self):
        """Test string representation without reason."""
        error = InvalidFlatpakIdError(app_id="bad-id")
        
        error_str = str(error)
        assert "bad-id" in error_str
        assert "Invalid Flatpak ID" in error_str
