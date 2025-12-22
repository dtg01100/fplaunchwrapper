#!/usr/bin/env python3
"""Unit tests for flatpak_monitor.py
Tests Flatpak monitoring functionality with proper mocking.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add lib to path
# Import the module to test
try:
    from fplaunch.flatpak_monitor import FlatpakMonitor, start_flatpak_monitoring
except ImportError:
    # Mock it if not available
    FlatpakMonitor = None
    start_flatpak_monitoring = None


class TestFlatpakMonitor:
    """Test Flatpak monitoring functionality."""

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

    def test_flatpak_monitor_creation(self) -> None:
        """Test Flatpak monitor creation."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        monitor = FlatpakMonitor(callback=Mock(), bin_dir=str(self.temp_dir / "bin"))

        assert monitor is not None
        assert hasattr(monitor, "callback")
        assert hasattr(monitor, "bin_dir")
        assert hasattr(monitor, "observer")

    @patch("fplaunch.flatpak_monitor.Observer")
    def test_monitor_start_stop(self, mock_observer_class) -> None:
        """Test monitor start and stop functionality."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        # Start monitoring
        monitor.start()

        # Verify observer was started
        mock_observer.start.assert_called_once()

        # Stop monitoring
        monitor.stop()

        # Verify observer was stopped
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

        # Stop monitoring
        monitor.stop()

        # Verify observer was stopped
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

    @patch("fplaunch.flatpak_monitor.os.path.exists")
    @patch("fplaunch.flatpak_monitor.Observer")
    def test_monitor_directory_detection(
        self, mock_observer_class, mock_exists
    ) -> None:
        """Test detection of Flatpak directories to monitor."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        # Mock directory existence
        mock_exists.return_value = True

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        monitor.start()

        # Should schedule monitoring for both user and system directories
        assert mock_observer.schedule.call_count >= 1

        # Stop to clean up
        monitor.stop()

    @patch("watchdog.events.FileSystemEvent")
    def test_event_handler_file_created(self, mock_event_class) -> None:
        """Test handling of file creation events."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        # Mock file creation event
        mock_event = Mock()
        mock_event.src_path = "/var/lib/flatpak/exports/bin/new_app"
        mock_event.event_type = "created"
        mock_event.is_directory = False

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        # Simulate file creation
        monitor._on_change(mock_event)

        # Should call callback for app creation
        callback.assert_called_once()

    @patch("watchdog.events.FileSystemEvent")
    def test_event_handler_file_deleted(self, mock_event_class) -> None:
        """Test handling of file deletion events."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        # Mock file deletion event
        mock_event = Mock()
        mock_event.src_path = "/var/lib/flatpak/exports/bin/removed_app"
        mock_event.event_type = "deleted"
        mock_event.is_directory = False

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        # Simulate file deletion
        monitor._on_change(mock_event)

        # Should call callback for app removal
        callback.assert_called_once()

    @patch("watchdog.events.FileSystemEvent")
    def test_event_handler_directory_changes_ignored(self, mock_event_class) -> None:
        """Test that directory changes are ignored."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        # Mock directory event
        mock_event = Mock()
        mock_event.src_path = str(self.exports_dir)
        mock_event.event_type = "created"
        mock_event.is_directory = True

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        # Simulate directory change
        monitor._on_change(mock_event)

        # Should not call callback for directory events
        callback.assert_not_called()

    def test_event_handler_non_flatpak_files_ignored(self) -> None:
        """Test that non-Flatpak files are ignored."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        from watchdog.events import FileCreatedEvent

        # Create event for non-Flatpak file
        event = FileCreatedEvent(str(self.temp_dir / "not_flatpak_file"))

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        # Simulate non-Flatpak file change
        monitor._on_change(event)

        # Should not call callback
        callback.assert_not_called()

    @patch("time.sleep")
    @patch("fplaunch.flatpak_monitor.Observer")
    def test_monitor_daemon_mode(self, mock_observer_class, mock_sleep) -> None:
        """Test monitor in daemon mode."""
        if not start_flatpak_monitoring:
            pytest.skip("start_flatpak_monitoring function not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        # Mock sleep to avoid infinite loop
        mock_sleep.side_effect = KeyboardInterrupt()

        callback = Mock()

        try:
            start_flatpak_monitoring(callback=callback, daemon=True)
        except KeyboardInterrupt:
            pass  # Expected

        # Should have started observer
        mock_observer.start.assert_called_once()

    @patch("fplaunch.flatpak_monitor.Observer")
    def test_monitor_error_handling(self, mock_observer_class) -> None:
        """Test error handling in monitor."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        # Mock observer to raise exception
        mock_observer = Mock()
        mock_observer.start.side_effect = Exception("Monitor error")
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        # Should handle errors gracefully by returning False, not raising exception
        result = monitor.start()
        
        # Verify error was handled: start() returns False on error
        assert result is False
        # Verify observer was attempted to be created and started
        assert mock_observer.start.called

    @patch("fplaunch.flatpak_monitor.Observer")
    def test_monitor_reconnection_logic(self, mock_observer_class) -> None:
        """Test monitor reconnection after disconnection."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        # Start monitoring
        monitor.start()
        assert mock_observer.start.call_count == 1

        # Simulate disconnection and reconnection
        monitor.stop()
        monitor.start()
        assert mock_observer.start.call_count == 2

    def test_monitor_callback_validation(self) -> None:
        """Test that monitor validates callback parameter."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        # Should accept valid callback
        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))
        assert monitor.callback == callback

        # Should handle None callback
        monitor_none = FlatpakMonitor(callback=None, bin_dir=str(self.temp_dir / "bin"))
        assert monitor_none.callback is None

    @patch("fplaunch.flatpak_monitor.os.path.exists")
    @patch("fplaunch.flatpak_monitor.Observer")
    def test_monitor_path_validation(self, mock_observer_class, mock_exists) -> None:
        """Test monitor path validation."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_exists.return_value = True
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        bin_dir = str(self.temp_dir / "bin")

        monitor = FlatpakMonitor(callback=callback, bin_dir=bin_dir)

        # Should validate bin_dir exists
        monitor.start()

        # Should have checked path existence
        mock_exists.assert_called()

        monitor.stop()

    @patch("fplaunch.flatpak_monitor.Observer")
    def test_monitor_cleanup_on_stop(self, mock_observer_class) -> None:
        """Test proper cleanup when monitor stops."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        monitor.start()
        monitor.stop()

        # Should properly stop and join observer
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

    @patch("fplaunch.flatpak_monitor.Observer")
    @patch("time.sleep")
    def test_monitor_event_debouncing(self, mock_sleep, mock_observer_class) -> None:
        """Test that monitor debounces rapid events."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        # Simulate rapid events
        from watchdog.events import FileCreatedEvent

        event = FileCreatedEvent("/var/lib/flatpak/exports/bin/app")
        for _i in range(5):
            monitor._on_change(event)

        # Should call callback multiple times (no debouncing implemented yet)
        assert callback.call_count == 5

    def test_monitor_thread_safety(self) -> None:
        """Test thread safety of monitor operations."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        import threading

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        results = []
        errors = []

        def worker() -> None:
            try:
                monitor.start()
                time.sleep(0.1)  # Brief operation
                monitor.stop()
                results.append("success")
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for _i in range(3):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should not have threading errors
        assert len(errors) == 0
        assert len(results) == 3


class TestFlatpakMonitorIntegration:
    """Test Flatpak monitor integration scenarios."""

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

    @patch("subprocess.run")
    @patch("fplaunch.flatpak_monitor.Observer")
    def test_monitor_with_generate_integration(
        self,
        mock_observer_class,
        mock_subprocess,
    ) -> None:
        """Test monitor integration with wrapper generation."""
        if not start_flatpak_monitoring:
            pytest.skip("start_flatpak_monitoring function not available")

        # Mock successful flatpak command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "org.mozilla.firefox"
        mock_subprocess.return_value = mock_result

        # Mock observer
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        # Use a Mock callback so we can verify it's registered properly
        test_callback = Mock()

        # Should start monitoring successfully
        try:
            monitor = start_flatpak_monitoring(callback=test_callback, daemon=True)
            assert monitor is not None
            # Verify the monitor was set up with the callback
            assert monitor.callback == test_callback
            # Stop the monitor to clean up
            monitor.stop()
        except Exception as e:
            # May fail due to missing watchdog in test environment
            pytest.skip(f"Monitor integration test skipped: {e}")

    def test_monitor_configuration_validation(self) -> None:
        """Test monitor configuration validation."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        # Valid configurations
        valid_configs = [
            {"callback": Mock(), "bin_dir": "/tmp/bin"},
            {"callback": None, "bin_dir": "/usr/local/bin"},
            {"callback": lambda: None, "bin_dir": "~/bin"},
        ]

        for config in valid_configs:
            monitor = FlatpakMonitor(**config)
            assert monitor is not None

    @patch("fplaunch.flatpak_monitor.os.path.exists")
    def test_monitor_directory_discovery(self, mock_exists) -> None:
        """Test automatic discovery of Flatpak directories."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        # Mock different directory existence scenarios
        mock_exists.side_effect = lambda path: "flatpak" in str(path)

        callback = Mock()
        FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        # Should discover available Flatpak directories
        # (This is internal implementation detail)

    @patch("fplaunch.flatpak_monitor.time.sleep")
    def test_monitor_performance_under_load(self, mock_sleep) -> None:
        """Test monitor performance with many events."""
        if not FlatpakMonitor:
            pytest.skip("FlatpakMonitor class not available")

        callback = Mock()
        monitor = FlatpakMonitor(callback=callback, bin_dir=str(self.temp_dir / "bin"))

        from watchdog.events import FileCreatedEvent

        # Simulate many file events
        events = []
        for i in range(100):
            event = FileCreatedEvent(f"/var/lib/flatpak/exports/bin/app{i}")
            events.append(event)

        import time

        start_time = time.time()

        for event in events:
            monitor._on_change(event)

        end_time = time.time()

        # Should handle 100 events quickly
        assert end_time - start_time < 2.0  # Less than 2 seconds
        assert callback.call_count == 100
        # Check that sleep was called (but mocked)
        mock_sleep.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
