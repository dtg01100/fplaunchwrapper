# Flatpak Launch Wrappers

A utility to create small wrapper scripts for Flatpak applications, allowing you to launch them by their simplified name (e.g., `chrome` instead of `flatpak run com.google.Chrome`). It handles conflicts with system packages, remembers user preferences, and provides management tools.

## Features

- Generates wrappers for user and system Flatpak apps
- Automatic updates via systemd (user changes trigger immediately, system changes daily)
- Conflict resolution: Choose between system package or Flatpak app
- Preference memory: Remembers choices to avoid repeated prompts
- Management script: Interactive menu or CLI for configuring wrappers
- Block/unblock specific apps
- Customizable wrapper directory

## Installation

1. Clone or download the scripts.
2. Run `bash install.sh [optional_bin_dir]` to install (default bin dir: `~/bin`).
3. Ensure `~/bin` (or your chosen dir) is in your PATH.

## Usage

- Launch apps: `chrome`, `firefox`, etc.
- Get info: `chrome --wrapper-info` or `chrome --help`.
- Manage: `bash manage_wrappers.sh` for interactive menu, or use CLI commands like `bash manage_wrappers.sh list`.

## Scripts

- `install.sh`: Sets up wrappers and systemd units.
- `uninstall.sh`: Removes everything.
- `generate_flatpak_wrappers.sh`: Generates/updates wrappers.
- `setup_systemd.sh`: Configures systemd for auto-updates.
- `manage_wrappers.sh`: Management utility.

## Requirements

- Bash
- Flatpak
- Systemd (for auto-updates)

## License

MIT or whatever.