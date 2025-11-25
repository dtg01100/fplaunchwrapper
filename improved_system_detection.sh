#!/usr/bin/env bash
# Improved system command detection for fplaunchwrapper
# This replaces the PATH-dependent logic with comprehensive system path scanning

# Function to auto-detect system paths (can be included in wrapper)
get_system_paths() {
    local system_paths=""
    
    # Standard system directories (most common first)
    local standard_paths=(
        "/usr/local/bin"
        "/usr/bin" 
        "/bin"
        "/usr/local/sbin"
        "/usr/sbin"
        "/sbin"
    )
    
    # Add system directories from PATH that aren't user-specific
    if command -v awk >/dev/null 2>&1; then
        # Get unique system directories from PATH, exclude user dirs
        local path_system_dirs=$(echo "$PATH" | awk -F: '{
            for(i=1;i<=NF;i++) {
                if ($i ~ "^/usr" || $i ~ "^/bin" || $i ~ "^/sbin") {
                    gsub(/\/$/, "", $i)  # Remove trailing slash
                    if ($i !~ "'"${HOME}"'" && $i !~ "snap" && $i !~ "flatpak" && $i !~ "conda" && $i !~ "pyenv") {
                        print $i
                    }
                }
            }
        }' | sort -u)
        
        # Combine standard and PATH-derived paths
        for path in "${standard_paths[@]}"; do
            if [ -d "$path" ] && [ -r "$path" ] && [[ ! "$system_paths" =~ "$path" ]]; then
                if [ -z "$system_paths" ]; then
                    system_paths="$path"
                else
                    system_paths="$system_paths $path"
                fi
            fi
        done
        
        # Add any additional system paths found in PATH
        for path in $path_system_dirs; do
            if [ -d "$path" ] && [ -r "$path" ] && [[ ! "$system_paths" =~ " $path " ]] && [[ ! "$system_paths" == "$path" ]]; then
                system_paths="$system_paths $path"
            fi
        done
    else
        # Fallback: just use standard paths
        for path in "${standard_paths[@]}"; do
            if [ -d "$path" ] && [ -r "$path" ]; then
                if [ -z "$system_paths" ]; then
                    system_paths="$path"
                else
                    system_paths="$system_paths $path"
                fi
            fi
        done
    fi
    
    echo "$system_paths"
}

# Function to detect system command (PATH-order independent)
detect_system_command() {
    local name="$1"
    local script_bin_dir="$2"
    
    local system_exists=false
    local cmd_path=""
    
    # Get all system paths
    local system_paths=$(get_system_paths)
    
    # Look for system command in system paths (NOT in script_bin_dir)
    for sys_dir in $system_paths; do
        local candidate="$sys_dir/$name"
        if [ -f "$candidate" ] && [ -x "$candidate" ]; then
            # Make sure it's not the wrapper itself
            if [ "$candidate" != "$script_bin_dir/$name" ]; then
                cmd_path="$candidate"
                system_exists=true
                break  # Found first non-wrapper system version
            fi
        fi
    done
    
    # Return results
    echo "$system_exists:$cmd_path"
}

# Example usage in wrapper (replace the existing system detection logic)
example_usage() {
    local name="libreoffice"
    local script_bin_dir="/var/home/dlafreniere/.local/bin"
    
    echo "=== Example: Using improved detection for $name ==="
    echo "Wrapper location: $script_bin_dir/$name"
    echo
    
    # Use improved detection
    local result=$(detect_system_command "$name" "$script_bin_dir")
    local system_exists=$(echo "$result" | cut -d: -f1)
    local cmd_path=$(echo "$result" | cut -d: -f2)
    
    echo "Improved detection results:"
    echo "  SYSTEM_EXISTS: $system_exists"
    echo "  CMD_PATH: $cmd_path"
    echo
    
    # Compare with current logic
    echo "Current wrapper logic:"
    if command -v "$name" >/dev/null 2>&1; then
        local current_path=$(which "$name")
        echo "  Found: $current_path"
        if [[ "$current_path" != "$script_bin_dir/$name" ]]; then
            echo "  SYSTEM_EXISTS: true"
        else
            echo "  SYSTEM_EXISTS: false (wrapper found itself)"
        fi
    else
        echo "  No command found"
        echo "  SYSTEM_EXISTS: false"
    fi
    
    # Show improvement
    echo
    if [ "$system_exists" = "true" ]; then
        echo "✅ IMPROVEMENT: System command detected at $cmd_path"
        echo "   Users can now choose between system and flatpak versions!"
    else
        echo "ℹ️  No system command found - flatpak-only app"
    fi
}

# Test with various scenarios
echo "=== Testing Improved System Detection ==="
echo

# Test with a command that exists in multiple locations
example_usage

echo
echo "=== System Paths Detected ==="
get_system_paths | tr ' ' '\n' | nl

echo
echo "=== Testing Edge Cases ==="

# Test with a command that should not exist
nonexistent_result=$(detect_system_command "this-command-should-not-exist" "/tmp")
nonexistent_exists=$(echo "$nonexistent_result" | cut -d: -f1)
echo "Nonexistent command: $nonexistent_exists (should be false)"

# Test with a wrapper that has no system equivalent
wrapper_only_result=$(detect_system_command "studio" "/var/home/dlafreniere/.local/bin")
wrapper_only_exists=$(echo "$wrapper_only_result" | cut -d: -f1)
echo "Wrapper-only command (studio): $wrapper_only_exists"

echo
echo "=== Integration Instructions ==="
echo "To integrate this into fplaunchwrapper:"
echo "1. Replace the SYSTEM_EXISTS detection logic in fplaunch-generate"
echo "2. Use detect_system_command() instead of command -v/which"
echo "3. This ensures system commands are always detected regardless of PATH order"