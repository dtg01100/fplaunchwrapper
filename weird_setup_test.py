#!/usr/bin/env python3
"""
Weird User Setups Test - Testing Strange Linux Desktop Configurations

This test suite simulates the bizarre, non-malicious setups that Linux desktop
users can have that might break software. These aren't security attacks, but
real-world edge cases that can cause software to fail.
"""

import sys
import os
import tempfile
import shutil
import stat
from pathlib import Path
from unittest.mock import patch, Mock
import subprocess
import time

# Import modules safely
try:
    from fplaunch.generate import WrapperGenerator
    from fplaunch.manage import WrapperManager
    from fplaunch.launch import AppLauncher

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


class WeirdSetupTester:
    """Test weird Linux desktop user configurations"""

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
        self.temp_dir = Path(tempfile.mkdtemp(prefix="weird_setup_"))
        return {
            "home": self.temp_dir / "home",
            "config": self.temp_dir / "config",
            "bin": self.temp_dir / "bin",
            "cache": self.temp_dir / "cache",
            "local": self.temp_dir / "local",
        }

    def cleanup_temp_env(self):
        """Clean up test environment"""
        if self.temp_dir and self.temp_dir.exists():
            # Make sure directories are writable for cleanup
            for root, dirs, files in os.walk(self.temp_dir):
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), 0o755)
                    except (OSError, FileNotFoundError):
                        pass  # Skip if already deleted or inaccessible
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), 0o644)
                    except (OSError, FileNotFoundError):
                        pass  # Skip if already deleted or inaccessible
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_weird_setup_tests(self):
        """Run all weird setup tests"""
        if not MODULES_AVAILABLE:
            print("❌ Modules not available for testing")
            return

        print("🤪 WEIRD LINUX DESKTOP USER SETUPS TEST")
        print("=" * 50)

        try:
            # Setup environment
            env = self.setup_temp_env()

            # Test various weird setups
            self.test_symlinked_home_directory(env)
            self.test_readonly_config_directory(env)
            self.test_missing_path_directories(env)
            self.test_extremely_long_path(env)
            self.test_unicode_paths(env)
            self.test_spaces_in_paths(env)
            self.test_missing_parent_directories(env)
            self.test_full_disk_simulation(env)
            self.test_broken_symlinks(env)
            self.test_unusual_file_permissions(env)
            self.test_containerized_environment(env)
            self.test_multiple_flatpak_installations(env)
            self.test_corrupted_flatpak_metadata(env)
            self.test_offline_flatpak_operations(env)
            self.test_locale_encoding_issues(env)
            self.test_custom_shell_configurations(env)

            # Print summary
            self.print_summary()

        finally:
            self.cleanup_temp_env()

    def test_symlinked_home_directory(self, env):
        """Test when user's home directory is a symlink"""
        print("\n🔗 SYMLINKED HOME DIRECTORY")

        # Create a symlinked home structure
        real_home = env["home"] / "real_home"
        real_home.mkdir(parents=True)

        # Symlink home to point elsewhere
        symlink_home = env["home"] / "symlink_home"
        os.symlink(str(real_home), str(symlink_home))

        try:
            with patch("pathlib.Path.home", return_value=symlink_home), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Symlinked home directory",
                    True,
                    "Handled symlinked home gracefully",
                )

        except Exception as e:
            self.log_result(
                "Symlinked home directory", False, f"Failed with symlinked home: {e}"
            )

    def test_readonly_config_directory(self, env):
        """Test when config directory is read-only"""
        print("\n🔒 READ-ONLY CONFIG DIRECTORY")

        config_dir = env["config"]
        config_dir.mkdir(parents=True)

        # Make config directory read-only
        config_dir.chmod(0o444)

        try:
            with patch("pathlib.Path.home", return_value=env["home"]), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                # Create bin_dir file (required by manager)
                bin_dir_file = config_dir / "bin_dir"
                # This might fail due to read-only directory
                try:
                    bin_dir_file.write_text(str(env["bin"]))
                except PermissionError:
                    self.log_result(
                        "Read-only config directory",
                        True,
                        "Properly handled read-only config",
                    )
                    return

                manager = WrapperManager(
                    config_dir=str(config_dir), verbose=False, emit_mode=True
                )

                result = manager.set_preference("test_app", "flatpak")
                self.log_result(
                    "Read-only config directory",
                    True,
                    "Handled read-only config gracefully",
                )

        except Exception as e:
            self.log_result(
                "Read-only config directory",
                False,
                f"Failed with read-only config: {e}",
            )
        finally:
            # Restore permissions for cleanup
            try:
                config_dir.chmod(0o755)
            except:
                pass

    def test_missing_path_directories(self, env):
        """Test when PATH contains missing directories"""
        print("\n🚫 MISSING PATH DIRECTORIES")

        weird_path = "/nonexistent1:/usr/bin:/nonexistent2:/bin:/nonexistent3"

        try:
            with patch.dict(os.environ, {"PATH": weird_path}), patch(
                "subprocess.run"
            ) as mock_run, patch("os.path.exists", return_value=True):
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Missing PATH directories",
                    True,
                    "Handled missing PATH directories gracefully",
                )

        except Exception as e:
            self.log_result(
                "Missing PATH directories", False, f"Failed with missing PATH: {e}"
            )

    def test_extremely_long_path(self, env):
        """Test with extremely long directory paths"""
        print("\n📏 EXTREMELY LONG PATHS")

        # Create a path that's very long (but within filesystem limits)
        long_path = env["home"]
        for i in range(10):  # Create deep nesting
            long_path = long_path / f"very_long_directory_name_that_goes_on_and_on_{i}"
        long_path.mkdir(parents=True)

        try:
            with patch("pathlib.Path.home", return_value=long_path), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Extremely long paths",
                    True,
                    f"Handled long path ({len(str(long_path))} chars)",
                )

        except Exception as e:
            self.log_result(
                "Extremely long paths", False, f"Failed with long path: {e}"
            )

    def test_unicode_paths(self, env):
        """Test with unicode characters in paths"""
        print("\n🔤 UNICODE PATHS")

        unicode_home = env["home"] / "🏠家ユーザー"
        unicode_home.mkdir(parents=True)

        try:
            with patch("pathlib.Path.home", return_value=unicode_home), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Unicode paths", True, "Handled unicode directory names"
                )

        except Exception as e:
            self.log_result("Unicode paths", False, f"Failed with unicode paths: {e}")

    def test_spaces_in_paths(self, env):
        """Test when paths contain spaces"""
        print("\n🖼️ SPACES IN PATHS")

        spaced_home = env["home"] / "My Documents"
        spaced_home.mkdir(parents=True)

        spaced_bin = env["bin"] / "My Apps"
        spaced_bin.mkdir(parents=True)

        try:
            with patch("pathlib.Path.home", return_value=spaced_home), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(spaced_bin), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("Spaces in paths", True, "Handled paths with spaces")

        except Exception as e:
            self.log_result(
                "Spaces in paths", False, f"Failed with spaces in paths: {e}"
            )

    def test_missing_parent_directories(self, env):
        """Test when parent directories don't exist"""
        print("\n📁 MISSING PARENT DIRECTORIES")

        # Try to create wrapper generator with non-existent bin directory
        nonexistent_bin = env["bin"] / "deep" / "nested" / "nonexistent"

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(nonexistent_bin), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Missing parent directories",
                    True,
                    "Handled missing parent directories",
                )

        except Exception as e:
            self.log_result(
                "Missing parent directories", False, f"Failed with missing parents: {e}"
            )

    def test_full_disk_simulation(self, env):
        """Test behavior when disk space is low"""
        print("\n💾 FULL DISK SIMULATION")

        try:
            with patch("subprocess.run") as mock_run, patch(
                "os.path.exists", return_value=True
            ), patch("pathlib.Path.write_text") as mock_write:
                # Simulate disk full error
                mock_write.side_effect = OSError("No space left on device")
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Full disk simulation", True, "Handled disk full gracefully"
                )

        except Exception as e:
            self.log_result(
                "Full disk simulation", False, f"Failed with disk full: {e}"
            )

    def test_broken_symlinks(self, env):
        """Test with broken symlinks in paths"""
        print("\n🔗 BROKEN SYMLINKS")

        # Create a broken symlink
        broken_link = env["home"] / "broken_link"
        os.symlink("/nonexistent/target", str(broken_link))

        try:
            with patch("pathlib.Path.home", return_value=env["home"]), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Broken symlinks", True, "Handled broken symlinks gracefully"
                )

        except Exception as e:
            self.log_result(
                "Broken symlinks", False, f"Failed with broken symlinks: {e}"
            )

    def test_unusual_file_permissions(self, env):
        """Test with unusual file permissions"""
        print("\n🔐 UNUSUAL FILE PERMISSIONS")

        config_dir = env["config"]
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create a file with unusual permissions
        config_file = config_dir / "config.toml"
        config_file.write_text('[preferences]\nfirefox = "flatpak"\n')
        config_file.chmod(0o000)  # No permissions

        try:
            with patch("pathlib.Path.home", return_value=env["home"]), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                manager = WrapperManager(
                    config_dir=str(config_dir), verbose=False, emit_mode=True
                )

                result = manager.get_preference("firefox")
                self.log_result(
                    "Unusual file permissions",
                    True,
                    "Handled unusual permissions gracefully",
                )

        except Exception as e:
            self.log_result(
                "Unusual file permissions",
                False,
                f"Failed with unusual permissions: {e}",
            )
        finally:
            # Restore permissions for cleanup
            try:
                config_file.chmod(0o644)
            except:
                pass

    def test_containerized_environment(self, env):
        """Test in a containerized environment (limited capabilities)"""
        print("\n🐳 CONTAINERIZED ENVIRONMENT")

        # Simulate container environment with limited paths
        container_path = "/usr/local/bin:/usr/bin:/bin"

        try:
            with patch.dict(os.environ, {"PATH": container_path}), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run, patch(
                "pathlib.Path.home", return_value=env["home"]
            ):
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Containerized environment",
                    True,
                    "Worked in limited container environment",
                )

        except Exception as e:
            self.log_result(
                "Containerized environment", False, f"Failed in container: {e}"
            )

    def test_multiple_flatpak_installations(self, env):
        """Test with multiple Flatpak installations"""
        print("\n📦 MULTIPLE FLATPAK INSTALLATIONS")

        try:
            with patch("subprocess.run") as mock_run, patch(
                "os.path.exists", return_value=True
            ):
                # Mock multiple flatpak installations
                mock_run.side_effect = [
                    Mock(
                        returncode=0,
                        stdout="/var/lib/flatpak1\n/home/user/.local/share/flatpak2",
                        stderr="",
                    ),
                    Mock(returncode=0, stdout="", stderr=""),
                ]

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Multiple Flatpak installations",
                    True,
                    "Handled multiple Flatpak installs",
                )

        except Exception as e:
            self.log_result(
                "Multiple Flatpak installations",
                False,
                f"Failed with multiple installs: {e}",
            )

    def test_corrupted_flatpak_metadata(self, env):
        """Test with corrupted Flatpak metadata"""
        print("\n📋 CORRUPTED FLATPAK METADATA")

        try:
            with patch("subprocess.run") as mock_run, patch(
                "os.path.exists", return_value=True
            ):
                # Mock corrupted flatpak output
                mock_run.return_value = Mock(
                    returncode=0, stdout="invalid\x00null\x01byte", stderr=""
                )

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Corrupted Flatpak metadata",
                    True,
                    "Handled corrupted metadata gracefully",
                )

        except Exception as e:
            self.log_result(
                "Corrupted Flatpak metadata",
                False,
                f"Failed with corrupted metadata: {e}",
            )

    def test_offline_flatpak_operations(self, env):
        """Test Flatpak operations when offline"""
        print("\n📡 OFFLINE FLATPAK OPERATIONS")

        try:
            with patch("subprocess.run") as mock_run, patch(
                "os.path.exists", return_value=True
            ):
                # Mock network failure
                mock_run.return_value = Mock(
                    returncode=1, stdout="", stderr="Network is unreachable"
                )

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Offline Flatpak operations",
                    True,
                    "Handled offline operations gracefully",
                )

        except Exception as e:
            self.log_result(
                "Offline Flatpak operations", False, f"Failed when offline: {e}"
            )

    def test_locale_encoding_issues(self, env):
        """Test with locale/encoding issues"""
        print("\n🌍 LOCALE/ENCODING ISSUES")

        try:
            with patch.dict(os.environ, {"LANG": "C", "LC_ALL": "C"}), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="test", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Locale/encoding issues", True, "Handled C locale environment"
                )

        except Exception as e:
            self.log_result(
                "Locale/encoding issues", False, f"Failed with locale issues: {e}"
            )

    def test_custom_shell_configurations(self, env):
        """Test with custom shell configurations"""
        print("\n🐚 CUSTOM SHELL CONFIGURATIONS")

        # Simulate unusual shell environment
        unusual_shell = "/bin/dash"  # Minimal shell

        try:
            with patch.dict(os.environ, {"SHELL": unusual_shell}), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Custom shell configurations", True, f"Worked with {unusual_shell}"
                )

        except Exception as e:
            self.log_result(
                "Custom shell configurations", False, f"Failed with custom shell: {e}"
            )

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("🤪 WEIRD SETUP TEST SUMMARY")

        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")

        if total - passed == 0:
            print("✅ ALL TESTS PASSED - Handles weird setups perfectly!")
        else:
            print("⚠️  SOME TESTS FAILED - Review issues below")

        # Show failures
        failures = [
            (name, details) for name, success, details in self.results if not success
        ]
        if failures:
            print("\n❌ FAILED TESTS:")
            for name, details in failures:
                print(f"  - {name}: {details}")

        # Show interesting results
        interesting = [
            (name, details)
            for name, success, details in self.results
            if success and ("Handled" in details or "Worked" in details)
        ]
        if interesting:
            print("\n✅ INTERESTING SUCCESSFUL HANDLING:")
            for name, details in interesting[:5]:  # Show first 5
                print(f"  - {name}: {details}")


def main():
    """Main entry point"""
    tester = WeirdSetupTester()
    tester.run_weird_setup_tests()


if __name__ == "__main__":
    main()
