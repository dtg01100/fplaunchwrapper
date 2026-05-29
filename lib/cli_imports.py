#!/usr/bin/env python3
"""Shared import utilities for CLI modules."""

from lib.cli_utils import console, console_err  # noqa: E402
from lib.import_utils import ImportErrorHandler

import_handler = ImportErrorHandler(console_err)

# Re-export run_command from cli_utils for backward compatibility
from lib.cli_utils import run_command  # noqa: E402, F401
