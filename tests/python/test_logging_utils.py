#!/usr/bin/env python3
"""Focused pytest coverage for lib.logging_utils."""

from unittest.mock import patch

import pytest

from lib.logging_utils import LoggingMixin, console, console_err


class TestConsoleInstances:
    """Test module-level console instances.

    The earlier ``test_console_is_not_none`` / ``test_console_err_is_not_none``
    were pure no-ops: the import on line 8 already raises if either
    binding is missing. These versions assert the actual contract --
    a Rich Console instance bound to the correct stream.
    """

    def test_console_is_rich_console_default_stdout(self) -> None:
        from rich.console import Console

        assert isinstance(console, Console)
        # The default console writes to sys.stdout; a non-forced-terminal
        # console is what the rest of the codebase expects.
        assert console.stderr is False

    def test_console_err_is_rich_console_stderr(self) -> None:
        from rich.console import Console

        assert isinstance(console_err, Console)
        assert console_err.stderr is True

    def test_console_and_console_err_are_distinct(self) -> None:
        # The two singletons must not alias the same object; otherwise
        # an error log would land on stdout and vice versa.
        assert console is not console_err


class TestLoggingMixin:
    """Test LoggingMixin log method."""

    @pytest.fixture
    def logger(self) -> LoggingMixin:
        return LoggingMixin()

    def test_info_level(self, logger: LoggingMixin) -> None:
        with patch.object(console, "print") as mock_print:
            logger.log("hello", level="info")
        mock_print.assert_called_once_with("hello")

    def test_error_level_uses_stderr(self, logger: LoggingMixin) -> None:
        with patch.object(console_err, "print") as mock_print:
            logger.log("something failed", level="error")
        mock_print.assert_called_once()

    def test_warning_level_uses_stderr(self, logger: LoggingMixin) -> None:
        with patch.object(console_err, "print") as mock_print:
            logger.log("caution", level="warning")
        mock_print.assert_called_once()

    def test_success_level(self, logger: LoggingMixin) -> None:
        with patch.object(console, "print") as mock_print:
            logger.log("done", level="success")
        mock_print.assert_called_once()

    def test_emit_level(self, logger: LoggingMixin) -> None:
        with patch.object(console, "print") as mock_print:
            logger.log("emitting", level="emit")
        mock_print.assert_called_once()

    def test_debug_not_printed_when_not_verbose(self, logger: LoggingMixin) -> None:
        logger.verbose = False
        with patch.object(console, "print") as mock_print:
            logger.log("debug info", level="debug")
        mock_print.assert_not_called()

    def test_debug_printed_when_verbose(self, logger: LoggingMixin) -> None:
        logger.verbose = True
        with patch.object(console, "print") as mock_print:
            logger.log("debug info", level="debug")
        mock_print.assert_called_once()

    def test_unknown_level_falls_through(self, logger: LoggingMixin) -> None:
        with patch.object(console, "print") as mock_print:
            logger.log("raw message", level="unknown_level")
        mock_print.assert_called_once_with("raw message")

    def test_default_verbose_is_false(self) -> None:
        assert LoggingMixin.verbose is False


class TestLoggingMixinSubclass:
    """Test that subclasses inherit log behavior correctly."""

    def test_subclass_inherits_log(self) -> None:
        class MyClass(LoggingMixin):
            pass

        obj = MyClass()
        with patch.object(console, "print") as mock_print:
            obj.log("from subclass")
        mock_print.assert_called_once_with("from subclass")

    def test_subclass_custom_verbose(self) -> None:
        class VerboseClass(LoggingMixin):
            verbose = True

        obj = VerboseClass()
        assert obj.verbose is True
        with patch.object(console, "print") as mock_print:
            obj.log("debug info", level="debug")
        mock_print.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
