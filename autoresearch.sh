#!/bin/bash
# Benchmark harness for test execution time optimization
# Measures the total test suite execution time

set -e

cd "$(dirname "$0")"

# Run pytest with timing measurement
echo "Running test suite..."

START=$(date +%s.%N)

# Run tests and capture the summary line
OUTPUT=$(python3 -m pytest tests/python/ -q --tb=no --no-header 2>&1)
EXIT_CODE=$?

END=$(date +%s.%N)

# Calculate duration
DURATION=$(echo "$END - $START" | bc)

# Extract test count and status from output
PASSED=$(echo "$OUTPUT" | grep -oP '\d+(?= passed)' | head -1 || echo "0")
FAILED=$(echo "$OUTPUT" | grep -oP '\d+(?= failed)' | head -1 || echo "0")

echo "$OUTPUT" | tail -3
echo ""
echo "METRIC test_execution_time=$DURATION"
echo "METRIC tests_passed=$PASSED"
echo "METRIC tests_failed=$FAILED"

# Exit with pytest's exit code
exit $EXIT_CODE
