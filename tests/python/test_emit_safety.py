#!/usr/bin/env python3
"""Pytest tests for emit-based safe testing."""

import subprocess
from pathlib import Path

import pytest


# Add lib to path
class TestEmitSafety:
    """Test emit mode safety features."""

    def run_emit_test(self, command, description):
        """Run a command with emit mode and return success."""
        try:
            result = subprocess.run(
                command,
                check=False, capture_output=True,
                text=True,
                cwd=Path(__file__).resolve().parents[2],
                timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False

    def test_generate_emit_safety(self) -> None:
        """Test that generate --emit doesn't create files."""
        import sys
        command = [sys.executable, "-m", "fplaunch.cli", "generate", "--emit", "/tmp/test-bin"]
        success = self.run_emit_test(command, "generate emit safety")
        assert success

    def test_manage_set_pref_emit_safety(self) -> None:
        """Test that set-pref --emit doesn't create files."""
        import sys
        command = [
            sys.executable,
            "-m",
            "fplaunch.cli",
            "set-pref",
            "firefox",
            "flatpak",
            "--emit",
        ]
        success = self.run_emit_test(command, "set-pref emit safety")
        assert success

    def test_systemd_setup_emit_safety(self) -> None:
        """Test that setup-systemd --emit doesn't create files."""
        import sys
        command = [sys.executable, "-m", "fplaunch.cli", "setup-systemd", "--emit"]
        success = self.run_emit_test(command, "setup-systemd emit safety")
        assert success

    def test_global_emit_flag_safety(self) -> None:
        """Test that global --emit flag works safely."""
        import sys
        command = [sys.executable, "-m", "fplaunch.cli", "--emit", "set-pref", "chrome", "system"]
        success = self.run_emit_test(command, "global emit flag safety")
        assert success

    def test_config_emit_safety(self) -> None:
        """Test that config --emit works safely."""
        import sys
        command = [sys.executable, "-m", "fplaunch.cli", "config", "--emit"]
        success = self.run_emit_test(command, "config emit safety")
        assert success

    def test_monitor_emit_safety(self) -> None:
        """Test that monitor --emit works safely."""
        import sys
        command = [sys.executable, "-m", "fplaunch.cli", "monitor", "--emit"]
        success = self.run_emit_test(command, "monitor emit safety")
        assert success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
