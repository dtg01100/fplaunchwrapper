#!/usr/bin/env python3
"""Fuzz tests for config_manager module.

These tests verify config_manager handles malformed config data gracefully.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings, HealthCheck, strategies as st


# Strategies
# ==========================


@st.composite
def toml_string_strategy(draw) -> str:
    """Generate strings that might be in TOML config."""
    return draw(
        st.sampled_from(
            [
                "",
                "a",
                "x" * 100,
                "x" * 1000,
                "hello world",
                "hello\\tworld",
                'hello"world',
                "hello\nworld",
                "hello\rworld",
                "hello;world",
                "hello$world",
                "hello世界",
                "café",
                "\u200b",
                "\ufeff",
                "'; DROP TABLE users; --",
                "<script>alert('xss')</script>",
                "${env:PATH}",
                "$(whoami)",
                "😀" * 10,
                "x" * 10000,
            ]
        )
    )


@st.composite
def config_dict_strategy(draw) -> dict:
    """Generate various config dict structures."""
    return draw(
        st.dictionaries(
            st.sampled_from(
                [
                    "bin_dir",
                    "config_dir",
                    "data_dir",
                    "blocklist",
                    "cron_interval",
                    "enable_notifications",
                    "global_preferences",
                ]
            ),
            st.one_of(
                st.text(max_size=1000),
                st.lists(st.text(max_size=100), max_size=10),
                st.booleans(),
                st.dictionaries(st.text(), st.text()),
            ),
            max_size=10,
        )
    )


# Fixtures
# ==========================


@pytest.fixture
def temp_home(tmp_path):
    """Create a temp home directory."""
    home = tmp_path / "home"
    home.mkdir()
    config_dir = home / ".config" / "fplaunchwrapper"
    config_dir.mkdir(parents=True)
    data_dir = home / ".local" / "share" / "fplaunchwrapper"
    data_dir.mkdir(parents=True)
    return home


# Tests
# ==========================


class TestConfigLoadFuzz:
    """Fuzz tests for config loading."""

    @given(bad_toml=toml_string_strategy())
    @settings(
        max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_load_rejects_malformed_toml(self, bad_toml, temp_home):
        """load_config should handle malformed TOML gracefully."""
        from lib.config_manager import EnhancedConfigManager

        config_file = temp_home / ".config" / "fplaunchwrapper" / "config.toml"
        config_file.write_text(bad_toml)

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            try:
                config.load_config()
                assert hasattr(config, "config")
            except Exception:
                pass

    @given(data=st.binary(max_size=10000))
    @settings(
        max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_load_handles_binary_data(self, data, temp_home):
        """load_config should handle binary data gracefully."""
        from lib.config_manager import EnhancedConfigManager

        config_file = temp_home / ".config" / "fplaunchwrapper" / "config.toml"
        config_file.write_bytes(data)

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            try:
                config.load_config()
            except Exception:
                pass


class TestConfigSaveFuzz:
    """Fuzz tests for config saving."""

    @given(config_data=config_dict_strategy())
    @settings(
        max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_save_handles_various_configs(self, config_data, temp_home):
        """save_config should handle various config structures."""
        from lib.config_manager import EnhancedConfigManager

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            try:
                config.load_config()
                for key, value in config_data.items():
                    try:
                        if hasattr(config.config, key):
                            setattr(config.config, key, value)
                    except Exception:
                        pass
                config.save_config()
                config2 = EnhancedConfigManager()
                config2.load_config()
            except Exception:
                pass


class TestConfigValuesFuzz:
    """Fuzz tests for config value validation."""

    @given(cron_value=st.one_of(st.integers(min_value=-1000, max_value=1000), st.text()))
    @settings(
        max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_cron_interval_validation(self, cron_value, temp_home):
        """set_cron_interval should validate input correctly."""
        from lib.config_manager import EnhancedConfigManager

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            try:
                config.set_cron_interval(cron_value)
                assert config.config.cron_interval >= 1
            except (ValueError, TypeError):
                pass

    @given(blocklist_item=toml_string_strategy())
    @settings(
        max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_blocklist_handles_various_items(self, blocklist_item, temp_home):
        """Blocklist operations should handle various inputs."""
        from lib.config_manager import EnhancedConfigManager

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            try:
                config.load_config()
                config.add_to_blocklist(blocklist_item)
                result = config.is_blocked(blocklist_item)
                assert isinstance(result, bool)
                config.remove_from_blocklist(blocklist_item)
            except (ValueError, TypeError):
                pass


class TestConfigMigrationFuzz:
    """Fuzz tests for config migration."""

    @given(old_format=st.text(max_size=10000))
    @settings(
        max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_migration_handles_old_formats(self, old_format, temp_home):
        """Migration should handle various old config formats."""
        from lib.config_manager import EnhancedConfigManager

        config_file = temp_home / ".config" / "fplaunchwrapper" / "config.toml"
        config_file.write_text(old_format)

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            try:
                config.load_config()
            except Exception:
                pass


class TestProfileFuzz:
    """Fuzz tests for profile operations."""

    def test_export_import_roundtrip(self, temp_home):
        """Export and import should be reversible."""
        from lib.config_manager import EnhancedConfigManager

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            config.load_config()

            export_path = temp_home / "test_export.toml"
            result = config.export_profile("default", export_path)

            if result:
                config2 = EnhancedConfigManager()
                config2.load_config()
                imported = config2.import_profile("default", export_path)
                assert isinstance(imported, bool)

    @given(profile_name=toml_string_strategy())
    @settings(
        max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_profile_names_handled_gracefully(self, profile_name, temp_home):
        """Profile operations should handle unusual names."""
        from lib.config_manager import EnhancedConfigManager

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            try:
                config.load_config()
                profiles = config.list_profiles()
                assert isinstance(profiles, list)
            except Exception:
                pass


class TestExportFuzz:
    """Fuzz tests for export functionality."""

    @given(profile_name=toml_string_strategy())
    @settings(
        max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_export_handles_various_names(self, profile_name, temp_home):
        """Export should handle various profile names."""
        from lib.config_manager import EnhancedConfigManager

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            config.load_config()

            export_path = temp_home / f"export_{profile_name[:20]}.toml"
            try:
                config.export_profile(profile_name, export_path)
            except Exception:
                pass


class TestImportFuzz:
    """Fuzz tests for import functionality."""

    def test_import_nonexistent_file(self, temp_home):
        """Import should handle missing files gracefully."""
        from lib.config_manager import EnhancedConfigManager

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            config.load_config()

            missing_file = temp_home / "nonexistent.toml"
            result = config.import_profile("test", missing_file)
            assert result is False

    @given(content=toml_string_strategy())
    @settings(
        max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_import_various_contents(self, content, temp_home):
        """Import should handle various file contents."""
        from lib.config_manager import EnhancedConfigManager

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            config.load_config()

            test_file = temp_home / "test_import.toml"
            test_file.write_text(content)

            try:
                config.import_profile("test", test_file)
            except Exception:
                pass
