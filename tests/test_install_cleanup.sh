#!/usr/bin/env bash

# Test suite for install.sh and cleanup/uninstall workflows
# Ensures minimal footprint on install and complete removal on cleanup

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Create a fresh test environment
setup_test_env() {
    local test_home="$1"
    
    # Clean slate
    rm -rf "$test_home"
    mkdir -p "$test_home"
    
    export HOME="$test_home"
    export XDG_CONFIG_HOME="$test_home/.config"
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

# Test 1: Manual install creates expected minimal set of files
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

# Test 2: fplaunch-cleanup removes all installed artifacts
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
echo "Installation & Cleanup Test Suite"
echo "======================================"

test_manual_install_minimal
test_cleanup_complete
test_cleanup_with_systemd
test_package_regenerate_minimal
test_install_idempotent
test_cleanup_dry_run

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
    exit 0
else
    echo "Some tests failed."
    exit 1
fi
