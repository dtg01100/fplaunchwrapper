#!/usr/bin/env python3
"""Desktop Entry file parser for Flatpak applications.

Parses .desktop files according to the XDG Desktop Entry specification,
extracting metadata such as app name, icon, categories, and Flatpak-specific fields.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional


class DesktopEntry:
    """Represents a parsed .desktop file entry."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._entries: dict[str, dict[str, str]] = {}
        self._raw_lines: list[str] = []
        self._parse()

    def _parse(self) -> None:
        """Parse the .desktop file."""
        try:
            content = self.file_path.read_text(errors="replace")
            self._raw_lines = content.splitlines()
        except (OSError, IOError):
            return

        current_section = None
        for line in self._raw_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("[") and stripped.endswith("]"):
                current_section = stripped[1:-1]
                if current_section not in self._entries:
                    self._entries[current_section] = {}
                continue

            if current_section and "=" in stripped:
                key, _, value = stripped.partition("=")
                self._entries[current_section][key.strip()] = value.strip()

    def get(
        self, key: str, section: str = "Desktop Entry", default: Optional[str] = None
    ) -> Optional[str]:
        """Get a value from the desktop entry.

        Args:
            key: The key to retrieve
            section: The section (default: "Desktop Entry")
            default: Default value if key not found

        Returns:
            The value or default
        """
        return self._entries.get(section, {}).get(key, default)

    def get_localized(
        self, key: str, section: str = "Desktop Entry", locale: Optional[str] = None
    ) -> Optional[str]:
        """Get a localized value from the desktop entry.

        Args:
            key: The key to retrieve
            section: The section (default: "Desktop Entry")
            locale: The locale to use (e.g., "en_US"). If None, uses system locale.

        Returns:
            The localized value or the non-localized fallback
        """
        if locale is None:
            locale = os.environ.get("LANG", "en_US").replace("_", ".")

        # Try localized version first
        localized_key = f"{key}[{locale}]"
        value = self.get(localized_key, section)
        if value:
            return value

        # Try language-only locale
        lang = locale.split(".")[0]
        localized_key = f"{key}[{lang}]"
        value = self.get(localized_key, section)
        if value:
            return value

        # Fall back to non-localized
        return self.get(key, section)

    @property
    def name(self) -> Optional[str]:
        """Get the application name."""
        return self.get_localized("Name") or self.file_path.stem

    @property
    def comment(self) -> Optional[str]:
        """Get the application comment/description."""
        return self.get_localized("Comment")

    @property
    def icon(self) -> Optional[str]:
        """Get the icon path or name."""
        return self.get("Icon")

    @property
    def categories(self) -> list[str]:
        """Get the application categories."""
        cats = self.get("Categories") or ""
        return [c.strip() for c in cats.split(";") if c.strip()]

    @property
    def flatpak_id(self) -> Optional[str]:
        """Get the Flatpak ID from X-Flatpak field."""
        return self.get("X-Flatpak")

    @property
    def exec_command(self) -> Optional[str]:
        """Get the exec command."""
        return self.get("Exec")

    @property
    def terminal_required(self) -> bool:
        """Check if the app requires a terminal."""
        value = self.get("Terminal") or "false"
        return value.lower() == "true"

    @property
    def is_hidden(self) -> bool:
        """Check if the app is hidden."""
        value = self.get("Hidden") or "false"
        return value.lower() == "true"

    @property
    def no_display(self) -> bool:
        """Check if the app should not be displayed."""
        value = self.get("NoDisplay") or "false"
        return value.lower() == "true"


def find_desktop_files(directory: Path, recursive: bool = True) -> list[Path]:
    """Find all .desktop files in a directory.

    Args:
        directory: The directory to search
        recursive: Whether to search recursively

    Returns:
        List of .desktop file paths
    """
    if not directory.exists() or not directory.is_dir():
        return []

    if recursive:
        return list(directory.rglob("*.desktop"))
    return list(directory.glob("*.desktop"))


def parse_flatpak_desktop_files(
    flatpak_dir: Optional[Path] = None,
) -> dict[str, DesktopEntry]:
    """Find and parse all Flatpak .desktop files.

    Args:
        flatpak_dir: Optional custom Flatpak directory. If None, uses default locations.

    Returns:
        Dictionary mapping Flatpak ID to DesktopEntry
    """
    results: dict[str, DesktopEntry] = {}
    search_dirs = []

    if flatpak_dir:
        search_dirs.append(flatpak_dir)
    else:
        # Default Flatpak locations
        user_share = Path.home() / ".local" / "share" / "flatpak"
        system_share = Path("/var/lib/flatpak")

        if user_share.exists():
            search_dirs.append(user_share)
        if system_share.exists():
            search_dirs.append(system_share)

    for search_dir in search_dirs:
        # Look in both apps and desktop dirs
        for subdir in [
            "apps",
            "current/active/files/share/applications",
            "exports/share/applications",
        ]:
            apps_dir = search_dir / subdir
            for desktop_file in find_desktop_files(apps_dir):
                entry = DesktopEntry(desktop_file)
                if entry.flatpak_id:
                    results[entry.flatpak_id] = entry
                elif entry.name:
                    # Fallback: use filename stem as ID if no X-Flatpak
                    results[desktop_file.stem] = entry

    return results


def get_app_metadata(
    flatpak_id: str, desktop_entries: Optional[dict[str, DesktopEntry]] = None
) -> dict[str, Any]:
    """Get metadata for a Flatpak app.

    Args:
        flatpak_id: The Flatpak application ID
        desktop_entries: Optional pre-fetched desktop entries. If None, will search.

    Returns:
        Dictionary with app metadata (name, icon, categories, comment)
    """
    if desktop_entries is None:
        desktop_entries = parse_flatpak_desktop_files()

    entry = desktop_entries.get(flatpak_id)

    if entry:
        return {
            "name": entry.name,
            "comment": entry.comment,
            "icon": entry.icon,
            "categories": entry.categories,
            "terminal": entry.terminal_required,
            "exec": entry.exec_command,
        }

    # Fallback: construct from ID
    return {
        "name": flatpak_id.split(".")[-1].replace("-", " ").title(),
        "comment": None,
        "icon": flatpak_id,
        "categories": [],
        "terminal": False,
        "exec": None,
    }
