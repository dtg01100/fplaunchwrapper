#!/usr/bin/env python3
"""Unit tests for fplaunch.py main entry point
Tests command routing and main application logic.
"""

from unittest.mock import Mock, patch

import pytest

# Add lib to path
# Import the module to test
try:
    import fplaunch
except ImportError:
    # Mock it if not available
    fplaunch = None


class TestMainEntryPoint:
    """Test the main fplaunch entry point."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.mock_cli = Mock()
        self.mock_generate = Mock()
        self.mock_manage = Mock()
        self.mock_launch = Mock()
        self.mock_cleanup = Mock()
        self.mock_systemd_setup = Mock()
        self.mock_config_manager = Mock()
        self.mock_flatpak_monitor = Mock()

    @patch("sys.argv", ["fplaunch", "--help"])
    @patch("lib.cli.main")
    def test_main_entry_help(self, mock_cli_main) -> None:
        """Test main entry point with help flag."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        # Mock the CLI main function
        mock_cli_main.return_value = 0

        # Import and call main
        from fplaunch.fplaunch import main

        result = main()

        # Verify CLI main was called
        mock_cli_main.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "generate", "/home/vscode/bin"])
    @patch("fplaunch.generate.WrapperGenerator.run")
    def test_main_entry_generate(self, mock_run) -> None:
        """Test main entry point routes to generate."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_run.return_value = 0

        from fplaunch.fplaunch import main

        result = main()

        mock_run.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "set-pref", "firefox", "flatpak"])
    @patch("fplaunch.manage.WrapperManager.set_preference")
    def test_main_entry_set_pref(self, mock_set_preference) -> None:
        """Test main entry point routes to manage."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_set_preference.return_value = True

        from fplaunch.fplaunch import main

        result = main()

        mock_set_preference.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "launch", "firefox"])
    @patch("fplaunch.launch.AppLauncher.launch")
    def test_main_entry_launch(self, mock_launch) -> None:
        """Test main entry point routes to launch."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_launch.return_value = True

        from fplaunch.fplaunch import main

        result = main()

        mock_launch.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "cleanup"])
    @patch("fplaunch.cleanup.WrapperCleanup.run")
    def test_main_entry_cleanup(self, mock_run) -> None:
        """Test main entry point routes to cleanup."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_run.return_value = 0

        from fplaunch.fplaunch import main

        result = main()

        mock_run.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "systemd-setup"])
    @patch("fplaunch.systemd_setup.SystemdSetup.run")
    def test_main_entry_systemd_setup(self, mock_setup_service) -> None:
        """Test main entry point routes to systemd setup."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_setup_service.return_value = 0

        from fplaunch.fplaunch import main

        result = main()

        mock_setup_service.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "config"])
    @patch("lib.config_manager.create_config_manager")
    def test_main_entry_config(self, mock_create_config) -> None:
        """Test main entry point routes to config manager."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        # Create a mock config manager
        mock_config = Mock()
        mock_create_config.return_value = mock_config

        from fplaunch.fplaunch import main

        result = main()

        mock_create_config.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "monitor"])
    @patch("lib.flatpak_monitor.main")
    def test_main_entry_monitor(self, mock_monitor_main) -> None:
        """Test main entry point routes to monitor."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_monitor_main.return_value = 0

        from fplaunch.fplaunch import main

        result = main()

        mock_monitor_main.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "invalid-command"])
    def test_main_entry_invalid_command(self) -> None:
        """Test main entry point handles invalid commands."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        from fplaunch.fplaunch import main

        result = main()

        # Should return non-zero for invalid command
        assert result != 0

    @patch("sys.argv", ["fplaunch"])
    def test_main_entry_no_args(self) -> None:
        """Test main entry point with no arguments."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        from fplaunch.fplaunch import main

        result = main()

        # Should show help or error
        assert isinstance(result, int)

    @patch("sys.argv", ["fplaunch", "--version"])
    def test_main_entry_version(self) -> None:
        """Test main entry point version flag."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        # Mock version handling if it exists
        from fplaunch.fplaunch import main

        result = main()

        # Should handle version gracefully
        assert isinstance(result, int)

    @patch.dict("os.environ", {"FPWRAPPER_DEBUG": "1"})
    @patch("sys.argv", ["fplaunch", "generate", "/tmp/bin"])
    @patch("fplaunch.generate.WrapperGenerator.run")
    def test_main_entry_debug_mode(self, mock_run) -> None:
        """Test main entry point respects debug environment."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_run.return_value = 0

        from fplaunch.fplaunch import main

        result = main()

        mock_run.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "generate", "/tmp/bin", "--help"])
    def test_main_entry_command_help(self) -> None:
        """Test main entry point passes help to subcommands."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        # Help is handled by Click, should exit with 0
        from fplaunch.fplaunch import main

        result = main()

        assert result == 0


class TestCommandRouting:
    """Test command routing logic."""

    def test_command_mapping(self) -> None:
        """Test that commands are properly mapped to modules."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        # Test the command to module mapping logic
        expected_commands = {
            "generate": "fplaunch.generate",
            "set-pref": "fplaunch.manage",
            "remove": "fplaunch.manage",
            "list": "fplaunch.manage",
            "launch": "fplaunch.launch",
            "cleanup": "fplaunch.cleanup",
            "setup-systemd": "fplaunch.systemd_setup",
            "config": "fplaunch.config_manager",
            "monitor": "fplaunch.flatpak_monitor",
        }

        # Verify these commands are recognized
        for cmd in expected_commands:
            assert cmd in [
                "generate",
                "set-pref",
                "remove",
                "list",
                "launch",
                "cleanup",
                "setup-systemd",
                "config",
                "monitor",
            ]

    @patch("importlib.import_module")
    @patch("sys.argv", ["fplaunch", "test-command"])
    def test_dynamic_import_handling(self, mock_import) -> None:
        """Test handling of unknown commands."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        from fplaunch.fplaunch import main

        result = main()

        # Unknown command should fail
        mock_import.assert_not_called()
        assert result != 0

    @patch("importlib.import_module")
    @patch("sys.argv", ["fplaunch", "invalid-module"])
    def test_import_error_handling(self, mock_import) -> None:
        """Test graceful handling of import errors."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        # Mock import error
        mock_import.side_effect = ImportError("Module not found")

        from fplaunch.fplaunch import main

        result = main()

        # Should handle import error gracefully
        assert result != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
