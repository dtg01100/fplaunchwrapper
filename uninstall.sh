#!/bin/bash

# Uninstall script for Flatpak Launch Wrappers

CONFIG_DIR="$HOME/.config/flatpak-wrappers"
BIN_DIR_FILE="$CONFIG_DIR/bin_dir"
BIN_DIR="$HOME/bin"  # default
if [ -f "$BIN_DIR_FILE" ]; then
    BIN_DIR=$(cat "$BIN_DIR_FILE")
fi

echo "Uninstalling Flatpak Launch Wrappers from $BIN_DIR..."

# Stop and disable systemd units
systemctl --user stop flatpak-wrappers.service 2>/dev/null || true
systemctl --user stop flatpak-wrappers.path 2>/dev/null || true
systemctl --user stop flatpak-wrappers.timer 2>/dev/null || true
systemctl --user disable flatpak-wrappers.service 2>/dev/null || true
systemctl --user disable flatpak-wrappers.path 2>/dev/null || true
systemctl --user disable flatpak-wrappers.timer 2>/dev/null || true

# Remove systemd unit files
UNIT_DIR="$HOME/.config/systemd/user"
rm -f "$UNIT_DIR/flatpak-wrappers.service"
rm -f "$UNIT_DIR/flatpak-wrappers.path"
rm -f "$UNIT_DIR/flatpak-wrappers.timer"
systemctl --user daemon-reload 2>/dev/null || true

# Remove wrappers
for script in "$BIN_DIR"/*; do
    if [ -f "$script" ] && grep -q "flatpak run" "$script" 2>/dev/null; then
        rm "$script"
    fi
done

# Remove config directory
rm -rf "$CONFIG_DIR"

echo "Uninstallation complete. Wrappers, preferences, and systemd units removed."