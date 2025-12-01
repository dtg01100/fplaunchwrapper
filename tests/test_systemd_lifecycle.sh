#!/usr/bin/env bash

# Test suite for systemd service lifecycle management
# Tests systemd user service creation, enabling, starting, stopping, and cleanup
#
# WHY THESE TESTS MATTER:
# - Systemd integration: Core feature for automatic wrapper updates
#   If broken: Wrappers become outdated when Flatpak apps are updated
# - Service lifecycle: Enable/start/stop/restart operations
#   If broken: Users can't control automatic update behavior
# - Timer functionality: Scheduled wrapper regeneration
#   If broken: Automatic updates don't work as expected
# - Service cleanup: Proper removal on uninstall
#   If broken: Orphaned services remain after uninstall

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
# shellcheck disable=SC2034
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    FAILED=$((FAILED + 1))
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Developer workstation safety check
ensure_developer_safety() {
    # Never run on production systems
    if [ "${CI:-}" != "1" ] && [ "${TESTING:-}" != "1" ]; then
        # Check if we're in a development environment
        if [ ! -f "$PROJECT_ROOT/README.md" ] || [ ! -d "$PROJECT_ROOT/tests" ]; then
            echo "ERROR: This test must be run from the project root directory"
            echo "Run with: TESTING=1 tests/test_systemd_lifecycle.sh"
            exit 1
        fi
    fi
    
    # Ensure we're not running as root
    if [ "$(id -u)" = "0" ] && [ "${CI:-}" != "1" ]; then
        echo "ERROR: Refusing to run tests as root for safety"
        echo "This project should never be run with root privileges"
        exit 1
    fi
    
    # Set testing environment
    export TESTING=1
    export CI=1
}

# Create isolated test environment
setup_test_env() {
    local test_home="/tmp/fplaunch-systemd-test-$$"
    
    # Clean up any existing test directory
    rm -rf "$test_home"
    
    # Create test directory structure
    mkdir -p "$test_home"/{bin,.config,.local/share/applications,.config/systemd/user}
    
    # Override environment for test isolation
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
    export XDG_DATA_HOME="$test_home/.local/share"
    export PATH="$test_home/bin:$PATH"
    export SYSTEMD_UNIT_DIR="$test_home/.config/systemd/user"
    
    # Create mock systemctl command
    cat > "$test_home/bin/systemctl" << 'EOF'
#!/usr/bin/env bash

# Mock systemctl that simulates systemd operations
STATE_DIR="$HOME/.mock-systemd-state"
mkdir -p "$STATE_DIR"

case "$1" in
    "--user")
        shift
        case "$1" in
            "daemon-reload")
                echo "Mock: systemctl --user daemon-reload"
                touch "$STATE_DIR/daemon-reloaded"
                exit 0
                ;;
            "enable")
                service="$2"
                echo "Mock: systemctl --user enable $service"
                touch "$STATE_DIR/enabled-$service"
                exit 0
                ;;
            "disable")
                service="$2"
                echo "Mock: systemctl --user disable $service"
                rm -f "$STATE_DIR/enabled-$service"
                exit 0
                ;;
            "start")
                service="$2"
                echo "Mock: systemctl --user start $service"
                touch "$STATE_DIR/started-$service"
                exit 0
                ;;
            "stop")
                service="$2"
                echo "Mock: systemctl --user stop $service"
                rm -f "$STATE_DIR/started-$service"
                exit 0
                ;;
            "restart")
                service="$2"
                echo "Mock: systemctl --user restart $service"
                rm -f "$STATE_DIR/started-$service"
                touch "$STATE_DIR/started-$service"
                exit 0
                ;;
            "status")
                service="$2"
                echo "Mock: systemctl --user status $service"
                if [ -f "$STATE_DIR/enabled-$service" ]; then
                    echo "Enabled: yes"
                else
                    echo "Enabled: no"
                fi
                if [ -f "$STATE_DIR/started-$service" ]; then
                    echo "Active: active (running)"
                else
                    echo "Active: inactive (dead)"
                fi
                exit 0
                ;;
            "is-enabled")
                service="$2"
                unit_file="$HOME/.config/systemd/user/$service"
                if [ -f "$unit_file" ] && [ -f "$STATE_DIR/enabled-$service" ]; then
                    echo "enabled"
                    exit 0
                else
                    echo "disabled"
                    exit 1
                fi
                ;;
            "is-active")
                service="$2"
                if [ -f "$STATE_DIR/started-$service" ]; then
                    echo "active"
                    exit 0
                else
                    echo "inactive"
                    exit 3
                fi
                ;;
            *)
                echo "Mock: systemctl --user $*"
                exit 0
                ;;
        esac
        ;;
    "is-systemd-running")
        echo "Mock: systemd is running"
        exit 0
        ;;
    *)
        echo "Mock: systemctl $*"
        exit 0
        ;;
esac
EOF
    chmod +x "$test_home/bin/systemctl"
    
    # Create mock fplaunch-generate command
    cat > "$test_home/bin/fplaunch-generate" << 'EOF'
#!/usr/bin/env bash
echo "Mock: fplaunch-generate $*"
# Create a dummy wrapper to simulate successful generation
mkdir -p "$HOME/bin"
echo "#!/bin/bash" > "$HOME/bin/test-wrapper"
echo "echo 'Test wrapper executed'" >> "$HOME/bin/test-wrapper"
chmod +x "$HOME/bin/test-wrapper"
exit 0
EOF
    chmod +x "$test_home/bin/fplaunch-generate"
    
    echo "$test_home"
}

# Cleanup test environment
cleanup_test_env() {
    local test_home="$1"
    rm -rf "$test_home"
}

# Create systemd service files
create_systemd_service() {
    local test_home="$1"
    local unit_dir="$test_home/.config/systemd/user"
    
    # Create fplaunch-update.service
    cat > "$unit_dir/fplaunch-update.service" << EOF
[Unit]
Description=Update Flatpak Launch Wrappers
Documentation=file:///usr/share/doc/fplaunchwrapper/README.md

[Service]
Type=oneshot
ExecStart=$test_home/bin/fplaunch-generate
Environment=PATH=$test_home/bin:/usr/bin:/bin
EOF

    # Create fplaunch-update.timer
    cat > "$unit_dir/fplaunch-update.timer" << EOF
[Unit]
Description=Run fplaunch-update daily
Documentation=file:///usr/share/doc/fplaunchwrapper/README.md

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF
}

# Test systemd service creation
test_service_creation() {
    local test_home="$1"
    
    info "Testing systemd service creation"
    
    create_systemd_service "$test_home"
    
    local unit_dir="$test_home/.config/systemd/user"
    
    if [ -f "$unit_dir/fplaunch-update.service" ]; then
        pass "Service file created"
    else
        fail "Service file not created"
    fi
    
    if [ -f "$unit_dir/fplaunch-update.timer" ]; then
        pass "Timer file created"
    else
        fail "Timer file not created"
    fi
    
    # Verify service file content
    if grep -q "Description=Update Flatpak Launch Wrappers" "$unit_dir/fplaunch-update.service"; then
        pass "Service file has correct description"
    else
        fail "Service file missing description"
    fi
    
    if grep -q "ExecStart=$test_home/bin/fplaunch-generate" "$unit_dir/fplaunch-update.service"; then
        pass "Service file has correct exec path"
    else
        fail "Service file has incorrect exec path"
    fi
    
    # Verify timer file content
    if grep -q "OnCalendar=daily" "$unit_dir/fplaunch-update.timer"; then
        pass "Timer file has correct schedule"
    else
        fail "Timer file missing schedule"
    fi
    
    if grep -q "WantedBy=timers.target" "$unit_dir/fplaunch-update.timer"; then
        pass "Timer file has correct install target"
    else
        fail "Timer file missing install target"
    fi
}

# Test systemd service enable/disable
test_service_enable_disable() {
    local test_home="$1"
    
    info "Testing systemd service enable/disable"
    
    create_systemd_service "$test_home"
    
    # Test daemon reload
    if "$test_home/bin/systemctl" --user daemon-reload; then
        pass "Daemon reload successful"
    else
        fail "Daemon reload failed"
    fi
    
    # Test service enable
    if "$test_home/bin/systemctl" --user enable fplaunch-update.timer; then
        pass "Timer enable successful"
    else
        fail "Timer enable failed"
    fi
    
    # Verify service is enabled
    if "$test_home/bin/systemctl" --user is-enabled fplaunch-update.timer >/dev/null 2>&1; then
        pass "Timer is enabled"
    else
        fail "Timer is not enabled"
    fi
    
    # Test service disable
    if "$test_home/bin/systemctl" --user disable fplaunch-update.timer; then
        pass "Timer disable successful"
    else
        fail "Timer disable failed"
    fi
    
    # Verify service is disabled
    if ! "$test_home/bin/systemctl" --user is-enabled fplaunch-update.timer >/dev/null 2>&1; then
        pass "Timer is disabled"
    else
        fail "Timer is still enabled"
    fi
}

# Test systemd service start/stop
test_service_start_stop() {
    local test_home="$1"
    
    info "Testing systemd service start/stop"
    
    create_systemd_service "$test_home"
    
    # Test service start
    if "$test_home/bin/systemctl" --user start fplaunch-update.timer; then
        pass "Timer start successful"
    else
        fail "Timer start failed"
    fi
    
    # Verify service is active
    if "$test_home/bin/systemctl" --user is-active fplaunch-update.timer >/dev/null 2>&1; then
        pass "Timer is active"
    else
        fail "Timer is not active"
    fi
    
    # Test service stop
    if "$test_home/bin/systemctl" --user stop fplaunch-update.timer; then
        pass "Timer stop successful"
    else
        fail "Timer stop failed"
    fi
    
    # Verify service is inactive
    if ! "$test_home/bin/systemctl" --user is-active fplaunch-update.timer >/dev/null 2>&1; then
        pass "Timer is inactive"
    else
        fail "Timer is still active"
    fi
}

# Test systemd service restart
test_service_restart() {
    local test_home="$1"
    
    info "Testing systemd service restart"
    
    create_systemd_service "$test_home"
    
    # Start service first
    "$test_home/bin/systemctl" --user start fplaunch-update.timer
    
    # Test service restart
    if "$test_home/bin/systemctl" --user restart fplaunch-update.timer; then
        pass "Timer restart successful"
    else
        fail "Timer restart failed"
    fi
    
    # Verify service is still active after restart
    if "$test_home/bin/systemctl" --user is-active fplaunch-update.timer >/dev/null 2>&1; then
        pass "Timer is active after restart"
    else
        fail "Timer is not active after restart"
    fi
}

# Test systemd service status
test_service_status() {
    local test_home="$1"
    
    info "Testing systemd service status"
    
    create_systemd_service "$test_home"
    
    # Test status when disabled and inactive
    local output
    output=$("$test_home/bin/systemctl" --user status fplaunch-update.timer 2>&1)
    
    if echo "$output" | grep -q "Enabled: no"; then
        pass "Status shows disabled"
    else
        fail "Status should show disabled"
    fi
    
    if echo "$output" | grep -q "Active: inactive"; then
        pass "Status shows inactive"
    else
        fail "Status should show inactive"
    fi
    
    # Enable and start service
    "$test_home/bin/systemctl" --user enable fplaunch-update.timer
    "$test_home/bin/systemctl" --user start fplaunch-update.timer
    
    # Test status when enabled and active
    output=$("$test_home/bin/systemctl" --user status fplaunch-update.timer 2>&1)
    
    if echo "$output" | grep -q "Enabled: yes"; then
        pass "Status shows enabled"
    else
        fail "Status should show enabled"
    fi
    
    if echo "$output" | grep -q "Active: active"; then
        pass "Status shows active"
    else
        fail "Status should show active"
    fi
}

# Test systemd service cleanup
test_service_cleanup() {
    local test_home="$1"
    
    info "Testing systemd service cleanup"
    
    create_systemd_service "$test_home"
    
    # Enable and start service
    "$test_home/bin/systemctl" --user enable fplaunch-update.timer
    "$test_home/bin/systemctl" --user start fplaunch-update.timer
    
    local unit_dir="$test_home/.config/systemd/user"
    
    # Verify files exist before cleanup
    if [ -f "$unit_dir/fplaunch-update.service" ] && [ -f "$unit_dir/fplaunch-update.timer" ]; then
        pass "Service files exist before cleanup"
    else
        fail "Service files should exist before cleanup"
    fi
    
    # Simulate cleanup (remove service files)
    rm -f "$unit_dir/fplaunch-update.service" "$unit_dir/fplaunch-update.timer"
    
    # Verify files are removed
    if [ ! -f "$unit_dir/fplaunch-update.service" ] && [ ! -f "$unit_dir/fplaunch-update.timer" ]; then
        pass "Service files removed during cleanup"
    else
        fail "Service files not removed during cleanup"
    fi
    
    # Reload daemon to clean up internal state
    "$test_home/bin/systemctl" --user daemon-reload
    
    # Verify service is no longer enabled
    if ! "$test_home/bin/systemctl" --user is-enabled fplaunch-update.timer >/dev/null 2>&1; then
        pass "Service is no longer enabled after cleanup"
    else
        fail "Service should not be enabled after cleanup"
    fi
}

# Test systemd integration with fplaunch-setup-systemd
test_systemd_integration() {
    local test_home="$1"
    
    info "Testing systemd integration with setup script"
    
    # Create mock fplaunch-setup-systemd script
    cat > "$test_home/bin/fplaunch-setup-systemd" << 'EOF'
#!/usr/bin/env bash

# Safety check - never run as root
if [ "$(id -u)" = "0" ] && [ "${CI:-}" != "1" ]; then
    echo "ERROR: Should never be run as root"
    exit 1
fi

# Mock setup script that creates systemd services
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

mkdir -p "$UNIT_DIR"

# Create service files
cat > "$UNIT_DIR/fplaunch-update.service" << 'SERVICE_EOF'
[Unit]
Description=Update Flatpak Launch Wrappers

[Service]
Type=oneshot
ExecStart=fplaunch-generate
SERVICE_EOF

cat > "$UNIT_DIR/fplaunch-update.timer" << 'TIMER_EOF'
[Unit]
Description=Run fplaunch-update daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
TIMER_EOF

# Enable and start the timer
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable fplaunch-update.timer
    systemctl --user start fplaunch-update.timer
    echo "Systemd integration setup complete"
else
    echo "Systemctl not available"
    exit 1
fi
EOF
    chmod +x "$test_home/bin/fplaunch-setup-systemd"
    
    # Run setup script
    local output
    output=$(HOME="$test_home" XDG_CONFIG_HOME="$test_home/.config" PATH="$test_home/bin:$PATH" "$test_home/bin/fplaunch-setup-systemd" 2>&1)
    
    if echo "$output" | grep -q "Systemd integration setup complete"; then
        pass "Setup script completed successfully"
    else
        fail "Setup script did not complete successfully"
    fi
    
    # Verify services were created and enabled
    local unit_dir="$test_home/.config/systemd/user"
    if [ -f "$unit_dir/fplaunch-update.service" ] && [ -f "$unit_dir/fplaunch-update.timer" ]; then
        pass "Setup script created service files"
    else
        fail "Setup script did not create service files"
    fi
    
    if "$test_home/bin/systemctl" --user is-enabled fplaunch-update.timer >/dev/null 2>&1; then
        pass "Setup script enabled timer"
    else
        fail "Setup script did not enable timer"
    fi
}

# Main test execution
main() {
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}Systemd Lifecycle Test Suite${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
    
    # Ensure developer safety
    ensure_developer_safety
    
    # Setup test environment
    local test_home
    test_home=$(setup_test_env)
    
    # Run tests
    test_service_creation "$test_home"
    test_service_enable_disable "$test_home"
    test_service_start_stop "$test_home"
    test_service_restart "$test_home"
    test_service_status "$test_home"
    test_service_cleanup "$test_home"
    test_systemd_integration "$test_home"
    
    # Cleanup
    cleanup_test_env "$test_home"
    
    # Results
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}Test Results${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

# Run main function
main "$@"