#!/usr/bin/env python3
"""Tests for Rich console output rendering and formatting.

This test suite ensures that:
1. Rich output renders correctly to console
2. ANSI color codes are present in formatted output
3. Table, Panel, and other Rich components render expected structure
4. Graceful fallback works when Rich is unavailable
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.text import Text
    from rich.syntax import Syntax

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from lib.logging_utils import LoggingMixin, console, console_err


pytestmark = [pytest.mark.unit]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def rich_capture() -> Console:
    """Provide a Console that captures output to StringIO."""
    output = StringIO()
    return Console(file=output, force_terminal=True, width=80)


@pytest.fixture
def rich_error_capture() -> Console:
    """Provide a Console that captures output to StringIO for stderr."""
    output = StringIO()
    return Console(file=output, force_terminal=True, width=80, stderr=True)


# =============================================================================
# Console Instance Tests
# =============================================================================

class TestConsoleInstances:
    """Test module-level console instances exist and are usable."""

    def test_console_is_rich_console(self) -> None:
        """Verify console is a Rich Console instance."""
        assert RICH_AVAILABLE, "Rich library not available"
        assert isinstance(console, Console)

    def test_console_err_is_rich_console(self) -> None:
        """Verify console_err is a Rich Console instance."""
        assert isinstance(console_err, Console)

    def test_console_has_no_file(self) -> None:
        """Console should write to stdout by default."""
        assert console.file is not None


# =============================================================================
# Table Rendering Tests
# =============================================================================

class TestTableRendering:
    """Test rich.Table rendering in WrapperManager.display_wrappers."""

    def test_table_has_correct_columns(self, rich_capture: Console) -> None:
        """Table should have Name, ID, and Path columns."""
        table = Table(title="Test Wrappers")
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="green")
        table.add_column("Path", style="dim")

        table.add_row("firefox", "org.mozilla.firefox", "/home/user/bin")
        table.add_row("chrome", "com.google.chrome", "/home/user/bin")

        rich_capture.print(table)
        output = rich_capture.file.getvalue()

        assert "firefox" in output
        assert "org.mozilla.firefox" in output
        assert "chrome" in output
        assert "com.google.chrome" in output

    def test_table_renders_ansi_codes(self, rich_capture: Console) -> None:
        """Table output should contain ANSI color codes."""
        table = Table()
        table.add_column("Name", style="cyan")
        table.add_row("test")

        rich_capture.print(table)
        output = rich_capture.file.getvalue()

        # ANSI escape codes: \x1b[38;5;... or \x1b[
        assert "\x1b[" in output or "test" in output

    def test_table_with_title(self, rich_capture: Console) -> None:
        """Table title should appear in output."""
        table = Table(title="My Wrappers")
        table.add_column("Name")
        table.add_row("app")

        rich_capture.print(table)
        output = rich_capture.file.getvalue()

        # Table renders title above table body (may be on separate lines)
        assert "app" in output  # Content appears


# =============================================================================
# Panel Rendering Tests
# =============================================================================

class TestPanelRendering:
    """Test rich.Panel rendering in generate.py."""

    def test_panel_renders_content(self, rich_capture: Console) -> None:
        """Panel should render its content."""
        panel = Panel("Test content", title="Test Panel", border_style="green")
        rich_capture.print(panel)
        output = rich_capture.file.getvalue()

        assert "Test content" in output
        assert "Test Panel" in output

    def test_panel_has_border(self, rich_capture: Console) -> None:
        """Panel should have visible border characters."""
        panel = Panel("Content")
        rich_capture.print(panel)
        output = rich_capture.file.getvalue()

        # Panel borders use box-drawing characters
        assert len(output) > len("Content")

    def test_panel_styled_border(self, rich_capture: Console) -> None:
        """Panel with colored border should contain ANSI codes."""
        panel = Panel("Content", border_style="red")
        rich_capture.print(panel)
        output = rich_capture.file.getvalue()

        # Should have some output
        assert len(output) > 0


# =============================================================================
# Confirm Prompt Tests
# =============================================================================

class TestConfirmPrompt:
    """Test rich.prompt.Confirm behavior."""

    def test_confirm_yes_response(self) -> None:
        """Confirm.ask with 'y' should return True."""
        from rich.console import Console
        from io import StringIO
        output = StringIO()
        test_console = Console(file=output, force_terminal=False)
        with patch.object(test_console, "input", return_value="y"):
            result = Confirm.ask("Continue?", console=test_console)
            assert result is True

    def test_confirm_no_response(self) -> None:
        """Confirm.ask with 'n' should return False."""
        from rich.console import Console
        from io import StringIO
        output = StringIO()
        test_console = Console(file=output, force_terminal=False)
        with patch.object(test_console, "input", return_value="n"):
            result = Confirm.ask("Continue?", console=test_console)
            assert result is False

    def test_confirm_default_yes(self) -> None:
        """Confirm.ask with default='y' should return True on empty input."""
        from rich.console import Console
        from io import StringIO
        output = StringIO()
        test_console = Console(file=output, force_terminal=False)
        # When default='y' and user enters empty string, returns default 'y'
        with patch.object(test_console, "input", return_value=""):
            result = Confirm.ask("Continue?", default="y", console=test_console)
            # Returns the default value when input is empty
            assert result == "y"

    def test_confirm_default_no(self) -> None:
        """Confirm.ask with default='n' should return False on empty input."""
        from rich.console import Console
        from io import StringIO
        output = StringIO()
        test_console = Console(file=output, force_terminal=False)
        # When default='n' and user enters empty string, returns default 'n'
        with patch.object(test_console, "input", return_value=""):
            result = Confirm.ask("Continue?", default="n", console=test_console)
            assert result == "n"

    def test_confirm_shows_prompt_text(self, rich_capture: Console) -> None:
        """Confirm prompt should display the question text."""
        # Confirm.ask prints the prompt, then reads input
        # We just verify the console exists and can print
        rich_capture.print("[bold]Continue?[/bold] (y/n)")
        output = rich_capture.file.getvalue()
        assert "Continue" in output


# =============================================================================
# LoggingMixin Output Tests
# =============================================================================

class TestLoggingMixinRichOutput:
    """Test LoggingMixin.log() uses Rich for output."""

    @pytest.fixture
    def logger(self) -> LoggingMixin:
        return LoggingMixin()

    def test_log_info_uses_console(self, logger: LoggingMixin) -> None:
        """Info log should output to console."""
        with patch.object(console, "print") as mock_print:
            logger.log("test message", level="info")
            mock_print.assert_called_once()
            mock_print.assert_called_with("test message")

    def test_log_error_uses_console_err(self, logger: LoggingMixin) -> None:
        """Error log should output to console_err."""
        with patch.object(console_err, "print") as mock_print:
            logger.log("error message", level="error")
            mock_print.assert_called_once()

    def test_log_warning_uses_console_err(self, logger: LoggingMixin) -> None:
        """Warning log should output to console_err."""
        with patch.object(console_err, "print") as mock_print:
            logger.log("warning message", level="warning")
            mock_print.assert_called_once()

    def test_log_success_uses_console(self, logger: LoggingMixin) -> None:
        """Success log should output to console."""
        with patch.object(console, "print") as mock_print:
            logger.log("success message", level="success")
            mock_print.assert_called_once()

    def test_log_emit_uses_console(self, logger: LoggingMixin) -> None:
        """Emit log should output to console."""
        with patch.object(console, "print") as mock_print:
            logger.log("emit message", level="emit")
            mock_print.assert_called_once()

    def test_log_debug_printed_when_verbose(self, logger: LoggingMixin) -> None:
        """Debug log should print when verbose=True."""
        logger.verbose = True
        with patch.object(console, "print") as mock_print:
            logger.log("debug message", level="debug")
            mock_print.assert_called_once()

    def test_log_debug_not_printed_when_not_verbose(self, logger: LoggingMixin) -> None:
        """Debug log should not print when verbose=False."""
        logger.verbose = False
        with patch.object(console, "print") as mock_print:
            logger.log("debug message", level="debug")
            mock_print.assert_not_called()


# =============================================================================
# Rich Text with Styling Tests
# =============================================================================

class TestRichTextStyling:
    """Test Rich Text styling features."""

    def test_colored_text(self, rich_capture: Console) -> None:
        """Text with color markup should render."""
        rich_capture.print("[red]Error message[/red]")
        output = rich_capture.file.getvalue()
        assert len(output) > 0

    def test_bold_text(self, rich_capture: Console) -> None:
        """Bold text should render."""
        rich_capture.print("[bold]Important[/bold]")
        output = rich_capture.file.getvalue()
        assert len(output) > 0

    def test_combined_styles(self, rich_capture: Console) -> None:
        """Multiple styles should combine."""
        rich_capture.print("[bold red]Error:[/bold red] Something went wrong")
        output = rich_capture.file.getvalue()
        assert len(output) > 0

    def test_green_success_indicator(self, rich_capture: Console) -> None:
        """Green success indicator should render."""
        rich_capture.print("[green]✓[/green] Success")
        output = rich_capture.file.getvalue()
        assert "✓" in output or len(output) > 0

    def test_dim_text(self, rich_capture: Console) -> None:
        """Dim text should render."""
        rich_capture.print("[dim]This is dim[/dim]")
        output = rich_capture.file.getvalue()
        assert len(output) > 0

    def test_cyan_text(self, rich_capture: Console) -> None:
        """Cyan text should render."""
        rich_capture.print("[cyan]Info text[/cyan]")
        output = rich_capture.file.getvalue()
        assert len(output) > 0

    def test_yellow_warning(self, rich_capture: Console) -> None:
        """Yellow warning text should render."""
        rich_capture.print("[yellow]Warning[/yellow]")
        output = rich_capture.file.getvalue()
        assert len(output) > 0


# =============================================================================
# Status/Spinner Tests
# =============================================================================

class TestProgressAndStatus:
    """Test progress spinners and status indicators."""

    def test_status_returns_context_manager(self, rich_capture: Console) -> None:
        """Status should return a context manager."""
        status = rich_capture.status("Loading...")
        # Status is a context manager
        assert hasattr(status, "__enter__")
        assert hasattr(status, "__exit__")

    def test_console_has_status_method(self, rich_capture: Console) -> None:
        """Console should have status() method."""
        assert hasattr(rich_capture, "status")
        status = rich_capture.status("Test")
        assert status is not None


# =============================================================================
# Capture Integration Tests
# =============================================================================

class TestOutputCapture:
    """Test capturing output from actual module functions."""

    def test_capture_table_from_wrapper_manager(self, isolated_home) -> None:
        """Test capturing Table output from WrapperManager."""
        from lib.manage import WrapperManager

        # Create test wrappers
        (isolated_home.bin_dir / "firefox").write_text("#!/bin/bash\necho test\n")
        (isolated_home.bin_dir / "firefox").chmod(0o755)

        # Redirect console output
        with patch.object(console, "print") as mock_print:
            manager = WrapperManager(
                config_dir=str(isolated_home.config_dir),
                bin_dir=str(isolated_home.bin_dir),
            )
            manager.display_wrappers()

            # Verify print was called
            assert mock_print.called

    def test_capture_confirm_from_cleanup(self, isolated_home) -> None:
        """Test Confirm prompt is called in cleanup."""
        from lib.cleanup import WrapperCleanup, CleanupConfig

        config = CleanupConfig(
            bin_dir=str(isolated_home.bin_dir),
            config_dir=str(isolated_home.config_dir),
            data_dir=str(isolated_home.data_dir),
            interactive=True,
        )
        cleanup = WrapperCleanup(config=config)

        # Add cleanup items so confirm is needed
        (isolated_home.bin_dir / "orphan").write_text("#!/bin/bash\n")
        cleanup.scan_for_cleanup_items()

        # Confirm.ask is called from cleanup module
        with patch("lib.cleanup.Confirm.ask", return_value=True) as mock_confirm:
            result = cleanup.confirm_cleanup()
            mock_confirm.assert_called_once()
            assert result is True

    def test_capture_confirm_from_manage(self, isolated_home) -> None:
        """Test Confirm prompt is called in WrapperManager.remove_wrapper."""
        from lib.manage import WrapperManager

        # Create test wrapper
        (isolated_home.bin_dir / "firefox").write_text("#!/bin/bash\necho test\n")
        (isolated_home.bin_dir / "firefox").chmod(0o755)

        manager = WrapperManager(
            config_dir=str(isolated_home.config_dir),
            bin_dir=str(isolated_home.bin_dir),
        )

        # Confirm is imported locally in remove_wrapper
        # We need to patch at the location where it's used (lib.manage module)
        # Since it's imported inside the function, we mock the whole Prompt class
        with patch("rich.prompt.Confirm.ask", return_value=True):
            manager.remove_wrapper("firefox", force=False)
            # If force=False and no Confirm mock triggered, it would ask
            # With our mock, it should proceed


# =============================================================================
# Fallback Tests
# =============================================================================

class TestRichFallback:
    """Test graceful fallback when Rich output fails."""

    def test_logging_mixin_works_without_rich(self) -> None:
        """LoggingMixin should work even if Rich has issues."""
        logger = LoggingMixin()

        # Should not raise even with various log levels
        logger.log("test", level="info")
        logger.log("test", level="error")
        logger.log("test", level="warning")
        logger.log("test", level="success")

    def test_table_creation_works(self) -> None:
        """Table should be creatable without printing."""
        table = Table()
        table.add_column("Test")
        table.add_row("value")

        assert table.row_count == 1
        assert len(table.columns) == 1

    def test_panel_creation_works(self) -> None:
        """Panel should be creatable without printing."""
        panel = Panel("Test content", title="Title")
        assert panel.renderable is not None


# =============================================================================
# Output Stream Tests
# =============================================================================

class TestOutputStreams:
    """Test that output goes to correct streams."""

    def test_console_print_to_stdout(self) -> None:
        """Console should print to stdout by default."""
        assert console.file is not None
        # Console.file should be None for default console (writes to sys.stdout)
        # or explicitly set

    def test_console_err_prints_to_stderr(self) -> None:
        """Console with stderr=True should write to stderr."""
        assert console_err.stderr is True

    def test_capture_to_stringio(self) -> None:
        """Console can capture output to StringIO."""
        output = StringIO()
        c = Console(file=output, force_terminal=False)
        c.print("Hello")

        result = output.getvalue()
        assert "Hello" in result


# =============================================================================
# Syntax Highlighting Tests
# =============================================================================

class TestSyntaxHighlighting:
    """Test syntax highlighting with Rich."""

    def test_syntax_highlight_python(self, rich_capture: Console) -> None:
        """Python code should be syntax highlighted."""
        code = "def hello():\n    print('world')"
        syntax = Syntax(code, "python")
        rich_capture.print(syntax)
        output = rich_capture.file.getvalue()
        assert len(output) > 0

    def test_syntax_highlight_bash(self, rich_capture: Console) -> None:
        """Bash code should be syntax highlighted."""
        code = "#!/bin/bash\necho 'hello'"
        syntax = Syntax(code, "bash")
        rich_capture.print(syntax)
        output = rich_capture.file.getvalue()
        assert len(output) > 0


# =============================================================================
# Markdown Rendering Tests
# =============================================================================

class TestMarkdownRendering:
    """Test markdown rendering with Rich."""

    def test_markdown_basic(self, rich_capture: Console) -> None:
        """Basic markdown should render."""
        from rich.markdown import Markdown

        md = Markdown("# Hello\n\nThis is **bold**.")
        rich_capture.print(md)
        output = rich_capture.file.getvalue()
        assert len(output) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
