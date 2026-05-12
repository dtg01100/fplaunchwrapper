#!/usr/bin/env python3
"""Focused pytest coverage for lib.import_utils."""

from typing import Any
from unittest.mock import Mock

import pytest

from lib.import_utils import ImportErrorHandler, safe_import


class TestSafeImport:
    """Test safe_import utility function."""

    def test_import_existing_module(self) -> None:
        result = safe_import("os")
        assert result is not None
        import os
        assert result is os

    def test_import_existing_name(self) -> None:
        result = safe_import("os.path", name="join")
        assert result is not None
        from os.path import join
        assert result is join

    def test_import_nonexistent_module(self) -> None:
        result = safe_import("nonexistent_module_xyz")
        assert result is None

    def test_import_nonexistent_name(self) -> None:
        result = safe_import("os", name="NonExistentName")
        assert result is None

    def test_import_with_custom_default(self) -> None:
        default = object()
        result = safe_import("nonexistent", default=default)
        assert result is default

    def test_import_nonexistent_name_no_default(self) -> None:
        result = safe_import("os", name="NonExistentName")
        assert result is None


class TestImportErrorHandler:
    """Test ImportErrorHandler class."""

    @pytest.fixture
    def console_err(self) -> Mock:
        return Mock()

    def test_require_existing_module(self, console_err: Mock) -> None:
        handler = ImportErrorHandler(console_err)
        result = handler.require("os")
        import os
        assert result is os

    def test_require_existing_name(self, console_err: Mock) -> None:
        handler = ImportErrorHandler(console_err)
        result = handler.require("os.path", name="join")
        from os.path import join
        assert result is join

    def test_require_nonexistent_module_raises(self, console_err: Mock) -> None:
        handler = ImportErrorHandler(console_err)
        with pytest.raises(SystemExit) as exc_info:
            handler.require("nonexistent_module_xyz")
        assert exc_info.value.code == 1
        console_err.print.assert_called_once()

    def test_require_nonexistent_name_raises(self, console_err: Mock) -> None:
        handler = ImportErrorHandler(console_err)
        with pytest.raises(SystemExit) as exc_info:
            handler.require("os", name="NonExistentName")
        assert exc_info.value.code == 1
        console_err.print.assert_called_once()

    def test_require_error_message_contains_module_name(self, console_err: Mock) -> None:
        handler = ImportErrorHandler(console_err)
        with pytest.raises(SystemExit):
            handler.require("nonexistent_module_xyz")
        call_arg: Any = console_err.print.call_args[0][0]
        assert "nonexistent_module_xyz" in str(call_arg)

    def test_require_error_message_contains_dotted_name(self, console_err: Mock) -> None:
        handler = ImportErrorHandler(console_err)
        with pytest.raises(SystemExit):
            handler.require("os", name="NonExistentName")
        call_arg: Any = console_err.print.call_args[0][0]
        assert "os.NonExistentName" in str(call_arg)

    def test_require_uses_custom_console(self) -> None:
        custom_console = Mock()
        handler = ImportErrorHandler(custom_console)
        with pytest.raises(SystemExit):
            handler.require("nonexistent")
        custom_console.print.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
