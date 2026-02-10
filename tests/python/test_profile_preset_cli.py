#!/usr/bin/env python3
"""Tests for profile and preset CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.config_manager import EnhancedConfigManager


class TestProfileCLICommands:
    """Test profile management CLI commands."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_list_profiles_default(self, temp_config_dir):
        """Test listing profiles shows default."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()
            profiles = manager.list_profiles()

            assert "default" in profiles
            assert isinstance(profiles, list)

    def test_create_profile(self, temp_config_dir):
        """Test creating a new profile."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Create a profile
            success = manager.create_profile("work")
            assert success is True

            # Verify it's in the list
            profiles = manager.list_profiles()
            assert "work" in profiles

    def test_create_profile_fails_for_default(self, temp_config_dir):
        """Test creating default profile fails."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Can't create default profile
            success = manager.create_profile("default")
            assert success is False

    def test_create_profile_duplicate_fails(self, temp_config_dir):
        """Test creating duplicate profile fails."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Create profile
            success1 = manager.create_profile("gaming")
            assert success1 is True

            # Try to create same profile again
            success2 = manager.create_profile("gaming")
            assert success2 is False

    def test_create_profile_with_copy(self, temp_config_dir):
        """Test creating profile by copying from existing."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Create source profile
            success1 = manager.create_profile("source")
            assert success1 is True

            # Create profile by copying
            success2 = manager.create_profile("target", copy_from="source")
            assert success2 is True

            # Both should exist
            profiles = manager.list_profiles()
            assert "source" in profiles
            assert "target" in profiles

    def test_switch_profile(self, temp_config_dir):
        """Test switching between profiles."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Create a profile
            manager.create_profile("work")

            # Switch to it
            success = manager.switch_profile("work")
            assert success is True

            # Verify it's active
            current = manager.get_active_profile()
            assert current == "work"

    def test_switch_profile_fails_nonexistent(self, temp_config_dir):
        """Test switching to nonexistent profile fails."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Try to switch to nonexistent profile
            success = manager.switch_profile("nonexistent")
            assert success is False

    def test_get_active_profile(self, temp_config_dir):
        """Test getting active profile."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Default should be active
            current = manager.get_active_profile()
            assert current == "default"

    def test_export_profile(self, temp_config_dir):
        """Test exporting a profile."""
        with tempfile.TemporaryDirectory() as export_dir:
            export_dir_path = Path(export_dir)

            with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
                manager = EnhancedConfigManager()

                # Create a profile
                manager.create_profile("gaming")

                # Export it
                export_path = export_dir_path / "gaming.toml"
                success = manager.export_profile("gaming", export_path)
                assert success is True
                assert export_path.exists()

    def test_import_profile(self, temp_config_dir):
        """Test importing a profile from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("# Test profile\n")
            import_path = Path(f.name)

        try:
            with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
                manager = EnhancedConfigManager()

                # Import profile
                success = manager.import_profile("imported", import_path)
                assert success is True

                # Verify it exists
                profiles = manager.list_profiles()
                assert "imported" in profiles
        finally:
            import_path.unlink()


class TestPresetCLICommands:
    """Test permission preset CLI commands."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_list_presets_empty(self, temp_config_dir):
        """Test listing presets includes built-in presets."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()
            presets = manager.list_permission_presets()

            assert isinstance(presets, list)
            assert len(presets) == 6  # Built-in presets
            assert "development" in presets
            assert "gaming" in presets
            assert "media" in presets

    def test_add_preset(self, temp_config_dir):
        """Test adding a permission preset."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Add preset
            permissions = ["--filesystem=home", "--device=dri"]
            manager.add_permission_preset("development", permissions)

            # Verify it's in the list
            presets = manager.list_permission_presets()
            assert "development" in presets

    def test_get_preset(self, temp_config_dir):
        """Test getting a preset's permissions."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Add preset
            permissions = ["--filesystem=home", "--device=dri"]
            manager.add_permission_preset("work", permissions)

            # Get it
            retrieved = manager.get_permission_preset("work")
            assert retrieved == permissions

    def test_get_preset_nonexistent(self, temp_config_dir):
        """Test getting nonexistent preset returns None."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Try to get nonexistent preset
            retrieved = manager.get_permission_preset("nonexistent")
            assert retrieved is None

    def test_remove_preset(self, temp_config_dir):
        """Test removing a preset."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Add preset
            manager.add_permission_preset("temporary", ["--share=network"])

            # Remove it
            success = manager.remove_permission_preset("temporary")
            assert success is True

            # Verify it's gone
            presets = manager.list_permission_presets()
            assert "temporary" not in presets

    def test_remove_preset_nonexistent(self, temp_config_dir):
        """Test removing nonexistent preset fails."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            # Try to remove nonexistent preset
            success = manager.remove_permission_preset("nonexistent")
            assert success is False

    def test_preset_persistence(self, temp_config_dir):
        """Test that presets persist across instances."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager1 = EnhancedConfigManager()
            manager1.add_permission_preset(
                "custom", ["--device=dri", "--socket=pulseaudio"]
            )

            manager2 = EnhancedConfigManager()
            presets = manager2.list_permission_presets()
            assert "custom" in presets

            perms = manager2.get_permission_preset("custom")
            assert perms is not None
            assert "--device=dri" in perms
            assert "--socket=pulseaudio" in perms

    def test_multiple_presets(self, temp_config_dir):
        """Test managing multiple custom presets."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            presets_data = {
                "custom1": ["--filesystem=home", "--device=dri"],
                "custom2": ["--device=dri", "--socket=pulseaudio"],
                "custom3": ["--share=network"],
            }

            for name, perms in presets_data.items():
                manager.add_permission_preset(name, perms)

            presets = manager.list_permission_presets()
            for name in presets_data.keys():
                assert name in presets

    def test_preset_update(self, temp_config_dir):
        """Test updating existing preset."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = EnhancedConfigManager()

            manager.add_permission_preset("custom", ["--device=dri"])
            updated_perms = ["--device=dri", "--socket=pulseaudio", "--share=network"]
            manager.add_permission_preset("custom", updated_perms)

            perms = manager.get_permission_preset("custom")
            assert perms is not None
            assert perms == updated_perms
            assert len(perms) == 3
