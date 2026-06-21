"""Lock-in tests: invalid CLI input produces clean errors, no tracebacks.

Every entry point MUST handle invalid input gracefully:
  * Exit code is non-zero (typically 1 or 2).
  * No Python traceback appears in stdout/stderr.
  * The user sees a useful error message (e.g. "No such command 'foo'.").
  * The process terminates promptly (<10s).
  * No uncaught exception bubbles out of main().

These tests are a contract: any future change that introduces a
traceback leak or hang on bad input will fail here.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from lib.cli import cli

PROJECT_ROOT = Path(__file__).parent.parent.parent


# --- Helpers ----------------------------------------------------------------

def _has_traceback(text: str) -> bool:
    """Detect Python's literal traceback marker (not the word 'Traceback' in prose)."""
    return "Traceback (most recent call last):" in text


def _run_subprocess(module: str, args: list[str], env: dict | None = None) -> dict:
    """Run a CLI command as a subprocess and return diagnostics."""
    cmd = [sys.executable, "-m", module, *args]
    base_env = os.environ.copy()
    base_env["HOME"] = "/tmp/fplaunch_invalid_test"
    base_env["XDG_CONFIG_HOME"] = "/tmp/fplaunch_invalid_test/.config"
    base_env["XDG_DATA_HOME"] = "/tmp/fplaunch_invalid_test/.local/share"
    base_env["XDG_CACHE_HOME"] = "/tmp/fplaunch_invalid_test/.cache"
    base_env["FPWRAPPER_TEST_ENV"] = "1"
    base_env["PYTHONPATH"] = str(PROJECT_ROOT)
    if env:
        base_env.update(env)

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            env=base_env, cwd=str(PROJECT_ROOT),
        )
        return {
            "exit": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "combined": result.stdout + result.stderr,
            "elapsed": time.monotonic() - start,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit": -1, "stdout": "", "stderr": "",
            "combined": "", "elapsed": time.monotonic() - start,
            "hung": True,
        }


# --- Core invariant tests (in-process via Click's CliRunner) ----------------

class TestNoTracebackOnInvalidInput:
    """Invalid subcommands and options must not produce Python tracebacks."""

    def setup_method(self):
        self.runner = CliRunner()

    @pytest.mark.parametrize("args", [
        ["nonexistent-command"],
        ["--unknown-top-level-flag"],
        ["-Z"],  # unknown short flag
        ["list", "--bogus"],  # unknown flag on a real subcommand
        ["presets", "unknown-action"],
        ["profiles", "unknown"],
        ["systemd", "unknown"],
        ["config", "unknown"],
        ["systemd", "start", "extra-positional"],  # too many args
        ["config", "init", "extra-positional"],
    ])
    def test_no_traceback_in_output(self, args):
        """Every invalid invocation must produce no Python traceback."""
        result = self.runner.invoke(cli, args, catch_exceptions=False)
        combined = result.output  # CliRunner merges stdout+stderr

        assert not _has_traceback(combined), (
            f"Invalid input {args!r} leaked a Python traceback:\n{combined[:1000]}"
        )

    @pytest.mark.parametrize("args", [
        ["nonexistent-command"],
        ["--unknown-top-level-flag"],
        ["presets", "unknown-action"],
        ["config", "unknown"],
    ])
    def test_nonzero_exit_on_invalid_input(self, args):
        """Invalid input must exit non-zero (typically 2 for Click usage errors)."""
        result = self.runner.invoke(cli, args, catch_exceptions=False)
        assert result.exit_code != 0, (
            f"Invalid input {args!r} unexpectedly exited 0\n{result.output[:500]}"
        )

    @pytest.mark.parametrize("args", [
        ["nonexistent-command"],
        ["--unknown-flag"],
        ["list", "--bogus"],
        ["presets", "unknown"],
    ])
    def test_helpful_error_message_present(self, args):
        """Error output should include a human-readable error (not just exception name)."""
        result = self.runner.invoke(cli, args, catch_exceptions=False)
        combined_lower = result.output.lower()
        assert (
            "error" in combined_lower
            or "usage" in combined_lower
            or "no such" in combined_lower
        ), f"No helpful message for {args!r}:\n{result.output[:500]}"


# --- Subprocess-level tests (real entry points, not CliRunner) ---------------

class TestEntryPointsHandleInvalidInput:
    """Every pyproject entry point must handle invalid input without traceback."""

    # Entry points that use argparse have a quirk: a stray word as
    # positional arg may be interpreted as a [bin_dir] path. The system
    # detects suspicious paths ("resolves outside home directory") and
    # falls back to a safe default. Not a bug, by design.
    ENTRY_POINTS = [
        ("lib.fplaunch", "fplaunch"),  # Click
        ("lib.cli", "fplaunch-cli"),  # Click
        ("lib.manage", "fplaunch-manage"),  # argparse
        ("lib.launch", "fplaunch-launch"),  # argparse
        ("lib.cleanup", "fplaunch-cleanup"),  # argparse
        ("lib.systemd_setup", "fplaunch-setup-systemd"),  # argparse
        ("lib.config_manager", "fplaunch-config"),  # argparse
        ("lib.flatpak_monitor", "fplaunch-monitor"),  # argparse
    ]
    @pytest.mark.parametrize("module,binary", ENTRY_POINTS)
    @pytest.mark.parametrize("args", [
        ["--unknown-flag"],
        ["nonexistent-subcommand"],
    ])
    def test_entry_point_no_traceback(self, module, binary, args):
        """Real subprocess invocation: no traceback on invalid input."""
        r = _run_subprocess(module, args)
        assert not r.get("hung", False), f"{binary} {args} hung > 10s"
        assert not _has_traceback(r["combined"]), (
            f"{binary} {' '.join(args)} leaked traceback:\n"
            f"stdout={r['stdout'][:300]!r}\nstderr={r['stderr'][:300]!r}"
        )
        assert r["exit"] != 0, (
            f"{binary} {' '.join(args)} exited 0 on invalid input\n"
            f"{r['combined'][:500]}"
        )


# --- Pathological inputs ----------------------------------------------------

class TestPathologicalInputHandled:
    """Inputs at the edge of validity: very long, unusual chars, etc."""

    def setup_method(self):
        self.runner = CliRunner()

    @pytest.mark.parametrize("args", [
        ["list", "a" * 1000],      # very long name
        ["launch", "a" * 1000],    # very long name
        ["launch", "org.foo" * 100],
        ["launch", "org..foo..app"],  # consecutive dots
        ["launch", "org.foo.bar; rm -rf /"],  # shell metacharacters
        ["launch", "org.foo.bar\nrm -rf /"],  # embedded newline
        ["launch", ""],            # empty
        ["launch", " "],           # whitespace
        ["launch", "-invalid"],     # starts with dash
        ["list", "\t\n"],          # control chars
    ])
    def test_no_crash_on_pathological(self, args):
        """Even pathological inputs must produce a clean error, never a crash."""
        result = self.runner.invoke(cli, args, catch_exceptions=False)
        # No traceback
        assert not _has_traceback(result.output), (
            f"Pathological {args!r} leaked traceback:\n{result.output[:800]}"
        )
        # CliRunner would raise if main() raised uncaught.

    def test_long_running_subprocess_terminates(self):
        """Real subprocess for a pathological launch input must terminate in <10s."""
        r = _run_subprocess("lib.fplaunch", ["launch", "org.foo.bar" * 100])
        assert not r.get("hung", False), (
            f"fplaunch launch hung on pathological input. exit={r['exit']}"
        )
        assert r["elapsed"] < 10, (
            f"fplaunch launch too slow: {r['elapsed']:.1f}s"
        )


# --- Regression: previously leaking traceback ------------------------------

class TestRegressionBugE1:
    """Regression: fplaunch and fplaunch-cli previously leaked tracebacks.

    Originally, lib.cli_commands.main() caught all exceptions and called
    logger.exception() which dumps the full Python traceback. This
    produced scary output for users with simple typos.
    """

    def test_fplaunch_no_traceback_on_typo(self):
        r = _run_subprocess("lib.fplaunch", ["garbage-command"])
        assert not _has_traceback(r["combined"]), (
            f"fplaunch leaked traceback on 'garbage-command':\n{r['combined'][:1000]}"
        )
        assert r["exit"] != 0

    def test_fplaunch_no_traceback_on_unknown_flag(self):
        r = _run_subprocess("lib.fplaunch", ["--no-such-flag"])
        assert not _has_traceback(r["combined"]), (
            f"fplaunch leaked traceback on '--no-such-flag':\n{r['combined'][:1000]}"
        )
        assert r["exit"] != 0

    def test_fplaunch_cli_no_traceback_on_typo(self):
        r = _run_subprocess("lib.cli", ["garbage-command"])
        assert not _has_traceback(r["combined"]), (
            f"fplaunch-cli leaked traceback on 'garbage-command':\n{r['combined'][:1000]}"
        )
        assert r["exit"] != 0

    def test_cli_main_returns_proper_exit_code(self):
        """main() should return non-zero for invalid input, never 0."""
        from lib.cli_commands import main as cli_main
        old = sys.argv
        try:
            sys.argv = ["fplaunch", "garbage"]
            rc = cli_main()
        finally:
            sys.argv = old
        assert rc != 0
