#!/usr/bin/env bash

# Uninstall script for Flatpak Launch Wrappers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
if [ -f "$SCRIPT_DIR/lib/common.sh" ]; then
    # shellcheck source=lib/common.sh
    source "$SCRIPT_DIR/lib/common.sh"
fi

init_paths

# Validate BIN_DIR is within user's home directory
if ! validate_home_dir "$BIN_DIR" "uninstallation"; then
    echo "This script only operates on user installations."
    exit 1
fi

read -r -p "Uninstall Flatpak Launch Wrappers from '$BIN_DIR'? This will remove all wrappers and preferences. (y/n): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

echo "Uninstalling Flatpak Launch Wrappers from $BIN_DIR..."

# Stop and disable systemd units, remove unit files
cleanup_systemd_units "flatpak-wrappers"

# Remove cron job if exists
if command -v crontab &> /dev/null; then
    crontab -l 2>/dev/null | grep -v "$SCRIPT_DIR/fplaunch-generate" | crontab -
fi

# Remove wrappers, aliases, and manager
for script in "$BIN_DIR"/*; do
    if is_wrapper_file "$script"; then
        rm "$script"
    elif [ -L "$script" ] && [ -f "$script" ] && is_wrapper_file "$script"; then
        # Check if symlink target is our wrapper
        rm "$script"
    elif [ "$script" = "$BIN_DIR/fplaunch-manage" ]; then
        rm "$script"
    fi
done

# Remove installed scripts and lib directory
rm -f "$BIN_DIR/fplaunch-generate"
rm -f "$BIN_DIR/fplaunch-setup-systemd"
rm -f "$BIN_DIR/fplaunch-cleanup"
if [ -n "$BIN_DIR" ] && [ -d "$BIN_DIR/lib" ]; then
    rm -rf "${BIN_DIR:?}/lib"
fi

# Remove bash completion
rm -f "$HOME/.bashrc.d/fplaunch_completion.bash"

# Remove man pages
MAN_DIR="$HOME/.local/share/man"
if [ -d "$MAN_DIR" ]; then
    rm -f "$MAN_DIR/man1/fplaunch-"*.1 2>/dev/null || true
    rm -f "$MAN_DIR/man7/fplaunchwrapper."* 2>/dev/null || true
    # Clean up empty directories
    rmdir "$MAN_DIR/man1" 2>/dev/null || true
    rmdir "$MAN_DIR/man7" 2>/dev/null || true
    rmdir "$MAN_DIR" 2>/dev/null || true
fi

# Remove config directory
rm -rf "$CONFIG_DIR"

echo "Uninstallation complete. All wrappers, preferences, man pages, and systemd units removed."