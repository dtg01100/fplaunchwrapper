#!/bin/bash
# Benchmark harness for test execution time optimization
# Measures the total test suite execution time

cd "$(dirname "$0")" || exit

export HYPOTHESIS_PROFILE=ci

echo "Running test suite..."

START=$(date +%s.%N)

python3 -m pytest tests/python/ -n auto --dist loadscope -q --tb=no --no-header 2>&1
RC=$?

END=$(date +%s.%N)

DURATION=$(echo "$END - $START" | bc)

echo ""
echo "METRIC test_execution_time=$DURATION"
echo "METRIC tests_passed=0"

exit $RC
