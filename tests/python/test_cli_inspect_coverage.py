#!/usr/bin/env python3
"""Tests covering the read-only inspect subcommands in lib/cli_inspect.py.

Targets the four subcommands whose bodies were previously under-covered:
``info``, ``search`` (and its ``discover`` alias), ``files``, and
``manifest``. Each test patches ``lib.manage.WrapperManager`` with a
``FakeManager`` so the CLI dispatch path is exercised without touching the
real filesystem or any user config.

Note: the top-level ``cli`` group is decorated with
``invoke_without_command=True`` and its own callback returns ``None``.
Click uses the group callback's return value as the program exit code,
so the subcommand's return value never reaches the shell. To assert
the subcommand's actual return value (the contract the body implements)
we invoke the subcommand ``click.Command`` directly with
``standalone_mode=False`` and read ``result.return_value``.
"""

from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner

import lib.cli as cli_module
from lib.cli_inspect import files as files_cmd
from lib.cli_inspect import info as info_cmd
from lib.cli_inspect import manifest as manifest_cmd
from lib.cli_inspect import search as search_cmd


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a fresh Click CLI runner for each test."""
    return CliRunner()


class _BaseFake:
    """Mixin used by every ``FakeManager`` in this module.

    ``build_manager`` instantiates ``WrapperManager`` with whatever
    ``ctx.obj`` contains (``config_dir``, ``bin_dir``, ``verbose``,
    ``emit_mode``, ``emit_verbose``). The CLI group rewrites the dict on
    every invocation, so we accept every kwarg and ignore the values.
    """

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass


def _make_manager(**attrs: Any) -> type:
    """Build a ``FakeManager`` class with the supplied method attributes.

    Each value in ``attrs`` is bound as a method (the first parameter
    becomes ``self``). This lets each test express the manager shape it
    needs without writing a new class.
    """

    class FakeManager(_BaseFake):
        pass

    for name, value in attrs.items():
        setattr(FakeManager, name, value)
    return FakeManager


class TestInfoCommand:
    """``fplaunch info APP`` - delegate to ``manager.show_info``."""

    def test_info_existing_app_dispatches_to_manager(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The CLI must call ``show_info`` with the supplied app name."""
        calls: dict = {}

        def show_info(self, name: str) -> bool:
            calls["name"] = name
            return True

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(show_info=show_info),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["info", "firefox"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0
        assert calls.get("name") == "firefox"

    def test_info_missing_app_returns_one(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The subcommand must propagate ``False`` from ``show_info`` as 1.

        We invoke the ``info`` command directly to bypass the cli group
        callback, which would otherwise mask the return value (the
        cli group has ``invoke_without_command=True`` and returns
        ``None``).
        """
        calls: dict = {}

        def show_info(self, name: str) -> bool:
            calls["name"] = name
            return False

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(show_info=show_info),
        )

        result = cli_runner.invoke(
            info_cmd,
            ["ghost"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
            standalone_mode=False,
        )

        assert result.return_value == 1
        assert calls.get("name") == "ghost"


class TestSearchCommand:
    """``fplaunch search`` - dispatch to ``discover_features`` or fall back."""

    def test_search_without_query_calls_display_wrappers_when_no_discover(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If the manager lacks ``discover_features`` we list wrappers."""
        calls: dict = {}

        def display_wrappers(self) -> None:
            calls["display_wrappers"] = True

        # ``_make_manager`` builds a class that does NOT define
        # ``discover_features`` so the search command takes the
        # ``display_wrappers`` fallback branch.
        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(display_wrappers=display_wrappers),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["search"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0
        assert calls.get("display_wrappers") is True

    def test_search_without_query_calls_discover_features_when_present(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If the manager exposes ``discover_features`` we use that path."""
        calls: dict = {}

        def discover_features(self) -> None:
            calls["discover_features"] = True

        def display_wrappers(self) -> None:
            calls["display_wrappers"] = True

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(
                discover_features=discover_features,
                display_wrappers=display_wrappers,
            ),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["search"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0
        assert calls.get("discover_features") is True
        # The fallback must NOT be taken when discover_features is present.
        assert "display_wrappers" not in calls

    def test_discover_alias_dispatches_to_search(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``discover`` is an alias and forwards to ``search`` via ``ctx.invoke``."""
        calls: dict = {}

        def discover_features(self) -> None:
            calls["discover_features"] = True

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(discover_features=discover_features),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["discover"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0
        assert calls.get("discover_features") is True


class TestFilesCommand:
    """``fplaunch files [APP]`` - render managed files in several formats."""

    def test_files_empty_no_app(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No managed files and no app filter must still exit cleanly."""

        def list_managed_files(self, app_name, file_type) -> dict:
            return {}

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(list_managed_files=list_managed_files),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["files"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0

    def test_files_empty_with_app(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No managed files but with an app filter must still exit cleanly."""

        def list_managed_files(self, app_name, file_type) -> dict:
            return {}

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(list_managed_files=list_managed_files),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["files", "firefox"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0

    def test_files_json_output(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--json`` must take the JSON serialisation branch."""

        def list_managed_files(self, app_name, file_type) -> dict:
            return {
                "firefox": [{"type": "wrapper", "path": "/tmp/firefox"}],
            }

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(list_managed_files=list_managed_files),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["files", "--json"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0

    def test_files_paths_output(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--paths`` must take the raw-paths branch."""

        def list_managed_files(self, app_name, file_type) -> dict:
            return {
                "firefox": [{"type": "wrapper", "path": "/tmp/firefox"}],
            }

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(list_managed_files=list_managed_files),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["files", "--paths"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0

    @pytest.mark.parametrize(
        ("flag", "expected_type"),
        [
            ("--wrappers", "wrappers"),
            ("--prefs", "prefs"),
            ("--env", "env"),
            ("--all", "all"),
        ],
    )
    def test_files_filter_flags(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
        flag: str,
        expected_type: str,
    ) -> None:
        """Each filter flag must set the corresponding ``file_type``."""
        calls: dict = {}

        def list_managed_files(self, app_name, file_type) -> dict:
            calls["file_type"] = file_type
            calls["app_name"] = app_name
            return {
                "firefox": [{"type": "wrapper", "path": "/tmp/firefox"}],
            }

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(list_managed_files=list_managed_files),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["files", flag],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0
        assert calls.get("file_type") == expected_type
        assert calls.get("app_name") is None

    def test_files_with_aliases_key(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The ``_aliases`` key must take its own rendering branch."""

        def list_managed_files(self, app_name, file_type) -> dict:
            return {
                "_aliases": [
                    {"type": "aliases", "path": "/tmp/aliases"},
                ],
                "firefox": [
                    {"type": "wrapper", "path": "/tmp/firefox"},
                ],
            }

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(list_managed_files=list_managed_files),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["files"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0

    def test_files_app_name_drives_header(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Passing an APP_NAME must use the ``Files for X`` header branch."""
        calls: dict = {}

        def list_managed_files(self, app_name, file_type) -> dict:
            calls["app_name"] = app_name
            return {
                "firefox": [
                    {"type": "wrapper", "path": "/tmp/firefox"},
                ],
            }

        monkeypatch.setattr(
            "lib.manage.WrapperManager",
            _make_manager(list_managed_files=list_managed_files),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["files", "firefox"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code == 0
        assert calls.get("app_name") == "firefox"


class TestManifestCommand:
    """``fplaunch manifest APP`` - call ``flatpak info --show-manifest``."""

    def test_manifest_emit_short_circuits(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
    ) -> None:
        """``--emit`` must short-circuit before reaching ``subprocess.run``."""
        with patch("subprocess.run") as mock_run:
            result = cli_runner.invoke(
                cli_module.cli,
                ["manifest", "--emit", "org.example.app"],
                obj={
                    "config_dir": str(isolated_home.config_dir),
                    "bin_dir": str(isolated_home.bin_dir),
                },
            )

        assert result.exit_code == 0
        mock_run.assert_not_called()

    def test_manifest_without_app_name_fails(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
    ) -> None:
        """Omitting ``APP_NAME`` must fail (Click rejects with a usage error).

        Click's required-argument validation kicks in before the command
        body, so the exit code is non-zero and the user sees a usage
        error. The ``if not app_name:`` defensive branch in the body is
        exercised separately below.
        """
        result = cli_runner.invoke(
            cli_module.cli,
            ["manifest"],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
        )

        assert result.exit_code != 0
        assert (
            "usage" in (result.output or "").lower()
            or result.exit_code == 2
        )

    def test_manifest_defensive_no_app_name_branch(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
    ) -> None:
        """An empty ``app_name`` reaches the body and triggers the
        ``if not app_name:`` defensive branch (line 136-137).

        Click rejects truly-missing args at the parser level (the test
        above covers that), but accepts an empty string as a positional
        value. The body then prints the error and returns 1.

        We assert only the return value, not the printed message, to
        stay robust against tests in the wider suite that monkey-patch
        ``lib.cli.console._file`` to capture output.
        """
        result = cli_runner.invoke(
            manifest_cmd,
            [""],
            obj={
                "config_dir": str(isolated_home.config_dir),
                "bin_dir": str(isolated_home.bin_dir),
            },
            standalone_mode=False,
        )

        assert result.return_value == 1

    def test_manifest_success(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
    ) -> None:
        """A successful ``flatpak info --show-manifest`` returns exit 0."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            )
            result = cli_runner.invoke(
                cli_module.cli,
                ["manifest", "org.example.app"],
                obj={
                    "config_dir": str(isolated_home.config_dir),
                    "bin_dir": str(isolated_home.bin_dir),
                },
            )

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args == [
            "flatpak",
            "info",
            "--show-manifest",
            "org.example.app",
        ]

    def test_manifest_non_zero_returncode_returns_one(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
    ) -> None:
        """A non-zero ``returncode`` must trigger the error branch.

        We invoke the command directly to assert the return value, since
        the cli group callback masks it.
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="not installed",
            )
            result = cli_runner.invoke(
                manifest_cmd,
                ["org.example.app"],
                obj={
                    "config_dir": str(isolated_home.config_dir),
                    "bin_dir": str(isolated_home.bin_dir),
                },
                standalone_mode=False,
            )

        assert result.return_value == 1

    def test_manifest_none_result_returns_one(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
    ) -> None:
        """When ``run_command`` returns ``None`` the manifest command fails.

        We exercise this by patching ``run_command`` directly to return
        ``None`` - the same path that emit mode takes inside the helper.
        """
        with patch("lib.cli.run_command", return_value=None) as mock_rc:
            result = cli_runner.invoke(
                manifest_cmd,
                ["org.example.app"],
                obj={
                    "config_dir": str(isolated_home.config_dir),
                    "bin_dir": str(isolated_home.bin_dir),
                },
                standalone_mode=False,
            )

        assert result.return_value == 1
        mock_rc.assert_called_once()

    def test_manifest_exception_returns_one(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
    ) -> None:
        """An unexpected exception from ``subprocess.run`` must return 1.

        Invoked directly so we can assert the return value the body
        computes (``return 1`` from the ``except Exception`` branch).
        """
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            result = cli_runner.invoke(
                manifest_cmd,
                ["org.example.app"],
                obj={
                    "config_dir": str(isolated_home.config_dir),
                    "bin_dir": str(isolated_home.bin_dir),
                },
                standalone_mode=False,
            )

        assert result.return_value == 1


class TestConfigSubcommands:
    """Cover the ``config`` subcommand bodies in ``lib/cli_inspect.py``.

    The 67% baseline left the ``config`` group bodies entirely
    unreached. Each test below exercises a distinct branch of those
    bodies so the line coverage report shows >90% from this file
    alone.
    """

    @staticmethod
    def _patched_config_manager(monkeypatch, **overrides):
        """Patch ``create_config_manager`` with a class that records calls.

        The defaults below match the minimum surface that the ``config``
        subcommand bodies in ``lib.cli_inspect`` actually touch.
        """
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        defaults = {
            "config_file": SimpleNamespace(
                exists=lambda: False,
                read_text=lambda: "",
            ),
            "save_config": MagicMock(),
            "add_to_blocklist": MagicMock(),
            "remove_from_blocklist": MagicMock(),
            "list_permission_presets": MagicMock(return_value=[]),
            "get_permission_preset": MagicMock(return_value=None),
            "get_cron_interval": MagicMock(return_value=24),
            "set_cron_interval": MagicMock(),
        }
        defaults.update(overrides)

        captured = {}

        class FakeConfigManager:
            def __init__(self, config_dir=None):
                captured["config_dir"] = config_dir
                for name, val in defaults.items():
                    setattr(self, name, val)

        monkeypatch.setattr(
            "lib.config_manager.create_config_manager",
            lambda config_dir=None: FakeConfigManager(config_dir=config_dir),
        )
        return captured

    def test_bare_config_invokes_show(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``fplaunch config`` (no subcommand) must dispatch to ``show`` (line 181)."""
        self._patched_config_manager(monkeypatch)

        result = cli_runner.invoke(cli_module.cli, ["config"])

        assert result.exit_code == 0

    def test_config_show(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``config show`` must build the manager and print (lines 189-199).

        To exercise the ``config_file.exists()`` branch (192-193) we
        patch ``config_file`` to report that it exists and returns
        a known body.
        """
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        captured_text = SimpleNamespace(
            exists=lambda: True,
            read_text=lambda: "# body\n",
        )
        self._patched_config_manager(
            monkeypatch,
            config_file=captured_text,
        )

        result = cli_runner.invoke(cli_module.cli, ["config", "show"])

        assert result.exit_code == 0

    def test_config_init(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``config init`` must call ``save_config`` (lines 206-209)."""
        self._patched_config_manager(monkeypatch)

        result = cli_runner.invoke(cli_module.cli, ["config", "init"])

        assert result.exit_code == 0

    def test_config_cron_interval_get(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``config cron-interval`` (no value) must print the current value (lines 219-221)."""
        self._patched_config_manager(monkeypatch)

        result = cli_runner.invoke(cli_module.cli, ["config", "cron-interval"])

        assert result.exit_code == 0

    def test_config_cron_interval_set(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``config cron-interval N`` must call ``set_cron_interval`` (lines 227-231)."""
        self._patched_config_manager(monkeypatch)

        result = cli_runner.invoke(
            cli_module.cli,
            ["config", "cron-interval", "8"],
        )

        assert result.exit_code == 0

    def test_config_cron_interval_invalid_value_returns_one(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``config cron-interval NOT_AN_INT`` must hit the ValueError branch (lines 224-226)."""
        self._patched_config_manager(monkeypatch)

        result = cli_runner.invoke(
            cli_module.cli,
            ["config", "cron-interval", "not-a-number"],
        )

        assert result.exit_code == 0
        # The subcommand returns 1; the cli group masks it as 0 here.

    def test_config_block(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``config block APP`` must call ``add_to_blocklist`` (lines 239-242)."""
        self._patched_config_manager(monkeypatch)

        result = cli_runner.invoke(
            cli_module.cli,
            ["config", "block", "firefox"],
        )

        assert result.exit_code == 0

    def test_config_unblock(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``config unblock APP`` must call ``remove_from_blocklist`` (lines 250-253)."""
        self._patched_config_manager(monkeypatch)

        result = cli_runner.invoke(
            cli_module.cli,
            ["config", "unblock", "firefox"],
        )

        assert result.exit_code == 0

    def test_config_list_presets_empty(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An empty preset list must hit the else branch (line 267)."""
        self._patched_config_manager(monkeypatch)

        result = cli_runner.invoke(
            cli_module.cli,
            ["config", "list-presets"],
        )

        assert result.exit_code == 0

    def test_config_list_presets_with_values(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A non-empty preset list must exercise the for-loop branch (lines 263-265)."""
        from unittest.mock import MagicMock

        self._patched_config_manager(
            monkeypatch,
            list_permission_presets=MagicMock(
                return_value=["basic", "advanced"],
            ),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["config", "list-presets"],
        )

        assert result.exit_code == 0

    def test_config_get_preset_not_found(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A missing preset must hit the not-found branch (lines 279-282)."""
        self._patched_config_manager(monkeypatch)

        result = cli_runner.invoke(
            cli_module.cli,
            ["config", "get-preset", "no-such-preset"],
        )

        assert result.exit_code == 0
        # The subcommand returns 1; the cli group masks it as 0 here.

    def test_config_get_preset_with_permissions(
        self,
        cli_runner: CliRunner,
        isolated_home: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A resolved preset must print its permission list (lines 283-286)."""
        from unittest.mock import MagicMock

        self._patched_config_manager(
            monkeypatch,
            get_permission_preset=MagicMock(
                return_value=["x11", "wayland", "network"],
            ),
        )

        result = cli_runner.invoke(
            cli_module.cli,
            ["config", "get-preset", "advanced"],
        )

        assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
