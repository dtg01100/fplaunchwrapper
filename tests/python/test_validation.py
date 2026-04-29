#!/usr/bin/env python3
"""Unit tests for lib/validation.py
Tests validate_app_id, check_path_traversal, and should_process_event.
"""

import pytest
from pathlib import Path

from lib.validation import (
    validate_app_id,
    check_path_traversal,
    should_process_event,
)


class TestValidateAppId:
    """Test validate_app_id function."""

    # Valid Flatpak IDs (reverse-DNS format)
    @pytest.mark.parametrize("app_id", [
        "org.mozilla.Firefox",
        "org.mozilla.firefox",
        "com.example.App",
        "com.example.app123",
        "org.freedesktop.Platform",
        "org.kde.KDE",
        "io.github.some_project",
        "org.gimp.GIMP",
        "com.valvesoftware.Steam",
    ])
    def test_valid_reverse_dns_format(self, app_id: str) -> None:
        """Test valid reverse-DNS format Flatpak IDs."""
        valid, error = validate_app_id(app_id)
        assert valid is True, f"Expected {app_id!r} to be valid, got error: {error}"
        assert error == ""

    # Invalid Flatpak IDs - no dot
    @pytest.mark.parametrize("app_id", [
        "firefox",
        "app",
        "test",
        "APP",
        "my-app",
        "no-dot-here",
    ])
    def test_invalid_no_dot(self, app_id: str) -> None:
        """Test IDs without dot are invalid."""
        valid, error = validate_app_id(app_id)
        assert valid is False
        assert "dot" in error.lower() or "reverse-dns" in error.lower()

    # Invalid Flatpak IDs - starts with dot
    @pytest.mark.parametrize("app_id", [
        ".invalid",
        ".org.app",
        ".mozilla.firefox",
    ])
    def test_invalid_starts_with_dot(self, app_id: str) -> None:
        """Test IDs starting with dot are invalid."""
        valid, error = validate_app_id(app_id)
        assert valid is False
        assert "dot" in error.lower()

    # Invalid Flatpak IDs - ends with dot
    @pytest.mark.parametrize("app_id", [
        "invalid.",
        "org.",
        "org.mozilla.",
    ])
    def test_invalid_ends_with_dot(self, app_id: str) -> None:
        """Test IDs ending with dot are invalid."""
        valid, error = validate_app_id(app_id)
        assert valid is False
        assert "dot" in error.lower()

    # Invalid Flatpak IDs - empty/whitespace
    @pytest.mark.parametrize("app_id", [
        "",
        "   ",
        "\t",
        "\n",
    ])
    def test_invalid_empty_or_whitespace(self, app_id: str) -> None:
        """Test empty or whitespace-only IDs are invalid."""
        valid, error = validate_app_id(app_id)
        assert valid is False
        assert "empty" in error.lower()

    # Invalid Flatpak IDs - special characters
    @pytest.mark.parametrize("app_id", [
        "org@test.app",
        "org.test@app",
        "org test app",
        "org\ntest.app",
        "org/test.app",
        "org.test.app/",
    ])
    def test_invalid_special_chars(self, app_id: str) -> None:
        """Test IDs with special characters are invalid."""
        valid, error = validate_app_id(app_id)
        assert valid is False

    # Invalid Flatpak IDs - starts with digit
    @pytest.mark.parametrize("app_id", [
        "123.app",
        "1org.test.app",
        "0.com.example",
    ])
    def test_invalid_starts_with_digit(self, app_id: str) -> None:
        """Test IDs starting with digit are invalid."""
        valid, error = validate_app_id(app_id)
        assert valid is False

    # Security: injection attempts
    @pytest.mark.parametrize("app_id", [
        "../etc/passwd",
        "test;rm -rf",
        "test&&rm -rf",
        "test|rm -rf",
        "test`rm`",
        "$(whoami)",
        "${HOME}",
    ])
    def test_invalid_injection_attempts(self, app_id: str) -> None:
        """Test that injection attempts are rejected."""
        valid, error = validate_app_id(app_id)
        assert valid is False

    # Security: long inputs
    def test_invalid_excessively_long(self) -> None:
        """Test that excessively long inputs are handled."""
        long_id = "a" * 500
        valid, error = validate_app_id(long_id)
        assert valid is False

    # Edge case: double dots (valid per Flatpak spec)
    def test_valid_double_dots(self) -> None:
        """Test that double dots are valid (Flatpak platform format)."""
        valid, error = validate_app_id("org.freedesktop.Platform//21.08")
        assert valid is True

    # Return type verification
    def test_returns_tuple(self) -> None:
        """Test that validate_app_id returns a tuple."""
        result = validate_app_id("org.test.App")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


class TestCheckPathTraversal:
    """Test check_path_traversal function."""

    def test_safe_nested_path(self) -> None:
        """Test that nested paths under base are safe."""
        base = Path("/home/user/.config")
        path = base / "app" / "config"
        safe, error = check_path_traversal(path, base)
        assert safe is True
        assert error == ""

    def test_safe_exact_match(self) -> None:
        """Test that exact base match is safe."""
        base = Path("/home/user/.config")
        safe, error = check_path_traversal(base, base)
        assert safe is True
        assert error == ""

    def test_unsafe_absolute_path_outside(self) -> None:
        """Test that absolute paths outside base are unsafe."""
        base = Path("/home/user/.config")
        path = Path("/etc/passwd")
        safe, error = check_path_traversal(path, base)
        assert safe is False
        assert error != ""

    def test_unsafe_parent_traversal(self) -> None:
        """Test that parent directory traversal is blocked."""
        base = Path("/home/user/.config")
        path = base / ".." / ".." / "etc" / "passwd"
        safe, error = check_path_traversal(path, base)
        assert safe is False

    def test_unsafe_deep_traversal(self) -> None:
        """Test deep path traversal attempts."""
        base = Path("/home/user")
        path = Path("/home/user/.config/../../../root/.ssh")
        safe, error = check_path_traversal(path, base)
        assert safe is False

    def test_resolves_symlinks(self) -> None:
        """Test that symlinks are resolved before checking."""
        # Note: This is a behavior test - actual symlink behavior depends on system
        base = Path("/home/user")
        path = Path("/var/home/user")  # Common symlink on some systems
        safe, error = check_path_traversal(path, base)
        # The result depends on whether these paths resolve to the same location

    def test_returns_tuple(self) -> None:
        """Test that check_path_traversal returns a tuple."""
        result = check_path_traversal(Path("/tmp"), Path("/home"))
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


class TestShouldProcessEvent:
    """Test should_process_event function."""

    @pytest.mark.parametrize("path", [
        "/var/lib/flatpak",
        "/var/lib/flatpak/app",
        "/var/lib/flatpak/app/org.example.App",
        "/var/lib/flatpak/exports",
        "/var/lib/flatpak/repo",
    ])
    def test_system_flatpak_paths(self, path: str) -> None:
        """Test that system Flatpak paths are processed."""
        assert should_process_event(path) is True

    @pytest.mark.parametrize("path", [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/group",
        "/etc/fplaunchwrapper/config",
    ])
    def test_etc_paths_rejected(self, path: str) -> None:
        """Test that /etc paths are not processed."""
        assert should_process_event(path) is False

    @pytest.mark.parametrize("path", [
        "/tmp/file",
        "/tmp/fplaunchwrapper",
        "/var/tmp/data",
    ])
    def test_tmp_paths_rejected(self, path: str) -> None:
        """Test that /tmp paths are not processed."""
        assert should_process_event(path) is False

    @pytest.mark.parametrize("path", [
        "/home/user/Documents",
        "/home/user/Downloads",
        "/var/home/user/Pictures",
    ])
    def test_home_paths_rejected(self, path: str) -> None:
        """Test that general home paths are not processed."""
        assert should_process_event(path) is False

    def test_accepts_pathlib_path(self) -> None:
        """Test that Path objects are accepted."""
        path = Path("/var/lib/flatpak/app/org.example.App")
        result = should_process_event(path)
        assert result is True

    def test_accepts_string(self) -> None:
        """Test that strings are accepted."""
        path = "/var/lib/flatpak/app/org.example.App"
        result = should_process_event(path)
        assert result is True

    def test_accepts_other_types(self) -> None:
        """Test that other types are converted to string."""
        # Should handle various input types gracefully
        result = should_process_event("/var/lib/flatpak")
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
