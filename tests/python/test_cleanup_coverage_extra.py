#!/usr/bin/env python3
"""Extra coverage tests for lib/cleanup.py uncovered branches.

Targeted gap regions (line numbers from coverage report):
- 41-42:    safety import fallback (except ImportError: pass)
- 158-159:  FileNotFoundError in _scan_wrapper_directory
- 171:      scripts list in _handle_wrapper_file
- 184-186:  OSError/RuntimeError in _handle_wrapper_symlink
- 262-263:  fplaunch files in /usr/local/share system completion dirs
- 304-305:  get_cleanup_summary return dict
- 380-381:  per-file backup error capture
- 405:      data_files > MAX_BACKUP_FILES warning
- 419-421:  backup error logging
- 457-478:  _cleanup_systemd_units (systemctl stop/disable/daemon-reload, unit removal)
- 485-498:  _cleanup_cron_entries (filter + install new crontab)
- 506:      symlinks removal
- 509:      scripts removal
- 513:      lib_dir removal
- 518:      completion files removal
- 526:      man pages removal
- 533-534:  man1 subdir rmdir
- 537-538:  parent man dir rmdir
- 543-544:  config_dir removal
- 565-567:  _remove_directory shutil.rmtree error path
- 579-580:  run() returns 0 when confirm_cleanup returns False
- 588:      run() returns 1 when perform_cleanup returns False
- 608:      cleanup() returns False when confirm_cleanup returns False
- 611:      cleanup() return bool(perform_cleanup()) path
- 631-633:  cleanup_app OSError/PermissionError catch
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.cleanup import CleanupConfig, WrapperCleanup, main


@pytest.fixture
def temp_env(monkeypatch):
    """Isolated HOME + bin/config/data dirs for cleanup tests."""
    temp_dir = Path(tempfile.mkdtemp(prefix="fp_cleanup_extra_"))
    home = temp_dir / "home"
    bin_dir = temp_dir / "bin"
    config_dir = temp_dir / "config"
    data_dir = temp_dir / "data"
    for d in (home, bin_dir, config_dir, data_dir):
        d.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    yield {
        "temp_dir": temp_dir,
        "home": home,
        "bin_dir": bin_dir,
        "config_dir": config_dir,
        "data_dir": data_dir,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


def make_cleanup(env, **kwargs):
    """Build a WrapperCleanup pointed at isolated paths."""
    return WrapperCleanup(
        config=CleanupConfig(
            bin_dir=str(env["bin_dir"]),
            config_dir=str(env["config_dir"]),
            data_dir=str(env["data_dir"]),
            **kwargs,
        )
    )


# === 41-42: safety import fallback ========================================


class TestSafetyImportFallback:
    """Lines 41-42: except ImportError: pass for safety.is_wrapper_file."""

    def test_safety_unavailable_marks_utils_unavailable(self):
        """When safety cannot be imported, UTILS_AVAILABLE is False and is_wrapper_file is None."""
        import lib.cleanup

        orig_safety = sys.modules.get("lib.safety")
        orig_cleanup = sys.modules.get("lib.cleanup")

        class _FakeSafety:
            def __getattr__(self, name):  # pragma: no cover - body runs at import
                raise ImportError(f"simulated missing safety.{name}")

        sys.modules["lib.safety"] = _FakeSafety()
        try:
            reloaded = importlib.reload(orig_cleanup)
            assert reloaded.UTILS_AVAILABLE is False
            assert reloaded.is_wrapper_file is None
        finally:
            if orig_safety is not None:
                sys.modules["lib.safety"] = orig_safety
            else:
                sys.modules.pop("lib.safety", None)
            importlib.reload(orig_cleanup)
            if orig_cleanup is not None:
                sys.modules["lib.cleanup"] = orig_cleanup
            globals()["WrapperCleanup"] = sys.modules["lib.cleanup"].WrapperCleanup
            globals()["CleanupConfig"] = sys.modules["lib.cleanup"].CleanupConfig
            globals()["main"] = sys.modules["lib.cleanup"].main


# === 158-159: FileNotFoundError in _scan_wrapper_directory =================


class TestScanWrapperDirectoryRace:
    """Lines 158-159: FileNotFoundError swallowed in iterdir()."""

    def test_iterdir_raises_file_not_found(self, temp_env):
        """When iterdir raises FNF, scan should not raise and adds nothing."""
        cleanup = make_cleanup(temp_env)
        with patch.object(Path, "exists", lambda _p: True), patch.object(
            Path, "iterdir", side_effect=FileNotFoundError("vanished")
        ):
            cleanup._scan_wrapper_directory()
        assert cleanup.cleanup_items["wrappers"] == []
        assert cleanup.cleanup_items["symlinks"] == []


# === 171: scripts list ====================================================


class TestHandleWrapperFileScripts:
    """Line 171: fplaunch-* script names go to the scripts list."""

    @pytest.mark.parametrize(
        "script_name",
        [
            "fplaunch-manage",
            "fplaunch-generate",
            "fplaunch-setup-systemd",
            "fplaunch-cleanup",
        ],
    )
    def test_known_script(self, temp_env, script_name):
        cleanup = make_cleanup(temp_env)
        f = temp_env["bin_dir"] / script_name
        cleanup._handle_wrapper_file(f)
        assert f in cleanup.cleanup_items["wrappers"]
        assert f in cleanup.cleanup_items["scripts"]


# === 184-186: symlink readlink errors =====================================


class TestSymlinkReadlinkErrors:
    """Lines 184-186: OSError/RuntimeError on readlink is logged and swallowed."""

    def test_readlink_oserror_swallowed(self, temp_env):
        cleanup = make_cleanup(temp_env)
        link = temp_env["bin_dir"] / "broken_link"
        link.symlink_to("missing_target")
        with patch("lib.cleanup.os.readlink", side_effect=OSError("dangling")):
            cleanup._handle_wrapper_symlink(link)
        assert link not in cleanup.cleanup_items["symlinks"]

    def test_valid_symlink_added_to_symlinks(self, temp_env):
        """A symlink whose target is a real wrapper gets added to symlinks (line 184)."""
        cleanup = make_cleanup(temp_env)
        real = temp_env["bin_dir"] / "real_wrapper"
        real.write_text(
            '#!/bin/bash\n# Generated by fplaunchwrapper\nNAME="real"\nID="org.test.real"\n'
        )
        real.chmod(0o755)
        link = temp_env["bin_dir"] / "my_alias"
        link.symlink_to("real_wrapper")
        # Call _handle_wrapper_symlink directly (the scan's is_file() check
        # would otherwise match the symlink-to-file first and route it to
        # _handle_wrapper_file instead).
        cleanup._handle_wrapper_symlink(link)
        assert link in cleanup.cleanup_items["symlinks"]


# === 262-263: system completion dirs =======================================


class TestScanCompletionSystemDirs:
    """Lines 262-263: fplaunch files in /usr/local/share/... dirs."""

    def test_system_completion_file_collected(self, temp_env):
        """A fplaunch file in a 'system' completion dir is found."""
        sys_dir = temp_env["temp_dir"] / "bash_comp"
        sys_dir.mkdir(parents=True)
        comp_file = sys_dir / "fplaunch-system"
        comp_file.write_text("x")

        target_str = "/usr/local/share/bash-completion/completions"
        real_exists = Path.exists
        real_glob = Path.glob

        def fake_exists(self):
            if str(self) == target_str:
                return True
            return real_exists(self)

        def fake_glob(self, pattern):
            if str(self) == target_str:
                return [comp_file]
            return list(real_glob(self, pattern))

        cleanup = make_cleanup(temp_env)
        with patch.object(Path, "exists", fake_exists), patch.object(
            Path, "glob", fake_glob
        ):
            cleanup._scan_completion_files()

        assert comp_file in cleanup.cleanup_items["completion_files"]


# === 304-305: get_cleanup_summary =========================================


class TestGetCleanupSummary:
    """Lines 304-305: get_cleanup_summary returns a dict with three keys."""

    def test_summary_keys_and_types(self, temp_env):
        cleanup = make_cleanup(temp_env)
        summary = cleanup.get_cleanup_summary()
        assert set(summary.keys()) == {"wrappers", "preferences", "data_files"}
        assert all(isinstance(v, int) for v in summary.values())

    def test_summary_counts_items(self, temp_env):
        (temp_env["bin_dir"] / "firefox").write_text("x")
        (temp_env["config_dir"] / "firefox.pref").write_text("y")
        (temp_env["data_dir"] / "data1").write_text("z")
        cleanup = make_cleanup(temp_env)
        s = cleanup.get_cleanup_summary()
        assert s["wrappers"] == 1
        assert s["preferences"] == 1
        assert s["data_files"] == 1


# === 380-381, 405, 419-421: backup paths ==================================


class TestBackupPaths:
    """Lines 380-381, 405, 419-421: backup errors and >MAX warning."""

    def test_backup_per_file_error_logged(self, temp_env, capsys):
        """shutil.copy2 failure -> backup_errors -> warning logged, had_errors=True."""
        cleanup = make_cleanup(temp_env, create_backup=True)
        fake_wrapper = Path("/nonexistent/this/path/wrapper_xyz")
        cleanup.cleanup_items["wrappers"] = [fake_wrapper]
        cleanup.cleanup_items["preferences"] = []
        cleanup.cleanup_items["data_files"] = []
        cleanup.backup_dir = temp_env["temp_dir"] / "backup_err"

        def boom(*args, **kwargs):
            raise OSError("disk full")

        with patch("lib.cleanup.shutil.copy2", side_effect=boom):
            ok = cleanup.perform_cleanup()
        captured = capsys.readouterr()
        assert ok is False
        assert cleanup.had_errors is True
        assert "Failed to backup" in captured.err

    def test_backup_data_files_over_max_warns(self, temp_env, capsys):
        """1001 data files -> warning message logged to stderr."""
        cleanup = make_cleanup(temp_env, create_backup=True)
        cleanup.cleanup_items["data_files"] = [
            Path(f"/fake/data_{i}") for i in range(1001)
        ]
        cleanup.cleanup_items["wrappers"] = []
        cleanup.cleanup_items["preferences"] = []
        cleanup.backup_dir = temp_env["temp_dir"] / "backup_max"
        with patch("lib.cleanup.shutil.copy2"):
            cleanup.perform_cleanup()
        captured = capsys.readouterr()
        assert "Backup limited to 1000" in captured.err


# === 457-478: _cleanup_systemd_units =======================================


class TestCleanupSystemdUnits:
    """Lines 457-478: _cleanup_systemd_units with systemctl available."""

    def test_with_systemctl_runs_stop_disable_reload(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        unit = temp_env["temp_dir"] / "fplaunch-wrapper.service"
        unit.parent.mkdir(parents=True, exist_ok=True)
        unit.write_text("[Unit]\n")
        cleanup.cleanup_items["systemd_units"] = [unit]
        with patch("lib.cleanup.shutil.which", return_value="/bin/systemctl"), patch(
            "lib.cleanup.run_systemctl"
        ) as mock_run:
            cleanup._cleanup_systemd_units()
        assert mock_run.call_count == 3
        assert not unit.exists()

    def test_dry_run_skips_systemctl(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=True)
        unit = temp_env["temp_dir"] / "fplaunch-wrapper.service"
        unit.parent.mkdir(parents=True, exist_ok=True)
        unit.write_text("[Unit]\n")
        cleanup.cleanup_items["systemd_units"] = [unit]
        with patch("lib.cleanup.shutil.which", return_value="/bin/systemctl"), patch(
            "lib.cleanup.run_systemctl"
        ) as mock_run:
            cleanup._cleanup_systemd_units()
        mock_run.assert_not_called()
        assert unit.exists()

    def test_empty_units_list_noop(self, temp_env):
        cleanup = make_cleanup(temp_env)
        cleanup.cleanup_items["systemd_units"] = []
        with patch("lib.cleanup.run_systemctl") as mock_run:
            cleanup._cleanup_systemd_units()
        mock_run.assert_not_called()

    def test_no_systemctl_available(self, temp_env):
        """When systemctl is not on PATH, the unit file is still removed."""
        cleanup = make_cleanup(temp_env, dry_run=False)
        unit = temp_env["temp_dir"] / "fplaunch-wrapper.service"
        unit.parent.mkdir(parents=True, exist_ok=True)
        unit.write_text("[Unit]\n")
        cleanup.cleanup_items["systemd_units"] = [unit]
        with patch("lib.cleanup.shutil.which", return_value=None), patch(
            "lib.cleanup.run_systemctl"
        ) as mock_run:
            cleanup._cleanup_systemd_units()
        mock_run.assert_not_called()
        assert not unit.exists()


# === 485-498: _cleanup_cron_entries =======================================


class TestCleanupCronEntries:
    """Lines 485-498: _cleanup_cron_entries filters fplaunch lines."""

    def test_filters_fplaunch_lines(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        cleanup.cleanup_items["cron_entries"] = [
            "0 * * * * /usr/bin/fplaunch-generate"
        ]
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="0 * * * * /usr/bin/fplaunch-generate\n# other\n",
            stderr="",
        )
        with patch("lib.cleanup.shutil.which", return_value="/bin/crontab"), patch(
            "lib.cleanup.run_crontab", return_value=result
        ) as mock_run:
            cleanup._cleanup_cron_entries()
        assert mock_run.call_count == 2
        second = mock_run.call_args_list[1]
        assert "-" in second.args
        assert "fplaunch" not in second.kwargs.get("input_text", "")

    def test_dry_run_skips_crontab(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=True)
        cleanup.cleanup_items["cron_entries"] = ["line"]
        with patch("lib.cleanup.shutil.which", return_value="/bin/crontab"), patch(
            "lib.cleanup.run_crontab"
        ) as mock_run:
            cleanup._cleanup_cron_entries()
        mock_run.assert_not_called()

    def test_subprocess_error_swallowed(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False)
        cleanup.cleanup_items["cron_entries"] = ["line"]
        with patch("lib.cleanup.shutil.which", return_value="/bin/crontab"), patch(
            "lib.cleanup.run_crontab",
            side_effect=subprocess.CalledProcessError(1, "crontab"),
        ):
            cleanup._cleanup_cron_entries()

    def test_oserror_swallowed(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False)
        cleanup.cleanup_items["cron_entries"] = ["line"]
        with patch("lib.cleanup.shutil.which", return_value="/bin/crontab"), patch(
            "lib.cleanup.run_crontab", side_effect=OSError("gone")
        ):
            cleanup._cleanup_cron_entries()

    def test_crontab_l_nonzero(self, temp_env):
        """When crontab -l returns non-zero, the new crontab is not installed."""
        cleanup = make_cleanup(temp_env, dry_run=False)
        cleanup.cleanup_items["cron_entries"] = ["line"]
        result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="no crontab"
        )
        with patch("lib.cleanup.shutil.which", return_value="/bin/crontab"), patch(
            "lib.cleanup.run_crontab", return_value=result
        ) as mock_run:
            cleanup._cleanup_cron_entries()
        assert mock_run.call_count == 1


# === 506, 509, 513: _cleanup_wrappers_and_scripts ==========================


class TestCleanupWrappersAndScripts:
    """Lines 506, 509, 513: symlinks, scripts, lib_dir removal."""

    def test_wrappers_symlinks_scripts_removed(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        w = temp_env["bin_dir"] / "firefox"
        w.write_text("x")
        s = temp_env["bin_dir"] / "firefox-link"
        s.symlink_to("firefox")
        sc = temp_env["bin_dir"] / "fplaunch-manage"
        sc.write_text("y")
        cleanup.cleanup_items["wrappers"] = [w, s, sc]
        cleanup.cleanup_items["symlinks"] = [s]
        cleanup.cleanup_items["scripts"] = [sc]
        cleanup._cleanup_wrappers_and_scripts()
        assert not w.exists()
        assert not s.exists()
        assert not sc.exists()

    def test_lib_dir_removed(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        lib = temp_env["bin_dir"] / "lib"
        lib.mkdir()
        (lib / "m.py").write_text("x")
        cleanup._cleanup_wrappers_and_scripts()
        assert not lib.exists()

    def test_lib_dir_does_not_exist(self, temp_env):
        """When bin_dir/lib doesn't exist, no error."""
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        cleanup._cleanup_wrappers_and_scripts()


# === 518: _cleanup_completion_files =======================================


class TestCleanupCompletionFiles:
    """Line 518: completion files are removed."""

    def test_completion_files_removed(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        c = temp_env["temp_dir"] / "comp.bash"
        c.write_text("x")
        cleanup.cleanup_items["completion_files"] = [c]
        cleanup._cleanup_completion_files()
        assert not c.exists()


# === 526, 533-534, 537-538: _cleanup_man_pages =============================


class TestCleanupManPages:
    """Lines 526, 533-534, 537-538: man pages + empty dir cleanup."""

    def test_man_pages_and_empty_dirs_removed(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        man_dir = temp_env["home"] / ".local" / "share" / "man"
        man1 = man_dir / "man1"
        man1.mkdir(parents=True)
        man7 = man_dir / "man7"
        man7.mkdir(parents=True)
        f1 = man1 / "fplaunch-foo.1"
        f1.write_text("x")
        f7 = man7 / "fplaunchwrapper.bar.7"
        f7.write_text("y")
        cleanup.cleanup_items["man_pages"] = [f1, f7]
        cleanup._cleanup_man_pages()
        assert not f1.exists()
        assert not f7.exists()
        # Empty subdirs should be removed
        assert not man1.exists()
        assert not man7.exists()
        # Parent man dir should be empty and removed
        assert not man_dir.exists()


# === 543-544: _cleanup_config_dir ==========================================


class TestCleanupConfigDir:
    """Lines 543-544: config_dir is removed."""

    def test_config_dir_removed(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        cfg = temp_env["temp_dir"] / "configdir"
        cfg.mkdir()
        (cfg / "setting").write_text("x")
        cleanup.cleanup_items["config_dir"] = [cfg]
        cleanup._cleanup_config_dir()
        assert not cfg.exists()


# === 565-567: _remove_directory ============================================


class TestRemoveDirectory:
    """Lines 565-567: shutil.rmtree failure path."""

    def test_rmtree_error_sets_had_errors(self, temp_env):
        cleanup = make_cleanup(temp_env)
        d = temp_env["bin_dir"] / "sub"
        d.mkdir()
        with patch("lib.cleanup.shutil.rmtree", side_effect=OSError("blocked")):
            cleanup._remove_directory(d, "Removing")
        assert cleanup.had_errors is True

    def test_rmtree_success(self, temp_env):
        cleanup = make_cleanup(temp_env)
        d = temp_env["bin_dir"] / "sub2"
        d.mkdir()
        (d / "child").write_text("x")
        cleanup._remove_directory(d, "Removing")
        assert not d.exists()


# === 579-580: run() cancelled ==============================================


class TestRunCancellation:
    """Lines 579-580: run() returns 0 when confirm_cleanup returns False."""

    def test_run_cancelled_returns_zero(self, temp_env):
        """When confirm_cleanup returns False (user declined), run() returns 0."""
        # Need at least one item so confirm_cleanup actually asks
        (temp_env["bin_dir"] / "firefox").write_text("x")
        cleanup = make_cleanup(temp_env, interactive=True)
        with patch("lib.cleanup.Confirm.ask", return_value=False):
            assert cleanup.run() == 0


# === 588: run() returns 1 when perform_cleanup fails =======================


class TestRunPerformFailure:
    """Line 588: run() returns 1 when perform_cleanup returns False."""

    def test_run_returns_one_on_perform_failure(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        with patch.object(
            cleanup, "_cleanup_systemd_units", side_effect=OSError("boom")
        ):
            assert cleanup.run() == 1


# === 608: cleanup() cancelled ==============================================


class TestCleanupCancellation:
    """Line 608: cleanup() returns False when confirm_cleanup returns False."""

    def test_cleanup_returns_false_when_cancelled(self, temp_env):
        """When confirm_cleanup returns False (user declined), cleanup() returns False."""
        # Need at least one item so confirm_cleanup actually asks
        (temp_env["bin_dir"] / "firefox").write_text("x")
        cleanup = make_cleanup(temp_env, interactive=True)
        with patch("lib.cleanup.Confirm.ask", return_value=False):
            assert cleanup.cleanup() is False


# === 611: cleanup() runs perform_cleanup ==================================


class TestCleanupRunsPerform:
    """Line 611: cleanup() calls perform_cleanup and returns its boolean."""

    def test_cleanup_returns_true_on_success(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        assert cleanup.cleanup() is True

    def test_cleanup_returns_false_on_perform_failure(self, temp_env):
        """When perform_cleanup raises and is caught, cleanup() returns False."""
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        with patch.object(
            cleanup, "_cleanup_systemd_units", side_effect=OSError("boom")
        ):
            assert cleanup.cleanup() is False


# === 631-633: cleanup_app OSError catch ====================================


class TestCleanupAppErrors:
    """Lines 631-633: cleanup_app handles OSError/PermissionError on unlink."""

    def test_cleanup_app_oserror_returns_false(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        wrapper = temp_env["bin_dir"] / "firefox"
        wrapper.write_text("x")
        real_unlink = Path.unlink

        def fake_unlink(self, *args, **kwargs):
            if str(self) == str(wrapper):
                raise OSError("permission denied")
            return real_unlink(self, *args, **kwargs)

        with patch.object(Path, "unlink", fake_unlink):
            result = cleanup.cleanup_app("org.mozilla.firefox")
        assert result is False

    def test_cleanup_app_permissionerror_returns_false(self, temp_env):
        cleanup = make_cleanup(temp_env, dry_run=False, assume_yes=True)
        wrapper = temp_env["bin_dir"] / "chrome"
        wrapper.write_text("x")
        real_unlink = Path.unlink

        def fake_unlink(self, *args, **kwargs):
            if str(self) == str(wrapper):
                raise PermissionError("nope")
            return real_unlink(self, *args, **kwargs)

        with patch.object(Path, "unlink", fake_unlink):
            result = cleanup.cleanup_app("org.chromium.chrome")
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
