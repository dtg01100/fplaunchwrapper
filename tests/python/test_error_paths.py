#!/usr/bin/env python3
"""Defensive tests for error paths and edge cases.

These tests verify that error conditions are properly handled
and exceptions contain useful information.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestConfigManagerErrorPaths:
    """Test error paths in config_manager.py."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / ".config" / "fplaunchwrapper"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_set_cron_interval_rejects_zero(self) -> None:
        """set_cron_interval should reject interval of 0."""
        from lib.config_manager import EnhancedConfigManager
        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            with pytest.raises(ValueError, match="at least 1 hour"):
                config.set_cron_interval(0)

    def test_set_cron_interval_rejects_negative(self) -> None:
        """set_cron_interval should reject negative intervals."""
        from lib.config_manager import EnhancedConfigManager
        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            with pytest.raises(ValueError, match="at least 1 hour"):
                config.set_cron_interval(-5)


class TestGenerateErrorPaths:
    """Test error paths in generate.py."""

    def test_bin_dir_type_validation(self) -> None:
        """WrapperGenerator should reject invalid bin_dir types."""
        from lib.generate import WrapperGenerator
        with pytest.raises(TypeError, match="bin_dir"):
            WrapperGenerator(bin_dir=123)  # type: ignore

    def test_config_dir_type_validation(self) -> None:
        """WrapperGenerator should reject invalid config_dir types."""
        from lib.generate import WrapperGenerator
        with pytest.raises(TypeError):
            WrapperGenerator(bin_dir=Path("/tmp"), config_dir=123)  # type: ignore


class TestManageErrorPaths:
    """Test error paths in manage.py."""

    def test_remove_wrapper_handles_none_config_dir(self) -> None:
        """remove_wrapper handles missing config_dir gracefully."""
        from lib.manage import WrapperManager
        manager = WrapperManager(config_dir=None, bin_dir=Path("/tmp/bin"))
        result = manager.remove_wrapper("nonexistent_app", force=True)
        assert result is False

    def test_set_preference_handles_none_config_dir(self) -> None:
        """set_preference handles missing config_dir gracefully."""
        from lib.manage import WrapperManager
        manager = WrapperManager(config_dir=None, bin_dir=Path("/tmp/bin"))
        result = manager.set_preference("test_app", "system")
        assert result is False


class TestPortalLauncherErrorPaths:
    """Test error paths in portal_launcher.py."""

    def test_launch_with_portal_raises_when_spawn_not_found(self) -> None:
        """launch_with_portal should raise FileNotFoundError when flatpak-spawn not found."""
        from lib.portal_launcher import launch_with_portal
        with patch("lib.portal_launcher._get_flatpak_spawn_path", return_value=None):
            with pytest.raises(FileNotFoundError, match="flatpak-spawn not found"):
                launch_with_portal("org.example.App")

    def test_launch_raises_on_subprocess_error(self) -> None:
        """Launch functions should raise when subprocess fails unexpectedly."""
        from lib.portal_launcher import launch_direct
        with patch("lib.portal_launcher.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Unexpected system error")
            with pytest.raises(OSError):
                launch_direct("org.example.App")


class TestValidationEdgeCases:
    """Test edge cases in validation."""

    def test_validate_app_id_rejects_empty(self) -> None:
        """validate_app_id should reject empty strings."""
        from lib.validation import validate_app_id
        valid, _ = validate_app_id("")
        assert valid is False

    def test_validate_app_id_rejects_whitespace_only(self) -> None:
        """validate_app_id should reject whitespace-only strings."""
        from lib.validation import validate_app_id
        valid, _ = validate_app_id("   ")
        assert valid is False

    def test_validate_app_id_rejects_invalid_format(self) -> None:
        """validate_app_id should reject invalid formats."""
        from lib.validation import validate_app_id
        # No dot
        valid, _ = validate_app_id("firefox")
        assert valid is False
        # Starts with digit
        valid, _ = validate_app_id("1.example.App")
        assert valid is False


class TestPathTraversalDefense:
    """Test path traversal defensive checks."""

    def test_check_path_traversal_blocks_obvious_attacks(self) -> None:
        """check_path_traversal should block obvious traversal attempts."""
        from lib.validation import check_path_traversal
        base = Path("/home/user/.config/fplaunchwrapper")
        malicious_paths = [
            "/home/user/.config/fplaunchwrapper/../../../etc/passwd",
            "/home/../../root/.ssh/id_rsa",
        ]
        for path in malicious_paths:
            valid, reason = check_path_traversal(Path(path), base)
            assert valid is False, f"Should reject: {path}"

    def test_check_path_traversal_allows_nested(self) -> None:
        """check_path_traversal should allow legitimate nested paths."""
        from lib.validation import check_path_traversal
        base = Path("/home/user/.config/fplaunchwrapper")
        valid_paths = [
            "/home/user/.config/fplaunchwrapper/wrappers/app1",
        ]
        for path in valid_paths:
            valid, _ = check_path_traversal(Path(path), base)
            assert valid is True, f"Should allow: {path}"


class TestImportErrorHandling:
    """Test import error handling."""

    def test_safe_import_returns_default_on_failure(self) -> None:
        """safe_import should return default when module not found."""
        from lib.import_utils import safe_import
        result = safe_import("nonexistent_module_xyz", default="fallback")
        assert result == "fallback"

    def test_safe_import_returns_none_on_not_found(self) -> None:
        """safe_import should return None when module not found and no default."""
        from lib.import_utils import safe_import
        result = safe_import("nonexistent_module_xyz")
        assert result is None


class TestSafetyChecks:
    """Test safety check behaviors."""

    def test_validate_flatpak_id_rejects_command_injection(self) -> None:
        """validate_flatpak_id should reject command injection attempts."""
        from lib.safety import validate_flatpak_id
        malicious_ids = [
            "org.test;rm -rf",
            "org.test`whoami`",
            "org.test$(whoami)",
        ]
        for malicious_id in malicious_ids:
            assert validate_flatpak_id(malicious_id) is False, f"Should reject: {malicious_id}"

    def test_sanitize_id_to_name_handles_edge_cases(self) -> None:
        """sanitize_id_to_name should handle edge cases gracefully."""
        from lib.python_utils import sanitize_id_to_name
        # Empty string produces a hash-like fallback (not crash)
        result = sanitize_id_to_name("")
        assert result.startswith("app-")
        # Very long ID should still work
        long_id = "a" * 200 + ".b"
        result = sanitize_id_to_name(long_id)
        assert len(result) <= 255
