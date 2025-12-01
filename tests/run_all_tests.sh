#!/usr/bin/env bash
# Run all test suites

set -e

# Source shared test helpers for CI detection and safety
# shellcheck source=./test_helpers.sh disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/test_helpers.sh"

# Developer workstation safety check - never run as root
if [ "$(id -u)" = "0" ] && ! is_ci; then
    echo "ERROR: Refusing to run tests as root for safety"
    echo "This project should never be run with root privileges"
    exit 1
fi

# Set testing environment
export TESTING=1
# Do not force CI in top-level runner; tests will source helpers and set CI as needed
# export CI=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # Variables kept for potential future aggregation
TOTAL_PASSED=0
# shellcheck disable=SC2034
TOTAL_FAILED=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Running All Test Suites${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Run common library tests
echo -e "${YELLOW}Running common library tests...${NC}"
if bash "$SCRIPT_DIR/test_common_lib.sh"; then
    echo -e "${GREEN}✓ Common library tests passed${NC}"
else
    echo -e "${RED}✗ Common library tests failed${NC}"
fi
echo ""

# Run wrapper generation tests
echo -e "${YELLOW}Running wrapper generation tests...${NC}"
if bash "$SCRIPT_DIR/test_wrapper_generation.sh"; then
    echo -e "${GREEN}✓ Wrapper generation tests passed${NC}"
else
    echo -e "${RED}✗ Wrapper generation tests failed${NC}"
fi
echo ""

# Run management function tests
echo -e "${YELLOW}Running management function tests...${NC}"
if bash "$SCRIPT_DIR/test_management_functions.sh"; then
    echo -e "${GREEN}✓ Management function tests passed${NC}"
else
    echo -e "${RED}✗ Management function tests failed${NC}"
fi
echo ""

# Run integration tests
echo -e "${YELLOW}Running integration tests...${NC}"
if bash "$SCRIPT_DIR/test_integration.sh"; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed${NC}"
fi
echo ""

# Run install/cleanup tests
echo -e "${YELLOW}Running install/cleanup tests...${NC}"
if bash "$SCRIPT_DIR/test_install_cleanup.sh"; then
    echo -e "${GREEN}✓ Install/cleanup tests passed${NC}"
else
    echo -e "${RED}✗ Install/cleanup tests failed${NC}"
fi
echo ""

# Run edge case tests
echo -e "${YELLOW}Running edge case tests...${NC}"
if bash "$SCRIPT_DIR/test_edge_cases.sh"; then
    echo -e "${GREEN}✓ Edge case tests passed${NC}"
else
    echo -e "${RED}✗ Edge case tests failed${NC}"
fi
echo ""

# Run wrapper options tests
echo -e "${YELLOW}Running wrapper options tests...${NC}"
if bash "$SCRIPT_DIR/test_wrapper_options.sh"; then
    echo -e "${GREEN}✓ Wrapper options tests passed${NC}"
else
    echo -e "${RED}✗ Wrapper options tests failed${NC}"
fi
echo ""

# Run systemd lifecycle tests
echo -e "${YELLOW}Running systemd lifecycle tests...${NC}"
if bash "$SCRIPT_DIR/test_systemd_lifecycle.sh"; then
    echo -e "${GREEN}✓ Systemd lifecycle tests passed${NC}"
else
    echo -e "${RED}✗ Systemd lifecycle tests failed${NC}"
fi
echo ""

# Run package installation tests
echo -e "${YELLOW}Running package installation tests...${NC}"
if bash "$SCRIPT_DIR/test_package_installation.sh"; then
    echo -e "${GREEN}✓ Package installation tests passed${NC}"
else
    echo -e "${RED}✗ Package installation tests failed${NC}"
fi
echo ""

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}All test suites completed${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                    ⚠️  ADVERSARIAL TESTS  ⚠️                    ║${NC}"
echo -e "${PURPLE}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${PURPLE}║ The following tests are DANGEROUS and attack fplaunchwrapper:    ║${NC}"
echo -e "${PURPLE}║ • test_fplaunchwrapper_adversarial.sh - Security attacks     ║${NC}"
echo -e "${PURPLE}║ • test_robustness_adversarial.sh - Weird setups         ║${NC}"
echo -e "${PURPLE}║ • test_wrapper_options_adversarial.sh - Option attacks     ║${NC}"
echo -e "${PURPLE}║ • test_systemd_adversarial.sh - Systemd attacks        ║${NC}"
echo -e "${PURPLE}║ • test_package_adversarial.sh - Package attacks         ║${NC}"
echo -e "${PURPLE}║                                                                        ║${NC}"
echo -e "${PURPLE}║ ⚠️  ONLY run in isolated environments you control!              ║${NC}"
echo -e "${PURPLE}║ ⚠️  NEVER run on production systems!                           ║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}To run adversarial tests:${NC}"
echo -e "${CYAN}  TESTING=1 tests/adversarial/test_fplaunchwrapper_adversarial.sh${NC}"
echo -e "${CYAN}  TESTING=1 tests/adversarial/test_robustness_adversarial.sh${NC}"
echo -e "${CYAN}  TESTING=1 tests/adversarial/test_wrapper_options_adversarial.sh${NC}"
echo -e "${CYAN}  TESTING=1 tests/adversarial/test_systemd_adversarial.sh${NC}"
echo -e "${CYAN}  TESTING=1 tests/adversarial/test_package_adversarial.sh${NC}"
echo ""
