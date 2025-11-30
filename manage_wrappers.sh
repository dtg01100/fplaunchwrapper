#!/usr/bin/env bash

# Safety check - never run as root
if [ "$(id -u)" = "0" ]; then
    echo "ERROR: manage_wrappers.sh should never be run as root for safety"
    echo "This tool is designed for user-level wrapper management only"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
if [ -f "$SCRIPT_DIR/lib/common.sh" ]; then
    # shellcheck source=lib/common.sh
    source "$SCRIPT_DIR/lib/common.sh"
elif [ -f "${SCRIPT_DIR%/bin}/lib/common.sh" ]; then
    # When installed, lib is relative to bin parent
    # shellcheck source=lib/common.sh
    source "${SCRIPT_DIR%/bin}/lib/common.sh"
fi

# Source library functions
for lib in pref env alias script launch; do
    if [ -f "$SCRIPT_DIR/lib/$lib.sh" ]; then
        # shellcheck source=lib/$lib.sh
        source "$SCRIPT_DIR/lib/$lib.sh"
    elif [ -f "${SCRIPT_DIR%/bin}/lib/$lib.sh" ]; then
        # shellcheck source=lib/$lib.sh
        source "${SCRIPT_DIR%/bin}/lib/$lib.sh"
    fi
done

# Check for --help as first argument
if [ "$1" = "--help" ]; then
    cat << 'EOF'
Usage: fplaunch-manage <command> [args]
       fplaunch-manage --help

For command-specific help: fplaunch-manage <command> --help

Flatpak Launch Wrapper management utility.
EOF
    exit 0
fi

init_paths
BLOCKLIST="$CONFIG_DIR/blocklist"

ensure_config_dir

usage() {
    cat << 'EOF'
Usage: fplaunch-manage <command> [args]
Commands:
  help                 - Show this help
  list                 - List current wrappers
  search <keyword>     - Search wrappers by name, ID, or description
  remove name          - Remove a specific wrapper
  remove-pref name     - Remove preference for a wrapper
  set-pref name system|flatpak - Set preference for a wrapper
  set-env name var value - Set environment variable for a wrapper
  remove-env name var  - Remove environment variable for a wrapper
  list-env name        - List environment variables for a wrapper
  set-pref-all system|flatpak - Set preference for all wrappers
  set-script name path - Set pre-launch script for a wrapper
   set-post-script name path - Set post-run script for a wrapper
   remove-script name - Remove pre-launch script for a wrapper
   remove-post-script name - Remove post-run script for a wrapper
  set-alias name alias - Set an alias for a wrapper
  remove-alias alias   - Remove an alias
  export-prefs file    - Export preferences and blocklist to file
  import-prefs file    - Import preferences and blocklist from file
  export-config file   - Export full config (prefs, envs, aliases)
  import-config file   - Import full config
  block id             - Block a Flatpak ID from wrapper generation
  unblock id           - Unblock a Flatpak ID
  list-blocked         - List blocked Flatpak IDs
  install app [remote] - Install Flatpak app and create wrapper
  launch name          - Launch wrapper by name
  info name            - Show detailed info for a wrapper
  manifest name [remote|local] - Show Flatpak manifest for a wrapper (default: remote)
  regenerate           - Regenerate all wrappers
  files                - List all generated files
  uninstall            - Remove all generated files and config

Interactive Behavior:
  Wrappers automatically detect execution context:
  • Interactive (terminal): Full wrapper functionality with prompts
  • Non-interactive (.desktop, scripts): Bypass wrapper, run system command
  • Force interactive: FPWRAPPER_FORCE=interactive or --fpwrapper-force-interactive

Examples:
  FPWRAPPER_FORCE=interactive firefox --fpwrapper-info
  firefox --fpwrapper-force-interactive --help
EOF
    exit 1
}

list_wrappers() {
    echo "Current wrappers in $BIN_DIR:"
    for script in "$BIN_DIR"/*; do
        if is_wrapper_file "$script" && [ -x "$script" ]; then
            local name id
            name=$(basename "$script")
            id=$(get_wrapper_id "$script")
            echo "  $name -> ${id:-unknown}"
        fi
    done
}

search_wrappers() {
    local keyword="$1"
    local found=0
    
    if [ -z "$keyword" ]; then
        echo "Usage: fplaunch-manage search <keyword>"
        return 1
    fi
    
    # Convert keyword to lowercase for case-insensitive search
    local keyword_lower
    keyword_lower=$(echo "$keyword" | tr '[:upper:]' '[:lower:]')
    
    echo "Searching for '$keyword'..."
    echo
    
    for script in "$BIN_DIR"/*; do
        if is_wrapper_file "$script" && [ -x "$script" ]; then
            local name id name_lower id_lower
            name=$(basename "$script")
            id=$(get_wrapper_id "$script")
            name_lower=$(echo "$name" | tr '[:upper:]' '[:lower:]')
            id_lower=$(echo "$id" | tr '[:upper:]' '[:lower:]')
            
            # Get description from flatpak if available
            local desc="" desc_lower
            if [ -n "$id" ]; then
                desc=$(flatpak info "$id" 2>/dev/null | grep -i "^Description:" | cut -d: -f2- | sed 's/^[[:space:]]*//')
                [ -z "$desc" ] && desc=$(flatpak info "$id" 2>/dev/null | grep -i "^Summary:" | cut -d: -f2- | sed 's/^[[:space:]]*//')
            fi
            desc_lower=$(echo "$desc" | tr '[:upper:]' '[:lower:]')
            
            # Check if keyword matches name, ID, or description
            if [[ "$name_lower" == *"$keyword_lower"* ]] || \
               [[ "$id_lower" == *"$keyword_lower"* ]] || \
               [[ "$desc_lower" == *"$keyword_lower"* ]]; then
                found=$((found + 1))
                echo "[$found] $name"
                echo "    ID: $id"
                if [ -n "$desc" ]; then
                    echo "    Description: $desc"
                fi
                
                # Show if it has preferences, env vars, or scripts
                local extras=""
                [ -f "$CONFIG_DIR/$name.pref" ] && extras="${extras}preference "
                [ -f "$CONFIG_DIR/$name.env" ] && extras="${extras}env-vars "
                [ -f "$CONFIG_DIR/scripts/$name/pre-launch.sh" ] && extras="${extras}pre-script "
                [ -f "$CONFIG_DIR/scripts/$name/post-run.sh" ] && extras="${extras}post-script "
                if [ -n "$extras" ]; then
                    echo "    Configured: $extras"
                fi
                
                # Show aliases if any
                if [ -f "$CONFIG_DIR/aliases" ]; then
                    local aliases
                    aliases=$(grep " $name$" "$CONFIG_DIR/aliases" 2>/dev/null | cut -d' ' -f1 | tr '\n' ' ')
                    if [ -n "$aliases" ]; then
                        echo "    Aliases: $aliases"
                    fi
                fi
                echo
            fi
        fi
    done
    
    if [ $found -eq 0 ]; then
        echo "No wrappers found matching '$keyword'"
        return 1
    else
        echo "Found $found wrapper(s) matching '$keyword'"
    fi
}

list_files() {
    echo "Generated files:"
    # Wrappers
    for script in "$BIN_DIR"/*; do
        if [ -f "$script" ] && grep -q "Generated by fplaunchwrapper" "$script" 2>/dev/null; then
            echo "  Wrapper: $script"
        elif [ "$(basename "$script")" = "fplaunch-manage" ]; then
            echo "  Manager: $script"
        fi
    done
    # Lib scripts
    if [ -d "$BIN_DIR/lib" ]; then
        for lib in "$BIN_DIR/lib"/*.sh; do
            if [ -f "$lib" ]; then
                echo "  Library: $lib"
            fi
        done
    fi
    # Config files
    if [ -d "$CONFIG_DIR" ]; then
        find "$CONFIG_DIR" -type f | while read f; do
            echo "  Config: $f"
        done
    fi
    # Systemd units
    UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    for unit in flatpak-wrappers.service flatpak-wrappers.path flatpak-wrappers.timer; do
        if [ -f "$UNIT_DIR/$unit" ]; then
            echo "  Systemd unit: $UNIT_DIR/$unit"
        fi
    done
}

uninstall_all() {
    if ! confirm_action "Uninstall Flatpak Launch Wrappers? This will remove all wrappers, preferences, and config."; then
        echo "Uninstallation cancelled."
        return 1
    fi

    echo "Uninstalling Flatpak Launch Wrappers..."
    
    # Stop and disable systemd units
    cleanup_systemd_units
    
    # Remove cron job if exists
    WRAPPER_SCRIPT="$SCRIPT_DIR/fplaunch-generate"
    manage_cron_entry remove "$WRAPPER_SCRIPT"
    
    # Remove wrappers and manager
    for script in "$BIN_DIR"/*; do
        if [ -f "$script" ] && grep -q "Generated by fplaunchwrapper" "$script" 2>/dev/null; then
            rm "$script"
        elif [ -L "$script" ] && [ -f "$script" ] && grep -q "Generated by fplaunchwrapper" "$script" 2>/dev/null; then
            rm "$script"
        elif [ "$script" = "$BIN_DIR/fplaunch-manage" ]; then
            rm "$script"
        fi
    done
    
    # Remove lib directory
    if [ -n "$BIN_DIR" ]; then
        rm -rf "${BIN_DIR:?}/lib"
    fi
    
    # Remove config directory
    if [ -n "$CONFIG_DIR" ]; then
        rm -rf "${CONFIG_DIR:?}"
    fi
    
    echo "Uninstallation complete. All wrappers, preferences, and config removed."
}

remove_wrapper() {
    name="$1"
    script_path="$BIN_DIR/$name"
    if [ -f "$script_path" ]; then
        if confirm_action "Are you sure you want to remove wrapper '$name'?"; then
            rm "$script_path"
            pref_file="$CONFIG_DIR/$name.pref"
            [ -f "$pref_file" ] && rm "$pref_file"
            # Remove aliases pointing to this wrapper
            sed -i "/^$name /d" "$CONFIG_DIR/aliases" 2>/dev/null
            for alias in "$BIN_DIR"/*; do
                if [ -L "$alias" ] && [ "$(readlink "$alias" 2>/dev/null)" = "$script_path" ]; then
                    rm "$alias"
                fi
            done
            echo "Removed wrapper, preference, and aliases for $name"
        else
            echo "Removal cancelled."
        fi
    else
        echo "Wrapper $name not found"
    fi
}







block_id() {
    id="$1"
    if ! grep -q "^$id$" "$BLOCKLIST" 2>/dev/null; then
        echo "$id" >> "$BLOCKLIST"
        echo "Blocked $id"
    else
        echo "$id is already blocked"
    fi
}

unblock_id() {
    id="$1"
    if grep -q "^$id$" "$BLOCKLIST" 2>/dev/null; then
        sed -i "/^$id$/d" "$BLOCKLIST"
        echo "Unblocked $id"
    else
        echo "$id is not blocked"
    fi
}

list_blocked() {
    if [ -f "$BLOCKLIST" ] && [ -s "$BLOCKLIST" ]; then
        echo "Blocked Flatpak IDs:"
        cat "$BLOCKLIST"
    else
        echo "No blocked Flatpak IDs"
    fi
}

install_app() {
    app="$1"
    remote="${2:-flathub}"
    echo "Installing $app from $remote..."
    if flatpak install "$remote" "$app" -y; then
        echo "Regenerating wrappers..."
        "$SCRIPT_DIR/generate_flatpak_wrappers.sh" "$BIN_DIR"
        id=$(flatpak info "$app" 2>/dev/null | grep "^ID:" | awk '{print $2}')
        if [ -n "$id" ]; then
            name=$(echo "$id" | awk -F. '{print tolower($NF)}')
            if [ -f "$BIN_DIR/$name" ]; then
                echo "Installed and created wrapper: $name"
            fi
        fi
    else
        echo "Installation failed."
    fi
}






show_manifest() {
    local name="$1"
    local type="${2:-remote}"
    local id
    if [ ! -f "$BIN_DIR/$name" ]; then
        echo "Wrapper '$name' not found" >&2
        return 1
    fi
    id=$(grep '^ID=' "$BIN_DIR/$name" | cut -d'"' -f2)
    if [ -z "$id" ]; then
        echo "Could not find Flatpak ID for '$name'" >&2
        return 1
    fi
    case "$type" in
        remote)
            flatpak remote-info --show-metadata "$(flatpak info "$id" | grep Origin | awk '{print $2}')" "$id" 2>/dev/null || echo "Remote manifest not available" >&2
            ;;
        local)
            flatpak info --show-metadata "$id" 2>/dev/null || echo "Local manifest not available" >&2
            ;;
        *)
            echo "Invalid type: $type. Use 'remote' or 'local'." >&2
            return 1
            ;;
    esac
}

show_info() {
    local name="$1"
    local id
    if [ ! -f "$BIN_DIR/$name" ]; then
        echo "Wrapper '$name' not found"
        return 1
    fi
    id=$(grep '^ID=' "$BIN_DIR/$name" | cut -d'"' -f2)
    if [ -z "$id" ]; then
        echo "Could not find Flatpak ID for '$name'"
        return 1
    fi
    echo "Wrapper: $name"
    echo "Flatpak ID: $id"
    echo
    echo "Flatpak Info:"
    flatpak info "$id" 2>/dev/null || echo "Failed to get Flatpak info"
    echo
    echo "Installed Metadata:"
    flatpak info --show-metadata "$id" 2>/dev/null || echo "Installed metadata not available"
    echo
    echo "Remote Manifest:"
    flatpak remote-info --show-metadata "$(flatpak info "$id" | grep Origin | awk '{print $2}')" "$id" 2>/dev/null || echo "Remote manifest not available"
    echo
    echo "Flathub Page: https://flathub.org/apps/$id"
}

regenerate() {
    echo "Regenerating all wrappers..."
    if [ -f "$SCRIPT_DIR/fplaunch-generate" ]; then
        "$SCRIPT_DIR/fplaunch-generate" "$BIN_DIR"
    else
        echo "Error: fplaunch-generate not found"
        return 1
    fi
}

# Main command dispatcher
if [ $# -eq 0 ]; then
    usage
else
    command="$1"
    shift

    case $command in
        help)
            usage
            ;;
        list)
            list_wrappers
            ;;
        search)
            if [ $# -ne 1 ]; then 
                echo "Usage: fplaunch-manage search <keyword>"
                exit 1
            fi
            search_wrappers "$1"
            ;;
        remove)
            if [ $# -ne 1 ]; then usage; fi
            remove_wrapper "$1"
            ;;
        remove-pref)
            if [ $# -ne 1 ]; then usage; fi
            remove_pref "$1"
            ;;
        set-pref)
            if [ $# -ne 2 ]; then usage; fi
            set_pref "$1" "$2"
            ;;
        set-env)
            if [ $# -ne 3 ]; then usage; fi
            set_env "$1" "$2" "$3"
            ;;
        remove-env)
            if [ $# -ne 2 ]; then usage; fi
            remove_env "$1" "$2"
            ;;
        list-env)
            if [ $# -ne 1 ]; then usage; fi
            list_env "$1"
            ;;
        set-pref-all)
            if [ $# -ne 1 ]; then usage; fi
            set_pref_all "$1"
            ;;
        set-script)
            if [ $# -ne 2 ]; then usage; fi
            set_script "$1" "$2"
            ;;
        set-post-script)
            if [ $# -ne 2 ]; then usage; fi
            set_post_script "$1" "$2"
            ;;
        remove-script)
            if [ $# -ne 1 ]; then usage; fi
            remove_script "$1"
            ;;
        remove-post-script)
            if [ $# -ne 1 ]; then usage; fi
            remove_post_script "$1"
            ;;
        set-alias)
            if [ $# -ne 2 ]; then usage; fi
            set_alias "$1" "$2"
            ;;
        remove-alias)
            if [ $# -ne 1 ]; then usage; fi
            remove_alias "$1"
            ;;
        export-prefs)
            if [ $# -ne 1 ]; then usage; fi
            export_prefs "$1"
            ;;
        import-prefs)
            if [ $# -ne 1 ]; then usage; fi
            import_prefs "$1"
            ;;
        export-config)
            if [ $# -ne 1 ]; then usage; fi
            export_config "$1"
            ;;
        import-config)
            if [ $# -ne 1 ]; then usage; fi
            import_config "$1"
            ;;
        block)
            if [ $# -ne 1 ]; then usage; fi
            block_id "$1"
            ;;
        unblock)
            if [ $# -ne 1 ]; then usage; fi
            unblock_id "$1"
            ;;
        list-blocked)
            list_blocked
            ;;
        install)
            if [ $# -lt 1 ]; then usage; fi
            install_app "$1" "$2"
            ;;
        launch)
            if [ $# -ne 1 ]; then usage; fi
            launch_wrapper "$1"
            ;;
        info)
            # Check for --help
            if [ "$1" = "--help" ]; then
                echo "fplaunch-manage info <name>"
                echo "Show detailed info for a Flatpak wrapper, including Flatpak info, installed metadata, remote manifest, and Flathub link."
                exit 0
            fi
            if [ $# -ne 1 ]; then usage; fi
            show_info "$1"
            ;;
        manifest)
            # Check for --help
            if [ "$1" = "--help" ]; then
                echo "fplaunch-manage manifest <name> [remote|local]"
                echo "Show Flatpak manifest for a wrapper. Default: remote. Use 'local' for installed version."
                exit 0
            fi
            if [ $# -lt 1 ] || [ $# -gt 2 ]; then usage; fi
            show_manifest "$1" "${2:-remote}"
            ;;
        regenerate)
            regenerate
            ;;
        files)
            list_files
            ;;
        uninstall)
            uninstall_all
            ;;
        *)
            echo "Unknown command: $command"
            usage
            ;;
    esac
fi
