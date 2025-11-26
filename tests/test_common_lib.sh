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
test_validate_home_dir_invalid() {
    echo "Test 2: validate_home_dir rejects system paths"
    
    # Test /usr/bin - primary system binary directory (MUST be protected)
    if ! validate_home_dir "/usr/bin" "test" 2>/dev/null; then
        pass "Rejects /usr/bin"
    else
        fail "Should reject /usr/bin"
    fi
    
    # Test /opt/bin - alternative system directory for third-party software
    if ! validate_home_dir "/opt/bin" "test" 2>/dev/null; then
        pass "Rejects /opt/bin"
    else
        fail "Should reject /opt/bin"
    fi
    
    # Test /usr/local/bin - system directory for locally compiled packages
    if ! validate_home_dir "/usr/local/bin" "test" 2>/dev/null; then
        pass "Rejects /usr/local/bin"
    else
        fail "Should reject /usr/local/bin"
    fi
    
    # Test /bin - essential system binaries (critical protection needed)
    if ! validate_home_dir "/bin" "test" 2>/dev/null; then
        pass "Rejects /bin"
    else
        fail "Should reject /bin"
    fi
    
    # Test /tmp - outside HOME directory (should be rejected for consistency)
    if ! validate_home_dir "/tmp/test" "test" 2>/dev/null; then
        pass "Rejects /tmp paths"
    else
        fail "Should reject /tmp paths"
    fi
}

# Test 3: is_wrapper_file detects generated wrappers
# WHAT IT TESTS: Ability to identify wrapper scripts created by fplaunchwrapper
# WHY IT MATTERS: Critical for cleanup operations and management commands
# WHAT COULD GO WRONG if broken:
# - Cleanup scripts remove wrong files (user scripts, system files)
# - Management commands fail to find wrappers
# - Orphaned wrapper files remain after cleanup
# - Security risk if malicious scripts masquerade as wrappers
test_is_wrapper_file() {
    echo "Test 3: is_wrapper_file detects wrapper files"
    
    mkdir -p "$TEST_BIN"
    
    # Create a valid wrapper file with proper header
    cat > "$TEST_BIN/test-wrapper" << 'EOF'
#!/usr/bin/env bash
# Generated by fplaunchwrapper

NAME="test-wrapper"
ID="com.example.Test"
EOF
    
    if is_wrapper_file "$TEST_BIN/test-wrapper"; then
        pass "Detects valid wrapper file"
    else
        fail "Should detect valid wrapper file"
    fi
    
    # Create a non-wrapper file to ensure we don't get false positives
    cat > "$TEST_BIN/not-wrapper" << 'EOF'
#!/usr/bin/env bash
# Just a regular script
echo "Hello"
EOF
    
    if ! is_wrapper_file "$TEST_BIN/not-wrapper"; then
        pass "Rejects non-wrapper file"
    else
        fail "Should reject non-wrapper file"
    fi
    
    # Test non-existent file handling
    if ! is_wrapper_file "$TEST_BIN/nonexistent"; then
        pass "Rejects non-existent file"
    else
        fail "Should reject non-existent file"
    fi
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
test_validate_home_dir_invalid
echo
test_is_wrapper_file
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
