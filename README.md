# Flatpak Launch Wrappers

A utility to create small wrapper scripts for Flatpak applications, allowing you to launch them by their simplified name (e.g., `chrome` instead of `flatpak run com.google.Chrome`). It handles conflicts with system packages, remembers user preferences, and provides management tools.

## Features

- Generates wrappers for user and system Flatpak apps
- Automatic updates via systemd (user changes trigger immediately, system changes daily)
- Conflict resolution: Choose between system package or Flatpak app, with preference memory
- Aliases: Create custom names for wrappers
- Help and info: `--help` and `--wrapper-info` flags on wrappers
- Backup/restore: Export/import preferences and blocklists
- Management script: Interactive menu (with dialog GUI fallback) or CLI for configuring wrappers
- Block/unblock specific apps
- Customizable wrapper directory

## Installation

1. Clone or download the scripts.
2. Run `bash install.sh [optional_bin_dir]` to install (default bin dir: `~/bin`). You'll be prompted to enable automatic updates.
3. Ensure `~/bin` (or your chosen dir) is in your PATH.

## Usage

- Launch apps: `chrome`, `firefox`, etc.
- Get info: `chrome --wrapper-info` or `chrome --help`.
- Manage: `fplaunch-manage` for interactive menu (uses dialog if available), or CLI commands like `fplaunch-manage list`.
- Examples:
  - `fplaunch-manage set-alias chrome browser`
  - `fplaunch-manage export-prefs prefs.tar.gz`
  - `bash manage_wrappers.sh block com.example.App`

## Scripts

- `install.sh`: Sets up wrappers and systemd units (accepts optional bin directory).
- `uninstall.sh`: Removes wrappers, preferences, and systemd units.
- `generate_flatpak_wrappers.sh`: Generates/updates wrappers.
- `setup_systemd.sh`: Configures systemd for auto-updates.
- `manage_wrappers.sh`: Management utility with commands: list, remove, remove-pref, set-pref, set-alias, remove-alias, export-prefs, import-prefs, block, unblock, list-blocked, regenerate.

## Requirements

- Bash
- Flatpak
- Systemd or crontab (optional, for auto-updates; falls back to crontab if systemd unavailable)

## License

MIT