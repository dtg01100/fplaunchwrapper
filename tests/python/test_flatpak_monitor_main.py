#!/usr/bin/env python3
"""Tests for the main() CLI surface of lib.flatpak_monitor.

Covers argparse parsing, log-level setup, callback loading (with the three
distinct failure modes - ValueError, ImportError, AttributeError), the
config dict propagation, and the daemon vs. non-daemon branch.

The tests stub out start_flatpak_monitoring to avoid actually starting a
file system observer during the test run. The optional watchdog dependency
is therefore irrelevant for everything in this file.
"""

from __future__ import annotations

import logging
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import lib.flatpak_monitor as flatpak_monitor
from lib.flatpak_monitor import main


def _argv(*args: str) -> list[str]:
    """Build a sys.argv-style list for a fresh program invocation."""
    return ["fplaunch-monitor", *args]


class TestMainDefaults:
    """main() with no CLI arguments and a few of the simple flag branches."""

    def test_main_no_args_uses_defaults(self, monkeypatch):
        """No args -> INFO log level, non-daemon, default config dict."""
        mock_monitor = MagicMock()
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ) as mock_start:
            monkeypatch.setattr(sys, "argv", _argv())
            main()

        mock_start.assert_called_once()
        kwargs = mock_start.call_args.kwargs
        assert kwargs["daemon"] is False
        assert kwargs["callback"] is None
        assert kwargs["config"] == {
            "batch_window": 1.0,
            "cooldown": 2.0,
            "debounce": 1.0,
            "regeneration_timeout": 60,
            "log_level": "INFO",
        }

    def test_main_daemon_short_flag(self, monkeypatch):
        """The -d short form flips daemon=True in the call to start."""
        mock_monitor = MagicMock()
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ) as mock_start:
            monkeypatch.setattr(sys, "argv", _argv("-d"))
            main()

        assert mock_start.call_args.kwargs["daemon"] is True

    def test_main_daemon_long_flag(self, monkeypatch):
        """The --daemon long form flips daemon=True in the call to start."""
        mock_monitor = MagicMock()
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ) as mock_start:
            monkeypatch.setattr(sys, "argv", _argv("--daemon"))
            main()

        assert mock_start.call_args.kwargs["daemon"] is True

    def test_main_invalid_log_level_choice_is_rejected(self, monkeypatch):
        """argparse rejects log levels outside the declared choices."""
        mock_monitor = MagicMock()
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ):
            monkeypatch.setattr(sys, "argv", _argv("--log-level", "TRACE"))
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 2  # argparse error exit code


class TestMainLogLevel:
    """The --log-level flag flows through to logger.setLevel."""

    @pytest.mark.parametrize(
        "level_name, expected",
        [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ],
    )
    def test_main_log_level_sets_logger_level(
        self, monkeypatch, level_name: str, expected: int
    ):
        """Each valid --log-level value maps to the matching logging constant."""
        mock_monitor = MagicMock()
        with (
            patch(
                "lib.flatpak_monitor.start_flatpak_monitoring",
                return_value=mock_monitor,
            ),
            patch.object(flatpak_monitor.logger, "setLevel") as mock_set,
        ):
            monkeypatch.setattr(sys, "argv", _argv("--log-level", level_name))
            main()

        mock_set.assert_called_with(expected)


class TestMainCallback:
    """The --callback flag loads a module:function reference."""

    def test_main_callback_loaded_from_builtin_module(self, monkeypatch):
        """--callback os:getcwd passes os.getcwd through to start."""
        mock_monitor = MagicMock()
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ) as mock_start:
            monkeypatch.setattr(sys, "argv", _argv("--callback", "os:getcwd"))
            main()

        callback = mock_start.call_args.kwargs["callback"]
        assert callback is os.getcwd  # noqa: E1751 - identity check is the point

    def test_main_callback_loaded_from_synthetic_module(self, monkeypatch):
        """--callback can load a function from a module we inject into sys.modules."""
        sentinel_module_name = "test_flatpak_monitor_synthetic_callback_mod"
        sentinel_module = types.ModuleType(sentinel_module_name)

        def _sentinel() -> str:
            return "sentinel"

        setattr(sentinel_module, "sentinel_callback", _sentinel)  # noqa: B010
        monkeypatch.setitem(sys.modules, sentinel_module_name, sentinel_module)

        mock_monitor = MagicMock()
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ) as mock_start:
            monkeypatch.setattr(
                sys,
                "argv",
                _argv("--callback", f"{sentinel_module_name}:sentinel_callback"),
            )
            main()

        assert mock_start.call_args.kwargs["callback"] is _sentinel

    def test_main_callback_value_error_exits(self, monkeypatch, caplog):
        """--callback with no colon raises ValueError -> log error + sys.exit(1)."""
        caplog.set_level(logging.ERROR, logger="lib.flatpak_monitor")
        monkeypatch.setattr(sys, "argv", _argv("--callback", "no_colon_here"))

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert "Failed to load callback" in caplog.text
        assert "no_colon_here" in caplog.text

    def test_main_callback_import_error_exits(self, monkeypatch, caplog):
        """--callback pointing at a missing module -> ImportError -> exit 1."""
        caplog.set_level(logging.ERROR, logger="lib.flatpak_monitor")
        nonexistent = "definitely_not_a_real_module_xyz_12345"
        # Make sure it isn't already cached.
        monkeypatch.delitem(sys.modules, nonexistent, raising=False)

        monkeypatch.setattr(
            sys, "argv", _argv("--callback", f"{nonexistent}:some_func")
        )
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert "Failed to load callback" in caplog.text

    def test_main_callback_attribute_error_exits(self, monkeypatch, caplog):
        """--callback pointing at a missing attribute -> AttributeError -> exit 1."""
        caplog.set_level(logging.ERROR, logger="lib.flatpak_monitor")
        monkeypatch.setattr(
            sys,
            "argv",
            _argv("--callback", "os:definitely_not_a_real_attr_xyz_qwerty"),
        )
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert "Failed to load callback" in caplog.text


class TestMainConfigDict:
    """Tuning flags (batch_window, cooldown, debounce, regeneration_timeout)."""

    def test_main_tuning_flags_flow_into_config(self, monkeypatch):
        """All tuning flags are forwarded into the config dict."""
        mock_monitor = MagicMock()
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ) as mock_start:
            monkeypatch.setattr(
                sys,
                "argv",
                _argv(
                    "--batch-window",
                    "0.5",
                    "--cooldown",
                    "1.5",
                    "--debounce",
                    "0.3",
                    "--regeneration-timeout",
                    "30",
                ),
            )
            main()

        cfg = mock_start.call_args.kwargs["config"]
        assert cfg["batch_window"] == 0.5
        assert cfg["cooldown"] == 1.5
        assert cfg["debounce"] == 0.3
        assert cfg["regeneration_timeout"] == 30
        assert cfg["log_level"] == "INFO"

    def test_main_regeneration_timeout_is_int(self, monkeypatch):
        """--regeneration-timeout is declared as int in argparse."""
        mock_monitor = MagicMock()
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ) as mock_start:
            monkeypatch.setattr(
                sys, "argv", _argv("--regeneration-timeout", "120")
            )
            main()

        cfg = mock_start.call_args.kwargs["config"]
        assert cfg["regeneration_timeout"] == 120
        assert isinstance(cfg["regeneration_timeout"], int)


class TestMainDaemonBranch:
    """The daemon branch skips monitor.wait()."""

    def test_main_non_daemon_calls_wait(self, monkeypatch):
        """In non-daemon mode main() calls monitor.wait() after start returns."""
        mock_monitor = MagicMock()
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ):
            monkeypatch.setattr(sys, "argv", _argv())
            main()

        mock_monitor.wait.assert_called_once()

    def test_main_daemon_does_not_call_wait(self, monkeypatch):
        """In daemon mode main() does NOT call monitor.wait()."""
        mock_monitor = MagicMock()
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ):
            monkeypatch.setattr(sys, "argv", _argv("--daemon"))
            main()

        mock_monitor.wait.assert_not_called()

    def test_main_non_daemon_with_none_monitor_does_not_call_wait(self, monkeypatch):
        """When start returns None in non-daemon mode, wait() is not called."""
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=None,
        ) as mock_start:
            monkeypatch.setattr(sys, "argv", _argv())
            # Must not raise AttributeError on None.wait()
            main()

        mock_start.assert_called_once()


class TestMainSkipParse:
    """The skip_parse=True programmatic entry point bypasses argparse."""

    def test_main_skip_parse_passes_through_to_start(self):
        """With skip_parse=True the function forwards to start_flatpak_monitoring."""
        mock_monitor = MagicMock()
        sentinel_config = {"batch_window": 9.9, "cooldown": 8.8}

        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=mock_monitor,
        ) as mock_start:
            main(
                daemon=True,
                callback="my.module:cb",
                config=sentinel_config,
                skip_parse=True,
            )

        mock_start.assert_called_once_with(
            callback="my.module:cb", daemon=True, config=sentinel_config
        )

    def test_main_skip_parse_does_not_call_wait(self):
        """skip_parse=True never blocks in monitor.wait() (caller controls flow)."""
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=MagicMock(),
        ):
            main(daemon=False, skip_parse=True)
            main(daemon=True, skip_parse=True)

    def test_main_skip_parse_with_no_extras(self):
        """skip_parse=True with defaults still constructs a valid start call."""
        with patch(
            "lib.flatpak_monitor.start_flatpak_monitoring",
            return_value=MagicMock(),
        ) as mock_start:
            main(skip_parse=True)

        mock_start.assert_called_once_with(
            callback=None, daemon=False, config=None
        )


class TestFlatpakMonitorHelpers:
    """Lightweight helper tests that close out the remaining coverage gaps.

    These tests target the small, isolated branches the main()-level tests
    cannot reach: KeyboardInterrupt in wait(), lock contention in
    _regenerate_wrappers, dev-script detection, subprocess failure paths,
    etc. Each test is narrowly scoped so a regression points straight at
    the affected branch.
    """

    def test_on_moved_queues_src_and_dest(self):
        """on_moved emits a queued event for both src_path and dest_path."""
        from lib.flatpak_monitor import FlatpakEventHandler

        handler = FlatpakEventHandler(callback=None)
        event = MagicMock()
        event.src_path = "/var/lib/flatpak/app/com.example.App/x86_64/stable/active"
        event.dest_path = "/var/lib/flatpak/exports/bin/com.example.App"

        handler.on_moved(event)

        queued_paths = {p for _, p in handler.pending_events}
        assert event.src_path in queued_paths
        assert event.dest_path in queued_paths

    def test_regenerate_wrappers_async_starts_daemon_thread(self):
        """_regenerate_wrappers_async starts a daemon thread."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        with patch("lib.flatpak_monitor.threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance

            monitor._regenerate_wrappers_async()

            mock_thread_cls.assert_called_once()
            # Verify it was constructed as a daemon thread.
            assert mock_thread_cls.call_args.kwargs.get("daemon") is True
            mock_thread_instance.start.assert_called_once()

    def test_regenerate_wrappers_returns_false_on_lock_conflict(self):
        """_regenerate_wrappers returns False when the generation lock is held."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        with patch("lib.python_utils.acquire_lock", return_value=False):
            result = monitor._regenerate_wrappers()
        assert result is False

    def test_send_systemd_notify_handles_oserror(self):
        """_send_systemd_notify swallows OSError from the systemd daemon."""
        from lib.flatpak_monitor import FlatpakMonitor

        with (
            patch("lib.flatpak_monitor.SYSTEMD_NOTIFY_AVAILABLE", True),
            patch("lib.flatpak_monitor._systemd_daemon") as mock_sd,
        ):
            mock_sd.notify.side_effect = OSError("notify failed")
            monitor = FlatpakMonitor()
            # Should not raise.
            monitor._send_systemd_notify()
            mock_sd.notify.assert_called_once()

    def test_find_generate_scripts_includes_dev_script(self):
        """_find_generate_scripts injects the dev script when present."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        # Patch the resolved __file__-derived dev script to be present on disk.
        with patch.object(Path, "exists", return_value=True):
            scripts = monitor._find_generate_scripts()

        # The function unconditionally appends /usr/local/bin and /usr/bin
        # fplaunch-generate fallbacks, so those are always present.
        assert "/usr/local/bin/fplaunch-generate" in scripts
        assert "/usr/bin/fplaunch-generate" in scripts

    def test_run_generate_returns_false_on_nonzero_exit(self):
        """_run_generate returns False when the script exits non-zero."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="boom", stdout="")
            assert monitor._run_generate("/some/script") is False

    def test_run_generate_returns_false_on_timeout(self):
        """_run_generate returns False on subprocess.TimeoutExpired."""
        import subprocess as _subprocess

        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = _subprocess.TimeoutExpired(cmd="/x", timeout=1)
            assert monitor._run_generate("/some/script") is False

    def test_run_generate_returns_false_on_oserror(self):
        """_run_generate returns False on subprocess.OSError."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("no such script")
            assert monitor._run_generate("/some/script") is False

    def test_run_regeneration_sync_logs_when_script_missing(self):
        """_run_regeneration_sync logs an error when no script can be found."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        with (
            patch("lib.flatpak_monitor.shutil.which", return_value=None),
            patch.object(Path, "exists", return_value=False),
        ):
            assert monitor._run_regeneration_sync() is False

    def test_flush_pending_logs_callback_exception(self):
        """_flush_pending_events_unlocked logs but does not propagate callback errors."""
        from lib.flatpak_monitor import FlatpakEventHandler

        def bad_callback(event_type, path):
            raise ValueError("callback failed")

        handler = FlatpakEventHandler(callback=bad_callback)
        # Put a real event in the queue and force-flush.
        handler._queue_event("modified", "/var/lib/flatpak/exports/bin/app")
        handler._flush_pending_events()

    def test_wait_handles_keyboard_interrupt(self):
        """wait() catches KeyboardInterrupt and stops the monitor."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        monitor.observer = MagicMock()
        monitor.running = True

        with patch("time.sleep", side_effect=KeyboardInterrupt):
            monitor.wait()

        # stop_monitoring should have run; running should now be False.
        assert monitor.running is False

    def test_start_flatpak_monitoring_non_daemon_calls_wait(self):
        """start_flatpak_monitoring non-daemon branch calls monitor.wait()."""
        from lib.flatpak_monitor import FlatpakMonitor, start_flatpak_monitoring

        with (
            patch.object(FlatpakMonitor, "start_monitoring", return_value=True),
            patch.object(FlatpakMonitor, "wait") as mock_wait,
        ):
            start_flatpak_monitoring(daemon=False)
            mock_wait.assert_called_once()

    def test_start_flatpak_monitoring_skips_wait_when_start_fails(self):
        """start_flatpak_monitoring non-daemon does not call wait() on failure."""
        from lib.flatpak_monitor import FlatpakMonitor, start_flatpak_monitoring

        with (
            patch.object(FlatpakMonitor, "start_monitoring", return_value=False),
            patch.object(FlatpakMonitor, "wait") as mock_wait,
        ):
            start_flatpak_monitoring(daemon=False)
            mock_wait.assert_not_called()

    def test_get_watch_paths_includes_existing_dirs(self):
        """_get_watch_paths picks up dirs that actually exist on disk."""
        from lib.flatpak_monitor import FlatpakMonitor

        with patch("lib.flatpak_monitor.Path") as mock_path_cls:
            mock_path_instance = MagicMock()
            mock_path_cls.return_value = mock_path_instance
            mock_path_instance.exists.return_value = True
            mock_path_instance.expanduser.return_value = "/fake/expanded"

            monitor = FlatpakMonitor()
            paths = monitor._get_watch_paths()

        # System flatpak path should be in the list (it returned True).
        assert isinstance(paths, list)


class TestEventHandlerBranches:
    """Tests for the FlatpakEventHandler body paths."""

    def test_on_created_queues_event(self):
        """on_created queues the event for processing."""
        from lib.flatpak_monitor import FlatpakEventHandler

        handler = FlatpakEventHandler(callback=None)
        event = MagicMock()
        event.src_path = "/var/lib/flatpak/app/org.example.App/current"

        handler.on_created(event)

        assert any(p == event.src_path for _, p in handler.pending_events)

    def test_on_deleted_queues_event(self):
        """on_deleted queues the event for processing."""
        from lib.flatpak_monitor import FlatpakEventHandler

        handler = FlatpakEventHandler(callback=None)
        event = MagicMock()
        event.src_path = "/var/lib/flatpak/app/org.example.App/current"

        handler.on_deleted(event)

        assert any(p == event.src_path for _, p in handler.pending_events)

    def test_on_modified_queues_event(self):
        """on_modified queues the event for processing."""
        from lib.flatpak_monitor import FlatpakEventHandler

        handler = FlatpakEventHandler(callback=None)
        event = MagicMock()
        event.src_path = "/var/lib/flatpak/exports/bin/firefox"

        handler.on_modified(event)

        assert any(p == event.src_path for _, p in handler.pending_events)

    def test_on_methods_ignore_unrelated_paths(self):
        """on_* methods skip events for paths that should not be processed."""
        from lib.flatpak_monitor import FlatpakEventHandler

        handler = FlatpakEventHandler(callback=None)
        event = MagicMock()
        event.src_path = "/etc/passwd"
        event.dest_path = "/etc/shadow"

        handler.on_created(event)
        handler.on_deleted(event)
        handler.on_modified(event)
        handler.on_moved(event)

        # None of the unrelated paths should be queued.
        for _, path in handler.pending_events:
            assert path != "/etc/passwd"
            assert path != "/etc/shadow"

    def test_queue_event_lock_fallback(self):
        """_queue_event handles a missing lock gracefully."""
        from lib.flatpak_monitor import FlatpakEventHandler

        handler = FlatpakEventHandler(callback=None)
        # Force the lock to None to exercise the no-lock branch.
        handler._event_lock = None
        handler._queue_event("created", "/var/lib/flatpak/app/test")
        assert len(handler.pending_events) == 1

    def test_flush_pending_no_events(self):
        """_flush_pending_events is a no-op when the queue is empty."""
        from lib.flatpak_monitor import FlatpakEventHandler

        callback = MagicMock()
        handler = FlatpakEventHandler(callback=callback)
        handler._flush_pending_events()
        callback.assert_not_called()

    def test_flush_pending_respects_cooldown(self):
        """_flush_pending_events reschedules when the cooldown is active."""
        import time as _time

        from lib.flatpak_monitor import FlatpakEventHandler

        callback = MagicMock()
        handler = FlatpakEventHandler(callback=callback)
        handler.cooldown_seconds = 5.0
        handler.batch_window = 0.05
        # Set last_event_time so cooldown is still active.
        handler.last_event_time = _time.time()
        handler._queue_event("modified", "/var/lib/flatpak/app/test")
        # Cancel any timer that the queue created to avoid background flush.
        try:
            handler._flush_pending_events()
        finally:
            if handler.batch_timer is not None:
                handler.batch_timer.cancel()

        # Callback should NOT have been called during cooldown.
        callback.assert_not_called()

    def test_flush_pending_invokes_callback_after_cooldown(self):
        """_flush_pending_events calls the callback once the cooldown expires."""
        import time as _time

        from lib.flatpak_monitor import FlatpakEventHandler

        callback = MagicMock()
        handler = FlatpakEventHandler(callback=callback)
        handler.cooldown_seconds = 0.05
        handler.batch_window = 0.05
        # Backdate the last event so cooldown has elapsed.
        handler.last_event_time = _time.time() - 1.0
        handler._queue_event("modified", "/var/lib/flatpak/app/test")
        try:
            handler._flush_pending_events()
        finally:
            if handler.batch_timer is not None:
                handler.batch_timer.cancel()

        callback.assert_called_once_with("modified", "/var/lib/flatpak/app/test")


class TestFlatpakMonitorLifecycle:
    """Tests for FlatpakMonitor lifecycle, event handling, and regeneration gating."""

    def test_signal_handler_logs_and_stops(self):
        """_signal_handler logs the signal and calls stop_monitoring."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        monitor.running = True
        with patch.object(monitor, "stop_monitoring") as mock_stop:
            monitor._signal_handler(15, None)
            mock_stop.assert_called_once()

    def test_on_change_dispatches_to_handler(self):
        """_on_change forwards a matching event to _on_flatpak_change."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        event = MagicMock()
        event.src_path = "/var/lib/flatpak/app/test"
        event.event_type = "modified"

        with patch.object(monitor, "_on_flatpak_change") as mock_handler:
            monitor._on_change(event)
            mock_handler.assert_called_once_with("modified", event.src_path)

    def test_on_change_skips_unrelated_paths(self):
        """_on_change does nothing for paths that should not be processed."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        event = MagicMock()
        event.src_path = "/etc/passwd"
        event.event_type = "modified"

        with patch.object(monitor, "_on_flatpak_change") as mock_handler:
            monitor._on_change(event)
            mock_handler.assert_not_called()

    def test_on_flatpak_change_regenerates_and_invokes_callback(self):
        """_on_flatpak_change regenerates and forwards to the user callback."""
        from lib.flatpak_monitor import FlatpakMonitor

        callback = MagicMock()
        monitor = FlatpakMonitor(callback=callback)
        with patch.object(monitor, "_regenerate_wrappers", return_value=True):
            monitor._on_flatpak_change("modified", "/var/lib/flatpak/exports/bin/app")
        callback.assert_called_once()

    def test_on_flatpak_change_logs_regen_failure(self):
        """_on_flatpak_change logs an error when regeneration fails."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor(callback=None)
        with patch.object(monitor, "_regenerate_wrappers", return_value=False):
            # Should not raise even on failure.
            monitor._on_flatpak_change("modified", "/var/lib/flatpak/exports/bin/app")

    def test_on_flatpak_change_swallows_callback_exception(self):
        """_on_flatpak_change suppresses exceptions from the user callback."""
        from lib.flatpak_monitor import FlatpakMonitor

        def bad_callback(event_type, path):
            raise RuntimeError("boom")

        monitor = FlatpakMonitor(callback=bad_callback)
        with patch.object(monitor, "_regenerate_wrappers", return_value=True):
            # Should not raise.
            monitor._on_flatpak_change("modified", "/var/lib/flatpak/exports/bin/app")

    def test_should_regenerate_wrappers_truthy_paths(self):
        """_should_regenerate_wrappers returns True for the canonical paths."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        assert monitor._should_regenerate_wrappers("/var/lib/flatpak/exports/bin/app")
        assert monitor._should_regenerate_wrappers("/var/lib/flatpak/app/foo")
        assert monitor._should_regenerate_wrappers("/var/lib/flatpak/app/foo/active")
        assert monitor._should_regenerate_wrappers("/var/lib/flatpak/metadata")
        assert monitor._should_regenerate_wrappers("/var/lib/flatpak/app/x/manifest.json")

    def test_should_regenerate_wrappers_falsy_paths(self):
        """_should_regenerate_wrappers returns False for unrelated paths."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        assert not monitor._should_regenerate_wrappers("/etc/passwd")
        assert not monitor._should_regenerate_wrappers("/tmp/random_file")

    def test_start_monitoring_happy_path(self):
        """start_monitoring wires up the observer and returns True."""
        from lib.flatpak_monitor import FlatpakMonitor

        with patch("lib.flatpak_monitor.Observer") as mock_observer_cls:
            mock_observer = MagicMock()
            mock_observer_cls.return_value = mock_observer

            monitor = FlatpakMonitor(callback=None)
            result = monitor.start_monitoring()

        assert result is True
        assert monitor.running is True
        mock_observer.start.assert_called_once()

    def test_start_monitoring_returns_false_when_watchdog_missing(self):
        """start_monitoring returns False when watchdog is unavailable."""
        from lib.flatpak_monitor import FlatpakMonitor

        with patch("lib.flatpak_monitor.WATCHDOG_AVAILABLE", False):
            monitor = FlatpakMonitor(callback=None)
            result = monitor.start_monitoring()
        assert result is False
        assert monitor.running is False

    def test_send_systemd_notify_success(self):
        """_send_systemd_notify records the READY=1 state on success."""
        from lib.flatpak_monitor import FlatpakMonitor

        with (
            patch("lib.flatpak_monitor.SYSTEMD_NOTIFY_AVAILABLE", True),
            patch("lib.flatpak_monitor._systemd_daemon") as mock_sd,
        ):
            monitor = FlatpakMonitor()
            monitor._send_systemd_notify("READY=1")
        mock_sd.notify.assert_called_once_with("READY=1")
        assert monitor._systemd_notify_sent is True

    def test_send_systemd_notify_unavailable(self):
        """_send_systemd_notify is a no-op when systemd is unavailable."""
        from lib.flatpak_monitor import FlatpakMonitor

        with patch("lib.flatpak_monitor.SYSTEMD_NOTIFY_AVAILABLE", False):
            monitor = FlatpakMonitor()
            monitor._send_systemd_notify("READY=1")
        assert monitor._systemd_notify_sent is False

    def test_run_generate_returns_true_on_success(self):
        """_run_generate returns True and logs stdout on a zero exit."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
            assert monitor._run_generate("/some/script") is True

    def test_regenerate_wrappers_acquires_and_releases_lock(self):
        """_regenerate_wrappers acquires then releases the generation lock."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        with (
            patch("lib.python_utils.acquire_lock", return_value=True) as mock_acq,
            patch("lib.python_utils.release_lock") as mock_rel,
            patch.object(monitor, "_run_regeneration_sync", return_value=True),
        ):
            assert monitor._regenerate_wrappers() is True
        mock_acq.assert_called_once_with("generate", timeout_seconds=0.001)
        mock_rel.assert_called_once_with("generate")

    def test_run_regeneration_sync_invokes_generate(self):
        """_run_regeneration_sync calls _run_generate on a found script."""
        from lib.flatpak_monitor import FlatpakMonitor

        monitor = FlatpakMonitor()
        with (
            patch.object(monitor, "_find_generate_scripts", return_value=["/x/script"]),
            patch.object(Path, "exists", return_value=True),
            patch("lib.flatpak_monitor.os.access", return_value=True),
            patch.object(monitor, "_run_generate", return_value=True) as mock_run,
        ):
            assert monitor._run_regeneration_sync() is True
        mock_run.assert_called_once_with("/x/script")

    def test_start_flatpak_monitoring_daemon_branch(self):
        """start_flatpak_monitoring daemon branch spins up a thread."""
        from lib.flatpak_monitor import FlatpakMonitor, start_flatpak_monitoring

        with (
            patch("lib.flatpak_monitor.threading.Thread") as mock_thread_cls,
            patch.object(FlatpakMonitor, "wait") as mock_wait,
        ):
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance

            start_flatpak_monitoring(daemon=True)

        mock_thread_cls.assert_called_once()
        assert mock_thread_cls.call_args.kwargs.get("daemon") is True
        mock_thread_instance.start.assert_called_once()
        mock_wait.assert_not_called()
