#!/usr/bin/env python3
"""Wrapper generation functionality for fplaunchwrapper
Replaces fplaunch-generate bash script with Python implementation.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import our utilities
try:
    from .python_utils import (
        acquire_lock,
        find_executable,
        get_temp_dir,
        get_wrapper_id,
        is_wrapper_file,
        release_lock,
        safe_mktemp,
        sanitize_id_to_name,
        validate_home_dir,
    )

    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None
console_err = Console(stderr=True) if RICH_AVAILABLE else None


class WrapperGenerator:
    """Generates Flatpak application wrappers."""

    def __init__(
        self,
        bin_dir: str,
        config_dir: str | None = None,
        verbose: bool = False,
        emit_mode: bool = False,
        emit_verbose: bool = False,
    ) -> None:
        # Backwards compatibility: allow positional booleans for verbose/emit flags
        if isinstance(config_dir, bool):
            verbose, emit_mode, emit_verbose = config_dir, verbose, emit_mode
            config_dir = None

        # Validate inputs to avoid creating unexpected artifact paths (e.g., MagicMock reprs)
        if not isinstance(bin_dir, (str, os.PathLike)):
            raise TypeError("bin_dir must be a string or path-like object")
        if config_dir is not None and not isinstance(
            config_dir, (str, os.PathLike, bool)
        ):
            raise TypeError("config_dir must be a string or path-like object or None")

        self.bin_dir = Path(bin_dir).expanduser().resolve()
        self.verbose = verbose
        self.emit_mode = emit_mode
        self.emit_verbose = emit_verbose
        self.lock_name = "generate"
        self.config_dir = (
            Path(config_dir)
            if config_dir
            else (Path.home() / ".config" / "fplaunchwrapper")
        )

        # Ensure directories exist (unless in emit mode)
        if not emit_mode:
            self.bin_dir.mkdir(parents=True, exist_ok=True)
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Save bin_dir to config
            (self.config_dir / "bin_dir").write_text(str(self.bin_dir))

    def log(self, message: str, level: str = "info") -> None:
        """Log a message to appropriate stream."""
        if level == "error":
            if console_err:
                console_err.print(f"[red]ERROR:[/red] {message}")
            else:
                print(f"ERROR: {message}", file=sys.stderr)
        elif level == "warning":
            if console_err:
                console_err.print(f"[yellow]WARN:[/yellow] {message}")
            else:
                print(f"WARN: {message}", file=sys.stderr)
        elif level == "success":
            if console:
                console.print(f"[green]✓[/green] {message}")
            else:
                print(f"✓ {message}")
        else:
            # info messages
            if console:
                console.print(message)
            else:
                print(message)

    def run_command(
        self,
        cmd: list[str],
        description: str = "",
    ) -> subprocess.CompletedProcess:
        """Run a command with optional progress display."""
        if description and console and not self.verbose:
            with console.status(f"[bold green]{description}..."):
                result = subprocess.run(
                    cmd, check=False, capture_output=True, text=True
                )
        else:
            if self.verbose:
                self.log(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

        return result

    def get_installed_flatpaks(self) -> list[str]:
        """Get list of installed Flatpak applications."""
        self.log("Checking for Flatpak installation...")

        flatpak_path = find_executable("flatpak") if UTILS_AVAILABLE else None
        if not flatpak_path:
            msg = "Flatpak not found. Please install Flatpak first."
            raise RuntimeError(msg)

        self.log(f"Found Flatpak at: {flatpak_path}")

        # Get installed apps from both user and system installations
        result = self.run_command(
            [flatpak_path, "list", "--app", "--columns=application"],
            "Getting installed Flatpak applications",
        )

        if result.returncode != 0:
            msg = f"Failed to get Flatpak applications: {result.stderr}"
            raise RuntimeError(msg)

        # Parse output and remove duplicates
        apps = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("Application ID"):
                apps.append(line)

        # Also check system installation
        result_system = self.run_command(
            [flatpak_path, "list", "--app", "--columns=application", "--system"],
            "Checking system Flatpak installations",
        )

        if result_system.returncode == 0:
            for line in result_system.stdout.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("Application ID") and line not in apps:
                    apps.append(line)

        return sorted(set(apps))

    def cleanup_obsolete_wrappers(self, installed_apps: list[str]) -> int:
        """Remove wrappers for uninstalled applications."""
        self.log("Cleaning up obsolete wrappers...")

        removed_count = 0

        # Get existing wrappers
        if not self.bin_dir.exists():
            return 0

        for item in self.bin_dir.iterdir():
            if not item.is_file():
                continue

            remove_item = False

            # Check if it's a wrapper
            if UTILS_AVAILABLE and is_wrapper_file(str(item)):
                wrapper_id = get_wrapper_id(str(item))
                if wrapper_id and wrapper_id not in installed_apps:
                    remove_item = True
            else:
                # Fallback: treat file as potential wrapper and remove if name not in installed apps
                sanitized_installed = [sanitize_id_to_name(a) for a in installed_apps]
                if item.name not in sanitized_installed:
                    remove_item = True

            if remove_item:
                self.log(f"Removing obsolete wrapper: {item.name}")
                try:
                    item.unlink()
                    removed_count += 1

                    # Remove preference file
                    pref_file = self.config_dir / f"{item.name}.pref"
                    if pref_file.exists():
                        pref_file.unlink()

                    # Remove aliases
                    aliases_file = self.config_dir / "aliases"
                    if aliases_file.exists():
                        content = aliases_file.read_text()
                        new_content = "\n".join(
                            line
                            for line in content.split("\n")
                            if not line.startswith(f"{item.name} ")
                        )
                        if new_content.strip():
                            aliases_file.write_text(new_content)
                        else:
                            aliases_file.unlink()

                except Exception as e:
                    self.log(f"Failed to remove {item.name}: {e}", "warning")

        if removed_count == 0:
            self.log("No obsolete wrappers found")
        else:
            self.log(f"Removed {removed_count} obsolete wrapper(s)")

        return removed_count

    def is_blocklisted(self, app_id: str) -> bool:
        """Check if an application is blocklisted."""
        blocklist_file = self.config_dir / "blocklist"
        if not blocklist_file.exists():
            return False

        try:
            blocklist_content = blocklist_file.read_text()
            for line in blocklist_content.split("\n"):
                line = line.strip()
                if line and line == app_id:
                    return True
        except Exception as e:
            self.log(f"Warning: Failed to read blocklist file: {e}", "warning")

        return False

    def generate_wrapper(self, app_id: str, flatpak_id: str | None = None) -> bool:
        """Generate a wrapper script for a single application.

        Args:
            app_id: Logical app name or identifier used for wrapper naming.
            flatpak_id: Optional explicit Flatpak ID. If provided, it must
                be a sanitized, safe ID. When omitted, app_id is used as the
                Flatpak ID.
        """
        if not UTILS_AVAILABLE:
            msg = "Python utilities not available"
            raise RuntimeError(msg)

        # Check if app is blocklisted
        if self.is_blocklisted(app_id):
            self.log(f"Skipping blocklisted app: {app_id}", "warning")
            return False

        # Sanitize app ID to create wrapper name
        wrapper_name = sanitize_id_to_name(app_id)
        if not wrapper_name:
            self.log(f"Skipping invalid app ID: {app_id}", "warning")
            return False

        target_flatpak_id = flatpak_id or app_id

        # Basic flatpak ID validation: allow alnum, dot, dash, underscore
        import re

        if not re.match(r"^[A-Za-z0-9._-]+$", target_flatpak_id):
            if flatpak_id is not None:
                self.log(
                    f"Skipping invalid Flatpak ID: {target_flatpak_id}",
                    "warning",
                )
                return False
            # If no explicit flatpak_id was provided, fall back to a sanitized name
            target_flatpak_id = sanitize_id_to_name(app_id)
            if not target_flatpak_id:
                self.log(
                    f"Skipping invalid app ID (unsanitizable): {app_id}",
                    "warning",
                )
                return False

        wrapper_path = self.bin_dir / wrapper_name

        # Check for existing wrapper (handle permission errors gracefully)
        try:
            wrapper_existed = wrapper_path.exists()
        except PermissionError:
            self.log(f"Permission denied accessing {wrapper_path}", "error")
            return False
        if wrapper_existed:
            existing_id = get_wrapper_id(str(wrapper_path)) if UTILS_AVAILABLE else None
            # If the existing file isn't recognized as our wrapper, treat it as a name collision
            if existing_id is None:
                try:
                    # Try reading file to ensure it's a real file and not a mocked path
                    _ = wrapper_path.read_text()
                except Exception as e:
                    # Can't read file (possibly mocked); allow creation
                    self.log(
                        f"Note: Could not verify existing wrapper file: {e}", "info"
                    )
                else:
                    self.log(
                        f"Name collision for '{wrapper_name}': existing file not a wrapper",
                        "warning",
                    )
                    return False
            if existing_id and existing_id != app_id:
                self.log(
                    f"Name collision for '{wrapper_name}': {existing_id} vs {app_id}",
                    "warning",
                )
                return False

        wrapper_content = self.create_wrapper_script(wrapper_name, target_flatpak_id)

        if self.emit_mode:
            # In emit mode, just show what would be done
            action = "Update" if wrapper_existed else "Create"
            self.log(f"EMIT: Would {action.lower()} wrapper: {wrapper_name}")
            self.log(
                f"EMIT: Would write {len(wrapper_content)} bytes to {wrapper_path}",
            )
            self.log(f"EMIT: Would set permissions to 755 on {wrapper_path}")

            # For debugging (tests), indicate emit
            print(f"EMIT MODE active for {wrapper_name}")

            # Show file content if verbose emit mode
            if self.emit_verbose:
                self.log(f"EMIT: File content for {wrapper_path}:")
                # Use Rich panel for better formatting if available
                if console:
                    from rich.panel import Panel

                    console.print(
                        Panel.fit(
                            wrapper_content,
                            title=f"📄 {wrapper_name} wrapper script",
                            border_style="blue",
                        ),
                    )
                    # Also print raw content so redirect_stdout-based tests can capture it
                    print(wrapper_content)
                else:
                    self.log("-" * 50)
                    for i, line in enumerate(wrapper_content.split("\n"), 1):
                        self.log(f"{i:2d}: {line}")
                    self.log("-" * 50)

            return True
        try:
            wrapper_path.write_text(wrapper_content)
            wrapper_path.chmod(0o755)

            if wrapper_existed:
                self.log(f"Updated wrapper: {wrapper_name}")
            else:
                self.log(f"Created wrapper: {wrapper_name}")

            return True

        except Exception as e:
            self.log(f"Failed to create wrapper {wrapper_name}: {e}", "error")
            return False

            return True

        except Exception as e:
            self.log(f"Failed to create wrapper {wrapper_name}: {e}", "error")
            return False

    def create_wrapper_script(self, wrapper_name: str, app_id: str) -> str:
        """Create the content of a wrapper script."""
        return f"""#!/usr/bin/env bash
# Generated by fplaunchwrapper

NAME="{wrapper_name}"
ID="{app_id}"
PREF_DIR="{self.config_dir}"
PREF_FILE="$PREF_DIR/$NAME.pref"
# Hook/script locations
HOOK_DIR="$PREF_DIR/scripts/$NAME"
PRE_SCRIPT="$HOOK_DIR/pre-launch.sh"
POST_SCRIPT="$HOOK_DIR/post-run.sh"
# Load configured script paths from config file if available
CONFIG_SCRIPT_PRE=""
CONFIG_SCRIPT_POST=""
if command -v python3 >/dev/null 2>&1; then
    CONFIG_SCRIPT_PRE=$(python3 -c "
from lib.config_manager import create_config_manager
config = create_config_manager()
prefs = config.get_app_preferences('{wrapper_name}')
print(prefs.pre_launch_script or '')
" 2>/dev/null)
    CONFIG_SCRIPT_POST=$(python3 -c "
from lib.config_manager import create_config_manager
config = create_config_manager()
prefs = config.get_app_preferences('{wrapper_name}')
print(prefs.post_launch_script or '')
" 2>/dev/null)
fi
# Use configured script path if valid
if [ -n "$CONFIG_SCRIPT_PRE" ] && [ -x "$CONFIG_SCRIPT_PRE" ]; then
    PRE_SCRIPT="$CONFIG_SCRIPT_PRE"
fi
if [ -n "$CONFIG_SCRIPT_POST" ] && [ -x "$CONFIG_SCRIPT_POST" ]; then
    POST_SCRIPT="$CONFIG_SCRIPT_POST"
fi
# Load environment variables if present
ENV_FILE="$PREF_DIR/$NAME.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi
SCRIPT_BIN_DIR="{self.bin_dir}"
ONE_SHOT_PREF=""

mkdir -p "$PREF_DIR"

# Interactive check
is_interactive() {{
    [ "${{FPWRAPPER_FORCE:-}}" = "interactive" ] || ([ -t 0 ] && [ -t 1 ] && [ "${{FPWRAPPER_FORCE:-}}" != "desktop" ])
}}

# System binary discovery
set_system_info() {{
    SYSTEM_EXISTS=false
    CMD_PATH=""
    if command -v "$NAME" >/dev/null 2>&1; then
        CMD_PATH=$(command -v "$NAME")
        if [ "$CMD_PATH" != "$SCRIPT_BIN_DIR/$NAME" ]; then
            SYSTEM_EXISTS=true
        else
            CMD_PATH=""
        fi
    fi
}}

# Run single launch
run_single_launch() {{
    local choice="$1"
    shift

    # Run pre-launch script if present
    run_pre_launch_script "$@"

    if [ "$choice" = "system" ]; then
        if [ "$SYSTEM_EXISTS" = true ]; then
            "$NAME" "$@"
            local exit_code=$?
            run_post_launch_script "$exit_code" "system"
            exit "$exit_code"
        else
            echo "System binary not found; falling back to flatpak for this launch." >&2
            flatpak run "$ID" "$@"
            local exit_code=$?
            run_post_launch_script "$exit_code" "flatpak"
            exit "$exit_code"
        fi
    else
        flatpak run "$ID" "$@"
        local exit_code=$?
        run_post_launch_script "$exit_code" "flatpak"
        exit "$exit_code"
    fi
}}

# Pre-launch script execution
run_pre_launch_script() {{
    if [ -x "$PRE_SCRIPT" ]; then
        "$PRE_SCRIPT" "$NAME" "$ID" "$source" "$@"
    fi
}}

# Post-launch script execution
run_post_launch_script() {{
    local exit_code="$1"
    local source="$2"  # "system" or "flatpak"
    
    if [ -x "$POST_SCRIPT" ]; then
        (
            export FPWRAPPER_EXIT_CODE="$exit_code"
            export FPWRAPPER_SOURCE="$source"
            export FPWRAPPER_WRAPPER_NAME="$NAME"
            export FPWRAPPER_APP_ID="$ID"
            "$POST_SCRIPT" "$NAME" "$ID" "$source" "$exit_code" "$@"
        ) 2>&1 || echo "[fplaunchwrapper] Warning: Post-launch script failed with exit code $?" >&2
    fi
}}

set_pre_script() {{
    local script_path="$1"
    if [ -z "$script_path" ]; then
        echo "Usage: $NAME --fpwrapper-set-pre-script <script_path>" >&2
        exit 1
    fi
    if [ ! -f "$script_path" ]; then
        echo "Script not found: $script_path" >&2
        exit 1
    fi
    mkdir -p "$HOOK_DIR"
    cp "$script_path" "$PRE_SCRIPT"
    chmod +x "$PRE_SCRIPT"
    echo "Pre-launch script set to $script_path"
    exit 0
}}

set_post_script() {{
    local script_path="$1"
    if [ -z "$script_path" ]; then
        echo "Usage: $NAME --fpwrapper-set-post-script <script_path>" >&2
        exit 1
    fi
    if [ ! -f "$script_path" ]; then
        echo "Script not found: $script_path" >&2
        exit 1
    fi
    mkdir -p "$HOOK_DIR"
    cp "$script_path" "$POST_SCRIPT"
    chmod +x "$POST_SCRIPT"
    echo "Post-run script set to $script_path"
    exit 0
}}

# One-shot launch
if [ "$1" = "--fpwrapper-launch" ]; then
    if [ -z "$2" ]; then
        echo "Usage: $NAME --fpwrapper-launch [system|flatpak]" >&2
        exit 1
    fi
    case "$2" in
        system|flatpak)
            ONE_SHOT_PREF="$2"
            shift 2
            ;;
        *)
            echo "Invalid choice for --fpwrapper-launch: $2 (use system|flatpak)" >&2
            exit 1
            ;;
    esac
fi

# Force interactive mode
if [ "$1" = "--fpwrapper-force-interactive" ]; then
    FPWRAPPER_FORCE="interactive"
    shift
fi

# Discover system info
set_system_info

# Check for wrapper options first (before interactive logic)
# Help command
if [ "$1" = "--fpwrapper-help" ]; then
    echo "Wrapper for $NAME"
    echo "Flatpak ID: $ID"
    pref=$(cat "$PREF_FILE" 2>/dev/null || echo "none")
    echo "Current preference: $pref"
    echo ""
    echo "Available options:"
    echo "  --help                 Show basic usage"
    echo "  --fpwrapper-help       Show detailed help"
    echo "  --fpwrapper-info       Show wrapper info"
    echo "  --fpwrapper-config-dir Show Flatpak data directory"
    echo "  --fpwrapper-sandbox-info Show Flatpak sandbox details"
    echo "  --fpwrapper-edit-sandbox Edit Flatpak permissions"
    echo "  --fpwrapper-sandbox-yolo Grant all permissions (dangerous)"
    echo "  --fpwrapper-sandbox-reset Reset sandbox to defaults"
    echo "  --fpwrapper-run-unrestricted Run with unrestricted permissions"
    echo "  --fpwrapper-set-override [system|flatpak] Set launch preference"
    echo "  --fpwrapper-set-preference [system|flatpak] Alias for --fpwrapper-set-override"
    echo "  --fpwrapper-launch [system|flatpak] Launch once without saving"
    echo "  --fpwrapper-force-interactive Force interactive mode (even in scripts)"
    echo "  --fpwrapper-set-pre-script <script> Set pre-launch script"
    echo "  --fpwrapper-set-post-script <script> Set post-run script"
    echo "  --fpwrapper-remove-pre-script Remove pre-launch script"
    echo "  --fpwrapper-remove-post-script Remove post-run script"
    exit 0
fi

# Info command
if [ "$1" = "--fpwrapper-info" ]; then
    echo "Wrapper for $NAME"
    echo "Flatpak ID: $ID"
    pref=$(cat "$PREF_FILE" 2>/dev/null || echo "none")
    echo "Preference: $pref"
    echo "Usage: ./$NAME [args]"
    exit 0
fi

# Config directory
if [ "$1" = "--fpwrapper-config-dir" ]; then
    config_dir="${{XDG_DATA_HOME:-$HOME/.local/share}}/applications/$ID"
    echo "$config_dir"
    exit 0
fi

# Sandbox info
if [ "$1" = "--fpwrapper-sandbox-info" ]; then
    if command -v flatpak >/dev/null 2>&1; then
        flatpak info "$ID"
    else
        echo "Flatpak not available"
    fi
    exit 0
fi

# Edit sandbox permissions - Full interactive implementation
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
    FLATSEAL_DECLINED_MARKER="${{XDG_CONFIG_HOME:-$HOME/.config}}/fplaunchwrapper/flatseal_declined"
    
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
    
    # CLI fallback - Interactive permission editor
    echo ""
    echo "=========================================="
    echo "Sandbox Permissions Editor for $ID"
    echo "=========================================="
    echo ""
    
    # Show current overrides
    echo "Current permissions:"
    if flatpak override --show --user "$ID" 2>/dev/null | grep -q "^\\["; then
        flatpak override --show --user "$ID" 2>/dev/null | grep -v "^\\[" || echo "  (none)"
    else
        echo "  (using defaults)"
    fi
    echo ""
    
    # Built-in presets
    PRESET_DEVELOPMENT="--filesystem=home --filesystem=host --device=dri --socket=x11 --socket=wayland --share=ipc"
    PRESET_MEDIA="--device=dri --socket=pulseaudio --socket=wayland --socket=x11 --share=ipc --filesystem=~/Music --filesystem=~/Videos"
    PRESET_NETWORK="--share=network --share=ipc --socket=x11 --socket=wayland"
    PRESET_MINIMAL="--share=ipc"
    PRESET_GAMING="--device=dri --device=input --socket=pulseaudio --socket=wayland --socket=x11 --share=ipc --share=network --filesystem=~/Games"
    PRESET_OFFLINE="--device=dri --socket=pulseaudio --socket=wayland --socket=x11 --share=ipc --filesystem=home"
    
    # Load custom presets from config
    CUSTOM_PRESETS=()
    if command -v python3 >/dev/null 2>&1; then
        while IFS= read -r preset_name; do
            [ -n "$preset_name" ] && CUSTOM_PRESETS+=("$preset_name")
        done < <(python3 -m fplaunch.config_manager list-presets 2>/dev/null)
    fi
    
    # Display menu
    echo "Select an option:"
    echo "  1) Manual entry (line-by-line)"
    echo "  2) Apply preset: Development (filesystem access, graphics)"
    echo "  3) Apply preset: Media (audio/video/graphics)"
    echo "  4) Apply preset: Network (networking + IPC)"
    echo "  5) Apply preset: Minimal (IPC only)"
    echo "  6) Apply preset: Gaming (graphics, input, audio, network)"
    echo "  7) Apply preset: Offline (local files, graphics, audio)"
    echo "  8) Remove specific permission"
    
    menu_option=9
    for custom_preset in "${{CUSTOM_PRESETS[@]}}"; do
        echo "  $menu_option) Apply custom preset: $custom_preset"
        ((menu_option++))
    done
    
    echo "  $menu_option) Show current overrides"
    ((menu_option++))
    echo "  $menu_option) Reset to defaults"
    ((menu_option++))
    echo "  $menu_option) Cancel"
    echo ""
    
    read -r -p "Choose option: " choice
    
    case "$choice" in
        1)
            # Manual entry
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
            echo ""
            
            PERMISSIONS=()
            while true; do
                read -r -p "Permission: " perm
                [ -z "$perm" ] && break
                
                # Validate format
                if [[ "$perm" =~ ^--[a-z-]+(=.+)?$ ]]; then
                    PERMISSIONS+=("$perm")
                else
                    echo "  Warning: Invalid format (must start with --, e.g., --filesystem=home)"
                fi
            done
            
            if [ ${{#PERMISSIONS[@]}} -eq 0 ]; then
                echo "No permissions entered."
                exit 0
            fi
            
            echo ""
            echo "Permissions to apply:"
            printf '  %s\\n' "${{PERMISSIONS[@]}}"
            echo ""
            read -r -p "Apply these ${{#PERMISSIONS[@]}} permissions? [y/N] " confirm
            
            if [[ "$confirm" =~ ^[yY]$ ]]; then
                for perm in "${{PERMISSIONS[@]}}"; do
                    if flatpak override --user "$ID" "$perm" 2>/dev/null; then
                        echo "  ✓ Applied: $perm"
                    else
                        echo "  ✗ Failed: $perm"
                    fi
                done
                echo ""
                echo "Permissions updated. Final state:"
                flatpak override --show --user "$ID" 2>/dev/null | grep -v "^\\[" || echo "  (none)"
            else
                echo "Cancelled."
            fi
            ;;
        2|3|4|5|6|7)
            # Built-in presets
            case "$choice" in
                2) PRESET_NAME="Development"; PRESET_PERMS=($PRESET_DEVELOPMENT) ;;
                3) PRESET_NAME="Media"; PRESET_PERMS=($PRESET_MEDIA) ;;
                4) PRESET_NAME="Network"; PRESET_PERMS=($PRESET_NETWORK) ;;
                5) PRESET_NAME="Minimal"; PRESET_PERMS=($PRESET_MINIMAL) ;;
                6) PRESET_NAME="Gaming"; PRESET_PERMS=($PRESET_GAMING) ;;
                7) PRESET_NAME="Offline"; PRESET_PERMS=($PRESET_OFFLINE) ;;
            esac
            
            echo ""
            echo "Preset: $PRESET_NAME"
            echo "Permissions:"
            printf '  %s\\n' "${{PRESET_PERMS[@]}}"
            echo ""
            read -r -p "Apply these ${{#PRESET_PERMS[@]}} permissions? [y/N] " confirm
            
            if [[ "$confirm" =~ ^[yY]$ ]]; then
                for perm in "${{PRESET_PERMS[@]}}"; do
                    if flatpak override --user "$ID" "$perm" 2>/dev/null; then
                        echo "  ✓ Applied: $perm"
                    else
                        echo "  ✗ Failed: $perm"
                    fi
                done
                echo ""
                echo "Permissions updated. Final state:"
                flatpak override --show --user "$ID" 2>/dev/null | grep -v "^\[" || echo "  (none)"
            else
                echo "Cancelled."
            fi
            ;;
        8)
            # Remove specific permission
            echo ""
            echo "Current permissions to remove:"
            CURRENT_PERMS=$(flatpak override --show --user "$ID" 2>&1 | grep -v "^\[" | grep -v "No overrides" | awk '{{print $$1}}')
            
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
                PERM_TO_REMOVE=$(echo "$CURRENT_PERMS" | sed -n "${{perm_number}}p")
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
            ;;
        *)
            # Check if it's a custom preset
            custom_index=$((choice - 9))
            if [ "$custom_index" -ge 0 ] && [ "$custom_index" -lt ${{#CUSTOM_PRESETS[@]}} ]; then
                PRESET_NAME="${{CUSTOM_PRESETS[$custom_index]}}"
                
                # Load preset permissions
                PRESET_PERMS=()
                if command -v python3 >/dev/null 2>&1; then
                    while IFS= read -r perm; do
                        [ -n "$perm" ] && PRESET_PERMS+=("$perm")
                    done < <(python3 -m fplaunch.config_manager get-preset "$PRESET_NAME" 2>/dev/null)
                fi
                
                if [ ${{#PRESET_PERMS[@]}} -eq 0 ]; then
                    echo "Failed to load preset: $PRESET_NAME"
                    exit 1
                fi
                
                echo ""
                echo "Custom preset: $PRESET_NAME"
                echo "Permissions:"
                printf '  %s\\n' "${{PRESET_PERMS[@]}}"
                echo ""
                read -r -p "Apply these ${{#PRESET_PERMS[@]}} permissions? [y/N] " confirm
                
                if [[ "$confirm" =~ ^[yY]$ ]]; then
                    for perm in "${{PRESET_PERMS[@]}}"; do
                        if flatpak override --user "$ID" "$perm" 2>/dev/null; then
                            echo "  ✓ Applied: $perm"
                        else
                            echo "  ✗ Failed: $perm"
                        fi
                    done
                    echo ""
                    echo "Permissions updated. Final state:"
                    flatpak override --show --user "$ID" 2>/dev/null | grep -v "^\\[" || echo "  (none)"
                else
                    echo "Cancelled."
                fi
            elif [ "$choice" = "$((menu_option - 3))" ]; then
                # Show current overrides
                echo ""
                echo "Current overrides for $ID:"
                flatpak override --show --user "$ID" 2>/dev/null || echo "  (using defaults)"
            elif [ "$choice" = "$((menu_option - 2))" ]; then
                # Reset to defaults
                echo ""
                echo "Current overrides:"
                flatpak override --show --user "$ID" 2>/dev/null | grep -v "^\\[" || echo "  (none)"
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

# Manage hook scripts
if [ "$1" = "--fpwrapper-set-pre-script" ]; then
    set_pre_script "$2"
fi

if [ "$1" = "--fpwrapper-set-post-script" ]; then
    set_post_script "$2"
fi

if [ "$1" = "--fpwrapper-remove-pre-script" ]; then
    if [ -f "$PRE_SCRIPT" ]; then
        rm "$PRE_SCRIPT"
        echo "Pre-launch script removed"
    else
        echo "No pre-launch script configured"
    fi
    exit 0
fi

if [ "$1" = "--fpwrapper-remove-post-script" ]; then
    if [ -f "$POST_SCRIPT" ]; then
        rm "$POST_SCRIPT"
        echo "Post-run script removed"
    else
        echo "No post-run script configured"
    fi
    exit 0
fi

# Set override (allow alias for preference)
if [ "$1" = "--fpwrapper-set-override" ] || [ "$1" = "--fpwrapper-set-preference" ]; then
    if [ -z "$2" ]; then
        echo "Usage: $0 --fpwrapper-set-override [system|flatpak]" >&2
        exit 1
    fi
    case "$2" in
        system|flatpak)
            echo "$2" > "$PREF_FILE"
            echo "Preference set to: $2"
            exit 0
            ;;
        *)
            echo "Invalid preference: $2 (use system|flatpak)" >&2
            exit 1
            ;;
    esac
fi

# Sandbox reset
if [ "$1" = "--fpwrapper-sandbox-reset" ]; then
    if command -v flatpak >/dev/null 2>&1; then
        flatpak override --reset "$ID"
        echo "Sandbox reset to defaults"
    else
        echo "Flatpak not available - would reset sandbox"
    fi
    exit 0
fi

# Sandbox yolo
if [ "$1" = "--fpwrapper-sandbox-yolo" ]; then
    if command -v flatpak >/dev/null 2>&1; then
        # Check if interactive (for safety warning)
        if is_interactive; then
            echo ""
            echo "⚠️  WARNING: YOLO mode grants ALL possible permissions!"
            echo "This completely disables the Flatpak sandbox and is extremely dangerous."
            echo "Only use this if you trust the application completely."
            echo ""
            read -r -p "Type 'YES' to confirm (case-sensitive): " confirm
            if [ "$confirm" != "YES" ]; then
                echo "Cancelled YOLO mode"
                exit 0
            fi
        fi
        
        # Apply all possible permissions
        flatpak override --user "$ID" \
            --filesystem=host \
            --device=all \
            --share=all \
            --socket=all \
            --system-talk-name= \
            --talk-name=
        echo "YOLO mode applied - ALL permissions granted (sandbox disabled)"
    else
        echo "Flatpak not available - would grant all permissions"
    fi
    exit 0
fi

# Run unrestricted
if [ "$1" = "--fpwrapper-run-unrestricted" ]; then
    if command -v flatpak >/dev/null 2>&1; then
        shift
        exec flatpak run --no-sandbox "$ID" "$@"
    else
        echo "Flatpak not available - would run unrestricted"
        exit 0
    fi
fi

# Non-interactive bypass
if ! is_interactive; then
    if [ -n "$ONE_SHOT_PREF" ]; then
        run_single_launch "$ONE_SHOT_PREF" "$@"
    fi

    # Ensure pre-launch hooks run in non-interactive flows
    run_pre_launch_script "$@"

    # Find next executable in PATH
    IFS=: read -ra PATH_DIRS <<< "$PATH"
    for dir in "${{PATH_DIRS[@]}}"; do
        [ -z "$dir" ] && continue
        if [ -x "$dir/$NAME" ] && [ "$dir/$NAME" != "$SCRIPT_BIN_DIR/$NAME" ]; then
            "$dir/$NAME" "$@"
            exit_code=$?
            run_post_launch_script "$exit_code" "system"
            exit "$exit_code"
        fi
    done

    # Run flatpak
    run_pre_launch_script "$@"
    flatpak run "$ID" "$@"
    exit_code=$?
    run_post_launch_script "$exit_code" "flatpak"
    exit "$exit_code"
fi

# For now, just run the interactive logic

# Load preference
if [ -f "$PREF_FILE" ]; then
    PREF=$(cat "$PREF_FILE")
else
    PREF=""
fi

# Check for system command
SYSTEM_EXISTS=false
CMD_PATH=""
if command -v "$NAME" >/dev/null 2>&1; then
    CMD_PATH=$(command -v "$NAME")
    [ "$CMD_PATH" != "$SCRIPT_BIN_DIR/$NAME" ] && SYSTEM_EXISTS=true
fi

# Interactive launch logic
if [ "$PREF" = "system" ]; then
    if [ "$SYSTEM_EXISTS" = true ]; then
        run_pre_launch_script "$@"
        "$NAME" "$@"
        exit_code=$?
        run_post_launch_script "$exit_code" "system"
        exit "$exit_code"
    else
        # System command gone, fall back to flatpak
        echo "flatpak" > "$PREF_FILE"
        run_pre_launch_script "$@"
        flatpak run "$ID" "$@"
        exit_code=$?
        run_post_launch_script "$exit_code" "flatpak"
        exit "$exit_code"
    fi
elif [ "$PREF" = "flatpak" ]; then
    run_pre_launch_script "$@"
    flatpak run "$ID" "$@"
    exit_code=$?
    run_post_launch_script "$exit_code" "flatpak"
    exit "$exit_code"
else
    # No preference set - show interactive prompt
    if is_interactive && [ "$SYSTEM_EXISTS" = true ]; then
        echo "Multiple options for '$NAME':"
        echo "1. System package ($CMD_PATH)"
        echo "2. Flatpak app ($ID)"
        echo ""
        read -r -p "Choose (1/2, default 1): " choice
        choice=${{choice:-1}}

        if [ "$choice" = "1" ]; then
            PREF="system"
        elif [ "$choice" = "2" ]; then
            PREF="flatpak"
        else
            echo "Invalid choice '$choice', using default: system"
            PREF="system"
        fi

        echo "$PREF" > "$PREF_FILE"
        run_pre_launch_script "$@"
        if [ "$PREF" = "system" ]; then
            "$NAME" "$@"
        else
            flatpak run "$ID" "$@"
        fi
        exit_code=$?
        run_post_launch_script "$exit_code" "$PREF"
        exit "$exit_code"
    else
        # Non-interactive or only flatpak available
        if [ "$SYSTEM_EXISTS" = true ]; then
            PREF="system"
            echo "$PREF" > "$PREF_FILE"
            run_pre_launch_script "$@"
            "$NAME" "$@"
            exit_code=$?
            run_post_launch_script "$exit_code" "system"
            exit "$exit_code"
        else
            PREF="flatpak"
            echo "$PREF" > "$PREF_FILE"
            run_pre_launch_script "$@"
            flatpak run "$ID" "$@"
            exit_code=$?
            run_post_launch_script "$exit_code" "flatpak"
            exit "$exit_code"
        fi
    fi
fi
"""

    def generate_all_wrappers(self, installed_apps: list[str]) -> tuple[int, int, int]:
        """Generate wrappers for all installed applications."""
        self.log("Generating wrappers...")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        # Use progress bar if rich is available
        if console and not self.verbose:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "Generating wrappers...",
                    total=len(installed_apps),
                )

                for app_id in installed_apps:
                    if self.generate_wrapper(app_id):
                        # Check if it was an update or create
                        wrapper_name = (
                            sanitize_id_to_name(app_id)
                            if UTILS_AVAILABLE
                            else app_id.split(".")[-1]
                        )
                        self.bin_dir / wrapper_name
                        # For now, assume it's a create (we'd need to track this)
                        created_count += 1
                    else:
                        skipped_count += 1
                    progress.update(task, advance=1)
        else:
            for app_id in installed_apps:
                if self.generate_wrapper(app_id):
                    created_count += 1
                else:
                    skipped_count += 1

        return created_count, updated_count, skipped_count

    def run(self) -> int:
        """Main generation process."""
        try:
            # Acquire lock (skip in emit mode)
            if not self.emit_mode and not acquire_lock(self.lock_name, 30):
                self.log("Failed to acquire generation lock", "error")
                return 1

            try:
                # Get installed applications
                installed_apps = self.get_installed_flatpaks()
                app_count = len(installed_apps)
                self.log(f"Found {app_count} Flatpak applications")

                if app_count == 0:
                    self.log(
                        "No Flatpak applications found. Install some with: flatpak install <app>",
                        "warning",
                    )
                    return 1

                # Clean up obsolete wrappers
                removed_count = self.cleanup_obsolete_wrappers(installed_apps)

                # Generate new wrappers
                created_count, updated_count, skipped_count = self.generate_wrappers(
                    installed_apps,
                )

                # Summary
                self.log("")
                self.log("📊 Generation Summary:")
                self.log(f"   ✅ Created: {created_count} new wrappers")
                self.log(f"   🔄 Updated: {updated_count} existing wrappers")
                self.log(f"   🚫 Skipped: {skipped_count} applications")
                if removed_count > 0:
                    self.log(f"   🗑️  Removed: {removed_count} obsolete wrappers")

                self.log("")
                self.log("🎉 Flatpak wrapper generation complete!")
                self.log("")
                self.log("💡 Next steps:")
                self.log("   fplaunch list              # See your wrappers")
                self.log("   fplaunch monitor           # Monitor for changes")
                self.log("   firefox --fpwrapper-help   # See wrapper options")

                return 0

            finally:
                if not self.emit_mode:
                    release_lock(self.lock_name)

        except Exception as e:
            self.log(f"Generation failed: {e}", "error")

            # Send failure notification if notifications are enabled
            try:
                from lib.config_manager import create_config_manager
                from lib.notifications import send_update_failure_notification

                config = create_config_manager()
                if config.get_enable_notifications():
                    send_update_failure_notification(str(e))
            except Exception:
                # Ignore any errors in notification system
                pass

            return 1

    def generate_wrappers(self, installed_apps: list[str]) -> tuple[int, int, int]:
        """Generate wrappers for all apps - alias for generate_all_wrappers."""
        return self.generate_all_wrappers(installed_apps)


def main():
    """Command-line interface for wrapper generation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Flatpak application wrappers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m generate /home/user/bin        # Generate in specific directory
  python -m generate --verbose ~/bin       # Verbose output
  python -m generate $HOME/.local/bin      # Use local bin directory
  python -m generate --emit ~/bin          # Show what would be done
        """,
    )

    parser.add_argument(
        "bin_dir",
        nargs="?",
        default=os.path.expanduser("~/bin"),
        help="Directory to store wrapper scripts (default: ~/bin)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of all wrappers",
    )

    parser.add_argument(
        "--emit",
        action="store_true",
        help="Emit commands instead of executing (dry run)",
    )

    args = parser.parse_args()

    # Validate bin directory (skip in emit mode)
    if not args.emit:
        bin_dir = os.path.expanduser(args.bin_dir)
        if not validate_home_dir(bin_dir) if UTILS_AVAILABLE else True:
            return 1

    # Create generator and run
    generator = WrapperGenerator(args.bin_dir, args.verbose, args.emit)
    return generator.run()


if __name__ == "__main__":
    sys.exit(main())
