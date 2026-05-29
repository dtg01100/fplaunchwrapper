#!/usr/bin/env python3
"""Modern CLI interface for fplaunchwrapper using Click.

All CLI commands return int for shell exit codes:
- 0: Success
- 1: Failure
"""

from __future__ import annotations

from lib.cli_commands import cli, main
from lib.cli_utils import run_command, find_fplaunch_script

# Re-export console and import_handler for backward compatibility with tests
from lib.cli_commands import console, console_err, import_handler

# For backward compatibility, also expose individual commands from submodules
from lib.cli_generation import (
    generate,
    list_wrappers,
    install,
    uninstall,
    remove,
    rm,
    set_pref,
    pref,
)
from lib.cli_system import (
    launch,
    cleanup,
    clean,
    monitor,
)
from lib.cli_systemd import (
    systemd_setup_cmd,
    systemd_group,
    systemd_enable,
    systemd_disable,
    systemd_status,
    systemd_start,
    systemd_stop,
    systemd_restart,
    systemd_reload,
    systemd_logs,
    systemd_list,
    systemd_test,
)
from lib.cli_profiles import (
    profiles_group,
    profiles_list,
    profiles_create,
    profiles_switch,
    profiles_current,
    profiles_export,
    profiles_import,
)
from lib.cli_presets import (
    presets_group,
    presets_list,
    presets_get,
    presets_add,
    presets_remove,
)
from lib.cli_utils_cmd import (
    info,
    search,
    discover,
    files,
    manifest,
    config,
)

__all__ = [
    # Main CLI
    "cli",
    "main",
    # Utilities (including run_command for backward compatibility)
    "run_command",
    "find_fplaunch_script",
    "console",
    "console_err",
    "import_handler",
    # Generation commands
    "generate",
    "list_wrappers",
    "install",
    "uninstall",
    "remove",
    "rm",
    "set_pref",
    "pref",
    # System commands
    "launch",
    "cleanup",
    "clean",
    "monitor",
    # Systemd commands
    "systemd_setup_cmd",
    "systemd_group",
    "systemd_enable",
    "systemd_disable",
    "systemd_status",
    "systemd_start",
    "systemd_stop",
    "systemd_restart",
    "systemd_reload",
    "systemd_logs",
    "systemd_list",
    "systemd_test",
    # Profiles commands
    "profiles_group",
    "profiles_list",
    "profiles_create",
    "profiles_switch",
    "profiles_current",
    "profiles_export",
    "profiles_import",
    # Presets commands
    "presets_group",
    "presets_list",
    "presets_get",
    "presets_add",
    "presets_remove",
    # Utility commands
    "info",
    "search",
    "discover",
    "files",
    "manifest",
    "config",
]


if __name__ == "__main__":
    raise SystemExit(main())
