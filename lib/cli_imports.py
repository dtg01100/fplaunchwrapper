#!/usr/bin/env python3
"""Shared import utilities for CLI modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lib.cli_utils import console, console_err  # noqa: E402  (used by ImportErrorHandler)
from lib.import_utils import ImportErrorHandler

# Shared import-handler used by every CLI module. Centralized here so test
# patches (and runtime overrides) only need to touch a single instance.
import_handler = ImportErrorHandler(console_err)

# Re-export run_command from cli_utils for backward compatibility
from lib.cli_utils import run_command  # noqa: E402, F401

if TYPE_CHECKING:
    from click import Context
    from lib.manage import WrapperManager
    from typing import Any


def build_manager(ctx: Context) -> Any:
    """Build a WrapperManager from a Click context.

    Reads ``config_dir``, ``verbose``, ``emit_mode`` and ``emit_verbose``
    from ``ctx.obj`` and constructs a :class:`WrapperManager` via lazy
    import. This consolidates the four-argument instantiation pattern
    that was previously duplicated across every CLI command.

    Args:
        ctx: The active Click context.

    Returns:
        A fully-configured ``WrapperManager`` instance.
    """
    WrapperManager = import_handler.require("lib.manage", "WrapperManager")
    return WrapperManager(
        config_dir=ctx.obj.get("config_dir"),
        verbose=ctx.obj.get("verbose", False),
        emit_mode=ctx.obj.get("emit", False),
        emit_verbose=ctx.obj.get("emit_verbose", False),
    )


def get_config_manager():
    """Return a config manager instance via lazy import.

    Replaces the three-line ``import_handler.require`` /
    ``create_config_manager()`` boilerplate previously repeated in every
    profile and preset command.
    """
    create_config_manager = import_handler.require(
        "lib.config_manager",
        "create_config_manager",
    )
    return create_config_manager()
