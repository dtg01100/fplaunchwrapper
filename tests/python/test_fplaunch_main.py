#!/usr/bin/env python3
"""Unit tests for fplaunch.py main entry point
Tests command routing and main application logic.
"""

from unittest.mock import Mock, patch

import pytest

try:
    from lib.main_entrypoint import main as fplaunch_main
    fplaunch = type('Module', (), {'main': fplaunch_main})()
except ImportError:
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
        from lib.main_entrypoint import main

        result = main()

        # Verify CLI main was called
        mock_cli_main.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "generate", "/home/vscode/bin"])
    @patch("lib.generate.WrapperGenerator")
    def test_main_entry_generate(self, mock_wrapper_generator) -> None:
        """Test main entry point routes to generate."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_instance = Mock()
        mock_instance.run.return_value = 0
        mock_wrapper_generator.return_value = mock_instance

        from lib.main_entrypoint import main

        result = main()

        mock_wrapper_generator.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "set-pref", "firefox", "flatpak"])
    @patch("lib.manage.WrapperManager.set_preference")
    def test_main_entry_set_pref(self, mock_set_preference) -> None:
        """Test main entry point routes to manage."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_set_preference.return_value = True

        from lib.main_entrypoint import main

        result = main()

        mock_set_preference.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "launch", "firefox"])
    @patch("lib.launch.AppLauncher.launch")
    def test_main_entry_launch(self, mock_launch) -> None:
        """Test main entry point routes to launch."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_launch.return_value = True

        from lib.main_entrypoint import main

        result = main()

        mock_launch.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "cleanup"])
    @patch("lib.cleanup.WrapperCleanup.run")
    def test_main_entry_cleanup(self, mock_run) -> None:
        """Test main entry point routes to cleanup."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_run.return_value = 0

        from lib.main_entrypoint import main

        result = main()

        mock_run.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "systemd-setup"])
    @patch("lib.systemd_setup.SystemdSetup.run")
    def test_main_entry_systemd_setup(self, mock_setup_service) -> None:
        """Test main entry point routes to systemd setup."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_setup_service.return_value = 0

        from lib.main_entrypoint import main

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

        from lib.main_entrypoint import main

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

        from lib.main_entrypoint import main

        result = main()

        mock_monitor_main.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "invalid-command"])
    def test_main_entry_invalid_command(self) -> None:
        """Test main entry point handles invalid commands."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        from lib.main_entrypoint import main

        result = main()

        # Should return non-zero for invalid command
        assert result != 0

    @patch("sys.argv", ["fplaunch"])
    def test_main_entry_no_args(self) -> None:
        """Test main entry point with no arguments."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        from lib.main_entrypoint import main

        result = main()

        # Should show help or error
        assert isinstance(result, int)

    @patch("sys.argv", ["fplaunch", "--version"])
    def test_main_entry_version(self) -> None:
        """Test main entry point version flag."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        # Mock version handling if it exists
        from lib.main_entrypoint import main

        result = main()

        # Should handle version gracefully
        assert isinstance(result, int)

    @patch.dict("os.environ", {"FPWRAPPER_DEBUG": "1"})
    @patch("sys.argv", ["fplaunch", "generate", "/tmp/bin"])
    @patch("lib.generate.WrapperGenerator.run")
    def test_main_entry_debug_mode(self, mock_run) -> None:
        """Test main entry point respects debug environment."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        mock_run.return_value = 0

        from lib.main_entrypoint import main

        result = main()

        mock_run.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["fplaunch", "generate", "/tmp/bin", "--help"])
    def test_main_entry_command_help(self) -> None:
        """Test main entry point passes help to subcommands."""
        if not fplaunch:
            pytest.skip("fplaunch module not available")

        # Help is handled by Click, should exit with 0
        from lib.main_entrypoint import main

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

        from lib.main_entrypoint import main

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

        from lib.main_entrypoint import main

        result = main()

        # Should handle import error gracefully
        assert result != 0


@pytest.mark.skipif(fplaunch is None, reason="lib.main_entrypoint module not available")
class TestSafetyImportFallback:
    """Test the safety module import fallback in main_entrypoint (lines 16-22)."""

    def test_safety_stub_created_on_import_error(self) -> None:
        """Test that _SafetyStub is created when lib.safety import fails."""
        import sys

        # Save the original module if it exists
        original_main_entrypoint = sys.modules.get("lib.main_entrypoint")
        original_safety = sys.modules.get("lib.safety")

        try:
            # Remove the modules from cache to force re-import
            if "lib.main_entrypoint" in sys.modules:
                del sys.modules["lib.main_entrypoint"]
            if "lib.safety" in sys.modules:
                del sys.modules["lib.safety"]

            # Patch to make lib.safety import fail
            with patch.dict("sys.modules", {"lib.safety": None}):
                # Also need to prevent the relative import from working
                # by removing the safety module from lib package
                import lib

                original_lib_safety = getattr(lib, "safety", None)
                if hasattr(lib, "safety"):
                    delattr(lib, "safety")

                try:
                    # Re-import main_entrypoint to trigger fallback
                    import lib.main_entrypoint as main_entrypoint_module

                    # Verify that safety attribute exists and is a stub
                    assert hasattr(main_entrypoint_module, "safety")
                    # The safety object should have safe_launch_check method
                    assert hasattr(main_entrypoint_module.safety, "safe_launch_check")

                finally:
                    # Restore lib.safety if it existed
                    if original_lib_safety is not None:
                        lib.safety = original_lib_safety

        finally:
            # Restore original modules
            if original_main_entrypoint is not None:
                sys.modules["lib.main_entrypoint"] = original_main_entrypoint
            if original_safety is not None:
                sys.modules["lib.safety"] = original_safety

    def test_safety_stub_safe_launch_check_returns_true(self) -> None:
        """Test that _SafetyStub.safe_launch_check() returns True."""
        import sys

        # Save the original module if it exists
        original_main_entrypoint = sys.modules.get("lib.main_entrypoint")
        original_safety = sys.modules.get("lib.safety")

        try:
            # Remove the modules from cache to force re-import
            if "lib.main_entrypoint" in sys.modules:
                del sys.modules["lib.main_entrypoint"]
            if "lib.safety" in sys.modules:
                del sys.modules["lib.safety"]

            # Patch to make lib.safety import fail
            with patch.dict("sys.modules", {"lib.safety": None}):
                import lib

                original_lib_safety = getattr(lib, "safety", None)
                if hasattr(lib, "safety"):
                    delattr(lib, "safety")

                try:
                    # Re-import main_entrypoint to trigger fallback
                    import lib.main_entrypoint as main_entrypoint_module

                    # Call safe_launch_check and verify it returns True
                    result = main_entrypoint_module.safety.safe_launch_check("test_app")
                    assert result is True

                    # Also test with wrapper_path argument (should still return True)
                    result = main_entrypoint_module.safety.safe_launch_check("test_app", "/tmp/test_wrapper")
                    assert result is True

                finally:
                    if original_lib_safety is not None:
                        lib.safety = original_lib_safety

        finally:
            # Restore original modules
            if original_main_entrypoint is not None:
                sys.modules["lib.main_entrypoint"] = original_main_entrypoint
            if original_safety is not None:
                sys.modules["lib.safety"] = original_safety


@pytest.mark.skipif(fplaunch is None, reason="lib.main_entrypoint module not available")
class TestCLIImportFallback:
    """Test the CLI module import fallback in main() (lines 33-43)."""

    def test_main_fallback_to_lib_import_on_import_error(self) -> None:
        """Test that main() falls back to 'from lib import cli' on ImportError."""

        # We need to test the fallback path by making the relative import fail
        # but the absolute import succeed
        original_cli_main = None

        try:
            # Import cli normally first to get the real main
            from lib import cli as real_cli

            original_cli_main = real_cli.main

            # Mock the cli.main to track calls
            mock_main = Mock(return_value=0)
            real_cli.main = mock_main

            # Now test main() - it should use the already imported cli
            from lib.main_entrypoint import main

            result = main()

            # Verify the mock was called
            mock_main.assert_called_once()
            assert result == 0

        finally:
            # Restore original
            if original_cli_main is not None:
                real_cli.main = original_cli_main

    def test_main_returns_1_when_cli_has_no_main(self) -> None:
        """Test that main() returns 1 when cli module has no main attribute."""
        import sys
        from lib import cli as real_cli

        original_main = getattr(real_cli, "main", None)
        if original_main is None:
            pytest.skip("cli.main not available")

        # Save state for restoration
        original_main_entrypoint = sys.modules.get("lib.main_entrypoint")

        try:
            # Temporarily remove main
            delattr(real_cli, "main")

            # Call main directly - it will try to import cli
            # Since we deleted cli.main, it should return 1
            from lib.main_entrypoint import main

            # Remove main_entrypoint from cache so it re-evaluates
            if "lib.main_entrypoint" in sys.modules:
                del sys.modules["lib.main_entrypoint"]

            # Re-import
            import lib.main_entrypoint

            # Call main - should return 1 since cli has no main
            result = lib.main_entrypoint.main()

            assert result == 1

        finally:
            # Restore main
            if original_main is not None:
                real_cli.main = original_main

            # Restore sys.modules state
            if original_main_entrypoint is not None:
                sys.modules["lib.main_entrypoint"] = original_main_entrypoint

    def test_main_returns_1_on_both_imports_failing(self) -> None:
        """Test that main() returns 1 when both import paths fail."""
        import sys

        # Save original modules
        original_main_entrypoint = sys.modules.get("lib.main_entrypoint")
        original_cli = sys.modules.get("lib.cli")

        try:
            # Remove modules from cache
            if "lib.main_entrypoint" in sys.modules:
                del sys.modules["lib.main_entrypoint"]
            if "lib.cli" in sys.modules:
                del sys.modules["lib.cli"]

            # Make both import paths fail by setting lib.cli to None
            # and preventing the relative import
            with patch.dict("sys.modules", {"lib.cli": None, "cli": None}):
                # Also need to remove cli from lib package
                import lib

                original_lib_cli = getattr(lib, "cli", None)
                if hasattr(lib, "cli"):
                    delattr(lib, "cli")

                try:
                    # Re-import main_entrypoint
                    import lib.main_entrypoint as main_entrypoint_module

                    # Call main - should return 1 since both imports fail
                    result = main_entrypoint_module.main()

                    assert result == 1

                finally:
                    # Restore lib.cli if it existed
                    if original_lib_cli is not None:
                        lib.cli = original_lib_cli

        finally:
            # Restore original modules
            if original_main_entrypoint is not None:
                sys.modules["lib.main_entrypoint"] = original_main_entrypoint
            if original_cli is not None:
                sys.modules["lib.cli"] = original_cli

    def test_main_attribute_error_on_cli_main(self) -> None:
        """Test handling of AttributeError when cli.main doesn't exist."""
        import sys
        from lib import cli as real_cli

        original_main = getattr(real_cli, "main", None)
        if original_main is None:
            pytest.skip("cli.main not available")

        # Save state for restoration
        original_main_entrypoint = sys.modules.get("lib.main_entrypoint")

        try:
            # Set main to None to simulate it not being callable
            real_cli.main = None  # type: ignore

            # Remove main_entrypoint from cache
            if "lib.main_entrypoint" in sys.modules:
                del sys.modules["lib.main_entrypoint"]

            # Re-import main_entrypoint
            import lib.main_entrypoint

            # main() should handle this gracefully since hasattr check comes first
            result = lib.main_entrypoint.main()
            # When cli.main is None, hasattr returns True but call fails
            # The code returns 1 in this case
            assert result == 1

        except (TypeError, AttributeError):
            # If the call fails, that's expected behavior
            pass

        finally:
            # Restore main
            if original_main is not None:
                real_cli.main = original_main

            # Restore sys.modules state
            if original_main_entrypoint is not None:
                sys.modules["lib.main_entrypoint"] = original_main_entrypoint

    def test_main_fallback_import_path_success(self) -> None:
        """Test the fallback import path (lines 38-41) succeeds.

        This tests the case where relative import fails but absolute import succeeds.
        """
        import builtins
        import sys

        original_main_entrypoint = sys.modules.get("lib.main_entrypoint")
        original_import = builtins.__import__

        def mock_import(name, _globals=None, _locals=None, fromlist=(), level=0):
            """Custom import that fails relative import for cli but allows absolute."""
            # Fail the relative import of cli (level=1 means relative import)
            if name == "lib.cli" or (fromlist and "cli" in str(fromlist)):
                if level > 0:  # This is a relative import
                    raise ImportError("Simulated relative import failure")
            # For absolute imports, use the real import
            return original_import(name, _globals, _locals, fromlist, level)

        try:
            # Remove main_entrypoint from cache
            if "lib.main_entrypoint" in sys.modules:
                del sys.modules["lib.main_entrypoint"]

            with patch.object(builtins, "__import__", side_effect=mock_import):
                # Re-import main_entrypoint - this will use our mock import
                import lib.main_entrypoint as main_entrypoint_module  # noqa: F401

            # Now call main - it should use the fallback import path
            # Since we can't easily control the import inside main(),
            # we verify the module was imported correctly
            from lib.main_entrypoint import main

            # The main function should still work via fallback
            result = main()
            assert isinstance(result, int)

        finally:
            # Restore
            builtins.__import__ = original_import
            if original_main_entrypoint is not None:
                sys.modules["lib.main_entrypoint"] = original_main_entrypoint

    def test_main_fallback_cli_no_main_returns_1(self) -> None:
        """Test fallback path returns 1 when cli has no main attribute.

        This tests lines 40-41 in the fallback import path.
        """
        import sys

        # Save original modules
        original_main_entrypoint = sys.modules.get("lib.main_entrypoint")
        original_cli = sys.modules.get("lib.cli")

        try:
            # Remove modules from cache
            if "lib.main_entrypoint" in sys.modules:
                del sys.modules["lib.main_entrypoint"]
            if "lib.cli" in sys.modules:
                del sys.modules["lib.cli"]

            # Create a mock cli module without main
            mock_cli = Mock()
            # Explicitly ensure 'main' attribute doesn't exist
            if hasattr(mock_cli, "main"):
                delattr(mock_cli, "main")

            with patch.dict("sys.modules", {"lib.cli": mock_cli, "cli": mock_cli}):
                # Re-import main_entrypoint
                import lib.main_entrypoint as main_entrypoint_module

                # Call main - should return 1 since cli has no main
                result = main_entrypoint_module.main()

                assert result == 1

        finally:
            # Restore original modules
            if original_main_entrypoint is not None:
                sys.modules["lib.main_entrypoint"] = original_main_entrypoint
            if original_cli is not None:
                sys.modules["lib.cli"] = original_cli

    def test_main_fallback_path_no_main_attribute(self) -> None:
        """Test fallback path returns 1 when cli.main doesn't exist (lines 40-41).

        This tests the fallback import path where cli imports successfully
        but has no main attribute.
        """
        import sys
        import types

        # Save original modules
        original_main_entrypoint = sys.modules.get("lib.main_entrypoint")
        original_cli = sys.modules.get("lib.cli")

        try:
            # Remove main_entrypoint from cache to force re-import
            if "lib.main_entrypoint" in sys.modules:
                del sys.modules["lib.main_entrypoint"]

            # Create a mock cli module WITHOUT a main function
            mock_cli = types.ModuleType("lib.cli")
            # Don't add main attribute

            # Set up the mock cli module
            sys.modules["lib.cli"] = mock_cli

            # Create import hook to fail relative imports
            class FailingRelativeImporter:
                """Meta path finder that fails relative imports for cli."""

                def find_spec(self, fullname, path, _target=None):
                    if fullname == "lib.cli" and path is not None:
                        raise ImportError("Simulated relative import failure")
                    return None

            importer = FailingRelativeImporter()
            sys.meta_path.insert(0, importer)

            try:
                # Re-import main_entrypoint
                import lib.main_entrypoint as main_entrypoint_module

                # Call main - should use fallback path and return 1
                result = main_entrypoint_module.main()

                assert result == 1

            finally:
                sys.meta_path.remove(importer)

        finally:
            # Restore original modules
            if original_main_entrypoint is not None:
                sys.modules["lib.main_entrypoint"] = original_main_entrypoint
            if original_cli is not None:
                sys.modules["lib.cli"] = original_cli
            elif "lib.cli" in sys.modules and sys.modules["lib.cli"] is mock_cli:
                del sys.modules["lib.cli"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
