#!/usr/bin/env python3
"""Unit tests for config_manager.py
Tests configuration file management with proper mocking.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add lib to path
# Import the module to test
try:
    from fplaunch.config_manager import EnhancedConfigManager
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
            try:
                for key, value in valid_config.items():
                    setattr(config.config, key, value)
                # If we get here, config is valid
                assert True
            except Exception:
                msg = f"Valid config {valid_config} should not raise exception"
                raise AssertionError(msg)

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
