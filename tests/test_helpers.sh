#!/usr/bin/env bash
# Test helpers to unify CI detection and safety checks across tests

is_ci() {
    [ -n "${CI:-}" ]
}

ensure_developer_safety() {
    # Never run on production systems
    if ! is_ci && [ "${TESTING:-}" != "1" ]; then
        local script_dir
        script_dir="${SCRIPT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
        if [ ! -f "$script_dir/README.md" ] || [ ! -d "$script_dir/tests" ]; then
            echo "ERROR: This test must be run from the project root directory"
            echo "Run with: TESTING=1 tests/<test-file>.sh"
            exit 1
        fi
    fi

    # Ensure we're not running as root (unless in CI or TESTING)
    if [ "$(id -u)" = "0" ] && ! is_ci && [ "${TESTING:-}" != "1" ]; then
        echo "ERROR: Refusing to run tests as root for safety"
        exit 1
    fi

    # Set testing environment for test scripts
    export TESTING=1
    export CI=1
}
