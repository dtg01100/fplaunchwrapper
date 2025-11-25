#!/usr/bin/env bash
export_prefs() {
    local file="$1"
    tar -czf "$file" -C "$CONFIG_DIR" prefs blocklist 2>/dev/null
    echo "Exported preferences to $file"
}

import_prefs() {
    local file="$1"
    if [ -f "$file" ]; then
        # Validate tar contents before extraction
        if tar -tzf "$file" 2>/dev/null | grep -q '\.\.'; then
            echo "Error: Archive contains suspicious paths. Import cancelled for security."
            return 1
        fi
        tar -xzf "$file" -C "$CONFIG_DIR" 2>/dev/null
        echo "Imported preferences from $file"
    else
        echo "File $file not found"
    fi
}

export_config() {
    local file="$1"
    tar -czf "$file" -C "$CONFIG_DIR" . 2>/dev/null
    echo "Exported full config to $file"
}

import_config() {
    local file="$1"
    if [ -f "$file" ]; then
        # Validate tar contents before extraction
        if tar -tzf "$file" 2>/dev/null | grep -q '\.\.'; then
            echo "Error: Archive contains suspicious paths. Import cancelled for security."
            return 1
        fi
        tar -xzf "$file" -C "$CONFIG_DIR" 2>/dev/null
        echo "Imported full config from $file"
    else
        echo "File $file not found"
    fi
}