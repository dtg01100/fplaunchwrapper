#!/usr/bin/env bash
set_env() {
    name="$1"
    var="$2"
    value="$3"
    env_file="$CONFIG_DIR/$name.env"
    if [ ! -f "$BIN_DIR/$name" ]; then
        echo "Wrapper $name not found"
        return 1
    fi
    read -r -p "Set $var=$value for '$name'? (y/n): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        if grep -q "^export $var=" "$env_file" 2>/dev/null; then
            # Update existing variable
            sed -i "s|^export $var=.*|export $var=\"$value\"|" "$env_file"
            echo "Updated $var for $name"
        else
            # Add new variable
            echo "export $var=\"$value\"" >> "$env_file"
            echo "Set $var for $name"
        fi
    else
        echo "Cancelled."
    fi
}

remove_env() {
    name="$1"
    var="$2"
    env_file="$CONFIG_DIR/$name.env"
    if [ -f "$env_file" ]; then
        sed -i "/export $var=/d" "$env_file"
        echo "Removed $var for $name"
    else
        echo "No env file for $name"
    fi
}

list_env() {
    name="$1"
    env_file="$CONFIG_DIR/$name.env"
    if [ -f "$env_file" ]; then
        echo "Environment variables for $name:"
        cat "$env_file"
    else
        echo "No environment variables set for $name"
    fi
}