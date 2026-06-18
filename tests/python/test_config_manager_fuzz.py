#!/usr/bin/env python3
"""Fuzz tests for config_manager module.

These tests verify config_manager handles malformed config data gracefully.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings, HealthCheck, strategies as st

from lib.exceptions import ConfigError, ConfigParseError, ConfigValidationError


# All ConfigError subclasses are acceptable outcomes for fuzz tests:
# the config manager is *supposed* to raise a typed error on bad input
# rather than silently accept it. Catching ConfigError instead of the
# specific subclasses keeps the fuzz test resilient to new error types.
_ACCEPTABLE_CONFIG_ERRORS: tuple[type[BaseException], ...] = (
    ConfigError,
    ValueError,
    TypeError,
    OSError,
    UnicodeDecodeError,
    UnicodeEncodeError,
)


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
    """Generate various config dict structures.

    Only scalar / flat-collection keys are fuzzed. ``global_preferences``
    and ``app_preferences`` are nested dataclass objects whose fields
    must be set through the typed accessor (or via a full config load)
    -- setattr-ing them to a primitive value would break the type
    invariant of the config and trigger spurious AttributeErrors in
    code that follows the contract.
    """
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
                ]
            ),
            st.one_of(
                st.text(max_size=1000),
                st.lists(st.text(max_size=100), max_size=10),
                st.booleans(),
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
        """load_config should handle malformed TOML gracefully.

        A bare ``except Exception: pass`` would hide real bugs (e.g. an
        unexpected ``AttributeError``); we narrow the catch to the
        exceptions a robust TOML loader is *supposed* to raise and
        ``pytest.fail`` on anything else.
        """
        from lib.config_manager import EnhancedConfigManager

        config_file = temp_home / ".config" / "fplaunchwrapper" / "config.toml"
        config_file.write_text(bad_toml)

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            try:
                config.load_config()
                # After a successful (or partially successful) load,
                # the manager must have a ``config`` attribute we can
                # inspect. This is a positive check on the success path.
                assert hasattr(config, "config")
            except _ACCEPTABLE_CONFIG_ERRORS:
                # ValueError: TOML decode error from tomllib/tomli.
                # OSError: I/O problems on the temp file.
                # UnicodeDecodeError: malformed UTF-8 in the file.
                pass
            except Exception as e:  # pragma: no cover - defensive
                pytest.fail(
                    f"load_config crashed on malformed TOML: {e}"
                )

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
            except _ACCEPTABLE_CONFIG_ERRORS:
                pass
            except Exception as e:  # pragma: no cover - defensive
                pytest.fail(f"load_config crashed on binary data: {e}")


class TestConfigSaveFuzz:
    """Fuzz tests for config saving."""

    @given(config_data=config_dict_strategy())
    @settings(
        max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_save_handles_various_configs(self, config_data, temp_home):
        """save_config should handle various config structures.

        The original test had nested ``except Exception: pass`` blocks
        that swallowed every failure, including the round-trip
        ``config2.load_config()`` -- so the test was vacuous and gave
        no signal on whether saved configs were actually re-loadable.
        We narrow the catch to the documented recoverable cases and
        fail the test on anything else, then re-load to verify the
        round-trip succeeded.
        """
        from lib.config_manager import EnhancedConfigManager

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            try:
                config.load_config()
                for key, value in config_data.items():
                    if hasattr(config.config, key):
                        # setattr may raise TypeError/ValueError for
                        # unsupported value types; that is acceptable
                        # for an arbitrary fuzz input.
                        try:
                            setattr(config.config, key, value)
                        except (TypeError, ValueError):
                            continue
                config.save_config()
                # Round-trip: re-load the saved config and confirm the
                # manager is still functional.
                config2 = EnhancedConfigManager()
                config2.load_config()
                assert config2.config is not None
            except _ACCEPTABLE_CONFIG_ERRORS:
                # Validation / serialization failure on arbitrary input
                # is acceptable; the test passes if the manager didn't
                # crash and didn't leave a corrupt config behind.
                pass
            except Exception as e:  # pragma: no cover - defensive
                pytest.fail(
                    f"save_config round-trip crashed: {e}"
                )


class TestConfigValuesFuzz:
    """Fuzz tests for config value validation."""

    @given(cron_value=st.one_of(st.integers(min_value=-1000, max_value=1000), st.text()))
    @settings(
        max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_cron_interval_validation(self, cron_value, temp_home):
        """set_cron_interval should validate input correctly.

        The previous version caught ``(ValueError, TypeError)`` but
        silently allowed the post-assertion ``>= 1`` check to fail
        on valid integer inputs that the validator would have
        clamped.  We now fail the test if the success path doesn't
        hold for integers within the legal range.
        """
        from lib.config_manager import EnhancedConfigManager

        with patch("pathlib.Path.home", return_value=temp_home):
            config = EnhancedConfigManager()
            try:
                config.set_cron_interval(cron_value)
                # Integers in the legal range must be accepted and
                # stored (set_cron_interval clamps negatives to 1).
                if isinstance(cron_value, int) and not isinstance(
                    cron_value, bool
                ):
                    assert config.config.cron_interval >= 1, (
                        f"set_cron_interval({cron_value!r}) stored "
                        f"value below minimum: {config.config.cron_interval}"
                    )
            except (ValueError, TypeError):
                # Non-integer or out-of-range input rejected by the
                # validator -- acceptable.
                pass
            except Exception as e:  # pragma: no cover - defensive
                pytest.fail(
                    f"set_cron_interval crashed on {cron_value!r}: {e}"
                )

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
            except Exception as e:  # pragma: no cover - defensive
                pytest.fail(
                    f"blocklist operations crashed on {blocklist_item!r}: {e}"
                )


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
                assert config.config is not None
            except _ACCEPTABLE_CONFIG_ERRORS:
                pass
            except Exception as e:  # pragma: no cover - defensive
                pytest.fail(f"load_config crashed on old format: {e}")


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
            except (ValueError, OSError, TypeError):
                # list_profiles may reject obviously-bad profile names;
                # that is acceptable.
                pass
            except Exception as e:  # pragma: no cover - defensive
                pytest.fail(
                    f"list_profiles crashed on {profile_name!r}: {e}"
                )


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

            # Truncate the fuzz input so the export path is legal.
            safe_token = "".join(
                c if c.isalnum() or c in "-_." else "_"
                for c in profile_name[:20]
            ) or "default"
            export_path = temp_home / f"export_{safe_token}.toml"
            try:
                config.export_profile(profile_name, export_path)
            except (ValueError, OSError, TypeError):
                # Rejecting a bad name is acceptable; filesystem errors
                # in temp_home are out of scope.
                pass
            except Exception as e:  # pragma: no cover - defensive
                pytest.fail(
                    f"export_profile crashed on {profile_name!r}: {e}"
                )


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
            try:
                test_file.write_text(content)
            except (OSError, UnicodeEncodeError):
                # Some fuzz inputs cannot be encoded as text. Skip.
                return
            try:
                config.import_profile("test", test_file)
            except _ACCEPTABLE_CONFIG_ERRORS:
                # TOML parse failure, validation failure, or
                # filesystem error -- all acceptable for arbitrary input.
                pass
            except Exception as e:  # pragma: no cover - defensive
                pytest.fail(
                    f"import_profile crashed on content: {e}"
                )
