#!/usr/bin/env bash
set_alias() {
    name="$1"
    alias="$2"
    script_path="$BIN_DIR/$name"
    alias_path="$BIN_DIR/$alias"
    if [ ! -f "$script_path" ]; then
        echo "Wrapper $name not found"
        return 1
    fi
    if [ -e "$alias_path" ]; then
        echo "Alias $alias already exists"
        return 1
    fi
    if grep -q " $alias$" "$CONFIG_DIR/aliases" 2>/dev/null; then
        echo "Alias $alias already exists in config"
        return 1
    fi
    read -r -p "Create alias '$alias' for '$name'? (y/n): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        ln -s "$script_path" "$alias_path"
        echo "$name $alias" >> "$CONFIG_DIR/aliases"
        echo "Set alias $alias for $name"
    else
        echo "Alias creation cancelled."
    fi
}

remove_alias() {
    alias="$1"
    alias_path="$BIN_DIR/$alias"
    if [ -L "$alias_path" ]; then
        read -r -p "Remove alias '$alias'? (y/n): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            rm "$alias_path"
            sed -i "/ $alias$/d" "$CONFIG_DIR/aliases" 2>/dev/null
            echo "Removed alias $alias"
        else
            echo "Removal cancelled."
        fi
    else
        echo "Alias $alias not found"
    fi
}