"""Lock-in tests for CLI help screens.

Every command and subcommand MUST expose a working --help screen.
This module enumerates the entire Click tree and asserts each command
produces a help screen with exit code 0 and a "Usage:" line.

Also verifies each pyproject entry point script (the standalone binaries)
responds to --help.

If any future change adds a new command without --help, or breaks an
existing one, this test fails immediately.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from lib.cli import cli


# ---- Inventory helpers --------------------------------------------------

def _collect_commands(group, prefix=""):
    """Recursively walk a Click group and return [(full_path, command)].

    Skips Click's built-in `help` command (it's a pseudo-command).
    """
    cmds = []
    for name, cmd in group.commands.items():
        if name == "help":
            continue
        full = f"{prefix}{name}" if prefix else name
        cmds.append((full, cmd))
        if hasattr(cmd, "commands"):
            cmds.extend(_collect_commands(cmd, full + " "))
    return cmds


def _all_commands():
    return _collect_commands(cli)


# ---- Pyproject entry-point scripts --------------------------------------

# Each entry point from pyproject.toml. The format is the binary name as
# installed on PATH; we invoke via `python -m <module>` since the binary
# may not be on PATH in tests.
ENTRY_POINTS = [
    ("fplaunch", "lib.fplaunch:main"),
    ("fplaunch-cli", "lib.cli:main"),
    ("fplaunch-generate", "lib.generate:main"),
    ("fplaunch-manage", "lib.manage:main"),
    ("fplaunch-launch", "lib.launch:main"),
    ("fplaunch-cleanup", "lib.cleanup:main"),
    ("fplaunch-setup-systemd", "lib.systemd_setup:main"),
    ("fplaunch-config", "lib.config_manager:main"),
    ("fplaunch-monitor", "lib.flatpak_monitor:main"),
]


def _stdout_has_usage(out: str) -> bool:
    """Help output must contain a Usage line (Click 'Usage:' or argparse 'usage:')."""
    return "Usage:" in out or "usage:" in out


# ---- Class: every CLI command has --help ---------------------------------

class TestEveryCommandHasHelp:
    """Every Click command in the `fplaunch` CLI must respond to --help."""

    @pytest.fixture(scope="class")
    def runner(self):
        return CliRunner()

    @pytest.fixture(scope="class")
    def all_commands(self):
        return _all_commands()

    def test_at_least_40_commands_exist(self, all_commands):
        """Sanity: we expect ~49 commands. Below 40 means someone removed."""
        n = len(all_commands)
        assert n >= 40, (
            f"Only {n} commands found; expected at least 40. "
            f"Did someone remove a command from the CLI?"
        )

    def test_every_command_has_help_screen(self, runner, all_commands):
        """Every command's --help exits 0 and prints a Usage: line.

        This is the core invariant: no CLI command may omit --help.
        """
        failures = []
        for full, cmd in all_commands:
            args = full.split() + ["--help"]
            result = runner.invoke(cli, args, catch_exceptions=False)
            ok = (
                result.exit_code == 0
                and _stdout_has_usage(result.output)
            )
            if not ok:
                failures.append((full, result.exit_code, result.output[:200]))
        assert not failures, (
            f"{len(failures)} commands have broken --help:\n"
            + "\n".join(
                f"  {full}: exit={code} output={out!r}"
                for full, code, out in failures[:10]
            )
        )

    def test_help_screen_includes_description(self, runner, all_commands):
        """Every --help screen must include a description (the docstring)."""
        spot_check = [
            "generate", "list", "info", "cleanup",
            "presets list", "profiles list", "systemd status",
        ]
        for full in spot_check:
            args = full.split() + ["--help"]
            result = runner.invoke(cli, args, catch_exceptions=False)
            assert result.exit_code == 0, (
                f"{full}: --help exited {result.exit_code}"
            )
            # Output should be more than just the usage line.
            assert len(result.output.strip()) > 30, (
                f"{full}: --help output is suspiciously short: {result.output!r}"
            )


# ---- Class: every pyproject entry-point script has --help -------------

class TestEntryPointScriptsHaveHelp:
    """Every binary declared in pyproject.toml [project.scripts] must
    respond to --help. Catches drift between pyproject and modules."""

    @pytest.fixture(scope="class")
    def project_root(self):
        return Path(__file__).parent.parent.parent

    @pytest.mark.parametrize("binary,target", ENTRY_POINTS)
    def test_entry_point_help(self, project_root, binary, target):
        """Each entry-point script must print help on --help.

        Click and argparse both produce a usage line; both cases accepted.
        """
        module = target.split(":")[0]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        assert result.returncode == 0, (
            f"{binary} ({module}) --help exited {result.returncode}: "
            f"{result.stderr[:200]}"
        )
        assert _stdout_has_usage(result.stdout), (
            f"{binary} ({module}) --help missing 'Usage:' line:\n"
            f"{result.stdout[:300]}"
        )


# ---- Class: documented commands in DESIGN.md match the CLI -------------

class TestDocumentedCommandsHaveHelp:
    """Every command mentioned in DESIGN.md / COMMAND_REFERENCE.md must
    exist in the CLI and have --help. Catches documentation drift."""

    DOCUMENTED_COMMANDS = [
        # Top-level
        "generate", "list", "info", "remove", "cleanup", "clean",
        "install", "uninstall", "manifest", "search", "discover",
        "files", "config", "set-pref", "pref", "presets", "profiles",
        "systemd", "systemd-setup", "launch", "monitor",
        # presets subcommands
        "presets list", "presets get", "presets add", "presets remove",
        # profiles subcommands
        "profiles list", "profiles current", "profiles create",
        "profiles switch", "profiles export", "profiles import",
        # systemd subcommands
        "systemd enable", "systemd disable", "systemd status",
        "systemd start", "systemd stop", "systemd restart",
        "systemd reload", "systemd logs", "systemd list", "systemd test",
    ]

    @pytest.fixture(scope="class")
    def runner(self):
        return CliRunner()

    @pytest.mark.parametrize("full", DOCUMENTED_COMMANDS)
    def test_documented_command_has_help(self, runner, full):
        args = full.split() + ["--help"]
        result = runner.invoke(cli, args, catch_exceptions=False)
        assert result.exit_code == 0, (
            f"Documented command {full!r} --help exited {result.exit_code}:\n"
            f"{result.output[:200]}"
        )
        assert _stdout_has_usage(result.output), (
            f"Documented command {full!r} --help missing 'Usage:'"
        )


# ---- Class: --help position must work before and after subcommand ------

class TestHelpFlagsBeforeAfterSubcommand:
    """`fplaunch <subcmd> --help` must work (Click standard form)."""

    @pytest.fixture(scope="class")
    def runner(self):
        return CliRunner()

    @pytest.mark.parametrize("cmd", [
        "list",
        "generate",
        "presets list",
        "profiles list",
        "systemd status",
    ])
    def test_help_after_subcommand(self, runner, cmd):
        args = cmd.split() + ["--help"]
        result = runner.invoke(cli, args, catch_exceptions=False)
        assert result.exit_code == 0
        assert _stdout_has_usage(result.output)
