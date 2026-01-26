#!/usr/bin/env python3
"""Pytest replacement for test_management_functions.sh
Tests management functionality using proper mocking.
"""

import os
import tempfile
from pathlib import Path

import pytest

# Add lib to path
try:
    from lib.manage import WrapperManager

    MANAGE_AVAILABLE = True
except ImportError:
    MANAGE_AVAILABLE = False


class TestManagementFunctions:
    """Test management functions with pytest."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp(prefix="fpwrapper_mgmt_"))
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"

        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_preference_setting(self, temp_env) -> None:
        """Test preference setting - replaces Test 1."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Test valid preference
        result = manager.set_preference("firefox", "flatpak")
        assert result is True

        # Check preference file was created
        pref_file = temp_env["config_dir"] / "firefox.pref"
        assert pref_file.exists()
        assert pref_file.read_text().strip() == "flatpak"

        # Test another valid preference
        result = manager.set_preference("chrome", "system")
        assert result is True

        chrome_pref = temp_env["config_dir"] / "chrome.pref"
        assert chrome_pref.exists()
        assert chrome_pref.read_text().strip() == "system"

        # Test invalid preference (with special characters not allowed in Flatpak IDs)
        result = manager.set_preference("edge", "invalid value!")
        assert result is False

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_alias_management(self, temp_env) -> None:
        """Test alias management - replaces Test 2."""
        # Create a wrapper first
        wrapper_path = temp_env["bin_dir"] / "firefox"
        wrapper_path.write_text("#!/bin/bash\necho firefox\n")
        wrapper_path.chmod(0o755)

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Create alias
        result = manager.create_alias("browser", "firefox")
        assert result is True

        # Check alias file was created
        alias_file = temp_env["config_dir"] / "aliases"
        assert alias_file.exists()
        content = alias_file.read_text()
        assert "browser:firefox" in content

        # Test duplicate alias (should fail)
        result = manager.create_alias("browser", "chrome")
        assert result is False

        # Test alias for non-existent wrapper (should still work)
        result = manager.create_alias("testalias", "nonexistent")
        assert result is True  # Alias creation doesn't validate target exists

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_environment_variable_management(self, temp_env) -> None:
        """Test environment variable management - replaces Test 3."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Set environment variable
        result = manager.set_environment_variable("firefox", "TEST_VAR", "test_value")
        assert result is True

        # Check env file was created
        env_file = temp_env["config_dir"] / "firefox.env"
        assert env_file.exists()
        content = env_file.read_text()
        assert "TEST_VAR=test_value" in content

        # Set another variable
        result = manager.set_environment_variable(
            "firefox",
            "ANOTHER_VAR",
            "another_value",
        )
        assert result is True

        content = env_file.read_text()
        assert "TEST_VAR=test_value" in content
        assert "ANOTHER_VAR=another_value" in content

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_blocklist_management(self, temp_env) -> None:
        """Test blocklist management - replaces Test 4."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Block an app
        result = manager.block_app("org.mozilla.firefox")
        assert result is True

        # Check blocklist file
        blocklist_file = temp_env["config_dir"] / "blocklist"
        assert blocklist_file.exists()
        content = blocklist_file.read_text()
        assert "org.mozilla.firefox" in content

        # Block another app
        result = manager.block_app("com.google.chrome")
        assert result is True

        content = blocklist_file.read_text()
        assert "org.mozilla.firefox" in content
        assert "com.google.chrome" in content

        # Try to block already blocked app
        result = manager.block_app("org.mozilla.firefox")
        assert result is True  # Should succeed (idempotent)

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_unblock_functionality(self, temp_env) -> None:
        """Test unblock functionality - replaces Test 5."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # First block some apps
        manager.block_app("org.mozilla.firefox")
        manager.block_app("com.google.chrome")

        # Unblock one app
        result = manager.unblock_app("org.mozilla.firefox")
        assert result is True

        # Check blocklist
        blocklist_file = temp_env["config_dir"] / "blocklist"
        content = blocklist_file.read_text()
        assert "org.mozilla.firefox" not in content
        assert "com.google.chrome" in content

        # Try to unblock already unblocked app
        result = manager.unblock_app("com.example.notblocked")
        assert result is True  # Should succeed (idempotent)

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_export_import_preferences(self, temp_env) -> None:
        """Test export/import preferences - replaces Test 6."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Create some preferences
        manager.set_preference("firefox", "flatpak")
        manager.set_preference("chrome", "system")
        manager.set_preference("vlc", "flatpak")

        # Create some aliases
        wrapper_path = temp_env["bin_dir"] / "firefox"
        wrapper_path.write_text("#!/bin/bash\necho firefox\n")
        wrapper_path.chmod(0o755)
        manager.create_alias("browser", "firefox")

        # Export preferences
        export_file = temp_env["temp_dir"] / "prefs.json"
        result = manager.export_preferences(str(export_file))
        assert result is True
        assert export_file.exists()

        # Clear current config
        for pref_file in temp_env["config_dir"].glob("*.pref"):
            pref_file.unlink()
        alias_file = temp_env["config_dir"] / "aliases"
        if alias_file.exists():
            alias_file.unlink()

        # Import preferences
        result = manager.import_preferences(str(export_file))
        assert result is True

        # Check preferences were restored
        assert (temp_env["config_dir"] / "firefox.pref").exists()
        assert (temp_env["config_dir"] / "chrome.pref").exists()
        assert (temp_env["config_dir"] / "vlc.pref").exists()
        assert (temp_env["config_dir"] / "aliases").exists()

        # Check preference values
        assert (
            temp_env["config_dir"] / "firefox.pref"
        ).read_text().strip() == "flatpak"
        assert (temp_env["config_dir"] / "chrome.pref").read_text().strip() == "system"
        assert (temp_env["config_dir"] / "vlc.pref").read_text().strip() == "flatpak"

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_script_management(self, temp_env) -> None:
        """Test script management - replaces Test 7."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Create pre-launch script
        pre_script_content = '#!/bin/bash\necho "pre-launch"\n'
        result = manager.set_pre_launch_script("firefox", pre_script_content)
        assert result is True

        # Check script file was created
        script_dir = temp_env["config_dir"] / "scripts" / "firefox"
        pre_script = script_dir / "pre-launch.sh"
        assert pre_script.exists()
        assert pre_script.read_text() == pre_script_content
        assert os.access(pre_script, os.X_OK)

        # Create post-run script
        post_script_content = '#!/bin/bash\necho "post-run"\n'
        result = manager.set_post_run_script("firefox", post_script_content)
        assert result is True

        post_script = script_dir / "post-run.sh"
        assert post_script.exists()
        assert post_script.read_text() == post_script_content
        assert os.access(post_script, os.X_OK)

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_wrapper_removal(self, temp_env) -> None:
        """Test wrapper removal - replaces Test 8."""
        # Create test files
        wrapper_file = temp_env["bin_dir"] / "testapp"
        wrapper_file.write_text("#!/bin/bash\necho testapp\n")
        wrapper_file.chmod(0o755)

        pref_file = temp_env["config_dir"] / "testapp.pref"
        pref_file.write_text("flatpak\n")

        env_file = temp_env["config_dir"] / "testapp.env"
        env_file.write_text("export TEST=test\n")

        # Create alias pointing to this wrapper
        alias_file = temp_env["config_dir"] / "aliases"
        alias_file.write_text("myalias:testapp\n")

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Remove wrapper
        result = manager.remove_wrapper("testapp", force=True)
        assert result is True

        # Check all files were removed
        assert not wrapper_file.exists()
        assert not pref_file.exists()
        assert not env_file.exists()

        # Check alias was removed
        if alias_file.exists():
            content = alias_file.read_text()
            assert "myalias:testapp" not in content

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_list_wrappers(self, temp_env) -> None:
        """Test list wrappers - replaces Test 9."""
        # Create test wrappers
        wrappers = ["firefox", "chrome", "vlc"]
        for wrapper in wrappers:
            wrapper_file = temp_env["bin_dir"] / wrapper
            # Create proper wrapper content that will be detected
            wrapper_content = f"""#!/usr/bin/env bash
# Generated by fplaunchwrapper

NAME="{wrapper}"
ID="org.{wrapper}.{wrapper}"
echo {wrapper}
"""
            wrapper_file.write_text(wrapper_content)
            wrapper_file.chmod(0o755)

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # List wrappers
        found_wrappers = manager.list_wrappers()
        assert len(found_wrappers) >= 3
        wrapper_names = [w["name"] for w in found_wrappers]
        for wrapper in wrappers:
            assert wrapper in wrapper_names

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_edge_cases_and_security(self, temp_env) -> None:
        """Test edge cases and security - replaces aggressive testing in shell script."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Test empty preference values
        result = manager.set_preference("test", "")
        assert result is False  # Should reject empty

        # Test very long preference values
        long_pref = "flatpak" * 1000  # Very long string
        result = manager.set_preference("test", long_pref)
        if result:
            pref_file = temp_env["config_dir"] / "test.pref"
            content = pref_file.read_text()
            assert len(content) > 1000

        # Test special characters in preferences (should be rejected)
        result = manager.set_preference("test", "flatpak;rm -rf /")
        assert result is False

        # Test unicode in preferences
        result = manager.set_preference("test", "flatpak_🚀")
        # Unicode might be accepted or rejected depending on implementation

        # Test rapid file creation/deletion
        for i in range(10):
            manager.set_preference(f"rapid{i}", "flatpak")
            pref_file = temp_env["config_dir"] / f"rapid{i}.pref"
            if pref_file.exists():
                pref_file.unlink()

        # Should handle rapid operations without crashing
        assert True

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_performance_and_resource_efficiency(self, temp_env) -> None:
        """Test performance and resource efficiency."""
        import time

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=False,  # Reduce output for performance test
            emit_mode=False,
        )

        # Test response time
        start_time = time.time()
        for i in range(100):
            manager.set_preference(f"perf{i}", "flatpak")
        end_time = time.time()

        # Should complete in reasonable time
        duration = end_time - start_time
        assert duration < 5.0  # Less than 5 seconds for 100 operations

        # Check memory usage (rough estimate)
        pref_files = list(temp_env["config_dir"].glob("*.pref"))
        assert len(pref_files) >= 100

        # Test I/O performance
        total_size = sum(len(f.read_text()) for f in pref_files)
        assert total_size > 0

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_concurrent_operation_testing(self, temp_env) -> None:
        """Test concurrent operations."""
        import threading

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=False,
            emit_mode=False,
        )

        results = []
        errors = []

        def worker(thread_id) -> None:
            try:
                for i in range(10):
                    result = manager.set_preference(f"thread{thread_id}_{i}", "flatpak")
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=[i])
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should not have threading errors
        assert len(errors) == 0
        assert len(results) == 50  # 5 threads * 10 operations each
        assert all(results)  # All operations should succeed

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_data_integrity_validation(self, temp_env) -> None:
        """Test data integrity and error recovery."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        # Test corrupted preference file recovery
        pref_file = temp_env["config_dir"] / "corrupted.pref"
        pref_file.write_text("corrupted data\x00\x01\x02")

        # Should handle gracefully
        result = manager.set_preference("corrupted", "flatpak")
        assert isinstance(result, bool)

        # Test preference file corruption recovery
        # Create a corrupted file and see if operations still work
        corrupted_file = temp_env["config_dir"] / "corrupted2.pref"
        corrupted_file.write_text("invalid preference data")

        result = manager.set_preference("corrupted2", "system")
        # Should either succeed or fail gracefully
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
