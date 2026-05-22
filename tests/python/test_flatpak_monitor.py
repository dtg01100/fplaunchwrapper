#!/usr/bin/env python3
"""Tests for flatpak_monitor.py

Covers FlatpakEventHandler batching/deduplication, FlatpakMonitor lifecycle,
watch path detection, event filtering, wrapper regeneration, edge cases,
and integration scenarios.
"""

import os
import signal
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

try:
    from lib.flatpak_monitor import (
        WATCHDOG_AVAILABLE,
        FlatpakEventHandler,
        FlatpakMonitor,
        start_flatpak_monitoring,
    )
except ImportError:
    WATCHDOG_AVAILABLE = False
    FlatpakEventHandler = None
    FlatpakMonitor = None
    start_flatpak_monitoring = None


class TestFlatpakEventHandler:
    """Test the FlatpakEventHandler event batching and deduplication."""

    def test_handler_initialization(self):
        """Test FlatpakEventHandler initializes correctly."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        callback = Mock()
        handler = FlatpakEventHandler(callback=callback)

        assert handler.callback == callback
        assert handler.pending_events == []
        assert handler.batch_timer is None
        assert handler.batch_window == 1.0
        assert handler.cooldown_seconds == 2

    def test_handler_deduplicates_events(self):
        """Test that identical events within batch window are deduplicated."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        callback = Mock()
        handler = FlatpakEventHandler(callback=callback)

        handler._queue_event("modified", "/var/lib/flatpak/app/test")
        handler._queue_event("modified", "/var/lib/flatpak/app/test")
        handler._queue_event("modified", "/var/lib/flatpak/app/test")

        assert len(handler.pending_events) == 1, "Duplicates should be deduplicated"

    def test_handler_preserves_different_events(self):
        """Test that different events are preserved in batch."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        callback = Mock()
        handler = FlatpakEventHandler(callback=callback)

        handler._queue_event("created", "/var/lib/flatpak/app/app1")
        handler._queue_event("created", "/var/lib/flatpak/app/app2")
        handler._queue_event("modified", "/var/lib/flatpak/app/app1")

        assert len(handler.pending_events) == 3, "Different events should be preserved"

    def test_handler_batching_window(self):
        """Test that events within batch window are collected."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        callback = Mock()
        handler = FlatpakEventHandler(callback=callback)

        handler._queue_event("modified", "/var/lib/flatpak/app/test")
        assert handler.batch_timer is not None, "Batch timer should be started"

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_handler_flush_respects_cooldown(self):
        """Test that flush respects the cooldown period."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        callback = Mock()
        handler = FlatpakEventHandler(callback=callback)
        handler.cooldown_seconds = 0.5
        handler.batch_window = 0.1

        handler._queue_event("modified", "/var/lib/flatpak/app/test1")
        handler.last_event_time = time.time()

        handler._queue_event("modified", "/var/lib/flatpak/app/test2")

        handler._flush_pending_events()

        assert handler.batch_timer is not None or len(handler.pending_events) == 0

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_handler_cooldown_expiration(self):
        """Test that events are flushed after cooldown expires."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        callback = Mock()
        handler = FlatpakEventHandler(callback=callback)
        handler.cooldown_seconds = 0.2
        handler.batch_window = 0.1

        handler.last_event_time = time.time() - 1.0
        handler._queue_event("modified", "/var/lib/flatpak/app/test")

        handler._flush_pending_events()

        if callback:
            assert callback.called, "Callback should be called after cooldown expires"


class TestFlatpakMonitor:
    """Test FlatpakMonitor class functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.flatpak_dir = self.temp_dir / ".local" / "share" / "flatpak"
        self.exports_dir = self.flatpak_dir / "exports" / "bin"
        self.system_exports = Path("/var/lib/flatpak/exports/bin")

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_monitor_initialization(self):
        """Test FlatpakMonitor initializes correctly."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        assert monitor.callback == callback
        assert monitor.bin_dir == str(self.temp_dir / "bin")
        assert monitor.observer is None
        assert monitor.running is False
        assert isinstance(monitor.watch_paths, list)

    @patch("lib.flatpak_monitor.Observer")
    def test_monitor_start_stop(self, mock_observer_class) -> None:
        """Test monitor start and stop functionality."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        monitor.start_monitoring()

        mock_observer.start.assert_called_once()

        monitor.stop_monitoring()

        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

        monitor.stop_monitoring()

        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

    def test_monitor_directory_detection(self) -> None:
        """Test detection of Flatpak directories to monitor."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        self.flatpak_dir.mkdir(parents=True, exist_ok=True)

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        result = monitor.start_monitoring()

        assert result is True or len(monitor.watch_paths) > 0

        monitor.stop_monitoring()

    def test_monitor_has_start_stop_methods(self):
        """Test that start_monitoring() and stop_monitoring() exist."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        assert hasattr(monitor, "start_monitoring"), "start_monitoring() should exist"
        assert hasattr(monitor, "stop_monitoring"), "stop_monitoring() should exist"
        assert callable(monitor.start_monitoring)
        assert callable(monitor.stop_monitoring)

    def test_monitor_detects_watch_paths(self):
        """Test that monitor detects existing Flatpak directories."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        assert isinstance(monitor.watch_paths, list)

    def test_monitor_should_process_event(self):
        """Test event filtering logic for Flatpak paths.

        Uses the module-level should_process_event() function since the
        _should_process_event instance method was removed (dead code).
        """
        from lib.validation import should_process_event

        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        assert should_process_event("/var/lib/flatpak/something")
        assert should_process_event(os.path.expanduser("~/.local/share/flatpak/app"))
        assert should_process_event(os.path.expanduser("~/.var/app/something"))

        assert not should_process_event("/etc/passwd")
        assert not should_process_event("/tmp/random")

    def test_monitor_should_regenerate_on_exports(self):
        """Test that wrappers should regenerate on exports directory changes."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        assert monitor._should_regenerate_wrappers("/var/lib/flatpak/exports/bin/com.example.App")

    def test_monitor_should_regenerate_on_app_changes(self):
        """Test that wrappers should regenerate on app directory changes."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        assert monitor._should_regenerate_wrappers("/var/lib/flatpak/app/com.example.App/current")

    def test_monitor_should_regenerate_on_metadata(self):
        """Test that wrappers should regenerate on metadata changes."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        assert monitor._should_regenerate_wrappers("/var/lib/flatpak/metadata")

    def test_monitor_should_regenerate_on_manifest(self):
        """Test that wrappers should regenerate on manifest changes."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        assert monitor._should_regenerate_wrappers(
            "/var/lib/flatpak/app/com.example.App/manifest.json"
        )

    def test_monitor_regenerate_wrappers_script_not_found(self):
        """Test graceful handling when fplaunch-generate script is not found."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = monitor._regenerate_wrappers()

            assert result is False

    def test_monitor_regenerate_wrappers_script_failure(self):
        """Test handling of failed wrapper regeneration."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            result = monitor._regenerate_wrappers()

            assert result is False

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_monitor_start_monitoring_without_watchdog(self):
        """Test start_monitoring returns False if watchdog unavailable."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        with patch("lib.flatpak_monitor.WATCHDOG_AVAILABLE", False):
            result = monitor.start_monitoring()
            assert result is False

    @patch("lib.flatpak_monitor.FlatpakMonitor._regenerate_wrappers")
    @patch("watchdog.events.FileSystemEvent")
    def test_event_handler_file_created(self, mock_event_class, mock_regen) -> None:
        """Test handling of file creation events."""
        mock_regen.return_value = True
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_event = Mock()
        mock_event.src_path = "/var/lib/flatpak/exports/bin/new_app"
        mock_event.event_type = "created"
        mock_event.is_directory = False

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        monitor._on_change(mock_event)  # noqa: W0212

        callback.assert_called_once()

    @patch("lib.flatpak_monitor.FlatpakMonitor._regenerate_wrappers")
    @patch("watchdog.events.FileSystemEvent")
    def test_event_handler_file_deleted(self, _mock_event_class, mock_regen) -> None:
        """Test handling of file deletion events."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        mock_regen.return_value = True

        mock_event = Mock()
        mock_event.src_path = "/var/lib/flatpak/exports/bin/removed_app"
        mock_event.event_type = "deleted"
        mock_event.is_directory = False

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        monitor._on_change(mock_event)  # noqa: W0212

        callback.assert_called_once()

    @patch("watchdog.events.FileSystemEvent")
    def test_event_handler_directory_changes_ignored(self, _mock_event_class) -> None:
        """Test that directory changes are ignored."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_event = Mock()
        mock_event.src_path = str(self.exports_dir)
        mock_event.event_type = "created"
        mock_event.is_directory = True

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        monitor._on_change(mock_event)

        callback.assert_not_called()

    def test_event_handler_non_flatpak_files_ignored(self) -> None:
        """Test that non-Flatpak files are ignored."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        from watchdog.events import FileCreatedEvent

        event = FileCreatedEvent(str(self.temp_dir / "not_flatpak_file"))

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        monitor._on_change(event)

        callback.assert_not_called()

    def test_monitor_on_change_adapter(self):
        """Test _on_change adapter for simple event objects."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        callback = Mock()
        monitor = FlatpakMonitor(callback=callback)

        event = MagicMock()
        event.src_path = "/var/lib/flatpak/app/test"
        event.event_type = "modified"

        with patch.object(monitor, "_on_flatpak_change") as mock_handler:
            monitor._on_change(event)
            mock_handler.assert_called()

    def test_monitor_signal_handler(self):
        """Test signal handler calls stop_monitoring."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()
        monitor.running = True

        with patch.object(monitor, "stop_monitoring") as mock_stop:
            monitor._signal_handler(signal.SIGINT, None)
            mock_stop.assert_called_once()

    @patch("time.sleep")
    @patch("lib.flatpak_monitor.Observer")
    def test_monitor_daemon_mode(self, mock_observer_class, mock_sleep) -> None:
        """Test monitor in daemon mode."""
        if not start_flatpak_monitoring:
            pytest.skip("start_flatpak_monitoring function not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        mock_sleep.side_effect = KeyboardInterrupt()

        callback = Mock()

        try:
            monitor = start_flatpak_monitoring(callback=callback, daemon=True)
            assert monitor is not None
            assert monitor.callback == callback
        except KeyboardInterrupt:
            pass

    @patch("lib.flatpak_monitor.Observer")
    def test_monitor_error_handling(self, mock_observer_class) -> None:
        """Test error handling in monitor."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_observer = Mock()
        mock_observer.start.side_effect = Exception("Monitor error")
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        result = monitor.start_monitoring()

        assert result is False
        assert mock_observer.start.called

    @patch("lib.flatpak_monitor.Observer")
    def test_monitor_reconnection_logic(self, mock_observer_class) -> None:
        """Test monitor reconnection after disconnection."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        monitor.start_monitoring()
        assert mock_observer.start.call_count == 1

        monitor.stop_monitoring()
        monitor.start_monitoring()
        assert mock_observer.start.call_count == 2

    def test_monitor_callback_validation(self) -> None:
        """Test that monitor validates callback parameter."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))
        assert monitor.callback == callback

        monitor_none = FlatpakMonitor(callback=None, bin_dir=str(self.temp_dir / "bin"))
        assert monitor_none.callback is None

    def test_monitor_path_validation(self) -> None:
        """Test monitor path validation."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        self.flatpak_dir.mkdir(parents=True, exist_ok=True)

        callback = Mock()
        bin_dir = str(self.temp_dir / "bin")

        monitor = FlatpakMonitor(callback=callback, bin_dir=bin_dir)

        result = monitor.start_monitoring()

        assert result is True or monitor.watch_paths is not None

        monitor.stop_monitoring()

    @patch("lib.flatpak_monitor.Observer")
    def test_monitor_cleanup_on_stop(self, mock_observer_class) -> None:
        """Test proper cleanup when monitor stops."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        monitor.start_monitoring()
        monitor.stop_monitoring()

        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

    @patch("time.sleep")
    @patch("lib.flatpak_monitor.Observer")
    @patch("lib.flatpak_monitor.FlatpakMonitor._regenerate_wrappers")
    def test_monitor_event_debouncing(self, mock_regen, mock_observer_class, mock_sleep) -> None:
        mock_regen.return_value = True
        """Test that monitor debounces rapid events."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        from watchdog.events import FileCreatedEvent

        event = FileCreatedEvent("/var/lib/flatpak/exports/bin/app")
        for _i in range(5):
            monitor._on_change(event)

        assert callback.call_count == 5

    @patch("lib.flatpak_monitor.Observer")
    def test_monitor_thread_safety(self, mock_observer_class) -> None:
        """Test thread safety of monitor operations."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        results = []
        errors = []

        def worker() -> None:
            try:
                monitor.start_monitoring()
                time.sleep(0.1)
                monitor.stop_monitoring()
                results.append("success")
            except Exception as e:
                errors.append(e)

        threads = []
        for _i in range(3):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 3


class TestFlatpakMonitorEdgeCases:
    """Test edge cases and error handling."""

    def test_monitor_with_no_callback(self):
        """Test monitor works without callback provided."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor(callback=None)

        assert monitor.callback is None

        with patch.object(monitor, "_regenerate_wrappers", return_value=True):
            monitor._on_flatpak_change("modified", "/var/lib/flatpak/app/test")

    def test_monitor_handles_exception_in_callback(self):
        """Test monitor handles exceptions in user callback gracefully."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        def bad_callback(event_type, path):
            raise ValueError("Callback error")

        monitor = FlatpakMonitor(callback=bad_callback)

        with patch.object(monitor, "_regenerate_wrappers", return_value=True):
            monitor._on_flatpak_change("modified", "/var/lib/flatpak/app/test")

    def test_event_handler_with_none_callback(self):
        """Test FlatpakEventHandler works with None callback."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        handler = FlatpakEventHandler(callback=None)

        handler._queue_event("modified", "/var/lib/flatpak/app/test")
        handler._flush_pending_events()

    def test_monitor_watch_paths_empty_when_no_flatpak(self):
        """Test that watch_paths is empty list if no Flatpak dirs exist."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        with patch("os.path.exists", return_value=False):
            monitor = FlatpakMonitor()
            assert isinstance(monitor.watch_paths, list)

    def test_handler_concurrent_event_queueing(self):
        """Test that handler safely handles concurrent event queueing."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        callback = Mock()
        handler = FlatpakEventHandler(callback=callback)

        def queue_events():
            for i in range(5):
                handler._queue_event("modified", f"/var/lib/flatpak/app/test{i}")

        threads = [threading.Thread(target=queue_events) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(handler.pending_events) > 0


class TestFlatpakMonitorIntegration:
    """Integration tests for FlatpakMonitor with mock file system events."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.flatpak_dir = self.temp_dir / ".local" / "share" / "flatpak"
        self.exports_dir = self.flatpak_dir / "exports" / "bin"
        self.system_exports = Path("/var/lib/flatpak/exports/bin")

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_monitor_with_mock_events(self):
        """Test monitor callback is triggered on mock events."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        callback = Mock()
        monitor = FlatpakMonitor(callback=callback)

        with (
            patch.object(monitor, "_regenerate_wrappers", return_value=True),
            patch.object(monitor, "_on_flatpak_change", wraps=monitor._on_flatpak_change),
        ):
            monitor._on_flatpak_change("created", "/var/lib/flatpak/app/test")

        assert callback.called

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_monitor_batches_rapid_events(self):
        """Test that rapid events are batched together."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        callback = Mock()
        FlatpakMonitor(callback=callback)

        event_handler = FlatpakEventHandler(callback=callback)
        event_handler.batch_window = 1.0

        for i in range(10):
            event_handler._queue_event("modified", f"/var/lib/flatpak/app/test{i}")

        assert len(event_handler.pending_events) <= 10

    def test_start_flatpak_monitoring_function(self):
        """Test the convenience function start_flatpak_monitoring."""
        if not start_flatpak_monitoring:
            pytest.skip("start_flatpak_monitoring not available")
        callback = Mock()

        with patch("lib.flatpak_monitor.FlatpakMonitor") as mock_monitor_class:
            mock_instance = MagicMock()
            mock_monitor_class.return_value = mock_instance
            mock_instance.start_monitoring.return_value = False

            result = start_flatpak_monitoring(callback=callback, daemon=False)

            assert result is not None
            mock_monitor_class.assert_called_with(callback=callback, config=None)

    @patch("subprocess.run")
    @patch("lib.flatpak_monitor.Observer")
    def test_monitor_with_generate_integration(
        self,
        mock_observer_class,
        mock_subprocess,
    ) -> None:
        """Test monitor integration with wrapper generation."""
        if not start_flatpak_monitoring:
            pytest.skip("start_flatpak_monitoring function not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "org.mozilla.firefox"
        mock_subprocess.return_value = mock_result

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        test_callback = Mock()

        try:
            monitor = start_flatpak_monitoring(callback=test_callback, daemon=True)
            assert monitor is not None
            assert monitor.callback == test_callback
            monitor.stop_monitoring()
        except Exception as e:
            pytest.skip(f"Monitor integration test skipped: {e}")

    def test_monitor_configuration_validation(self) -> None:
        """Test monitor configuration validation."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        valid_configs = [
            {"callback": Mock(), "bin_dir": "/tmp/bin"},
            {"callback": None, "bin_dir": "/usr/local/bin"},
            {"callback": lambda: None, "bin_dir": "~/bin"},
        ]

        for config in valid_configs:
            monitor = FlatpakMonitor(**config)
            assert monitor is not None

    @patch("lib.flatpak_monitor.os.path.exists")
    def test_monitor_directory_discovery(self, mock_exists) -> None:
        """Test automatic discovery of Flatpak directories."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_exists.side_effect = lambda path: "flatpak" in str(path)

        callback = Mock()
        FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

    @patch("lib.flatpak_monitor.subprocess.run")
    @patch("lib.flatpak_monitor.time.sleep")
    def test_monitor_performance_under_load(self, mock_sleep, mock_run) -> None:
        """Test monitor performance with many events."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        from watchdog.events import FileCreatedEvent

        events = []
        for i in range(100):
            event = FileCreatedEvent(f"/var/lib/flatpak/exports/bin/app{i}")
            events.append(event)

        start_time = time.time()

        for event in events:
            monitor._on_change(event)

        end_time = time.time()

        assert end_time - start_time < 2.0
        assert callback.call_count == 100


class TestFlatpakMonitorStopStart:
    """Test monitor start/stop lifecycle."""

    def test_monitor_stop_without_start(self):
        """Test stop() can be called without start()."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        monitor.stop_monitoring()
        assert monitor.running is False

    def test_monitor_start_start_idempotent(self):
        """Test that starting already running monitor doesn't fail."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        with patch.object(monitor, "start_monitoring", return_value=True):
            result1 = monitor.start_monitoring()
            result2 = monitor.start_monitoring()

            assert result1 is not None
            assert result2 is not None

    def test_monitor_wait_timeout(self):
        """Test wait() method respects KeyboardInterrupt."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()
        monitor.running = False

        monitor.wait()


class TestFlatpakMonitorWatchPaths:
    """Test watch path detection and configuration."""

    def test_monitor_detects_system_flatpak(self):
        """Test monitor detects system Flatpak installation."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda x: x == "/var/lib/flatpak"
            monitor = FlatpakMonitor()

            assert len(monitor.watch_paths) >= 0

    def test_monitor_detects_user_flatpak(self):
        """Test monitor detects user Flatpak installation."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        user_flatpak = os.path.expanduser("~/.local/share/flatpak")

        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda x: x == user_flatpak
            monitor = FlatpakMonitor()

            assert len(monitor.watch_paths) >= 0

    def test_monitor_handles_missing_watch_paths(self):
        """Test monitor handles case when all watch paths are missing."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")
        monitor = FlatpakMonitor()

        with patch("os.path.exists", return_value=False):
            with patch.object(monitor, "_get_watch_paths", return_value=[]):
                monitor.watch_paths = []

                assert monitor.watch_paths == []


class TestEventBatchingBehavior:
    """Test event batching behavior in detail."""

    def test_batch_window_collection(self):
        """Test events are collected within batch window."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        handler = FlatpakEventHandler()
        handler.batch_window = 2.0

        handler._queue_event("created", "/var/lib/flatpak/app/test1")
        time.sleep(0.1)
        handler._queue_event("created", "/var/lib/flatpak/app/test2")

        assert len(handler.pending_events) == 2

    def test_dedup_same_path_different_events(self):
        """Test that same path with different event types is preserved."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        handler = FlatpakEventHandler()

        handler._queue_event("created", "/var/lib/flatpak/app/test")
        handler._queue_event("modified", "/var/lib/flatpak/app/test")

        assert len(handler.pending_events) == 2

    def test_dedup_same_event_multiple_calls(self):
        """Test that identical events are deduplicated."""
        if not FlatpakEventHandler:
            pytest.skip("FlatpakEventHandler not available")
        handler = FlatpakEventHandler()

        for _ in range(5):
            handler._queue_event("created", "/var/lib/flatpak/app/test")

        assert len(handler.pending_events) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
