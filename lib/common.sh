#!/usr/bin/env bash

# Common utility functions for fplaunchwrapper

# Python availability check (cached)
_has_python3=""
_check_python3() {
    [ -z "$_has_python3" ] && _has_python3=$(command -v python3 >/dev/null 2>&1 && echo "yes" || echo "no")
    [ "$_has_python3" = "yes" ]
}

# Error handling framework
error_exit() {
    local message="$1"
    local exit_code="${2:-1}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Log error to stderr with timestamp
    echo "[$timestamp] ERROR: $message" >&2
    
    # Additional logging to file if available
    if [ -n "${ERROR_LOG:-}" ] && [ -w "$ERROR_LOG" ]; then
        echo "[$timestamp] ERROR: $message" >> "$ERROR_LOG"
    fi
    
    exit "$exit_code"
}

# Safe command execution with error handling
safe_execute() {
    local description="$1"
    shift
    
    # Log command execution
    echo "Executing: $description" >&2
    
    # Execute with error handling
    if "$@"; then
        return 0
    else
        local exit_code=$?
        error_exit "Failed to $description (exit code: $exit_code)" "$exit_code"
    fi
}

# Improved file operation with error handling
safe_file_operation() {
    local operation="$1"
    local file="$2"
    shift 2
    
    case "$operation" in
        "read")
            if [ ! -r "$file" ]; then
                error_exit "Cannot read file: $file (permission denied or file does not exist)"
            fi
            cat "$file" "$@"
            ;;
        "write")
            if [ ! -w "$(dirname "$file")" ]; then
                error_exit "Cannot write to file: $file (directory not writable)"
            fi
            echo "$@" > "$file"
            ;;
        "append")
            if [ ! -w "$(dirname "$file")" ]; then
                error_exit "Cannot append to file: $file (directory not writable)"
            fi
            echo "$@" >> "$file"
            ;;
        *)
            error_exit "Unknown file operation: $operation"
            ;;
    esac
}

# Structured logging and debugging
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Log to stderr with level prefix
    echo "[$timestamp] [$level]: $message" >&2
    
    # Log to file if LOG_FILE is set and writable
    if [ -n "${LOG_FILE:-}" ] && [ -w "$LOG_FILE" ]; then
        echo "[$timestamp] [$level]: $message" >> "$LOG_FILE"
    fi
}

debug_log() {
    if [ "${DEBUG:-0}" = "1" ]; then
        log_message "DEBUG" "$1"
    fi
}

info_log() {
    log_message "INFO" "$1"
}

warn_log() {
    log_message "WARN" "$1"
}

# Debug mode function for detailed logging
enable_debug_mode() {
    export DEBUG=1
    LOG_FILE="${CONFIG_DIR:-$HOME/.config/flatpak-wrappers}/debug.log"
    debug_log "Debug mode enabled"
    debug_log "Environment variables:"
    debug_log "  HOME: ${HOME:-<not set>}"
    # Sanitize PATH for security (show only first and last components)
    if [ -n "${PATH:-}" ]; then
        local first_path=$(echo "$PATH" | cut -d: -f1)
        local last_path=$(echo "$PATH" | cut -d: -f-1)
        if [ "$first_path" = "$last_path" ]; then
            debug_log "  PATH: $first_path"
        else
            debug_log "  PATH: $first_path:...:$last_path"
        fi
    else
        debug_log "  PATH: <not set>"
    fi
    debug_log "  XDG_CONFIG_HOME: ${XDG_CONFIG_HOME:-<not set>}"
    debug_log "  CONFIG_DIR: ${CONFIG_DIR:-<not set>}"
    debug_log "  BIN_DIR: ${BIN_DIR:-<not set>}"
}

# Safety check - never run as root
if [ "$(id -u)" = "0" ]; then
    error_exit "fplaunchwrapper should never be run as root for safety"
fi
echo "This tool is designed for user-level wrapper management only"

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
    
    # Use Python utility for robust path normalization if available
    if _check_python3 && [ -f "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" ]; then
        local result
        result=$(python3 "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" canonicalize_path "$path" 2>/dev/null)
        if [ -n "$result" ]; then
            printf '%s' "$result"
            return 0
        fi
    fi
    
    # Fallback to original implementation
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
    
    # Use Python utility for robust path validation if available
    if _check_python3 && [ -f "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" ]; then
        local result
        result=$(python3 "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" validate_home "$dir" 2>/dev/null)
        if [ -n "$result" ]; then
            printf '%s' "$result"
            return 0
        fi
    fi
    
    # Fallback to original implementation
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
    
    # Basic validation first
    [ -f "$file" ] || return 1
    [ -r "$file" ] || return 1
    [ ! -L "$file" ] || return 1  # Reject symlinks
    
    # Use Python utility for robust content validation if available
    if _check_python3 && [ -f "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" ]; then
        python3 "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" is_wrapper_file "$file" >/dev/null 2>&1 && return 0
    fi
    
    # Fallback to original implementation with additional safeguards
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
    
    # Use Python utility for robust ID extraction if available
    if _check_python3 && [ -f "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" ]; then
        python3 "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" get_wrapper_id "$file" 2>/dev/null && return 0
    fi
    
    # Fallback to original implementation
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
    
    local lock_name="${1:-fplaunch}"
    local timeout_seconds="${2:-30}"
    local lock_dir="$CONFIG_DIR/locks"
    
    # Create lock directory
    mkdir -p "$lock_dir" || return 1
    
    local lockfile="$lock_dir/$lock_name.lock"
    local pidfile="$lock_dir/$lock_name.pid"
    
    # Try to acquire lock with timeout using reliable timing
    local start_time=$(date +%s)
    local end_time=$((start_time + timeout_seconds))
    while [ $(date +%s) -lt $end_time ]; do
        # Use mkdir for atomic directory creation as lock
        if mkdir "$lockfile" 2>/dev/null; then
            # Write PID to lock file
            echo $$ > "$pidfile"
            # Set cleanup trap
            trap 'release_lock_internal "$lock_dir" "$lock_name"' EXIT
            return 0
        fi
        sleep 0.1
    done
    
    echo "Timeout acquiring lock: $lock_name" >&2
    return 1
}

release_lock() {
    local lock_name="${1:-fplaunch}"
    local lock_dir="$CONFIG_DIR/locks"
    release_lock_internal "$lock_dir" "$lock_name"
}

release_lock_internal() {
    local lock_dir="$1"
    local lock_name="$2"
    
    local lockfile="$lock_dir/$lock_name.lock"
    local pidfile="$lock_dir/$lock_name.pid"
    
    # Verify this process owns the lock
    if [ -f "$pidfile" ]; then
        local lock_pid
        lock_pid=$(cat "$pidfile" 2>/dev/null || echo 0)
        if [ "$lock_pid" = $$ ]; then
            # Use specific file removal instead of rm -rf
            rm -f "$lockfile" 2>/dev/null || true
            rm -f "$pidfile" 2>/dev/null || true
        fi
    fi
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
    
    # Use Python utility for robust path resolution if available
    if _check_python3 && [ -f "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" ]; then
        python3 "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" find_executable "$cmd" 2>/dev/null && return 0
    fi
    
    # Fallback to original implementation
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
    
    # Use Python utility for secure temp file creation if available
    if _check_python3 && [ -f "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" ]; then
        python3 "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" safe_mktemp "$template" "$dir_param" 2>/dev/null && return 0
    fi
    
    # Fallback to original implementation
    local tdir
    
    # Get secure temp directory
    if [ -n "$dir_param" ] && [ -d "$dir_param" ]; then
        tdir="$dir_param"
    else
        tdir=$(get_temp_dir 2>/dev/null) || tdir="/tmp"
    fi
    
    # Fallback to mktemp if available
    if command -v mktemp >/dev/null 2>&1; then
        if mktemp -p "$tdir" "$template" 2>/dev/null; then
            mktemp -p "$tdir" "$template"
            return 0
        fi
        if mktemp "$tdir/$template" 2>/dev/null; then
            mktemp "$tdir/$template"
            return 0
        fi
    fi
    
    # Last resort: use random number with current timestamp
    local timestamp=$(date +%s%N)
    local random_val=$((RANDOM % 100000))
    echo "$tdir/${template//X/0}.${timestamp}.${random_val}"
}

sanitize_id_to_name() {
    local id="$1"
    
    # Use Python utility for robust name sanitization if available
    if _check_python3 && [ -f "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" ]; then
        python3 "$(dirname "${BASH_SOURCE[0]}")/python_utils.py" sanitize_name "$id" 2>/dev/null && return 0
    fi
    
    # Fallback to original implementation
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
