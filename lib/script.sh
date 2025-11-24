#!/usr/bin/env bash
set_script() {
    local name="$1"
    local path="$2"
    if [ ! -f "$BIN_DIR/$name" ]; then
        echo "Wrapper $name not found"
    fi
    if [ ! -f "$path" ]; then
        echo "Script $path not found"
    fi
    local script_dir="$CONFIG_DIR/scripts/$name"
    mkdir -p "$script_dir"
    cp "$path" "$script_dir/pre-launch.sh"
    chmod +x "$script_dir/pre-launch.sh"
    echo "Set pre-launch script for $name"
}