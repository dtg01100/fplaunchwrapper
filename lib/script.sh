#!/usr/bin/env bash
set_script() {
    local name="$1"
    local path="$2"
    if [ ! -f "$BIN_DIR/$name" ]; then
        echo "Wrapper $name not found"
        return 1
    fi
    if [ ! -f "$path" ]; then
        echo "Script $path not found"
        return 1
    fi
    if [ ! -r "$path" ]; then
        echo "Script $path is not readable"
        return 1
    fi
    if [ ! -s "$path" ]; then
        echo "Script $path is empty"
        return 1
    fi
    # Basic size check (100KB limit)
    local size=$(stat -f%z "$path" 2>/dev/null || stat -c%s "$path" 2>/dev/null || echo 0)
    if [ "$size" -gt 100000 ]; then
        echo "Script $path is too large (>100KB)"
        return 1
    fi
    local script_dir="$CONFIG_DIR/scripts/$name"
    mkdir -p "$script_dir"
    cp "$path" "$script_dir/pre-launch.sh"
    chmod +x "$script_dir/pre-launch.sh"
    echo "Set pre-launch script for $name"
}

set_post_script() {
    local name="$1"
    local path="$2"
    if [ ! -f "$BIN_DIR/$name" ]; then
        echo "Wrapper $name not found"
        return 1
    fi
    if [ ! -f "$path" ]; then
        echo "Script $path not found"
        return 1
    fi
    if [ ! -r "$path" ]; then
        echo "Script $path is not readable"
        return 1
    fi
    if [ ! -s "$path" ]; then
        echo "Script $path is empty"
        return 1
    fi
    # Basic size check (100KB limit)
    local size=$(stat -f%z "$path" 2>/dev/null || stat -c%s "$path" 2>/dev/null || echo 0)
    if [ "$size" -gt 100000 ]; then
        echo "Script $path is too large (>100KB)"
        return 1
    fi
    local script_dir="$CONFIG_DIR/scripts/$name"
    mkdir -p "$script_dir"
    cp "$path" "$script_dir/post-run.sh"
    chmod +x "$script_dir/post-run.sh"
    echo "Set post-run script for $name"
}

remove_script() {
    local name="$1"
    local script_dir="$CONFIG_DIR/scripts/$name"
    if [ -f "$script_dir/pre-launch.sh" ]; then
        rm "$script_dir/pre-launch.sh"
        echo "Removed pre-launch script for $name"
    else
        echo "No pre-launch script found for $name"
    fi
}

remove_post_script() {
    local name="$1"
    local script_dir="$CONFIG_DIR/scripts/$name"
    if [ -f "$script_dir/post-run.sh" ]; then
        rm "$script_dir/post-run.sh"
        echo "Removed post-run script for $name"
    else
        echo "No post-run script found for $name"
    fi
}