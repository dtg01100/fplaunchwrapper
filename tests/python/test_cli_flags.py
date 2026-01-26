import os
import sys
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

sys.path.insert(0, os.path.abspath("."))

import lib.manage as manage


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cli_mod():
    import lib.cli as cli

    if not getattr(cli, "CLICK_AVAILABLE", False):
        pytest.skip("Click not available")
    return cli


def test_generate_accepts_global_flags(cli_mod, runner, monkeypatch, tmp_path):
    calls = {}

    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    class FakeGenerator:
        def __init__(self, bin_dir, verbose, emit_mode, emit_verbose):
            calls["args"] = (bin_dir, verbose, emit_mode, emit_verbose)

        def run(self):
            calls["run"] = True
            return 0

    monkeypatch.setattr("lib.generate.WrapperGenerator", FakeGenerator)

    result = runner.invoke(
        cli_mod.cli,
        [
            "--verbose",
            "--emit",
            "--emit-verbose",
            "--config-dir",
            str(config_dir),
            "generate",
            str(bin_dir),
        ],
    )

    assert result.exit_code == 0
    assert calls["args"] == (str(bin_dir), True, True, True)
    assert calls.get("run") is True


def test_remove_alias_rm(cli_mod, runner, monkeypatch):
    monkeypatch.setattr(
        "lib.cli.find_fplaunch_script",
        lambda name: Path("/bin/true"),
    )

    def fake_run_command(cmd, description="", show_output=True, emit_mode=False):
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("lib.cli.run_command", fake_run_command)

    result = runner.invoke(cli_mod.cli, ["rm", "example.app"], catch_exceptions=False)
    assert result.exit_code == 0


def test_systemd_setup_alias(cli_mod, runner, monkeypatch):
    calls = {}

    class FakeSystemdSetup:
        def __init__(
            self, bin_dir=None, wrapper_script=None, emit_mode=False, emit_verbose=False
        ):
            calls["init"] = (emit_mode, emit_verbose)

        def run(self):
            calls["run"] = True
            return 0

    monkeypatch.setattr("lib.systemd_setup.SystemdSetup", FakeSystemdSetup)

    result = runner.invoke(cli_mod.cli, ["systemd-setup"], catch_exceptions=False)
    assert result.exit_code == 0
    assert calls == {"init": (False, False), "run": True}


def test_config_defaults_to_show(cli_mod, runner, monkeypatch):
    calls = []

    class FakeConfigManager:
        def __init__(self):
            calls.append("init")

        def save_config(self):
            calls.append("save_config")

        def add_to_blocklist(self, app):
            calls.append(f"block {app}")

        def remove_from_blocklist(self, app):
            calls.append(f"unblock {app}")

        def list_permission_presets(self):
            calls.append("list-presets")
            return []

        def get_permission_preset(self, preset):
            calls.append(f"get-preset {preset}")
            return []

    monkeypatch.setattr(
        "lib.config_manager.create_config_manager", lambda: FakeConfigManager()
    )

    result = runner.invoke(cli_mod.cli, ["config"], catch_exceptions=False)
    assert result.exit_code == 0


def test_set_pref_flags(cli_mod, runner, monkeypatch, tmp_path):
    calls = {}

    config_dir = tmp_path / "cfg"
    config_dir.mkdir()

    class FakeManager:
        def __init__(self, config_dir, verbose, emit_mode, emit_verbose):
            calls["init"] = (config_dir, verbose, emit_mode, emit_verbose)

        def set_preference(self, app, pref):
            calls["set_pref"] = (app, pref)
            return True

    monkeypatch.setattr("lib.manage.WrapperManager", FakeManager)

    result = runner.invoke(
        cli_mod.cli,
        [
            "--config-dir",
            str(config_dir),
            "--emit",
            "--emit-verbose",
            "set-pref",
            "org.example.App",
            "system",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert calls["init"] == (str(tmp_path / "cfg"), False, True, True)
    assert calls["set_pref"] == ("org.example.App", "system")


def test_list_with_all_flag(cli_mod, runner, monkeypatch):
    calls = {}

    class FakeManager:
        def __init__(self, config_dir, verbose):
            calls["init"] = (config_dir, verbose)

        def show_info(self, app_name):
            calls["info"] = app_name
            return True

        def display_wrappers(self):
            calls["listed"] = True

    monkeypatch.setattr("lib.manage.WrapperManager", FakeManager)

    result = runner.invoke(cli_mod.cli, ["list", "--all"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "listed" in calls


def test_monitor_emit_mode(cli_mod, runner):
    result = runner.invoke(cli_mod.cli, ["--emit", "monitor"], catch_exceptions=False)
    assert result.exit_code == 0


def test_no_magicmock_artifacts_created(tmp_path, monkeypatch):
    """Ensure running tests/CLI does not leave MagicMock artifact dirs."""

    # Sanity: no MagicMock dirs at start
    start = list(Path(".").glob("<MagicMock name='run.__getitem__()' id='*'>"))
    assert not start

    # Run a minimal generator init to ensure validation blocks bad inputs
    from lib.generate import WrapperGenerator

    # Use normal paths
    gen = WrapperGenerator(
        bin_dir=str(tmp_path / "bin"), config_dir=str(tmp_path / "cfg")
    )
    assert gen.bin_dir.exists()

    # Ensure still no MagicMock dirs
    after = list(Path(".").glob("<MagicMock name='run.__getitem__()' id='*'>"))
    assert not after


def test_manage_aliases_search_and_rm(monkeypatch):
    calls = {}

    class FakeManager:
        def __init__(self, config_dir, verbose=False, emit_mode=False):
            calls.setdefault("init", []).append((config_dir, verbose, emit_mode))

        def display_wrappers(self):
            calls["list"] = True

        def remove_wrapper(self, name, force=False):
            calls["remove"] = (name, force)
            return True

        def discover_features(self):
            calls["discover"] = True

        def cleanup_obsolete(self):
            calls["cleanup"] = 1
            return 1

        def log(self, message, level="info"):
            calls.setdefault("logs", []).append((level, message))

    monkeypatch.setattr("lib.manage.WrapperManager", FakeManager)

    original_argv = sys.argv
    try:
        sys.argv = ["fplaunch-manage", "search"]
        assert manage.main() == 0
        assert calls.get("discover") is True

        calls.clear()
        sys.argv = ["fplaunch-manage", "rm", "app"]
        assert manage.main() == 0
        assert calls.get("remove") == ("app", False)

        calls.clear()
        sys.argv = ["fplaunch-manage", "cleanup"]
        assert manage.main() == 0
        assert calls.get("cleanup") == 1
    finally:
        sys.argv = original_argv
