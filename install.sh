#!/usr/bin/env bash

# Install script for Flatpak Launch Wrappers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Sanity checks
echo "Checking dependencies..."
if ! command -v flatpak &> /dev/null; then
    echo "Warning: Flatpak is not installed. This utility requires Flatpak to function."
fi

if command -v systemctl &> /dev/null && systemctl --user is-systemd-running &> /dev/null 2>&1; then
    echo "Systemd user available for auto-updates."
elif command -v crontab &> /dev/null; then
    echo "Crontab available for auto-updates."
else
    echo "Warning: Neither systemd nor crontab available. Auto-updates will not be possible."
fi

# Set BIN_DIR from arg or default
BIN_DIR="${1:-$HOME/.local/bin}"

# Non-interactive mode detection (CI or no TTY)
NON_INTERACTIVE=0
if [ -n "${CI:-}" ] || [ ! -t 0 ]; then
    NON_INTERACTIVE=1
fi

# If custom BIN_DIR provided and interactive, confirm
if [ "$BIN_DIR" != "$HOME/.local/bin" ] && [ "$NON_INTERACTIVE" -eq 0 ]; then
    read -r -p "Install to '$BIN_DIR' instead of default '$HOME/.local/bin'? (y/n) [y]: " confirm
    confirm=${confirm:-y}
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        BIN_DIR="$HOME/.local/bin"
        echo "Using default directory: $BIN_DIR"
    fi
fi

# Ensure BIN_DIR exists and is writable
if ! mkdir -p "$BIN_DIR" 2>/dev/null; then
    echo "Error: Cannot create directory $BIN_DIR"
    exit 1
fi
if [ ! -w "$BIN_DIR" ]; then
    echo "Error: Cannot write to $BIN_DIR"
    exit 1
fi

echo "Installing Flatpak Launch Wrappers to $BIN_DIR..."

# Make scripts executable
chmod +x "$SCRIPT_DIR/fplaunch-generate"
chmod +x "$SCRIPT_DIR/fplaunch-setup-systemd"
chmod +x "$SCRIPT_DIR/manage_wrappers.sh"

# Copy and make lib scripts executable
mkdir -p "$BIN_DIR/lib"
cp "$SCRIPT_DIR/lib/"*.sh "$BIN_DIR/lib/"
chmod +x "$BIN_DIR/lib/"*.sh

# Copy generate and setup scripts
cp "$SCRIPT_DIR/fplaunch-generate" "$BIN_DIR/"
cp "$SCRIPT_DIR/fplaunch-setup-systemd" "$BIN_DIR/"
chmod +x "$BIN_DIR/fplaunch-generate"
chmod +x "$BIN_DIR/fplaunch-setup-systemd"

# Export BIN_DIR for generate script
export BIN_DIR

# Generate initial wrappers
echo "Generating wrappers..."
bash "$SCRIPT_DIR/fplaunch-generate" "$BIN_DIR"

# Ask for auto-updates (skip in CI/non-interactive)
if [ "$NON_INTERACTIVE" -eq 0 ]; then
    read -r -p "Enable automatic updates? (y/n) [y]: " enable_auto
    enable_auto=${enable_auto:-y}
else
    enable_auto=n
fi

if [[ $enable_auto =~ ^[Yy]$ ]]; then
    echo "Setting up automatic updates..."
    bash "$BIN_DIR/fplaunch-setup-systemd"
else
    echo "Skipping automatic updates. Run 'bash $BIN_DIR/fplaunch-generate $BIN_DIR' or 'fplaunch-manage regenerate' manually to update wrappers."
fi

# Copy manager and completion
cp "$SCRIPT_DIR/manage_wrappers.sh" "$BIN_DIR/fplaunch-manage"
chmod +x "$BIN_DIR/fplaunch-manage"

if [ -d "$HOME/.bashrc.d" ]; then
    cp "$SCRIPT_DIR/fplaunch_completion.bash" "$HOME/.bashrc.d/fplaunch_completion.bash"
    echo "Bash completion installed to ~/.bashrc.d/fplaunch_completion.bash"
else
    cp "$SCRIPT_DIR/fplaunch_completion.bash" "$BIN_DIR/fplaunch_completion.bash"
    echo "Bash completion copied to $BIN_DIR/fplaunch_completion.bash"
    echo "To enable, add 'source $BIN_DIR/fplaunch_completion.bash' to your ~/.bashrc"
fi

echo "Installation complete. Wrappers are in $BIN_DIR. Use 'fplaunch-manage' to configure."