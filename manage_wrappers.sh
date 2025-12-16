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
else
    echo "ERROR: Cannot find common.sh library" >&2
    echo "Searched in:" >&2
    echo "  - $SCRIPT_DIR/lib/common.sh" >&2
    echo "  - ${SCRIPT_DIR%/bin}/lib/common.sh" >&2
    exit 1
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
  discover             - Discover advanced features and examples
  status               - Show configuration overview and status
  doctor               - Run diagnostics to troubleshoot issues
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

discover_features() {
    echo "🚀 fplaunchwrapper Features You Might Like"
    echo ""
    echo "📝 Pre-launch Scripts: Run commands before apps start"
    echo "   Example: fplaunch-manage set-script firefox ~/scripts/firefox-setup.sh"
    echo "   Use case: Set up VPN, mount drives, or configure environment"
    echo ""
    echo "🧹 Post-run Scripts: Clean up after apps exit"
    echo "   Example: fplaunch-manage set-post-script firefox ~/scripts/firefox-cleanup.sh"
    echo "   Use case: Disconnect VPN, backup data, or clean temp files"
    echo ""
    echo "🔧 Environment Variables: Set per-app environment"
    echo "   Example: fplaunch-manage set-env firefox MOZ_ENABLE_WAYLAND 1"
    echo "   Use case: Force Wayland, set themes, or configure paths"
    echo ""
    echo "🎯 Smart Preferences: Choose system vs Flatpak automatically"
    echo "   Example: fplaunch-manage set-pref chrome system"
    echo "   Use case: Prefer system Chrome when available, fallback to Flatpak"
    echo ""
    echo "🔍 Sandbox Management: Control Flatpak permissions"
    echo "   Example: firefox --fpwrapper-edit-sandbox"
    echo "   Use case: Grant filesystem access, enable devices, or network"
    echo ""
    echo "⚡ Quick Actions: Direct wrapper commands"
    echo "   Example: firefox --fpwrapper-info"
    echo "   Use case: Get info, edit sandbox, or reset permissions"
    echo ""
    echo "📚 Learn more:"
    echo "   examples/script-usage-guide.md    # Script examples"
    echo "   examples/pre-launch-examples.md    # Pre-launch ideas"
    echo "   examples/post-run-examples.md     # Post-run ideas"
    echo "   man fplaunchwrapper               # Full documentation"
    echo ""
    echo "💡 Try these commands to get started:"
    echo "   fplaunch-manage list              # See your wrappers"
    echo "   fplaunch-manage search browser    # Find browser apps"
    echo "   firefox --fpwrapper-help          # See all options"
}

show_status() {
    echo "📊 fplaunchwrapper Status"
    echo ""
    
    # Installation info
    echo "📁 Installation:"
    echo "   Bin directory: $BIN_DIR"
    echo "   Config directory: $CONFIG_DIR"
    if [ -f "$CONFIG_DIR/bin_dir" ]; then
        saved_bin_dir=$(cat "$CONFIG_DIR/bin_dir")
        if [ "$saved_bin_dir" = "$BIN_DIR" ]; then
            echo "   ✅ Configuration consistent"
        else
            echo "   ⚠️  Configuration mismatch (saved: $saved_bin_dir)"
        fi
    else
        echo "   ⚠️  No saved configuration"
    fi
    echo ""
    
    # Wrapper statistics
    local wrapper_count=0
    local blocked_count=0
    local alias_count=0
    local script_count=0
    local env_count=0
    
    for script in "$BIN_DIR"/*; do
        if is_wrapper_file "$script" && [ -x "$script" ]; then
            wrapper_count=$((wrapper_count + 1))
        fi
    done
    
    if [ -f "$CONFIG_DIR/blocklist" ]; then
        blocked_count=$(wc -l < "$CONFIG_DIR/blocklist" 2>/dev/null || echo 0)
    fi
    
    if [ -f "$CONFIG_DIR/aliases" ]; then
        alias_count=$(wc -l < "$CONFIG_DIR/aliases" 2>/dev/null || echo 0)
    fi
    
    if [ -d "$CONFIG_DIR/scripts" ]; then
        script_count=$(find "$CONFIG_DIR/scripts" -name "*.sh" 2>/dev/null | wc -l)
    fi
    
    env_count=$(find "$CONFIG_DIR" -name "*.env" 2>/dev/null | wc -l)
    
    echo "📦 Statistics:"
    echo "   Wrappers: $wrapper_count generated"
    echo "   Blocked: $blocked_count applications"
    echo "   Aliases: $alias_count configured"
    echo "   Scripts: $script_count pre/post scripts"
    echo "   Environment files: $env_count"
    echo ""
    
    # Auto-update status
    local systemd_status="disabled"
    local cron_status="disabled"
    
    UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    if [ -f "$UNIT_DIR/flatpak-wrappers.service" ]; then
        if systemctl --user is-enabled flatpak-wrappers.service >/dev/null 2>&1; then
            systemd_status="enabled"
        fi
    fi
    
    if crontab -l 2>/dev/null | grep -q "fplaunch-generate"; then
        cron_status="enabled"
    fi
    
    echo "🔄 Auto-updates:"
    echo "   Systemd: $systemd_status"
    echo "   Cron: $cron_status"
    echo ""
    
    # Recent activity (if we can determine it)
    echo "🔧 Recent activity:"
    if [ -n "$BIN_DIR" ] && [ -d "$BIN_DIR" ]; then
        local newest_wrapper
        newest_wrapper=$(find "$BIN_DIR" -maxdepth 1 -type f -name "*" -executable -exec test -f {} \; -print0 2>/dev/null | xargs -0 ls -t 2>/dev/null | head -1)
        if [ -n "$newest_wrapper" ]; then
            echo "   Latest wrapper: $(basename "$newest_wrapper")"
        fi
    fi
    
    # PATH check
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo "   ⚠️  $BIN_DIR not in PATH"
    else
        echo "   ✅ $BIN_DIR in PATH"
    fi
}

run_doctor() {
    echo "🔍 Running fplaunchwrapper diagnostics..."
    echo ""
    
    local issues=0
    
    # Check installation
    echo "📁 Checking installation..."
    if [ ! -d "$BIN_DIR" ]; then
        echo "   ❌ BIN_DIR not found: $BIN_DIR"
        issues=$((issues + 1))
    else
        echo "   ✅ BIN_DIR exists: $BIN_DIR"
    fi
    
    if [ ! -d "$CONFIG_DIR" ]; then
        echo "   ❌ CONFIG_DIR not found: $CONFIG_DIR"
        issues=$((issues + 1))
    else
        echo "   ✅ CONFIG_DIR exists: $CONFIG_DIR"
    fi
    
    # Check permissions
    echo ""
    echo "🔐 Checking permissions..."
    if [ ! -w "$BIN_DIR" ]; then
        echo "   ❌ Cannot write to BIN_DIR: $BIN_DIR"
        issues=$((issues + 1))
    else
        echo "   ✅ BIN_DIR writable"
    fi
    
    if [ ! -w "$CONFIG_DIR" ]; then
        echo "   ❌ Cannot write to CONFIG_DIR: $CONFIG_DIR"
        issues=$((issues + 1))
    else
        echo "   ✅ CONFIG_DIR writable"
    fi
    
    # Check PATH
    echo ""
    echo "🛤️  Checking PATH..."
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo "   ⚠️  $BIN_DIR not in PATH"
        echo "   💡 Add to PATH: export PATH=\"$BIN_DIR:\$PATH\""
        issues=$((issues + 1))
    else
        echo "   ✅ $BIN_DIR in PATH"
    fi
    
    # Check dependencies
    echo ""
    echo "📦 Checking dependencies..."
    if ! command -v flatpak >/dev/null 2>&1; then
        echo "   ❌ Flatpak not found"
        echo "   💡 Install: sudo apt install flatpak (Ubuntu/Debian)"
        issues=$((issues + 1))
    else
        echo "   ✅ Flatpak found: $(flatpak --version | head -1)"
    fi
    
    # Check Flatpak remotes
    if flatpak remotes >/dev/null 2>&1; then
        if flatpak remotes | grep -q "flathub"; then
            echo "   ✅ Flathub remote configured"
        else
            echo "   ⚠️  Flathub remote not found"
            echo "   💡 Add: flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo"
            issues=$((issues + 1))
        fi
    fi
    
    # Check wrapper functionality
    echo ""
    echo "🧪 Testing wrapper functionality..."
    local test_wrapper=""
    for script in "$BIN_DIR"/*; do
        if is_wrapper_file "$script" && [ -x "$script" ]; then
            test_wrapper="$script"
            break
        fi
    done
    
    if [ -n "$test_wrapper" ]; then
        local wrapper_name
        wrapper_name=$(basename "$test_wrapper")
        if "$test_wrapper" --fpwrapper-info >/dev/null 2>&1; then
            echo "   ✅ Wrapper test passed: $wrapper_name"
        else
            echo "   ❌ Wrapper test failed: $wrapper_name"
            issues=$((issues + 1))
        fi
    else
        echo "   ⚠️  No wrappers found to test"
        echo "   💡 Run: fplaunch-generate $BIN_DIR"
    fi
    
    # Check auto-updates
    echo ""
    echo "🔄 Checking auto-updates..."
    local update_found=false
    
    UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    if [ -f "$UNIT_DIR/flatpak-wrappers.service" ]; then
        if systemctl --user is-enabled flatpak-wrappers.service >/dev/null 2>&1; then
            echo "   ✅ Systemd auto-updates enabled"
            update_found=true
        else
            echo "   ⚠️  Systemd service exists but not enabled"
        fi
    fi
    
    if crontab -l 2>/dev/null | grep -q "fplaunch-generate"; then
        echo "   ✅ Cron auto-updates enabled"
        update_found=true
    fi
    
    if [ "$update_found" = false ]; then
        echo "   ⚠️  No auto-updates configured"
        echo "   💡 Enable: fplaunch-setup-systemd"
    fi
    
    # Summary
    echo ""
    if [ $issues -eq 0 ]; then
        echo "🎉 All checks passed! fplaunchwrapper is properly configured."
    else
        echo "⚠️  Found $issues issue(s) that may affect functionality."
        echo ""
        echo "💡 Common fixes:"
        echo "   - Add to PATH: export PATH=\"$BIN_DIR:\$PATH\""
        echo "   - Install Flatpak: sudo apt install flatpak"
        echo "   - Add Flathub: flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo"
        echo "   - Generate wrappers: fplaunch-generate $BIN_DIR"
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
        discover)
            discover_features
            ;;
        status)
            show_status
            ;;
        doctor)
            run_doctor
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
