#!/bin/bash

# Install script for Flatpak Launch Wrappers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Sanity checks
echo "Checking dependencies..."
if ! command -v flatpak &> /dev/null; then
    echo "Warning: Flatpak is not installed. This utility requires Flatpak to function."
fi

auto_update_possible=false
if command -v systemctl &> /dev/null && systemctl --user is-systemd-running &> /dev/null 2>&1; then
    auto_update_possible=true
    echo "Systemd user available for auto-updates."
elif command -v crontab &> /dev/null; then
    auto_update_possible=true
    echo "Crontab available for auto-updates."
else
    echo "Warning: Neither systemd nor crontab available. Auto-updates will not be possible."
fi

# Set BIN_DIR from arg or default
BIN_DIR="${1:-$HOME/bin}"

echo "Installing Flatpak Launch Wrappers to $BIN_DIR..."

# Make scripts executable
chmod +x "$SCRIPT_DIR/generate_flatpak_wrappers.sh"
chmod +x "$SCRIPT_DIR/setup_systemd.sh"
chmod +x "$SCRIPT_DIR/manage_wrappers.sh"

# Export BIN_DIR for generate script
export BIN_DIR

# Generate initial wrappers
echo "Generating wrappers..."
bash "$SCRIPT_DIR/generate_flatpak_wrappers.sh" "$BIN_DIR"

# Ask for auto-updates
read -p "Enable automatic updates? (y/n) [y]: " enable_auto
enable_auto=${enable_auto:-y}
if [[ $enable_auto =~ ^[Yy]$ ]]; then
    echo "Setting up automatic updates..."
    bash "$SCRIPT_DIR/setup_systemd.sh"
else
    echo "Skipping automatic updates. Run 'bash $SCRIPT_DIR/generate_flatpak_wrappers.sh $BIN_DIR' manually to update wrappers."
fi

# Copy manager to bin dir
cp "$SCRIPT_DIR/manage_wrappers.sh" "$BIN_DIR/fplaunch-manage"
chmod +x "$BIN_DIR/fplaunch-manage"

echo "Installation complete. Wrappers are in $BIN_DIR. Use 'fplaunch-manage' to configure."