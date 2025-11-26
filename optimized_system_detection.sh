#!/usr/bin/env bash
# Optimized system command detection for fplaunchwrapper
# Maintains standard path precedence while skipping wrapper location

# Function to detect system command with proper precedence
detect_system_command_optimized() {
    local name="$1"
    local script_bin_dir="$2"
    
    # Standard system path precedence (from most to least preferred)
    # This matches the typical Unix/Linux PATH order
    local system_paths=(
        "/usr/local/bin"   # Local system software
        "/usr/bin"         # Standard system commands  
        "/bin"             # Essential system commands
        "/usr/local/sbin"  # Local system admin tools
        "/usr/sbin"        # Standard system admin tools
        "/sbin"            # Essential system admin tools
    )
    
    # Also check for additional system paths that might be in PATH
    # but exclude user-specific and package manager directories
    if command -v awk >/dev/null 2>&1; then
        local additional_paths
    additional_paths=$(echo "$PATH" | awk -F: '{
            for(i=1;i<=NF;i++) {
                path = $i
                gsub(/\/$/, "", path)  # Remove trailing slash
                # Include if it looks like a system path but exclude user/package manager paths
                if (path ~ "^/usr" || path ~ "^/bin" || path ~ "^/sbin") {
                    if (path !~ "'"${HOME}"'" && path !~ "snap" && path !~ "flatpak" && 
                        path !~ "conda" && path !~ "pyenv" && path !~ "node_modules" &&
                        path !~ ".linuxbrew" && path !~ "homebrew") {
                        print path
                    }
                }
            }
        }' | sort -u)
        
        # Add additional paths that aren't already in our list
        for additional_path in $additional_paths; do
            local already_included=false
            for existing_path in "${system_paths[@]}"; do
                if [ "$additional_path" = "$existing_path" ]; then
                    already_included=true
                    break
                fi
            done
            if [ "$already_included" = false ] && [ -d "$additional_path" ] && [ -r "$additional_path" ]; then
                system_paths+=("$additional_path")
            fi
        done
    fi
    
    # Search system paths in precedence order, skipping wrapper location
    for sys_dir in "${system_paths[@]}"; do
        local candidate="$sys_dir/$name"
        
        # Check if command exists and is executable
        if [ -f "$candidate" ] && [ -x "$candidate" ]; then
            # Skip if this is the wrapper itself
            if [ "$candidate" = "$script_bin_dir/$name" ]; then
                continue
            fi
            
            # Found a real system command
            echo "true:$candidate"
            return 0
        fi
    done
    
    # No system command found
    echo "false:"
    return 0
}

# Function to demonstrate the improved logic
demonstrate_detection() {
    local name="$1"
    local script_bin_dir="$2"
    
    echo "=== Optimized Detection for: $name ==="
    echo "Wrapper location: $script_bin_dir/$name"
    echo
    
    # Show system paths being checked (in order)
    echo "System paths checked (in precedence order):"
    local system_paths=(
        "/usr/local/bin"
        "/usr/bin" 
        "/bin"
        "/usr/local/sbin"
        "/usr/sbin"
        "/sbin"
    )
    
    for i in "${!system_paths[@]}"; do
        local path="${system_paths[$i]}"
        local status="❌"
        if [ -d "$path" ] && [ -r "$path" ]; then
            if [ -f "$path/$name" ] && [ -x "$path/$name" ]; then
                status="✅"
            fi
            printf "  %2d. %-15s %s\n" $((i+1)) "$path" "$status"
        else
            printf "  %2d. %-15s %s (not accessible)\n" $((i+1)) "$path" "$status"
        fi
    done
    echo
    
    # Run optimized detection
    local result
    result=$(detect_system_command_optimized "$name" "$script_bin_dir")
    local system_exists
    system_exists=$(echo "$result" | cut -d: -f1)
    local cmd_path
    cmd_path=$(echo "$result" | cut -d: -f2)
    
    echo "Detection results:"
    if [ "$system_exists" = "true" ]; then
        echo "  ✅ SYSTEM_EXISTS: true"
        echo "  📍 CMD_PATH: $cmd_path"
        echo
        echo "🎯 USER CHOICE: User will be prompted to choose between:"
        echo "   1. System package ($cmd_path)"
        echo "   2. Flatpak app (org.example.App)"
    else
        echo "  ❌ SYSTEM_EXISTS: false"
        echo "  📝 CMD_PATH: (none)"
        echo
        echo "🚀 AUTO-FLATPAK: No system version found, will use Flatpak"
    fi
    echo
}

# Function to show comparison with current logic
compare_with_current() {
    local name="$1"
    local script_bin_dir="$2"
    
    echo "=== Comparison with Current Wrapper Logic ==="
    
    # Current logic (PATH-dependent)
    echo "Current logic:"
    if command -v "$name" >/dev/null 2>&1; then
        local current_path
        current_path=$(which "$name")
        echo "  Found via PATH: $current_path"
        if [[ "$current_path" != "$script_bin_dir/$name" ]]; then
            echo "  SYSTEM_EXISTS: true (different command found)"
        else
            echo "  SYSTEM_EXISTS: false (wrapper found itself)"
        fi
    else
        echo "  SYSTEM_EXISTS: false (no command found)"
    fi
    echo
    
    # Optimized logic
    echo "Optimized logic:"
    local result
    result=$(detect_system_command_optimized "$name" "$script_bin_dir")
    local system_exists
    system_exists=$(echo "$result" | cut -d: -f1)
    local cmd_path
    cmd_path=$(echo "$result" | cut -d: -f2)
    
    if [ "$system_exists" = "true" ]; then
        echo "  SYSTEM_EXISTS: true"
        echo "  CMD_PATH: $cmd_path"
    else
        echo "  SYSTEM_EXISTS: false"
        echo "  CMD_PATH: (none)"
    fi
    echo
    
    # Show the difference
    if [ "$system_exists" = "true" ] && ! command -v "$name" >/dev/null 2>&1; then
        echo "🚨 CRITICAL IMPROVEMENT: Current logic would miss this system command!"
    elif [ "$system_exists" = "true" ] && command -v "$name" >/dev/null 2>&1; then
        local current_path
        current_path=$(which "$name")
        if [[ "$current_path" = "$script_bin_dir/$name" ]]; then
            echo "🚨 PATH-ORDER ISSUE: Current logic fails due to wrapper precedence"
            echo "   Optimized logic correctly finds: $cmd_path"
        else
            echo "✅ Both logics work for this case"
        fi
    else
        echo "✅ Both logics agree: no system command"
    fi
}

# Test with various applications
echo "=== Optimized System Command Detection Test ==="
echo

# Test with commands that commonly have both system and flatpak versions
test_apps=("libreoffice" "gedit" "evince" "thunderbird" "vlc")

for app in "${test_apps[@]}"; do
    if [ -f "/var/home/dlafreniere/.local/bin/$app" ]; then
        demonstrate_detection "$app" "/var/home/dlafreniere/.local/bin"
        compare_with_current "$app" "/var/home/dlafreniere/.local/bin"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo
    fi
done

# Test with a guaranteed system command
echo "=== Testing with guaranteed system command (which) ==="
demonstrate_detection "which" "/var/home/dlafreniere/.local/bin"
compare_with_current "which" "/var/home/dlafreniere/.local/bin"

echo "=== Integration Code for fplaunchwrapper ==="
echo
echo "Replace this section in fplaunch-generate (around line 278-285):"
echo
echo "# OLD CODE:"
echo 'SYSTEM_EXISTS=false'
echo "if command -v \"$name\" >/dev/null 2>&1; then"
echo "    CMD_PATH=\$(which \"$name\")"
echo "    if [[ \"\$CMD_PATH\" != \"$script_bin_dir/\$name\" ]]; then"
echo '        SYSTEM_EXISTS=true'
echo '    fi'
echo 'fi'
echo
echo "# NEW CODE:"
echo 'SYSTEM_EXISTS=false'
echo 'CMD_PATH=""'
echo ''
echo '# Check standard system paths in precedence order'
echo 'for sys_dir in "/usr/local/bin" "/usr/bin" "/bin" "/usr/local/sbin" "/usr/sbin" "/sbin"; do'
echo "    candidate=\"\$sys_dir/\$NAME\""
echo "    if [ -f \"\$candidate\" ] && [ -x \"\$candidate\" ] && [ \"\$candidate\" != \"$script_bin_dir/\$name\" ]; then"
echo '        SYSTEM_EXISTS=true'
echo "        CMD_PATH=\"\$candidate\""
echo '        break'
echo '    fi'
echo 'done'
echo
echo "This ensures system commands are always detected regardless of PATH order!"