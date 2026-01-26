#!/usr/bin/env python3
with open("lib/generate.py", "r") as f:
    lines = f.readlines()

# Enhanced --fpwrapper-edit-sandbox implementation
enhanced_edit_sandbox = """# Edit sandbox permissions - Enhanced interactive implementation
if [ "$1" = "--fpwrapper-edit-sandbox" ]; then
    if ! command -v flatpak >/dev/null 2>&1; then
        echo "Flatpak not available - cannot edit sandbox"
        exit 1
    fi
    
    if ! is_interactive; then
        echo "Error: Sandbox editing requires interactive CLI" >&2
        exit 1
    fi
    
    # Check if Flatseal is installed
    if flatpak list --app 2>/dev/null | grep -q "com.github.tchx84.Flatseal"; then
        echo "Launching Flatseal for $ID..."
        flatpak run com.github.tchx84.Flatseal "$ID" 2>/dev/null &
        exit 0
    fi
    
    # Check if user previously declined Flatseal installation
    FLATSEAL_DECLINED_MARKER="${XDG_CONFIG_HOME:-$HOME/.config}/fplaunchwrapper/flatseal_declined"
    
    if [ ! -f "$FLATSEAL_DECLINED_MARKER" ]; then
        echo ""
        echo "Flatseal (GUI permissions editor) not found."
        read -r -p "Would you like to install it? [y/N] " install_flatseal
        case "$install_flatseal" in
            [yY]|[yY][eE][sS])
                echo "Installing Flatseal..."
                if flatpak install flathub com.github.tchx84.Flatseal -y; then
                    echo "Flatseal installed successfully. Launching..."
                    flatpak run com.github.tchx84.Flatseal "$ID" 2>/dev/null &
                    exit 0
                else
                    echo "Failed to install Flatseal. Falling back to CLI editor."
                fi
                ;;
            *)
                echo "Flatseal installation declined. Using CLI editor."
                mkdir -p "$(dirname "$FLATSEAL_DECLINED_MARKER")"
                touch "$FLATSEAL_DECLINED_MARKER"
                ;;
        esac
    fi
    
    # CLI fallback - Enhanced interactive permission editor
    echo ""
    echo "=========================================="
    echo "Sandbox Permissions Editor for $ID"
    echo "=========================================="
    echo ""
    
    # Show detailed current permissions
    echo "Current permissions:"
    CURRENT_OVERRIDES=$(flatpak override --show --user "$ID" 2>&1)
    if [ $? -eq 0 ] && [ -n "$CURRENT_OVERRIDES" ] && ! echo "$CURRENT_OVERRIDES" | grep -q "No overrides"; then
        echo "$CURRENT_OVERRIDES" | grep -v "^\["
    else
        echo "  (using default permissions)"
    fi
    echo ""
    
    # Enhanced built-in presets
    PRESET_DEVELOPMENT="--filesystem=home --filesystem=host --device=dri --socket=x11 --socket=wayland --share=network --share=ipc"
    PRESET_MEDIA="--device=dri --device=all --socket=pulseaudio --socket=wayland --socket=x11 --share=ipc"
    PRESET_NETWORK="--share=network --share=ipc --socket=wayland --socket=x11"
    PRESET_MINIMAL="--share=ipc"
    PRESET_GAMING="--filesystem=home --device=dri --device=all --socket=pulseaudio --socket=wayland --socket=x11 --share=network --share=ipc"
    PRESET_OFFLINE="--filesystem=home --device=dri --socket=wayland --socket=x11 --share=ipc"
    
    # Load custom presets from config
    CUSTOM_PRESETS=()
    if command -v python3 >/dev/null 2>&1; then
        while IFS= read -r preset_name; do
            [ -n "$preset_name" ] && CUSTOM_PRESETS+=("$preset_name")
        done < <(python3 -m fplaunch.config_manager list-presets 2>/dev/null)
    fi
    
    # Display enhanced menu
    echo "Select an option:"
    echo "  1) Manual entry (line-by-line)"
    echo "  2) Apply preset: Development (full access + dev tools)"
    echo "  3) Apply preset: Media (audio/video/graphics)"
    echo "  4) Apply preset: Network (networking + IPC)"
    echo "  5) Apply preset: Gaming (full hardware access)"
    echo "  6) Apply preset: Offline (local files + graphics only)"
    echo "  7) Apply preset: Minimal (IPC only)"
    
    menu_option=8
    for custom_preset in "${CUSTOM_PRESETS[@]}"; do
        echo "  $menu_option) Apply custom preset: $custom_preset"
        ((menu_option++))
    done
    
    echo "  $menu_option) Show current overrides"
    ((menu_option++))
    echo "  $menu_option) Remove specific permission"
    ((menu_option++))
    echo "  $menu_option) Reset to defaults"
    ((menu_option++))
    echo "  $menu_option) Cancel"
    echo ""
    
    read -r -p "Choose option: " choice
    
    case "$choice" in
        1)
            # Manual entry with enhanced validation
            echo ""
            echo "Enter permissions one per line (empty line to finish)"
            echo "Examples:"
            echo "  --filesystem=home"
            echo "  --filesystem=host"
            echo "  --device=dri"
            echo "  --device=all"
            echo "  --share=network"
            echo "  --share=ipc"
            echo "  --socket=x11"
            echo "  --socket=wayland"
            echo "  --socket=pulseaudio"
            echo "  --talk-name=org.freedesktop.Notifications"
            echo ""
            
            PERMISSIONS=()
            while true; do
                read -r -p "Permission: " perm
                [ -z "$perm" ] && break
                
                # Enhanced validation for common permission types
                if [[ "$perm" =~ ^--[a-z-]+(=.+)?$ ]]; then
                    PERMISSIONS+=("$perm")
                else
                    echo "  Warning: Invalid format (must start with --, e.g., --filesystem=home)"
                fi
            done
            
            if [ ${#PERMISSIONS[@]} -eq 0 ]; then
                echo "No permissions entered."
                exit 0
            fi
            
            echo ""
            echo "Permissions to apply:"
            printf '  %s\\n' "${PERMISSIONS[@]}"
            echo ""
            read -r -p "Apply these ${#PERMISSIONS[@]} permissions? [y/N] " confirm
            
            if [[ "$confirm" =~ ^[yY]$ ]]; then
                echo "Applying permissions..."
                for perm in "${PERMISSIONS[@]}"; do
                    if flatpak override --user "$ID" "$perm" 2>/dev/null; then
                        echo "  ✓ Applied: $perm"
                    else
                        echo "  ✗ Failed: $perm"
                    fi
                done
                echo ""
                echo "Permissions updated. Final state:"
                flatpak override --show --user "$ID" 2>&1 | grep -v "^\[" || echo "  (none)"
            else
                echo "Cancelled."
            fi
            ;;
        2|3|4|5|6|7)
            # Enhanced built-in presets
            case "$choice" in
                2) PRESET_NAME="Development"; PRESET_PERMS=($PRESET_DEVELOPMENT) ;;
                3) PRESET_NAME="Media"; PRESET_PERMS=($PRESET_MEDIA) ;;
                4) PRESET_NAME="Network"; PRESET_PERMS=($PRESET_NETWORK) ;;
                5) PRESET_NAME="Gaming"; PRESET_PERMS=($PRESET_GAMING) ;;
                6) PRESET_NAME="Offline"; PRESET_PERMS=($PRESET_OFFLINE) ;;
                7) PRESET_NAME="Minimal"; PRESET_PERMS=($PRESET_MINIMAL) ;;
            esac
            
            echo ""
            echo "Preset: $PRESET_NAME"
            echo "Permissions:"
            printf '  %s\\n' "${PRESET_PERMS[@]}"
            echo ""
            read -r -p "Apply these ${#PRESET_PERMS[@]} permissions? [y/N] " confirm
            
            if [[ "$confirm" =~ ^[yY]$ ]]; then
                echo "Applying preset..."
                for perm in "${PRESET_PERMS[@]}"; do
                    if flatpak override --user "$ID" "$perm" 2>/dev/null; then
                        echo "  ✓ Applied: $perm"
                    else
                        echo "  ✗ Failed: $perm"
                    fi
                done
                echo ""
                echo "Permissions updated. Final state:"
                flatpak override --show --user "$ID" 2>&1 | grep -v "^\[" || echo "  (none)"
            else
                echo "Cancelled."
            fi
            ;;
        *)
            # Check if it's a custom preset
            custom_index=$((choice - 8))
            if [ "$custom_index" -ge 0 ] && [ "$custom_index" -lt ${#CUSTOM_PRESETS[@]} ]; then
                PRESET_NAME="${CUSTOM_PRESETS[$custom_index]}"
                
                # Load preset permissions
                PRESET_PERMS=()
                if command -v python3 >/dev/null 2>&1; then
                    while IFS= read -r perm; do
                        [ -n "$perm" ] && PRESET_PERMS+=("$perm")
                    done < <(python3 -m fplaunch.config_manager get-preset "$PRESET_NAME" 2>/dev/null)
                fi
                
                if [ ${#PRESET_PERMS[@]} -eq 0 ]; then
                    echo "Failed to load preset: $PRESET_NAME"
                    exit 1
                fi
                
                echo ""
                echo "Custom preset: $PRESET_NAME"
                echo "Permissions:"
                printf '  %s\\n' "${PRESET_PERMS[@]}"
                echo ""
                read -r -p "Apply these ${#PRESET_PERMS[@]} permissions? [y/N] " confirm
                
                if [[ "$confirm" =~ ^[yY]$ ]]; then
                    echo "Applying custom preset..."
                    for perm in "${PRESET_PERMS[@]}"; do
                        if flatpak override --user "$ID" "$perm" 2>/dev/null; then
                            echo "  ✓ Applied: $perm"
                        else
                            echo "  ✗ Failed: $perm"
                        fi
                    done
                    echo ""
                    echo "Permissions updated. Final state:"
                    flatpak override --show --user "$ID" 2>&1 | grep -v "^\[" || echo "  (none)"
                else
                    echo "Cancelled."
                fi
            elif [ "$choice" = "$((menu_option - 4))" ]; then
                # Show current overrides with details
                echo ""
                echo "Current overrides for $ID:"
                flatpak override --show --user "$ID" 2>&1 || echo "  (using default permissions)"
            elif [ "$choice" = "$((menu_option - 3))" ]; then
                # Remove specific permission
                echo ""
                echo "Current permissions to remove:"
                CURRENT_PERMS=$(flatpak override --show --user "$ID" 2>&1 | grep -v "^\[" | grep -v "No overrides" | awk '{print $1}')
                
                if [ -z "$CURRENT_PERMS" ]; then
                    echo "  No custom permissions set"
                    exit 0
                fi
                
                echo "$CURRENT_PERMS" | nl -ba
                
                read -r -p "Enter number of permission to remove (or empty to cancel): " perm_number
                if [ -z "$perm_number" ]; then
                    echo "Cancelled."
                    exit 0
                fi
                
                if [[ "$perm_number" =~ ^[0-9]+$ ]]; then
                    PERM_TO_REMOVE=$(echo "$CURRENT_PERMS" | sed -n "${perm_number}p")
                    if [ -n "$PERM_TO_REMOVE" ]; then
                        echo ""
                        read -r -p "Remove permission: $PERM_TO_REMOVE? [y/N] " confirm
                        if [[ "$confirm" =~ ^[yY]$ ]]; then
                            # Remove the permission by resetting that specific override type
                            # This is a workaround since flatpak doesn't support direct removal
                            echo "Removing $PERM_TO_REMOVE..."
                            # Get current overrides without this permission
                            NEW_OVERRIDES=$(flatpak override --show --user "$ID" 2>&1 | grep -v "^\[" | grep -v "$PERM_TO_REMOVE")
                            # Reset all overrides and apply remaining ones
                            flatpak override --user --reset "$ID" 2>/dev/null
                            if [ -n "$NEW_OVERRIDES" ]; then
                                while IFS= read -r line; do
                                    if [ -n "$line" ]; then
                                        flatpak override --user "$ID" "$line" 2>/dev/null
                                    fi
                                done <<< "$NEW_OVERRIDES"
                            fi
                            echo "Permission removed successfully."
                            echo ""
                            echo "Updated permissions:"
                            flatpak override --show --user "$ID" 2>&1 | grep -v "^\[" || echo "  (using default permissions)"
                        else
                            echo "Cancelled."
                        fi
                    else
                        echo "Invalid permission number"
                    fi
                else
                    echo "Invalid input"
                fi
            elif [ "$choice" = "$((menu_option - 2))" ]; then
                # Reset to defaults with confirmation
                echo ""
                echo "Current overrides:"
                flatpak override --show --user "$ID" 2>&1 | grep -v "^\[" || echo "  (none)"
                echo ""
                echo "WARNING: This will reset ALL permissions to defaults."
                echo "This action cannot be undone!"
                echo ""
                read -r -p "Type 'yes' to confirm reset: " confirm
                
                if [ "$confirm" = "yes" ]; then
                    if flatpak override --user --reset "$ID" 2>/dev/null; then
                        echo "Permissions reset to defaults."
                    else
                        echo "Failed to reset permissions."
                        exit 1
                    fi
                else
                    echo "Reset cancelled."
                fi
            else
                # Cancel
                echo "Cancelled."
            fi
            ;;
    esac
    exit 0
fi
"""

# Replace lines 582-841 with enhanced implementation
lines[582:841] = enhanced_edit_sandbox.splitlines(True)

with open("lib/generate.py", "w") as f:
    f.writelines(lines)

print("Successfully updated --fpwrapper-edit-sandbox implementation")
