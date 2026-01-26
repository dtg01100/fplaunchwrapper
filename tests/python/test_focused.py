#!/usr/bin/env python3
"""Pytest tests for focused fplaunchwrapper functionality."""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add lib to path
# Mock python_utils
sys.modules["python_utils"] = type(sys)("python_utils")
sys.modules["python_utils"].sanitize_string = lambda x: x
sys.modules["python_utils"].canonicalize_path_no_resolve = lambda x: x
sys.modules["python_utils"].validate_home_dir = lambda x: x
sys.modules["python_utils"].is_wrapper_file = lambda x: True
sys.modules["python_utils"].get_wrapper_id = lambda x: "org.test.app"
sys.modules["python_utils"].sanitize_id_to_name = lambda x: x.split(".")[-1].lower()
sys.modules["python_utils"].find_executable = lambda x: f"/usr/bin/{x}"
sys.modules["python_utils"].safe_mktemp = lambda *args: f"/tmp/test_{args[0] if args else 'tmp'}"

try:
    from lib.generate import WrapperGenerator
    from lib.manage import WrapperManager
    from lib.systemd_setup import SystemdSetup

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
class TestFocusedFunctionality:
    """Focused functionality tests."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp())
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"
        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_module_imports(self) -> None:
        """Test that modules can be imported."""
        assert MODULES_AVAILABLE

    def test_wrapper_generator_creation(self, temp_env) -> None:
        """Test WrapperGenerator creation."""
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=True,
            emit_verbose=True,
        )
        assert generator is not None

    def test_wrapper_manager_creation(self, temp_env) -> None:
        """Test WrapperManager creation."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=True,
            emit_verbose=True,
        )
        assert manager is not None

    def test_systemd_setup_creation(self, temp_env) -> None:
        """Test SystemdSetup creation."""
        setup = SystemdSetup(
            bin_dir=str(temp_env["bin_dir"]),
            emit_mode=True,
            emit_verbose=True,
        )
        assert setup is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
