#!/usr/bin/env python3
"""File system monitoring for fplaunchwrapper
Automatically detects new Flatpak installations and updates wrappers.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .validation import should_process_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

__all__ = [
    "FlatpakEventHandler",
    "FlatpakMonitor",
    "start_flatpak_monitoring",
]

# Optional watchdog dependency - use Any to avoid static type conflicts
WatchdogEventHandler: Any
WatchdogObserver: Any
WATCHDOG_AVAILABLE: bool


try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
    WatchdogEventHandler = FileSystemEventHandler
    WatchdogObserver = Observer
except ImportError:
    WATCHDOG_AVAILABLE = False
    WatchdogEventHandler = object
    WatchdogObserver = object


def _get_observer_cls() -> Any:
    """Return the current Observer class (supports runtime patch for tests)."""
    return Observer


# Backward-compatible alias for tests that patch Observer directly
Observer = WatchdogObserver


# For runtime we select a base handler that is the watchdog class when present,
# otherwise a neutral fallback (object).
_BaseFSHandler: Any = (
    WatchdogEventHandler if WatchdogEventHandler is not None else object
)


# Systemd notify support (optional) - import at runtime via importlib to avoid
# static import resolution errors in environments where systemd Python
# bindings aren't installed.

try:
    _systemd_daemon = importlib.import_module("systemd.daemon")
    SYSTEMD_NOTIFY_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    _systemd_daemon = None  # type: ignore[assignment]
    SYSTEMD_NOTIFY_AVAILABLE = False


class FlatpakEventHandler(_BaseFSHandler):
    """Handler for Flatpak installation/removal events with event batching."""

    def __init__(
        self, callback=None, config: dict[str, Any] | None = None
    ) -> None:
        self.callback = callback
        self.last_event_time = 0.0
        self.config = config or {}
        self.cooldown_seconds: float = self.config.get("cooldown", 2)
        self.pending_events: list[tuple[str, str]] = []
        self.batch_window: float = self.config.get("batch_window", 1.0)
        self.batch_timer: threading.Timer | None = None
        self._event_lock: threading.Lock | None = None
        self._init_lock()

    def _init_lock(self) -> None:
        """Initialize thread lock for event queueing."""
        try:
            self._event_lock = threading.Lock()
        except ImportError:
            self._event_lock = None

    def on_created(self, event) -> None:
        """Called when a new file/directory is created."""
        if should_process_event(event.src_path):
            self._queue_event("created", event.src_path)

    def on_deleted(self, event) -> None:
        """Called when a file/directory is deleted."""
        if should_process_event(event.src_path):
            self._queue_event("deleted", event.src_path)

    def on_modified(self, event) -> None:
        """Called when a file/directory is modified."""
        if should_process_event(event.src_path):
            self._queue_event("modified", event.src_path)

    def on_moved(self, event) -> None:
        """Called when a file/directory is moved."""
        if should_process_event(event.src_path):
            self._queue_event("moved", event.src_path)
        if should_process_event(event.dest_path):
            self._queue_event("moved", event.dest_path)

    def _queue_event(self, event_type: str, path: str) -> None:
        """Queue event for batching instead of processing immediately."""
        if self._event_lock:
            with self._event_lock:
                self._queue_event_unlocked(event_type, path)
        else:
            self._queue_event_unlocked(event_type, path)

    def _queue_event_unlocked(self, event_type: str, path: str) -> None:
        """Queue event without lock (internal method)."""
        event_key = (event_type, path)
        if event_key not in self.pending_events:
            self.pending_events.append(event_key)
            logger.debug("Queued event: %s - %s", event_type, path)

        if self.batch_timer is not None:
            self.batch_timer.cancel()

        self.batch_timer = threading.Timer(
            self.batch_window,
            self._flush_pending_events,
        )
        if self.batch_timer is not None:
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

        current_time = time.time()
        if current_time - self.last_event_time < self.cooldown_seconds:
            delay = self.cooldown_seconds - (current_time - self.last_event_time)
            # Cancel existing timer before creating new one to prevent race
            if self.batch_timer is not None:
                self.batch_timer.cancel()
            self.batch_timer = threading.Timer(
                delay, self._flush_pending_events
            )
            self.batch_timer.daemon = True
            self.batch_timer.start()
            logger.debug("Cooldown active, rescheduling flush in %.1fs", delay)
            return

        self.last_event_time = current_time

        if self.callback:
            logger.debug(
                "Flushing %d batched events", len(self.pending_events)
            )
            for event_type, path in self.pending_events:
                try:
                    self.callback(event_type, path)
                except Exception as e:
                    logger.error(
                        "Callback failed for %s %s: %s", event_type, path, e, exc_info=True
                    )

        self.pending_events = []
        self.batch_timer = None


class FlatpakMonitor:
    """Monitor for Flatpak installation changes."""

    def __init__(
        self,
        callback=None,
        bin_dir: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.callback = callback
        self.bin_dir = bin_dir
        self.observer: Any = None
        self.running = False
        self.config = config or {}

        self.watch_paths = self._get_watch_paths()

        self._systemd_notify_sent = False

    def _get_watch_paths(self) -> list[str]:
        """Get paths that should be monitored for Flatpak changes."""
        paths: list[str] = []

        if Path("/var/lib/flatpak").exists():
            paths.append("/var/lib/flatpak")

        user_flatpak = str(Path("~/.local/share/flatpak").expanduser())
        if Path(user_flatpak).exists():
            paths.append(user_flatpak)

        user_app_data = str(Path("~/.var/app").expanduser())
        if Path(user_app_data).exists():
            paths.append(user_app_data)

        return paths

    def _send_systemd_notify(self, status: str = "READY=1") -> None:
        """Send notification to systemd."""
        if SYSTEMD_NOTIFY_AVAILABLE and _systemd_daemon is not None:
            try:
                _systemd_daemon.notify(status)
                logger.debug("Systemd notify sent: %s", status)
                if status == "READY=1":
                    self._systemd_notify_sent = True
            except OSError as e:
                logger.warning("Failed to send systemd notify: %s", e)

    def start_monitoring(self) -> bool:
        """Start monitoring for Flatpak changes."""
        observer_cls = _get_observer_cls()
        if not WATCHDOG_AVAILABLE or observer_cls is None:
            logger.error("Watchdog library not available")
            return False

        try:
            self.observer = observer_cls() if observer_cls is not None else None

            event_handler = FlatpakEventHandler(
                callback=self._on_flatpak_change,
                config=self.config,
            )

            for path in self.watch_paths:
                if Path(path).exists() and self.observer is not None:
                    self.observer.schedule(event_handler, path, recursive=True)
                    logger.info("Watching path: %s", path)

            if self.observer is not None:
                self.observer.start()
            self.running = True

            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            self._send_systemd_notify()

            logger.info("Flatpak monitor started successfully")
            return True

        except Exception as e:
            logger.error("Failed to start Flatpak monitor: %s", e, exc_info=True)
            return False

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        if self.observer and self.running:
            logger.info("Stopping Flatpak monitor")
            self.observer.stop()
            self.observer.join(timeout=5)
            self.running = False
            logger.info("Flatpak monitor stopped")

    def _on_change(self, event) -> None:
        """Handle simple event objects with src_path and event_type."""
        path = getattr(event, "src_path", "")
        event_type = getattr(event, "event_type", "modified")

        if should_process_event(path):
            self._on_flatpak_change(event_type, path)

    def _on_flatpak_change(self, event_type: str, path: str) -> None:
        """Handle Flatpak-related file system changes."""
        logger.debug("Flatpak change detected: %s - %s", event_type, path)

        if self._should_regenerate_wrappers(path):
            logger.info(
                "Regenerating Flatpak wrappers due to change: %s", path
            )
            success = self._regenerate_wrappers()
            if success:
                logger.info("Flatpak wrappers regenerated successfully")
            else:
                logger.error("Failed to regenerate Flatpak wrappers")

        if self.callback:
            with contextlib.suppress(Exception):
                self.callback(event_type, path)

    def _should_regenerate_wrappers(self, path: str) -> bool:
        """Determine if wrappers should be regenerated based on the path."""
        path_str = str(path).lower()

        if (
            "/exports/" in path_str
            or "/app/" in path_str
            or path_str.endswith("/app")
        ):
            return True

        return "/metadata" in path_str or "/manifest" in path_str

    def _regenerate_wrappers(self) -> bool:
        """Regenerate Flatpak wrappers (non-blocking if already running)."""
        from .python_utils import acquire_lock, release_lock

        if not acquire_lock("generate", timeout_seconds=0.001):
            logger.debug("Generation already in progress, skipping")
            return False
        try:
            return self._run_regeneration_sync()
        finally:
            release_lock("generate")

    def _run_regeneration_sync(self) -> bool:
        """Run wrapper regeneration synchronously."""
        for script_path in self._find_generate_scripts():
            if Path(script_path).exists() and os.access(script_path, os.X_OK):
                return self._run_generate(script_path)
        logger.error("fplaunch-generate script not found")
        return False

    def _regenerate_wrappers_async(self) -> None:
        """Trigger wrapper regeneration in a background thread."""
        thread = threading.Thread(target=self._regenerate_wrappers, daemon=True)
        thread.start()

    def _find_generate_scripts(self) -> list[str]:
        """Build list of possible fplaunch-generate script locations."""
        script_paths = []
        generate_cmd = shutil.which("fplaunch-generate")
        if generate_cmd:
            script_paths.append(generate_cmd)
        script_paths.extend(
            [
                "/usr/local/bin/fplaunch-generate",
                "/usr/bin/fplaunch-generate",
            ],
        )
        dev_script = Path(__file__).parent.parent / "fplaunch-generate"
        if dev_script.exists():
            script_paths.insert(1, str(dev_script))
        return script_paths

    def _run_generate(self, script_path: str) -> bool:
        """Run a specific regeneration script."""
        try:
            logger.debug(
                "Running wrapper regeneration script: %s", script_path
            )
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
            logger.error(
                "Wrapper regeneration failed with code %d: %s",
                result.returncode,
                result.stderr.strip(),
            )
            return False
        except subprocess.TimeoutExpired:
            logger.error("Wrapper regeneration timed out")
            return False
        except OSError as e:
            logger.error("Failed to regenerate wrappers: %s", e)
            return False

    def _signal_handler(self, signum: int, _frame: object) -> None:
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
    callback: Any = None,
    daemon: bool = False,
    config: dict[str, Any] | None = None,
) -> FlatpakMonitor:
    """Start Flatpak monitoring (convenience function)."""
    monitor = FlatpakMonitor(callback=callback, config=config)

    if daemon:
        thread = threading.Thread(
            target=monitor.start_monitoring, daemon=True
        )
        thread.start()
        return monitor

    if monitor.start_monitoring():
        monitor.wait()
    return monitor


def main(
    daemon: bool = False,
    callback: str | None = None,
    config: dict[str, Any] | None = None,
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
        start_flatpak_monitoring(
            callback=callback, daemon=daemon, config=config
        )
        return

    parser = argparse.ArgumentParser(
        description="Flatpak installation monitoring service",
    )
    parser.add_argument(
        "-d",
        "--daemon",
        action="store_true",
        help="Run in background as a daemon",
    )
    parser.add_argument(
        "-c",
        "--callback",
        type=str,
        default=None,
        help="Callback function to execute on events "
        "(format: module:function)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
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

    logger.setLevel(getattr(logging, args.log_level.upper()))

    callback_func = None
    if args.callback:
        try:
            module_name, func_name = args.callback.split(":")
            module = importlib.import_module(module_name)
            callback_func = getattr(module, func_name)
        except (ValueError, ImportError, AttributeError) as e:
            logger.error("Failed to load callback %s: %s", args.callback, e)
            sys.exit(1)

    config_dict = {
        "batch_window": args.batch_window,
        "cooldown": args.cooldown,
        "debounce": args.debounce,
        "regeneration_timeout": args.regeneration_timeout,
        "log_level": args.log_level.upper(),
    }

    logger.info(
        "Starting Flatpak monitor with configuration: %s", config_dict
    )
    monitor = start_flatpak_monitoring(
        callback=callback_func,
        daemon=args.daemon,
        config=config_dict,
    )

    if not args.daemon and monitor:
        # In non-daemon mode, wait for events until interrupted
        monitor.wait()


if __name__ == "__main__":
    main()
