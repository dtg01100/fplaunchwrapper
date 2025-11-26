#!/usr/bin/env bash
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

remove_wrapper() {
    name="$1"
    script_path="$BIN_DIR/$name"
    if [ -f "$script_path" ]; then
        read -r -p "Are you sure you want to remove wrapper '$name'? (y/n): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
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

regenerate() {
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    wrapper_script="$script_dir/generate_flatpak_wrappers.sh"
    if [ -f "$wrapper_script" ]; then
        bash "$wrapper_script" "$BIN_DIR"
    else
        echo "Wrapper script not found"
    fi
}

block_id() {
    id="$1"
    if ! grep -q "^$id$" "$BLOCKLIST" 2>/dev/null; then
        read -r -p "Block Flatpak ID '$id'? Wrappers won't be created for it. (y/n): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo "$id" >> "$BLOCKLIST"
            echo "Blocked $id"
        else
            echo "Blocking cancelled."
        fi
    else
        echo "$id already blocked"
    fi
}

unblock_id() {
    id="$1"
    if grep -q "^$id$" "$BLOCKLIST" 2>/dev/null; then
        read -r -p "Unblock Flatpak ID '$id'? (y/n): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            sed -i "/^$id$/d" "$BLOCKLIST"
            echo "Unblocked $id"
        else
            echo "Unblocking cancelled."
        fi
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

select_wrapper() {
    echo "Available wrappers:"
    wrappers=()
    i=1
    for script in "$BIN_DIR"/*; do
        if is_wrapper_file "$script" && [ -x "$script" ]; then
            local name id
            name=$(basename "$script")
            id=$(get_wrapper_id "$script")
            echo "$i. $name -> ${id:-unknown}"
            wrappers[$i]="$name"
            ((i++))
        fi
    done
    if [ ${#wrappers[@]} -eq 0 ]; then
        echo "No wrappers found"
    fi
    read -r -p "Choose a wrapper (1-$((i-1))): " choice
    if [[ $choice =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -lt "$i" ]; then
        selected="${wrappers[$choice]}"
        echo "Selected: $selected"
    else
        echo "Invalid choice"
    fi
}