"""Lock-in tests: validate the suite is hermetic.

A hermetic test suite:
  * Tests pass in any order.
  * Tests pass on re-runs.
  * Tests don't mutate global state that bleeds into other tests.

These tests run the FULL suite in random order multiple times and
assert that 100% of tests pass. Any hermeticity regression is caught
immediately.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _run_full_suite(seed: int) -> tuple[int, str, str]:
    """Run the full test suite with random ordering at the given seed.

    Returns (exit_code, stdout, stderr).
    """
    env = os.environ.copy()
    env["FPWRAPPER_TEST_ENV"] = "true"  # must be the string "true", not "1"
    # (this test invokes pytest which would otherwise re-run itself).
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header",
         "-p", "randomly", "--randomly-seed", str(seed),
         "--ignore=tests/test_meta_verification/test_hermeticity.py"],
        capture_output=True, text=True, timeout=600,
        env=env, cwd=str(PROJECT_ROOT),
    )
    return result.returncode, result.stdout, result.stderr


def test_suite_passes_in_random_order_seed_1():
    """The full suite must pass in random order with seed=1."""
    rc, out, err = _run_full_suite(1)
    assert rc == 0, (
        f"Suite failed in random order (seed=1) with exit={rc}.\n"
        f"--- last 50 lines of stdout ---\n"
        f"{chr(10).join(out.splitlines()[-50:])}\n"
        f"--- last 50 lines of stderr ---\n"
        f"{chr(10).join(err.splitlines()[-50:])}"
    )


def test_suite_passes_in_random_order_seed_42():
    """The full suite must pass in random order with seed=42."""
    rc, out, err = _run_full_suite(42)
    assert rc == 0, (
        f"Suite failed in random order (seed=42) with exit={rc}.\n"
        f"--- last 50 lines of stdout ---\n"
        f"{chr(10).join(out.splitlines()[-50:])}\n"
        f"--- last 50 lines of stderr ---\n"
        f"{chr(10).join(err.splitlines()[-50:])}"
    )


def test_suite_passes_in_random_order_seed_100():
    """The full suite must pass in random order with seed=100."""
    rc, out, err = _run_full_suite(100)
    assert rc == 0, (
        f"Suite failed in random order (seed=100) with exit={rc}.\n"
        f"--- last 50 lines of stdout ---\n"
        f"{chr(10).join(out.splitlines()[-50:])}\n"
        f"--- last 50 lines of stderr ---\n"
        f"{chr(10).join(err.splitlines()[-50:])}"
    )
