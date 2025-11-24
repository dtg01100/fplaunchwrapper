#!/usr/bin/env bash
install_app() {
    local app="$1"
    local remote="${2:-flathub}"
    echo "Installing $app from $remote..."
    if flatpak install "$remote" "$app" -y; then
        echo "Regenerating wrappers..."
        "$SCRIPT_DIR/generate_flatpak_wrappers.sh" "$BIN_DIR" > /dev/null
        local id
        id=$(flatpak info "$app" 2>/dev/null | grep "^ID:" | awk '{print $2}')
        if [ -n "$id" ]; then
            local name
        name=$(echo "$id" | awk -F. '{print tolower($NF)}')
            if [ -f "$BIN_DIR/$name" ]; then
                echo "Launching $name..."
                "$BIN_DIR/$name" &
            fi
        fi
    else
        echo "Installation failed."
    fi
}