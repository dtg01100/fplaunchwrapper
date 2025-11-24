#!/bin/bash

CONFIG_DIR="$HOME/.config/flatpak-wrappers"
BIN_DIR_FILE="$CONFIG_DIR/bin_dir"
BIN_DIR="$HOME/bin"  # default
if [ -f "$BIN_DIR_FILE" ]; then
    BIN_DIR=$(cat "$BIN_DIR_FILE")
fi
BLOCKLIST="$CONFIG_DIR/blocklist"

mkdir -p "$CONFIG_DIR"

usage() {
    echo "Usage: $0 <command> [args]"
    echo "Commands:"
    echo "  list                 - List current wrappers"
    echo "  remove <name>        - Remove a specific wrapper"
    echo "  remove-pref <name>   - Remove preference for a wrapper"
    echo "  set-pref <name> <system|flatpak> - Set preference for a wrapper"
    echo "  set-alias <name> <alias> - Set an alias for a wrapper"
    echo "  remove-alias <alias> - Remove an alias"
    echo "  export-prefs <file>  - Export preferences and blocklist to file"
    echo "  import-prefs <file>  - Import preferences and blocklist from file"
    echo "  block <id>           - Block a Flatpak ID from getting a wrapper"
    echo "  unblock <id>         - Unblock a Flatpak ID"
    echo "  list-blocked         - List blocked IDs"
    echo "  regenerate           - Regenerate all wrappers"
    exit 1
}

list_wrappers() {
    echo "Current wrappers in $BIN_DIR:"
    for script in "$BIN_DIR"/*; do
        if [ -f "$script" ] && [ -x "$script" ]; then
            name=$(basename "$script")
            id=$(grep "flatpak run" "$script" | awk '{print $3}' || echo "unknown")
            echo "  $name -> $id"
        fi
    done
}

remove_wrapper() {
    name="$1"
    script_path="$BIN_DIR/$name"
    if [ -f "$script_path" ]; then
        rm "$script_path"
        pref_file="$CONFIG_DIR/$name.pref"
        [ -f "$pref_file" ] && rm "$pref_file"
        echo "Removed wrapper and preference for $name"
    else
        echo "Wrapper $name not found"
    fi
}

remove_pref() {
    name="$1"
    pref_file="$CONFIG_DIR/$name.pref"
    if [ -f "$pref_file" ]; then
        rm "$pref_file"
        echo "Removed preference for $name"
    else
        echo "No preference found for $name"
    fi
}

set_pref() {
    name="$1"
    choice="$2"
    if [ "$choice" != "system" ] && [ "$choice" != "flatpak" ]; then
        echo "Invalid choice: use 'system' or 'flatpak'"
        return
    fi
    pref_file="$CONFIG_DIR/$name.pref"
    echo "$choice" > "$pref_file"
    echo "Set preference for $name to $choice"
}

set_alias() {
    name="$1"
    alias="$2"
    script_path="$BIN_DIR/$name"
    alias_path="$BIN_DIR/$alias"
    if [ ! -f "$script_path" ]; then
        echo "Wrapper $name not found"
        return
    fi
    if [ -e "$alias_path" ]; then
        echo "Alias $alias already exists"
        return
    fi
    ln -s "$script_path" "$alias_path"
    echo "$name $alias" >> "$CONFIG_DIR/aliases"
    echo "Set alias $alias for $name"
}

remove_alias() {
    alias="$1"
    alias_path="$BIN_DIR/$alias"
    if [ -L "$alias_path" ]; then
        rm "$alias_path"
        sed -i "/ $alias$/d" "$CONFIG_DIR/aliases" 2>/dev/null
        echo "Removed alias $alias"
    else
        echo "Alias $alias not found"
    fi
}

export_prefs() {
    file="$1"
    tar -czf "$file" -C "$CONFIG_DIR" . 2>/dev/null
    echo "Exported preferences to $file"
}

import_prefs() {
    file="$1"
    if [ -f "$file" ]; then
        tar -xzf "$file" -C "$CONFIG_DIR" 2>/dev/null
        echo "Imported preferences from $file"
    else
        echo "File $file not found"
    fi
}

block_id() {
    id="$1"
    if ! grep -q "^$id$" "$BLOCKLIST" 2>/dev/null; then
        echo "$id" >> "$BLOCKLIST"
        echo "Blocked $id"
    else
        echo "$id already blocked"
    fi
}

unblock_id() {
    id="$1"
    if grep -q "^$id$" "$BLOCKLIST" 2>/dev/null; then
        sed -i "/^$id$/d" "$BLOCKLIST"
        echo "Unblocked $id"
    else
        echo "$id not blocked"
    fi
}

list_blocked() {
    echo "Blocked Flatpak IDs:"
    if [ -f "$BLOCKLIST" ]; then
        cat "$BLOCKLIST"
    else
        echo "None"
    fi
}

regenerate() {
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    wrapper_script="$script_dir/generate_flatpak_wrappers.sh"
    if [ -f "$wrapper_script" ]; then
        bash "$wrapper_script"
    else
        echo "Wrapper script not found"
    fi
}

select_wrapper() {
    echo "Available wrappers:"
    wrappers=()
    i=1
    for script in "$BIN_DIR"/*; do
        if [ -f "$script" ] && [ -x "$script" ]; then
            name=$(basename "$script")
            id=$(grep "flatpak run" "$script" | awk '{print $3}' || echo "unknown")
            echo "$i. $name -> $id"
            wrappers[$i]="$name"
            ((i++))
        fi
    done
    if [ ${#wrappers[@]} -eq 0 ]; then
        echo "No wrappers found"
        return 1
    fi
    read -p "Choose a wrapper (1-$((i-1))): " choice
    if [[ $choice =~ ^[0-9]+$ ]] && [ $choice -ge 1 ] && [ $choice -lt $i ]; then
        selected="${wrappers[$choice]}"
        echo "Selected: $selected"
        return 0
    else
        echo "Invalid choice"
        return 1
    fi
}

if [ $# -eq 0 ]; then
    # Interactive menu
    while true; do
        echo
        echo "Flatpak Wrappers Management Menu"
        echo "1. List wrappers"
        echo "2. Remove wrapper"
        echo "3. Remove preference"
        echo "4. Set preference"
        echo "5. Set alias"
        echo "6. Remove alias"
        echo "7. Export preferences"
        echo "8. Import preferences"
        echo "9. Block ID"
        echo "10. Unblock ID"
        echo "11. List blocked IDs"
        echo "12. Regenerate wrappers"
        echo "13. Exit"
        read -p "Choose an option (1-13): " option
        case $option in
            1)
                list_wrappers
                ;;
            2)
                if select_wrapper; then
                    remove_wrapper "$selected"
                fi
                ;;
            3)
                if select_wrapper; then
                    remove_pref "$selected"
                fi
                ;;
            4)
                if select_wrapper; then
                    read -p "Enter preference (system/flatpak): " pref
                    set_pref "$selected" "$pref"
                fi
                ;;
            5)
                if select_wrapper; then
                    read -p "Enter alias name: " alias
                    set_alias "$selected" "$alias"
                fi
                ;;
            6)
                read -p "Enter alias to remove: " alias
                remove_alias "$alias"
                ;;
            7)
                read -p "Enter export file path: " file
                export_prefs "$file"
                ;;
            8)
                read -p "Enter import file path: " file
                import_prefs "$file"
                ;;
            9)
                read -p "Enter Flatpak ID to block: " id
                block_id "$id"
                ;;
            10)
                read -p "Enter Flatpak ID to unblock: " id
                unblock_id "$id"
                ;;
            11)
                list_blocked
                ;;
            12)
                regenerate
                ;;
            13)
                exit 0
                ;;
            *)
                echo "Invalid option"
                ;;
        esac
    done
else
    command="$1"
    shift

    case "$command" in
        list)
            list_wrappers
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
        regenerate)
            regenerate
            ;;
        *)
            usage
            ;;
    esac
fi