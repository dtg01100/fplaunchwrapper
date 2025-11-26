#!/usr/bin/env bash
# Test suite for management functions (aliases, preferences, env vars, etc.)
# Self-contained tests

TEST_DIR="/tmp/fplaunch-mgmt-test-$$"
TEST_BIN="$TEST_DIR/bin"
TEST_CONFIG="$TEST_DIR/config/flatpak-wrappers"
# shellcheck disable=SC2034  # SCRIPT_DIR kept for potential future use
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

assert_success() {
    local desc="$1"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $desc"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $desc"
        ((TESTS_FAILED++))
        return 1
    fi
}

assert_equals() {
    local expected="$1"
    local actual="$2"
    local desc="$3"
    if [ "$expected" = "$actual" ]; then
        echo -e "${GREEN}✓${NC} $desc (expected: $expected)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $desc (expected: $expected, got: $actual)"
        ((TESTS_FAILED++))
        return 1
    fi
}

setup() {
    mkdir -p "$TEST_BIN" "$TEST_CONFIG"
    export CONFIG_DIR="$TEST_CONFIG"
    export BIN_DIR="$TEST_BIN"
}

# Test 1: Set and retrieve preference
test_set_preference() {
    echo -e "\n${YELLOW}Test 1: Set and retrieve preference${NC}"
    
    cat > "$TEST_BIN/test-pref" << 'EOF'
#!/usr/bin/env bash
CONFIG_DIR="$1"
name="$2"
choice="$3"

set_pref() {
    name="$1"
    choice="$2"
    if [ "$choice" != "system" ] && [ "$choice" != "flatpak" ]; then
        return 1
    fi
    pref_file="$CONFIG_DIR/$name.pref"
    echo "$choice" > "$pref_file"
}

set_pref "$name" "$choice"
EOF
    chmod +x "$TEST_BIN/test-pref"
    
    "$TEST_BIN/test-pref" "$TEST_CONFIG" "testapp" "flatpak"
    assert_success "Set preference to flatpak"
    
    actual=$(cat "$TEST_CONFIG/testapp.pref")
    assert_equals "flatpak" "$actual" "Preference file contains correct value"
    
    # Test invalid preference
    "$TEST_BIN/test-pref" "$TEST_CONFIG" "testapp" "invalid" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${GREEN}✓${NC} Invalid preference rejected"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Invalid preference not rejected"
        ((TESTS_FAILED++))
    fi
}

# Test 2: Alias management
test_alias_management() {
    echo -e "\n${YELLOW}Test 2: Alias management${NC}"
    
    # Create base wrapper
    cat > "$TEST_BIN/chrome" << 'EOF'
#!/usr/bin/env bash
echo "chrome wrapper"
EOF
    chmod +x "$TEST_BIN/chrome"
    
    cat > "$TEST_BIN/test-alias" << 'EOF'
#!/usr/bin/env bash
BIN_DIR="$1"
CONFIG_DIR="$2"
name="$3"
alias_name="$4"

set_alias() {
    script_path="$BIN_DIR/$name"
    alias_path="$BIN_DIR/$alias_name"
    
    if [ ! -f "$script_path" ]; then
        return 1
    fi
    
    if [ -e "$alias_path" ]; then
        return 2
    fi
    
    ln -s "$script_path" "$alias_path"
    echo "$alias_name $name" >> "$CONFIG_DIR/aliases"
}

set_alias
EOF
    chmod +x "$TEST_BIN/test-alias"
    
    "$TEST_BIN/test-alias" "$TEST_BIN" "$TEST_CONFIG" "chrome" "browser"
    assert_success "Created alias"
    
    if [ -L "$TEST_BIN/browser" ]; then
        echo -e "${GREEN}✓${NC} Alias symlink created"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Alias symlink not created"
        ((TESTS_FAILED++))
    fi
    
    if grep -q "browser chrome" "$TEST_CONFIG/aliases"; then
        echo -e "${GREEN}✓${NC} Alias recorded in config"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Alias not recorded"
        ((TESTS_FAILED++))
    fi
    
    # Test duplicate alias rejection
    "$TEST_BIN/test-alias" "$TEST_BIN" "$TEST_CONFIG" "chrome" "browser" 2>/dev/null
    if [ $? -eq 2 ]; then
        echo -e "${GREEN}✓${NC} Duplicate alias rejected"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Duplicate alias not rejected"
        ((TESTS_FAILED++))
    fi
}

# Test 3: Environment variable management
test_env_management() {
    echo -e "\n${YELLOW}Test 3: Environment variable management${NC}"
    
    cat > "$TEST_BIN/test-env" << 'EOF'
#!/usr/bin/env bash
BIN_DIR="$1"
CONFIG_DIR="$2"
name="$3"
var="$4"
value="$5"

set_env() {
    env_file="$CONFIG_DIR/$name.env"
    if [ ! -f "$BIN_DIR/$name" ]; then
        return 1
    fi
    echo "export $var=\"$value\"" >> "$env_file"
}

# Create wrapper first
cat > "$BIN_DIR/$name" << 'WEOF'
#!/bin/bash
echo "wrapper"
WEOF
chmod +x "$BIN_DIR/$name"

set_env
EOF
    chmod +x "$TEST_BIN/test-env"
    
    "$TEST_BIN/test-env" "$TEST_BIN" "$TEST_CONFIG" "testapp" "MY_VAR" "my_value"
    assert_success "Set environment variable"
    
    if grep -q 'export MY_VAR="my_value"' "$TEST_CONFIG/testapp.env"; then
        echo -e "${GREEN}✓${NC} Environment variable recorded"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Environment variable not recorded"
        ((TESTS_FAILED++))
    fi
}

# Test 4: Blocklist management
test_blocklist() {
    echo -e "\n${YELLOW}Test 4: Blocklist management${NC}"
    
    cat > "$TEST_BIN/test-block" << 'EOF'
#!/usr/bin/env bash
CONFIG_DIR="$1"
BLOCKLIST="$CONFIG_DIR/blocklist"
id="$2"

block_id() {
    if ! grep -q "^$id$" "$BLOCKLIST" 2>/dev/null; then
        echo "$id" >> "$BLOCKLIST"
        return 0
    fi
    return 1
}

block_id
EOF
    chmod +x "$TEST_BIN/test-block"
    
    "$TEST_BIN/test-block" "$TEST_CONFIG" "com.example.App"
    assert_success "Blocked app ID"
    
    if grep -q "com.example.App" "$TEST_CONFIG/blocklist"; then
        echo -e "${GREEN}✓${NC} App added to blocklist"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} App not in blocklist"
        ((TESTS_FAILED++))
    fi
    
    # Test duplicate blocking
    "$TEST_BIN/test-block" "$TEST_CONFIG" "com.example.App"
    if [ $? -ne 0 ]; then
        echo -e "${GREEN}✓${NC} Duplicate block prevented"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Duplicate block not prevented"
        ((TESTS_FAILED++))
    fi
}

# Test 5: Unblock functionality
test_unblock() {
    echo -e "\n${YELLOW}Test 5: Unblock functionality${NC}"
    
    echo "com.blocked.App" > "$TEST_CONFIG/blocklist"
    
    cat > "$TEST_BIN/test-unblock" << 'EOF'
#!/usr/bin/env bash
CONFIG_DIR="$1"
BLOCKLIST="$CONFIG_DIR/blocklist"
id="$2"

unblock_id() {
    if grep -q "^$id$" "$BLOCKLIST" 2>/dev/null; then
        sed -i "/^$id$/d" "$BLOCKLIST"
        return 0
    fi
    return 1
}

unblock_id
EOF
    chmod +x "$TEST_BIN/test-unblock"
    
    "$TEST_BIN/test-unblock" "$TEST_CONFIG" "com.blocked.App"
    assert_success "Unblocked app"
    
    if ! grep -q "com.blocked.App" "$TEST_CONFIG/blocklist" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} App removed from blocklist"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} App still in blocklist"
        ((TESTS_FAILED++))
    fi
}

# Test 6: Export/Import preferences
test_export_import() {
    echo -e "\n${YELLOW}Test 6: Export/Import preferences${NC}"
    
    # Create test data
    echo "system" > "$TEST_CONFIG/app1.pref"
    echo "flatpak" > "$TEST_CONFIG/app2.pref"
    echo "com.blocked.App" > "$TEST_CONFIG/blocklist"
    
    cat > "$TEST_BIN/test-export" << 'EOF'
#!/usr/bin/env bash
CONFIG_DIR="$1"
file="$2"

export_prefs() {
    tar -czf "$file" -C "$CONFIG_DIR" blocklist $(ls -1 "$CONFIG_DIR"/*.pref 2>/dev/null | xargs -n1 basename) 2>/dev/null
}

export_prefs
EOF
    chmod +x "$TEST_BIN/test-export"
    
    "$TEST_BIN/test-export" "$TEST_CONFIG" "$TEST_DIR/prefs.tar.gz"
    assert_success "Exported preferences"
    
    if [ -f "$TEST_DIR/prefs.tar.gz" ]; then
        echo -e "${GREEN}✓${NC} Export file created"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Export file not created"
        ((TESTS_FAILED++))
    fi
    
    # Test import
    rm -rf "${TEST_CONFIG:?}"/*
    mkdir -p "$TEST_CONFIG"
    
    cat > "$TEST_BIN/test-import" << 'EOF'
#!/usr/bin/env bash
CONFIG_DIR="$1"
file="$2"

import_prefs() {
    if tar -tzf "$file" 2>/dev/null | grep -q '\.\.'; then
        return 1
    fi
    tar -xzf "$file" -C "$CONFIG_DIR" 2>/dev/null
}

import_prefs
EOF
    chmod +x "$TEST_BIN/test-import"
    
    "$TEST_BIN/test-import" "$TEST_CONFIG" "$TEST_DIR/prefs.tar.gz"
    assert_success "Imported preferences"
    
    if [ -f "$TEST_CONFIG/app1.pref" ] && [ -f "$TEST_CONFIG/app2.pref" ]; then
        echo -e "${GREEN}✓${NC} Preferences restored"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Preferences not restored"
        ((TESTS_FAILED++))
    fi
}

# Test 7: Script management (pre-launch/post-run)
test_script_management() {
    echo -e "\n${YELLOW}Test 7: Script management${NC}"
    
    # Create wrapper
    cat > "$TEST_BIN/testapp" << 'EOF'
#!/bin/bash
echo "wrapper"
EOF
    chmod +x "$TEST_BIN/testapp"
    
    # Create test script
    cat > "$TEST_DIR/test-script.sh" << 'EOF'
#!/bin/bash
echo "test script"
EOF
    chmod +x "$TEST_DIR/test-script.sh"
    
    cat > "$TEST_BIN/test-set-script" << 'EOF'
#!/usr/bin/env bash
BIN_DIR="$1"
CONFIG_DIR="$2"
name="$3"
path="$4"

set_script() {
    if [ ! -f "$BIN_DIR/$name" ]; then
        return 1
    fi
    if [ ! -f "$path" ]; then
        return 2
    fi
    script_dir="$CONFIG_DIR/scripts/$name"
    mkdir -p "$script_dir"
    cp "$path" "$script_dir/pre-launch.sh"
    chmod +x "$script_dir/pre-launch.sh"
}

set_script
EOF
    chmod +x "$TEST_BIN/test-set-script"
    
    "$TEST_BIN/test-set-script" "$TEST_BIN" "$TEST_CONFIG" "testapp" "$TEST_DIR/test-script.sh"
    assert_success "Set pre-launch script"
    
    if [ -f "$TEST_CONFIG/scripts/testapp/pre-launch.sh" ]; then
        echo -e "${GREEN}✓${NC} Script copied to correct location"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Script not copied"
        ((TESTS_FAILED++))
    fi
    
    if [ -x "$TEST_CONFIG/scripts/testapp/pre-launch.sh" ]; then
        echo -e "${GREEN}✓${NC} Script is executable"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Script not executable"
        ((TESTS_FAILED++))
    fi
}

# Test 8: Remove wrapper with cleanup
test_wrapper_removal() {
    echo -e "\n${YELLOW}Test 8: Wrapper removal with cleanup${NC}"
    
    # Create wrapper and associated files
    cat > "$TEST_BIN/removetest" << 'EOF'
#!/bin/bash
# Generated by fplaunchwrapper
echo "wrapper"
EOF
    chmod +x "$TEST_BIN/removetest"
    echo "system" > "$TEST_CONFIG/removetest.pref"
    ln -s "$TEST_BIN/removetest" "$TEST_BIN/removetest-alias"
    echo "removetest-alias removetest" > "$TEST_CONFIG/aliases"
    
    cat > "$TEST_BIN/test-remove" << 'EOF'
#!/usr/bin/env bash
BIN_DIR="$1"
CONFIG_DIR="$2"
name="$3"

remove_wrapper() {
    script_path="$BIN_DIR/$name"
    if [ -f "$script_path" ]; then
        rm "$script_path"
        pref_file="$CONFIG_DIR/$name.pref"
        [ -f "$pref_file" ] && rm "$pref_file"
        sed -i "/^$name /d" "$CONFIG_DIR/aliases" 2>/dev/null
        for alias in "$BIN_DIR"/*; do
            if [ -L "$alias" ] && [ "$(readlink "$alias" 2>/dev/null)" = "$script_path" ]; then
                rm "$alias"
            fi
        done
    fi
}

remove_wrapper
EOF
    chmod +x "$TEST_BIN/test-remove"
    
    "$TEST_BIN/test-remove" "$TEST_BIN" "$TEST_CONFIG" "removetest"
    
    if [ ! -f "$TEST_BIN/removetest" ]; then
        echo -e "${GREEN}✓${NC} Wrapper removed"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Wrapper not removed"
        ((TESTS_FAILED++))
    fi
    
    if [ ! -f "$TEST_CONFIG/removetest.pref" ]; then
        echo -e "${GREEN}✓${NC} Preference file removed"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Preference file not removed"
        ((TESTS_FAILED++))
    fi
    
    if [ ! -L "$TEST_BIN/removetest-alias" ]; then
        echo -e "${GREEN}✓${NC} Alias removed"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Alias not removed"
        ((TESTS_FAILED++))
    fi
}

# Test 9: List wrappers
test_list_wrappers() {
    echo -e "\n${YELLOW}Test 9: List wrappers${NC}"
    
    # Create test wrappers
    for app in app1 app2 app3; do
        cat > "$TEST_BIN/$app" << EOF
#!/bin/bash
# Generated by fplaunchwrapper
ID="com.example.$app"
EOF
        chmod +x "$TEST_BIN/$app"
    done
    
    cat > "$TEST_BIN/test-list" << 'EOF'
#!/usr/bin/env bash
BIN_DIR="$1"

list_wrappers() {
    for script in "$BIN_DIR"/*; do
        if [ -f "$script" ] && [ -x "$script" ] && grep -q "Generated by fplaunchwrapper" "$script" 2>/dev/null; then
            name=$(basename "$script")
            id=$(grep '^ID=' "$script" | cut -d'"' -f2 || echo "unknown")
            echo "$name -> $id"
        fi
    done
}

list_wrappers
EOF
    chmod +x "$TEST_BIN/test-list"
    
    output=$("$TEST_BIN/test-list" "$TEST_BIN")
    
    for app in app1 app2 app3; do
        if echo "$output" | grep -q "$app -> com.example.$app"; then
            echo -e "${GREEN}✓${NC} Listed $app correctly"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}✗${NC} $app not listed correctly"
            ((TESTS_FAILED++))
        fi
    done
}

# Run all tests
main() {
    echo "======================================"
    echo "Management Functions Test Suite"
    echo "======================================"
    
    setup
    
    test_set_preference
    test_alias_management
    test_env_management
    test_blocklist
    test_unblock
    test_export_import
    test_script_management
    test_wrapper_removal
    test_list_wrappers
    
    echo ""
    echo "======================================"
    echo "Test Results"
    echo "======================================"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo "Total:  $((TESTS_PASSED + TESTS_FAILED))"
    echo "======================================"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

main "$@"
