import importlib, sys

# Ensure fplaunch.notifications refers to the same module object as lib.notifications
_mod = importlib.import_module("lib.notifications")
sys.modules["fplaunch.notifications"] = _mod

from lib.notifications import *

