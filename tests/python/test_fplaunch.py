#!/usr/bin/env python3
"""Focused pytest coverage for lib.fplaunch (entry point module)."""

import sys
from unittest.mock import patch
import pytest


class TestFplaunchModule:
    """Test fplaunch module attributes and safety stub."""

    def test_safe_launch_check_exists(self) -> None:
        from lib import fplaunch

        assert fplaunch.safe_launch_check is not None
        assert callable(fplaunch.safe_launch_check)

    def test_safety_exists(self) -> None:
        from lib import fplaunch

        assert fplaunch.safety is not None

    def test_safe_launch_check_is_callable(self) -> None:
        from lib import fplaunch

        result = fplaunch.safe_launch_check("test-app")
        assert isinstance(result, bool)


class TestFplaunchMain:
    """Test fplaunch.main() entry point."""

    def test_main_returns_exit_code(self) -> None:
        from lib.fplaunch import main

        result = main()
        assert isinstance(result, int)

    def test_main_returns_int_from_cli(self) -> None:
        """Test main returns the int returned by cli_main."""
        from lib.fplaunch import main

        with patch("lib.cli.main", return_value=0):
            assert main() == 0

    def test_main_returns_one_when_cli_main_is_none(self) -> None:
        """Test main returns 1 when cli.cli_main is None."""
        from lib import fplaunch

        with patch("lib.cli.main", None):
            assert fplaunch.main() == 1

    def test_main_handles_import_error(self, capsys) -> None:
        """Test main returns 1 and writes to stderr on ImportError."""
        from lib import fplaunch

        # Force the lazy `from .cli import main` to fail
        with patch.dict(sys.modules, {"lib.cli": None}):
            # When sys.modules['lib.cli'] is None, the import will raise ImportError
            result = fplaunch.main()
        assert result == 1
        captured = capsys.readouterr()
        assert "failed to import" in captured.err
        assert "PYTHONPATH" in captured.err

    def test_main_handles_attribute_error(self, capsys) -> None:
        """Test main returns 1 and writes to stderr on AttributeError."""
        from lib import fplaunch
        from lib import cli as cli_module
        import importlib

        original_main = cli_module.main
        # Replace cli_module.main with something that raises AttributeError
        try:
            def _raise_attribute_error():
                raise AttributeError("mocked attribute error")

            with patch.object(cli_module, "main", _raise_attribute_error):
                # Force reimport of fplaunch so its lazy import picks up the patched main
                importlib.reload(fplaunch)
                result = fplaunch.main()
            assert result == 1
            captured = capsys.readouterr()
            assert "fplaunchwrapper:" in captured.err
        finally:
            cli_module.main = original_main
            importlib.reload(fplaunch)


class TestFplaunchDunderMain:
    """Test __main__ block."""

    def test_dunder_main_calls_sys_exit(self) -> None:
        """Test that running fplaunch as __main__ calls sys.exit with main's return."""
        import runpy
        import sys as real_sys

        old_argv = real_sys.argv
        real_sys.argv = ["fplaunch"]
        try:
            runpy.run_module(
                "lib.fplaunch",
                run_name="__main__",
                alter_sys=True,
            )
        except SystemExit as e:
            # main() should call sys.exit(return_value), propagating the
            # click exit code (0 for help, 2 for usage error, etc.)
            assert isinstance(e.code, int)
            assert e.code >= 0
        else:
            # If sys.exit was called with None/0, runpy returns normally
            # which is also acceptable.
            pass
        finally:
            real_sys.argv = old_argv


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
