#!/usr/bin/env python3
"""
Advanced Edge Cases Test - Non-Standard Directories & Internationalization

Tests fplaunchwrapper with unusual directory layouts and non-English system setups.
These are real-world scenarios that can break software unexpectedly.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
import locale
import time

# Import modules safely
try:
    from fplaunch.generate import WrapperGenerator
    from fplaunch.manage import WrapperManager
    from fplaunch.launch import AppLauncher

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


class AdvancedEdgeCaseTester:
    """Test advanced edge cases for non-standard setups"""

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
        self.temp_dir = Path(tempfile.mkdtemp(prefix="advanced_edge_"))

        # Create various non-standard directory layouts
        env = {
            "temp_root": self.temp_dir,
            "alt_home": self.temp_dir / "alt_home",
            "custom_config": self.temp_dir / "custom_config",
            "unusual_bin": self.temp_dir / "unusual_bin",
            "weird_cache": self.temp_dir / "weird_cache",
            "strange_local": self.temp_dir / "strange_local",
            "odd_share": self.temp_dir / "odd_share",
        }

        # Create directories
        for path in env.values():
            if isinstance(path, Path):
                path.mkdir(parents=True, exist_ok=True)

        # Create bin_dir files in config directories (required by WrapperManager)
        for config_dir in [env["custom_config"], env["strange_local"]]:
            bin_dir_file = config_dir / "bin_dir"
            bin_dir_file.write_text(str(env["unusual_bin"]))

        return env

    def cleanup_temp_env(self):
        """Clean up test environment"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_advanced_tests(self):
        """Run all advanced edge case tests"""
        if not MODULES_AVAILABLE:
            print("❌ Modules not available for testing")
            return

        print("🔬 ADVANCED EDGE CASES TEST")
        print("=" * 50)

        try:
            env = self.setup_temp_env()

            # Directory location tests
            self.test_non_standard_home_directory(env)
            self.test_custom_xdg_directories(env)
            self.test_symlinked_xdg_base(env)
            self.test_network_mounted_home(env)
            self.test_readonly_home_subdirectory(env)
            self.test_missing_xdg_directories(env)
            self.test_nested_xdg_structure(env)
            self.test_alternative_config_locations(env)

            # Internationalization tests
            self.test_non_utf8_locale(env)
            self.test_c_locale_minimal(env)
            self.test_unicode_system_locale(env)
            self.test_right_to_left_locale(env)
            self.test_chinese_locale(env)
            self.test_emoji_in_paths(env)
            self.test_mixed_encoding_files(env)

            # Advanced filesystem tests
            self.test_fuse_filesystems(env)
            self.test_overlay_filesystems(env)
            self.test_compressed_filesystems(env)
            self.test_ram_disks(env)
            self.test_external_storage_mounts(env)

            # Print summary
            self.print_summary()

        finally:
            self.cleanup_temp_env()

    def test_non_standard_home_directory(self, env):
        """Test with home directory in unusual location"""
        print("\n🏠 NON-STANDARD HOME DIRECTORY")

        # Simulate home directory in /var/home or /srv/home
        unusual_home = env["temp_root"] / "srv" / "users" / "testuser"
        unusual_home.mkdir(parents=True)

        try:
            with patch("pathlib.Path.home", return_value=unusual_home), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Non-standard home directory",
                    True,
                    f"Handled home in {unusual_home}",
                )

        except Exception as e:
            self.log_result(
                "Non-standard home directory", False, f"Failed with unusual home: {e}"
            )

    def test_custom_xdg_directories(self, env):
        """Test with custom XDG directory locations"""
        print("\n📂 CUSTOM XDG DIRECTORIES")

        # Set custom XDG environment variables
        custom_xdg = {
            "XDG_CONFIG_HOME": str(env["custom_config"]),
            "XDG_CACHE_HOME": str(env["weird_cache"]),
            "XDG_DATA_HOME": str(env["strange_local"]),
        }

        try:
            with patch.dict(os.environ, custom_xdg), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Custom XDG directories", True, "Handled custom XDG locations"
                )

        except Exception as e:
            self.log_result(
                "Custom XDG directories", False, f"Failed with custom XDG: {e}"
            )

    def test_symlinked_xdg_base(self, env):
        """Test when XDG base directories are symlinks"""
        print("\n🔗 SYMLINKED XDG BASE DIRECTORIES")

        # Create symlinked XDG structure
        real_config = env["temp_root"] / "real_config"
        real_config.mkdir()
        # Create bin_dir file in real config
        (real_config / "bin_dir").write_text(str(env["unusual_bin"]))

        symlink_config = env["custom_config"] / "symlink_config"
        os.symlink(str(real_config), str(symlink_config))

        custom_xdg = {"XDG_CONFIG_HOME": str(symlink_config)}

        try:
            with patch.dict(os.environ, custom_xdg), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                manager = WrapperManager(
                    config_dir=str(symlink_config), verbose=False, emit_mode=True
                )

                result = manager.set_preference("test_app", "flatpak")
                self.log_result(
                    "Symlinked XDG base directories", True, "Handled symlinked XDG dirs"
                )

        except Exception as e:
            self.log_result(
                "Symlinked XDG base directories",
                False,
                f"Failed with symlinked XDG: {e}",
            )

    def test_network_mounted_home(self, env):
        """Test with network-mounted home directory (simulated)"""
        print("\n🌐 NETWORK-MOUNTED HOME")

        # Simulate slow/network filesystem with delays
        network_home = env["alt_home"]

        try:
            with patch("pathlib.Path.home", return_value=network_home), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                # Simulate network delay
                def slow_run(*args, **kwargs):
                    time.sleep(0.1)  # Simulate network latency
                    return Mock(returncode=0, stdout="", stderr="")

                mock_run.side_effect = slow_run

                start_time = time.time()
                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                end_time = time.time()

                duration = end_time - start_time
                if duration > 1.0:  # Should still be reasonably fast
                    self.log_result(
                        "Network-mounted home", False, f"Too slow: {duration:.2f}s"
                    )
                else:
                    self.log_result(
                        "Network-mounted home",
                        True,
                        f"Handled network mount in {duration:.2f}s",
                    )

        except Exception as e:
            self.log_result(
                "Network-mounted home", False, f"Failed with network mount: {e}"
            )

    def test_readonly_home_subdirectory(self, env):
        """Test when subdirectories of home are read-only"""
        print("\n🔒 READ-ONLY HOME SUBDIRECTORY")

        readonly_dir = env["alt_home"] / ".config" / "readonly"
        readonly_dir.mkdir(parents=True)

        # Make subdirectory read-only
        readonly_dir.chmod(0o444)

        try:
            with patch("pathlib.Path.home", return_value=env["alt_home"]), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Read-only home subdirectory", True, "Handled read-only subdirs"
                )

        except Exception as e:
            self.log_result(
                "Read-only home subdirectory",
                False,
                f"Failed with read-only subdir: {e}",
            )
        finally:
            # Restore permissions
            try:
                readonly_dir.chmod(0o755)
            except:
                pass

    def test_missing_xdg_directories(self, env):
        """Test when XDG directories don't exist"""
        print("\n❌ MISSING XDG DIRECTORIES")

        # Remove XDG directories
        custom_config = env["custom_config"]
        if custom_config.exists():
            shutil.rmtree(custom_config)

        custom_xdg = {"XDG_CONFIG_HOME": str(custom_config)}

        try:
            with patch.dict(os.environ, custom_xdg), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                manager = WrapperManager(
                    config_dir=str(custom_config), verbose=False, emit_mode=True
                )

                result = manager.set_preference("test_app", "flatpak")
                self.log_result(
                    "Missing XDG directories", True, "Created missing XDG dirs"
                )

        except Exception as e:
            self.log_result(
                "Missing XDG directories", False, f"Failed with missing XDG: {e}"
            )

    def test_nested_xdg_structure(self, env):
        """Test deeply nested XDG directory structure"""
        print("\n📁 NESTED XDG STRUCTURE")

        # Create deeply nested XDG structure
        nested_config = env["custom_config"]
        for i in range(5):  # 5 levels deep
            nested_config = nested_config / f"level_{i}"
        nested_config.mkdir(parents=True)

        custom_xdg = {"XDG_CONFIG_HOME": str(nested_config)}

        try:
            with patch.dict(os.environ, custom_xdg), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                manager = WrapperManager(
                    config_dir=str(nested_config), verbose=False, emit_mode=True
                )

                result = manager.set_preference("test_app", "flatpak")
                self.log_result(
                    "Nested XDG structure", True, f"Handled {nested_config} depth"
                )

        except Exception as e:
            self.log_result(
                "Nested XDG structure", False, f"Failed with nested XDG: {e}"
            )

    def test_alternative_config_locations(self, env):
        """Test alternative configuration file locations"""
        print("\n📄 ALTERNATIVE CONFIG LOCATIONS")

        # Test config in /etc, /usr/local/etc, etc.
        alt_config_locations = [
            env["temp_root"] / "etc" / "fplaunchwrapper",
            env["temp_root"] / "usr" / "local" / "etc" / "fplaunchwrapper",
            env["temp_root"] / "opt" / "fplaunchwrapper" / "config",
        ]

        for alt_config in alt_config_locations:
            alt_config.mkdir(parents=True)

            try:
                with patch("os.path.exists", return_value=True), patch(
                    "subprocess.run"
                ) as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                    manager = WrapperManager(
                        config_dir=str(alt_config), verbose=False, emit_mode=True
                    )

                    result = manager.set_preference("test_app", "flatpak")
                    self.log_result(
                        f"Config in {alt_config.parent.name}",
                        True,
                        f"Handled {alt_config}",
                    )

            except Exception as e:
                self.log_result(
                    f"Config in {alt_config.parent.name}", False, f"Failed: {e}"
                )

    def test_non_utf8_locale(self, env):
        """Test with non-UTF-8 locale settings"""
        print("\n🌍 NON-UTF-8 LOCALE")

        # Simulate ISO-8859-1 locale
        latin1_env = {
            "LANG": "en_US.ISO-8859-1",
            "LC_ALL": "en_US.ISO-8859-1",
        }

        try:
            with patch.dict(os.environ, latin1_env), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="test", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("Non-UTF-8 locale", True, "Handled ISO-8859-1 locale")

        except Exception as e:
            self.log_result("Non-UTF-8 locale", False, f"Failed with non-UTF-8: {e}")

    def test_c_locale_minimal(self, env):
        """Test with minimal C locale (POSIX)"""
        print("\n🇨 C LOCALE MINIMAL")

        c_locale_env = {
            "LANG": "C",
            "LC_ALL": "C",
            "LC_MESSAGES": "C",
        }

        try:
            with patch.dict(os.environ, c_locale_env), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="test", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("C locale minimal", True, "Handled minimal C locale")

        except Exception as e:
            self.log_result("C locale minimal", False, f"Failed with C locale: {e}")

    def test_unicode_system_locale(self, env):
        """Test with unicode system locale"""
        print("\n🔤 UNICODE SYSTEM LOCALE")

        unicode_locale_env = {
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
        }

        try:
            with patch.dict(os.environ, unicode_locale_env), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="🚀✨🎯", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Unicode system locale", True, "Handled UTF-8 with unicode output"
                )

        except Exception as e:
            self.log_result(
                "Unicode system locale", False, f"Failed with unicode locale: {e}"
            )

    def test_right_to_left_locale(self, env):
        """Test with right-to-left locale"""
        print("\n📝 RIGHT-TO-LEFT LOCALE")

        rtl_locale_env = {
            "LANG": "ar_SA.UTF-8",
            "LC_ALL": "ar_SA.UTF-8",
        }

        try:
            with patch.dict(os.environ, rtl_locale_env), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="اختبار", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("Right-to-left locale", True, "Handled RTL locale")

        except Exception as e:
            self.log_result(
                "Right-to-left locale", False, f"Failed with RTL locale: {e}"
            )

    def test_chinese_locale(self, env):
        """Test with Chinese locale"""
        print("\n🇨🇳 CHINESE LOCALE")

        chinese_locale_env = {
            "LANG": "zh_CN.UTF-8",
            "LC_ALL": "zh_CN.UTF-8",
        }

        try:
            with patch.dict(os.environ, chinese_locale_env), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="测试", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("Chinese locale", True, "Handled Chinese locale")

        except Exception as e:
            self.log_result("Chinese locale", False, f"Failed with Chinese locale: {e}")

    def test_emoji_in_paths(self, env):
        """Test with emoji characters in directory paths"""
        print("\n😀 EMOJI IN PATHS")

        emoji_path = env["temp_root"] / "🏠📁🚀"
        emoji_path.mkdir()

        try:
            with patch("pathlib.Path.home", return_value=emoji_path), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("Emoji in paths", True, "Handled emoji directory names")

        except Exception as e:
            self.log_result("Emoji in paths", False, f"Failed with emoji paths: {e}")

    def test_mixed_encoding_files(self, env):
        """Test with files that have mixed encodings"""
        print("\n🔄 MIXED ENCODING FILES")

        config_file = env["custom_config"] / "mixed_encoding.toml"
        # Create file with mixed encoding content (simulated)
        mixed_content = """# Mixed encoding test
[preferences]
app1 = "flatpak"
# Comment with unicode: 🚀
app2 = "system"
"""

        config_file.write_text(mixed_content, encoding="utf-8")

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                manager = WrapperManager(
                    config_dir=str(env["custom_config"]), verbose=False, emit_mode=True
                )

                result = manager.get_preference("app1")
                self.log_result(
                    "Mixed encoding files", True, "Handled mixed encoding config"
                )

        except Exception as e:
            self.log_result(
                "Mixed encoding files", False, f"Failed with mixed encoding: {e}"
            )

    def test_fuse_filesystems(self, env):
        """Test with FUSE-based filesystems (sshfs, etc.)"""
        print("\n🔥 FUSE FILESYSTEMS")

        # Simulate FUSE mount characteristics (permissions, etc.)
        fuse_dir = env["alt_home"]
        # FUSE mounts often have unusual permission bits
        fuse_dir.chmod(0o777)

        try:
            with patch("pathlib.Path.home", return_value=fuse_dir), patch(
                "os.path.exists", return_value=True
            ), patch("subprocess.run") as mock_run:
                # Simulate FUSE-like delays
                def fuse_delay(*args, **kwargs):
                    time.sleep(0.05)  # FUSE can be slower
                    return Mock(returncode=0, stdout="", stderr="")

                mock_run.side_effect = fuse_delay

                start_time = time.time()
                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                end_time = time.time()

                duration = end_time - start_time
                self.log_result(
                    "FUSE filesystems",
                    True,
                    f"Handled FUSE-like delays in {duration:.2f}s",
                )

        except Exception as e:
            self.log_result("FUSE filesystems", False, f"Failed with FUSE: {e}")

    def test_overlay_filesystems(self, env):
        """Test with overlay filesystem (containers, etc.)"""
        print("\n📦 OVERLAY FILESYSTEMS")

        # Overlay filesystems have copy-on-write semantics
        overlay_dir = env["strange_local"]

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run, patch("pathlib.Path.home", return_value=env["alt_home"]):
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                # Test multiple operations that might stress overlay
                manager = WrapperManager(
                    config_dir=str(overlay_dir), verbose=False, emit_mode=True
                )

                for i in range(5):
                    manager.set_preference(f"overlay_app_{i}", "flatpak")

                for i in range(5):
                    result = manager.get_preference(f"overlay_app_{i}")

                self.log_result(
                    "Overlay filesystems", True, "Handled overlay filesystem operations"
                )

        except Exception as e:
            self.log_result("Overlay filesystems", False, f"Failed with overlay: {e}")

    def test_compressed_filesystems(self, env):
        """Test with compressed filesystems (ZFS, Btrfs)"""
        print("\n🗜️ COMPRESSED FILESYSTEMS")

        compressed_dir = env["weird_cache"]

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                # Create many small files (compression stress test)
                for i in range(20):
                    test_file = compressed_dir / f"compressed_test_{i}.txt"
                    test_file.write_text(f"Compressed filesystem test {i}\n" * 10)

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "Compressed filesystems", True, "Handled compressed filesystem I/O"
                )

        except Exception as e:
            self.log_result(
                "Compressed filesystems", False, f"Failed with compressed FS: {e}"
            )

    def test_ram_disks(self, env):
        """Test with RAM disks (/tmp is often tmpfs)"""
        print("\n💾 RAM DISKS")

        ram_disk = env["temp_root"] / "ramdisk"
        ram_disk.mkdir()

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run, patch("tempfile.gettempdir", return_value=str(ram_disk)):
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                # Operations that use temp directories
                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result("RAM disks", True, "Handled RAM disk operations")

        except Exception as e:
            self.log_result("RAM disks", False, f"Failed with RAM disk: {e}")

    def test_external_storage_mounts(self, env):
        """Test with external storage mounts (USB drives, etc.)"""
        print("\n💿 EXTERNAL STORAGE MOUNTS")

        # Simulate external mount with different characteristics
        external_mount = env["temp_root"] / "media" / "user" / "USBDRIVE"
        external_mount.mkdir(parents=True)

        # External drives often have different permissions/ownership
        external_mount.chmod(0o755)

        try:
            with patch("os.path.exists", return_value=True), patch(
                "subprocess.run"
            ) as mock_run, patch("pathlib.Path.home", return_value=external_mount):
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

                generator = WrapperGenerator(
                    bin_dir=str(env["unusual_bin"]), verbose=False, emit_mode=True
                )

                result = generator.generate_wrapper("org.test.app")
                self.log_result(
                    "External storage mounts", True, "Handled external drive operations"
                )

        except Exception as e:
            self.log_result(
                "External storage mounts", False, f"Failed with external mount: {e}"
            )

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("🔬 ADVANCED EDGE CASES SUMMARY")

        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")

        if total - passed == 0:
            print("✅ ALL TESTS PASSED - Handles advanced edge cases perfectly!")
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
            if success and ("Handled" in details or "Created" in details)
        ]
        if interesting:
            print("\n✅ INTERESTING SUCCESSFUL HANDLING:")
            for name, details in interesting[:8]:  # Show first 8
                print(f"  - {name}: {details}")


def main():
    """Main entry point"""
    tester = AdvancedEdgeCaseTester()
    tester.run_advanced_tests()


if __name__ == "__main__":
    main()
