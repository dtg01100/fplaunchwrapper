#!/usr/bin/env python3
"""Install / uninstall lifecycle tests for the flatpak monitoring service.

Verifies that when a flatpak is installed or uninstalled, the monitoring
service correctly triggers wrapper regeneration. Covers both:

  * System flatpak installations: ``/var/lib/flatpak``
  * User flatpak installations: ``~/.local/share/flatpak`` and
    ``~/.var/app``

These tests directly exercise the public surface of
``lib.flatpak_monitor`` without relying on a real Flatpak binary or a
real ``fplaunch-generate`` script. The regeneration script is patched
out so the test is hermetic.

Hermeticity:
  * All filesystem paths live inside ``tmp_path``.
  * ``HOME``, ``XDG_*`` and ``FPWRAPPER_TEST_ENV`` are all set via
    ``monkeypatch`` (or via the ``isolated_home`` fixture).
  * No real ``flatpak`` or ``fplaunch-generate`` is invoked.
  * Tests pass in any order.
"""

from __future__ import annotations

import os
import subprocess as sp
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lib.flatpak_monitor import (
    WATCHDOG_AVAILABLE,
    FlatpakEventHandler,
    FlatpakMonitor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SYSTEM_FLATPAK = "/var/lib/flatpak"
USER_FLATPAK_REL = ".local/share/flatpak"
USER_VAR_APP_REL = ".var/app"


def _make_event(src_path: str, event_type: str = "created"):
    """Build a minimal watchdog-like event object."""
    e = MagicMock()
    e.src_path = src_path
    e.event_type = event_type
    e.is_directory = True
    return e


def _patch_should_process(monkeypatch, *paths: str):
    """Make ``should_process_event`` return True for any child of ``paths``.

    The real implementation resolves ``~/.local/share/flatpak`` against
    the real $HOME; in tests we work inside ``tmp_path`` so we need to
    override the watch list. This fake mirrors real semantics: a path is
    accepted if it sits at or below one of the allowed base directories.
    """
    allowed = [os.path.realpath(p) for p in paths]

    def fake(path):
        try:
            rp = os.path.realpath(str(path))
        except OSError:
            return False
        for base in allowed:
            if rp == base or rp.startswith(base + os.sep):
                return True
        return False

    monkeypatch.setattr("lib.flatpak_monitor.should_process_event", fake)


# ---------------------------------------------------------------------------
# Watch-path coverage
# ---------------------------------------------------------------------------


class TestWatchPathsBothUserAndSystem:
    """The monitor must observe both system and user flatpak dirs."""

    def test_watch_paths_includes_system_flatpak(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """``/var/lib/flatpak`` is added to the watch list when it exists."""
        # Force ``/var/lib/flatpak`` to "exist" for this test environment.
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        # Redirect ``~`` expansions into our temp dir.
        monkeypatch.setattr(
            "pathlib.Path.expanduser",
            lambda self: Path(str(tmp_path / USER_FLATPAK_REL)),
        )

        monitor = FlatpakMonitor(bin_dir=str(tmp_path / "bin"))
        paths = monitor.watch_paths

        assert (
            SYSTEM_FLATPAK in paths
        ), f"System flatpak dir {SYSTEM_FLATPAK} missing from watch_paths={paths!r}"

    def test_watch_paths_includes_user_flatpak(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """The per-user flatpak dir is added to the watch list."""
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        monkeypatch.setattr(
            "pathlib.Path.expanduser",
            lambda self: Path(str(tmp_path / USER_FLATPAK_REL)),
        )

        monitor = FlatpakMonitor(bin_dir=str(tmp_path / "bin"))
        paths = monitor.watch_paths

        user_flatpak_abs = str(tmp_path / USER_FLATPAK_REL)
        assert user_flatpak_abs in paths, f"User flatpak dir missing from watch_paths={paths!r}"

    def test_watch_paths_includes_user_var_app(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """``.var/app`` (user app data) is also watched."""
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        monkeypatch.setattr(
            "pathlib.Path.expanduser",
            lambda self: Path(str(tmp_path / USER_VAR_APP_REL)),
        )

        monitor = FlatpakMonitor(bin_dir=str(tmp_path / "bin"))
        paths = monitor.watch_paths

        user_var_app_abs = str(tmp_path / USER_VAR_APP_REL)
        assert user_var_app_abs in paths

    def test_watch_paths_returns_empty_when_no_flatpaks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """If neither system nor user dirs exist, watch_paths is empty."""
        monkeypatch.setattr("pathlib.Path.exists", lambda self: False)
        monkeypatch.setattr(
            "pathlib.Path.expanduser",
            lambda self: Path(str(tmp_path / "missing")),
        )

        monitor = FlatpakMonitor(bin_dir=str(tmp_path / "bin"))
        assert monitor.watch_paths == []


# ---------------------------------------------------------------------------
# Install (create) lifecycle
# ---------------------------------------------------------------------------


class TestWrapperCreateOnInstall:
    """Installing a flatpak should trigger wrapper regeneration.

    The contract: any change event that the monitor accepts fires the
    callback. ``fplaunch-generate`` reconciles wrapper state on each
    call (it is the source of truth for create-vs-destroy semantics).
    """

    def test_user_install_fires_callback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Create event under user flatpak dir fires the monitor callback."""
        user_flatpak = tmp_path / USER_FLATPAK_REL
        user_flatpak.mkdir(parents=True)
        new_app = user_flatpak / "app" / "org.mozilla.firefox"
        new_app.mkdir(parents=True)

        callback = MagicMock()
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            monitor = FlatpakMonitor(callback=callback, bin_dir=str(tmp_path / "bin"))
            monitor._on_flatpak_change("created", str(new_app))

        assert (
            callback.called
        ), "Callback should fire when a new flatpak is installed in the user dir"
        event_type, path = callback.call_args[0]
        assert event_type == "created"
        assert path == str(new_app)

    def test_system_install_fires_callback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Create event under /var/lib/flatpak fires the monitor callback."""
        new_app = tmp_path / "var" / "lib" / "flatpak" / "app" / "org.gimp.GIMP"
        new_app.mkdir(parents=True)

        callback = MagicMock()
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            monitor = FlatpakMonitor(callback=callback, bin_dir=str(tmp_path / "bin"))
            monitor._on_flatpak_change("created", str(new_app))

        assert callback.called
        event_type, path = callback.call_args[0]
        assert event_type == "created"
        assert path == str(new_app)

    def test_user_var_app_install_fires_callback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Installing into ``~/.var/app/<id>`` fires the callback."""
        user_var = tmp_path / USER_VAR_APP_REL
        user_var.mkdir(parents=True)
        new_app = user_var / "org.example.MyApp"
        new_app.mkdir(parents=True)

        callback = MagicMock()
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            monitor = FlatpakMonitor(callback=callback, bin_dir=str(tmp_path / "bin"))
            monitor._on_flatpak_change("created", str(new_app))

        assert callback.called

    def test_install_triggers_regen_for_app_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Install of an ``/app/<id>`` path triggers wrapper regeneration."""
        new_app = tmp_path / "var" / "lib" / "flatpak" / "app" / "org.example.Foo"
        new_app.mkdir(parents=True)

        regen = MagicMock(return_value=True)
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", regen):
            monitor = FlatpakMonitor(callback=MagicMock(), bin_dir=str(tmp_path / "bin"))
            monitor._on_flatpak_change("created", str(new_app))

        regen.assert_called_once()


# ---------------------------------------------------------------------------
# Uninstall (destroy) lifecycle
# ---------------------------------------------------------------------------


class TestWrapperDestroyOnUninstall:
    """Uninstalling a flatpak should trigger wrapper regeneration.

    The monitor doesn't track individual apps -- it triggers a full
    regeneration when any flatpak-related change happens. ``fplaunch-generate``
    reconciles by removing orphan wrappers. We test that the monitor fires
    the trigger on the uninstall event.
    """

    def test_user_uninstall_fires_callback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """A delete event under the user flatpak dir fires the callback."""
        user_flatpak = tmp_path / USER_FLATPAK_REL
        user_flatpak.mkdir(parents=True)
        app = user_flatpak / "app" / "org.mozilla.firefox"
        app.mkdir(parents=True)

        callback = MagicMock()
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            monitor = FlatpakMonitor(callback=callback, bin_dir=str(tmp_path / "bin"))
            monitor._on_flatpak_change("deleted", str(app))

        assert callback.called
        event_type, path = callback.call_args[0]
        assert event_type == "deleted"
        assert path == str(app)

    def test_system_uninstall_fires_callback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """A delete event under /var/lib/flatpak fires the callback."""
        app = tmp_path / "var" / "lib" / "flatpak" / "app" / "org.gimp.GIMP"
        app.mkdir(parents=True)

        callback = MagicMock()
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            monitor = FlatpakMonitor(callback=callback, bin_dir=str(tmp_path / "bin"))
            monitor._on_flatpak_change("deleted", str(app))

        assert callback.called
        event_type, _ = callback.call_args[0]
        assert event_type == "deleted"

    def test_user_var_app_uninstall_fires_callback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """A delete under ~/.var/app fires the callback."""
        user_var = tmp_path / USER_VAR_APP_REL
        user_var.mkdir(parents=True)
        app = user_var / "org.example.MyApp"
        app.mkdir(parents=True)

        callback = MagicMock()
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            monitor = FlatpakMonitor(callback=callback, bin_dir=str(tmp_path / "bin"))
            monitor._on_flatpak_change("deleted", str(app))

        assert callback.called

    def test_uninstall_triggers_regen_for_app_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Uninstall of an ``/app/<id>`` path triggers regeneration."""
        app = tmp_path / "var" / "lib" / "flatpak" / "app" / "org.example.Foo"
        app.mkdir(parents=True)

        regen = MagicMock(return_value=True)
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", regen):
            monitor = FlatpakMonitor(callback=MagicMock(), bin_dir=str(tmp_path / "bin"))
            monitor._on_flatpak_change("deleted", str(app))

        regen.assert_called_once()


# ---------------------------------------------------------------------------
# Event filtering: only flatpak paths reach the callback
# ---------------------------------------------------------------------------


class TestEventFilteringIgnoresUnrelatedPaths:
    """The watchdog-style ``_on_change`` hook filters out non-flatpak paths.

    Note: ``_on_change`` (watchdog entry point) is the public path-filter;
    ``_on_flatpak_change`` (direct) intentionally fires the callback for
    whatever path is passed.
    """

    @pytest.mark.parametrize(
        "unrelated_path",
        [
            "/tmp/random_file",
            "/home/user/Documents/foo.txt",
            "/var/log/syslog",
            "/etc/passwd",
        ],
    )
    def test_unrelated_paths_do_not_reach_callback(self, unrelated_path: str, tmp_path: Path):
        """Paths outside flatpak dirs are ignored at the watchdog hook."""
        callback = MagicMock()
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            monitor = FlatpakMonitor(callback=callback, bin_dir=str(tmp_path / "bin"))
            monitor._on_change(_make_event(unrelated_path, "created"))

        assert not callback.called, f"Callback should NOT fire for {unrelated_path}"

    def test_flatpak_path_reaches_callback_at_watchdog_hook(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """A flatpak-path event delivered to ``_on_change`` fires the callback."""
        user_flatpak = tmp_path / USER_FLATPAK_REL
        user_flatpak.mkdir(parents=True)
        new_app = user_flatpak / "app" / "org.mozilla.firefox"
        new_app.mkdir(parents=True)
        _patch_should_process(monkeypatch, str(user_flatpak))

        callback = MagicMock()
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            monitor = FlatpakMonitor(callback=callback, bin_dir=str(tmp_path / "bin"))
            monitor._on_change(_make_event(str(new_app), "created"))

        assert callback.called


# ---------------------------------------------------------------------------
# Event-handler integration: watchdog-style events flow through the queue
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
class TestEventHandlerInstallUninstall:
    """End-to-end: watchdog events flow through FlatpakEventHandler into the
    monitor's callback, for both install and uninstall events.
    """

    def _drive_handler_to_flush(self, handler: FlatpakEventHandler) -> None:
        """Force the handler to flush without waiting on the timer.

        The handler's flush respects a 2s cooldown. To make the test
        deterministic, set ``last_event_time`` to 0 so the first flush
        bypasses the cooldown.
        """
        handler.last_event_time = 0
        handler._flush_pending_events()

    def test_user_install_event_reaches_callback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Install event under user flatpak dir reaches the monitor callback."""
        user_flatpak = tmp_path / USER_FLATPAK_REL
        user_flatpak.mkdir(parents=True)
        new_app = user_flatpak / "app" / "org.mozilla.firefox"
        new_app.mkdir(parents=True)
        _patch_should_process(monkeypatch, str(user_flatpak))

        results: list[tuple[str, str]] = []
        monitor = FlatpakMonitor(
            callback=lambda e, p: results.append((e, p)),
            bin_dir=str(tmp_path / "bin"),
        )
        handler = FlatpakEventHandler(callback=monitor._on_flatpak_change)
        handler.batch_window = 0.05

        from watchdog.events import FileCreatedEvent

        handler.on_created(FileCreatedEvent(str(new_app)))
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            self._drive_handler_to_flush(handler)

        assert results, "Install event should reach the monitor callback"
        event_type, path = results[0]
        assert event_type == "created"
        assert path == str(new_app)

    def test_system_uninstall_event_reaches_callback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Uninstall event under /var/lib/flatpak reaches the monitor callback."""
        app = tmp_path / "var" / "lib" / "flatpak" / "app" / "org.gimp.GIMP"
        app.mkdir(parents=True)
        _patch_should_process(monkeypatch, str(app.parent))

        results: list[tuple[str, str]] = []
        monitor = FlatpakMonitor(
            callback=lambda e, p: results.append((e, p)),
            bin_dir=str(tmp_path / "bin"),
        )
        handler = FlatpakEventHandler(callback=monitor._on_flatpak_change)
        handler.batch_window = 0.05

        from watchdog.events import FileDeletedEvent

        handler.on_deleted(FileDeletedEvent(str(app)))
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            self._drive_handler_to_flush(handler)

        assert results
        event_type, path = results[0]
        assert event_type == "deleted"
        assert path == str(app)

    def test_user_install_then_uninstall_yields_two_callbacks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Install then uninstall of the same app fires two distinct callbacks."""
        user_flatpak = tmp_path / USER_FLATPAK_REL
        user_flatpak.mkdir(parents=True)
        new_app = user_flatpak / "app" / "org.example.App"
        new_app.mkdir(parents=True)
        _patch_should_process(monkeypatch, str(user_flatpak))

        results: list[tuple[str, str]] = []
        monitor = FlatpakMonitor(
            callback=lambda e, p: results.append((e, p)),
            bin_dir=str(tmp_path / "bin"),
        )
        handler = FlatpakEventHandler(callback=monitor._on_flatpak_change)
        handler.batch_window = 0.05

        from watchdog.events import FileCreatedEvent, FileDeletedEvent

        # Install
        handler.on_created(FileCreatedEvent(str(new_app)))
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            self._drive_handler_to_flush(handler)
        # Cooldown must pass between two flushes.
        handler.last_event_time = 0

        # Uninstall
        handler.on_deleted(FileDeletedEvent(str(new_app)))
        with patch.object(FlatpakMonitor, "_regenerate_wrappers", return_value=True):
            self._drive_handler_to_flush(handler)

        types = [t for t, _ in results]
        assert "created" in types
        assert "deleted" in types
        assert len(results) == 2


# ---------------------------------------------------------------------------
# End-to-end: events trigger fplaunch-generate execution
# ---------------------------------------------------------------------------


class TestEndToEndTriggersFplaunchGenerate:
    """When a flatpak is installed/uninstalled, the monitor runs
    ``fplaunch-generate`` to reconcile wrappers.
    """

    def _setup_fake_generate(self, monkeypatch, tmp_path, returncode=0, stderr=""):
        """Write a fake ``fplaunch-generate`` script and patch subprocess.run."""
        captured: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured.append(list(cmd))
            return sp.CompletedProcess(args=cmd, returncode=returncode, stderr=stderr)

        monkeypatch.setattr("lib.flatpak_monitor.subprocess.run", fake_run)
        fake_script = tmp_path / "fplaunch-generate"
        fake_script.write_text("#!/bin/sh\n")
        fake_script.chmod(0o755)
        monkeypatch.setattr("shutil.which", lambda _: str(fake_script))
        return captured

    def test_install_event_runs_fplaunch_generate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """An install event runs the fplaunch-generate script."""
        captured = self._setup_fake_generate(monkeypatch, tmp_path)
        monitor = FlatpakMonitor(bin_dir=str(tmp_path / "bin"))
        assert monitor._regenerate_wrappers() is True
        assert captured, "subprocess.run was not invoked"
        assert captured[0] == [str(tmp_path / "fplaunch-generate")]

    def test_uninstall_event_runs_fplaunch_generate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """An uninstall event also runs fplaunch-generate (to remove orphans)."""
        captured = self._setup_fake_generate(monkeypatch, tmp_path)
        monitor = FlatpakMonitor(bin_dir=str(tmp_path / "bin"))
        assert monitor._regenerate_wrappers() is True
        assert captured
        assert captured[0] == [str(tmp_path / "fplaunch-generate")]

    def test_failing_generate_returns_false(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """If fplaunch-generate returns non-zero, regeneration reports failure."""
        self._setup_fake_generate(monkeypatch, tmp_path, returncode=1, stderr="boom")
        monitor = FlatpakMonitor(bin_dir=str(tmp_path / "bin"))
        assert monitor._regenerate_wrappers() is False

    def test_end_to_end_install_flow_runs_generate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Full flow: install event -> callback fires -> generate runs."""
        captured = self._setup_fake_generate(monkeypatch, tmp_path)

        user_flatpak = tmp_path / USER_FLATPAK_REL
        user_flatpak.mkdir(parents=True)
        new_app = user_flatpak / "app" / "org.example.App"
        new_app.mkdir(parents=True)

        callback = MagicMock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(tmp_path / "bin"))
        monitor._on_flatpak_change("created", str(new_app))

        assert callback.called
        assert captured, "fplaunch-generate was not invoked"
        assert captured[0] == [str(tmp_path / "fplaunch-generate")]

    def test_end_to_end_uninstall_flow_runs_generate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Full flow: uninstall event -> callback fires -> generate runs."""
        captured = self._setup_fake_generate(monkeypatch, tmp_path)

        app = tmp_path / "var" / "lib" / "flatpak" / "app" / "org.example.App"
        app.mkdir(parents=True)

        callback = MagicMock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(tmp_path / "bin"))
        monitor._on_flatpak_change("deleted", str(app))

        assert callback.called
        assert captured


# ---------------------------------------------------------------------------
# Observer schedule: monitor must schedule on both user and system dirs
# ---------------------------------------------------------------------------


class TestObserverSchedulesBothPaths:
    """The watchdog observer must be scheduled on every watch path."""

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_start_schedules_observer_on_both_user_and_system(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """start_monitoring schedules the observer on every watch path."""
        fake_system = tmp_path / "var" / "lib" / "flatpak"
        fake_system.mkdir(parents=True)
        user_flatpak = tmp_path / USER_FLATPAK_REL
        user_flatpak.mkdir(parents=True)
        user_var = tmp_path / USER_VAR_APP_REL
        user_var.mkdir(parents=True)

        monkeypatch.setattr(
            FlatpakMonitor,
            "_get_watch_paths",
            lambda self: [str(fake_system), str(user_flatpak), str(user_var)],
        )

        mock_observer = MagicMock()
        with patch("lib.flatpak_monitor.Observer", return_value=mock_observer):
            monitor = FlatpakMonitor(bin_dir=str(tmp_path / "bin"))
            assert monitor.start_monitoring() is True

        scheduled_paths = {call.args[1] for call in mock_observer.schedule.call_args_list}
        expected = {str(fake_system), str(user_flatpak), str(user_var)}
        assert (
            scheduled_paths == expected
        ), f"Expected schedule calls for {expected}, got {scheduled_paths}"
        mock_observer.start.assert_called_once()
        monitor.stop_monitoring()
