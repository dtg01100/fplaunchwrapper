#!/usr/bin/env bash
# Test suite for lib/common.sh utility functions
# Tests critical security and helper functions that are used across the entire codebase
#
# WHY THESE TESTS MATTER:
# - validate_home_dir(): Security-critical function preventing installation to system directories
#   If broken: Users could accidentally install wrappers to /usr/bin, breaking system commands
# - is_wrapper_file(): Identifies generated wrapper scripts
#   If broken: Cleanup scripts might remove wrong files, or fail to remove actual wrappers
# - get_wrapper_id(): Extracts Flatpak IDs from wrapper scripts
#   If broken: Management commands won't work, ID-based operations fail
# - init_paths(): Sets up configuration paths consistently
#   If broken: Scripts lose track of config files, settings lost
# - cleanup_systemd_units(): Removes systemd service files
#   If broken: Orphaned services remain, causing conflicts on reinstall

# Developer workstation safety check
ensure_developer_safety() {
    # Never run on production systems
    if [ -z "${CI:-}" ] && [ "${TESTING:-}" != "1" ]; then
        # Check if we're in a development environment
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
        if [ ! -f "$SCRIPT_DIR/README.md" ] || [ ! -d "$SCRIPT_DIR/tests" ]; then
            echo "ERROR: This test must be run from the project root directory"
            echo "Run with: TESTING=1 tests/test_common_lib.sh"
            exit 1
        fi
    fi
    
    # Ensure we're not running as root
    if [ "$(id -u)" = "0" ] && [ -z "${CI:-}" ] && [ "${TESTING:-}" != "1" ]; then
        echo "ERROR: Refusing to run tests as root for safety"
        exit 1
    fi
    
    # Set testing environment
    export TESTING=1
    export CI=1
}

# Ensure developer safety before proceeding
ensure_developer_safety

TEST_DIR="/tmp/fplaunch-common-test-$$"
TEST_BIN="$TEST_DIR/bin"
TEST_CONFIG="$TEST_DIR/config/flatpak-wrappers"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Source the common library - this is what we're testing
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

# Test 1: validate_home_dir accepts valid paths
# WHAT IT TESTS: Security function that ensures installation only happens in user directories
# WHY IT MATTERS: Prevents accidental installation to system directories like /usr/bin
# WHAT COULD GO WRONG if broken:
# - Users install wrappers to /usr/bin, potentially breaking system commands
# - Malicious scripts could exploit weak validation to install system-wide
# - Package managers might conflict with user installations
test_validate_home_dir_valid() {
    echo "Test 1: validate_home_dir accepts valid home paths"
    
    # Test home directory itself - should always be allowed
    if validate_home_dir "$HOME" "test" 2>/dev/null; then
        pass "Accepts HOME directory itself"
    else
        fail "Should accept HOME directory itself"
    fi
    
    # Test subdirectory of home - typical install location
    if validate_home_dir "$HOME/.local/bin" "test" 2>/dev/null; then
        pass "Accepts subdirectory of HOME"
    else
        fail "Should accept subdirectory of HOME"
    fi
    
    # Test deep subdirectory - ensures pattern matching works correctly
    if validate_home_dir "$HOME/some/deep/path" "test" 2>/dev/null; then
        pass "Accepts deep subdirectory of HOME"
    else
        fail "Should accept deep subdirectory of HOME"
    fi
}

# Test 2: validate_home_dir rejects system paths
# WHAT IT TESTS: Security boundary enforcement - blocking dangerous system directories  
# WHY IT MATTERS: Prevents catastrophic system damage from wrong installation paths
# WHAT COULD GO WRONG if broken:
# - Wrapper scripts overwrite critical system commands (rm, mv, cp, etc.)
# - System becomes unstable, unbootable, or corrupted
# - Creates security vulnerabilities through path hijacking
# - Breaks existing software installations and system integrity
# - Advanced attack scenarios including symlink attacks, path traversal, encoding attacks
test_validate_home_dir_aggressive() {
    echo "Test 2: validate_home_dir rejects system paths and attack attempts"
    
    # Attack 1: Direct system directory attempts
    local system_dirs=("/usr/bin" "/usr/local/bin" "/bin" "/sbin" "/usr/sbin" "/opt/bin" "/snap/bin")
    for sys_dir in "${system_dirs[@]}"; do
        if ! validate_home_dir "$sys_dir" "test" 2>/dev/null; then
            pass "Rejects system directory: $sys_dir"
        else
            fail "Should reject system directory: $sys_dir"
        fi
    done
    
    # Attack 2: Path traversal attempts
    echo "Testing path traversal attacks..."
    local traversal_attacks=(
        "/home/user/../../../etc"
        "/home/user/../../../../root"
        "/tmp/evil/../../../usr/bin"
        "/var/www/../../../bin"
        "/opt/app/../../../sbin"
        "/home/user/./././../../../etc/shadow"
    )
    
    for attack in "${traversal_attacks[@]}"; do
        if ! validate_home_dir "$attack" "test" 2>/dev/null; then
            pass "Blocked path traversal: $attack"
        else
            fail "Failed to block path traversal: $attack"
        fi
    done
    
    # Attack 3: Symlink attacks
    echo "Testing symlink attacks..."
    local temp_symlink="/tmp/test_symlink_$$"
    local attacks_blocked=0
    
    # Create malicious symlinks
    ln -sf "/usr/bin" "$temp_symlink" 2>/dev/null && {
        if ! validate_home_dir "$temp_symlink" "test" 2>/dev/null; then
            pass "Blocked symlink to /usr/bin"
            ((attacks_blocked++))
        else
            fail "Failed to block symlink to /usr/bin"
        fi
        rm -f "$temp_symlink"
    }
    
    ln -sf "/etc" "$temp_symlink" 2>/dev/null && {
        if ! validate_home_dir "$temp_symlink" "test" 2>/dev/null; then
            pass "Blocked symlink to /etc"
            ((attacks_blocked++))
        else
            fail "Failed to block symlink to /etc"
        fi
        rm -f "$temp_symlink"
    }
    
    # Attack 4: Encoding and Unicode attacks
    echo "Testing encoding attacks..."
    local encoding_attacks=(
        "/tmp/evil%2e%2e%2f"
        "/tmp/evil%C0%AE%C0%AE/"
        "/tmp/evil\x2e\x2e\x2f"
        "/tmp/evil\\u002e\\u002e\\u002f"
    )
    
    for encoding in "${encoding_attacks[@]}"; do
        if ! validate_home_dir "$encoding" "test" 2>/dev/null; then
            pass "Blocked encoding attack: $encoding"
            ((attacks_blocked++))
        else
            fail "Failed to block encoding attack: $encoding"
        fi
    done
    
    # Attack 5: Extremely long paths
    echo "Testing buffer overflow attempts..."
    local long_path="/very/long/path/that/exceeds/reasonable/limits/and/could/cause/buffer/overflow/issues/that/never/ends/and/keeps/going/forever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever/and/ever"
    
    if ! validate_home_dir "$long_path" "test" 2>/dev/null; then
        pass "Blocked excessively long path (${#long_path} chars)"
    else
        fail "Failed to block long path attack (${#long_path} chars)"
    fi
    
    # Attack 6: Race condition attempts (simulate rapid changes)
    echo "Testing race condition resilience..."
    local race_test="/tmp/race_test_$$"
    for i in {1..5}; do
        mkdir -p "$race_test"
        # Rapidly change directory permissions and ownership
        chmod 777 "$race_test" 2>/dev/null
        if ! validate_home_dir "$race_test" "test" 2>/dev/null; then
            pass "Race condition test $i: Correctly rejected non-home directory"
        else
            fail "Race condition test $i: Should reject non-home directory"
        fi
        rm -rf "$race_test"
    done
    
    echo "Advanced security boundary testing completed"
}

# Test 3: is_wrapper_file detects generated wrappers
# WHAT IT TESTS: Ability to identify wrapper scripts created by fplaunchwrapper
# WHY IT MATTERS: Critical for cleanup operations and management commands
# WHAT COULD GO WRONG if broken:
# - Cleanup scripts remove wrong files (user scripts, system files)
# - Management commands fail to find wrappers
# - Orphaned wrapper files remain after cleanup
# - Security risk if malicious scripts masquerade as wrappers
# - Advanced attack scenarios including impersonation, corruption, and race conditions
test_is_wrapper_file_aggressive() {
    echo "Test 3: is_wrapper_file_aggressive detects wrapper files and evades attacks"
    
    mkdir -p "$TEST_BIN"
    
    # Test 1: Valid wrapper detection
    echo "Testing valid wrapper detection..."
    cat > "$TEST_BIN/valid-wrapper" << 'EOF'
#!/usr/bin/env bash
# Generated by fplaunchwrapper

NAME="valid-wrapper"
ID="com.example.ValidApp"
EOF
    
    if is_wrapper_file "$TEST_BIN/valid-wrapper"; then
        pass "Detects valid wrapper file"
    else
        fail "Failed to detect valid wrapper file"
    fi
    
    # Attack 1: Malicious script impersonation attempts
    echo "Testing wrapper impersonation attacks..."
    local impersonation_attacks=(
        "#!/bin/bash\n# Fake wrapper script\nmalicious_code_here"
        "#!/usr/bin/env python\n# Generated by fplaunchwrapper\nimport os; os.system('rm -rf /')"
        "#!/usr/bin/env node\n/* Generated by fplaunchwrapper */\nrequire('child_process').exec('sudo rm -rf /')"
        "#!/usr/bin/env bash\n# Generated by FAKE-wrapper\nrm -rf /tmp/dangerous"
        "#!/usr/bin/env bash\nNAME=\"evil\"\nID=\"malicious\"\necho \"harmless\""
    )
    
    local attacks_blocked=0
    for i in "${!impersonation_attacks[@]}"; do
        local attack_file="$TEST_BIN/attack_$i"
        printf "%s\n" "${impersonation_attacks[$i]}" > "$attack_file"
        
        if ! is_wrapper_file "$attack_file" 2>/dev/null; then
            pass "Blocked impersonation attack $i"
            ((attacks_blocked++))
        else
            fail "Failed to block impersonation attack $i"
        fi
    done
    
    # Attack 2: Corrupted wrapper attempts
    echo "Testing corrupted wrapper detection..."
    local corrupted_wrappers=(
        "#!/usr/bin/env bash\n# Generated by fplaunchwrapper\n# [CORRUPTED DATA]"
        "#!/usr/bin/env bash\n# Generated by fplaunchwrapper\n[MISSING REQUIRED FIELDS]"
        "#!/usr/bin/env bash\n# Generated by fplaunchwrapper\n\n# [TRUNCATED]"
        ""
        "#!/usr/bin/env bash\n# Generated by different-tool"
    )
    
    for i in "${!corrupted_wrappers[@]}"; do
        local corrupt_file="$TEST_BIN/corrupt_$i"
        printf "%s\n" "${corrupted_wrappers[$i]}" > "$corrupt_file"
        
        if ! is_wrapper_file "$corrupt_file" 2>/dev/null; then
            pass "Correctly rejected corrupted wrapper $i"
            ((attacks_blocked++))
        else
            fail "Failed to reject corrupted wrapper $i"
        fi
    done
    
    # Attack 3: Symlink attacks
    echo "Testing symlink attacks..."
    local real_wrapper="$TEST_BIN/real_wrapper"
    local malicious_symlink="$TEST_BIN/malicious_symlink"
    
    # Create a real wrapper
    cat > "$real_wrapper" << 'EOF'
#!/usr/bin/env bash
# Generated by fplaunchwrapper

NAME="real-app"
ID="com.example.RealApp"
EOF
    
    # Create a malicious symlink pointing to the wrapper
    ln -sf "$real_wrapper" "$malicious_symlink" 2>/dev/null
    
    if ! is_wrapper_file "$malicious_symlink" 2>/dev/null; then
        pass "Symlink detection works correctly"
        ((attacks_blocked++))
    else
        fail "Symlink detection failed"
    fi
    
    # Attack 4: Race condition attempts
    echo "Testing race condition attacks..."
    local race_file="$TEST_BIN/race_test"
    for i in {1..3}; do
        # Create file with wrapper content
        cat > "$race_file" << EOF
#!/usr/bin/env bash
# Generated by fplaunchwrapper

NAME="race-test-$i"
ID="com.example.RaceTest$i"
EOF
        
        # Rapidly change content
        printf "#!/bin/bash\n# Fake wrapper\nrm -rf /\n" > "$race_file" &
        sleep 0.001
        if is_wrapper_file "$race_file" 2>/dev/null; then
            fail "Race condition test $i failed"
        else
            pass "Race condition test $i passed"
            ((attacks_blocked++))
        fi
    done
    
    # Attack 5: Encoding attacks
    echo "Testing encoding bypass attempts..."
    local encoding_file="$TEST_BIN/encoding_test"
    printf "#!/usr/bin/env bash\n# Generated by fplaunchwrapper%c\nNAME=\"test\"%cID=\"com.example.Test\"\n" $'\x00' $'\x00' > "$encoding_file"
    
    if ! is_wrapper_file "$encoding_file" 2>/dev/null; then
        pass "Blocked encoding attack"
        ((attacks_blocked++))
    else
        fail "Failed to block encoding attack"
    fi
    
    echo "Aggressive wrapper detection testing completed"
}

# Test 4: get_wrapper_id extracts correct ID
# WHAT IT TESTS: Extracts Flatpak application ID from wrapper script content
# WHY IT MATTERS: Essential for all ID-based operations (preferences, blocking, management)
# WHAT COULD GO WRONG if broken:
# - fplaunch-manage commands fail to work with wrappers
# - Preferences can't be set per application
# - Blocklist functionality breaks
# - Wrapper identification becomes unreliable
test_get_wrapper_id() {
    echo "Test 4: get_wrapper_id extracts Flatpak ID"
    
    mkdir -p "$TEST_BIN"
    
    # Create wrapper with standard ID format
    cat > "$TEST_BIN/test-app" << 'EOF'
#!/usr/bin/env bash
# Generated by fplaunchwrapper

NAME="test-app"
ID="org.example.TestApp"
PREF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/flatpak-wrappers"
EOF
    
    local extracted_id
    extracted_id=$(get_wrapper_id "$TEST_BIN/test-app")
    
    if [ "$extracted_id" = "org.example.TestApp" ]; then
        pass "Extracted correct ID: $extracted_id"
    else
        fail "Expected 'org.example.TestApp', got '$extracted_id'"
    fi
    
    # Test wrapper with complex ID format (dots, vendor prefix)
    cat > "$TEST_BIN/another-app" << 'EOF'
#!/usr/bin/env bash
# Generated by fplaunchwrapper
NAME="another-app"
ID="com.github.Developer.App"
EOF
    
    extracted_id=$(get_wrapper_id "$TEST_BIN/another-app")
    
    if [ "$extracted_id" = "com.github.Developer.App" ]; then
        pass "Extracted ID with dots: $extracted_id"
    else
        fail "Expected 'com.github.Developer.App', got '$extracted_id'"
    fi
}

# Test 5: init_paths sets up correct paths
# WHAT IT TESTS: Path initialization and configuration loading
# WHY IT MATTERS: Ensures all scripts use consistent paths and can find config files
# WHAT COULD GO WRONG if broken:
# - Scripts lose track of configuration files
# - Settings and preferences are lost or inaccessible
# - Inconsistent behavior between different scripts
# - BIN_DIR not loaded from saved configuration
test_init_paths() {
    echo "Test 5: init_paths initializes paths correctly"
    
    mkdir -p "$TEST_CONFIG"
    echo "$TEST_BIN" > "$TEST_CONFIG/bin_dir"
    
    # Set environment to use test config
    XDG_CONFIG_HOME="$TEST_DIR/config"
    
    # Call init_paths
    init_paths
    
    if [ "$CONFIG_DIR" = "$TEST_CONFIG" ]; then
        pass "CONFIG_DIR set correctly: $CONFIG_DIR"
    else
        fail "Expected CONFIG_DIR=$TEST_CONFIG, got $CONFIG_DIR"
    fi
    
    if [ "$BIN_DIR" = "$TEST_BIN" ]; then
        pass "BIN_DIR loaded from config: $BIN_DIR"
    else
        fail "Expected BIN_DIR=$TEST_BIN, got $BIN_DIR"
    fi
}

# Test 6: ensure_config_dir creates directory
# WHAT IT TESTS: Configuration directory creation and setup
# WHY IT MATTERS: Ensures config files have a proper location to be stored
# WHAT COULD GO WRONG if broken:
# - Configuration files can't be created or saved
# - Scripts fail when trying to write preferences
# - Inconsistent config file locations
# - Permission errors when accessing non-existent directories
test_ensure_config_dir() {
    echo "Test 6: ensure_config_dir creates config directory"
    
    local test_config="$TEST_DIR/new-config/flatpak-wrappers"
    CONFIG_DIR="$test_config"
    
    ensure_config_dir
    
    if [ -d "$test_config" ]; then
        pass "Config directory created: $test_config"
    else
        fail "Config directory not created"
    fi
}

# Test 7: get_systemd_unit_dir returns correct path
# WHAT IT TESTS: Systemd user unit directory path resolution
# WHY IT MATTERS: Critical for systemd service management and cleanup
# WHAT COULD GO WRONG if broken:
# - Systemd services installed to wrong location
# - Cleanup fails to remove service files
# - Service management commands fail
# - Conflicts with system-wide systemd units
test_get_systemd_unit_dir() {
    echo "Test 7: get_systemd_unit_dir returns correct path"
    
    local unit_dir
    unit_dir=$(get_systemd_unit_dir)
    
    local expected="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    
    if [ "$unit_dir" = "$expected" ]; then
        pass "Systemd unit dir correct: $unit_dir"
    else
        fail "Expected $expected, got $unit_dir"
    fi
}

# Test 8: cleanup_systemd_units removes units
# WHAT IT TESTS: Systemd service file cleanup functionality
# WHY IT MATTERS: Ensures clean uninstallation and prevents service conflicts
# WHAT COULD GO WRONG if broken:
# - Orphaned systemd services remain after uninstall
# - Service conflicts on reinstallation
# - Systemd becomes polluted with old services
# - Users experience startup delays from stale services
test_cleanup_systemd_units() {
    echo "Test 8: cleanup_systemd_units removes unit files"
    
    # Test the file removal part in isolation since systemctl won't work in container
    local unit_dir="$TEST_DIR/systemd/user"
    mkdir -p "$unit_dir"
    
    # Create test unit files
    touch "$unit_dir/test-units.service"
    touch "$unit_dir/test-units.path"
    touch "$unit_dir/test-units.timer"
    
    # Mock systemctl globally for this subshell
    systemctl() { return 0; }
    export -f systemctl
    
    # Temporarily override XDG_CONFIG_HOME to use test directory
    XDG_CONFIG_HOME="$TEST_DIR" cleanup_systemd_units "test-units" 2>/dev/null
    
    if [ ! -f "$unit_dir/test-units.service" ]; then
        pass "Service unit removed"
    else
        fail "Service unit not removed"
    fi
    
    if [ ! -f "$unit_dir/test-units.path" ]; then
        pass "Path unit removed"
    else
        fail "Path unit not removed"
    fi
    
    if [ ! -f "$unit_dir/test-units.timer" ]; then
        pass "Timer unit removed"
    else
        fail "Timer unit not removed"
    fi
}

# Test 9: get_wrapper_name returns correct name
# WHAT IT TESTS: Wrapper name extraction from file paths
# WHY IT MATTERS: Used for display and identification purposes
# WHAT COULD GO WRONG if broken:
# - Incorrect names displayed in management commands
# - Confusion between wrapper names and file paths
# - User interface shows wrong application names
# - Script logic fails when expecting basename only
test_get_wrapper_name() {
    echo "Test 9: get_wrapper_name returns correct name"
    
    local name
    name=$(get_wrapper_name "/path/to/wrapper/firefox")
    
    if [ "$name" = "firefox" ]; then
        pass "Extracted wrapper name: $name"
    else
        fail "Expected 'firefox', got '$name'"
    fi
}

# Run all tests
echo "Common Library Test Suite"
echo "========================="
echo

test_validate_home_dir_valid
echo
test_validate_home_dir_aggressive
echo
test_is_wrapper_file_aggressive
echo
test_get_wrapper_id
echo
test_init_paths
echo
test_ensure_config_dir
echo
test_get_systemd_unit_dir
echo
test_cleanup_systemd_units
echo
test_get_wrapper_name
echo

# Summary
echo "======================================"
echo "Test Results"
echo "======================================"
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"
echo "Total:  $((TESTS_PASSED + TESTS_FAILED))"
echo "======================================"

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Common library tests passed"
    exit 0
else
    echo -e "${RED}✗${NC} Some common library tests failed"
    exit 1
fi
