#!/usr/bin/env bash
launch_wrapper() {
    local name="$1"
    if [ -f "$BIN_DIR/$name" ]; then
        "$BIN_DIR/$name" &
    else
        echo "Wrapper $name not found."
    fi
}