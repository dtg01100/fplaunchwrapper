#!/bin/bash

# Install script for Flatpak Launch Wrappers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Setup systemd units
echo "Setting up systemd units..."
bash "$SCRIPT_DIR/setup_systemd.sh"

echo "Installation complete. Wrappers are in $BIN_DIR. Use manage_wrappers.sh to configure."