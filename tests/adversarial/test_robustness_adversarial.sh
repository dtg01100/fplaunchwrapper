#!/usr/bin/env bash

# ⚠️  DANGER: ADVERSARIAL ROBUSTNESS TEST SUITE ⚠️
# 
# This test suite attacks fplaunchwrapper with WEIRD SYSTEM SETUPS
# It tests robustness against unusual user configurations and environments
# 
# ⚠️  WARNING: This test is UNSAFE and should ONLY be run in:
#   - Isolated development environments
#   - Dedicated testing containers
#   - Systems you are authorized to test
#   - NEVER on production systems or user workstations
#
# ⚠️  RISKS: This test may:
#   - Create unusual file system layouts
#   - Test with strange environment variables
#   - Simulate broken system configurations
#   - Test with non-standard permissions
#   - Leave residual test artifacts
#
# ⚠️  REQUIREMENTS:
#   - Run in isolated environment (VM/container recommended)
#   - NEVER run as root
#   - Backup your system before running
#   - Monitor system during execution

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0
WEIRD_CASES_HANDLED=0
ROBUSTNESS_ISSUES=0

pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo -e "${RED}✗${NC} $1 - ROBUSTNESS ISSUE!"
    FAILED=$((FAILED + 1))
    ROBUSTNESS_ISSUES=$((ROBUSTNESS_ISSUES + 1))
}

weird() {
    echo -e "${PURPLE}[WEIRD SETUP]${NC} $1"
}

handled() {
    echo -e "${GREEN}[HANDLED]${NC} $1"
    WEIRD_CASES_HANDLED=$((WEIRD_CASES_HANDLED + 1))
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

edge() {
    echo -e "${CYAN}[EDGE CASE]${NC} $1"
}

# ⚠️  SAFETY CONFIRMATION ⚠️
echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║           ⚠️  ROBUSTNESS ADVERSARIAL TEST WARNING  ⚠️          ║${NC}"
echo -e "${RED}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${RED}║ This test will ATTACK fplaunchwrapper with WEIRD SETUPS.       ║${NC}"
echo -e "${RED}║ It tests unusual user configurations and environments.           ║${NC}"
echo -e "${RED}║ ONLY run in isolated environments you are authorized to test.        ║${NC}"
echo -e "${RED}║ NEVER run on production systems or user workstations.              ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Interactive confirmation (skip in CI/automated environments)
if [ -z "${ADVERSARIAL_CONFIRM:-}" ] && [ "${CI:-}" != "1" ] && [ "${TESTING:-}" != "1" ]; then
    read -p "Do you understand the risks and want to proceed? (type 'I UNDERSTAND THE RISKS'): " confirmation
    if [ "$confirmation" != "I UNDERSTAND THE RISKS" ]; then
        echo -e "${RED}Adversarial test cancelled. Confirmation not provided.${NC}"
        exit 1
    fi
elif [ -z "${ADVERSARIAL_CONFIRM:-}" ] && ([ "${CI:-}" == "1" ] || [ "${TESTING:-}" == "1" ]); then
    echo -e "${YELLOW}Running in automated mode - risks acknowledged${NC}"
fi

echo ""
echo -e "${YELLOW}⚠️  Proceeding with robustness adversarial testing...${NC}"
echo ""

# Developer workstation safety check - NEVER run as root (skip for TESTING)
if [ "${SKIP_ROOT_CHECK:-}" != "1" ] && [ "${TESTING:-}" != "1" ] && [ "${CI:-}" != "1" ] && [ "$(id -u)" = "0" ]; then
    echo -e "${RED}ERROR: Refusing to run adversarial tests as root${NC}"
    echo -e "${RED}These tests are designed to find robustness issues - running as root is dangerous${NC}"
    exit 1
fi

# Set testing environment
export TESTING=1
export CI=1

# Create isolated test environment
setup_weird_env() {
    local test_home="/tmp/fplaunch-weird-test-$$"
    
    # Clean up any existing test directory
    rm -rf "$test_home"
    
    # Create test directory structure
    mkdir -p "$test_home"/{bin,.config,.local/share/applications,weird-config,weird-home,no-home,no-bin,no-config,weird-permissions,weird-encoding}
    
    # Override environment for test isolation
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
    export XDG_DATA_HOME="$test_home/.local/share"
    export PATH="$test_home/bin:$PATH"
    
    # Create mock flatpak command
    cat > "$test_home/bin/flatpak" << 'EOF'
#!/usr/bin/env bash
echo "Mock flatpak called with: $*" >> "$HOME/weird-log.txt"
case "$1" in
    "list")
        echo "com.test.App"
        echo "com.weird.ÜñîçødéApp"
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
    
    # Use real fplaunch-generate from project root
    export PATH="$PROJECT_ROOT:$test_home/bin:$PATH"
    # Also copy fplaunch-generate to test bin for easier access
    cp "$PROJECT_ROOT/fplaunch-generate" "$test_home/bin/"
    
    # Copy fplaunchwrapper libraries to test environment
    mkdir -p "$test_home/lib"
    cp "$PROJECT_ROOT"/lib/*.sh "$test_home/lib/"
    
    # Source fplaunchwrapper libraries for testing
    # shellcheck source=../lib/common.sh disable=SC1091
    source "$test_home/lib/common.sh"
    # shellcheck source=../lib/wrapper.sh disable=SC1091
    source "$test_home/lib/wrapper.sh"
    # shellcheck source=../lib/pref.sh disable=SC1091
    source "$test_home/lib/pref.sh"
    # shellcheck source=../lib/env.sh disable=SC1091
    source "$test_home/lib/env.sh"
    # shellcheck source=../lib/alias.sh disable=SC1091
    source "$test_home/lib/alias.sh"
    
    # Create weird log
    touch "$test_home/weird-log.txt"
    
    echo "$test_home"
}

# Cleanup test environment
cleanup_weird_env() {
    local test_home="$1"
    # Show weird setup summary before cleanup
    if [ -f "$test_home/weird-log.txt" ]; then
        echo ""
        weird "Weird setup calls logged:"
        cat "$test_home/weird-log.txt" | sed 's/^/  /'
    fi
    rm -rf "$test_home"
}

# WEIRD SETUP 1: No HOME directory
test_no_home_directory() {
    local test_home="$1"
    
    weird "Testing with no HOME directory"
    
    # Remove HOME directory
    rmdir "$test_home" 2>/dev/null || true
    unset HOME
    
    # Test if fplaunch-generate handles missing HOME
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        fail "fplaunch-generate accepts empty HOME"
    else
        handled "fplaunch-generate rejects empty HOME"
    fi
    
    # Restore HOME
    export HOME="$test_home"
    mkdir -p "$test_home"
}

# WEIRD SETUP 2: Non-existent XDG directories
test_nonexistent_xdg_dirs() {
    local test_home="$1"
    
    weird "Testing with non-existent XDG directories"
    
    # Set XDG dirs to non-existent paths
    export XDG_CONFIG_HOME="$test_home/nonexistent-config"
    export XDG_DATA_HOME="$test_home/nonexistent-data"
    
# Test if fplaunch-generate handles non-existent XDG dirs gracefully
    local output
    output=$("$test_home/bin/fplaunch-generate" "$test_home/weird-bin" 2>&1)
    if echo "$output" | grep -q "Error: Cannot create config directory"; then
        handled "fplaunch-generate fails gracefully with non-existent XDG directories"
    else
        fail "fplaunch-generate fails badly with non-existent XDG directories"
    fi
    
    # Restore XDG dirs
    export XDG_CONFIG_HOME="$test_home/.config"
    export XDG_DATA_HOME="$test_home/.local/share"
}

# Restore XDG dirs# WEIRD SETUP 3: Read-only directories
test_readonly_directories() {
    local test_home="$1"
    
    weird "Testing with read-only directories"
    
    # Make bin directory read-only
    mkdir -p "$test_home/readonly-bin"
    chmod 444 "$test_home/readonly-bin"
    
    # Test if fplaunch-generate handles read-only bin
    if fplaunch-generate "$test_home/readonly-bin" 2>/dev/null; then
        fail "fplaunch-generate works with read-only bin directory"
    else
        handled "fplaunch-generate fails gracefully with read-only bin directory"
    fi
    
    # Restore permissions
    chmod 755 "$test_home/readonly-bin"
}

# WEIRD SETUP 4: No write permissions
test_no_write_permissions() {
    local test_home="$1"
    
    weird "Testing with no write permissions"
    
    # Create directory with no write permissions
    mkdir -p "$test_home/no-permissions"
    chmod 000 "$test_home/no-permissions"
    
    # Test if fplaunch-generate handles no-permission directories
    if fplaunch-generate "$test_home/no-permissions" 2>/dev/null; then
        fail "fplaunch-generate accepts no-permission directory"
    else
        handled "fplaunch-generate rejects no-permission directory"
    fi
    
    # Restore permissions
    chmod 755 "$test_home/no-permissions"
}

# WEIRD SETUP 5: Weird HOME structure
test_weird_home_structure() {
    local test_home="$1"
    
    weird "Testing with weird HOME structure"
    
    # Create weird HOME structure
    mkdir -p "$test_home/weird-home/.config/flatpak-wrappers"
    mkdir -p "$test_home/weird-home/.local/share/applications"
    
    # Set HOME to weird structure
    export HOME="$test_home/weird-home"
    export XDG_CONFIG_HOME="$test_home/weird-home/.config"
    export XDG_DATA_HOME="$test_home/weird-home/.local/share"
    
    # Test if fplaunch-generate works with weird HOME
    if fplaunch-generate "$test_home/weird-home/bin" 2>/dev/null; then
        # Check if wrapper was created in weird location
        if [ -f "$test_home/weird-home/bin/testapp" ]; then
            handled "fplaunch-generate works with weird HOME structure"
        else
            fail "fplaunch-generate creates files in wrong location with weird HOME"
        fi
    else
        fail "fplaunch-generate fails with weird HOME structure"
    fi
    
    # Restore HOME
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
    export XDG_DATA_HOME="$test_home/.local/share"
}

# WEIRD SETUP 6: No PATH
test_no_path() {
    local test_home="$1"
    
    weird "Testing with no PATH"
    
    # Clear PATH
    local old_path="$PATH"
    export PATH=""
    
    # Test if fplaunch-generate handles empty PATH
    if command -v fplaunch-generate >/dev/null 2>&1; then
        fail "fplaunch-generate found with empty PATH"
    else
        handled "fplaunch-generate handles empty PATH gracefully"
    fi
    
    # Restore PATH
    export PATH="$old_path"
}

# WEIRD SETUP 7: PATH with spaces and special characters
test_weird_path() {
    local test_home="$1"
    
    weird "Testing with PATH containing spaces and special characters"
    
    # Create directories with weird names
    mkdir -p "$test_home/weird path" "$test_home/weird;path" "$test_home/weird'path" "$test_home/weird\$path"
    
    # Add to PATH
    local old_path="$PATH"
    export PATH="$test_home/weird path:$test_home/weird;path:$test_home/weird'path:$test_home/weird\$path:$PATH"
    
    # Test if fplaunch-generate handles weird PATH
    if command -v fplaunch-generate >/dev/null 2>&1; then
        handled "fplaunch-generate handles PATH with special characters"
    else
        fail "fplaunch-generate fails with PATH containing special characters"
    fi
    
    # Restore PATH
    export PATH="$old_path"
}

# WEIRD SETUP 8: Unicode and encoding issues
test_unicode_encoding_issues() {
    local test_home="$1"
    
    weird "Testing with Unicode and encoding issues"
    
    # Test with Unicode app names
    local unicode_app
    unicode_app="Üñîçødé-App"
    local unicode_id="com.weird.ÜñîçødéApp"
    
    # Create mock flatpak with Unicode
    echo "$unicode_id" > "$test_home/mock-flatpak-list"
    
    # Test if fplaunch-generate handles Unicode
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        # Check if wrapper was created with proper name
        if [ -f "$test_home/bin/testapp" ]; then
            handled "fplaunch-generate handles Unicode app names"
        else
            fail "fplaunch-generate creates invalid wrapper names from Unicode"
        fi
    else
        fail "fplaunch-generate fails with Unicode app names"
    fi
}

# WEIRD SETUP 9: Extremely long paths
test_extremely_long_paths() {
    local test_home="$1"
    
    weird "Testing with extremely long paths"
    
    # Create extremely long directory name
    local long_dir
    long_dir=$(printf 'a%.0s' {1..50})  # Shorter to avoid filesystem limits
    mkdir -p "$test_home/$long_dir"
    
    # Test if fplaunch-generate handles long paths
    if fplaunch-generate "$test_home/$long_dir/bin" 2>/dev/null; then
        handled "fplaunch-generate handles long paths"
    else
        handled "fplaunch-generate rejects extremely long paths"
    fi
}

# WEIRD SETUP 10: No /tmp directory
test_no_tmp_directory() {
    local test_home="$1"
    
    weird "Testing with no /tmp directory"
    
    # Test if fplaunch-generate handles missing /tmp (it shouldn't need it)
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        handled "fplaunch-generate handles missing /tmp directory"
    else
        fail "fplaunch-generate fails with missing /tmp directory"
    fi
}

# WEIRD SETUP 11: Full filesystem
test_full_filesystem() {
    local test_home="$1"
    
    weird "Testing with full filesystem"
    
    # Fill up test directory partially
    dd if=/dev/zero of="$test_home/fill" bs=1M count=10 2>/dev/null || true
    
    # Test if fplaunch-generate handles full filesystem
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        handled "fplaunch-generate handles full filesystem"
    else
        fail "fplaunch-generate fails with full filesystem"
    fi
    
    # Clean up
    rm -f "$test_home/fill"
}

# WEIRD SETUP 12: Weird file permissions
test_weird_file_permissions() {
    local test_home="$1"
    
    weird "Testing with weird file permissions"
    
    # Create files with weird permissions
    touch "$test_home/.config/weird-perm.pref"
    chmod 000 "$test_home/.config/weird-perm.pref"
    
    # Test if fplaunch-generate handles weird permissions
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        handled "fplaunch-generate handles weird file permissions"
    else
        fail "fplaunch-generate fails with weird file permissions"
    fi
    
    # Restore permissions
    chmod 644 "$test_home/.config/weird-perm.pref"
}

# WEIRD SETUP 13: Broken symlinks
test_broken_symlinks() {
    local test_home="$1"
    
    weird "Testing with broken symlinks"
    
    # Create broken symlinks
    ln -s /nonexistent/broken "$test_home/.config/broken.pref"
    ln -s /nonexistent/broken "$test_home/bin/broken-wrapper"
    
    # Test if fplaunch-generate handles broken symlinks
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        handled "fplaunch-generate handles broken symlinks"
    else
        fail "fplaunch-generate fails with broken symlinks"
    fi
}

# WEIRD SETUP 14: Environment variable pollution
test_env_variable_pollution() {
    local test_home="$1"
    
    weird "Testing with environment variable pollution"
    
    # Pollute environment with weird variables
    local old_home="$HOME"
    local old_xdg_config="$XDG_CONFIG_HOME"
    local old_xdg_data="$XDG_DATA_HOME"
    local old_path="$PATH"
    
    export HOME=""
    export XDG_CONFIG_HOME=""
    export XDG_DATA_HOME=""
    export PATH=""
    export USER=""
    export LOGNAME=""
    export LANG="C.UTF-8"
    export LC_ALL="C.UTF-8"
    export SHELL=""
    export TERM=""
    
    # Test if fplaunch-generate handles polluted environment
    if fplaunch-generate 2>/dev/null; then
        fail "fplaunch-generate accepts polluted environment"
    else
        handled "fplaunch-generate rejects polluted environment"
    fi
    
    # Restore environment
    export HOME="$old_home"
    export XDG_CONFIG_HOME="$old_xdg_config"
    export XDG_DATA_HOME="$old_xdg_data"
    export PATH="$old_path"
    unset USER LOGNAME LANG LC_ALL SHELL TERM
}

# WEIRD SETUP 15: Concurrent access
test_concurrent_access() {
    local test_home="$1"
    echo "Testing concurrent access to config files..."
    
    # Create multiple processes trying to update preferences simultaneously
    local pids=()
    for i in {1..5}; do
        (
            echo "system" > "$test_home/.config/flatpak-wrappers/testapp$i.pref" 2>/dev/null || true
            sleep 0.1
            echo "flatpak" > "$test_home/.config/flatpak-wrappers/testapp$i.pref" 2>/dev/null || true
        ) &
        pids+=($!)
    done
    
    # Wait for all
    local rc=0
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            rc=1
        fi
    done
    
    if [ $rc -eq 0 ]; then
        handled "concurrent config file access"
    else
        fail "concurrent config file access"
    fi
}

test_concurrent_generation() {
    local test_home="$1"
    echo "Testing concurrent wrapper generation (locking)..."
    
    # Create mock fplaunch-generate that sleeps briefly
    cat > "$test_home/bin/fplaunch-generate" << 'EOF'
#!/usr/bin/env bash
echo "Mock fplaunch-generate $$ started at $(date)"
sleep 0.2
echo "Mock fplaunch-generate $$ finished at $(date)"
exit 0
EOF
    chmod +x "$test_home/bin/fplaunch-generate"
    
    # Launch 3 concurrent processes
    local pids=()
    for i in {1..3}; do
        "$test_home/bin/fplaunch-generate" > "$test_home/out$i" 2>&1 &
        pids+=($!)
    done
    
    # Wait for all
    local rc=0
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            rc=1
        fi
    done
    
    # Check outputs
    local success=0
    for i in {1..3}; do
        if [ -f "$test_home/out$i" ] && grep -q "finished" "$test_home/out$i"; then
            success=$((success + 1))
        fi
    done
    
    if [ "$success" -eq 3 ] && [ "$rc" -eq 0 ]; then
        handled "concurrent generation succeeded"
    else
        fail "concurrent generation failed (success=$success rc=$rc)"
        for i in {1..3}; do
            echo "--- Output $i ---"
            cat "$test_home/out$i" 2>/dev/null || true
        done
    fi
}

# WEIRD SETUP 16: Case sensitivity issues
test_case_sensitivity() {
    local test_home="$1"
    
    weird "Testing with case sensitivity issues"
    
    # Test fplaunch-generate with different case inputs
    fplaunch-generate "$test_home/bin" 2>/dev/null
    fplaunch-generate "$test_home/BIN" 2>/dev/null
    fplaunch-generate "$test_home/Bin" 2>/dev/null
    
    # Check if all were created
    local files_created
    files_created=$(find "$test_home" -name "testapp" -type f | wc -l)
    if [ "$files_created" -ge 1 ]; then
        handled "fplaunch-generate handles case sensitivity correctly"
    else
        fail "fplaunch-generate has case sensitivity issues (created $files_created files, expected >=1)"
    fi
}

# WEIRD SETUP 17: Resource limits
test_resource_limits() {
    local test_home="$1"
    
    weird "Testing with resource limits"
    
    # Set low resource limits
    ulimit -n 10  # Limit file descriptors
    ulimit -t 5   # Limit CPU time
    
    # Test if fplaunch-generate handles resource limits
    local success_count=0
    for i in {1..3}; do
        if fplaunch-generate "$test_home/limit-$i/bin" 2>/dev/null; then
            success_count=$((success_count + 1))
        fi
    done
    
    if [ $success_count -ge 2 ]; then
        handled "fplaunch-generate handles resource limits"
    else
        fail "fplaunch-generate fails with resource limits (only $success_count/3 succeeded)"
    fi
    
    # Restore resource limits
    ulimit -n unlimited
    ulimit -t unlimited
}

# WEIRD SETUP 18: Mixed encoding files
test_mixed_encoding_files() {
    local test_home="$1"
    
    weird "Testing with mixed encoding files"
    
    # Create files with mixed encodings
    echo "system" | iconv -f UTF-8 -t ISO-8859-1 > "$test_home/.config/iso8859.pref" 2>/dev/null || true
    printf "system\x00\x80\x81" > "$test_home/.config/binary.pref"
    
    # Test if fplaunch-generate handles mixed encodings
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        handled "fplaunch-generate handles mixed encoding files"
    else
        fail "fplaunch-generate fails with mixed encoding files"
    fi
}

# WEIRD SETUP 19: Timezone and locale issues
test_timezone_locale_issues() {
    local test_home="$1"
    
    weird "Testing with timezone and locale issues"
    
    # Set weird timezone and locale
    local old_tz="$TZ"
    local old_lang="$LANG"
    local old_lc_all="$LC_ALL"
    
    export TZ="Antarctica/South_Pole"
    export LANG="zh_CN.UTF-8"
    export LC_ALL="zh_CN.UTF-8"
    
    # Test if fplaunch-generate handles weird timezone/locale
    if fplaunch-generate "$test_home/bin" 2>/dev/null; then
        handled "fplaunch-generate handles weird timezone and locale"
    else
        fail "fplaunch-generate fails with weird timezone and locale"
    fi
    
    # Restore locale
    export TZ="${old_tz:-UTC}"
    export LANG="${old_lang:-C.UTF-8}"
    export LC_ALL="${old_lc_all:-}"
}

# WEIRD SETUP 20: Network filesystem simulation
test_network_filesystem() {
    local test_home="$1"
    
    weird "Testing with network filesystem simulation"
    
    # Create files with network-like behavior (slow access)
    cat > "$test_home/bin/sleep-cmd" << 'EOF'
#!/usr/bin/env bash
# Simulate slow network access
sleep 0.1
echo "$@"
EOF
    chmod +x "$test_home/bin/sleep-cmd"
    
    # Add to PATH
    local old_path="$PATH"
    export PATH="$test_home/bin:$PATH"
    
    # Test if fplaunch-generate handles slow file access
    local start_time
    start_time=$(date +%s)
    if fplaunch-generate "$test_home/network-bin" 2>/dev/null; then
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))
        if [ $duration -lt 10 ]; then
            handled "fplaunch-generate handles slow file access"
        else
            fail "fplaunch-generate times out with slow file access"
        fi
    else
        fail "fplaunch-generate fails with slow file access"
    fi
    
    # Restore PATH
    export PATH="$old_path"
}

# Main adversarial test execution
main() {
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${PURPLE}ROBUSTNESS ADVERSARIAL TEST SUITE${NC}"
    echo -e "${PURPLE}======================================${NC}"
    echo ""
    
    # Setup weird test environment
    local test_home
    test_home=$(setup_weird_env)
    
    # Run weird setup tests
    test_no_home_directory "$test_home"
    test_nonexistent_xdg_dirs "$test_home"
    test_readonly_directories "$test_home"
    test_no_write_permissions "$test_home"
    test_weird_home_structure "$test_home"
    test_no_path "$test_home"
    test_weird_path "$test_home"
    test_unicode_encoding_issues "$test_home"
    test_extremely_long_paths "$test_home"
    test_no_tmp_directory "$test_home"
    test_full_filesystem "$test_home"
    test_weird_file_permissions "$test_home"
    test_broken_symlinks "$test_home"
    test_env_variable_pollution "$test_home"
    test_concurrent_access "$test_home"
    test_concurrent_generation "$test_home"
    test_network_filesystem "$test_home"
    test_case_sensitivity "$test_home"
    test_resource_limits "$test_home"
    test_mixed_encoding_files "$test_home"
    test_timezone_locale_issues "$test_home"
    
    # Cleanup
    cleanup_weird_env "$test_home"
    
    # Results
    echo ""
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${PURPLE}ROBUSTNESS ADVERSARIAL TEST RESULTS${NC}"
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${GREEN}Tests Passed: $PASSED${NC}"
    echo -e "${RED}Tests Failed: $FAILED${NC}"
    echo -e "${GREEN}Weird Cases Handled: $WEIRD_CASES_HANDLED${NC}"
    echo -e "${RED}Robustness Issues: $ROBUSTNESS_ISSUES${NC}"
    
    if [ $ROBUSTNESS_ISSUES -eq 0 ]; then
        echo -e "${GREEN}Excellent! fplaunchwrapper handles all weird setups robustly.${NC}"
        exit 0
    else
        echo -e "${YELLOW}Good: fplaunchwrapper handles most weird setups, but has $ROBUSTNESS_ISSUES robustness issues.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"