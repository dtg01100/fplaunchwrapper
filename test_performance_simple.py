#!/usr/bin/env python3
"""
Simple Performance Testing for fplaunchwrapper - Safe and Isolated
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch, Mock
import statistics

try:
    from fplaunch.generate import WrapperGenerator
    from fplaunch.manage import WrapperManager
    from fplaunch.cleanup import WrapperCleanup
    from fplaunch.launch import AppLauncher

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


def benchmark_operation(name, operation_func, iterations=5):
    """Benchmark a single operation"""
    print(f"Testing {name} ({iterations} iterations)...")

    times = []

    for i in range(iterations):
        start_time = time.perf_counter()
        result = operation_func(i)
        end_time = time.perf_counter()

        execution_time = (end_time - start_time) * 1000
        times.append(execution_time)

    avg_time = statistics.mean(times)
    std_time = statistics.stdev(times) if len(times) > 1 else 0

    print(f"  Avg time: {avg_time:.2f}ms")
    print(f"  Std dev: {std_time:.2f}ms")

    return {"avg_time": avg_time, "std_time": std_time}


def run_performance_tests():
    """Run safe performance tests"""
    print("FLAUNCHWRAPPER PERFORMANCE TESTS")
    print("=" * 40)

    if not MODULES_AVAILABLE:
        print("Required modules not available")
        return

    results = {}

    # Test wrapper generation
    def generation_test(i):
        with patch("subprocess.run") as mock_run, patch(
            "os.path.exists", return_value=True
        ):
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")
            generator = WrapperGenerator(
                bin_dir=f"/tmp/test_{i}", verbose=False, emit_mode=True
            )
            return generator.generate_wrapper(f"org.test.app{i}")

    results["generation"] = benchmark_operation("Wrapper Generation", generation_test)

    # Test manager operations
    def manager_test(i):
        with patch("subprocess.run") as mock_run, patch(
            "os.path.exists", return_value=True
        ), patch("pathlib.Path.home", return_value=Path("/tmp")), patch(
            "pathlib.Path.exists", return_value=True
        ), patch("pathlib.Path.read_text", return_value="/tmp/bin"), patch(
            "pathlib.Path.is_file", return_value=True
        ):
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")
            manager = WrapperManager(
                config_dir=f"/tmp/test_{i}", verbose=False, emit_mode=True
            )
            manager.set_preference(f"app_{i}", "flatpak")
            return manager.get_preference(f"app_{i}")

    results["management"] = benchmark_operation("Manager Operations", manager_test)

    print("\nPERFORMANCE SUMMARY")
    print("-" * 20)

    for test_name, metrics in results.items():
        avg_time = metrics["avg_time"]
        status = "FAST" if avg_time < 50 else "SLOW" if avg_time > 200 else "OK"
        print(f"{test_name}: {avg_time:.1f}ms ({status})")

    return results


if __name__ == "__main__":
    run_performance_tests()
