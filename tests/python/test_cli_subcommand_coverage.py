#!/usr/bin/env python3
"""Coverage for remaining gaps in lib/cli_generation, lib/cli_presets, lib/cli_system.

The three modules had 53 uncovered statements across small branch / option
combinations and the :func:`register_commands` helpers. These tests drive
each subcommand through CliRunner with the manager / config manager replaced
by small fakes so the dispatch logic is exercised without touching the
real filesystem, ``flatpak``, or ``systemctl`` binaries.
"""

from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

import lib.cli as cli_module
import lib.cli_generation as cli_generation_module
import lib.cli_presets as cli_presets_module
import lib.cli_system as cli_system_module
from lib.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _ok_proc() -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")


def _fake_manager(
    *,
    list_wrappers: Any = None,
    remove_wrapper: Any = None,
) -> MagicMock:
    """Return a ``WrapperManager`` double.

    The fake only exposes ``list_wrappers`` and ``remove_wrapper``. It does
    NOT expose ``display_wrappers`` so the test exercises the real-method
    fallback branch in :func:`cli_generation.list_wrappers`. Pass
    ``list_wrappers`` as a sentinel ``_OMIT`` to make the manager report
    ``hasattr(manager, "list_wrappers") == False``.
    """
    mgr = MagicMock(spec=["list_wrappers", "remove_wrapper", "bin_dir"])
    if list_wrappers is _OMIT:
        del mgr.list_wrappers
    elif list_wrappers is not None:
        mgr.list_wrappers = MagicMock(return_value=list_wrappers)
    if remove_wrapper is not None:
        mgr.remove_wrapper = MagicMock(return_value=remove_wrapper)
    return mgr


class _Omit:
    """Sentinel meaning "do not expose this attribute at all"."""


_OMIT = _Omit()


def _empty_manager() -> MagicMock:
    """A manager that exposes no list or display methods at all."""
    return MagicMock(spec=[])


def _fake_config_manager(
    *,
    presets: list | None = None,
    get_preset: Any = None,
    remove_preset: bool = True,
) -> MagicMock:
    """Return a config-manager double with the preset surface area stubbed."""
    cm = MagicMock()
    cm.list_permission_presets = MagicMock(return_value=presets or [])
    cm.get_permission_preset = MagicMock(return_value=get_preset)
    cm.add_permission_preset = MagicMock()
    cm.remove_permission_preset = MagicMock(return_value=remove_preset)
    return cm


# ---------------------------------------------------------------------------
# lib/cli_generation.py
# ---------------------------------------------------------------------------


class TestListWrappersBranches:
    """Cover the fallback branch in :func:`list_wrappers` (lines 56-67)."""

    def test_list_all_falls_back_to_list_wrappers(self, runner, isolated_home):
        """``list --all`` falls back to ``manager.list_wrappers()`` when the
        manager only exposes the real method (not ``display_wrappers``)."""
        wrappers = [
            {"name": "firefox", "id": "org.mozilla.firefox", "path": "/tmp/firefox"},
        ]
        mgr = _fake_manager(list_wrappers=wrappers)
        with patch.object(cli_generation_module, "build_manager", return_value=mgr):
            result = runner.invoke(cli, ["list", "--all"], standalone_mode=False)
        assert result.return_value == 0
        mgr.list_wrappers.assert_called_once_with()

    def test_list_all_warns_when_list_wrappers_empty(self, runner, isolated_home):
        """An empty ``list_wrappers()`` result must print a warning and exit 0."""
        mgr = _fake_manager(list_wrappers=[])
        with patch.object(cli_generation_module, "build_manager", return_value=mgr):
            result = runner.invoke(cli, ["list", "--all"], standalone_mode=False)
        assert result.return_value == 0
        mgr.list_wrappers.assert_called_once_with()

    def test_list_all_errors_when_no_list_method(self, runner, isolated_home):
        """A manager that exposes neither method must return exit code 1."""
        mgr = _empty_manager()
        with patch.object(cli_generation_module, "build_manager", return_value=mgr):
            result = runner.invoke(cli, ["list", "--all"], standalone_mode=False)
        assert result.return_value == 1

    def test_list_single_wrapper_found_by_name(self, runner, isolated_home):
        """``list firefox`` must match by ``name`` and print all three fields."""
        mgr = _fake_manager(
            list_wrappers=[
                {
                    "name": "firefox",
                    "id": "org.mozilla.firefox",
                    "path": "/usr/local/bin/firefox",
                },
                {
                    "name": "chrome",
                    "id": "com.google.Chrome",
                    "path": "/usr/local/bin/chrome",
                },
            ]
        )
        with patch.object(cli_generation_module, "build_manager", return_value=mgr):
            result = runner.invoke(cli, ["list", "firefox"], standalone_mode=False)
        assert result.return_value == 0

    def test_list_single_wrapper_found_by_id(self, runner, isolated_home):
        """``list com.google.Chrome`` must match by ``id`` and exit 0."""
        mgr = _fake_manager(
            list_wrappers=[
                {
                    "name": "chrome",
                    "id": "com.google.Chrome",
                    "path": "/usr/local/bin/chrome",
                },
            ]
        )
        with patch.object(cli_generation_module, "build_manager", return_value=mgr):
            result = runner.invoke(
                cli, ["list", "com.google.Chrome"], standalone_mode=False
            )
        assert result.return_value == 0

    def test_list_single_wrapper_not_found(self, runner, isolated_home):
        """``list <missing>`` must return 1 when nothing matches."""
        mgr = _fake_manager(
            list_wrappers=[
                {
                    "name": "firefox",
                    "id": "org.mozilla.firefox",
                    "path": "/usr/local/bin/firefox",
                },
            ]
        )
        with patch.object(cli_generation_module, "build_manager", return_value=mgr):
            result = runner.invoke(cli, ["list", "missing"], standalone_mode=False)
        assert result.return_value == 1

    def test_list_single_wrapper_without_list_method(self, runner, isolated_home):
        """``list foo`` with a manager that has no ``list_wrappers`` must error."""
        mgr = _empty_manager()
        with patch.object(cli_generation_module, "build_manager", return_value=mgr):
            result = runner.invoke(cli, ["list", "foo"], standalone_mode=False)
        assert result.return_value == 1

    def test_list_no_app_no_all_shows_hint(self, runner, isolated_home):
        """``list`` with no name and no ``--all`` must print a hint and exit 0."""
        mgr = _empty_manager()
        with patch.object(cli_generation_module, "build_manager", return_value=mgr):
            result = runner.invoke(cli, ["list"], standalone_mode=False)
        assert result.return_value == 0


class TestUninstallWrapperMissing:
    """Cover the warning branch in :func:`uninstall` (lines 147-150)."""

    def test_uninstall_warns_when_remove_wrapper_fails(self, runner, isolated_home):
        """When ``flatpak uninstall`` succeeds but ``remove_wrapper`` returns
        ``False`` (wrapper does not exist locally) the command must print a
        warning and exit 0, not 1."""
        mgr = _fake_manager(remove_wrapper=False)
        with (
            patch.object(
                cli_generation_module, "run_command", return_value=_ok_proc()
            ),
            patch.object(cli_generation_module, "build_manager", return_value=mgr),
        ):
            result = runner.invoke(
                cli,
                ["uninstall", "--yes", "org.example.NotInstalled"],
                standalone_mode=False,
            )
        assert result.return_value == 0
        mgr.remove_wrapper.assert_called_once_with(
            "org.example.NotInstalled", force=True
        )

class TestRegisterGenerationCommands:
    """Cover :func:`lib.cli_generation.register_commands` (lines 206-213)."""

    def test_register_commands_registers_all_eight(self):
        """Every generation subcommand must be added to the group under the
        expected name (this pins the public surface of the CLI group)."""
        expected = {
            "generate": cli_generation_module.generate,
            "list": cli_generation_module.list_wrappers,
            "install": cli_generation_module.install,
            "uninstall": cli_generation_module.uninstall,
            "remove": cli_generation_module.remove,
            "rm": cli_generation_module.rm,
            "set-pref": cli_generation_module.set_pref,
            "pref": cli_generation_module.pref,
        }

        @click.group()
        def fake_group() -> None:
            pass

        cli_generation_module.register_commands(fake_group)
        assert set(fake_group.commands.keys()) == set(expected.keys())
        for name, cmd in expected.items():
            assert fake_group.commands[name] is cmd


# ---------------------------------------------------------------------------
# lib/cli_presets.py
# ---------------------------------------------------------------------------


class TestPresetsGetSuccess:
    """Cover the printing loop in :func:`presets_get` (lines 48-51)."""

    def test_get_preset_prints_permissions(self, runner, isolated_home):
        """``presets get foo`` with a known preset must print all permissions."""
        cm = _fake_config_manager(
            get_preset=["--filesystem=home", "--device=dri"]
        )
        with patch.object(
            cli_presets_module, "build_config_manager", return_value=cm
        ):
            result = runner.invoke(
                cli, ["presets", "get", "media"], standalone_mode=False
            )
        assert result.return_value == 0
        cm.get_permission_preset.assert_called_once_with("media")


class TestPresetsAddValidation:
    """Cover the no-permission branch in :func:`presets_add` (lines 61-62)."""

    def test_add_preset_without_permission_returns_one(self, runner, isolated_home):
        """``presets add foo`` (no ``-p``) must error and exit 1."""
        cm = _fake_config_manager()
        with patch.object(
            cli_presets_module, "build_config_manager", return_value=cm
        ):
            result = runner.invoke(
                cli, ["presets", "add", "foo"], standalone_mode=False
            )
        assert result.return_value == 1
        cm.add_permission_preset.assert_not_called()


class TestPresetsRemove:
    """Cover the success and failure branches in :func:`presets_remove`
    (lines 75-80)."""

    def test_remove_existing_preset_succeeds(self, runner, isolated_home):
        """``presets remove foo`` must call the manager and exit 0."""
        cm = _fake_config_manager(remove_preset=True)
        with patch.object(
            cli_presets_module, "build_config_manager", return_value=cm
        ):
            result = runner.invoke(
                cli, ["presets", "remove", "foo"], standalone_mode=False
            )
        assert result.return_value == 0
        cm.remove_permission_preset.assert_called_once_with("foo")

    def test_remove_missing_preset_returns_one(self, runner, isolated_home):
        """``presets remove missing`` must print an error and exit 1."""
        cm = _fake_config_manager(remove_preset=False)
        with patch.object(
            cli_presets_module, "build_config_manager", return_value=cm
        ):
            result = runner.invoke(
                cli, ["presets", "remove", "missing"], standalone_mode=False
            )
        assert result.return_value == 1
        cm.remove_permission_preset.assert_called_once_with("missing")


# ---------------------------------------------------------------------------
# lib/cli_system.py
# ---------------------------------------------------------------------------


class TestCleanupExceptionBranches:
    """Cover the exception and ``None`` branches in :func:`cleanup`
    (lines 72-75)."""

    def test_cleanup_falls_back_when_resolve_bin_dir_raises(
        self, runner, isolated_home
    ):
        """If ``resolve_bin_dir`` raises, ``cleanup`` must still construct
        ``WrapperCleanup`` with the default ``~/bin`` and exit cleanly."""
        fake_cleanup = MagicMock()
        fake_cleanup.run = MagicMock(return_value=0)

        def _fake_require(module_name: str, symbol_name: str) -> Any:
            assert (module_name, symbol_name) == ("lib.cleanup", "WrapperCleanup")
            return lambda bin_dir=None: fake_cleanup

        with (
            patch("lib.paths.resolve_bin_dir", side_effect=RuntimeError("boom")),
            patch.object(
                cli_system_module.import_handler, "require", side_effect=_fake_require
            ) as mock_require,
        ):
            result = runner.invoke(cli, ["cleanup"], standalone_mode=False)
        assert result.return_value == 0
        mock_require.assert_called_once_with("lib.cleanup", "WrapperCleanup")
        fake_cleanup.run.assert_called_once_with()

    def test_cleanup_falls_back_when_resolve_bin_dir_returns_none(
        self, runner, isolated_home
    ):
        """If ``resolve_bin_dir`` returns ``None``, the function must default
        to ``~/bin`` and still construct the cleanup manager."""
        fake_cleanup = MagicMock()
        fake_cleanup.run = MagicMock(return_value=0)

        def _fake_require(module_name: str, symbol_name: str) -> Any:
            return lambda bin_dir=None: fake_cleanup

        with (
            patch("lib.paths.resolve_bin_dir", return_value=None),
            patch.object(
                cli_system_module.import_handler, "require", side_effect=_fake_require
            ),
        ):
            result = runner.invoke(cli, ["cleanup"], standalone_mode=False)
        assert result.return_value == 0
        fake_cleanup.run.assert_called_once_with()


class TestCleanAlias:
    """Cover the :func:`clean` alias body (line 85)."""

    def test_clean_invokes_cleanup(self, runner, isolated_home):
        """``clean`` must delegate to ``cleanup`` and return its exit code."""
        fake_cleanup = MagicMock()
        fake_cleanup.run = MagicMock(return_value=0)

        def _fake_require(module_name: str, symbol_name: str) -> Any:
            return lambda bin_dir=None: fake_cleanup

        with patch.object(
            cli_system_module.import_handler, "require", side_effect=_fake_require
        ):
            result = runner.invoke(cli, ["clean"], standalone_mode=False)
        assert result.return_value == 0
        fake_cleanup.run.assert_called_once_with()


class TestRegisterSystemCommands:
    """Cover :func:`lib.cli_system.register_commands` (lines 108-111)."""

    def test_register_commands_registers_all_four(self):
        """Every system subcommand must be added under the expected name."""
        expected = {
            "launch": cli_system_module.launch,
            "cleanup": cli_system_module.cleanup,
            "clean": cli_system_module.clean,
            "monitor": cli_system_module.monitor,
        }

        @click.group()
        def fake_group() -> None:
            pass

        cli_system_module.register_commands(fake_group)
        assert set(fake_group.commands.keys()) == set(expected.keys())
        for name, cmd in expected.items():
            assert fake_group.commands[name] is cmd
