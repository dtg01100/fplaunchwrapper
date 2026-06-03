#!/usr/bin/env python3
"""Built-in permission presets for fplaunchwrapper.

These presets define common combinations of Flatpak permission flags that
users can apply to their wrappers. Custom presets can also be added via
the configuration system.
"""

from __future__ import annotations

BUILTIN_PRESETS: dict[str, list[str]] = {
    "development": [
        "--filesystem=home",
        "--filesystem=host",
        "--device=dri",
        "--socket=x11",
        "--socket=wayland",
        "--share=ipc",
    ],
    "media": [
        "--device=dri",
        "--socket=pulseaudio",
        "--socket=wayland",
        "--socket=x11",
        "--share=ipc",
        "--filesystem=~/Music",
        "--filesystem=~/Videos",
    ],
    "network": [
        "--share=network",
        "--share=ipc",
        "--socket=x11",
        "--socket=wayland",
    ],
    "minimal": ["--share=ipc"],
    "gaming": [
        "--device=dri",
        "--device=input",
        "--socket=pulseaudio",
        "--socket=wayland",
        "--socket=x11",
        "--share=ipc",
        "--share=network",
        "--filesystem=~/Games",
    ],
    "offline": [
        "--device=dri",
        "--socket=pulseaudio",
        "--socket=wayland",
        "--socket=x11",
        "--share=ipc",
        "--filesystem=home",
    ],
}


__all__ = ["BUILTIN_PRESETS"]
