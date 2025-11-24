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
2. Run `bash install.sh [optional_bin_dir]` to install (default bin dir: `~/bin`).
3. Ensure `~/bin` (or your chosen dir) is in your PATH.

## Usage

- Launch apps: `chrome`, `firefox`, etc.
- Get info: `chrome --wrapper-info` or `chrome --help`.
- Manage: `bash manage_wrappers.sh` for interactive menu (uses dialog if available), or CLI commands like `bash manage_wrappers.sh list`.
- Examples:
  - `bash manage_wrappers.sh set-alias chrome browser`
  - `bash manage_wrappers.sh export-prefs prefs.tar.gz`
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
- Systemd (for auto-updates)

## License

MIT