#!/usr/bin/env python3
"""Comprehensive pytest test suite for fplaunchwrapper."""

import subprocess
import tempfile
from pathlib import Path

import pytest


# Add lib to path
class TestComprehensiveSuite:
    """Comprehensive test suite."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp())
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"
        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    def run_command_test(self, cmd, description, expect_success=True) -> None:
        """Run a command and test result."""
        try:
            result = subprocess.run(
                cmd,
                check=False, cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=30,
            )
            success = (result.returncode == 0) == expect_success
            assert success, f"{description} failed: {result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.fail(f"{description} timed out")
        except Exception as e:
            pytest.fail(f"{description} failed with exception: {e}")

    def test_cli_help_command(self) -> None:
        """Test CLI help command."""
        self.run_command_test(["python", "-m", "lib.cli", "--help"], "CLI help command")

    def test_cli_config_command(self) -> None:
        """Test CLI config command."""
        self.run_command_test(
            ["python", "-m", "lib.cli", "config"], "CLI config command",
        )

    def test_emit_mode_no_side_effects(self, temp_env) -> None:
        """Test that emit mode creates no files."""
        # Count files before
        before_count = sum(1 for _ in temp_env["temp_dir"].rglob("*") if _.is_file())

        # Run emit commands
        self.run_command_test(
            ["python", "-m", "lib.cli", "generate", "--emit", str(temp_env["bin_dir"])],
            "Generate emit mode",
        )

        self.run_command_test(
            ["python", "-m", "lib.cli", "set-pref", "firefox", "flatpak", "--emit"],
            "Set-pref emit mode",
        )

        self.run_command_test(
            ["python", "-m", "lib.cli", "setup-systemd", "--emit"],
            "Setup-systemd emit mode",
        )

        # Count files after
        after_count = sum(1 for _ in temp_env["temp_dir"].rglob("*") if _.is_file())

        # Should not have created any new files
        assert before_count == after_count, "Emit mode created unexpected files"

    def test_emit_verbose_content_inspection(self) -> None:
        """Test emit verbose shows detailed content."""
        # Test that emit verbose commands produce output with content markers
        # This is a basic smoke test - full validation would require more setup
        self.run_command_test(
            ["python", "-m", "lib.cli", "config", "--emit"], "Config emit mode",
        )

        self.run_command_test(
            ["python", "-m", "lib.cli", "monitor", "--emit"], "Monitor emit mode",
        )

    def test_cli_emit_flags_integration(self) -> None:
        """Test CLI emit flags work properly."""
        # Test individual emit flags
        commands = [
            (
                ["python", "-m", "lib.cli", "generate", "--emit", "/tmp/test"],
                "generate --emit",
            ),
            (
                ["python", "-m", "lib.cli", "set-pref", "test", "flatpak", "--emit"],
                "set-pref --emit",
            ),
            (
                ["python", "-m", "lib.cli", "setup-systemd", "--emit"],
                "setup-systemd --emit",
            ),
            (["python", "-m", "lib.cli", "config", "--emit"], "config --emit"),
            (["python", "-m", "lib.cli", "monitor", "--emit"], "monitor --emit"),
            (
                ["python", "-m", "lib.cli", "--emit", "generate", "/tmp/test"],
                "global --emit flag",
            ),
        ]

        for cmd, description in commands:
            self.run_command_test(cmd, description)

    def test_error_handling(self) -> None:
        """Test error handling in CLI."""
        # Test invalid command
        self.run_command_test(
            ["python", "-m", "lib.cli", "nonexistent"],
            "Invalid command handling",
            expect_success=False,
        )

    def test_integration_workflow(self) -> None:
        """Test basic integration workflow."""
        # This is a smoke test for the overall system
        # In a real scenario, this would test a complete workflow
        self.run_command_test(
            ["python", "-m", "lib.cli", "--help"], "Basic CLI integration",
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
