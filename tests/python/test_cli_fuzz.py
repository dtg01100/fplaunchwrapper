#!/usr/bin/env python3
"""Fuzz tests for CLI using Hypothesis property-based testing."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


import pytest
from hypothesis import given, settings, HealthCheck, strategies as st


@st.composite
def cli_string_strategy(draw) -> str:
    """Generate various string inputs for CLI fuzzing."""
    return draw(
        st.sampled_from(
            [
                "",
                "a",
                "ab",
                "abc",
                "x" * 10,
                "x" * 50,
                "x" * 100,
                "x" * 255,
                "x" * 1000,
                "hello world",
                "hello\tworld",
                'hello"world',
                "hello'world",
                "hello;world",
                "hello|world",
                "hello&world",
                "hello$world",
                "hello世界",
                "Привет",
                "café",
                "naïve",
                "\u200b",
                "\ufeff",
                "../../../etc/passwd",
                "../" * 10 + "etc/passwd",
                "/etc/passwd",
                "'; DROP TABLE users; --",
                "<script>alert('xss')</script>",
                "${env:PATH}",
                "$(whoami)",
                "`id`",
                "file.txt;rm -rf",
                "file.txt|cat",
                "file.txt&&echo",
                "\x7f\x80\xff",
                "😀" * 10,  # 10 emoji chars (40 bytes) - reasonable limit
                "🏠" * 20,  # 20 emoji chars (80 bytes) - safe limit for path length
            ]
        )
    )


PROJECT_DIR = Path(__file__).parent.parent.parent


def run_cli(*args, home: str | None = None) -> subprocess.CompletedProcess:
    """Run CLI command with isolated environment."""
    cmd = [sys.executable, str(PROJECT_DIR / "lib" / "cli.py")] + list(args)
    env = os.environ.copy()
    env["HOME"] = home or tempfile.mkdtemp()
    env["PYTHONPATH"] = str(PROJECT_DIR)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, env=env, cwd=str(PROJECT_DIR)
        )
    except ValueError:
        result = subprocess.CompletedProcess(cmd, 1, "", "ValueError: embedded null byte")
    return result


def run_cli_inproc(*args, home: str | None = None) -> SimpleNamespace:
    """Run CLI command in-process (no subprocess overhead).

    Captures stdout/stderr by redirecting sys.std{out,err} and
    Console.file/console_err.file to StringIO objects. Returns a
    SimpleNamespace with returncode, stdout, stderr (same shape as
    CompletedProcess for subprocess-based run_cli).
    """
    import click
    import shutil
    from io import StringIO
    from unittest.mock import patch

    from lib import cli as cli_module

    _home = home or tempfile.mkdtemp()
    out_capture = StringIO()
    err_capture = StringIO()

    old_console_file = cli_module.console.file
    old_console_err_file = cli_module.console_err.file
    cli_module.console.file = out_capture
    cli_module.console_err.file = err_capture

    try:
        with (
            patch.dict(os.environ, {"HOME": str(_home)}),
            patch("sys.stdout", out_capture),
            patch("sys.stderr", err_capture),
        ):
            try:
                ret = cli_module.cli(list(args), standalone_mode=False)
                code = ret if ret is not None else 0
            except SystemExit as e:
                code = e.code if e.code is not None else 0
            except click.exceptions.ClickException as e:
                code = e.exit_code
            except click.exceptions.Abort:
                code = 1
    finally:
        cli_module.console.file = old_console_file
        cli_module.console_err.file = old_console_err_file

    if home is None:
        shutil.rmtree(_home, ignore_errors=True)

    return SimpleNamespace(
        returncode=code,
        stdout=out_capture.getvalue(),
        stderr=err_capture.getvalue(),
    )


class TestGenerateCommandFuzz:
    """Fuzz tests for the generate command."""

    def test_generate_help(self):
        """generate --help should work."""
        result = run_cli_inproc("generate", "--help")
        assert result.returncode in (0, 1, 2, 64, 65, 127)

    @given(extra_args=st.lists(cli_string_strategy(), max_size=5))
    @settings(
        max_examples=8, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_generate_with_extra_args(self, extra_args):
        """generate command should reject or handle arbitrary extra args."""
        result = run_cli_inproc("generate", "org.example.App", *extra_args)
        assert result.returncode in (0, 1, 2, 64, 65, 127)


class TestLaunchCommandFuzz:
    """Fuzz tests for the launch command."""

    @given(app_name=cli_string_strategy())
    @settings(
        max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_launch_handles_various_app_names(self, app_name):
        """launch command should handle various app_name formats gracefully."""
        result = run_cli_inproc("launch", app_name)
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "Traceback" not in result.stderr or "NoSuchOption" in result.stderr

    @given(
        app_name=st.text(min_size=1, max_size=100),
        flags=st.lists(
            st.sampled_from(["--abort-on-hook-failure", "--ignore-hook-failure"]), max_size=2
        ),
    )
    @settings(
        max_examples=8, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_launch_with_flags(self, app_name, flags):
        """launch command should handle flags without crashing."""
        result = run_cli_inproc("launch", app_name, *flags)
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "Traceback" not in result.stderr or "NoSuchOption" in result.stderr


class TestRemoveCommandFuzz:
    """Fuzz tests for the remove command."""

    @given(name=cli_string_strategy())
    @settings(
        max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_remove_handles_various_names(self, name):
        """remove command should handle various wrapper names."""
        result = run_cli_inproc("remove", name, "--force")
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "Traceback" not in result.stderr


class TestInstallCommandFuzz:
    """Fuzz tests for the install command."""

    @given(
        app_name=cli_string_strategy(),
        extra_args=st.lists(st.sampled_from(["--force-reinstall", "--no-pull"]), max_size=2),
    )
    @settings(
        max_examples=8, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_install_handles_various_inputs(self, app_name, extra_args):
        """install command should handle various inputs gracefully."""
        result = run_cli_inproc("install", app_name, *extra_args)
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "Traceback" not in result.stderr or "NoSuchOption" in result.stderr


class TestUninstallCommandFuzz:
    """Fuzz tests for the uninstall command."""

    @given(
        app_name=cli_string_strategy(),
        extra_args=st.lists(st.sampled_from(["--remove-data", "--force"]), max_size=2),
    )
    @settings(
        max_examples=8, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_uninstall_handles_various_inputs(self, app_name, extra_args):
        """uninstall command should handle various inputs gracefully."""
        result = run_cli_inproc("uninstall", app_name, *extra_args)
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "Traceback" not in result.stderr or "NoSuchOption" in result.stderr


class TestInfoCommandFuzz:
    """Fuzz tests for the info command."""

    @given(app_name=st.text(max_size=50).filter(lambda x: x and not x.startswith("-")))
    @settings(
        max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_info_handles_various_app_names(self, app_name):
        """info command should handle various inputs."""
        result = run_cli_inproc("info", app_name)
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "Traceback" not in result.stderr


class TestConfigCommandFuzz:
    """Fuzz tests for the config command."""

    @given(
        subcommand=st.sampled_from(["get", "set", "list", "edit", "reset"]),
        key=st.text(min_size=1, max_size=50).filter(lambda x: not x.startswith("-")),
        value=st.one_of(st.none(), cli_string_strategy()),
    )
    @settings(
        max_examples=8, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_config_subcommands(self, subcommand, key, value):
        """config subcommands should handle various inputs gracefully."""
        args = ["config", subcommand]
        if subcommand in ("get", "list"):
            args.append(key)
        elif subcommand in ("set",):
            args.append(key)
            if value:
                args.append(value)
        result = run_cli_inproc(*args)
        assert result.returncode in (0, 1, 2, 64, 127)
        assert (
            "Traceback" not in result.stderr
            or "UsageError" in result.stderr
            or "NoSuchOption" in result.stderr
        )


class TestSetPrefCommandFuzz:
    """Fuzz tests for set-pref command."""

    @given(
        app_name=cli_string_strategy(),
        preference=st.sampled_from(["system", "user", "default", "auto"]),
    )
    @settings(
        max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_set_pref_handles_various_inputs(self, app_name, preference):
        """set-pref command should handle various inputs."""
        result = run_cli_inproc("set-pref", app_name, preference)
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "Traceback" not in result.stderr


class TestGlobalOptionsFuzz:
    """Fuzz tests for global CLI options."""

    @given(
        args=st.lists(
            st.sampled_from(["--verbose", "-v", "--emit", "--help", "--version"]), max_size=4
        )
    )
    @settings(
        max_examples=8, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_global_options(self, args):
        """Global options should not cause crashes."""
        result = run_cli_inproc(*args)
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "Traceback" not in result.stderr

    def test_help_for_each_command(self):
        """Each command's --help should work."""
        for command in ["generate", "launch", "remove", "list"]:
            result = run_cli_inproc(command, "--help")
            assert result.returncode == 0
            assert "usage:" in result.stdout.lower()
            assert "Traceback" not in result.stderr


class TestCLIEdgeCases:
    """Test specific edge cases."""

    def test_empty_arguments(self):
        """CLI should handle empty argument list gracefully."""
        result = run_cli_inproc()
        assert result.returncode in (0, 1, 64, 127)
        assert "Traceback" not in result.stderr

    def test_null_bytes_in_arguments(self):
        """CLI should not crash on null bytes."""
        result = run_cli_inproc("launch", "org\x00.example")
        assert result.returncode in (0, 1, 2, 64, 127)

    def test_very_long_arguments(self):
        """CLI should handle very long arguments."""
        long_arg = "x" * 10000
        result = run_cli_inproc("launch", long_arg)
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "Traceback" not in result.stderr

    def test_unicode_in_arguments(self):
        """CLI should handle unicode in arguments."""
        result = run_cli_inproc("launch", "org.example.世界")
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "UnicodeError" not in result.stderr

    def test_path_traversal_is_sanitized(self):
        """CLI should sanitize path traversal attempts."""
        for args in [["launch", "../../../etc/passwd"], ["generate", "../../../etc/passwd"]]:
            result = run_cli_inproc(*args)
            assert result.returncode in (0, 1, 2, 64, 127)
            if result.returncode == 0:
                assert "/etc/passwd" not in result.stdout or "Warning" in result.stderr

    def test_shell_injection_attempts(self):
        """CLI should be resistant to shell injection."""
        for args in [
            ["launch", "org.example; rm -rf"],
            ["launch", "org.example `id`"],
            ["launch", "org.example$(whoami)"],
            ["launch", "org.example|cat /etc/passwd"],
        ]:
            result = run_cli_inproc(*args)
            assert result.returncode in (0, 1, 2, 64, 127)
            assert "root:" not in result.stdout.lower()

    def test_repeated_arguments(self):
        """CLI should handle repeated arguments."""
        args = ["launch", "org.example"] * 10
        result = run_cli_inproc(*args)
        assert result.returncode in (0, 1, 2, 64, 127)

    def test_environment_variable_injection(self):
        """CLI should handle malicious environment variables."""
        malicious_env = {
            "LD_PRELOAD": "/malicious.so",
            "LD_LIBRARY_PATH": "/tmp/malicious",
            "PYTHONPATH": "/tmp/injected",
            "FPLAUNCH_CONFIG": "../../../etc/passwd",
            "FPLAUNCH_BIN_DIR": "../../../etc",
        }
        from unittest.mock import patch

        with patch.dict(os.environ, malicious_env):
            result = run_cli_inproc("list")
        assert result.returncode in (0, 1, 2, 64, 127)
        assert "Traceback" not in result.stderr


class TestCLIPerformance:
    """Test CLI performance with many arguments."""

    def test_many_arguments_dont_crash(self):
        """CLI should handle many arguments without crashing."""
        args = ["launch", "org.example"] + [f"--arg{i}" for i in range(100)]
        result = run_cli_inproc(*args)
        assert result.returncode in (0, 1, 2, 64, 127)

    @pytest.mark.slow
    def test_rapid_commands(self):
        """CLI should handle rapid sequential commands without issues."""
        from lib import cli
        import tempfile
        from unittest.mock import patch

        for _ in range(20):
            with tempfile.TemporaryDirectory() as home:
                with patch.dict(os.environ, {"HOME": str(home)}):
                    try:
                        ret = cli.cli(["list"], standalone_mode=False)
                        code = ret if ret is not None else 0
                    except SystemExit as e:
                        code = e.code if e.code is not None else 0
            assert code in (0, 1, 64, 127)
