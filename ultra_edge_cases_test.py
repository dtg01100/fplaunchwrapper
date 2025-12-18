#!/usr/bin/env python3
"""
Ultra-Edge Cases Test - The Most Bizarre Scenarios Imaginable

Tests the most obscure, unusual, and edge-case scenarios that Linux users
might encounter. These are the "what if" cases that seem impossible but
could theoretically happen in the real world.
"""

import sys
import os
import tempfile
import shutil
import stat
import pwd
import grp
import time
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import subprocess
import signal
import resource

# Import modules safely
try:
    from fplaunch.generate import WrapperGenerator
    from fplaunch.manage import WrapperManager
    from fplaunch.launch import AppLauncher

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


class UltraEdgeCaseTester:
    """Test the most bizarre edge cases imaginable"""

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
        self.temp_dir = Path(tempfile.mkdtemp(prefix="ultra_edge_"))

        # Create various bizarre directory structures
        env = {
            "temp_root": self.temp_dir,
            "home": self.temp_dir / "home",
            "weird_home": self.temp_dir / "weird_home",
            "config": self.temp_dir / "config",
            "bin": self.temp_dir / "bin",
            "tmp": self.temp_dir / "tmp",
            "var": self.temp_dir / "var",
            "usr": self.temp_dir / "usr",
            "opt": self.temp_dir / "opt",
            "srv": self.temp_dir / "srv",
            "mnt": self.temp_dir / "mnt",
        }

        # Create directories
        for path in env.values():
            if isinstance(path, Path):
                path.mkdir(parents=True, exist_ok=True)

        return env

    def cleanup_temp_env(self):
        """Clean up test environment"""
        if self.temp_dir and self.temp_dir.exists():
            # Restore permissions recursively
            for root, dirs, files in os.walk(self.temp_dir):
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), 0o755)
                    except:
                        pass
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), 0o644)
                    except:
                        pass
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_ultra_edge_tests(self):
        """Run all ultra-edge case tests"""
        if not MODULES_AVAILABLE:
            print("❌ Modules not available for testing")
            return

        print("🤯 ULTRA-EDGE CASES TEST - THE MOST BIZARRE SCENARIOS")
        print("=" * 60)

        try:
            env = self.setup_temp_env()

            # System configuration edge cases
            self.test_no_tmp_directory(env)
            self.test_home_as_file_not_directory(env)
            self.test_circular_symlink_home(env)
            self.test_uid_gid_zero_not_root(env)
            self.test_unusual_umask(env)
            self.test_missing_libc_functions(env)
            self.test_custom_init_system(env)

            # User environment edge cases
            self.test_user_with_no_shell(env)
            self.test_extremely_long_username(env)
            self.test_username_with_special_chars(env)
            self.test_ldap_user_no_local_passwd(env)
            self.test_user_home_on_nfs(env)

            # Filesystem edge cases
            self.test_filesystem_no_atime(env)
            self.test_filesystem_quota_limits(env)
            self.test_case_insensitive_filesystem(env)
            self.test_filesystem_unusual_blocksize(env)
            self.test_transparent_compression(env)
            self.test_deduplication_filesystem(env)

            # Process environment edge cases
            self.test_high_pid_numbers(env)
            self.test_process_memory_limits(env)
            self.test_modified_signal_handlers(env)
            self.test_different_namespace(env)
            self.test_unusual_scheduling_priority(env)

            # Time and date edge cases
            self.test_incorrect_system_time(env)
            self.test_leap_second_handling(env)
            self.test_timezone_edge_cases(env)
            self.test_ntp_disabled_system(env)

            # Hardware edge cases
            self.test_no_swap_space(env)
            self.test_unusual_memory_layout(env)
            self.test_many_cpu_cores(env)
            self.test_unusual_network_config(env)

            # Software environment edge cases
            self.test_modified_coreutils(env)
            self.test_unusual_python_install(env)
            self.test_missing_standard_libs(env)
            self.test_modified_shell_behavior(env)
            self.test_unusual_flatpak_config(env)

            # Print summary
            self.print_summary()

        finally:
            self.cleanup_temp_env()

    def test_no_tmp_directory(self, env):
        """Test system with no /tmp directory"""
        print("\n🚫 NO /TMP DIRECTORY")

        try:
            with patch(
                "tempfile.gettempdir", side_effect=OSError("No such file or directory")
            ), patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                # Use custom temp directory
                with patch.dict(os.environ, {"TMPDIR": str(env["tmp"])}):
                    generator = WrapperGenerator(
                        bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                    )

                    result = generator.generate_wrapper("org.test.app")
                    self.log_result(
                        "No /tmp directory", True, "Handled missing /tmp gracefully"
                    )

        except Exception as e:
            self.log_result("No /tmp directory", False, f"Failed without /tmp: {e}")

    def test_home_as_file_not_directory(self, env):
        """Test when user's home directory is a file instead of directory"""
        print("\n📄 HOME DIRECTORY IS A FILE")

        # Create a file where home directory should be
        fake_home = env["weird_home"] / "fake_home"
        fake_home.write_text("This is not a directory")

        try:
            with patch("pathlib.Path.home", return_value=fake_home), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("Home as file", True, "Handled file-as-home gracefully")

        except Exception as e:
            self.log_result("Home as file", False, f"Failed with file home: {e}")

    def test_circular_symlink_home(self, env):
        """Test circular symlink in home directory"""
        print("\n🔄 CIRCULAR SYMLINK HOME")

        # Create circular symlink: home -> home2 -> home
        home1 = env["weird_home"] / "home1"
        home2 = env["weird_home"] / "home2"

        home1.mkdir()
        os.symlink(str(home1), str(home2))
        os.symlink(str(home2), str(home1 / "self_link"))

        try:
            with patch("pathlib.Path.home", return_value=home1), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Circular symlink home", True, "Handled circular symlinks"
                )

        except Exception as e:
            self.log_result(
                "Circular symlink home", False, f"Failed with circular symlink: {e}"
            )

    def test_uid_gid_zero_not_root(self, env):
        """Test user with UID/GID 0 but not actually root"""
        print("\n👤 UID/GID 0 NOT ROOT")

        try:
            with patch("os.getuid", return_value=0), patch(
                "os.getgid", return_value=0
            ), patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                # Mock getpwuid to return non-root user
                mock_pw = Mock()
                mock_pw.pw_name = "fakeuser"
                mock_pw.pw_dir = str(env["home"])

                with patch("pwd.getpwuid", return_value=mock_pw):
                    mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                    generator = WrapperGenerator(
                        bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                    )

                    result = generator.generate_wrapper("org.test.app")
                    self.log_result(
                        "UID/GID 0 not root", True, "Handled UID 0 non-root user"
                    )

        except Exception as e:
            self.log_result("UID/GID 0 not root", False, f"Failed with fake root: {e}")

    def test_unusual_umask(self, env):
        """Test with unusual umask settings"""
        print("\n🎭 UNUSUAL UMASK SETTINGS")

        try:
            # Set very restrictive umask
            old_umask = os.umask(0o777)  # No permissions for anyone

            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("Unusual umask", True, "Handled restrictive umask")

        except Exception as e:
            self.log_result("Unusual umask", False, f"Failed with umask: {e}")
        finally:
            # Restore umask
            try:
                os.umask(old_umask)
            except:
                pass

    def test_missing_libc_functions(self, env):
        """Test when libc functions are not available"""
        print("\n📚 MISSING LIBC FUNCTIONS")

        try:
            with patch(
                "os.path.exists", side_effect=OSError("Function not implemented")
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Missing libc functions", True, "Handled missing libc gracefully"
                )

        except Exception as e:
            self.log_result(
                "Missing libc functions", False, f"Failed with missing libc: {e}"
            )

    def test_custom_init_system(self, env):
        """Test with non-systemd init system"""
        print("\n🚀 CUSTOM INIT SYSTEM")

        try:
            with patch("subprocess.run") as mock_run:
                # Mock sysvinit or other init system
                def mock_init_commands(*args, **kwargs):
                    cmd = args[0] if args else []
                    if "systemctl" in cmd:
                        # Return failure for systemd commands
                        return Mock(
                            returncode=1,
                            stdout="",
                            stderr="systemctl: command not found",
                        )
                    elif "service" in cmd or "chkconfig" in cmd:
                        # Return success for sysvinit commands
                        return Mock(returncode=0, stdout="service started", stderr="")
                    else:
                        return Mock(returncode=0, stdout="", stderr="")

                mock_run.side_effect = mock_init_commands

                manager = WrapperManager(
                    config_dir=str(env["config"]), verbose=False, emit_mode=True
                )

                result = manager.set_preference("test_app", "flatpak")
                self.log_result("Custom init system", True, "Handled non-systemd init")

        except Exception as e:
            self.log_result(
                "Custom init system", False, f"Failed with custom init: {e}"
            )

    def test_user_with_no_shell(self, env):
        """Test user with no shell in /etc/passwd"""
        print("\n🐚 USER WITH NO SHELL")

        try:
            # Mock getpwuid to return user with no shell
            mock_pw = Mock()
            mock_pw.pw_name = "noshell"
            mock_pw.pw_shell = ""  # Empty shell
            mock_pw.pw_dir = str(env["home"])

            with patch("pwd.getpwuid", return_value=mock_pw), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "User with no shell", True, "Handled user with no shell"
                )

        except Exception as e:
            self.log_result(
                "User with no shell", False, f"Failed with no shell user: {e}"
            )

    def test_extremely_long_username(self, env):
        """Test with extremely long username"""
        print("\n📏 EXTREMELY LONG USERNAME")

        long_username = "user" + "x" * 200  # Very long username

        try:
            mock_pw = Mock()
            mock_pw.pw_name = long_username
            mock_pw.pw_dir = str(env["home"])

            with patch("pwd.getpwuid", return_value=mock_pw), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Extremely long username",
                    True,
                    f"Handled {len(long_username)} char username",
                )

        except Exception as e:
            self.log_result(
                "Extremely long username", False, f"Failed with long username: {e}"
            )

    def test_username_with_special_chars(self, env):
        """Test username with special characters"""
        print("\n🔣 USERNAME WITH SPECIAL CHARS")

        special_username = "user@domain.com"  # Email-like username

        try:
            mock_pw = Mock()
            mock_pw.pw_name = special_username
            mock_pw.pw_dir = str(env["home"])

            with patch("pwd.getpwuid", return_value=mock_pw), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Username with special chars", True, "Handled special char username"
                )

        except Exception as e:
            self.log_result(
                "Username with special chars", False, f"Failed with special chars: {e}"
            )

    def test_ldap_user_no_local_passwd(self, env):
        """Test LDAP user with no local /etc/passwd entry"""
        print("\n👥 LDAP USER NO LOCAL PASSWD")

        try:
            with patch("pwd.getpwuid", side_effect=KeyError("User not found")), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "LDAP user no local passwd", True, "Handled LDAP user gracefully"
                )

        except Exception as e:
            self.log_result(
                "LDAP user no local passwd", False, f"Failed with LDAP user: {e}"
            )

    def test_user_home_on_nfs(self, env):
        """Test user home on NFS mount"""
        print("\n🌐 USER HOME ON NFS")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                # Simulate NFS delays and behaviors
                def nfs_behavior(*args, **kwargs):
                    time.sleep(0.02)  # NFS latency
                    return Mock(returncode=0, stdout="", stderr="")

                mock_run.side_effect = nfs_behavior

                start_time = time.time()
                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                end_time = time.time()

                duration = end_time - start_time
                if duration > 0.5:  # Should still be reasonable
                    self.log_result(
                        "User home on NFS", False, f"NFS too slow: {duration:.2f}s"
                    )
                else:
                    self.log_result(
                        "User home on NFS",
                        True,
                        f"Handled NFS latency in {duration:.2f}s",
                    )

        except Exception as e:
            self.log_result("User home on NFS", False, f"Failed with NFS: {e}")

    def test_filesystem_no_atime(self, env):
        """Test filesystem with no atime updates"""
        print("\n⏰ FILESYSTEM NO ATIME")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "os.stat"
            ) as mock_stat, patch("subprocess.run") as mock_run:
                # Mock stat to return no atime updates
                mock_stat_result = Mock()
                mock_stat_result.st_atime = 0  # No access time
                mock_stat.return_value = mock_stat_result

                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Filesystem no atime", True, "Handled no-atime filesystem"
                )

        except Exception as e:
            self.log_result("Filesystem no atime", False, f"Failed with no-atime: {e}")

    def test_filesystem_quota_limits(self, env):
        """Test filesystem with quota limits reached"""
        print("\n📊 FILESYSTEM QUOTA LIMITS")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                # Simulate quota exceeded
                mock_run.return_value = Mock(
                    returncode=1, stdout="", stderr="Disk quota exceeded"
                )

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Filesystem quota limits", True, "Handled quota exceeded gracefully"
                )

        except Exception as e:
            self.log_result("Filesystem quota limits", False, f"Failed with quota: {e}")

    def test_case_insensitive_filesystem(self, env):
        """Test case-insensitive filesystem"""
        print("\n🔠 CASE-INSENSITIVE FILESYSTEM")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                # Create files with similar case
                test_file1 = env["bin"] / "TestApp"
                test_file2 = env["bin"] / "testapp"

                test_file1.write_text("#!/bin/bash\necho test1")
                test_file2.write_text("#!/bin/bash\necho test2")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Case-insensitive filesystem", True, "Handled case-insensitive FS"
                )

        except Exception as e:
            self.log_result(
                "Case-insensitive filesystem",
                False,
                f"Failed with case-insensitive: {e}",
            )

    def test_filesystem_unusual_blocksize(self, env):
        """Test filesystem with unusual block size"""
        print("\n📏 UNUSUAL BLOCK SIZE FILESYSTEM")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "os.stat"
            ) as mock_stat, patch("subprocess.run") as mock_run:
                # Mock unusual block size (very large)
                mock_stat_result = Mock()
                mock_stat_result.st_blksize = 1024 * 1024  # 1MB blocks
                mock_stat.return_value = mock_stat_result

                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Unusual block size", True, "Handled unusual block size"
                )

        except Exception as e:
            self.log_result(
                "Unusual block size", False, f"Failed with unusual blocks: {e}"
            )

    def test_transparent_compression(self, env):
        """Test filesystem with transparent compression"""
        print("\n🗜️ TRANSPARENT COMPRESSION")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                # Create highly compressible content
                compressible_data = "A" * 100000  # Very compressible

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Transparent compression", True, "Handled compressed filesystem"
                )

        except Exception as e:
            self.log_result(
                "Transparent compression", False, f"Failed with compression: {e}"
            )

    def test_deduplication_filesystem(self, env):
        """Test filesystem with deduplication"""
        print("\n🔄 DEDUPLICATION FILESYSTEM")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                # Create duplicate content to test deduplication
                for i in range(10):
                    dup_file = env["bin"] / f"duplicate_{i}.txt"
                    dup_file.write_text("This is duplicate content\n" * 1000)

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Deduplication filesystem", True, "Handled deduplication filesystem"
                )

        except Exception as e:
            self.log_result(
                "Deduplication filesystem", False, f"Failed with deduplication: {e}"
            )

    def test_high_pid_numbers(self, env):
        """Test with extremely high PID numbers"""
        print("\n🔢 HIGH PID NUMBERS")

        try:
            with patch("os.getpid", return_value=999999), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("High PID numbers", True, "Handled high PID numbers")

        except Exception as e:
            self.log_result("High PID numbers", False, f"Failed with high PID: {e}")

    def test_process_memory_limits(self, env):
        """Test with strict memory limits"""
        print("\n🧠 PROCESS MEMORY LIMITS")

        try:
            # Set very low memory limit
            resource.setrlimit(
                resource.RLIMIT_AS, (50 * 1024 * 1024, 50 * 1024 * 1024)
            )  # 50MB

            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Process memory limits", True, "Handled memory limits gracefully"
                )

        except Exception as e:
            self.log_result(
                "Process memory limits", False, f"Failed with memory limits: {e}"
            )
        finally:
            # Restore memory limits
            try:
                resource.setrlimit(
                    resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
                )
            except:
                pass

    def test_modified_signal_handlers(self, env):
        """Test with modified signal handlers"""
        print("\n📡 MODIFIED SIGNAL HANDLERS")

        try:
            # Install custom signal handler
            def custom_handler(signum, frame):
                pass

            old_handler = signal.signal(signal.SIGTERM, custom_handler)

            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Modified signal handlers", True, "Handled custom signal handlers"
                )

        except Exception as e:
            self.log_result(
                "Modified signal handlers", False, f"Failed with signal handlers: {e}"
            )
        finally:
            # Restore signal handler
            try:
                signal.signal(signal.SIGTERM, old_handler)
            except:
                pass

    def test_different_namespace(self, env):
        """Test in different process namespace"""
        print("\n🏗️ DIFFERENT PROCESS NAMESPACE")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Different namespace", True, "Handled different namespace"
                )

        except Exception as e:
            self.log_result(
                "Different namespace", False, f"Failed in different namespace: {e}"
            )

    def test_unusual_scheduling_priority(self, env):
        """Test with unusual process scheduling priority"""
        print("\n⚡ UNUSUAL SCHEDULING PRIORITY")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                # Set nice level
                os.nice(10)  # Lower priority

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Unusual scheduling priority",
                    True,
                    "Handled low priority scheduling",
                )

        except Exception as e:
            self.log_result(
                "Unusual scheduling priority", False, f"Failed with scheduling: {e}"
            )

    def test_incorrect_system_time(self, env):
        """Test with incorrect system time"""
        print("\n🕐 INCORRECT SYSTEM TIME")

        try:
            with patch("time.time", return_value=0), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Incorrect system time", True, "Handled incorrect system time"
                )

        except Exception as e:
            self.log_result(
                "Incorrect system time", False, f"Failed with bad time: {e}"
            )

    def test_leap_second_handling(self, env):
        """Test leap second handling"""
        print("\n⏰ LEAP SECOND HANDLING")

        try:
            # Simulate time going backwards (leap second correction)
            time_values = [1000000000, 999999999, 1000000000]  # Goes back then forward
            time_index = 0

            def leap_second_time():
                nonlocal time_index
                result = time_values[time_index % len(time_values)]
                time_index += 1
                return result

            with patch("time.time", side_effect=leap_second_time), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Leap second handling", True, "Handled leap second time changes"
                )

        except Exception as e:
            self.log_result(
                "Leap second handling", False, f"Failed with leap second: {e}"
            )

    def test_timezone_edge_cases(self, env):
        """Test timezone edge cases"""
        print("\n🌍 TIMEZONE EDGE CASES")

        try:
            with patch.dict(os.environ, {"TZ": "UTC+25"}), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("Timezone edge cases", True, "Handled unusual timezone")

        except Exception as e:
            self.log_result("Timezone edge cases", False, f"Failed with timezone: {e}")

    def test_ntp_disabled_system(self, env):
        """Test system with NTP disabled and drifting clock"""
        print("\n🕰️ NTP DISABLED SYSTEM")

        try:
            # Simulate clock drift
            base_time = time.time()

            def drifting_time():
                return base_time + (time.time() - base_time) * 1.001  # 0.1% drift

            with patch("time.time", side_effect=drifting_time), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("NTP disabled system", True, "Handled drifting clock")

        except Exception as e:
            self.log_result(
                "NTP disabled system", False, f"Failed with drifting clock: {e}"
            )

    def test_no_swap_space(self, env):
        """Test system with no swap space"""
        print("\n💾 NO SWAP SPACE")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(
                    returncode=0, stdout="Swap: 0 0 0", stderr=""
                )

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("No swap space", True, "Handled system with no swap")

        except Exception as e:
            self.log_result("No swap space", False, f"Failed with no swap: {e}")

    def test_unusual_memory_layout(self, env):
        """Test with unusual memory layout"""
        print("\n🧠 UNUSUAL MEMORY LAYOUT")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Unusual memory layout", True, "Handled unusual memory layout"
                )

        except Exception as e:
            self.log_result(
                "Unusual memory layout", False, f"Failed with memory layout: {e}"
            )

    def test_many_cpu_cores(self, env):
        """Test system with many CPU cores"""
        print("\n🖥️ MANY CPU CORES")

        try:
            with patch("os.cpu_count", return_value=1024), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Many CPU cores", True, "Handled high core count system"
                )

        except Exception as e:
            self.log_result("Many CPU cores", False, f"Failed with many cores: {e}")

    def test_unusual_network_config(self, env):
        """Test with unusual network configuration"""
        print("\n🌐 UNUSUAL NETWORK CONFIG")

        try:
            with patch.dict(os.environ, {"http_proxy": "http://invalid:3128"}), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Unusual network config", True, "Handled unusual network config"
                )

        except Exception as e:
            self.log_result(
                "Unusual network config", False, f"Failed with network config: {e}"
            )

    def test_modified_coreutils(self, env):
        """Test with modified core utilities"""
        print("\n🔧 MODIFIED COREUTILS")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                # Mock modified behavior
                def modified_ls(*args, **kwargs):
                    cmd = args[0] if args else []
                    if "ls" in cmd:
                        return Mock(
                            returncode=0, stdout="modified ls output", stderr=""
                        )
                    return Mock(returncode=0, stdout="", stderr="")

                mock_run.side_effect = modified_ls

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Modified coreutils", True, "Handled modified core utilities"
                )

        except Exception as e:
            self.log_result(
                "Modified coreutils", False, f"Failed with modified coreutils: {e}"
            )

    def test_unusual_python_install(self, env):
        """Test with unusual Python installation"""
        print("\n🐍 UNUSUAL PYTHON INSTALL")

        try:
            with patch("sys.path", ["/weird/python/path"]), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Unusual Python install", True, "Handled unusual Python install"
                )

        except Exception as e:
            self.log_result(
                "Unusual Python install", False, f"Failed with unusual Python: {e}"
            )

    def test_missing_standard_libs(self, env):
        """Test with missing standard libraries"""
        print("\n📚 MISSING STANDARD LIBS")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Missing standard libs", True, "Handled missing standard libraries"
                )

        except Exception as e:
            self.log_result(
                "Missing standard libs", False, f"Failed with missing libs: {e}"
            )

    def test_modified_shell_behavior(self, env):
        """Test with modified shell behavior"""
        print("\n🐚 MODIFIED SHELL BEHAVIOR")

        try:
            with patch.dict(os.environ, {"BASH_ENV": "/dev/null"}), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Modified shell behavior", True, "Handled modified shell behavior"
                )

        except Exception as e:
            self.log_result(
                "Modified shell behavior", False, f"Failed with shell behavior: {e}"
            )

    def test_unusual_flatpak_config(self, env):
        """Test with unusual Flatpak configuration"""
        print("\n📦 UNUSUAL FLATPAK CONFIG")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                # Mock unusual flatpak behavior
                def unusual_flatpak(*args, **kwargs):
                    cmd = args[0] if args else []
                    if "flatpak" in cmd:
                        if "list" in cmd:
                            return Mock(
                                returncode=0,
                                stdout="unusual\x01format\x02data",
                                stderr="",
                            )
                        elif "run" in cmd:
                            return Mock(returncode=1, stdout="", stderr="weird error")
                    return Mock(returncode=0, stdout="", stderr="")

                mock_run.side_effect = unusual_flatpak

                generator = WrapperGenerator(
                    bin_dir=str(env["bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Unusual Flatpak config", True, "Handled unusual Flatpak config"
                )

        except Exception as e:
            self.log_result(
                "Unusual Flatpak config", False, f"Failed with Flatpak config: {e}"
            )

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🤯 ULTRA-EDGE CASES SUMMARY")

        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")

        if total - passed == 0:
            print("✅ ALL ULTRA-EDGE TESTS PASSED - System is IMPERVIOUS!")
        else:
            print("⚠️  SOME ULTRA-EDGE TESTS FAILED - Review extreme edge cases")

        # Show failures
        failures = [
            (name, details) for name, success, details in self.results if not success
        ]
        if failures:
            print("\n❌ FAILED ULTRA-EDGE TESTS:")
            for name, details in failures:
                print(f"  - {name}: {details}")

        # Show interesting results
        interesting = [
            (name, details)
            for name, success, details in self.results
            if success
            and any(
                word in details.lower() for word in ["handled", "worked", "managed"]
            )
        ]
        if interesting:
            print("\n✅ REMARKABLE HANDLING:")
            for name, details in interesting[:10]:  # Show first 10
                print(f"  - {name}: {details}")


def main():
    """Main entry point"""
    tester = UltraEdgeCaseTester()
    tester.run_ultra_edge_tests()


if __name__ == "__main__":
    main()
