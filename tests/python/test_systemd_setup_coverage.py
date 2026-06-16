"""Additional coverage tests for ``lib.systemd_setup``.

These tests target the previously-uncovered code paths in
``lib/systemd_setup.py`` reported by the project coverage report
(specifically lines 138-161, 165-167, 196-197, 232-234, 263-294,
303-318, 327-328, 342-343, 351-353, 361-373, 390-391, 423-425,
442-443, 464-466, 476, 479-483).  The user-facing methods covered are
``list_all_units``, ``enable_app_service``, ``disable_app_service``,
``install_systemd_units``, ``disable_systemd_units``,
``list_app_services``, ``check_prerequisites``, ``check_systemd_status``,
``run`` and ``install_cron_job``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from lib.systemd_setup import SystemdSetup


# ---------------------------------------------------------------------------
# Local helpers (kept module-local so this file is hermetic and does not
# depend on the SystemdTestFixtures class in test_systemd_setup.py).
# ---------------------------------------------------------------------------


def _make_systemd_dir() -> tuple[Path, Path]:
    """Create a temp directory tree with a ``systemd/user`` subdir.

    Returns ``(parent_tmp, systemd_unit_dir)``.  The caller is responsible
    for removing ``parent_tmp`` when finished.
    """
    parent = Path(tempfile.mkdtemp(prefix="test_systemd_cov_"))
    systemd_dir = parent / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)
    return parent, systemd_dir


def _make_bin_dir() -> tuple[Path, Path]:
    """Create a temp bin directory containing a fake ``fplaunch-generate``."""
    parent = Path(tempfile.mkdtemp(prefix="test_bin_cov_"))
    bin_dir = parent / "bin"
    bin_dir.mkdir(exist_ok=True)
    wrapper = bin_dir / "fplaunch-generate"
    wrapper.write_text("#!/bin/bash\necho 'Generated wrappers'")
    wrapper.chmod(0o755)
    return parent, bin_dir


def _ok_proc() -> subprocess.CompletedProcess:
    """Return a successful CompletedProcess suitable for mocking ``systemctl``."""
    return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")


def _make_setup(systemd_dir: Path, *, emit: bool = False) -> SystemdSetup:
    """Construct a ``SystemdSetup`` whose ``systemd_unit_dir`` points at a temp dir."""
    from lib.systemd_setup import SystemdSetup

    parent_bin, bin_dir = _make_bin_dir()
    setup = SystemdSetup(
        bin_dir=str(bin_dir),
        wrapper_script=str(bin_dir / "fplaunch-generate"),
        emit_mode=emit,
    )
    setup.systemd_unit_dir = systemd_dir
    # Stash bin_dir for cleanup by the caller (we attach it on the setup
    # object so the caller can find it in the ``finally`` block).
    setup._cov_bin_dir_parent = parent_bin  # type: ignore[attr-defined]
    return setup


# ---------------------------------------------------------------------------
# list_all_units  (lines 355-373)
# ---------------------------------------------------------------------------


class TestListAllUnits:
    """Cover the ``systemd_unit_dir`` iteration and prefix/suffix filter."""

    def test_returns_empty_list_when_dir_missing(self):
        """If ``systemd_unit_dir`` does not exist, return ``[]``."""
        from lib.systemd_setup import SystemdSetup

        missing = Path(tempfile.mkdtemp(prefix="missing_listdir_")) / "systemd" / "user"
        setup = SystemdSetup(emit_mode=True)
        setup.systemd_unit_dir = missing

        assert setup.list_all_units() == []

    def test_returns_only_fplaunch_units_sorted(self):
        """Return only ``fplaunch-*.{service,timer,path}`` files, sorted."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=True)

            (systemd_dir / "fplaunch-wrapper.service").write_text("x")
            (systemd_dir / "fplaunch-wrapper.timer").write_text("x")
            (systemd_dir / "fplaunch-org.mozilla.Firefox.path").write_text("x")

            result = setup.list_all_units()
            assert result == [
                "fplaunch-org.mozilla.Firefox.path",
                "fplaunch-wrapper.service",
                "fplaunch-wrapper.timer",
            ]
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_skips_files_with_other_prefixes_or_suffixes(self):
        """Files that do not match ``fplaunch-*`` + known suffix are skipped."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=True)

            # Wrong prefix
            (systemd_dir / "other-wrapper.service").write_text("x")
            # Right prefix, wrong suffix
            (systemd_dir / "fplaunch-wrapper.txt").write_text("x")
            (systemd_dir / "fplaunch-wrapper.socket").write_text("x")
            # No suffix, no prefix
            (systemd_dir / "README").write_text("x")
            # A subdirectory should not be iterated into
            (systemd_dir / "fplaunch-sub").mkdir(exist_ok=True)
            (systemd_dir / "fplaunch-sub" / "inner.service").write_text("x")

            # The only thing that should be returned is the valid .service
            (systemd_dir / "fplaunch-valid.service").write_text("x")

            result = setup.list_all_units()
            assert result == ["fplaunch-valid.service"]
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# enable_app_service  (lines 375-425)
# ---------------------------------------------------------------------------


class TestEnableAppService:
    """Cover validation, emit mode, happy path, and the OSError branch."""

    def test_invalid_app_id_returns_false(self):
        """An invalid ``app_id`` causes ``validate_app_id`` to fail -> return False."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch("subprocess.run") as mock_run:
                result = setup.enable_app_service("../../../etc/passwd")

            assert result is False
            mock_run.assert_not_called()
            # No files were created.
            assert list(systemd_dir.iterdir()) == []
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_emit_mode_does_not_touch_filesystem(self):
        """In ``emit_mode``, the function logs EMIT and returns True without writing."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=True)

            with patch("subprocess.run") as mock_run:
                result = setup.enable_app_service("org.mozilla.Firefox")

            assert result is True
            mock_run.assert_not_called()
            assert list(systemd_dir.iterdir()) == []
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_happy_path_creates_service_file(self):
        """Valid id + mocked subprocess -> service file is created with expected content."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch("subprocess.run", return_value=_ok_proc()) as mock_run:
                result = setup.enable_app_service("org.mozilla.Firefox")

            assert result is True
            service_path = systemd_dir / "fplaunch-org.mozilla.Firefox.service"
            assert service_path.exists()
            content = service_path.read_text()
            assert "[Unit]" in content
            assert "Description=Wrapper for org.mozilla.Firefox" in content
            assert "ExecStart=flatpak run" in content
            # daemon-reload + enable calls happen
            assert mock_run.call_count >= 1
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_ensure_dir_oserror_returns_false(self):
        """If ``ensure_dir`` raises ``OSError``, return False and do not write any file."""
        from lib import systemd_setup as ssm

        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch.object(ssm, "ensure_dir", side_effect=OSError("permission denied")):
                with patch("subprocess.run") as mock_run:
                    result = setup.enable_app_service("org.mozilla.Firefox")

            assert result is False
            mock_run.assert_not_called()
            assert list(systemd_dir.iterdir()) == []
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_path_traversal_returns_false(self):
        """If ``check_path_traversal`` reports the resolved path escapes, return False."""
        from lib import systemd_setup as ssm

        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch.object(
                ssm,
                "check_path_traversal",
                return_value=(False, "escapes base dir"),
            ):
                with patch("subprocess.run") as mock_run:
                    result = setup.enable_app_service("org.mozilla.Firefox")

            assert result is False
            mock_run.assert_not_called()
            assert list(systemd_dir.iterdir()) == []
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# disable_app_service  (lines 427-466)
# ---------------------------------------------------------------------------


class TestDisableAppService:
    """Cover validation, emit mode, and the idempotent (no-file) branch."""

    def test_invalid_app_id_returns_false(self):
        """An invalid ``app_id`` is rejected before any filesystem work."""
        from lib.systemd_setup import SystemdSetup

        parent_bin, bin_dir = _make_bin_dir()
        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )

            with patch("subprocess.run") as mock_run:
                result = setup.disable_app_service("not a real id!")

            assert result is False
            mock_run.assert_not_called()
        finally:
            shutil.rmtree(parent_bin)

    def test_emit_mode_does_not_touch_filesystem(self):
        """In ``emit_mode``, the function logs EMIT and returns True without writing."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=True)

            with patch("subprocess.run") as mock_run:
                result = setup.disable_app_service("org.mozilla.Firefox")

            assert result is True
            mock_run.assert_not_called()
            assert list(systemd_dir.iterdir()) == []
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_disable_nonexistent_unit_returns_true(self):
        """Disabling a unit that does not exist is idempotent and returns True."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch("subprocess.run", return_value=_ok_proc()):
                # No service file was ever created.
                result = setup.disable_app_service("org.example.never-installed")

            assert result is True
            # Nothing was created on disk.
            assert list(systemd_dir.iterdir()) == []
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_path_traversal_returns_false(self):
        """If ``check_path_traversal`` reports the resolved path escapes, return False."""
        from lib import systemd_setup as ssm

        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch.object(
                ssm,
                "check_path_traversal",
                return_value=(False, "escapes base dir"),
            ):
                with patch("subprocess.run") as mock_run:
                    result = setup.disable_app_service("org.mozilla.Firefox")

            assert result is False
            mock_run.assert_not_called()
            assert list(systemd_dir.iterdir()) == []
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_disable_app_service_oserror_returns_false(self):
        """If ``subprocess.run`` raises ``OSError``, ``disable_app_service`` returns False."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch(
                "subprocess.run",
                side_effect=OSError("systemctl crashed"),
            ):
                result = setup.disable_app_service("org.mozilla.Firefox")

            assert result is False
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_disable_app_service_removes_existing_file(self):
        """If the service file already exists on disk, it is unlinked."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            service_path = systemd_dir / "fplaunch-org.mozilla.Firefox.service"
            service_path.write_text("[Unit]\nDescription=existing\n")

            with patch("subprocess.run", return_value=_ok_proc()):
                result = setup.disable_app_service("org.mozilla.Firefox")

            assert result is True
            assert not service_path.exists()
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# install_systemd_units  (lines 136-161)
# ---------------------------------------------------------------------------


class TestInstallSystemdUnits:
    """Cover emit mode, happy path, and systemctl-missing branch."""

    def test_emit_mode_logs_and_skips(self):
        """In ``emit_mode``, the function logs EMIT and returns True."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=True)

            with patch("subprocess.run") as mock_run:
                result = setup.install_systemd_units()

            assert result is True
            mock_run.assert_not_called()
            assert list(systemd_dir.iterdir()) == []
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_happy_path_creates_service_and_timer(self):
        """Service + timer files are created on disk and ``systemctl`` is invoked."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch("subprocess.run", return_value=_ok_proc()) as mock_run:
                result = setup.install_systemd_units(cron_interval=12)

            assert result is True
            service_path = systemd_dir / "fplaunch-wrapper.service"
            timer_path = systemd_dir / "fplaunch-wrapper.timer"
            assert service_path.exists()
            assert timer_path.exists()
            assert "Type=oneshot" in service_path.read_text()
            assert "OnUnitActiveSec=12h" in timer_path.read_text()
            # daemon-reload + enable
            assert mock_run.call_count >= 2
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_systemctl_not_available_returns_false(self):
        """If ``subprocess.run`` raises ``FileNotFoundError`` (no systemctl), return False."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch(
                "subprocess.run",
                side_effect=FileNotFoundError("systemctl not found"),
            ):
                result = setup.install_systemd_units()

            assert result is False
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# disable_systemd_units  (lines 320-353)
# ---------------------------------------------------------------------------


class TestDisableSystemdUnits:
    """Cover emit mode, happy path, and the no-files-present no-op."""

    def test_emit_mode_logs_and_skips(self):
        """In ``emit_mode``, existing files are NOT removed."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=True)

            # Pre-create the unit files
            (systemd_dir / "fplaunch-wrapper.service").write_text("x")
            (systemd_dir / "fplaunch-wrapper.timer").write_text("x")

            with patch("subprocess.run") as mock_run:
                result = setup.disable_systemd_units()

            assert result is True
            mock_run.assert_not_called()
            # Files are still there because we're in emit mode.
            assert (systemd_dir / "fplaunch-wrapper.service").exists()
            assert (systemd_dir / "fplaunch-wrapper.timer").exists()
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_happy_path_removes_files(self):
        """Service, timer, and path files are all removed on disk."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            (systemd_dir / "fplaunch-wrapper.service").write_text("x")
            (systemd_dir / "fplaunch-wrapper.timer").write_text("x")
            (systemd_dir / "fplaunch-wrapper.path").write_text("x")

            with patch("subprocess.run", return_value=_ok_proc()) as mock_run:
                result = setup.disable_systemd_units()

            assert result is True
            assert not (systemd_dir / "fplaunch-wrapper.service").exists()
            assert not (systemd_dir / "fplaunch-wrapper.timer").exists()
            assert not (systemd_dir / "fplaunch-wrapper.path").exists()
            # Multiple systemctl invocations (disable x2, daemon-reload)
            assert mock_run.call_count >= 3
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_no_files_present_is_noop(self):
        """If no unit files exist, the function returns True and does not raise."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch("subprocess.run", return_value=_ok_proc()):
                result = setup.disable_systemd_units()

            assert result is True
            assert list(systemd_dir.iterdir()) == []
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_disable_systemd_units_oserror_returns_false(self):
        """If ``subprocess.run`` raises ``OSError``, ``disable_systemd_units`` returns False."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch(
                "subprocess.run",
                side_effect=OSError("systemctl crashed"),
            ):
                result = setup.disable_systemd_units()

            assert result is False
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# list_app_services  (lines 468-485)
# ---------------------------------------------------------------------------


class TestListAppServices:
    """Cover the empty-dir and iteration branches of ``list_app_services``."""

    def test_returns_empty_when_dir_missing(self):
        """If ``systemd_unit_dir`` does not exist, return ``[]``."""
        from lib.systemd_setup import SystemdSetup

        missing = Path(tempfile.mkdtemp(prefix="missing_listapp_")) / "systemd" / "user"
        setup = SystemdSetup(emit_mode=True)
        setup.systemd_unit_dir = missing

        assert setup.list_app_services() == []

    def test_extracts_app_ids_from_service_names(self):
        """Strip the ``fplaunch-`` prefix and ``.service`` suffix and sort the result."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=True)

            (systemd_dir / "fplaunch-org.mozilla.Firefox.service").write_text("x")
            (systemd_dir / "fplaunch-org.gimp.GIMP.service").write_text("x")
            # Wrong suffix - should be excluded.
            (systemd_dir / "fplaunch-org.mozilla.Firefox.timer").write_text("x")

            result = setup.list_app_services()
            assert result == ["org.gimp.GIMP", "org.mozilla.Firefox"]
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# check_prerequisites  (lines 296-318)
# ---------------------------------------------------------------------------


class TestCheckPrerequisites:
    """Cover the three failure branches and the happy path."""

    def test_flatpak_missing_returns_false(self):
        """``shutil.which('flatpak')`` is None -> return False."""
        parent_bin, bin_dir = _make_bin_dir()
        try:
            setup = _make_setup(_make_systemd_dir()[1], emit=False)
            # Replace the bin_dir set by _make_setup with ours so cleanup is correct.
            setup.bin_dir = bin_dir
            setup._cov_bin_dir_parent = parent_bin  # type: ignore[attr-defined]

            with patch("shutil.which", return_value=None):
                result = setup.check_prerequisites()

            assert result is False
        finally:
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_wrapper_script_missing_returns_false(self):
        """Wrapper script not in PATH and not on disk -> return False."""
        parent_bin, bin_dir = _make_bin_dir()
        try:
            setup = _make_setup(_make_systemd_dir()[1], emit=False)
            setup.bin_dir = bin_dir
            setup._cov_bin_dir_parent = parent_bin  # type: ignore[attr-defined]
            setup.wrapper_script = "/nonexistent/fplaunch-generate"

            def which_side_effect(cmd: str) -> str | None:
                if cmd == "flatpak":
                    return "/usr/bin/flatpak"
                return None

            with patch("shutil.which", side_effect=which_side_effect):
                result = setup.check_prerequisites()

            assert result is False
        finally:
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_bin_dir_not_writable_returns_false(self):
        """If ``os.access(bin_dir, os.W_OK)`` is False, return False."""
        if os.geteuid() == 0:
            pytest.skip("Running as root; bin_dir is always writable")

        parent_bin, bin_dir = _make_bin_dir()
        try:
            setup = _make_setup(_make_systemd_dir()[1], emit=False)
            setup.bin_dir = bin_dir
            setup._cov_bin_dir_parent = parent_bin  # type: ignore[attr-defined]
            setup.wrapper_script = str(bin_dir / "fplaunch-generate")

            def which_side_effect(cmd: str) -> str | None:
                if cmd == "flatpak":
                    return "/usr/bin/flatpak"
                if cmd == setup.wrapper_script:
                    return setup.wrapper_script
                return None

            bin_dir.chmod(0o555)
            try:
                with patch("shutil.which", side_effect=which_side_effect):
                    result = setup.check_prerequisites()
                assert result is False
            finally:
                bin_dir.chmod(0o755)
        finally:
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_all_prerequisites_met_returns_true(self):
        """If flatpak and the wrapper script are available and the bin dir is writable, return True."""
        parent_bin, bin_dir = _make_bin_dir()
        try:
            setup = _make_setup(_make_systemd_dir()[1], emit=False)
            setup.bin_dir = bin_dir
            setup._cov_bin_dir_parent = parent_bin  # type: ignore[attr-defined]

            def which_side_effect(cmd: str) -> str | None:
                if cmd == "flatpak":
                    return "/usr/bin/flatpak"
                if cmd == setup.wrapper_script:
                    return setup.wrapper_script
                return None

            with patch("shutil.which", side_effect=which_side_effect):
                result = setup.check_prerequisites()

            assert result is True
        finally:
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# check_systemd_status  (lines 257-294)
# ---------------------------------------------------------------------------


class TestCheckSystemdStatus:
    """Cover the no-systemctl early return and the main status-fetching path."""

    def test_systemctl_not_available_returns_all_false(self):
        """If ``shutil.which('systemctl')`` is None, return the default all-false dict."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup(emit_mode=True)

        with patch("shutil.which", return_value=None):
            result = setup.check_systemd_status()

        assert result == {
            "service": {"exists": False, "enabled": False, "active": False},
            "timer": {"exists": False, "enabled": False, "active": False},
        }

    def test_status_reports_existence_and_state(self):
        """With systemctl mocked, the dict is populated with exists/enabled/active flags."""
        from lib.systemd_setup import SystemdSetup

        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            # The service and timer files do not exist yet
            def which_side_effect(cmd: str) -> str | None:
                if cmd == "systemctl":
                    return "/usr/bin/systemctl"
                return None

            with patch("shutil.which", side_effect=which_side_effect):
                with patch(
                    "subprocess.run",
                    return_value=_ok_proc(),
                ) as mock_run:
                    result = setup.check_systemd_status()

            # With no unit files on disk, the existence flags should be False
            assert result["service"]["exists"] is False
            assert result["timer"]["exists"] is False
            # ``is-enabled`` returned 0 so enabled should be True
            assert result["service"]["enabled"] is True
            assert result["timer"]["enabled"] is True
            # ``is-active`` stdout was empty so active should be False
            assert result["service"]["active"] is False
            assert result["timer"]["active"] is False
            # systemctl was called at least 4 times (2 is-enabled + 2 is-active)
            assert mock_run.call_count >= 4
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_status_reports_files_present(self):
        """If the unit files exist on disk, the ``exists`` flags are True."""
        from lib.systemd_setup import SystemdSetup

        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            (systemd_dir / "fplaunch-wrapper.service").write_text("x")
            (systemd_dir / "fplaunch-wrapper.timer").write_text("x")

            def which_side_effect(cmd: str) -> str | None:
                if cmd == "systemctl":
                    return "/usr/bin/systemctl"
                return None

            with patch("shutil.which", side_effect=which_side_effect):
                with patch("subprocess.run", return_value=_ok_proc()):
                    result = setup.check_systemd_status()

            assert result["service"]["exists"] is True
            assert result["timer"]["exists"] is True
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_status_swallows_oserror(self):
        """If ``subprocess.run`` raises ``OSError``, the result dict is still returned."""
        from lib.systemd_setup import SystemdSetup

        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            def which_side_effect(cmd: str) -> str | None:
                if cmd == "systemctl":
                    return "/usr/bin/systemctl"
                return None

            with patch("shutil.which", side_effect=which_side_effect):
                with patch(
                    "subprocess.run",
                    side_effect=OSError("dbus connection lost"),
                ):
                    result = setup.check_systemd_status()

            # No exception is raised, dict shape is preserved.
            assert "service" in result
            assert "timer" in result
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# run()  (lines 163-167)
# ---------------------------------------------------------------------------


class TestRun:
    """Cover the install-failure and install-success branches of ``run``."""

    def test_run_returns_1_on_install_failure(self):
        """If ``install_systemd_units`` returns False, ``run`` returns 1."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch.object(setup, "install_systemd_units", return_value=False):
                assert setup.run() == 1
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_run_returns_0_on_success(self):
        """If ``install_systemd_units`` returns True, ``run`` returns 0."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch.object(setup, "install_systemd_units", return_value=True):
                assert setup.run() == 0
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# install_cron_job  (lines 186-234)
# ---------------------------------------------------------------------------


class TestInstallCronJob:
    """Cover the emit-mode and the no-cron-available branches."""

    def test_emit_mode_logs_and_skips(self):
        """In ``emit_mode``, ``install_cron_job`` returns True without writing anything."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=True)

            with patch("shutil.which", return_value="/usr/bin/crontab"):
                with patch("subprocess.run") as mock_run:
                    result = setup.install_cron_job()

            assert result is True
            mock_run.assert_not_called()
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_cron_unavailable_returns_false(self):
        """If ``shutil.which('crontab')`` is None in non-emit mode, return False."""
        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)

            with patch("shutil.which", return_value=None):
                result = setup.install_cron_job()

            assert result is False
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_cron_already_exists_skips_rewrite(self):
        """If the matching cron entry already exists, do not call crontab ``-``."""
        from lib.systemd_setup import SystemdSetup

        parent, systemd_dir = _make_systemd_dir()
        parent_bin, bin_dir = _make_bin_dir()
        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            cron_script = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
            cron_script = cron_script / "cron" / "fplaunch-wrapper.sh"
            cron_script.parent.mkdir(parents=True, exist_ok=True)
            cron_script.write_text("#!/bin/bash\ntrue\n")
            cron_script.chmod(0o755)

            existing_cron = f"0 */6 * * * {cron_script}\n"

            calls: list[list[str]] = []

            def run_side_effect(cmd, *args, **kwargs):
                calls.append(list(cmd))
                if cmd[1:] == ["-l"]:
                    return subprocess.CompletedProcess(
                        args=cmd, returncode=0, stdout=existing_cron, stderr=""
                    )
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

            with patch("shutil.which", return_value="/usr/bin/crontab"):
                with patch("subprocess.run", side_effect=run_side_effect):
                    result = setup.install_cron_job()

            assert result is True
            # The ``-l`` listing call happened, but the ``-`` write call did not.
            assert any(c[1:] == ["-l"] for c in calls)
            assert not any(c[1:] == ["-"] for c in calls)
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(parent_bin)

    def test_cron_install_writes_new_entry(self, monkeypatch: pytest.MonkeyPatch):
        """If no matching entry exists, ``_run_crontab('-', input_text=...)`` is called."""
        from lib.systemd_setup import SystemdSetup

        parent, systemd_dir = _make_systemd_dir()
        parent_bin, bin_dir = _make_bin_dir()
        try:
            # Force XDG_CONFIG_HOME so the test uses an isolated cron dir.
            xdg = parent / "xdg"
            xdg.mkdir(exist_ok=True)
            monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))

            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            calls: list[list[str]] = []

            def run_side_effect(cmd, *args, **kwargs):
                calls.append(list(cmd))
                if cmd[1:] == ["-l"]:
                    # ``-l`` returns 1 (no existing crontab).
                    return subprocess.CompletedProcess(
                        args=cmd, returncode=1, stdout="", stderr=""
                    )
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

            with patch("shutil.which", return_value="/usr/bin/crontab"):
                with patch("subprocess.run", side_effect=run_side_effect):
                    result = setup.install_cron_job()

            assert result is True
            # ``-l`` listing call happened, AND the ``-`` write call happened.
            assert any(c[1:] == ["-l"] for c in calls)
            assert any(c[1:] == ["-"] for c in calls)
            # The cron script was created on disk.
            cron_script = xdg / "cron" / "fplaunch-wrapper.sh"
            assert cron_script.exists()
            assert os.access(cron_script, os.X_OK)
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(parent_bin)

    def test_cron_install_oserror_returns_false(self):
        """If the cron script write raises ``OSError``, ``install_cron_job`` returns False."""
        from lib.systemd_setup import SystemdSetup

        parent, systemd_dir = _make_systemd_dir()
        parent_bin, bin_dir = _make_bin_dir()
        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script=str(bin_dir / "fplaunch-generate"),
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            with patch("shutil.which", return_value="/usr/bin/crontab"):
                with patch(
                    "pathlib.Path.mkdir",
                    side_effect=OSError("disk full"),
                ):
                    with patch("subprocess.run", return_value=_ok_proc()):
                        result = setup.install_cron_job()

            assert result is False
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(parent_bin)


# ---------------------------------------------------------------------------
# main() and CLI  (lines 498-524)
# ---------------------------------------------------------------------------


class TestCreateUnits:
    """Cover the three thin ``create_*_unit`` wrapper methods (lines 236-246)."""

    def test_create_service_unit(self):
        from lib.systemd_setup import SystemdSetup

        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)
            content = setup.create_service_unit()
            assert "[Unit]" in content
            assert "[Service]" in content
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_create_timer_unit(self):
        from lib.systemd_setup import SystemdSetup

        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)
            content = setup.create_timer_unit()
            assert "[Timer]" in content
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]

    def test_create_path_unit(self):
        from lib.systemd_setup import SystemdSetup

        parent, systemd_dir = _make_systemd_dir()
        try:
            setup = _make_setup(systemd_dir, emit=False)
            content = setup.create_path_unit()
            assert "[Path]" in content
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(setup._cov_bin_dir_parent)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# _find_wrapper_script  (lines 74-93) - init-time fallback
# ---------------------------------------------------------------------------


class TestFindWrapperScript:
    """Cover the ``_find_wrapper_script`` common-paths fallback loop."""

    def test_init_falls_back_to_name_only(self):
        """If neither PATH nor the common paths contain the script, return the bare name."""
        from lib.systemd_setup import SystemdSetup

        parent_bin, bin_dir = _make_bin_dir()
        try:
            with patch("shutil.which", return_value=None):
                # Make all the common-path existence/access checks fail.
                with patch("pathlib.Path.is_file", return_value=False):
                    setup = SystemdSetup(
                        bin_dir=str(bin_dir),
                        wrapper_script=None,
                        emit_mode=True,
                    )

            assert setup.wrapper_script == "fplaunch-generate"
        finally:
            shutil.rmtree(parent_bin)

    def test_init_finds_via_common_path(self):
        """If the script is in a common location, ``_find_wrapper_script`` returns that path.

        With shutil.which patched to return None, the function iterates over
        common_paths and returns the first one where Path.is_file() AND
        os.access() succeed. The test patches both; the first common_path
        candidate matches.
        """
        from lib.systemd_setup import SystemdSetup

        parent_bin, bin_dir = _make_bin_dir()
        try:
            with patch("shutil.which", return_value=None):
                with patch("pathlib.Path.is_file", return_value=True), \
                     patch("os.access", return_value=True):
                    setup = SystemdSetup(
                        bin_dir=str(bin_dir),
                        wrapper_script=None,
                        emit_mode=True,
                    )

            # The function returns the first matching common_paths entry when
            # the file exists and is executable.
            assert setup.wrapper_script == "/usr/bin/fplaunch-generate"
        finally:
            shutil.rmtree(parent_bin)


# ---------------------------------------------------------------------------
# _detect_flatpak_bin_dir  (lines 95-105) - init-time fallback
# ---------------------------------------------------------------------------


class TestDetectFlatpakBinDir:
    """Cover the return-empty-string branch of ``_detect_flatpak_bin_dir``."""

    def test_returns_empty_string_when_no_flatpak_dir(self):
        """If neither standard flatpak bin dir exists, the attribute is set to ``''``."""
        from lib.systemd_setup import SystemdSetup

        parent_bin, bin_dir = _make_bin_dir()
        try:
            with patch("pathlib.Path.is_dir", return_value=False):
                setup = SystemdSetup(
                    bin_dir=str(bin_dir),
                    wrapper_script=str(bin_dir / "fplaunch-generate"),
                    emit_mode=True,
                )

            assert setup.flatpak_bin_dir == ""
        finally:
            shutil.rmtree(parent_bin)


# ---------------------------------------------------------------------------
# main() and CLI  (lines 498-524)
# ---------------------------------------------------------------------------


class TestMain:
    """Smoke test for the ``main()`` CLI entry point."""

    def test_main_runs_with_emit_mode(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
        """``main()`` in emit mode runs the install path and returns 0."""
        from lib import systemd_setup

        parent, systemd_dir = _make_systemd_dir()
        parent_bin, bin_dir = _make_bin_dir()
        try:
            monkeypatch.setattr(
                "sys.argv",
                [
                    "fplaunch-setup-systemd",
                    "--bin-dir",
                    str(bin_dir),
                    "--script",
                    str(bin_dir / "fplaunch-generate"),
                ],
            )

            # Force the systemd dir to point at our temp directory by patching the
            # module function used by ``main()`` (or by ``SystemdSetup.__init__``).
            monkeypatch.setattr(systemd_setup, "get_systemd_unit_dir", lambda: systemd_dir)

            rc = systemd_setup.main()
            assert rc == 0
        finally:
            shutil.rmtree(parent)
            shutil.rmtree(parent_bin)
