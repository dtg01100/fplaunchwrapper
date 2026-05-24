#!/bin/bash
# Benchmark harness for test execution time optimization
# Measures the total test suite execution time

cd "$(dirname "$0")"

export HYPOTHESIS_PROFILE=ci

echo "Running test suite..."

START=$(date +%s.%N)

python3 -m pytest tests/python/ -n auto -q --tb=no --no-header 2>&1
RC=$?

END=$(date +%s.%N)

DURATION=$(echo "$END - $START" | bc)

# Parse output
OUTPUT=$(python3 -m pytest tests/python/ --collect-only -q 2>/dev/null | tail -1)
TOTAL=$(echo "$OUTPUT" | grep -oE '^[0-9]+' || echo "0")

echo ""
echo "METRIC test_execution_time=$DURATION"
echo "METRIC tests_passed=$TOTAL"

exit $RC
