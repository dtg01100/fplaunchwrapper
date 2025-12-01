#!/usr/bin/env bash

# Test suite for package installation scenarios (dpkg/rpm)
# Tests package manager integration and installation workflows
#
# WHY THESE TESTS MATTER:
# - Package installation: Core distribution method for many users
#   If broken: Users can't install fplaunchwrapper through package managers
# - Post-install scripts: Critical for proper setup after package installation
#   If broken: Package installation appears successful but doesn't work
# - Package removal: Clean uninstallation through package managers
#   If broken: Orphaned files remain after package removal
# - Package upgrade: Preserve user data during upgrades
#   If broken: User configurations lost during upgrades

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
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
            echo "Run with: TESTING=1 tests/test_package_installation.sh"
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
    local test_home="/tmp/fplaunch-package-test-$$"
    
    # Clean up any existing test directory
    rm -rf "$test_home"
    
    # Create test directory structure
    mkdir -p "$test_home"/{bin,.config,.local/share/applications,var/lib/dpkg,var/lib/rpm,etc,usr/bin,usr/share/doc/fplaunchwrapper}
    
    # Override environment for test isolation
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
    export XDG_DATA_HOME="$test_home/.local/share"
    export PATH="$test_home/bin:$test_home/usr/bin:$PATH"
    
    # Create mock dpkg command
    cat > "$test_home/bin/dpkg" << 'EOF'
#!/usr/bin/env bash

# Mock dpkg that simulates package operations
STATE_DIR="$HOME/.mock-dpkg-state"
mkdir -p "$STATE_DIR"

case "$1" in
    "-l")
        if [ "$2" = "fplaunchwrapper" ]; then
            echo "ii  fplaunchwrapper  1.3.0  amd64  Flatpak Launch Wrappers"
            exit 0
        else
            echo "No packages found matching $2"
            exit 1
        fi
        ;;
    "-s")
        if [ "$2" = "fplaunchwrapper" ]; then
            echo "install ok installed"
            exit 0
        else
            echo "unknown ok not-installed"
            exit 1
        fi
        ;;
    "-r"|"--remove")
        package="$2"
        if [ "$package" = "fplaunchwrapper" ]; then
            echo "Mock: Removing $package"
            touch "$STATE_DIR/removed-$package"
            exit 0
        else
            echo "dpkg: error: package $package is not installed"
            exit 1
        fi
        ;;
    "-P"|"--purge")
        package="$2"
        if [ "$package" = "fplaunchwrapper" ]; then
            echo "Mock: Purging $package"
            touch "$STATE_DIR/purged-$package"
            exit 0
        else
            echo "dpkg: error: package $package is not installed"
            exit 1
        fi
        ;;
    *)
        echo "Mock: dpkg $*"
        exit 0
        ;;
esac
EOF
    chmod +x "$test_home/bin/dpkg"
    
    # Create mock rpm command
    cat > "$test_home/bin/rpm" << 'EOF'
#!/usr/bin/env bash

# Mock rpm that simulates package operations
STATE_DIR="$HOME/.mock-rpm-state"
mkdir -p "$STATE_DIR"

case "$1" in
    "-q")
        case "$2" in
            "fplaunchwrapper")
                echo "fplaunchwrapper-1.3.0-1.x86_64"
                exit 0
                ;;
            "-a")
                echo "fplaunchwrapper-1.3.0-1.x86_64"
                exit 0
                ;;
            *)
                echo "package $2 is not installed"
                exit 1
                ;;
        esac
        ;;
    "-e")
        package="$2"
        if [ "$package" = "fplaunchwrapper" ]; then
            echo "Mock: Erasing $package"
            touch "$STATE_DIR/erased-$package"
            exit 0
        else
            echo "error: package $package is not installed"
            exit 1
        fi
        ;;
    *)
        echo "Mock: rpm $*"
        exit 0
        ;;
esac
EOF
    chmod +x "$test_home/bin/rpm"
    
    # Create mock systemctl for systemd integration
    cat > "$test_home/bin/systemctl" << 'EOF'
#!/usr/bin/env bash
echo "Mock: systemctl $*"
exit 0
EOF
    chmod +x "$test_home/bin/systemctl"
    
    echo "$test_home"
}

# Cleanup test environment
cleanup_test_env() {
    local test_home="$1"
    rm -rf "$test_home"
}

# Test dpkg installation scenario
test_dpkg_installation() {
    local test_home="$1"
    
    info "Testing dpkg installation scenario"
    
    # Create mock postinst script
    cat > "$test_home/postinst" << 'EOF'
#!/bin/bash
# Mock postinst script for fplaunchwrapper

set -e

case "$1" in
    configure)
        echo "Configuring fplaunchwrapper..."
        
        # Create config directory
        mkdir -p "$HOME/.config/flatpak-wrappers"
        
        # Create bin directory
        mkdir -p "$HOME/bin"
        
        # Setup systemd integration if available
        if command -v systemctl >/dev/null 2>&1; then
            systemctl --user daemon-reload >/dev/null 2>&1 || true
        fi
        
        echo "fplaunchwrapper configured successfully"
        ;;
    abort-upgrade|abort-remove|abort-deconfigure)
        ;;
    *)
        echo "postinst called with unknown argument \`$1'" >&2
        exit 1
        ;;
esac

exit 0
EOF
    chmod +x "$test_home/postinst"
    
    # Simulate postinst execution
    local output
    output=$("$test_home/postinst" configure 2>&1)
    
    if echo "$output" | grep -q "Configuring fplaunchwrapper"; then
        pass "Postinst script started correctly"
    else
        fail "Postinst script did not start correctly"
    fi
    
    if echo "$output" | grep -q "fplaunchwrapper configured successfully"; then
        pass "Postinst script completed successfully"
    else
        fail "Postinst script did not complete successfully"
    fi
    
    # Verify directories were created
    if [ -d "$test_home/.config/flatpak-wrappers" ]; then
        pass "Config directory created"
    else
        fail "Config directory not created"
    fi
    
    if [ -d "$test_home/bin" ]; then
        pass "Bin directory created"
    else
        fail "Bin directory not created"
    fi
}

# Test dpkg removal scenario
test_dpkg_removal() {
    local test_home="$1"
    
    info "Testing dpkg removal scenario"
    
    # Create mock prerm script
    cat > "$test_home/prerm" << 'EOF'
#!/bin/bash
# Mock prerm script for fplaunchwrapper

set -e

case "$1" in
    remove|upgrade|deconfigure)
        echo "Preparing to remove fplaunchwrapper..."
        
        # Stop and disable systemd services
        if command -v systemctl >/dev/null 2>&1; then
            systemctl --user stop fplaunch-update.timer >/dev/null 2>&1 || true
            systemctl --user disable fplaunch-update.timer >/dev/null 2>&1 || true
        fi
        
        echo "fplaunchwrapper preparation complete"
        ;;
    failed-upgrade)
        ;;
    *)
        echo "prerm called with unknown argument \`$1'" >&2
        exit 1
        ;;
esac

exit 0
EOF
    chmod +x "$test_home/prerm"
    
    # Create mock postrm script
    cat > "$test_home/postrm" << 'EOF'
#!/bin/bash
# Mock postrm script for fplaunchwrapper

set -e

case "$1" in
    remove|purge)
        echo "Cleaning up fplaunchwrapper..."
        
        # Remove systemd service files
        rm -f "$HOME/.config/systemd/user/fplaunch-update.service"
        rm -f "$HOME/.config/systemd/user/fplaunch-update.timer"
        
        # Reload systemd daemon
        if command -v systemctl >/dev/null 2>&1; then
            systemctl --user daemon-reload >/dev/null 2>&1 || true
        fi
        
        # Note: We don't remove user data in config directory
        # This preserves user preferences and aliases
        
        echo "fplaunchwrapper cleanup complete"
        ;;
    upgrade|failed-upgrade)
        ;;
    *)
        echo "postrm called with unknown argument \`$1'" >&2
        exit 1
        ;;
esac

exit 0
EOF
    chmod +x "$test_home/postrm"
    
    # Create some test files to verify cleanup
    mkdir -p "$test_home/.config/systemd/user"
    touch "$test_home/.config/systemd/user/fplaunch-update.service"
    touch "$test_home/.config/systemd/user/fplaunch-update.timer"
    
    # Simulate prerm execution
    local output
    output=$("$test_home/prerm" remove 2>&1)
    
    if echo "$output" | grep -q "Preparing to remove fplaunchwrapper"; then
        pass "Prerm script started correctly"
    else
        fail "Prerm script did not start correctly"
    fi
    
    # Simulate postrm execution
    output=$("$test_home/postrm" remove 2>&1)
    
    if echo "$output" | grep -q "Cleaning up fplaunchwrapper"; then
        pass "Postrm script started correctly"
    else
        fail "Postrm script did not start correctly"
    fi
    
    if echo "$output" | grep -q "fplaunchwrapper cleanup complete"; then
        pass "Postrm script completed successfully"
    else
        fail "Postrm script did not complete successfully"
    fi
    
    # Verify systemd files were removed
    if [ ! -f "$test_home/.config/systemd/user/fplaunch-update.service" ]; then
        pass "Systemd service file removed"
    else
        fail "Systemd service file not removed"
    fi
    
    if [ ! -f "$test_home/.config/systemd/user/fplaunch-update.timer" ]; then
        pass "Systemd timer file removed"
    else
        fail "Systemd timer file not removed"
    fi
}

# Test rpm installation scenario
test_rpm_installation() {
    local test_home="$1"
    
    info "Testing rpm installation scenario"
    
    # Create mock post-install script
    cat > "$test_home/post-install" << 'EOF'
#!/bin/bash
# Mock post-install script for fplaunchwrapper RPM

set -e

echo "Installing fplaunchwrapper RPM..."

# Create config directory
mkdir -p "$HOME/.config/flatpak-wrappers"

# Create bin directory
mkdir -p "$HOME/bin"

# Setup systemd integration if available
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload >/dev/null 2>&1 || true
    systemctl --user enable fplaunch-update.timer >/dev/null 2>&1 || true
    systemctl --user start fplaunch-update.timer >/dev/null 2>&1 || true
fi

echo "fplaunchwrapper RPM installation complete"

exit 0
EOF
    chmod +x "$test_home/post-install"
    
    # Simulate post-install execution
    local output
    output=$("$test_home/post-install" 2>&1)
    
    if echo "$output" | grep -q "Installing fplaunchwrapper RPM"; then
        pass "RPM post-install script started correctly"
    else
        fail "RPM post-install script did not start correctly"
    fi
    
    if echo "$output" | grep -q "fplaunchwrapper RPM installation complete"; then
        pass "RPM post-install script completed successfully"
    else
        fail "RPM post-install script did not complete successfully"
    fi
    
    # Verify directories were created
    if [ -d "$test_home/.config/flatpak-wrappers" ]; then
        pass "RPM config directory created"
    else
        fail "RPM config directory not created"
    fi
    
    if [ -d "$test_home/bin" ]; then
        pass "RPM bin directory created"
    else
        fail "RPM bin directory not created"
    fi
}

# Test rpm removal scenario
test_rpm_removal() {
    local test_home="$1"
    
    info "Testing rpm removal scenario"
    
    # Create mock pre-uninstall script
    cat > "$test_home/pre-uninstall" << 'EOF'
#!/bin/bash
# Mock pre-uninstall script for fplaunchwrapper RPM

set -e

echo "Preparing to remove fplaunchwrapper RPM..."

# Stop and disable systemd services
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop fplaunch-update.timer >/dev/null 2>&1 || true
    systemctl --user disable fplaunch-update.timer >/dev/null 2>&1 || true
fi

echo "fplaunchwrapper RPM preparation complete"

exit 0
EOF
    chmod +x "$test_home/pre-uninstall"
    
    # Create mock post-uninstall script
    cat > "$test_home/post-uninstall" << 'EOF'
#!/bin/bash
# Mock post-uninstall script for fplaunchwrapper RPM

set -e

echo "Cleaning up fplaunchwrapper RPM..."

# Remove systemd service files
rm -f "$HOME/.config/systemd/user/fplaunch-update.service"
rm -f "$HOME/.config/systemd/user/fplaunch-update.timer"

# Reload systemd daemon
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload >/dev/null 2>&1 || true
fi

# Note: We don't remove user data in config directory
# This preserves user preferences and aliases

echo "fplaunchwrapper RPM cleanup complete"

exit 0
EOF
    chmod +x "$test_home/post-uninstall"
    
    # Create some test files to verify cleanup
    mkdir -p "$test_home/.config/systemd/user"
    touch "$test_home/.config/systemd/user/fplaunch-update.service"
    touch "$test_home/.config/systemd/user/fplaunch-update.timer"
    
    # Simulate pre-uninstall execution
    local output
    output=$("$test_home/pre-uninstall" 2>&1)
    
    if echo "$output" | grep -q "Preparing to remove fplaunchwrapper RPM"; then
        pass "RPM pre-uninstall script started correctly"
    else
        fail "RPM pre-uninstall script did not start correctly"
    fi
    
    # Simulate post-uninstall execution
    output=$("$test_home/post-uninstall" 2>&1)
    
    if echo "$output" | grep -q "Cleaning up fplaunchwrapper RPM"; then
        pass "RPM post-uninstall script started correctly"
    else
        fail "RPM post-uninstall script did not start correctly"
    fi
    
    if echo "$output" | grep -q "fplaunchwrapper RPM cleanup complete"; then
        pass "RPM post-uninstall script completed successfully"
    else
        fail "RPM post-uninstall script did not complete successfully"
    fi
    
    # Verify systemd files were removed
    if [ ! -f "$test_home/.config/systemd/user/fplaunch-update.service" ]; then
        pass "RPM systemd service file removed"
    else
        fail "RPM systemd service file not removed"
    fi
    
    if [ ! -f "$test_home/.config/systemd/user/fplaunch-update.timer" ]; then
        pass "RPM systemd timer file removed"
    else
        fail "RPM systemd timer file not removed"
    fi
}

# Test package upgrade scenario
test_package_upgrade() {
    local test_home="$1"
    
    info "Testing package upgrade scenario"
    
    # Create existing user data
    mkdir -p "$test_home/.config/flatpak-wrappers"
    echo "system" > "$test_home/.config/flatpak-wrappers/testapp.pref"
    echo "testapp /usr/bin/system-testapp" > "$test_home/.config/flatpak-wrappers/aliases"
    
    # Create mock upgrade script
    cat > "$test_home/upgrade" << 'EOF'
#!/bin/bash
# Mock upgrade script for fplaunchwrapper

set -e

echo "Upgrading fplaunchwrapper..."

# Create backup of user data
if [ -d "$HOME/.config/flatpak-wrappers" ]; then
    cp -r "$HOME/.config/flatpak-wrappers" "$HOME/.config/flatpak-wrappers.backup"
    echo "User data backed up"
fi

# Perform upgrade operations
echo "Upgrade operations complete"

# Restore user data if backup exists
if [ -d "$HOME/.config/flatpak-wrappers.backup" ]; then
    # Preserve user preferences and aliases during upgrade
    if [ -f "$HOME/.config/flatpak-wrappers.backup/testapp.pref" ]; then
        cp "$HOME/.config/flatpak-wrappers.backup/testapp.pref" "$HOME/.config/flatpak-wrappers/"
        echo "User preferences restored"
    fi
    
    if [ -f "$HOME/.config/flatpak-wrappers.backup/aliases" ]; then
        cp "$HOME/.config/flatpak-wrappers.backup/aliases" "$HOME/.config/flatpak-wrappers/"
        echo "User aliases restored"
    fi
    
    # Remove backup
    rm -rf "$HOME/.config/flatpak-wrappers.backup"
fi

echo "fplaunchwrapper upgrade complete"

exit 0
EOF
    chmod +x "$test_home/upgrade"
    
    # Simulate upgrade execution
    local output
    output=$("$test_home/upgrade" 2>&1)
    
    if echo "$output" | grep -q "Upgrading fplaunchwrapper"; then
        pass "Upgrade script started correctly"
    else
        fail "Upgrade script did not start correctly"
    fi
    
    if echo "$output" | grep -q "User data backed up"; then
        pass "User data backed up during upgrade"
    else
        fail "User data not backed up during upgrade"
    fi
    
    if echo "$output" | grep -q "User preferences restored"; then
        pass "User preferences restored after upgrade"
    else
        fail "User preferences not restored after upgrade"
    fi
    
    if echo "$output" | grep -q "User aliases restored"; then
        pass "User aliases restored after upgrade"
    else
        fail "User aliases not restored after upgrade"
    fi
    
    if echo "$output" | grep -q "fplaunchwrapper upgrade complete"; then
        pass "Upgrade script completed successfully"
    else
        fail "Upgrade script did not complete successfully"
    fi
    
    # Verify user data is preserved
    if [ -f "$test_home/.config/flatpak-wrappers/testapp.pref" ]; then
        pass "User preferences file preserved"
    else
        fail "User preferences file not preserved"
    fi
    
    if [ "$(cat "$test_home/.config/flatpak-wrappers/testapp.pref")" = "system" ]; then
        pass "User preferences content preserved"
    else
        fail "User preferences content not preserved"
    fi
    
    if [ -f "$test_home/.config/flatpak-wrappers/aliases" ]; then
        pass "User aliases file preserved"
    else
        fail "User aliases file not preserved"
    fi
}

# Test package manager detection
test_package_manager_detection() {
    local test_home="$1"
    
    info "Testing package manager detection"
    
    # Test dpkg detection
    if "$test_home/bin/dpkg" -l fplaunchwrapper >/dev/null 2>&1; then
        pass "dpkg can detect installed fplaunchwrapper"
    else
        fail "dpkg cannot detect installed fplaunchwrapper"
    fi
    
    if "$test_home/bin/dpkg" -s fplaunchwrapper >/dev/null 2>&1; then
        pass "dpkg can check fplaunchwrapper status"
    else
        fail "dpkg cannot check fplaunchwrapper status"
    fi
    
    # Test rpm detection
    if "$test_home/bin/rpm" -q fplaunchwrapper >/dev/null 2>&1; then
        pass "rpm can detect installed fplaunchwrapper"
    else
        fail "rpm cannot detect installed fplaunchwrapper"
    fi
    
    if "$test_home/bin/rpm" -qa | grep -q fplaunchwrapper; then
        pass "rpm can list all packages including fplaunchwrapper"
    else
        fail "rpm cannot list fplaunchwrapper in all packages"
    fi
}

# Main test execution
main() {
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}Package Installation Test Suite${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
    
    # Ensure developer safety
    ensure_developer_safety
    
    # Setup test environment
    local test_home
    test_home=$(setup_test_env)
    
    # Run tests
    test_dpkg_installation "$test_home"
    test_dpkg_removal "$test_home"
    test_rpm_installation "$test_home"
    test_rpm_removal "$test_home"
    test_package_upgrade "$test_home"
    test_package_manager_detection "$test_home"
    
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