#!/usr/bin/env bash

NAME="testapp"
ID="com.test.App"
SCRIPT_BIN_DIR="/usr/local/bin"

# Check if running in interactive CLI
is_interactive() {
    [ -t 0 ] && [ -t 1 ] && [ "${FPWRAPPER_FORCE:-}" != "desktop" ]
}

# Non-interactive bypass: skip wrapper and continue PATH search
if ! is_interactive; then
    echo "Non-interactive detected - bypassing wrapper"
    # Find next executable in PATH (skip our wrapper)
    IFS=: read -ra PATH_DIRS <<< "$PATH"
    for dir in "${PATH_DIRS[@]}"; do
        if [ -x "$dir/$NAME" ] && [ "$dir/$NAME" != "$SCRIPT_BIN_DIR/$NAME" ]; then
            echo "Found system command: $dir/$NAME"
            exec "$dir/$NAME" "$@"
        fi
    done
    
    # If no system command found, run flatpak
    echo "No system command found, running flatpak"
    exec flatpak run "$ID" "$@"
else
    echo "Interactive detected - wrapper functionality active"
    echo "Would show prompts and wrapper features here"
fi
