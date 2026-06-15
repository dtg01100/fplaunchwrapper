#!/usr/bin/env python3
"""In-process tests for ``lib.config_manager_cli.main()``.

This file exercises the ``fplaunch-config`` entry point end-to-end:
``create_config_manager`` is monkey-patched with a ``FakeConfigManager``
and ``main()`` is invoked via the in-process argparse pattern (set
``sys.argv``, redirect ``sys.stdout``/``sys.stderr`` to ``io.StringIO``,
catch ``SystemExit``).

Each test covers one of the branches left uncovered on the
``lib.config_manager_cli`` module prior to this file being added.
"""

from __future__ import annotations

import io
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


_UNSET = object()


class FakeConfigManager:
    """Test double for ``EnhancedConfigManager``.

    Each method that the CLI calls is wired up to a ``MagicMock`` so
    tests can assert on the call and configure return values. The
    ``config_file`` attribute is a real ``Path`` so the ``show``
    command can call ``.exists()`` and ``.read_text()`` on it.
    """

    def __init__(
        self,
        *,
        config_file: Path | None = None,
        config_exists: bool = False,
        config_contents: str = "",
        presets: list[str] | None = None,
        preset_permissions: Any = _UNSET,
        cron_interval: int = 24,
    ) -> None:
        if config_file is None:
            config_file = Path("/tmp/fake_config_dir/config.toml")
        self.config_file = config_file
        self._config_exists = config_exists
        self._config_contents = config_contents

        self.save_config = MagicMock()
        self.add_to_blocklist = MagicMock()
        self.remove_from_blocklist = MagicMock()
        self.list_permission_presets = MagicMock(
            return_value=list(presets) if presets is not None else ["gaming", "office"]
        )
        if preset_permissions is _UNSET:
            preset_return: list[str] | None = ["--filesystem=home", "--device=dri"]
        else:
            preset_return = list(preset_permissions) if preset_permissions is not None else None
        self.get_permission_preset = MagicMock(return_value=preset_return)
        self.get_cron_interval = MagicMock(return_value=cron_interval)
        self.set_cron_interval = MagicMock()


def _wire_config_file(fake: FakeConfigManager) -> None:
    """Replace ``config_file`` on a FakeConfigManager with a Path that
    can answer ``.exists()``/``.read_text()`` like a real config file.
    """
    real_path = fake.config_file

    class _FakePath:
        def __init__(self, underlying: Path) -> None:
            self._path = underlying

        def exists(self) -> bool:
            return fake._config_exists

        def read_text(self) -> str:
            return fake._config_contents

        def __str__(self) -> str:
            return str(self._path)

    fake.config_file = _FakePath(real_path)  # type: ignore[assignment]


def _run_cli(argv: list[str], fake: FakeConfigManager) -> SimpleNamespace:
    """Invoke ``config_manager_cli.main()`` with a FakeConfigManager.

    Returns a ``SimpleNamespace(returncode, stdout, stderr)``.
    """
    # Make the config_file attribute act like a real path
    _wire_config_file(fake)

    old_argv = sys.argv
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    sys.argv = argv
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    try:
        with patch("lib.config_manager.create_config_manager", return_value=fake):
            from lib import config_manager_cli

            config_manager_cli.main()
        return SimpleNamespace(
            returncode=0,
            stdout=sys.stdout.getvalue(),
            stderr=sys.stderr.getvalue(),
        )
    except SystemExit as e:
        return SimpleNamespace(
            returncode=e.code if e.code is not None else 0,
            stdout=sys.stdout.getvalue(),
            stderr=sys.stderr.getvalue(),
        )
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.argv = old_argv


class TestInitCommand:
    """Coverage for lines 73-76: the ``init`` command branch."""

    def test_init_runs_and_prints_success(self) -> None:
        """``init`` calls ``save_config`` and prints the success line."""
        fake = FakeConfigManager()
        result = _run_cli(["fplaunch-config", "init"], fake)

        assert result.returncode == 0
        assert "Configuration initialized successfully" in result.stdout
        fake.save_config.assert_called_once_with()


class TestShowCommand:
    """Coverage for lines 78-84: the ``show`` command branch (both paths)."""

    def test_show_existing_config_file(self, tmp_path: Path) -> None:
        """``show`` with an existing file prints the file contents."""
        existing = tmp_path / "config.toml"
        fake = FakeConfigManager(
            config_file=existing,
            config_exists=True,
            config_contents="bin_dir = '/tmp/bin'\ndebug_mode = true\n",
        )
        result = _run_cli(["fplaunch-config", "show"], fake)

        assert result.returncode == 0
        assert "bin_dir" in result.stdout
        assert "debug_mode" in result.stdout

    def test_show_missing_config_file(self) -> None:
        """``show`` without a file prints the 'not found' message and hint."""
        fake = FakeConfigManager(config_exists=False)
        result = _run_cli(["fplaunch-config", "show"], fake)

        assert result.returncode == 0
        assert "No configuration file found at" in result.stdout
        assert "Run 'fplaunch config init'" in result.stdout


class TestBlockCommand:
    """Coverage for lines 86-91: the ``block`` command branch."""

    def test_block_with_app_name(self) -> None:
        """``block <app>`` calls ``add_to_blocklist`` and prints confirmation."""
        fake = FakeConfigManager()
        result = _run_cli(["fplaunch-config", "block", "firefox"], fake)

        assert result.returncode == 0
        assert "Blocked firefox" in result.stdout
        fake.add_to_blocklist.assert_called_once_with("firefox")

    def test_block_without_app_name_invokes_parser_error(self) -> None:
        """``block`` without a value exits with argparse's error code (2)."""
        fake = FakeConfigManager()
        with patch("argparse.ArgumentParser.error") as mock_error:
            mock_error.side_effect = SystemExit(2)
            result = _run_cli(["fplaunch-config", "block"], fake)

        assert result.returncode == 2
        mock_error.assert_called_once()
        # The error message should mention the requirement
        args, _ = mock_error.call_args
        assert "block" in args[0]
        assert "app name" in args[0]
        # And we should NOT have called add_to_blocklist
        fake.add_to_blocklist.assert_not_called()


class TestUnblockCommand:
    """Coverage for lines 93-98: the ``unblock`` command branch."""

    def test_unblock_with_app_name(self) -> None:
        """``unblock <app>`` calls ``remove_from_blocklist`` and prints confirmation."""
        fake = FakeConfigManager()
        result = _run_cli(["fplaunch-config", "unblock", "firefox"], fake)

        assert result.returncode == 0
        assert "Unblocked firefox" in result.stdout
        fake.remove_from_blocklist.assert_called_once_with("firefox")

    def test_unblock_without_app_name_invokes_parser_error(self) -> None:
        """``unblock`` without a value exits with argparse's error code (2)."""
        fake = FakeConfigManager()
        with patch("argparse.ArgumentParser.error") as mock_error:
            mock_error.side_effect = SystemExit(2)
            result = _run_cli(["fplaunch-config", "unblock"], fake)

        assert result.returncode == 2
        mock_error.assert_called_once()
        args, _ = mock_error.call_args
        assert "unblock" in args[0]
        assert "app name" in args[0]
        fake.remove_from_blocklist.assert_not_called()


class TestListPresetsCommand:
    """Coverage for lines 100-108: the ``list-presets`` command branch."""

    def test_list_presets_with_presets_available(self) -> None:
        """``list-presets`` prints each preset name when presets exist."""
        fake = FakeConfigManager(presets=["gaming", "office", "creative"])
        result = _run_cli(["fplaunch-config", "list-presets"], fake)

        assert result.returncode == 0
        assert "Available permission presets:" in result.stdout
        assert "gaming" in result.stdout
        assert "office" in result.stdout
        assert "creative" in result.stdout
        fake.list_permission_presets.assert_called_once_with()

    def test_list_presets_with_empty_presets(self) -> None:
        """``list-presets`` prints the empty message when no presets are defined."""
        fake = FakeConfigManager(presets=[])
        result = _run_cli(["fplaunch-config", "list-presets"], fake)

        assert result.returncode == 0
        assert "No permission presets defined" in result.stdout
        # The "Available" header should NOT appear in the empty case
        assert "Available permission presets" not in result.stdout
        fake.list_permission_presets.assert_called_once_with()


class TestGetPresetCommand:
    """Coverage for lines 110-121: the ``get-preset`` command branch."""

    def test_get_preset_with_valid_preset(self) -> None:
        """``get-preset <name>`` prints the permissions list for that preset."""
        fake = FakeConfigManager(
            preset_permissions=["--filesystem=home", "--device=dri"],
        )
        result = _run_cli(["fplaunch-config", "get-preset", "gaming"], fake)

        assert result.returncode == 0
        assert "Permissions for preset 'gaming':" in result.stdout
        assert "--filesystem=home" in result.stdout
        assert "--device=dri" in result.stdout
        fake.get_permission_preset.assert_called_once_with("gaming")

    def test_get_preset_without_preset_name_invokes_parser_error(self) -> None:
        """``get-preset`` without a name exits with argparse's error code (2)."""
        fake = FakeConfigManager()
        with patch("argparse.ArgumentParser.error") as mock_error:
            mock_error.side_effect = SystemExit(2)
            result = _run_cli(["fplaunch-config", "get-preset"], fake)

        assert result.returncode == 2
        mock_error.assert_called_once()
        args, _ = mock_error.call_args
        assert "get-preset" in args[0]
        assert "preset name" in args[0]
        fake.get_permission_preset.assert_not_called()

    def test_get_preset_with_unknown_preset(self) -> None:
        """``get-preset <unknown>`` writes to stderr and exits with code 1."""
        fake = FakeConfigManager(preset_permissions=None)
        result = _run_cli(["fplaunch-config", "get-preset", "nonexistent"], fake)

        assert result.returncode == 1
        assert "nonexistent" in result.stderr
        # The 'Permissions for' header should NOT appear on stdout
        assert "Permissions for" not in result.stdout
        fake.get_permission_preset.assert_called_once_with("nonexistent")


class TestCronIntervalCommand:
    """Coverage for lines 123-135: the ``cron-interval`` command branch."""

    def test_cron_interval_without_value_shows_current(self) -> None:
        """``cron-interval`` with no value prints the current interval."""
        fake = FakeConfigManager(cron_interval=12)
        result = _run_cli(["fplaunch-config", "cron-interval"], fake)

        assert result.returncode == 0
        assert "Current cron interval" in result.stdout
        assert "12" in result.stdout
        assert "hours" in result.stdout
        fake.get_cron_interval.assert_called_once_with()
        # We should NOT have called set_cron_interval in the read path
        fake.set_cron_interval.assert_not_called()

    def test_cron_interval_with_valid_integer_sets_it(self) -> None:
        """``cron-interval <int>`` calls ``set_cron_interval`` and confirms."""
        fake = FakeConfigManager()
        result = _run_cli(["fplaunch-config", "cron-interval", "6"], fake)

        assert result.returncode == 0
        assert "Cron interval set to 6 hours" in result.stdout
        fake.set_cron_interval.assert_called_once_with(6)
        # We should NOT have called get_cron_interval when setting
        fake.get_cron_interval.assert_not_called()

    def test_cron_interval_with_non_integer_errors(self) -> None:
        """``cron-interval <non-int>`` writes to stderr and exits with code 1."""
        fake = FakeConfigManager()
        result = _run_cli(["fplaunch-config", "cron-interval", "abc"], fake)

        assert result.returncode == 1
        assert "Invalid interval value" in result.stderr
        assert "abc" in result.stderr
        # We should NOT have called either getter or setter on bad input
        fake.get_cron_interval.assert_not_called()
        fake.set_cron_interval.assert_not_called()


class TestModuleEntryPoint:
    """Coverage for line 142: ``if __name__ == "__main__": main()``.

    The file is invoked as ``__main__`` via subprocess with ``--help``
    so argparse exits before any module-level side effects. We use
    ``--help`` because invoking a real subcommand would require a real
    ``create_config_manager`` and an isolated home.
    """

    def test_module_entry_point(self) -> None:
        """Running the file as a script hits the ``if __name__`` branch."""
        script = PROJECT_ROOT / "lib" / "config_manager_cli.py"
        assert script.exists(), f"Expected script at {script}"

        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, (
            f"--help exited with {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        # Sanity-check that argparse actually emitted help text
        assert "usage:" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
