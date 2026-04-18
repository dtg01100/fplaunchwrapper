#!/usr/bin/env python3
"""Pytest replacement for test_management_functions.sh
Tests management functionality using proper mocking.
"""

import tempfile
from pathlib import Path

import pytest

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

        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_preference_setting(self, temp_env) -> None:
        """Test preference setting - replaces Test 1."""
        (temp_env["bin_dir"] / "firefox").write_text("#!/bin/bash\necho firefox\n")
        (temp_env["bin_dir"] / "firefox").chmod(0o755)
        (temp_env["bin_dir"] / "chrome").write_text("#!/bin/bash\necho chrome\n")
        (temp_env["bin_dir"] / "chrome").chmod(0o755)

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        result = manager.set_preference("firefox", "flatpak")
        assert result is True

        pref_file = temp_env["config_dir"] / "firefox.pref"
        assert pref_file.exists()
        assert pref_file.read_text().strip() == "flatpak"

        result = manager.set_preference("chrome", "system")
        assert result is True

        chrome_pref = temp_env["config_dir"] / "chrome.pref"
        assert chrome_pref.exists()
        assert chrome_pref.read_text().strip() == "system"

        result = manager.set_preference("chrome", "system")
        assert result is True

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_invalid_preference_does_not_write_file(self, temp_env) -> None:
        wrapper_path = temp_env["bin_dir"] / "firefox"
        wrapper_path.write_text("#!/bin/bash\necho firefox\n")
        wrapper_path.chmod(0o755)

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        result = manager.set_preference("firefox", "flatpak;rm -rf /")

        assert result is False
        assert not (temp_env["config_dir"] / "firefox.pref").exists()

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_alias_management(self, temp_env) -> None:
        """Test alias management - replaces Test 2."""
        wrapper_path = temp_env["bin_dir"] / "firefox"
        wrapper_path.write_text("#!/bin/bash\necho firefox\n")
        wrapper_path.chmod(0o755)

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        result = manager.create_alias("browser", "firefox")
        assert result is True

        alias_file = temp_env["config_dir"] / "aliases"
        assert alias_file.exists()
        content = alias_file.read_text()
        assert "browser:firefox" in content

        result = manager.create_alias("browser", "chrome")
        assert result is False

        result = manager.create_alias("testalias", "nonexistent")
        assert result is True

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_wrapper_removal(self, temp_env) -> None:
        """Test wrapper removal - replaces Test 8."""
        wrapper_file = temp_env["bin_dir"] / "testapp"
        wrapper_file.write_text("#!/bin/bash\necho testapp\n")
        wrapper_file.chmod(0o755)

        pref_file = temp_env["config_dir"] / "testapp.pref"
        pref_file.write_text("flatpak\n")

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        result = manager.remove_wrapper("testapp", force=True)
        assert result is True

        assert not wrapper_file.exists()
        assert not pref_file.exists()

    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_list_wrappers(self, temp_env) -> None:
        """Test list wrappers - replaces Test 9."""
        wrappers = ["firefox", "chrome", "vlc"]
        for wrapper in wrappers:
            wrapper_file = temp_env["bin_dir"] / wrapper
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

        found_wrappers = manager.list_wrappers()
        assert len(found_wrappers) >= 3
        wrapper_names = [w["name"] for w in found_wrappers]
        for wrapper in wrappers:
            assert wrapper in wrapper_names

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
