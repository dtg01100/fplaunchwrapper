#!/usr/bin/env bash

# Install script for Flatpak Launch Wrappers

# Safety check - never run as root
if [ "$(id -u)" = "0" ]; then
    echo "ERROR: install.sh should never be run as root for safety"
    echo "This tool is designed for user-level wrapper management only"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
if [ -f "$SCRIPT_DIR/lib/common.sh" ]; then
    # shellcheck source=lib/common.sh
    source "$SCRIPT_DIR/lib/common.sh"
fi

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

# Validate BIN_DIR is within user's home directory
if ! validate_home_dir "$BIN_DIR" "installation"; then
    exit 1
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

# Optional: also copy cleanup helper for convenience (user-run only)
cp "$SCRIPT_DIR/fplaunch-cleanup" "$BIN_DIR/fplaunch-cleanup" 2>/dev/null || true
chmod +x "$BIN_DIR/fplaunch-cleanup" 2>/dev/null || true

setup_path() {
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        # Detect shell and add to appropriate config file
        local shell_config=""
        local shell_name=""
        
        # Determine current shell
        if [ -n "${ZSH_VERSION:-}" ] || [ "$SHELL" = "/bin/zsh" ] || [ "$SHELL" = "/usr/bin/zsh" ]; then
            shell_name="zsh"
            if [ -f "$HOME/.zshrc" ]; then
                shell_config="$HOME/.zshrc"
            elif [ -f "$HOME/.zprofile" ]; then
                shell_config="$HOME/.zprofile"
            fi
        elif [ -n "${BASH_VERSION:-}" ] || [ "$SHELL" = "/bin/bash" ] || [ "$SHELL" = "/usr/bin/bash" ]; then
            shell_name="bash"
            if [ -f "$HOME/.bashrc" ]; then
                shell_config="$HOME/.bashrc"
            elif [ -f "$HOME/.bash_profile" ]; then
                shell_config="$HOME/.bash_profile"
            fi
        fi
        
        # If no config file found, create one based on shell
        if [ -z "$shell_config" ]; then
            if [ "$shell_name" = "zsh" ]; then
                shell_config="$HOME/.zshrc"
            else
                shell_config="$HOME/.bashrc"
            fi
        fi
        
        # Add PATH to config file
        echo "" >> "$shell_config"
        echo "# Added by fplaunchwrapper installation" >> "$shell_config"
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$shell_config"
        
        echo "✅ Added $BIN_DIR to PATH in $shell_config"
        echo "💡 Run 'source $shell_config' or restart your terminal to use wrappers immediately"
    else
        echo "✅ $BIN_DIR is already in PATH"
    fi
}

setup_path

mkdir -p "$HOME/.bashrc.d"
cp "$SCRIPT_DIR/fplaunch_completion.bash" "$HOME/.bashrc.d/fplaunch_completion.bash"
echo "Bash completion installed to ~/.bashrc.d/fplaunch_completion.bash"

# Auto-source completion if not already done
if ! grep -q "fplaunch_completion.bash" "$HOME/.bashrc" 2>/dev/null; then
    echo "" >> "$HOME/.bashrc"
    echo "# fplaunchwrapper bash completion" >> "$HOME/.bashrc"
    echo "source ~/.bashrc.d/fplaunch_completion.bash" >> "$HOME/.bashrc"
    echo "✅ Bash completion auto-enabled in ~/.bashrc"
else
    echo "✅ Bash completion already configured"
fi

# Install man pages to user's local man directory
if [ -d "$SCRIPT_DIR/docs/man" ]; then
    MAN_DIR="$HOME/.local/share/man"
    echo "Installing man pages to $MAN_DIR..."
    mkdir -p "$MAN_DIR/man1" "$MAN_DIR/man7"
    cp "$SCRIPT_DIR/docs/man/"*.1 "$MAN_DIR/man1/" 2>/dev/null || true
    cp "$SCRIPT_DIR/docs/man/"*.7 "$MAN_DIR/man7/" 2>/dev/null || true
    
    # Update MANPATH if not already set
    if [[ ":$MANPATH:" != *":$MAN_DIR:"* ]]; then
        echo "Note: Add '$MAN_DIR' to your MANPATH to view man pages."
        echo "      Add to ~/.bashrc: export MANPATH=\"$MAN_DIR:\$MANPATH\""
    fi
fi

show_welcome_message() {
    echo ""
    echo "🎉 Welcome to fplaunchwrapper!"
    echo ""
    echo "Quick start:"
    echo "  fplaunch-manage list          # See your wrappers"
    echo "  firefox                       # Launch Firefox (if installed)"
    echo "  firefox --fpwrapper-help      # See wrapper options"
    echo ""
    echo "Learn more:"
    echo "  man fplaunchwrapper           # Full documentation"
    echo "  fplaunch-manage help          # Command help"
    echo "  fplaunch-manage discover      # Discover features"
    echo ""
    echo "💡 Pro tip: Use 'fplaunch-manage discover' to see advanced features!"
}

echo ""
echo "Installation complete!"
echo "Wrappers are in $BIN_DIR"
echo ""
show_welcome_message