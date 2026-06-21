#!/usr/bin/env python3
"""Shared import utilities for CLI modules."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from lib.cli_utils import console, console_err  # noqa: E402,F401,E501  (re-export for cli/presets/profiles)
from lib.import_utils import ImportErrorHandler

# Shared import-handler used by every CLI module. Centralized here so test
# patches (and runtime overrides) only need to touch a single instance.
import_handler = ImportErrorHandler(console_err)

# Re-export run_command from cli_utils for backward compatibility
from lib.cli_utils import run_command  # noqa: E402,F401

__all__ = [
    "build_config_manager",
    "build_manager",
    "console",
    "console_err",
    "get_config_manager",
    "import_handler",
    "run_command",
]

if TYPE_CHECKING:
    from click import Context
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


def get_config_manager(config_dir: str | Path | None = None):
    """Return a config manager instance via lazy import.

    Replaces the three-line ``import_handler.require`` /
    ``create_config_manager()`` boilerplate previously repeated in every
    profile and preset command.

    Args:
        config_dir: Optional override for the configuration directory.
            When ``None`` the XDG default is used.
    """
    create_config_manager = import_handler.require(
        "lib.config_manager",
        "create_config_manager",
    )
    return create_config_manager(config_dir=config_dir)


def build_config_manager(ctx: "Context"):
    """Build a config manager from a Click context.

    Reads ``config_dir`` and the active profile name from ``ctx.obj``
    and constructs an :class:`EnhancedConfigManager` that honours both.
    Use this from Click commands that take ``--config-dir`` so the
    override actually reaches the manager.
    """
    config_dir = ctx.obj.get("config_dir")
    return get_config_manager(config_dir=config_dir)
