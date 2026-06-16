#!/usr/bin/env python3
"""Extra coverage tests for lib/launch.py uncovered branches.

Targets the 11 gap regions reported at 93% coverage:
  - lines 48-50:    FPWRAPPER_CACHE_TTL <= 0 or non-numeric fallback
  - line 140:       get_hook_scripts pre-launch successful append
  - lines 142-148:  get_hook_scripts post-launch branch (file/safe/exec checks)
  - line 151:       get_hook_scripts verbose OSError/ImportError warning
  - lines 381-387:  _get_safety_check relative-import fallback
  - line 461:       _check_preference_override invalid preference value
  - line 566:       _sanitize_arg method body
  - line 601:       _wrapper_exists success return path
  - lines 631-633:  launch verbose warning when pre-launch hooks fail
  - lines 645-646:  launch verbose warning when post-launch hooks fail
  - line 757:       module __main__ entry point

Uses isolated temp directories, monkeypatch, and unittest.mock.patch for
filesystem/external interactions. No real flatpak invocations.
"""

from __future__ import annotations

import builtins
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lib.launch import AppLauncher, main as launch_main


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_env() -> Generator[dict[str, Path], None, None]:
    """Create an isolated bin_dir + config_dir pair for the test."""
    temp_dir = Path(tempfile.mkdtemp(prefix="fp_launch_cov_extra_"))
    bin_dir = temp_dir / "bin"
    config_dir = temp_dir / "config"
    bin_dir.mkdir()
    config_dir.mkdir()
    yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}
    shutil.rmtree(temp_dir, ignore_errors=True)


def _make_launcher(env: dict[str, Path], **kwargs: object) -> AppLauncher:
    """Build an AppLauncher pointed at the isolated temp directories."""
    return AppLauncher(
        app_name=kwargs.pop("app_name", "test_app"),  # type: ignore[arg-type]
        bin_dir=str(env["bin_dir"]),
        config_dir=str(env["config_dir"]),
        **kwargs,  # type: ignore[arg-type]
    )


def _make_prefs_mock(post_launch_script: str | None = None,
                     pre_launch_script: str | None = None) -> Mock:
    """Create a Mock that quacks like AppPreferences."""
    prefs = Mock()
    prefs.pre_launch_script = pre_launch_script
    prefs.post_launch_script = post_launch_script
    return prefs


# ---------------------------------------------------------------------------
# Lines 48-50: FPWRAPPER_CACHE_TTL fallback
# ---------------------------------------------------------------------------


class TestCacheTTLImportFallback:
    """Lines 48-50: when FPWRAPPER_CACHE_TTL is non-positive or non-numeric
    the module falls back to DEFAULT_CACHE_TTL."""

    def _reload_with_ttl(self, ttl_value: str) -> float:
        """Set the env var, reload lib.launch, return the new TTL constant."""
        with patch.dict(os.environ, {"FPWRAPPER_CACHE_TTL": ttl_value}, clear=False):
            import lib.launch as launch_mod  # noqa: PLC0415
            reloaded = importlib.reload(launch_mod)
            return reloaded._CACHE_TTL_SECONDS

    def test_zero_ttl_uses_default(self) -> None:
        """FPWRAPPER_CACHE_TTL='0' must fall back to DEFAULT_CACHE_TTL."""
        result = self._reload_with_ttl("0")
        import lib.launch as launch_mod  # noqa: PLC0415

        assert result == launch_mod.DEFAULT_CACHE_TTL
        assert result == 300.0

    def test_negative_ttl_uses_default(self) -> None:
        """FPWRAPPER_CACHE_TTL='-5' must fall back to DEFAULT_CACHE_TTL."""
        result = self._reload_with_ttl("-5")
        import lib.launch as launch_mod  # noqa: PLC0415

        assert result == launch_mod.DEFAULT_CACHE_TTL

    def test_non_numeric_ttl_uses_default(self) -> None:
        """FPWRAPPER_CACHE_TTL='not-a-number' must fall back to DEFAULT_CACHE_TTL."""
        result = self._reload_with_ttl("not-a-number")
        import lib.launch as launch_mod  # noqa: PLC0415

        assert result == launch_mod.DEFAULT_CACHE_TTL


# ---------------------------------------------------------------------------
# Lines 140 + 142-148: _get_hook_scripts pre and post-launch config branches
# ---------------------------------------------------------------------------


class TestGetHookScriptsConfig:
    """Lines 140 and 141-148: pre and post launch scripts configured via
    the config manager. Covers the in-config-dir success path."""

    def test_pre_launch_script_configured_is_returned(self, temp_env: dict[str, Path]) -> None:
        """pre_launch_script set, file exists, executable, and in config_dir -> line 140."""
        scripts_dir = temp_env["config_dir"] / "scripts" / "test_app"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        script = scripts_dir / "pre-launch.sh"
        script.write_text("#!/bin/bash\necho pre\n")
        script.chmod(0o755)

        launcher = _make_launcher(temp_env)
        with patch(
            "lib.config_manager.create_config_manager"
        ) as mock_cm_factory:
            mock_cm_factory.return_value.get_app_preferences.return_value = (
                _make_prefs_mock(pre_launch_script=str(script))
            )

            scripts = launcher._get_hook_scripts("test_app", "pre")

        assert script in scripts

    def test_post_launch_script_configured_is_returned(
        self, temp_env: dict[str, Path]
    ) -> None:
        """post_launch_script set, file exists, executable, and in config_dir -> 141-148."""
        scripts_dir = temp_env["config_dir"] / "scripts" / "test_app"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        script = scripts_dir / "post-run.sh"
        script.write_text("#!/bin/bash\necho post\n")
        script.chmod(0o755)

        launcher = _make_launcher(temp_env)
        with patch(
            "lib.config_manager.create_config_manager"
        ) as mock_cm_factory:
            mock_cm_factory.return_value.get_app_preferences.return_value = (
                _make_prefs_mock(post_launch_script=str(script))
            )

            scripts = launcher._get_hook_scripts("test_app", "post")

        assert script in scripts

    def test_post_launch_script_not_executable_is_skipped(
        self, temp_env: dict[str, Path]
    ) -> None:
        """post_launch_script points to a non-executable file -> skipped."""
        scripts_dir = temp_env["config_dir"] / "scripts" / "test_app"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        script = scripts_dir / "post-run.sh"
        script.write_text("#!/bin/bash\necho post\n")
        script.chmod(0o644)  # explicitly NOT executable

        launcher = _make_launcher(temp_env)
        with patch(
            "lib.config_manager.create_config_manager"
        ) as mock_cm_factory:
            mock_cm_factory.return_value.get_app_preferences.return_value = (
                _make_prefs_mock(post_launch_script=str(script))
            )

            scripts = launcher._get_hook_scripts("test_app", "post")

        assert scripts == []

    def test_post_launch_script_unsafe_path_is_skipped(
        self, temp_env: dict[str, Path]
    ) -> None:
        """post_launch_script points outside config_dir -> path safety rejects -> skipped."""
        # External script in /tmp (outside config_dir)
        external = Path(tempfile.mkdtemp(prefix="fp_external_")) / "evil.sh"
        external.write_text("#!/bin/bash\necho evil\n")
        external.chmod(0o755)
        try:
            launcher = _make_launcher(temp_env)
            with patch(
                "lib.config_manager.create_config_manager"
            ) as mock_cm_factory:
                mock_cm_factory.return_value.get_app_preferences.return_value = (
                    _make_prefs_mock(post_launch_script=str(external))
                )

                scripts = launcher._get_hook_scripts("test_app", "post")

            assert scripts == []
        finally:
            shutil.rmtree(external.parent, ignore_errors=True)


# ---------------------------------------------------------------------------
# Line 151: verbose warning when config raises
# ---------------------------------------------------------------------------


class TestGetHookScriptsConfigError:
    """Line 151: when create_config_manager raises OSError/ImportError and
    verbose=True, a warning is logged."""

    def test_oserror_with_verbose_logs_warning(
        self, temp_env: dict[str, Path], caplog: pytest.LogCaptureFixture
    ) -> None:
        """OSError from create_config_manager with verbose=True -> warning logged."""
        caplog.set_level("WARNING")
        launcher = _make_launcher(temp_env, verbose=True)

        with patch(
            "lib.config_manager.create_config_manager",
            side_effect=OSError("disk gone"),
        ):
            scripts = launcher._get_hook_scripts("test_app", "pre")

        assert scripts == []
        assert "Failed to load hook scripts from config" in caplog.text

    def test_importerror_with_verbose_logs_warning(
        self, temp_env: dict[str, Path], caplog: pytest.LogCaptureFixture
    ) -> None:
        """ImportError from create_config_manager with verbose=True -> warning logged."""
        caplog.set_level("WARNING")
        launcher = _make_launcher(temp_env, verbose=True)

        with patch(
            "lib.config_manager.create_config_manager",
            side_effect=ImportError("simulated"),
        ):
            scripts = launcher._get_hook_scripts("test_app", "post")

        assert scripts == []
        assert "Failed to load hook scripts from config" in caplog.text

    def test_oserror_without_verbose_is_silent(
        self, temp_env: dict[str, Path], caplog: pytest.LogCaptureFixture
    ) -> None:
        """OSError from create_config_manager with verbose=False -> no warning logged."""
        caplog.set_level("WARNING")
        launcher = _make_launcher(temp_env, verbose=False)

        with patch(
            "lib.config_manager.create_config_manager",
            side_effect=OSError("disk gone"),
        ):
            scripts = launcher._get_hook_scripts("test_app", "pre")

        assert scripts == []
        assert "Failed to load hook scripts from config" not in caplog.text


# ---------------------------------------------------------------------------
# Lines 381-387: _get_safety_check relative-import fallback
# ---------------------------------------------------------------------------


class TestSafetyCheckRelativeImportFallback:
    """Lines 381-387: when ``from lib.safety import safe_launch_check`` fails
    with ImportError but the relative import ``from .safety import ...``
    succeeds, the inner try block returns the function."""

    def test_relative_import_succeeds_when_absolute_fails(
        self, temp_env: dict[str, Path]
    ) -> None:
        """Patched __import__ fails on level=0 (absolute) and succeeds on
        level=1 (relative) -> the inner try block returns the function."""
        real_import = builtins.__import__

        def fake_import(name, globals_=None, locals_=None, fromlist=(), level=0):  # noqa: A002
            if (
                name == "lib.safety"
                and "safe_launch_check" in (fromlist or ())
                and level == 0
            ):
                raise ImportError("simulated absolute import failure")
            return real_import(name, globals_, locals_, fromlist, level)

        launcher = _make_launcher(temp_env)
        with patch.object(builtins, "__import__", side_effect=fake_import):
            available, check = launcher._get_safety_check()

        assert available is True
        assert check is not None
        assert callable(check)

    def test_both_imports_fail_returns_unavailable(
        self, temp_env: dict[str, Path]
    ) -> None:
        """When both absolute and relative imports raise ImportError,
        _get_safety_check returns (False, None) -> lines 386-387.

        Note: the relative ``from .safety import X`` import calls
        ``__import__`` with ``name='safety', level=1`` (the bare name, not
        ``lib.safety``), so the filter must match both call shapes.
        """
        real_import = builtins.__import__

        def fake_import(name, globals_=None, locals_=None, fromlist=(), level=0):  # noqa: A002
            fromlist = fromlist or ()
            if "safe_launch_check" in fromlist and (
                (name == "lib.safety" and level == 0)
                or (name == "safety" and level == 1)
            ):
                raise ImportError("simulated import failure")
            return real_import(name, globals_, locals_, fromlist, level)

        launcher = _make_launcher(temp_env)
        with patch.object(builtins, "__import__", side_effect=fake_import):
            available, check = launcher._get_safety_check()

        assert available is False
        assert check is None


# ---------------------------------------------------------------------------
# Line 461: invalid preference file value
# ---------------------------------------------------------------------------


class TestInvalidPreferenceValue:
    """Line 461: a preference file with an unknown value must log a warning
    and leave wrapper_path / source unchanged."""

    def test_invalid_pref_value_warns_and_is_ignored(
        self,
        temp_env: dict[str, Path],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level("WARNING")
        # Wrapper exists and is executable
        wrapper = temp_env["bin_dir"] / "test_app"
        wrapper.write_text("#!/bin/bash\necho test\n")
        wrapper.chmod(0o755)

        # Preference file with an unknown value
        pref_file = temp_env["config_dir"] / "test_app.pref"
        pref_file.write_text("banana")

        launcher = _make_launcher(temp_env)
        # Path is the existing wrapper, source initially "system" via _find_wrapper
        wrapper_path, source = launcher._check_preference_override(wrapper, "system")

        # Unknown value is logged and ignored - wrapper/source unchanged
        assert "Invalid preference file value 'banana' for test_app" in caplog.text
        assert wrapper_path == wrapper
        assert source == "system"


# ---------------------------------------------------------------------------
# Line 566: _sanitize_arg method body
# ---------------------------------------------------------------------------


class TestSanitizeArg:
    """Line 566: _sanitize_arg replaces shell metacharacters with underscores
    while keeping common filename characters."""

    def test_sanitize_arg_strips_dangerous_chars(
        self, temp_env: dict[str, Path]
    ) -> None:
        launcher = _make_launcher(temp_env)
        sanitized = launcher._sanitize_arg("hello; rm -rf / && echo ok")
        # Dangerous chars replaced
        assert ";" not in sanitized
        assert "&" not in sanitized
        assert " " not in sanitized
        # Allowed chars kept
        assert "hello" in sanitized
        assert "rm" in sanitized

    def test_sanitize_arg_keeps_safe_chars(
        self, temp_env: dict[str, Path]
    ) -> None:
        launcher = _make_launcher(temp_env)
        sanitized = launcher._sanitize_arg("/path/to/file=arg@host:123.txt")
        assert sanitized == "/path/to/file=arg@host:123.txt"

    def test_sanitize_arg_keeps_dash_dot_underscore(
        self, temp_env: dict[str, Path]
    ) -> None:
        launcher = _make_launcher(temp_env)
        sanitized = launcher._sanitize_arg("a-b_c.d")
        assert sanitized == "a-b_c.d"


# ---------------------------------------------------------------------------
# Line 601: _wrapper_exists success return
# ---------------------------------------------------------------------------


class TestWrapperExists:
    """Line 601: _wrapper_exists returns the boolean combination of
    exists() and X_OK when the path is safe."""

    def test_wrapper_exists_returns_true_for_executable(
        self, temp_env: dict[str, Path]
    ) -> None:
        wrapper = temp_env["bin_dir"] / "test_app"
        wrapper.write_text("#!/bin/bash\necho test\n")
        wrapper.chmod(0o755)

        launcher = _make_launcher(temp_env)
        assert launcher._wrapper_exists() is True

    def test_wrapper_exists_returns_false_for_non_executable(
        self, temp_env: dict[str, Path]
    ) -> None:
        wrapper = temp_env["bin_dir"] / "test_app"
        wrapper.write_text("#!/bin/bash\necho test\n")
        wrapper.chmod(0o644)  # not executable

        launcher = _make_launcher(temp_env)
        assert launcher._wrapper_exists() is False

    def test_wrapper_exists_returns_false_for_missing(
        self, temp_env: dict[str, Path]
    ) -> None:
        launcher = _make_launcher(temp_env)
        assert launcher._wrapper_exists() is False

    def test_wrapper_exists_returns_false_for_escaped_path(
        self, temp_env: dict[str, Path]
    ) -> None:
        launcher = _make_launcher(temp_env, app_name="../../etc/passwd")
        # Path escapes bin_dir -> _is_path_safe returns False -> False
        assert launcher._wrapper_exists("../../etc/passwd") is False


# ---------------------------------------------------------------------------
# Lines 631-633: launch verbose warning on pre-launch hook failure
# ---------------------------------------------------------------------------


class TestLaunchPreHookFailureVerbose:
    """Lines 631-633: when pre-launch hooks return False with verbose=True,
    a warning is logged and the launch returns False."""

    def test_pre_launch_hook_failure_verbose_returns_false(
        self,
        temp_env: dict[str, Path],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level("WARNING")
        launcher = _make_launcher(temp_env, verbose=True)

        with patch.object(launcher, "_perform_safety_checks", return_value=True):
            with patch.object(launcher, "_run_hook_scripts", return_value=False):
                result = launcher.launch()

        assert result is False
        assert "Pre-launch hooks failed" in caplog.text


# ---------------------------------------------------------------------------
# Lines 645-646: launch verbose warning on post-launch hook failure
# ---------------------------------------------------------------------------


class TestLaunchPostHookFailureVerbose:
    """Lines 645-646: when post-launch hooks return False with verbose=True,
    a warning is logged. The launch return value reflects only the app's
    own exit code, not the hook result."""

    def test_post_launch_hook_failure_verbose_logs_warning(
        self,
        temp_env: dict[str, Path],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level("WARNING")
        launcher = _make_launcher(temp_env, verbose=True)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            with patch.object(launcher, "_perform_safety_checks", return_value=True):
                with patch.object(launcher, "_run_hook_scripts") as mock_hooks:
                    mock_hooks.side_effect = [True, False]  # pre=True, post=False
                    result = launcher.launch()

        # App launched successfully (returncode=0), but post hook failed.
        # The launch return value reflects the app exit code, not the hook.
        assert result is True
        assert "Post-launch hooks failed" in caplog.text


# ---------------------------------------------------------------------------
# Line 757: module __main__ entry point
# ---------------------------------------------------------------------------


class TestMainEntryPoint:
    """Line 757: when lib/launch.py is run as a script the
    ``if __name__ == '__main__': sys.exit(main())`` block executes."""

    def test_run_module_as_script_executes_entry_point(
        self, temp_env: dict[str, Path]
    ) -> None:
        """Compiling and exec'ing the source with __name__='__main__' must
        run the entry point, which calls sys.exit(main())."""
        import lib.launch  # noqa: PLC0415

        module_file = lib.launch.__file__
        assert module_file is not None

        real_argv = sys.argv
        sys.argv = ["lib.launch", "--help"]
        real_name = lib.launch.__name__
        lib.launch.__name__ = "__main__"

        try:
            with open(module_file) as fh:
                source = fh.read()
            code = compile(source, module_file, "exec")

            with pytest.raises(SystemExit) as exc_info:
                exec(code, lib.launch.__dict__)
        finally:
            sys.argv = real_argv
            lib.launch.__name__ = real_name

        # --help makes argparse call sys.exit(0); main() catches it and
        # returns 0; the entry point then calls sys.exit(0).
        assert exc_info.value.code == 0
