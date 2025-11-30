#!/usr/bin/env bash

# Common utility functions for fplaunchwrapper

# Safety check - never run as root
if [ "$(id -u)" = "0" ]; then
    echo "ERROR: fplaunchwrapper should never be run as root for safety"
    echo "This tool is designed for user-level wrapper management only"
    exit 1
fi

# Get systemd user unit directory
get_systemd_unit_dir() {
    echo "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
}

# Create config directory if it doesn't exist
ensure_config_dir() {
    CONFIG_DIR="${CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/flatpak-wrappers}"
    # Create parent directories if they don't exist, with better error handling
    local parent_dir
    parent_dir="$(dirname "$CONFIG_DIR")"
    
    # Try to create parent directory first
    if [ ! -d "$parent_dir" ]; then
        if ! mkdir -p "$parent_dir" 2>/dev/null; then
            echo "Error: Cannot create config directory parent: $parent_dir" >&2
            echo "Please check permissions and disk space." >&2
            echo "" >&2
            echo "Alternative: You can set a custom config directory by setting:" >&2
            echo "  export XDG_CONFIG_HOME=/path/to/your/config" >&2
            echo "  export CONFIG_DIR=/path/to/your/flatpak-wrappers" >&2
            return 1
        fi
    fi
    
    # Try to create config directory
    if ! mkdir -p "$CONFIG_DIR" 2>/dev/null; then
        echo "Error: Cannot create config directory: $CONFIG_DIR" >&2
        echo "Please check permissions and disk space." >&2
        echo "" >&2
        echo "Alternative: You can set a custom config directory by setting:" >&2
        echo "  export XDG_CONFIG_HOME=/path/to/your/config" >&2
        echo "  export CONFIG_DIR=/path/to/your/flatpak-wrappers" >&2
        return 1
    fi
    
    return 0
}

# Initialize common paths used across scripts
init_paths() {
    CONFIG_DIR="${CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/flatpak-wrappers}"
    # Allow BIN_DIR to be set explicitly, otherwise try to read from config file
    if [ -z "${BIN_DIR:-}" ]; then
        if [ -f "$CONFIG_DIR/bin_dir" ]; then
            BIN_DIR=$(cat "$CONFIG_DIR/bin_dir" 2>/dev/null || true)
        else
            BIN_DIR="${BIN_DIR:-$HOME/bin}"
        fi
    fi
    BLOCKLIST="$CONFIG_DIR/blocklist"
    # Export for scripts that source this file
    export CONFIG_DIR BIN_DIR BLOCKLIST
}

# Remove systemd user units with given base name
cleanup_systemd_units() {
    local name="$1"
    local unit_dir
    unit_dir="$(get_systemd_unit_dir)"
    [ -d "$unit_dir" ] || return 0
    rm -f "$unit_dir/$name.service" "$unit_dir/$name.path" "$unit_dir/$name.timer" 2>/dev/null || true
    # Attempt to stop/disable units if systemctl available
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user stop "$name.service" 2>/dev/null || true
        systemctl --user disable "$name.service" 2>/dev/null || true
        systemctl --user stop "$name.timer" 2>/dev/null || true
        systemctl --user disable "$name.timer" 2>/dev/null || true
    fi
}

# Normalize a path without resolving symlinks; handles '.' and '..'
canonicalize_path_no_resolve() {
    local path="$1"
    [ -n "$path" ] || return 1
    # Expand tilde
    if [[ "$path" == ~* ]]; then
        path="${path/#~/$HOME}"
    fi
    # Make absolute
    if [[ "$path" != /* ]]; then
        path="$PWD/$path"
    fi
    # Collapse '.' and '..'
    local -a parts stack
    IFS='/' read -ra parts <<< "$path"
    for part in "${parts[@]}"; do
        case "$part" in
            ''|'.') continue ;;
            '..') if [ ${#stack[@]} -gt 0 ]; then
                        unset 'stack[${#stack[@]}-1]'
                    fi ;;
            *) stack+=("$part") ;;
        esac
    done
    local result
    result="/$(IFS=/; echo "${stack[*]}")"
    printf '%s' "$result"
}

validate_home_dir() {
    local dir="$1"
    if [ -z "$dir" ]; then
        return 1
    fi
    # Expand relative paths and tildes
    if [[ "$dir" == ~* ]]; then
        dir="${dir/#~/$HOME}"
    fi
    if [[ "$dir" != /* ]]; then
        dir="$PWD/$dir"
    fi
    # If it's a symlink, resolve target (we must not allow symlinks pointing outside HOME)
    if [ -L "$dir" ]; then
        if command -v readlink >/dev/null 2>&1; then
            local target
            target=$(readlink -f "$dir" 2>/dev/null || true)
            if [ -z "$target" ]; then
                return 1
            fi
            dir="$target"
        else
            # Fall back to treating symlink as insecure
            return 1
        fi
    fi
    # Canonicalize without requiring the path to exist
    local resolved
    resolved=$(canonicalize_path_no_resolve "$dir" 2>/dev/null || true)
    if [ -z "$resolved" ]; then
        return 1
    fi
    case "$resolved" in
        "$HOME"|"$HOME"/*) return 0 ;;
        *) return 1 ;;
    esac
}

is_wrapper_file() {
    local file="$1"
    [ -f "$file" ] || return 1
    # Reject symlinks - ensure wrapper is an actual file
    [ -L "$file" ] && return 1
    # Read header (first 30 lines) for faster processing
    local header
    header=$(head -n 30 -- "$file" 2>/dev/null || true)
    # Reject binary or control characters in header
    if printf '%s' "$header" | LC_ALL=C tr -d '[:print:][:space:]' | grep -q .; then
        return 1
    fi
    # Must be a shell script (bash or sh)
    if ! printf '%s' "$header" | grep -qE '^#!.*(bash|sh)'; then
        return 1
    fi
    # Must contain exact marker
    if ! printf '%s' "$header" | grep -qF "Generated by fplaunchwrapper"; then
        return 1
    fi
    # Must contain NAME= and ID= lines in header
    if ! printf '%s' "$header" | grep -q '^NAME='; then
        return 1
    fi
    if ! printf '%s' "$header" | grep -q '^ID='; then
        return 1
    fi
    # Validate ID contents
    local idval
    idval=$(printf '%s' "$header" | grep -m1 '^ID=' | cut -d'"' -f2 || true)
    if [ -z "$idval" ]; then
        return 1
    fi
    if printf '%s' "$idval" | grep -q '[^A-Za-z0-9._-]'; then
        return 1
    fi
    return 0
}

get_wrapper_id() {
    local file="$1"
    [ -f "$file" ] || return 1
    local id
    id=$(grep -m1 '^ID=' "$file" 2>/dev/null | cut -d'"' -f2 || true)
    if [ -n "$id" ]; then
        printf '%s' "$id"
        return 0
    fi
    # Look for Flatpak ID in comment lines
    id=$(awk '/Flatpak ID:/ {print substr($0, index($0,$3))}' "$file" 2>/dev/null | head -n1 | sed -E 's/[^a-zA-Z0-9._-].*$//' || true)
    if [ -n "$id" ]; then
        printf '%s' "$id"
        return 0
    fi
    return 1
}

acquire_lock() {
    ensure_config_dir || return 1
    local lockfile="$CONFIG_DIR/.fplaunch-lock"
    if command -v flock >/dev/null 2>&1; then
        exec 9>"$lockfile" || return 1
        flock -x 9 || return 1
        LOCK_FD=9
    else
        local lockdir="$CONFIG_DIR/.fplaunch-lockdir"
        while ! mkdir "$lockdir" 2>/dev/null; do
            sleep 0.05
        done
        LOCK_DIR="$lockdir"
    fi
    return 0
}

release_lock() {
    if [ -n "${LOCK_FD:-}" ]; then
        flock -u "$LOCK_FD" 2>/dev/null || true
        eval "exec ${LOCK_FD}>&-" 2>/dev/null || true
        unset LOCK_FD
    fi
    if [ -n "${LOCK_DIR:-}" ]; then
        rmdir "$LOCK_DIR" 2>/dev/null || true
        unset LOCK_DIR
    fi
    return 0
}

get_temp_dir() {
    if [ -n "${TMPDIR:-}" ] && [ -d "${TMPDIR:-}" ]; then
        printf '%s' "${TMPDIR:-}"
        return 0
    fi
    if [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -d "${XDG_RUNTIME_DIR:-}" ]; then
        printf '%s' "${XDG_RUNTIME_DIR:-}"
        return 0
    fi
    if [ -n "${XDG_CACHE_HOME:-}" ] && [ -d "${XDG_CACHE_HOME:-}" ]; then
        printf '%s' "${XDG_CACHE_HOME:-}"
        return 0
    fi
    if [ -d "$HOME/.cache" ]; then
        printf '%s' "$HOME/.cache"
        return 0
    fi
    if [ -d "/var/tmp" ]; then
        printf '%s' "/var/tmp"
        return 0
    fi
    if [ -d "/tmp" ]; then
        printf '%s' "/tmp"
        return 0
    fi
    return 1
}

find_executable() {
    local cmd="$1"
    [ -n "$cmd" ] || return 1
    # Absolute or relative path
    if [[ "$cmd" == */* ]]; then
        [ -x "$cmd" ] && printf '%s' "$cmd" && return 0
        return 1
    fi
    # command -v is the most reliable
    if command -v "$cmd" >/dev/null 2>&1; then
        printf '%s' "$(command -v "$cmd")"
        return 0
    fi
    # Fallback: iterate over PATH entries
    IFS=':' read -ra _dirs <<< "$PATH"
    for _d in "${_dirs[@]}"; do
        [ -z "$_d" ] && continue
        if [ -x "$_d/$cmd" ]; then
            printf '%s' "$_d/$cmd"
            return 0
        fi
    done
    return 1
}

safe_mktemp() {
    local template="${1:-tmp.XXXXXX}"
    local dir_param="${2:-}"
    local tdir
    if [ -n "$dir_param" ] && [ -d "$dir_param" ]; then
        tdir="$dir_param"
    else
        tdir=$(get_temp_dir 2>/dev/null) || tdir="/tmp"
    fi
    if command -v mktemp >/dev/null 2>&1; then
        if mktemp -p "$tdir" "$template" >/dev/null 2>&1; then
            mktemp -p "$tdir" "$template"
            return 0
        fi
        if mktemp "$tdir/$template" >/dev/null 2>&1; then
            mktemp "$tdir/$template"
            return 0
        fi
    fi
    printf '%s' "$tdir/${template//X/0}.$RANDOM"
}

sanitize_id_to_name() {
    local id="$1"
    local name
    name=$(printf '%s' "$id" | awk -F. '{print tolower($NF)}')
    # Try Unicode normalization and transliteration
    if command -v iconv >/dev/null 2>&1; then
        # Try NFKD normalization first
        local norm
        norm=$(printf '%s' "$name" | iconv -f UTF-8 -t UTF-8//IGNORE 2>/dev/null || true)
        [ -n "$norm" ] && name="$norm"
        # Transliterate to ASCII
        local translit
        translit=$(printf '%s' "$name" | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null || true)
        [ -n "$translit" ] && name="$translit"
    fi
    name=$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')
    name=$(printf '%s' "$name" | sed 's/[^a-z0-9_\-]/-/g')
    name=$(printf '%s' "$name" | sed 's/^[^a-z0-9]\+//; s/[^a-z0-9]\+$//; s/-\+/-/g')
    if [ -z "$name" ]; then
        if command -v sha256sum >/dev/null 2>&1; then
            name="app-$(printf '%s' "$id" | sha256sum | cut -c1-8)"
        elif command -v md5sum >/dev/null 2>&1; then
            name="app-$(printf '%s' "$id" | md5sum | cut -c1-8)"
        else
            name="app-$(printf '%s' "$RANDOM")"
        fi
    fi
    name=$(printf '%s' "$name" | cut -c1-100)
    printf '%s' "$name"
}

check_disk_space() {
    local dir="${1:-.}"
    local min_mb="${2:-10}"
    [ -n "$dir" ] || return 1
    [ -d "$dir" ] || return 1
    local avail_kb
    avail_kb=$(df -P -k "$dir" 2>/dev/null | awk 'NR==2 {print $4}') || avail_kb=0
    [ -n "$avail_kb" ] || avail_kb=0
    local avail_mb=$((avail_kb / 1024))
    if [ "$avail_mb" -lt "$min_mb" ]; then
        return 1
    fi
    return 0
}

get_wrapper_name() {
    local path="$1"
    [ -n "$path" ] || return 1
    printf '%s' "$(basename "$path")"
}
