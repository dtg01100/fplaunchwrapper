#!/usr/bin/env python3
"""Regression tests for bugs found during code review.

Each test is named after the bug it guards against to make failures easy
to diagnose.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. validate_script_path security bypass
#    Bug: the raise ValueError inside the try-block was immediately caught by
#    the except ValueError: pass clause, so sensitive directories were never
#    rejected.
# ---------------------------------------------------------------------------


class TestValidateScriptPathSecurityBypass:
    """validate_script_path must reject scripts in sensitive directories."""

    @pytest.fixture()
    def pydantic_app_prefs_class(self):
        """Return PydanticAppPreferences or skip if pydantic is unavailable."""
        try:
            # Access the inner class through the module-level attribute
            import lib.config_manager as cm

            return cm.PydanticAppPreferences
        except (ImportError, AttributeError):
            pytest.skip("PydanticAppPreferences not available")

    @pytest.mark.parametrize(
        "path",
        [
            "/etc/malicious_script",
            "/usr/bin/evil",
            "/bin/backdoor",
            "/sbin/rootkit",
            "/boot/bootloader",
            "/root/hidden",
        ],
    )
    def test_sensitive_directories_are_rejected(self, pydantic_app_prefs_class, path):
        """Scripts in sensitive system directories must raise ValueError."""
        from pydantic import ValidationError

        # Patch file-system checks so the sensitive-dir guard is the only thing
        # standing between us and a ValidationError.
        with patch("os.path.isfile", return_value=True), patch(
            "os.access", return_value=True
        ):
            with pytest.raises(ValidationError) as exc_info:
                pydantic_app_prefs_class(pre_launch_script=path)

            assert "sensitive system directory" in str(exc_info.value)

    def test_user_home_script_is_accepted(self, pydantic_app_prefs_class):
        """Scripts in the user's home directory should not be rejected."""
        home = str(Path.home() / ".local" / "bin" / "pre_launch.sh")
        with patch("os.path.isfile", return_value=True), patch(
            "os.access", return_value=True
        ):
            # Should not raise
            obj = pydantic_app_prefs_class(pre_launch_script=home)
            assert obj.pre_launch_script == home


# ---------------------------------------------------------------------------
# 2. portal_launcher --wait flag position
#    Bug: --wait was appended after the app ID and was therefore passed to the
#    application rather than to `flatpak run`.
# ---------------------------------------------------------------------------


class TestPortalLauncherWaitFlagPosition:
    """--wait must appear before the app ID in the flatpak run command."""

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_wait_before_app_id_portal(self, mock_run: MagicMock) -> None:
        """launch_with_portal: --wait must precede the app ID."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0)
        launch_with_portal("org.example.App", wait=True)

        cmd = mock_run.call_args[0][0]
        app_index = cmd.index("org.example.App")
        wait_index = cmd.index("--wait")
        assert wait_index < app_index, (
            f"--wait (index {wait_index}) must come before app ID (index {app_index})"
        )

    @patch("lib.portal_launcher.subprocess.run")
    def test_wait_before_app_id_direct(self, mock_run: MagicMock) -> None:
        """launch_direct: --wait must precede the app ID."""
        from lib.portal_launcher import launch_direct

        mock_run.return_value = MagicMock(returncode=0)
        launch_direct("org.example.App", wait=True)

        cmd = mock_run.call_args[0][0]
        app_index = cmd.index("org.example.App")
        wait_index = cmd.index("--wait")
        assert wait_index < app_index, (
            f"--wait (index {wait_index}) must come before app ID (index {app_index})"
        )

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_app_args_still_after_app_id(self, mock_run: MagicMock) -> None:
        """Application arguments must remain after the app ID even when wait=True."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0)
        launch_with_portal("org.example.App", args=["--url", "https://example.com"], wait=True)

        cmd = mock_run.call_args[0][0]
        app_index = cmd.index("org.example.App")
        url_index = cmd.index("--url")
        assert url_index > app_index, (
            "Application arguments must appear after the app ID"
        )

    @patch("lib.portal_launcher.subprocess.run")
    @patch("lib.portal_launcher.FLATPAK_SPAWN_PATH", "/usr/bin/flatpak-spawn")
    def test_no_wait_flag_when_wait_false(self, mock_run: MagicMock) -> None:
        """When wait=False, --wait must not appear in the command."""
        from lib.portal_launcher import launch_with_portal

        mock_run.return_value = MagicMock(returncode=0)
        launch_with_portal("org.example.App", wait=False)

        cmd = mock_run.call_args[0][0]
        assert "--wait" not in cmd


# ---------------------------------------------------------------------------
# 3. CLI pref and discover aliases must work via ctx.invoke
# Bug: both aliases called their target Click Command object as a plain
# function, which re-invoked Click's argument parsing machinery.
# ---------------------------------------------------------------------------


class TestCliAliasesUseCtxInvoke:
    """pref and discover aliases must delegate via ctx.invoke."""

    def _run_cli(self, args: list[str]):
        """Run CLI command and return result."""
        from click.testing import CliRunner

        from lib.cli import cli

        runner = CliRunner()
        return runner.invoke(cli, args, catch_exceptions=False)

    def test_pref_alias_invokes_set_pref_logic(self, tmp_path: Path) -> None:
        """fplaunch pref <wrapper> <pref> must behave like fplaunch set-pref."""
        pytest.importorskip("lib.manage")

        with patch(
            "lib.manage.WrapperManager.set_preference", return_value=True
        ), patch("lib.manage.WrapperManager.__init__", return_value=None):
            # Also patch the import inside cli.py
            result = self._run_cli(["pref", "firefox", "flatpak"])

            # The command should exit 0 (or at least not crash with TypeError)
            assert result.exit_code == 0

    def test_discover_alias_invokes_search_logic(self, tmp_path: Path) -> None:
        """fplaunch discover must behave like fplaunch search."""
        with patch(
            "lib.manage.WrapperManager.display_wrappers", return_value=None
        ), patch("lib.manage.WrapperManager.__init__", return_value=None):
            result = self._run_cli(["discover"])

            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# 4. Cron duplicate-detection field index
# Bug: code checked parts[3] (month field, always "*") instead of
# parts[1] (hour field, "*/N") so duplicates were never detected.
# ---------------------------------------------------------------------------


class TestCronDuplicateDetection:
    """install_cron_job must not add a duplicate entry."""

    def _make_systemd_setup(self, tmp_path: Path):
        """Return a SystemdSetup instance pointing at tmp_path."""
        try:
            from lib.systemd_setup import SystemdSetup
        except ImportError:
            pytest.skip("SystemdSetup not available")

        return SystemdSetup(
            bin_dir=str(tmp_path / "bin"),
            config_dir=str(tmp_path / "config"),
            data_dir=str(tmp_path / "data"),
        )

    def test_duplicate_cron_not_added(self, tmp_path: Path) -> None:
        """Calling install_cron_job twice must not add a second cron line."""
        setup = self._make_systemd_setup(tmp_path)
        cron_interval = 6

        # install_cron_job writes its script to ~/.config/cron/fplaunch-wrapper.sh
        existing_script = Path.home() / ".config" / "cron" / "fplaunch-wrapper.sh"
        existing_line = f"0 */{cron_interval} * * * {existing_script}"

        added_lines: list[str] = []

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            if isinstance(cmd, list) and cmd[-1] == "-l":
                # Return a crontab that already contains the entry
                result.returncode = 0
                result.stdout = existing_line + "\n"
            elif isinstance(cmd, list) and cmd[-1] == "-":
                # Record what would be written
                added_lines.append(kwargs.get("input", ""))
                result.returncode = 0
                result.stdout = ""
            else:
                result.returncode = 0
                result.stdout = ""
            return result

        with patch("shutil.which", return_value="/usr/bin/crontab"):
            with patch("subprocess.run", side_effect=fake_run):
                setup.install_cron_job(cron_interval=cron_interval)

        # The crontab writer (-) should NOT have been called because the entry
        # already exists.
        assert added_lines == [], (
            "install_cron_job incorrectly added a duplicate cron entry"
        )

    def test_fresh_cron_is_added(self, tmp_path: Path) -> None:
        """install_cron_job must add an entry when none exists yet."""
        setup = self._make_systemd_setup(tmp_path)

        added_lines: list[str] = []

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            if cmd[-1] == "-l":
                result.returncode = 0
                result.stdout = ""  # empty crontab
            elif cmd[-1] == "-":
                added_lines.append(kwargs.get("input", ""))
                result.returncode = 0
                result.stdout = ""
            else:
                result.returncode = 0
                result.stdout = ""
            return result

        with patch("shutil.which", return_value="/usr/bin/crontab"):
            with patch("subprocess.run", side_effect=fake_run):
                setup.install_cron_job(cron_interval=6)

        assert added_lines, "install_cron_job must write a cron entry when none exists"
        assert "fplaunch" in added_lines[0] or "regenerate" in added_lines[0]


# ---------------------------------------------------------------------------
# 5. _check_preference_override must handle "auto"
# Bug: "auto" fell through both if/elif branches silently, leaving the
# preference unacknowledged.
# ---------------------------------------------------------------------------


class TestCheckPreferenceOverrideWithAuto:
    """'auto' preference must be handled explicitly (not lost silently)."""

    def _make_launcher(self, tmp_path: Path, pref_value: str):
        """Create test launcher instance with specified preference."""
        try:
            from lib.launch import AppLauncher
        except ImportError:
            pytest.skip("AppLauncher not available")

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        pref_file = config_dir / "firefox.pref"
        pref_file.write_text(pref_value)
        launcher = AppLauncher.__new__(AppLauncher)
        launcher.app_name = "firefox"
        launcher.config_dir = config_dir
        return launcher

    def test_auto_preference_is_no_op(self, tmp_path: Path) -> None:
        """'auto' preference must leave wrapper_path and source unchanged."""
        launcher = self._make_launcher(tmp_path, "auto")
        original_path = Path("/usr/bin/firefox")

        result_path, result_source = launcher._check_preference_override(
            original_path, "system"
        )

        assert result_path == original_path, "'auto' must not clear wrapper_path"
        assert result_source == "system", "'auto' must not change source"


# ---------------------------------------------------------------------------
# 6. flatpak_monitor observer thread must not sleep
# Bug: time.sleep() was called inside the watchdog observer callback,
# blocking event delivery for the entire debounce period.
# ---------------------------------------------------------------------------


class TestFlatpakMonitorNoSleepInCallback:
    """_on_flatpak_change must not block the observer thread with sleep()."""

    def test_on_flatpak_change_does_not_sleep(self) -> None:
        """time.sleep must not be called inside _on_flatpak_change."""
        try:
            from lib.flatpak_monitor import FlatpakMonitor
        except ImportError:
            pytest.skip("FlatpakMonitor not available")

        monitor = FlatpakMonitor.__new__(FlatpakMonitor)
        monitor.config = {"debounce": 1}
        monitor.callback = None

        with patch.object(
            monitor, "_should_regenerate_wrappers", return_value=False
        ), patch("lib.flatpak_monitor.time.sleep") as mock_sleep:
            monitor._on_flatpak_change("modified", "/some/path")

            mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# 7. cleanup.py _handle_wrapper_symlink Python 3.8 compatibility
# Bug: item.readlink() was used, which is only available from Python 3.9.
# Fix: use os.readlink() which exists since Python 3.3.
# ---------------------------------------------------------------------------


class TestCleanupReadlinkCompatibility:
    """WrapperCleanup._handle_wrapper_symlink must use os.readlink."""

    def test_handle_wrapper_symlink_uses_os_readlink(
        self, tmp_path: Path
    ) -> None:
        """Symlink handling must not call Path.readlink (Python 3.9+)."""
        try:
            from lib.cleanup import CleanupConfig, WrapperCleanup
        except ImportError:
            pytest.skip("WrapperCleanup not available")

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        target = bin_dir / "firefox"
        target.write_text("#!/bin/bash\nflatpak run org.mozilla.Firefox\n")
        symlink = bin_dir / "firefox-shortcut"
        symlink.symlink_to(target)

        cleanup = WrapperCleanup(CleanupConfig(bin_dir=str(bin_dir)))

        # Patch Path.readlink to raise AttributeError (simulating Python 3.8)
        with patch.object(
            Path, "readlink", side_effect=AttributeError("no readlink"), create=True
        ):
            # Should not raise even without Path.readlink
            try:
                cleanup._handle_wrapper_symlink(symlink)
            except AttributeError:
                pytest.fail(
                    "_handle_wrapper_symlink called Path.readlink (Python 3.9+) "
                    "instead of os.readlink (compatible with Python 3.8+)"
                )


# ---------------------------------------------------------------------------
# 8. Version consistency: pyproject.toml must match __init__.py
# ---------------------------------------------------------------------------


class TestVersionConsistency:
    """pyproject.toml version must match the runtime __version__ attribute."""

    def test_pyproject_version_matches_package_version(self) -> None:
        """pyproject.toml version must equal lib.__version__."""
        import tomllib

        pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        if not pyproject.exists():
            pytest.skip("pyproject.toml not found")

        with pyproject.open("rb") as f:
            data = tomllib.load(f)

        toml_version = data["project"]["version"]

        try:
            import lib
            module_version = lib.__version__
        except (ImportError, AttributeError):
            pytest.skip("lib.__version__ not available")

        assert toml_version == module_version, (
            f"pyproject.toml version ({toml_version}) != lib.__version__ ({module_version})"
        )
