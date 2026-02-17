#!/usr/bin/env python3
"""Unit tests for config_manager.py
Tests configuration file management with proper mocking.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add lib to path
try:
    from lib.config_manager import EnhancedConfigManager, create_config_manager
except ImportError:
    # Mock it if not available
    EnhancedConfigManager = None
    create_config_manager = None


class TestConfigManager:
    """Test configuration manager functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / ".config" / "fplaunchwrapper"
        self.data_dir = self.temp_dir / ".local" / "share" / "fplaunchwrapper"
        self.config_file = self.config_dir / "config.toml"

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_config_manager(self) -> None:
        """Test config manager creation."""
        if not create_config_manager:
            pytest.skip("config_manager module not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = create_config_manager()

            assert config is not None
            assert hasattr(config, "config")
            assert hasattr(config, "config_dir")
            assert hasattr(config, "data_dir")

    def test_config_manager_initialization(self) -> None:
        """Test config manager initialization with defaults."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        config = EnhancedConfigManager()

        # Check default values
        assert hasattr(config.config, "bin_dir")
        assert hasattr(config.config, "debug_mode")
        assert hasattr(config.config, "log_level")
        assert hasattr(config.config, "blocklist")

        # Default values
        assert config.config.debug_mode is False
        assert config.config.log_level == "INFO"
        assert isinstance(config.config.blocklist, list)

    @patch("pathlib.Path.home")
    def test_config_directory_creation(self, mock_home) -> None:
        """Test config directory creation."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        EnhancedConfigManager()

        # Should create config directory
        assert self.config_dir.exists()
        assert self.data_dir.exists()

    @patch("pathlib.Path.home")
    @patch("tomli.load")
    def test_config_file_loading(self, mock_tomli_load, mock_home) -> None:
        """Test loading configuration from TOML file."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        # Mock TOML content
        mock_config = {
            "bin_dir": "/custom/bin",
            "debug_mode": True,
            "log_level": "DEBUG",
            "blocklist": ["app1", "app2"],
        }
        mock_tomli_load.return_value = mock_config

        # Create config file
        self.config_dir.mkdir(parents=True)
        self.config_file.write_text('bin_dir = "/custom/bin"')

        config = EnhancedConfigManager()

        # Should load config from file
        assert config.config.bin_dir == "/custom/bin"
        assert config.config.debug_mode is True
        assert config.config.log_level == "DEBUG"
        assert config.config.blocklist == ["app1", "app2"]

    @patch("pathlib.Path.home")
    @patch("tomli.load", side_effect=FileNotFoundError)
    def test_config_file_missing(self, mock_tomli_load, mock_home) -> None:
        """Test behavior when config file doesn't exist."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        config = EnhancedConfigManager()

        # Should use defaults when file doesn't exist
        assert config.config.debug_mode is False
        assert config.config.log_level == "INFO"
        assert config.config.blocklist == []

    @patch("pathlib.Path.home")
    @patch("tomli.load", side_effect=Exception("Parse error"))
    def test_config_file_parse_error(self, mock_tomli_load, mock_home) -> None:
        """Test handling of config file parse errors."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        config = EnhancedConfigManager()

        # Should fall back to defaults on parse error
        assert config.config.debug_mode is False
        assert config.config.log_level == "INFO"

    @patch("pathlib.Path.home")
    @patch("tomli_w.dump")
    def test_config_save(self, mock_tomli_dump, mock_home) -> None:
        """Test saving configuration to file."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        config = EnhancedConfigManager()

        # Modify config
        config.config.debug_mode = True
        config.config.bin_dir = "/new/bin"

        # Save config
        config.save_config()

        # Should write to file
        mock_tomli_dump.assert_called_once()

    @patch("pathlib.Path.home")
    def test_config_validation(self, mock_home) -> None:
        """Test configuration validation."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        config = EnhancedConfigManager()

        # Test valid configurations
        valid_configs = [
            {"debug_mode": True, "log_level": "DEBUG"},
            {"debug_mode": False, "log_level": "INFO"},
            {"debug_mode": False, "log_level": "WARNING"},
            {"blocklist": ["app1", "app2"]},
            {"bin_dir": "/valid/path"},
        ]

        for valid_config in valid_configs:
            # Should not raise exceptions for valid configs
            for key, value in valid_config.items():
                setattr(config.config, key, value)
                # Verify the value was actually set
                actual_value = getattr(config.config, key)
                assert actual_value == value, (
                    f"Expected {key}={value}, got {actual_value}"
                )

    @patch("pathlib.Path.home")
    def test_config_directory_paths(self, mock_home) -> None:
        """Test configuration directory path resolution."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        config = EnhancedConfigManager()

        # Check directory paths
        expected_config_dir = self.temp_dir / ".config" / "fplaunchwrapper"
        expected_data_dir = self.temp_dir / ".local" / "share" / "fplaunchwrapper"

        assert str(config.config_dir) == str(expected_config_dir)
        assert str(config.data_dir) == str(expected_data_dir)

    @patch("pathlib.Path.home")
    @patch.dict("os.environ", {"XDG_CONFIG_HOME": "/custom/config"})
    def test_xdg_config_home_support(self, mock_home) -> None:
        """Test XDG_CONFIG_HOME environment variable support."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        config = EnhancedConfigManager()

        # Should respect XDG_CONFIG_HOME
        expected_config_dir = Path("/custom/config/fplaunchwrapper")
        assert str(config.config_dir) == str(expected_config_dir)

    @patch("pathlib.Path.home")
    @patch.dict("os.environ", {"XDG_DATA_HOME": "/custom/data"})
    def test_xdg_data_home_support(self, mock_home) -> None:
        """Test XDG_DATA_HOME environment variable support."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        config = EnhancedConfigManager()

        # Should respect XDG_DATA_HOME
        expected_data_dir = Path("/custom/data/fplaunchwrapper")
        assert str(config.data_dir) == str(expected_data_dir)

    @patch("pathlib.Path.home")
    def test_config_reset_to_defaults(self, mock_home) -> None:
        """Test resetting configuration to defaults."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        config = EnhancedConfigManager()

        # Modify config
        config.config.debug_mode = True
        config.config.log_level = "DEBUG"
        config.config.blocklist = ["test"]

        # Reset should restore defaults
        config.reset_to_defaults()

        assert config.config.debug_mode is False
        assert config.config.log_level == "INFO"
        assert config.config.blocklist == []

    @patch("pathlib.Path.home")
    @patch("tomli_w.dump")
    def test_atomic_config_save(self, mock_tomli_dump, mock_home) -> None:
        """Test atomic configuration saving."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        config = EnhancedConfigManager()

        # Save should be atomic (use temporary file then rename)
        config.save_config()

        # Verify atomic save was attempted
        mock_tomli_dump.assert_called_once()

    def test_config_schema_validation(self) -> None:
        """Test configuration schema validation."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        config = EnhancedConfigManager()

        # Test that config has expected attributes
        required_attrs = ["bin_dir", "debug_mode", "log_level", "blocklist"]

        for attr in required_attrs:
            assert hasattr(config.config, attr), (
                f"Config missing required attribute: {attr}"
            )

    @patch("pathlib.Path.home")
    def test_config_migration_handling(self, mock_home) -> None:
        """Test handling of old configuration formats."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = self.temp_dir

        # Create old-style config file
        self.config_dir.mkdir(parents=True)
        old_config = self.config_dir / "config"
        old_config.write_text("/old/bin/dir\n")

        config = EnhancedConfigManager()

        # Should handle old config gracefully
        assert config.config.bin_dir is not None


class TestConfigManagerIntegration:
    """Test config manager integration with other components."""

    @patch("pathlib.Path.home")
    def test_config_manager_with_generate(self, mock_home) -> None:
        """Test config manager integration with generator."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = Path(tempfile.gettempdir())

        config = EnhancedConfigManager()

        # Should provide valid paths for generator
        assert config.config_dir.exists() or config.config_dir.parent.exists()
        assert config.data_dir.exists() or config.data_dir.parent.exists()

    @patch("pathlib.Path.home")
    def test_config_manager_thread_safety(self, mock_home) -> None:
        """Test thread safety of config manager."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        mock_home.return_value = Path(tempfile.gettempdir())

        import threading

        results = []
        errors = []

        def worker() -> None:
            try:
                config = EnhancedConfigManager()
                results.append(config.config.debug_mode)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for _i in range(5):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should not have errors
        assert len(errors) == 0
        # All results should be the same (default value)
        assert all(r is False for r in results)


class TestGetEffectiveHookFailureMode:
    """Test get_effective_hook_failure_mode() with all precedence levels."""

    def setup_method(self) -> None:
        """Set up test environment."""
        import tempfile
        import shutil

        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / ".config" / "fplaunchwrapper"
        self.data_dir = self.temp_dir / ".local" / "fplaunchwrapper"

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_runtime_override_valid_value(self) -> None:
        """Test runtime override with valid value in HOOK_FAILURE_MODES."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            # Runtime override should take highest precedence
            mode = config.get_effective_hook_failure_mode(
                "test.App", "pre", runtime_override="abort"
            )
            assert mode == "abort"

    def test_runtime_override_warn_value(self) -> None:
        """Test runtime override with 'warn' value."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            mode = config.get_effective_hook_failure_mode(
                "test.App", "pre", runtime_override="warn"
            )
            assert mode == "warn"

    def test_runtime_override_ignore_value(self) -> None:
        """Test runtime override with 'ignore' value."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            mode = config.get_effective_hook_failure_mode(
                "test.App", "post", runtime_override="ignore"
            )
            assert mode == "ignore"

    def test_runtime_override_invalid_value_ignored(self) -> None:
        """Test that invalid runtime override values are ignored."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            # Invalid runtime override should be ignored, fall back to default
            mode = config.get_effective_hook_failure_mode(
                "test.App", "pre", runtime_override="invalid"
            )
            assert mode == "warn"  # Falls through to built-in default

    def test_env_var_valid_value(self) -> None:
        """Test environment variable FPWRAPPER_HOOK_FAILURE with valid value."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch.dict("os.environ", {"FPWRAPPER_HOOK_FAILURE": "abort"}, clear=False):
                config = EnhancedConfigManager()
                mode = config.get_effective_hook_failure_mode("test.App", "pre")
                assert mode == "abort"

    def test_env_var_warn_value(self) -> None:
        """Test environment variable with 'warn' value."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch.dict("os.environ", {"FPWRAPPER_HOOK_FAILURE": "warn"}, clear=False):
                config = EnhancedConfigManager()
                mode = config.get_effective_hook_failure_mode("test.App", "post")
                assert mode == "warn"

    def test_env_var_invalid_value_ignored(self) -> None:
        """Test that invalid environment variable values are ignored."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch.dict("os.environ", {"FPWRAPPER_HOOK_FAILURE": "invalid"}, clear=False):
                config = EnhancedConfigManager()
                mode = config.get_effective_hook_failure_mode("test.App", "pre")
                assert mode == "warn"  # Falls through to built-in default

    def test_runtime_override_beats_env_var(self) -> None:
        """Test that runtime override takes precedence over environment variable."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch.dict("os.environ", {"FPWRAPPER_HOOK_FAILURE": "abort"}, clear=False):
                config = EnhancedConfigManager()
                # Runtime override should win over env var
                mode = config.get_effective_hook_failure_mode(
                    "test.App", "pre", runtime_override="ignore"
                )
                assert mode == "ignore"

    def test_per_app_pre_launch_failure_mode(self) -> None:
        """Test per-app pre_launch_failure_mode configuration."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            # Set per-app preference
            from lib.config_manager import AppPreferences

            config.config.app_preferences["test.App"] = AppPreferences(
                pre_launch_failure_mode="abort"
            )
            mode = config.get_effective_hook_failure_mode("test.App", "pre")
            assert mode == "abort"

    def test_per_app_post_launch_failure_mode(self) -> None:
        """Test per-app post_launch_failure_mode configuration."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            # Set per-app preference
            from lib.config_manager import AppPreferences

            config.config.app_preferences["test.App"] = AppPreferences(
                post_launch_failure_mode="ignore"
            )
            mode = config.get_effective_hook_failure_mode("test.App", "post")
            assert mode == "ignore"

    def test_per_app_pre_mode_for_post_hook(self) -> None:
        """Test that pre_launch_failure_mode is not used for post hooks."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            from lib.config_manager import AppPreferences

            config.config.app_preferences["test.App"] = AppPreferences(
                pre_launch_failure_mode="abort"
            )
            # post hook should not use pre_launch_failure_mode
            mode = config.get_effective_hook_failure_mode("test.App", "post")
            assert mode == "warn"  # Falls through to built-in default

    def test_global_pre_launch_failure_mode_default(self) -> None:
        """Test global pre_launch_failure_mode_default fallback."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            config.config.pre_launch_failure_mode_default = "abort"
            mode = config.get_effective_hook_failure_mode("test.App", "pre")
            assert mode == "abort"

    def test_global_post_launch_failure_mode_default(self) -> None:
        """Test global post_launch_failure_mode_default fallback."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            config.config.post_launch_failure_mode_default = "ignore"
            mode = config.get_effective_hook_failure_mode("test.App", "post")
            assert mode == "ignore"

    def test_global_hook_failure_mode_default(self) -> None:
        """Test global hook_failure_mode_default fallback."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            config.config.hook_failure_mode_default = "abort"
            mode = config.get_effective_hook_failure_mode("test.App", "pre")
            assert mode == "abort"

    def test_pre_launch_default_beats_global_default(self) -> None:
        """Test that pre_launch_failure_mode_default beats hook_failure_mode_default."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            config.config.hook_failure_mode_default = "abort"
            config.config.pre_launch_failure_mode_default = "ignore"
            mode = config.get_effective_hook_failure_mode("test.App", "pre")
            assert mode == "ignore"  # pre_launch_default wins

    def test_built_in_default(self) -> None:
        """Test built-in default 'warn' when all else fails."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            # Clear all defaults
            config.config.hook_failure_mode_default = None
            config.config.pre_launch_failure_mode_default = None
            config.config.post_launch_failure_mode_default = None
            mode = config.get_effective_hook_failure_mode("unknown.App", "pre")
            assert mode == "warn"

    def test_full_precedence_chain(self) -> None:
        """Test the full precedence chain from runtime override to built-in default."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        from lib.config_manager import AppPreferences

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch.dict("os.environ", {"FPWRAPPER_HOOK_FAILURE": "warn"}, clear=False):
                config = EnhancedConfigManager()

                # Set up all levels
                config.config.hook_failure_mode_default = "ignore"
                config.config.pre_launch_failure_mode_default = "abort"
                config.config.app_preferences["test.App"] = AppPreferences(
                    pre_launch_failure_mode="warn"
                )

                # Runtime override wins
                mode = config.get_effective_hook_failure_mode(
                    "test.App", "pre", runtime_override="abort"
                )
                assert mode == "abort"

                # Without runtime override, env var wins
                mode = config.get_effective_hook_failure_mode("test.App", "pre")
                assert mode == "warn"  # From env var

    def test_unknown_app_falls_back_to_global(self) -> None:
        """Test that unknown apps fall back to global preferences."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            config.config.hook_failure_mode_default = "abort"
            mode = config.get_effective_hook_failure_mode("unknown.App", "pre")
            assert mode == "abort"


class TestPydanticValidators:
    """Test Pydantic validators for security and validation."""

    def test_validate_custom_args_safe(self) -> None:
        """Test that safe custom args pass validation."""
        try:
            from lib.config_manager import PydanticAppPreferences, PYDANTIC_AVAILABLE
        except ImportError:
            pytest.skip("PydanticAppPreferences not available")

        if not PYDANTIC_AVAILABLE:
            pytest.skip("Pydantic not available")

        # Safe args should pass
        prefs = PydanticAppPreferences(custom_args=["--verbose", "--force"])
        assert prefs.custom_args == ["--verbose", "--force"]

    def test_validate_custom_args_with_flag_allowed(self) -> None:
        """Test that flags starting with -- are allowed even with special chars."""
        try:
            from lib.config_manager import PydanticAppPreferences, PYDANTIC_AVAILABLE
        except ImportError:
            pytest.skip("PydanticAppPreferences not available")

        if not PYDANTIC_AVAILABLE:
            pytest.skip("Pydantic not available")

        # Flags starting with -- should be allowed
        prefs = PydanticAppPreferences(
            custom_args=["--filesystem=/home/user/test", "--device=/dev/dri"]
        )
        assert prefs.custom_args == ["--filesystem=/home/user/test", "--device=/dev/dri"]

    def test_validate_custom_args_dangerous_semicolon(self) -> None:
        """Test that semicolon in custom args is rejected."""
        try:
            from lib.config_manager import (
                PydanticAppPreferences,
                PYDANTIC_AVAILABLE,
                ValidationError,
            )
        except ImportError:
            pytest.skip("PydanticAppPreferences not available")

        if not PYDANTIC_AVAILABLE:
            pytest.skip("Pydantic not available")

        with pytest.raises(ValidationError):
            PydanticAppPreferences(custom_args=["test;rm -rf /"])

    def test_validate_custom_args_dangerous_pipe(self) -> None:
        """Test that pipe in custom args is rejected."""
        try:
            from lib.config_manager import (
                PydanticAppPreferences,
                PYDANTIC_AVAILABLE,
                ValidationError,
            )
        except ImportError:
            pytest.skip("PydanticAppPreferences not available")

        if not PYDANTIC_AVAILABLE:
            pytest.skip("Pydantic not available")

        with pytest.raises(ValidationError):
            PydanticAppPreferences(custom_args=["test | cat"])

    def test_validate_custom_args_dangerous_backtick(self) -> None:
        """Test that backtick in custom args is rejected."""
        try:
            from lib.config_manager import (
                PydanticAppPreferences,
                PYDANTIC_AVAILABLE,
                ValidationError,
            )
        except ImportError:
            pytest.skip("PydanticAppPreferences not available")

        if not PYDANTIC_AVAILABLE:
            pytest.skip("Pydantic not available")

        with pytest.raises(ValidationError):
            PydanticAppPreferences(custom_args=["`whoami`"])

    def test_validate_custom_args_dangerous_dollar(self) -> None:
        """Test that dollar sign in custom args is rejected."""
        try:
            from lib.config_manager import (
                PydanticAppPreferences,
                PYDANTIC_AVAILABLE,
                ValidationError,
            )
        except ImportError:
            pytest.skip("PydanticAppPreferences not available")

        if not PYDANTIC_AVAILABLE:
            pytest.skip("Pydantic not available")

        with pytest.raises(ValidationError):
            PydanticAppPreferences(custom_args=["$(whoami)"])

    def test_validate_failure_mode_valid(self) -> None:
        """Test that valid failure modes pass validation."""
        try:
            from lib.config_manager import PydanticAppPreferences, PYDANTIC_AVAILABLE
        except ImportError:
            pytest.skip("PydanticAppPreferences not available")

        if not PYDANTIC_AVAILABLE:
            pytest.skip("Pydantic not available")

        prefs = PydanticAppPreferences(pre_launch_failure_mode="abort")
        assert prefs.pre_launch_failure_mode == "abort"

        prefs = PydanticAppPreferences(post_launch_failure_mode="ignore")
        assert prefs.post_launch_failure_mode == "ignore"

    def test_validate_failure_mode_invalid(self) -> None:
        """Test that invalid failure modes are rejected."""
        try:
            from lib.config_manager import (
                PydanticAppPreferences,
                PYDANTIC_AVAILABLE,
                ValidationError,
            )
        except ImportError:
            pytest.skip("PydanticAppPreferences not available")

        if not PYDANTIC_AVAILABLE:
            pytest.skip("Pydantic not available")

        with pytest.raises(ValidationError):
            PydanticAppPreferences(pre_launch_failure_mode="invalid")


class TestFallbackConfig:
    """Test fallback config functions when TOML is not available."""

    def setup_method(self) -> None:
        """Set up test environment."""
        import tempfile
        import shutil

        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / ".config" / "fplaunchwrapper"
        self.config_dir.mkdir(parents=True)
        self.config_file = self.config_dir / "config.toml"

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_fallback_config_basic(self) -> None:
        """Test _load_fallback_config with basic key=value format."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        # Write a simple key=value config
        self.config_file.write_text(
            "# Test config\n"
            "bin_dir=/custom/bin\n"
            "debug_mode=true\n"
            "log_level=DEBUG\n"
            "cron_interval=12\n"
            "enable_notifications=false\n"
            "hook_failure_mode_default=abort\n"
        )

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            # Force fallback loading
            with patch("lib.config_manager.TOML_AVAILABLE", False):
                config._load_fallback_config()
                assert config.config.bin_dir == "/custom/bin"
                assert config.config.debug_mode is True
                assert config.config.log_level == "DEBUG"
                assert config.config.cron_interval == 12
                assert config.config.enable_notifications is False
                assert config.config.hook_failure_mode_default == "abort"

    def test_load_fallback_config_missing_file(self) -> None:
        """Test _load_fallback_config when file doesn't exist."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            # Remove config file
            self.config_file.unlink(missing_ok=True)
            with patch("lib.config_manager.TOML_AVAILABLE", False):
                config._load_fallback_config()
                # Should use defaults
                assert config.config.bin_dir is not None

    def test_load_fallback_config_ignores_comments(self) -> None:
        """Test that _load_fallback_config ignores comments and empty lines."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        self.config_file.write_text(
            "# This is a comment\n"
            "\n"
            "  # Indented comment\n"
            "bin_dir=/test/bin\n"
        )

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            with patch("lib.config_manager.TOML_AVAILABLE", False):
                config._load_fallback_config()
                assert config.config.bin_dir == "/test/bin"

    def test_load_fallback_config_invalid_hook_mode(self) -> None:
        """Test that invalid hook_failure_mode_default is ignored."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        self.config_file.write_text(
            "hook_failure_mode_default=invalid\n"
        )

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            with patch("lib.config_manager.TOML_AVAILABLE", False):
                config._load_fallback_config()
                # Should keep the default "warn"
                assert config.config.hook_failure_mode_default == "warn"

    def test_save_fallback_config(self) -> None:
        """Test _save_fallback_config writes key=value format."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            config.config.bin_dir = "/test/bin"
            config.config.debug_mode = True
            config.config.log_level = "DEBUG"
            config.config.cron_interval = 24
            config.config.enable_notifications = False
            config.config.hook_failure_mode_default = "abort"

            with patch("lib.config_manager.TOML_AVAILABLE", False):
                config._save_fallback_config()

            # Read back and verify
            content = self.config_file.read_text()
            assert "bin_dir=/test/bin" in content
            assert "debug_mode=True" in content
            assert "log_level=DEBUG" in content
            assert "cron_interval=24" in content
            assert "enable_notifications=False" in content
            assert "hook_failure_mode_default=abort" in content

    def test_save_fallback_config_creates_file(self) -> None:
        """Test that _save_fallback_config creates the config file."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        # Ensure config file doesn't exist
        self.config_file.unlink(missing_ok=True)

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            with patch("lib.config_manager.TOML_AVAILABLE", False):
                config._save_fallback_config()

            assert self.config_file.exists()


class TestSerializeConfig:
    """Test _serialize_config method."""

    def setup_method(self) -> None:
        """Set up test environment."""
        import tempfile
        import shutil

        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_serialize_basic_config(self) -> None:
        """Test serializing basic configuration."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            config.config.bin_dir = "/test/bin"
            config.config.debug_mode = True
            config.config.log_level = "DEBUG"

            data = config._serialize_config()

            assert data["bin_dir"] == "/test/bin"
            assert data["debug_mode"] is True
            assert data["log_level"] == "DEBUG"
            assert "schema_version" in data

    def test_serialize_with_app_preferences(self) -> None:
        """Test serializing configuration with app preferences."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        from lib.config_manager import AppPreferences

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            config.config.app_preferences["test.App"] = AppPreferences(
                launch_method="flatpak",
                pre_launch_script="/path/to/pre.sh",
                post_launch_script="/path/to/post.sh",
                pre_launch_failure_mode="abort",
                post_launch_failure_mode="ignore",
            )

            data = config._serialize_config()

            assert "app_preferences" in data
            assert "test.App" in data["app_preferences"]
            assert data["app_preferences"]["test.App"]["launch_method"] == "flatpak"
            assert data["app_preferences"]["test.App"]["pre_launch_script"] == "/path/to/pre.sh"
            assert data["app_preferences"]["test.App"]["post_launch_script"] == "/path/to/post.sh"
            assert data["app_preferences"]["test.App"]["pre_launch_failure_mode"] == "abort"
            assert data["app_preferences"]["test.App"]["post_launch_failure_mode"] == "ignore"

    def test_serialize_with_hook_failure_modes(self) -> None:
        """Test serializing configuration with hook failure mode defaults."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            config.config.hook_failure_mode_default = "abort"
            config.config.pre_launch_failure_mode_default = "warn"
            config.config.post_launch_failure_mode_default = "ignore"

            data = config._serialize_config()

            assert data["hook_failure_mode_default"] == "abort"
            assert data["pre_launch_failure_mode_default"] == "warn"
            assert data["post_launch_failure_mode_default"] == "ignore"

    def test_serialize_with_permission_presets(self) -> None:
        """Test serializing configuration with permission presets."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            config.config.permission_presets["custom"] = [
                "--filesystem=home",
                "--device=dri",
            ]

            data = config._serialize_config()

            assert "permission_presets" in data
            assert data["permission_presets"]["custom"] == [
                "--filesystem=home",
                "--device=dri",
            ]


class TestApplyUnvalidatedConfig:
    """Test _apply_unvalidated_config method (fallback when Pydantic unavailable)."""

    def setup_method(self) -> None:
        """Set up test environment."""
        import tempfile
        import shutil

        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_apply_basic_config(self) -> None:
        """Test applying basic configuration data."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            data = {
                "bin_dir": "/custom/bin",
                "debug_mode": True,
                "log_level": "DEBUG",
                "cron_interval": 12,
                "enable_notifications": False,
            }

            config._apply_unvalidated_config(data)

            assert config.config.bin_dir == "/custom/bin"
            assert config.config.debug_mode is True
            assert config.config.log_level == "DEBUG"
            assert config.config.cron_interval == 12
            assert config.config.enable_notifications is False

    def test_apply_with_hook_failure_modes(self) -> None:
        """Test applying configuration with hook failure modes."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            data = {
                "hook_failure_mode_default": "abort",
                "pre_launch_failure_mode_default": "warn",
                "post_launch_failure_mode_default": "ignore",
            }

            config._apply_unvalidated_config(data)

            assert config.config.hook_failure_mode_default == "abort"
            assert config.config.pre_launch_failure_mode_default == "warn"
            assert config.config.post_launch_failure_mode_default == "ignore"

    def test_apply_with_global_preferences(self) -> None:
        """Test applying configuration with global preferences."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            data = {
                "global_preferences": {
                    "launch_method": "flatpak",
                    "env_vars": {"VAR1": "value1"},
                    "pre_launch_script": "/path/to/pre.sh",
                    "post_launch_script": "/path/to/post.sh",
                    "pre_launch_failure_mode": "abort",
                    "post_launch_failure_mode": "ignore",
                }
            }

            config._apply_unvalidated_config(data)

            assert config.config.global_preferences.launch_method == "flatpak"
            assert config.config.global_preferences.env_vars == {"VAR1": "value1"}
            assert config.config.global_preferences.pre_launch_script == "/path/to/pre.sh"
            assert config.config.global_preferences.post_launch_script == "/path/to/post.sh"
            assert config.config.global_preferences.pre_launch_failure_mode == "abort"
            assert config.config.global_preferences.post_launch_failure_mode == "ignore"

    def test_apply_with_app_preferences(self) -> None:
        """Test applying configuration with app preferences."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            data = {
                "app_preferences": {
                    "test.App": {
                        "launch_method": "system",
                        "env_vars": {"APP_VAR": "app_value"},
                        "pre_launch_failure_mode": "abort",
                    }
                }
            }

            config._apply_unvalidated_config(data)

            assert "test.App" in config.config.app_preferences
            assert config.config.app_preferences["test.App"].launch_method == "system"
            assert config.config.app_preferences["test.App"].env_vars == {"APP_VAR": "app_value"}
            assert config.config.app_preferences["test.App"].pre_launch_failure_mode == "abort"

    def test_apply_with_permission_presets_dict(self) -> None:
        """Test applying configuration with permission presets in dict format."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            data = {
                "permission_presets": {
                    "custom": {
                        "permissions": ["--filesystem=home", "--device=dri"]
                    }
                }
            }

            config._apply_unvalidated_config(data)

            assert config.config.permission_presets["custom"] == [
                "--filesystem=home",
                "--device=dri",
            ]

    def test_apply_with_permission_presets_list(self) -> None:
        """Test applying configuration with permission presets in list format."""
        if not EnhancedConfigManager:
            pytest.skip("EnhancedConfigManager class not available")

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            config = EnhancedConfigManager()
            data = {
                "permission_presets": {
                    "custom": ["--filesystem=home", "--device=dri"]
                }
            }

            config._apply_unvalidated_config(data)

            assert config.config.permission_presets["custom"] == [
                "--filesystem=home",
                "--device=dri",
            ]


class TestMainFunction:
    """Test the main() CLI function."""

    def setup_method(self) -> None:
        """Set up test environment."""
        import tempfile
        import shutil

        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_main_init(self, capsys) -> None:
        """Test main() with init command."""
        from lib.config_manager import main

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch("sys.argv", ["fplaunch-config", "init"]):
                main()
                captured = capsys.readouterr()
                assert "initialized successfully" in captured.out

    def test_main_block(self, capsys) -> None:
        """Test main() with block command."""
        from lib.config_manager import main

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch("sys.argv", ["fplaunch-config", "block", "test.app"]):
                main()
                captured = capsys.readouterr()
                assert "Blocked test.app" in captured.out

    def test_main_unblock(self, capsys) -> None:
        """Test main() with unblock command."""
        from lib.config_manager import main

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            # First block the app
            with patch("sys.argv", ["fplaunch-config", "block", "test.app"]):
                main()
            # Then unblock it
            with patch("sys.argv", ["fplaunch-config", "unblock", "test.app"]):
                main()
                captured = capsys.readouterr()
                assert "Unblocked test.app" in captured.out

    def test_main_list_presets(self, capsys) -> None:
        """Test main() with list-presets command."""
        from lib.config_manager import main

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch("sys.argv", ["fplaunch-config", "list-presets"]):
                main()
                captured = capsys.readouterr()
                assert "Available permission presets" in captured.out

    def test_main_get_preset(self, capsys) -> None:
        """Test main() with get-preset command."""
        from lib.config_manager import main

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch("sys.argv", ["fplaunch-config", "get-preset", "gaming"]):
                main()
                captured = capsys.readouterr()
                assert "Permissions for preset 'gaming'" in captured.out

    def test_main_get_preset_not_found(self, capsys) -> None:
        """Test main() with get-preset command for non-existent preset."""
        from lib.config_manager import main

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch("sys.argv", ["fplaunch-config", "get-preset", "nonexistent"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
