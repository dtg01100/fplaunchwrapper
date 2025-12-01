#!/usr/bin/env bash

# ⚠️  DANGER: ADVERSARIAL FPLAUNCHWRAPPER TEST SUITE ⚠️
# 
# This test suite ATTACKS fplaunchwrapper code to find security vulnerabilities.
# It tests if our project properly blocks attacks and validates inputs.
# 
# ⚠️  WARNING: This test is UNSAFE and should ONLY be run in:
#   - Isolated development environments
#   - Dedicated testing containers
#   - Systems you are authorized to penetration test
#   - NEVER on production systems or user workstations
#
# ⚠️  RISKS: This test may:
#   - Execute malicious inputs through fplaunchwrapper
#   - Test fplaunchwrapper security boundaries
#   - Attempt to bypass fplaunchwrapper protections
#   - Create temporary attack artifacts
#   - Leave residual test files
#
# ⚠️  REQUIREMENTS:
#   - Run in isolated environment (VM/container recommended)
#   - NEVER run as root
#   - Backup your system before running
#   - Monitor system during execution

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0
ATTACKS_BLOCKED=0
VULNERABILITIES_FOUND=0

pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo -e "${RED}✗${NC} $1 - VULNERABILITY!"
    FAILED=$((FAILED + 1))
    VULNERABILITIES_FOUND=$((VULNERABILITIES_FOUND + 1))
}

attack() {
    echo -e "${PURPLE}[ATTACK]${NC} $1"
}

defense() {
    echo -e "${GREEN}[DEFENSE]${NC} $1"
    ATTACKS_BLOCKED=$((ATTACKS_BLOCKED + 1))
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# ⚠️  SAFETY CONFIRMATION ⚠️
echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║          ⚠️  FPLAUNCHWRAPPER ADVERSARIAL TEST WARNING  ⚠️         ║${NC}"
echo -e "${RED}╠══════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${RED}║ This test will ATTACK fplaunchwrapper code to find vulnerabilities. ║${NC}"
echo -e "${RED}║ It tests if our project properly blocks malicious inputs.          ║${NC}"
echo -e "${RED}║ ONLY run in isolated environments you are authorized to test.        ║${NC}"
echo -e "${RED}║ NEVER run on production systems or user workstations.              ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Interactive confirmation
read -r -p "Do you understand the risks and want to proceed? (type 'I UNDERSTAND THE RISKS'): " confirmation
if [ "$confirmation" != "I UNDERSTAND THE RISKS" ]; then
    echo -e "${RED}Adversarial test cancelled. Confirmation not provided.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}⚠️  Proceeding with fplaunchwrapper adversarial testing...${NC}"
echo ""

# Developer workstation safety check - NEVER run as root
if [ "$(id -u)" = "0" ] && ! is_ci && [ "${TESTING:-}" != "1" ]; then
    echo -e "${RED}ERROR: Refusing to run adversarial tests as root${NC}"
    echo -e "${RED}These tests are designed to find vulnerabilities - running as root is dangerous${NC}"
    exit 1
fi

# Set testing environment
export TESTING=1
export CI=1

# Create isolated test environment
setup_adversarial_env() {
    local test_home="/tmp/fplaunch-adversarial-test-$$"
    
    # Clean up any existing test directory
    rm -rf "$test_home"
    
    # Create test directory structure
    mkdir -p "$test_home"/{bin,.config,.local/share/applications,attack-vectors}
    
    # Override environment for test isolation
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
    export XDG_DATA_HOME="$test_home/.local/share"
    export PATH="$test_home/bin:$PATH"
    
    # Source fplaunchwrapper libraries for testing
    # shellcheck source=../../lib/common.sh disable=SC1091
    source "$PROJECT_ROOT/lib/common.sh"
    # shellcheck source=../../lib/wrapper.sh disable=SC1091
    source "$PROJECT_ROOT/lib/wrapper.sh"
    # shellcheck source=../../lib/pref.sh disable=SC1091
    source "$PROJECT_ROOT/lib/pref.sh"
    # shellcheck source=../../lib/env.sh disable=SC1091
    source "$PROJECT_ROOT/lib/env.sh"
    # shellcheck source=../../lib/alias.sh disable=SC1091
    source "$PROJECT_ROOT/lib/alias.sh"
    
    # Create mock flatpak command
    cat > "$test_home/bin/flatpak" << 'EOF'
#!/usr/bin/env bash
echo "Mock flatpak called with: $*" >> "$HOME/attack-log.txt"
case "$1" in
    "list")
        echo "com.test.App"
        echo "com.evil.MaliciousApp"
        echo "com.normal.NormalApp"
        ;;
    "run")
        echo "Mock flatpak run $*"
        exit 0
        ;;
    "info")
        echo "Mock flatpak info for $2"
        exit 0
        ;;
    *)
        echo "Mock flatpak $*"
        exit 0
        ;;
esac
EOF
    chmod +x "$test_home/bin/flatpak"
    
    # Create attack log
    touch "$test_home/attack-log.txt"
    
    echo "$test_home"
}

# Cleanup test environment
cleanup_adversarial_env() {
    local test_home="$1"
    # Show attack summary before cleanup
    if [ -f "$test_home/attack-log.txt" ]; then
        echo ""
        attack "fplaunchwrapper calls logged:"
        cat "$test_home/attack-log.txt" | sed 's/^/  /'
    fi
    rm -rf "$test_home"
}

# ATTACK 1: Test validate_home_dir function against attacks
test_validate_home_dir_attacks() {
    local test_home="$1"
    
    attack "Testing validate_home_dir function against attacks"
    
    # Test 1: Path traversal attack
    if validate_home_dir "/home/user/../../../etc" "test" 2>/dev/null; then
        fail "validate_home_dir allows path traversal"
    else
        defense "validate_home_dir blocks path traversal"
    fi
    
    # Test 2: Symlink attack
    ln -sf /etc "$test_home/symlink-etc"
    if validate_home_dir "$test_home/symlink-etc" "test" 2>/dev/null; then
        fail "validate_home_dir allows symlink to system directory"
    else
        defense "validate_home_dir blocks symlink to system directory"
    fi
    
    # Test 3: Null byte injection
    if validate_home_dir "/home/user/passwd\x00" "test" 2>/dev/null; then
        fail "validate_home_dir allows null byte injection"
    else
        defense "validate_home_dir blocks null byte injection"
    fi
    
    # Test 4: URL-encoded path traversal
    if validate_home_dir "/home/user/%2e%2e%2f%2e%2e%2f%2e%2fetc" "test" 2>/dev/null; then
        fail "validate_home_dir allows URL-encoded path traversal"
    else
        defense "validate_home_dir blocks URL-encoded path traversal"
    fi
}

# ATTACK 2: Test is_wrapper_file function against attacks
test_is_wrapper_file_attacks() {
    local test_home="$1"
    
    attack "Testing is_wrapper_file function against attacks"
    
    # Test 1: Non-file input
    if is_wrapper_file "/dev/null" 2>/dev/null; then
        fail "is_wrapper_file accepts non-file input"
    else
        defense "is_wrapper_file rejects non-file input"
    fi
    
    # Test 2: Symlink attack
    echo "Not a wrapper" > "$test_home/normal-file"
    ln -sf "$test_home/normal-file" "$test_home/wrapper-symlink"
    if is_wrapper_file "$test_home/wrapper-symlink" 2>/dev/null; then
        fail "is_wrapper_file accepts symlink to non-wrapper"
    else
        defense "is_wrapper_file rejects symlink to non-wrapper"
    fi
    
    # Test 3: Empty file
    touch "$test_home/empty-file"
    if is_wrapper_file "$test_home/empty-file" 2>/dev/null; then
        fail "is_wrapper_file accepts empty file"
    else
        defense "is_wrapper_file rejects empty file"
    fi
}

# ATTACK 3: Test wrapper generation against malicious inputs
test_wrapper_generation_attacks() {
    local test_home="$1"
    
    attack "Testing wrapper generation against malicious inputs"
    
    # Test 1: Command injection in app name
    local malicious_app="testapp; rm -rf /tmp/*"
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        # Check if malicious command was executed
        if [ -f "$test_home/bin/$malicious_app" ]; then
            fail "Wrapper generation allows command injection in app name"
        else
            defense "Wrapper generation blocks command injection in app name"
        fi
    else
        defense "Wrapper generation fails on malicious input"
    fi
    
    # Test 2: Path traversal in bin directory
    if fplaunch-generate "../../../bin" 2>/dev/null; then
        fail "Wrapper generation allows path traversal in bin directory"
    else
        defense "Wrapper generation blocks path traversal in bin directory"
    fi
    
    # Test 3: Extremely long app name
    local long_name
    long_name=$(printf 'A%.0s' {1..1000})
    # Create mock flatpak with long name
    echo "com.test.$long_name" > "$test_home/mock-flatpak-list"
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        fail "Wrapper generation allows extremely long app names"
    else
        defense "Wrapper generation blocks extremely long app names"
    fi
}

# ATTACK 4: Test preference management against attacks
test_preference_management_attacks() {
    local test_home="$1"
    
    attack "Testing preference management against attacks"
    
    # Test 1: Command injection in preference value
    local malicious_pref="system; rm -rf /tmp/*"
    if set_pref "testapp" "$malicious_pref" 2>/dev/null; then
        # Check if malicious command was executed
        if [ -f "$test_home/.config/flatpak-wrappers/testapp.pref" ]; then
            local pref_content
            pref_content=$(cat "$test_home/.config/flatpak-wrappers/testapp.pref")
            if echo "$pref_content" | grep -q "rm -rf"; then
                fail "Preference management allows command injection"
            else
                defense "Preference management blocks command injection"
            fi
        fi
    else
        defense "Preference management rejects malicious input"
    fi
    
    # Test 2: Path traversal in app name
    if set_pref "../../../etc/testapp" "system" 2>/dev/null; then
        if [ -f "/etc/testapp.pref" ]; then
            fail "Preference management allows path traversal in app name"
        else
            defense "Preference management blocks path traversal in app name"
        fi
    else
        defense "Preference management rejects path traversal in app name"
    fi
    
    # Test 3: Null byte injection in preference value
    if set_pref "testapp" "system\x00malicious" 2>/dev/null; then
        local pref_content
        pref_content=$(cat "$test_home/.config/flatpak-wrappers/testapp.pref" 2>/dev/null || echo "")
        if echo "$pref_content" | grep -q "malicious"; then
            fail "Preference management allows null byte injection"
        else
            defense "Preference management blocks null byte injection"
        fi
    else
        defense "Preference management rejects null byte injection"
    fi
}

# ATTACK 5: Test environment variable management against attacks
test_env_var_management_attacks() {
    local test_home="$1"
    
    attack "Testing environment variable management against attacks"
    
    # Test 1: Command injection in env var value
    local malicious_env="PATH=/tmp; rm -rf /tmp/*"
    if set_env "testapp" "MALICIOUS_VAR" "$malicious_env" 2>/dev/null; then
        # Check if malicious command was executed
        if [ -f "$test_home/.config/flatpak-wrappers/testapp.env" ]; then
            local env_content
            env_content=$(cat "$test_home/.config/flatpak-wrappers/testapp.env")
            if echo "$env_content" | grep -q "rm -rf"; then
                fail "Environment variable management allows command injection"
            else
                defense "Environment variable management blocks command injection"
            fi
        fi
    else
        defense "Environment variable management rejects malicious input"
    fi
    
    # Test 2: Path traversal in app name
    if set_env "../../../etc/testapp" "VAR" "value" 2>/dev/null; then
        if [ -f "/etc/testapp.env" ]; then
            fail "Environment variable management allows path traversal in app name"
        else
            defense "Environment variable management blocks path traversal in app name"
        fi
    else
        defense "Environment variable management rejects path traversal in app name"
    fi
    
    # Test 3: Shell metacharacter injection
    if set_env "testapp" "TEST_VAR" '`whoami`' 2>/dev/null; then
        local env_content
        env_content=$(cat "$test_home/.config/flatpak-wrappers/testapp.env" 2>/dev/null || echo "")
        if echo "$env_content" | grep -q "whoami"; then
            fail "Environment variable management allows shell metacharacter injection"
        else
            defense "Environment variable management blocks shell metacharacter injection"
        fi
    else
        defense "Environment variable management rejects shell metacharacter injection"
    fi
}

# ATTACK 6: Test alias management against attacks
test_alias_management_attacks() {
    local test_home="$1"
    
    attack "Testing alias management against attacks"
    
    # Test 1: Command injection in alias target
    local malicious_target="system; rm -rf /tmp/*"
    if set_alias "testapp" "$malicious_target" 2>/dev/null; then
        # Check if malicious command was executed
        if [ -f "$test_home/.config/flatpak-wrappers/aliases" ]; then
            local alias_content
            alias_content=$(cat "$test_home/.config/flatpak-wrappers/aliases")
            if echo "$alias_content" | grep -q "rm -rf"; then
                fail "Alias management allows command injection"
            else
                defense "Alias management blocks command injection"
            fi
        fi
    else
        defense "Alias management rejects malicious input"
    fi
    
    # Test 2: Path traversal in alias name
    if set_alias "../../../etc/testapp" "target" 2>/dev/null; then
        if grep -q "../../../etc/testapp" "$test_home/.config/flatpak-wrappers/aliases"; then
            fail "Alias management allows path traversal in alias name"
        else
            defense "Alias management blocks path traversal in alias name"
        fi
    else
        defense "Alias management rejects path traversal in alias name"
    fi
    
    # Test 3: Alias cycle attack
    if set_alias "testapp1" "testapp2" 2>/dev/null && set_alias "testapp2" "testapp1" 2>/dev/null; then
        # Test if cycle is detected
        local alias_output
        alias_output=$(list_env "testapp1" 2>/dev/null || echo "")
        if [ -n "$alias_output" ]; then
            fail "Alias management allows infinite cycles"
        else
            defense "Alias management prevents infinite cycles"
        fi
    else
        defense "Alias management rejects cycle creation"
    fi
}

# ATTACK 7: Test wrapper script generation against attacks
test_wrapper_script_attacks() {
    local test_home="$1"
    
    attack "Testing wrapper script generation against attacks"
    
    # Test 1: Malicious app ID injection
    local malicious_id="com.test.App'; rm -rf /tmp/*; echo '"
    # Create mock flatpak output
    echo "$malicious_id" > "$test_home/mock-flatpak-list"
    
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        # Check generated wrapper for malicious content
        local wrapper_file
        wrapper_file=$(find "$test_home/bin" -name "*" -type f | head -1)
        if [ -f "$wrapper_file" ]; then
            if grep -q "rm -rf" "$wrapper_file"; then
                fail "Wrapper script generation allows malicious app ID injection"
            else
                defense "Wrapper script generation blocks malicious app ID injection"
            fi
        fi
    else
        defense "Wrapper script generation rejects malicious app ID"
    fi
    
    # Test 2: Script injection in app name
    local script_name
    # shellcheck disable=SC2034
    script_name=$(echo 'malicious; cat /etc/passwd' | tr -d '\n')
    echo "com.test.App" > "$test_home/mock-flatpak-list"
    
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        # Check if script name was sanitized
        local wrapper_files
        wrapper_files=$(find "$test_home/bin" -name "*" -type f)
        if echo "$wrapper_files" | grep -q "malicious"; then
            fail "Wrapper script generation allows script injection in name"
        else
            defense "Wrapper script generation blocks script injection in name"
        fi
    else
        defense "Wrapper script generation rejects script injection"
    fi
}

# ATTACK 8: Test installation scripts against attacks
test_installation_script_attacks() {
    local test_home="$1"
    
    attack "Testing installation scripts against attacks"
    
    # Test 1: Malicious BIN_DIR injection
    local malicious_bin="/tmp; rm -rf /tmp/*"
    if BIN_DIR="$malicious_bin" fplaunch-generate 2>/dev/null; then
        # Check if malicious command was executed
        if [ ! -d "/tmp" ] || [ -f "/tmp/malicious" ]; then
            fail "Installation allows malicious BIN_DIR injection"
        else
            defense "Installation blocks malicious BIN_DIR injection"
        fi
    else
        defense "Installation rejects malicious BIN_DIR"
    fi
    
    # Test 2: Path traversal in installation directory
    if fplaunch-generate "../../../bin" 2>/dev/null; then
        if [ -f "/bin/wrapper" ]; then
            fail "Installation allows path traversal in directory"
        else
            defense "Installation blocks path traversal in directory"
        fi
    else
        defense "Installation rejects path traversal in directory"
    fi
    
    # Test 3: Environment variable poisoning during installation
    HOME="/etc" fplaunch-generate "$test_home/bin" 2>/dev/null
    if [ -f "/etc/bin/wrapper" ]; then
        fail "Installation allows HOME poisoning"
    else
        defense "Installation blocks HOME poisoning"
    fi
}

# ATTACK 9: Test cleanup functions against attacks
test_cleanup_function_attacks() {
    local test_home="$1"
    
    attack "Testing cleanup functions against attacks"
    
    # Test 1: Malicious config directory
    local malicious_config="/etc; rm -rf /tmp/*"
    CONFIG_DIR="$malicious_config" cleanup_systemd_units 2>/dev/null
    if [ -f "/etc/fplaunch-update.service" ]; then
        fail "Cleanup allows malicious CONFIG_DIR injection"
    else
        defense "Cleanup blocks malicious CONFIG_DIR injection"
    fi
    
    # Test 2: Path traversal in cleanup
    cleanup_systemd_units "../../../etc" 2>/dev/null
    if [ -f "/etc/fplaunch-update.service" ]; then
        fail "Cleanup allows path traversal"
    else
        defense "Cleanup blocks path traversal"
    fi
    
    # Test 3: Symlink attack in cleanup
    ln -sf /etc "$test_home/fake-config"
    CONFIG_DIR="$test_home/fake-config" cleanup_systemd_units 2>/dev/null
    if [ -f "/etc/fplaunch-update.service" ]; then
        fail "Cleanup allows symlink attack"
    else
        defense "Cleanup blocks symlink attack"
    fi
}

# ATTACK 10: Test wrapper execution against attacks
test_wrapper_execution_attacks() {
    local test_home="$1"
    
    attack "Testing wrapper execution against attacks"
    
    # Create a test wrapper
    cat > "$test_home/bin/testapp" << 'EOF'
#!/usr/bin/env bash
# Generated by fplaunchwrapper

NAME="testapp"
ID="com.test.App"
PREF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/flatpak-wrappers"
PREF_FILE="$PREF_DIR/$NAME.pref"
SCRIPT_BIN_DIR="$test_home/bin"

mkdir -p "$PREF_DIR"

# Check if running in interactive CLI
is_interactive() {
    [ "${FPWRAPPER_FORCE:-}" = "interactive" ] || ([ -t 0 ] && [ -t 1 ] && [ "${FPWRAPPER_FORCE:-}" != "desktop" ])
}

# Check for force flag for testing
if [ "$1" = "--fpwrapper-force-interactive" ]; then
    export FPWRAPPER_FORCE=interactive
    shift
fi

# Non-interactive bypass: skip wrapper and continue PATH search
if ! is_interactive; then
    # Find next executable in PATH (skip our wrapper)
    IFS=: read -ra PATH_DIRS <<< "$PATH"
    for dir in "${PATH_DIRS[@]}"; do
        if [ -x "$dir/$NAME" ] && [ "$dir/$NAME" != "$SCRIPT_BIN_DIR/$NAME" ]; then
            exec "$dir/$NAME" "$@"
        fi
    done
    
    # If no system command found, run flatpak
    exec flatpak run "$ID" "$@"
fi

if [ "$1" = "--fpwrapper-help" ]; then
    echo "Wrapper for $NAME"
    echo "Flatpak ID: $ID"
    pref=$(cat "$PREF_FILE" 2>/dev/null || echo "none")
    echo "Current preference: $pref"
    echo ""
    echo "Available options:"
    echo "  --help                          Show basic usage"
    echo "  --fpwrapper-help             Show this detailed help"
    echo "  --fpwrapper-info             Show wrapper info"
    echo "  --fpwrapper-config-dir       Show Flatpak data directory"
    echo "  --fpwrapper-sandbox-info     Show Flatpak sandbox details"
    echo "  --fpwrapper-edit-sandbox     Edit Flatpak permissions"
    echo "  --fpwrapper-sandbox-yolo     Grant all permissions (dangerous)"
    echo "  --fpwrapper-sandbox-reset    Reset sandbox to defaults"
    echo "  --fpwrapper-run-unrestricted Run with unrestricted permissions (transient)"
    echo "  --fpwrapper-force-interactive    Force interactive mode for testing"
    echo "  --fpwrapper-set-override [system|flatpak]  Set launch preference"
    echo "  --fpwrapper-set-pre-script <script>        Set pre-launch script"
    echo "  --fpwrapper-set-post-script <script>       Set post-run script"
    echo "  --fpwrapper-remove-pre-script               Remove pre-launch script"
    echo "  --fpwrapper-remove-post-script              Remove post-run script"
    echo ""
    echo "Examples:"
    echo "  $NAME --fpwrapper-info"
    echo "  cd \"\$(\$NAME --fpwrapper-config-dir)\""
    echo "  $NAME --fpwrapper-sandbox-info"
    echo "  $NAME --fpwrapper-edit-sandbox"
    echo "  $NAME --fpwrapper-sandbox-yolo"
    echo "  $NAME --fpwrapper-sandbox-reset"
    echo "  $NAME --fpwrapper-run-unrestricted"
    echo "  $NAME --fpwrapper-force-interactive"
    echo "  $NAME --fpwrapper-set-override system"
    echo "  $NAME --fpwrapper-set-pre-script ~/scripts/my-pre-script.sh"
    echo "  $NAME --fpwrapper-set-post-script ~/scripts/my-post-script.sh"
    echo "  $NAME --fpwrapper-remove-pre-script"
    echo "  $NAME --fpwrapper-remove-post-script"
    exit 0
elif [ "$1" = "--fpwrapper-info" ]; then
    echo "Wrapper for $NAME"
    echo "Flatpak ID: $ID"
    pref=$(cat "$PREF_FILE" 2>/dev/null || echo "none")
    echo "Preference: $pref"
    echo "Usage: $0 [args]"
    exit 0
elif [ "$1" = "--fpwrapper-config-dir" ]; then
    config_dir="${XDG_DATA_HOME:-$HOME/.local}/share/applications/$ID"
    echo "$config_dir"
    exit 0
elif [ "$1" = "--fpwrapper-sandbox-info" ]; then
    flatpak info "$ID"
    exit 0
elif [ "$1" = "--fpwrapper-edit-sandbox" ]; then
    if ! is_interactive; then
        echo "Error: Sandbox editing requires interactive CLI" >&2
        exit 1
    fi
    echo "Flatpak Sandbox Editor for $ID"
    echo "Common permissions:"
    echo "  --filesystem=home"
    echo "  --filesystem=host"
    echo "  --share=network"
    echo "  --share=ipc"
    echo "  --device=dri"
    echo "  --socket=pulseaudio"
    echo "  --socket=wayland"
    echo "  --socket=x11"
    echo ""
    echo "Enter permissions (one per line, empty line to finish):"
    exit 0
elif [ "$1" = "--fpwrapper-sandbox-yolo" ]; then
    if ! is_interactive; then
        echo "Error: YOLO mode requires interactive CLI" >&2
        exit 1
    fi
    echo "WARNING: YOLO mode will grant ALL permissions to $ID"
    echo "This is dangerous and should only be used for testing!"
    echo ""
    read -r -p "Are you sure you want to continue? [y/N] " response
    case "$response" in
        [yY]|[yY][eE][sS])
            echo "Granting all permissions to $ID..."
            echo "YOLO mode activated - use responsibly!"
            ;;
        *)
            echo "Cancelled YOLO mode"
            exit 0
            ;;
    esac
    exit 0
elif [ "$1" = "--fpwrapper-sandbox-reset" ]; then
    echo "Resetting sandbox permissions for $ID to defaults"
    exit 0
elif [ "$1" = "--fpwrapper-run-unrestricted" ]; then
    echo "Running $ID with unrestricted permissions (transient)"
    exec flatpak run "$ID" "$@"
elif [ "$1" = "--fpwrapper-set-override" ]; then
    override="${2:-}"
    if [ -z "$override" ]; then
        echo "Error: Must specify override type (system|flatpak)" >&2
        exit 1
    fi
    case "$override" in
        "system"|"flatpak")
            echo "$override" > "$PREF_FILE"
            echo "Set launch preference for $NAME to: $override"
            ;;
        *)
            echo "Error: Invalid override type '$override'. Use 'system' or 'flatpak'" >&2
            exit 1
            ;;
    esac
    exit 0
elif [ "$1" = "--fpwrapper-set-pre-script" ]; then
    script_path="${2:-}"
    if [ -z "$script_path" ]; then
        echo "Error: Must specify script path" >&2
        exit 1
    fi
    if [ ! -f "$script_path" ]; then
        echo "Error: Script not found: $script_path" >&2
        exit 1
    fi
    mkdir -p "$PREF_DIR"
    echo "$script_path" > "$PREF_DIR/$NAME.pre-script"
    echo "Set pre-launch script for $NAME to: $script_path"
    exit 0
elif [ "$1" = "--fpwrapper-set-post-script" ]; then
    script_path="${2:-}"
    if [ -z "$script_path" ]; then
        echo "Error: Must specify script path" >&2
        exit 1
    fi
    if [ ! -f "$script_path" ]; then
        echo "Error: Script not found: $script_path" >&2
        exit 1
    fi
    mkdir -p "$PREF_DIR"
    echo "$script_path" > "$PREF_DIR/$NAME.post-script"
    echo "Set post-run script for $NAME to: $script_path"
    exit 0
elif [ "$1" = "--fpwrapper-remove-pre-script" ]; then
    if [ -f "$PREF_DIR/$NAME.pre-script" ]; then
        rm "$PREF_DIR/$NAME.pre-script"
        echo "Removed pre-launch script for $NAME"
    else
        echo "No pre-launch script found for $NAME"
    fi
    exit 0
elif [ "$1" = "--fpwrapper-remove-post-script" ]; then
    if [ -f "$PREF_DIR/$NAME.post-script" ]; then
        rm "$PREF_DIR/$NAME.post-script"
        echo "Removed post-run script for $NAME"
    else
        echo "No post-run script found for $NAME"
    fi
    exit 0
fi

# Default behavior: run flatpak
exec flatpak run "$ID" "$@"
EOF
    chmod +x "$test_home/bin/testapp"
    
    # Test 1: Command injection through wrapper arguments
    local output
    output=$("$test_home/bin/testapp" --fpwrapper-info '; rm -rf /tmp/*' 2>&1 || true)
    if echo "$output" | grep -q "rm -rf"; then
        fail "Wrapper execution allows command injection in arguments"
    else
        defense "Wrapper execution blocks command injection in arguments"
    fi
    
    # Test 2: Path traversal through config directory
    output=$("$test_home/bin/testapp" --fpwrapper-config-dir '../../../etc' 2>&1 || true)
    if echo "$output" | grep -q "/etc"; then
        fail "Wrapper execution allows path traversal in config directory"
    else
        defense "Wrapper execution blocks path traversal in config directory"
    fi
    
    # Test 3: Environment variable injection
    local output
    # shellcheck disable=SC2034
    FPWRAPPER_FORCE="desktop; rm -rf /tmp/*"; output=$("$test_home/bin/testapp" --fpwrapper-info 2>&1 || true)
    if [ -f "/tmp/malicious" ]; then
        fail "Wrapper execution allows environment variable injection"
    else
        defense "Wrapper execution blocks environment variable injection"
    fi
}

# Main adversarial test execution
main() {
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${PURPLE}ADVERSARIAL fplaunchwrapper Test Suite${NC}"
    echo -e "${PURPLE}======================================${NC}"
    echo ""
    
    # Setup adversarial test environment
    local test_home
    test_home=$(setup_adversarial_env)
    
    # Run adversarial attacks against fplaunchwrapper
    test_validate_home_dir_attacks "$test_home"
    test_is_wrapper_file_attacks "$test_home"
    test_wrapper_generation_attacks "$test_home"
    test_preference_management_attacks "$test_home"
    test_env_var_management_attacks "$test_home"
    test_alias_management_attacks "$test_home"
    test_wrapper_script_attacks "$test_home"
    test_installation_script_attacks "$test_home"
    test_cleanup_function_attacks "$test_home"
    test_wrapper_execution_attacks "$test_home"
    
    # Cleanup
    cleanup_adversarial_env "$test_home"
    
    # Results
    echo ""
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${PURPLE}ADVERSARIAL fplaunchwrapper Test Results${NC}"
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${GREEN}Tests Passed: $PASSED${NC}"
    echo -e "${RED}Tests Failed: $FAILED${NC}"
    echo -e "${GREEN}Attacks Blocked: $ATTACKS_BLOCKED${NC}"
    echo -e "${RED}Vulnerabilities Found: $VULNERABILITIES_FOUND${NC}"
    
    if [ $VULNERABILITIES_FOUND -eq 0 ]; then
        echo -e "${GREEN}All attacks blocked! fplaunchwrapper appears secure.${NC}"
        exit 0
    else
        echo -e "${RED}CRITICAL: $VULNERABILITIES_FOUND fplaunchwrapper vulnerabilities found!${NC}"
        echo -e "${RED}fplaunchwrapper security compromised!${NC}"
        exit 1
    fi
}

# Run main function
main "$@"