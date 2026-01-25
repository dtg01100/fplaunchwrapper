import importlib, sys

# Ensure fplaunch.notifications refers to the same module object as lib.notifications
_mod = importlib.import_module("lib.notifications")
sys.modules["fplaunch.notifications"] = _mod

from lib.notifications import (
    notify_send_available,
    send_notification,
    send_update_failure_notification,
)
