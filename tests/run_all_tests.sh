#!/usr/bin/env bash
# Run all test suites

set -e

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

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}All test suites completed${NC}"
echo -e "${BLUE}======================================${NC}"
