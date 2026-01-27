#!/usr/bin/env python3
"""File system monitoring for fplaunchwrapper
Automatically detects new Flatpak installations and updates wrappers.
"""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

try:
    from watchdog.events import (
        FileSystemEventHandler as _WatchdogFileSystemEventHandler,
    )
    from watchdog.observers import Observer as _WatchdogObserver

    WATCHDOG_AVAILABLE = True
except Exception:
    _WatchdogFileSystemEventHandler = None
    _WatchdogObserver = None
    WATCHDOG_AVAILABLE = False

# For runtime we select a base handler that is the watchdog class when present,
# otherwise a neutral fallback (object). We intentionally do NOT define a
# module-level `FileSystemEventHandler` class here to avoid static type
# mismatches with watchdog's own type.
_BaseFSHandler: Any = (
    _WatchdogFileSystemEventHandler
    if _WatchdogFileSystemEventHandler is not None
    else object
)

# Make Observer available at module scope (None when watchdog not present)
Observer = _WatchdogObserver


# Systemd notify support (optional) - import at runtime via importlib to avoid
# static import resolution errors in environments where systemd Python
# bindings aren't installed.
import importlib  # noqa: E402

try:
    _systemd_daemon = importlib.import_module("systemd.daemon")
    SYSTEMD_NOTIFY_AVAILABLE = True
except Exception:
    _systemd_daemon = None
    SYSTEMD_NOTIFY_AVAILABLE = False


class FlatpakEventHandler(_BaseFSHandler):
    """Handler for Flatpak installation/removal events with event batching."""

    def __init__(self, callback=None, config: Optional[Dict[str, Any]] = None) -> None:
        self.callback = callback
        self.last_event_time = 0
        self.config = config or {}
        self.cooldown_seconds = self.config.get(
            "cooldown", 2
        )  # Prevent rapid-fire events
        self.pending_events = []
        self.batch_window = self.config.get(
            "batch_window", 1.0
        )  # Collect events for 1 second
        self.batch_timer = None
        self._event_lock = None
        self._init_lock()

    def _init_lock(self):
        """Initialize thread lock for event queueing."""
        try:
            import threading

            self._event_lock = threading.Lock()
        except ImportError:
            self._event_lock = None

    def on_created(self, event) -> None:
        """Called when a new file/directory is created."""
        if self._should_process_event(event.src_path):
            self._queue_event("created", event.src_path)

    def on_deleted(self, event) -> None:
        """Called when a file/directory is deleted."""
        if self._should_process_event(event.src_path):
            self._queue_event("deleted", event.src_path)

    def on_modified(self, event) -> None:
        """Called when a file/directory is modified."""
        if self._should_process_event(event.src_path):
            self._queue_event("modified", event.src_path)

    def on_moved(self, event) -> None:
        """Called when a file/directory is moved."""
        if self._should_process_event(event.src_path):
            self._queue_event("moved", event.src_path)
        if self._should_process_event(event.dest_path):
            self._queue_event("moved", event.dest_path)

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

    def _queue_event(self, event_type, path) -> None:
        """Queue event for batching instead of processing immediately."""
        if self._event_lock:
            with self._event_lock:
                self._queue_event_unlocked(event_type, path)
        else:
            self._queue_event_unlocked(event_type, path)

    def _queue_event_unlocked(self, event_type, path) -> None:
        """Queue event without lock (internal method)."""
        # Add to pending events if not already there
        event_key = (event_type, path)
        if event_key not in self.pending_events:
            self.pending_events.append(event_key)
            logger.debug("Queued event: %s - %s", event_type, path)

        # Reset batch timer
        if self.batch_timer:
            self.batch_timer.cancel()

        # Import threading here to avoid issues if not available
        import threading

        self.batch_timer = threading.Timer(
            self.batch_window, self._flush_pending_events
        )
        self.batch_timer.daemon = True
        self.batch_timer.start()

    def _flush_pending_events(self) -> None:
        """Process all pending events and trigger callback once."""
        if self._event_lock:
            with self._event_lock:
                self._flush_pending_events_unlocked()
        else:
            self._flush_pending_events_unlocked()

    def _flush_pending_events_unlocked(self) -> None:
        """Flush pending events without lock (internal method)."""
        if not self.pending_events:
            return

        # Check cooldown
        current_time = time.time()
        if current_time - self.last_event_time < self.cooldown_seconds:
            # Still in cooldown, reschedule
            import threading

            delay = self.cooldown_seconds - (current_time - self.last_event_time)
            self.batch_timer = threading.Timer(delay, self._flush_pending_events)
            self.batch_timer.daemon = True
            self.batch_timer.start()
            logger.debug("Cooldown active, rescheduling flush in %.1fs", delay)
            return

        # Update cooldown timestamp
        self.last_event_time = current_time

        # Trigger callback with all batched events
        if self.callback:
            with contextlib.suppress(Exception):
                logger.debug("Flushing %d batched events", len(self.pending_events))
                for event_type, path in self.pending_events:
                    self.callback(event_type, path)

        self.pending_events = []
        self.batch_timer = None


class FlatpakMonitor:
    """Monitor for Flatpak installation changes."""

    def __init__(
        self,
        callback=None,
        bin_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        # bin_dir is accepted for test compatibility but not used in monitoring logic
        self.callback = callback
        self.bin_dir = bin_dir
        self.observer = None
        self.running = False
        self.config = config or {}

        # Paths to monitor
        self.watch_paths = self._get_watch_paths()

        # Systemd notify state
        self._systemd_notify_sent = False

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

    def _send_systemd_notify(self, status: str = "READY=1"):
        """Send notification to systemd."""
        if SYSTEMD_NOTIFY_AVAILABLE and _systemd_daemon is not None:
            try:
                _systemd_daemon.notify(status)
                logger.debug("Systemd notify sent: %s", status)
                if status == "READY=1":
                    self._systemd_notify_sent = True
            except Exception as e:
                logger.warning("Failed to send systemd notify: %s", e)

    def start_monitoring(self) -> bool:
        """Start monitoring for Flatpak changes."""
        if not WATCHDOG_AVAILABLE or Observer is None:
            logger.error("Watchdog library not available")
            return False

        try:
            # Instantiate the observer only when the class is available
            self.observer = Observer() if Observer is not None else None

            # Set up event handler
            event_handler = FlatpakEventHandler(
                callback=self._on_flatpak_change, config=self.config
            )

            # Watch all relevant paths
            for path in self.watch_paths:
                if os.path.exists(path) and self.observer is not None:
                    # Schedule the handler for this path
                    self.observer.schedule(event_handler, path, recursive=True)
                    logger.info("Watching path: %s", path)

            if self.observer is not None:
                self.observer.start()
            self.running = True

            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            # Send systemd notify ready signal
            self._send_systemd_notify()

            logger.info("Flatpak monitor started successfully")
            return True

        except Exception as e:
            logger.error("Failed to start Flatpak monitor: %s", e)
            return False

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        if self.observer and self.running:
            logger.info("Stopping Flatpak monitor")
            self.observer.stop()
            self.observer.join()
            self.running = False
            logger.info("Flatpak monitor stopped")

    # Compatibility methods expected by tests
    def start(self) -> bool:
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
        logger.debug("Flatpak change detected: %s - %s", event_type, path)

        # Debounce rapid events
        time.sleep(self.config.get("debounce", 1))

        # Check if we need to regenerate wrappers
        if self._should_regenerate_wrappers(path):
            logger.info("Regenerating Flatpak wrappers due to change: %s", path)
            success = self._regenerate_wrappers()
            if success:
                logger.info("Flatpak wrappers regenerated successfully")
            else:
                logger.error("Failed to regenerate Flatpak wrappers")

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

    def _regenerate_wrappers(self) -> bool:
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
                    logger.debug("Running wrapper regeneration script: %s", script_path)
                    result = subprocess.run(
                        [script_path],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=self.config.get("regeneration_timeout", 60),
                    )

                    if result.returncode == 0:
                        logger.debug(
                            "Wrapper regeneration stdout: %s",
                            str(result.stdout).strip(),
                        )
                        return True
                    else:
                        logger.error(
                            "Wrapper regeneration failed with code %d: %s",
                            result.returncode,
                            result.stderr.strip(),
                        )
                        return False

            logger.error("fplaunch-generate script not found")
            return False

        except subprocess.TimeoutExpired:
            logger.error("Wrapper regeneration timed out")
            return False
        except Exception as e:
            logger.error("Failed to regenerate wrappers: %s", e)
            return False

    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        logger.info("Received signal %d, stopping monitor", signum)
        self.stop_monitoring()

    def wait(self) -> None:
        """Wait for monitoring to complete."""
        if self.observer:
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
            finally:
                self.stop_monitoring()


def start_flatpak_monitoring(
    callback=None, daemon=False, config: Optional[Dict[str, Any]] = None
):
    """Start Flatpak monitoring (convenience function)."""
    monitor = FlatpakMonitor(callback=callback, config=config)

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


def main(
    daemon: bool = False,
    callback: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    skip_parse: bool = False,
) -> None:
    """Command-line interface for flatpak monitoring.

    When called programmatically with `skip_parse=True`, this function will
    honor the provided ``daemon``, ``callback`` and ``config`` parameters and
    will NOT attempt to parse sys.argv using argparse. This enables safe,
    non-CLI invocations from other modules (for example from the Click-based
    wrapper) without argparse trying to parse unrelated arguments.
    """
    if skip_parse:
        # Programmatic invocation: use provided args directly and do not parse argv.
        start_flatpak_monitoring(callback=callback, daemon=daemon, config=config)
        return

    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Flatpak installation monitoring service"
    )
    parser.add_argument(
        "-d", "--daemon", action="store_true", help="Run in background as a daemon"
    )
    parser.add_argument(
        "-c",
        "--callback",
        type=str,
        default=None,
        help="Callback function to execute on events (format: module:function)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--batch-window",
        type=float,
        default=1.0,
        help="Event batch window in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=2.0,
        help="Cooldown period between events in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--debounce",
        type=float,
        default=1.0,
        help="Debounce delay before processing events (default: 1.0)",
    )
    parser.add_argument(
        "--regeneration-timeout",
        type=int,
        default=60,
        help="Wrapper regeneration timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logger.setLevel(getattr(logging, args.log_level.upper()))

    # Load callback if specified
    callback_func = None
    if args.callback:
        try:
            module_name, func_name = args.callback.split(":")
            module = __import__(module_name)
            callback_func = getattr(module, func_name)
        except Exception as e:
            logger.error("Failed to load callback %s: %s", args.callback, e)
            sys.exit(1)

    # Build configuration
    config = {
        "batch_window": args.batch_window,
        "cooldown": args.cooldown,
        "debounce": args.debounce,
        "regeneration_timeout": args.regeneration_timeout,
        "log_level": args.log_level.upper(),
    }

    logger.info("Starting Flatpak monitor with configuration: %s", config)
    start_flatpak_monitoring(callback=callback_func, daemon=args.daemon, config=config)

    if not args.daemon:
        pass


# CLI interface
if __name__ == "__main__":
    main()
