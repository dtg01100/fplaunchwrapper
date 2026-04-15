#!/usr/bin/env python3
"""Shared logging utilities for fplaunchwrapper.

Provides LoggingMixin base class and Console setup for consistent
logging behavior across all modules.
"""

from __future__ import annotations

from rich.console import Console as _Console

# Console instances for consistent output
console = _Console()
console_err = _Console(stderr=True)


class LoggingMixin:
    """Mixin class providing standardized logging for all components.

    Subclasses get a log() method that outputs to stdout/stderr based on level.
    """

    verbose: bool = False
    emit_mode: bool = False
    emit_verbose: bool = False

    def log(self, message: str, level: str = "info") -> None:
        """Log a message to stdout or stderr based on level.

        Args:
            message: The message to log
            level: Log level - "error", "warning", "success", "emit", "info", "debug"
                   - error/warning: goes to stderr
                   - success/emit/info/debug: goes to stdout
        """
        # Skip debug if not verbose
        if not self.verbose and level == "debug":
            return

        if level == "error":
            console_err.print(f"[red]ERROR:[/red] {message}")
        elif level == "warning":
            console_err.print(f"[yellow]WARN:[/yellow] {message}")
        elif level == "success":
            console.print(f"[green]✓[/green] {message}")
        elif level == "emit":
            console.print(f"[blue]EMIT:[/blue] {message}")
        elif level == "debug":
            console.print(f"[dim]{message}[/dim]")
        else:
            console.print(message)
