#!/usr/bin/env python3
"""File system monitoring for fplaunchwrapper
Automatically detects new Flatpak installations and updates wrappers.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

    # Create a dummy base class when watchdog is not available
    class FileSystemEventHandler:
        """Dummy base class when watchdog is not available."""

        pass


class FlatpakEventHandler(FileSystemEventHandler):
    """Handler for Flatpak installation/removal events."""

    def __init__(self, callback=None) -> None:
        self.callback = callback
        self.last_event_time = 0
        self.cooldown_seconds = 2  # Prevent rapid-fire events

    def on_created(self, event) -> None:
        """Called when a new file/directory is created."""
        if self._should_process_event(event.src_path):
            self._trigger_callback("created", event.src_path)

    def on_deleted(self, event) -> None:
        """Called when a file/directory is deleted."""
        if self._should_process_event(event.src_path):
            self._trigger_callback("deleted", event.src_path)

    def on_modified(self, event) -> None:
        """Called when a file/directory is modified."""
        if self._should_process_event(event.src_path):
            self._trigger_callback("modified", event.src_path)

    def on_moved(self, event) -> None:
        """Called when a file/directory is moved."""
        if self._should_process_event(event.src_path):
            self._trigger_callback("moved", event.src_path)

    def _should_process_event(self, path) -> bool:
        """Determine if we should process this event."""
        # Only process events related to Flatpak installations
        path_str = str(path)

        # Check for Flatpak-related paths
        flatpak_paths = [
            "/var/lib/flatpak",
            "/home",
            os.path.expanduser("~/.local/share/flatpak"),
            os.path.expanduser("~/.var/app"),
        ]

        for flatpak_path in flatpak_paths:
            if path_str.startswith(flatpak_path):
                # Check cooldown to prevent spam
                current_time = time.time()
                if current_time - self.last_event_time > self.cooldown_seconds:
                    self.last_event_time = current_time
                    return True

        return False

    def _trigger_callback(self, event_type, path) -> None:
        """Trigger the callback function."""
        if self.callback:
            with contextlib.suppress(Exception):
                self.callback(event_type, path)


class FlatpakMonitor:
    """Monitor for Flatpak installation changes."""

    def __init__(self, callback=None, bin_dir: str | None = None) -> None:
        # bin_dir is accepted for test compatibility but not used in monitoring logic
        self.callback = callback
        self.bin_dir = bin_dir
        self.observer = None
        self.running = False

        # Paths to monitor
        self.watch_paths = self._get_watch_paths()

    def _get_watch_paths(self):
        """Get paths that should be monitored for Flatpak changes."""
        paths = []

        # System Flatpak installations
        if os.path.exists("/var/lib/flatpak"):
            paths.append("/var/lib/flatpak")

        # User Flatpak installations
        user_flatpak = os.path.expanduser("~/.local/share/flatpak")
        if os.path.exists(user_flatpak):
            paths.append(user_flatpak)

        # User app data (where Flatpak apps store data)
        user_app_data = os.path.expanduser("~/.var/app")
        if os.path.exists(user_app_data):
            paths.append(user_app_data)

        return paths

    def start_monitoring(self) -> bool | None:
        """Start monitoring for Flatpak changes."""
        if not WATCHDOG_AVAILABLE:
            return False

        try:
            self.observer = Observer()

            # Set up event handler
            event_handler = FlatpakEventHandler(callback=self._on_flatpak_change)

            # Watch all relevant paths
            for path in self.watch_paths:
                if os.path.exists(path):
                    self.observer.schedule(event_handler, path, recursive=True)

            self.observer.start()
            self.running = True

            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            return True

        except Exception:
            return False

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        if self.observer and self.running:
            self.observer.stop()
            self.observer.join()
            self.running = False

    # Compatibility methods expected by tests
    def start(self) -> bool | None:
        """Alias for start_monitoring()."""
        return self.start_monitoring()

    def stop(self) -> None:
        """Alias for stop_monitoring()."""
        self.stop_monitoring()

    def _on_change(self, event) -> None:
        """Adapter to handle simple event objects with src_path and event_type."""
        path = getattr(event, "src_path", "")
        event_type = getattr(event, "event_type", "modified")

        # Check if we should process this event (similar to FlatpakEventHandler)
        if self._should_process_event(path):
            self._on_flatpak_change(event_type, path)

    def _should_process_event(self, path) -> bool:
        """Determine if we should process this event."""
        # Only process events related to Flatpak installations
        path_str = str(path)

        # Check for Flatpak-related paths
        flatpak_paths = [
            "/var/lib/flatpak",
            "/home",
            os.path.expanduser("~/.local/share/flatpak"),
            os.path.expanduser("~/.var/app"),
        ]

        for flatpak_path in flatpak_paths:
            if path_str.startswith(flatpak_path):
                return True

        return False

    def _on_flatpak_change(self, event_type, path) -> None:
        """Handle Flatpak-related file system changes."""
        # Debounce rapid events
        time.sleep(1)

        # Check if we need to regenerate wrappers
        if self._should_regenerate_wrappers(path):
            self._regenerate_wrappers()

        # Call user callback if provided
        if self.callback:
            with contextlib.suppress(Exception):
                self.callback(event_type, path)

    def _should_regenerate_wrappers(self, path) -> bool:
        """Determine if wrappers should be regenerated based on the path."""
        path_str = str(path).lower()

        # Regenerate on app installation/removal
        if "exports" in path_str or "app" in path_str:
            return True

        # Regenerate on metadata changes
        return bool("metadata" in path_str or "manifest" in path_str)

    def _regenerate_wrappers(self) -> bool | None:
        """Regenerate Flatpak wrappers."""
        try:
            # Find the fplaunch-generate script
            script_paths = [
                os.path.join(os.path.dirname(__file__), "..", "fplaunch-generate"),
                "/usr/local/bin/fplaunch-generate",
                "/usr/bin/fplaunch-generate",
            ]

            for script_path in script_paths:
                if os.path.exists(script_path) and os.access(script_path, os.X_OK):
                    result = subprocess.run(
                        [script_path],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    return result.returncode == 0

            return False

        except Exception:
            return False

    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        self.stop_monitoring()

    def wait(self) -> None:
        """Wait for monitoring to complete."""
        if self.observer:
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                self.stop_monitoring()


def start_flatpak_monitoring(callback=None, daemon=False):
    """Start Flatpak monitoring (convenience function)."""
    monitor = FlatpakMonitor(callback=callback)

    if daemon:
        # Run in background
        import threading

        thread = threading.Thread(target=monitor.start_monitoring, daemon=True)
        thread.start()
        return monitor
    # Run in foreground
    if monitor.start_monitoring():
        monitor.wait()
    return monitor


def main() -> None:
    """Command-line interface for flatpak monitoring."""
    import argparse

    parser = argparse.ArgumentParser(description="Flatpak file system monitor")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument(
        "--callback",
        type=str,
        help="Python module:function to call on events",
    )

    args = parser.parse_args()

    # Load callback if specified
    callback = None
    if args.callback:
        try:
            module_name, func_name = args.callback.split(":")
            module = __import__(module_name)
            callback = getattr(module, func_name)
        except Exception:
            sys.exit(1)

    start_flatpak_monitoring(callback=callback, daemon=args.daemon)

    if not args.daemon:
        pass


# CLI interface
if __name__ == "__main__":
    main()
